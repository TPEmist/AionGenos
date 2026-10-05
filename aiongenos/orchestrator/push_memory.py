"""push_memory.py — cross-episode memory (recap → buffer → retrieval) for the
WP1-③a PUSH collect instrument (push_collect.py).

Why a separate module: the shared memory substrate (stage4_recap,
RecapBuffer, MemoryRetriever) is reach-shaped and frozen with the P1
submission (a D11 night batch imports it; equivalence is ledgered in
docs/p2_prereg/dual_collect_equivalence_ledger.md). Push re-uses its PIECES
unedited — RecapRecord + RecapBuffer.add (storage/schema), call_vlm_sync
(teacher call), ImageEmbedder (DINOv2 key), MemoryPreamble +
_load_past_image_b64_list (preamble container + past-image loading),
_trim_to_word_limit (hard word cap) — and adds only what is push-semantic:

  - a PUSH recap prompt (cube displacement / cube→goal per round, round-1
    EEF target vs what happened, ends in a reusable LESSON);
  - a push outcome class from cube→goal distance (cm), not EE distance;
  - PushMemoryRetriever: same score SHAPE as RecapBuffer.retrieve
    (α·img_cos + (1−α)·exp(−‖Δ‖/scale), success floor) but the state term is
    keyed on state_anchor["push_situation"] = cube_xy + goal_xy (base frame,
    cm) — the EE starts at a fixed standby pose so init_L_EE carries no
    situation information in push;
  - a push-worded preamble;
  - per-episode dump dir + replay augmentation (init_* fields + metadata)
    without changing _write_episode's signature.

Every deviation from the L0/L2 path is a ledger entry (dual_collect_equivalence_ledger.md,
"Push cross-episode memory", items 6–17).
"""

from __future__ import annotations

import io
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import numpy as np

from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord

logger = logging.getLogger(__name__)

PUSH_TASK_TAG = "WP1_3a_push"
PUSH_RECAP_PROMPT_VERSION = "push_recap_v1"
# Default retrieval hyper-parameters (surface to the run script as flags).
# state_scale_cm=5: Pin-4b situation space (cube region × cube-relative goal)
# gives a median pairwise ‖Δ push_situation‖ ≈ 5.4 cm (p10 2.5, p90 9.9; MC
# over the push_s3a_cfg ranges). With the reach default 30 cm the state term
# would span only 0.92→0.72 over that range (the same collapse D10 saw on the
# image term); 5 cm spans 0.61→0.14. It also equals the Pin-11 success radius.
DEFAULT_IMAGE_WEIGHT = 0.4
DEFAULT_STATE_SCALE_CM = 5.0
DEFAULT_SUCCESS_FLOOR_FRAC = 2.0 / 3.0
# near-miss: best cube→goal within this multiple of the success radius
NEAR_MISS_RADIUS_MULT = 1.5


# ─────────────────────────── state snapshots ───────────────────────────


@dataclass(frozen=True)
class PushStateSnapshot:
    """Pre-action push state (base frame). Metric fields are what the sim
    measured; *_int fields are what the teacher was shown (get_state grid)."""

    ee_b: tuple[float, float, float]
    cube_b: tuple[float, float, float]
    goal_b: tuple[float, float, float]
    ee_int: tuple[int, int, int]
    cube_int: tuple[int, int]
    goal_int: tuple[int, int]

    @property
    def cube_goal_dist_cm(self) -> float:
        return float(np.linalg.norm(np.array(self.cube_b[:2]) - np.array(self.goal_b[:2]))) * 100.0

    def situation(self) -> list[float]:
        return push_situation(self.cube_b, self.goal_b)


def _r4(xs: Sequence[float]) -> list[float]:
    return [round(float(v), 4) for v in xs]


def _int_or_none(v: Any) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def snapshot_push_state(env, level_config, state: Optional[dict] = None) -> PushStateSnapshot:
    """Read the push state from the env interface. Pass ``state`` if the
    caller already called env.get_state this step (avoids a second read)."""
    st = state if state is not None else env.get_state(level_config)
    return PushStateSnapshot(
        ee_b=tuple(_r4(env.get_left_ee_pose_b())),
        cube_b=tuple(_r4(env.get_cube_pose_b())),
        goal_b=tuple(_r4(env.get_goal_pose_b())),
        ee_int=(_int_or_none(st.get("left_x")), _int_or_none(st.get("left_y")), _int_or_none(st.get("left_z"))),
        cube_int=(_int_or_none(st.get("cube_x")), _int_or_none(st.get("cube_y"))),
        goal_int=(_int_or_none(st.get("goal_x")), _int_or_none(st.get("goal_y"))),
    )


def snapshot_to_round_fields(snap: PushStateSnapshot) -> dict[str, Any]:
    """Per-round pre-action state for round_meta (r-tracking raw material)."""
    return {
        "ee_b_pre": list(snap.ee_b),
        "cube_b_pre": list(snap.cube_b),
        "goal_b_pre": list(snap.goal_b),
        "ee_int_pre": list(snap.ee_int),
        "cube_int_pre": list(snap.cube_int),
        "goal_int_pre": list(snap.goal_int),
        "cube_goal_dist_m_pre": round(snap.cube_goal_dist_cm / 100.0, 4),
    }


def push_situation(cube_b: Sequence[float], goal_b: Sequence[float]) -> list[float]:
    """Retrieval situation key: [cube_x, cube_y, goal_x, goal_y], metric base
    frame (m). Distances between keys are converted to cm when scored."""
    return _r4([cube_b[0], cube_b[1], goal_b[0], goal_b[1]])


# ─────────────────────────── dumps + replay ───────────────────────────


def episode_dump_dir(dump_images_root: Optional[Path], run_id: str, ep_id: str) -> Optional[Path]:
    """Same layout as collect.py: {root}/{run_id}/{ep_id}/ (created)."""
    if dump_images_root is None:
        return None
    d = Path(dump_images_root) / run_id / ep_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def dump_png(ep_dump_dir: Optional[Path], name: str, png: Optional[bytes]) -> Optional[Path]:
    if ep_dump_dir is None or not png:
        return None
    p = Path(ep_dump_dir) / name
    p.write_bytes(png)
    return p


def write_dump_meta(ep_dump_dir: Optional[Path], meta: dict[str, Any]) -> None:
    if ep_dump_dir is not None:
        (Path(ep_dump_dir) / "meta.json").write_text(json.dumps(meta, indent=2))


class _AugmentingReplay:
    """Proxy handed to the SHARED _write_episode: forwards base_path and
    injects the extra ReplayEpisode fields at write() time. Lets push
    populate init_* / env_seed / metadata with zero copy of _write_episode
    and no change to its signature."""

    def __init__(self, inner, update: dict[str, Any]) -> None:
        self._inner = inner
        self._update = update
        self.base_path = inner.base_path

    def write(self, episode):
        return self._inner.write(episode.model_copy(update=self._update))


def write_push_episode(replay, write_args: tuple, *, init: PushStateSnapshot,
                       env_seed: Optional[int], metadata: dict[str, Any]) -> None:
    """_write_episode(replay, *write_args) + push init fields + metadata."""
    from aiongenos.orchestrator.collect_common import _write_episode
    update = {
        "init_cube_pose": {"yellow": list(init.cube_b)},
        "init_left_ee_pose": list(init.ee_b),
        "env_seed": env_seed,
        "metadata": metadata,
    }
    _write_episode(_AugmentingReplay(replay, update), *write_args)


def replay_rounds_state(round_meta: list[dict]) -> list[dict[str, Any]]:
    """Compact per-round state for replay metadata (so (c, s) are computable
    from the replay alone — scripts/analysis/push_r_inputs.py)."""
    keys = ("round", "ee_b_pre", "cube_b_pre", "goal_b_pre", "eef_target_int",
            "eef_target_m", "ori_offset_deg", "cube_disp_m", "cube_goal_dist_m")
    return [{k: rm.get(k) for k in keys} for rm in round_meta]


# ─────────────────────────── outcome class ───────────────────────────


def classify_push_outcome(outcome: str, init_dist_cm: float, round_dists_cm: Sequence[float],
                          round_disps_cm: Sequence[float], success_cm: float,
                          min_disp_cm: float) -> str:
    """Push analogue of stage4_recap._classify_outcome, on cube→goal (cm).
    Order: success → cube_not_moved → near_miss → wrong_direction → outcome."""
    if outcome == "success":
        return "success"
    if not round_dists_cm:
        return outcome
    if all(d < min_disp_cm for d in round_disps_cm):
        return "cube_not_moved"
    best, final = min(round_dists_cm), round_dists_cm[-1]
    if best < success_cm * NEAR_MISS_RADIUS_MULT and best < init_dist_cm - min_disp_cm:
        return "near_miss"
    if final > init_dist_cm + min_disp_cm:
        return "wrong_direction"
    return outcome


def select_push_key_round(outcome_class: str, round_dists_cm: Sequence[float]) -> Optional[int]:
    """1-based round whose END scene is the key image (None for success —
    episode_end covers it). near_miss → closest, wrong_direction → furthest,
    else middle (stage4_recap's policy, on cube→goal)."""
    n = len(round_dists_cm)
    if n == 0 or outcome_class == "success":
        return None
    if outcome_class == "near_miss":
        return int(np.argmin(round_dists_cm)) + 1
    if outcome_class == "wrong_direction":
        return int(np.argmax(round_dists_cm)) + 1
    return n // 2 + 1 if n > 1 else 1


def key_round_post_png(ep_dump_dir: Optional[Path], key_round: Optional[int], n_rounds: int) -> Optional[Path]:
    """The scene AFTER round k = round_{k+1}_pre.png (no sim step between).
    None for the last round — its post scene IS episode_end (final image)."""
    if ep_dump_dir is None or key_round is None or key_round >= n_rounds:
        return None
    cand = Path(ep_dump_dir) / f"round_{key_round + 1:02d}_pre.png"
    return cand if cand.exists() else None


# ─────────────────────────── recap prompt ───────────────────────────


def build_push_recap_system_prompt(max_words: int) -> str:
    return (
        "You are a robot reviewing your own past PUSH episode. Your left "
        "end-effector is a rigid pushing tool (gripper held closed, it cannot "
        "grasp). The task was to push the yellow cube onto the green goal zone. "
        "You will see the scene at the start, at the end, and optionally one key "
        "mid-episode scene, plus the per-round physical outcome measured by the "
        "simulator.\n"
        "\n"
        "Your goal is to write a short lesson that a future-you, facing a similar "
        "cube/goal layout, can reuse when choosing the FIRST push target.\n"
        "\n"
        "STRICT RULES:\n"
        f"  - Output {max_words} words MAX, plain prose, single paragraph.\n"
        "  - Do NOT output a LEFT_TARGET_POS / LEFT_TARGET_ORI line or a plan for\n"
        "    this episode. This is a reflection, not an action.\n"
        "  - Say where your round-1 EEF target was relative to the cube and the\n"
        "    goal, and what the cube actually did (how far it moved; closer to or\n"
        "    further from the goal).\n"
        "  - Name ONE concrete adjustment (aim point behind the cube, push depth\n"
        "    past the cube, contact height Z, approach direction) that would have\n"
        "    moved the cube toward the goal — or, on success, what made it work.\n"
        "  - You MAY cite the integer grid coordinates and the cm distances given\n"
        "    below; they are physical facts.\n"
        "  - Finish with one sentence that starts with 'LESSON:'.\n"
    )


def _fmt_int3(v: Sequence[Optional[int]]) -> str:
    return f"(X={v[0]}, Y={v[1]}, Z={v[2]})"


def _fmt_int2(v: Sequence[Optional[int]]) -> str:
    return f"(X={v[0]}, Y={v[1]})"


def build_push_recap_user_prompt(*, instruction: str, outcome: str, outcome_class: str,
                                 init: PushStateSnapshot, round_meta: list[dict],
                                 success_cm: float, key_round: Optional[int],
                                 has_final_image: bool, has_key_image: bool,
                                 max_words: int) -> str:
    n = len(round_meta)
    dists = [rm["cube_goal_dist_m"] * 100 for rm in round_meta]
    p: list[str] = [
        f"TASK: {instruction}",
        f"OUTCOME: {outcome}  (class: {outcome_class})",
        f"ROUND_COUNT: {n}",
        f"SUCCESS_RULE: cube centre within {success_cm:.1f} cm of the goal centre",
        "",
        "INITIAL STATE (Image 1; base-frame integer grid, same scale as your actions):",
        f"  LEFT_EE_POS = {_fmt_int3(init.ee_int)}",
        f"  CUBE_POS    = {_fmt_int2(init.cube_int)}",
        f"  GOAL_POS    = {_fmt_int2(init.goal_int)}",
        f"  CUBE_TO_GOAL distance = {init.cube_goal_dist_cm:.1f} cm",
    ]
    if round_meta:
        r1 = round_meta[0]
        t = r1["eef_target_int"]
        ori = r1.get("ori_offset_deg")
        d1 = dists[0] - init.cube_goal_dist_cm
        p += [
            "",
            "ROUND 1 — YOUR EEF TARGET vs WHAT HAPPENED:",
            f"  EEF target   = {_fmt_int3(t)}  ORI offset = "
            + (f"(P={ori[0]}, Y={ori[1]}, R={ori[2]})" if ori is not None else "neutral"),
            f"  target − start EE = (dX={t[0] - (init.ee_int[0] or 0)}, dY={t[1] - (init.ee_int[1] or 0)}, "
            f"dZ={t[2] - (init.ee_int[2] or 0)}) grid units",
            f"  EE got within {r1.get('servo_min_err_cm', float('nan')):.1f} cm of the target",
            f"  cube moved {r1['cube_disp_m'] * 100:.1f} cm; cube→goal "
            f"{init.cube_goal_dist_cm:.1f} → {dists[0]:.1f} cm "
            f"({'closer' if d1 < 0 else 'further'} by {abs(d1):.1f} cm)",
        ]
        p += ["", "PER-ROUND (EEF target → cube moved / cube→goal after the round):"]
        prev = init.cube_goal_dist_cm
        for rm, d in zip(round_meta, dists):
            p.append(f"  R{rm['round']}: EEF→{_fmt_int3(rm['eef_target_int'])}  cube moved "
                     f"{rm['cube_disp_m'] * 100:.1f} cm, cube→goal {d:.1f} cm ({d - prev:+.1f})")
            prev = d
    if has_final_image and dists:
        best_i = int(np.argmin(dists))
        p += ["", "FINAL STATE (Image 2):",
              f"  final cube→goal = {dists[-1]:.1f} cm; best = {dists[best_i]:.1f} cm after round {best_i + 1}"]
    if has_key_image and key_round is not None:
        p += ["", f"KEY SCENE (Image {3 if has_final_image else 2}): right after round {key_round}, "
                  f"cube→goal = {dists[key_round - 1]:.1f} cm"]
    p += ["", f"Now write your ≤{max_words}-word lesson for future-you, ending with 'LESSON: ...'."]
    return "\n".join(p)


# ─────────────────────────── recap record ───────────────────────────


def build_push_recap_record(*, ep_id: str, run_id: str, outcome: str, outcome_class: str,
                            label: str, instruction: str, init: PushStateSnapshot,
                            final: Optional[PushStateSnapshot], round_meta: list[dict],
                            anchors: dict[str, str], text_lesson: str,
                            embedding: Sequence[float], key_round: Optional[int]) -> RecapRecord:
    """Same RecapRecord schema the shared buffer/retriever load. init_L_EE is
    the HONEST init EE grid (fixed standby → near-constant); push_situation is
    the key PushMemoryRetriever scores on."""
    dists_cm = [round(rm["cube_goal_dist_m"] * 100, 2) for rm in round_meta]
    r1 = round_meta[0] if round_meta else {}
    state_anchor: dict[str, Any] = {
        "init_L_EE": list(init.ee_int),
        "final_L_EE": list(final.ee_int) if final is not None else None,
        "round_count": len(round_meta),
        "active_arm": "left",
        "outcome_class": outcome_class,
        "push_situation": init.situation(),
        "init_cube_int": list(init.cube_int),
        "goal_int": list(init.goal_int),
        "init_cube_goal_dist_cm": round(init.cube_goal_dist_cm, 2),
        "final_cube_goal_dist_cm": dists_cm[-1] if dists_cm else None,
        "best_cube_goal_dist_cm": min(dists_cm) if dists_cm else None,
        "r1_eef_target_int": r1.get("eef_target_int"),
        "r1_eef_disp_m": (_r4(np.array(r1["eef_target_m"]) - np.array(init.ee_b))
                          if r1.get("eef_target_m") else None),
        "r1_cube_disp_cm": round(r1["cube_disp_m"] * 100, 2) if r1 else None,
    }
    return RecapRecord(
        ep_id=ep_id,
        run_id=run_id,
        outcome=outcome,
        is_success=outcome == "success",
        image_anchors=anchors,
        state_anchor=state_anchor,
        text_lesson=text_lesson,
        image_embedding=[float(v) for v in embedding],
        metadata={
            "instruction": instruction,
            "key_round_idx": key_round,
            "task": PUSH_TASK_TAG,
            "label": label,
            "recap_prompt_version": PUSH_RECAP_PROMPT_VERSION,
            "round_cube_goal_dist_cm": dists_cm,
        },
        left_reached=None,
        right_reached=None,
    )


def _default_embed(png: bytes) -> np.ndarray:
    from aiongenos.memory.image_embedding import embed_image_bytes
    return embed_image_bytes(png, device="cpu")


def _default_vlm(**kw) -> str:
    from aiongenos.vlm.client import call_vlm_sync
    return call_vlm_sync(**kw)


def request_push_recap_text(*, teacher_url: str, system_prompt: str, user_prompt: str,
                            images_png: list[bytes], max_words: int,
                            vlm_call: Callable[..., str] = _default_vlm) -> Optional[str]:
    """One teacher call, same sampling params as stage4_recap (T=0.4, 400 tok)."""
    from aiongenos.vlm.client import encode_image_bytes_base64
    from aiongenos.pipeline.stage4_recap import _trim_to_word_limit
    try:
        raw = vlm_call(url=teacher_url, system_prompt=system_prompt, user_prompt=user_prompt,
                       image_base64_list=[encode_image_bytes_base64(b) for b in images_png],
                       temperature=0.4, max_tokens=400, timeout=180.0)
    except Exception as e:
        logger.warning(f"push recap VLM call failed: {e}")
        return None
    text = (raw or "").strip()
    return _trim_to_word_limit(text, max_words) if text else None


def emit_push_recap(*, recap_buffer: RecapBuffer, ep_id: str, run_id: str, outcome: str,
                    label: str, instruction: str, init: PushStateSnapshot,
                    final: Optional[PushStateSnapshot], round_meta: list[dict],
                    ep_dump_dir: Optional[Path], rgb_start: Optional[bytes],
                    rgb_end: Optional[bytes], teacher_url: str, success_cm: float,
                    min_disp_cm: float, max_words: int = 100,
                    vlm_call: Callable[..., str] = _default_vlm,
                    embed_fn: Callable[[bytes], np.ndarray] = _default_embed) -> Optional[RecapRecord]:
    """Build + persist the push recap for one episode (always, any outcome)."""
    if not round_meta:
        logger.info(f"  push recap({ep_id}): no rounds (parse fail?), skip")
        return None
    dists = [rm["cube_goal_dist_m"] * 100 for rm in round_meta]
    disps = [rm["cube_disp_m"] * 100 for rm in round_meta]
    oc = classify_push_outcome(outcome, init.cube_goal_dist_cm, dists, disps, success_cm, min_disp_cm)
    key_round = select_push_key_round(oc, dists)

    anchors: dict[str, str] = {}
    if ep_dump_dir is not None:
        for name, fn in (("init_pre", "round_01_pre.png"), ("final_post", "episode_end.png")):
            if (Path(ep_dump_dir) / fn).exists():
                anchors[name] = str((Path(ep_dump_dir) / fn).resolve())
        kp = key_round_post_png(ep_dump_dir, key_round, len(round_meta))
        if kp is not None:
            anchors["key_round_post"] = str(kp.resolve())
    init_png = Path(anchors["init_pre"]).read_bytes() if "init_pre" in anchors else rgb_start
    final_png = Path(anchors["final_post"]).read_bytes() if "final_post" in anchors else rgb_end
    key_png = Path(anchors["key_round_post"]).read_bytes() if "key_round_post" in anchors else None
    if not init_png:
        logger.warning(f"  push recap({ep_id}): no init image, skip")
        return None

    images = [init_png] + ([final_png] if final_png else []) + ([key_png] if key_png else [])
    user_prompt = build_push_recap_user_prompt(
        instruction=instruction, outcome=outcome, outcome_class=oc, init=init,
        round_meta=round_meta, success_cm=success_cm, key_round=key_round,
        has_final_image=bool(final_png), has_key_image=bool(key_png), max_words=max_words)
    lesson = request_push_recap_text(
        teacher_url=teacher_url, system_prompt=build_push_recap_system_prompt(max_words),
        user_prompt=user_prompt, images_png=images, max_words=max_words, vlm_call=vlm_call)
    if not lesson:
        logger.warning(f"  push recap({ep_id}): VLM returned empty, skip")
        return None
    rec = build_push_recap_record(
        ep_id=ep_id, run_id=run_id, outcome=outcome, outcome_class=oc, label=label,
        instruction=instruction, init=init, final=final, round_meta=round_meta,
        anchors=anchors, text_lesson=lesson, embedding=embed_fn(init_png), key_round=key_round)
    path = recap_buffer.add(rec)
    logger.info(f"  push recap({ep_id}): saved → {path} ({len(lesson.split())} words, class={oc})")
    return rec


# ─────────────────────────── retrieval ───────────────────────────


def is_push_record(rec: RecapRecord) -> bool:
    sit = rec.state_anchor.get("push_situation")
    return isinstance(sit, (list, tuple)) and len(sit) == 4


def score_push_candidates(records: Sequence[RecapRecord], q_situation: Sequence[float],
                          q_embedding: np.ndarray, image_weight: float,
                          state_scale_cm: float) -> np.ndarray:
    """score = α·img_cos + (1−α)·exp(−‖Δsituation‖_cm / scale) — the
    RecapBuffer.retrieve formula with the state term on push_situation.
    Image-dim mismatch drops the image term (same fallback as the original)."""
    if not records:
        return np.zeros(0, dtype=np.float32)
    sit = np.asarray([r.state_anchor["push_situation"] for r in records], dtype=np.float32)
    q = np.asarray(q_situation, dtype=np.float32).reshape(1, 4)
    state_sims = np.exp(-(np.linalg.norm(sit - q, axis=1) * 100.0) / float(state_scale_cm))
    q_emb = np.asarray(q_embedding, dtype=np.float32)
    qn = np.linalg.norm(q_emb)
    if qn > 1e-8:
        q_emb = q_emb / qn
    dims = {len(r.image_embedding) for r in records}
    if dims == {q_emb.shape[0]}:
        img_sims = np.asarray([r.image_embedding for r in records], dtype=np.float32) @ q_emb
        w = image_weight
    else:
        logger.warning(f"push retrieve: image dim mismatch (buffer={dims}, query={q_emb.shape}), state only")
        img_sims, w = np.zeros_like(state_sims), 0.0
    return w * img_sims + (1.0 - w) * state_sims


def select_with_success_floor(records: Sequence[RecapRecord], scores: np.ndarray, fine_k: int,
                              success_floor_frac: float) -> list[int]:
    """Indices of the top-``fine_k`` with ≥ceil(floor·k) successes when the
    pool has them — same policy as RecapBuffer.retrieve (Phase 4 Q12)."""
    order = [int(j) for j in np.argsort(-scores, kind="stable")]
    min_success = int(math.ceil(success_floor_frac * fine_k))
    chosen = [j for j in order if records[j].is_success][:min_success]
    taken = set(chosen)
    for j in order:
        if len(chosen) >= fine_k:
            break
        if j not in taken:
            chosen.append(j)
            taken.add(j)
    return sorted(chosen, key=lambda j: -scores[j])


_PUSH_PREAMBLE_HEADER = (
    "PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see "
    "the scene at its start, where the cube and the goal were, your round-1 EEF "
    "target, what the cube did, the outcome, and a short lesson you wrote "
    "afterwards. Use these to choose a better push target for the current scene.\n"
)


def format_push_preamble_text(records: Sequence[RecapRecord], scores: Sequence[float]) -> str:
    if not records:
        return ""
    parts: list[str] = [_PUSH_PREAMBLE_HEADER]
    for i, (rec, s) in enumerate(zip(records, scores), start=1):
        sa = rec.state_anchor
        parts += ["", f"[PAST EPISODE {i}] (similarity={s:.3f})",
                  f"  Image {i}: the scene at the start of that episode"]
        if sa.get("init_cube_int") and sa.get("goal_int"):
            parts.append(f"  cube start = {_fmt_int2(sa['init_cube_int'])}   goal = {_fmt_int2(sa['goal_int'])}")
        if sa.get("init_cube_goal_dist_cm") is not None:
            parts.append(f"  start cube→goal = {float(sa['init_cube_goal_dist_cm']):.1f} cm")
        if sa.get("r1_eef_target_int"):
            parts.append(f"  round-1 EEF target = {_fmt_int3(sa['r1_eef_target_int'])}"
                         + (f"  → cube moved {float(sa['r1_cube_disp_cm']):.1f} cm"
                            if sa.get("r1_cube_disp_cm") is not None else ""))
        if sa.get("final_cube_goal_dist_cm") is not None:
            best = sa.get("best_cube_goal_dist_cm")
            parts.append(f"  final cube→goal = {float(sa['final_cube_goal_dist_cm']):.1f} cm"
                         + (f" (best {float(best):.1f} cm)" if best is not None else ""))
        parts.append(f"  outcome    = {rec.outcome}  (class: {sa.get('outcome_class', rec.outcome)})")
        if sa.get("round_count") is not None:
            parts.append(f"  rounds     = {sa['round_count']}")
        parts.append(f"  lesson     : {rec.text_lesson.strip()}")
    parts += ["", "─── END OF PAST EPISODES ───", "",
              "The LAST image below is the CURRENT scene you must act on. Use the past "
              "lessons above to choose your push target for this current scene."]
    return "\n".join(parts)


class PushMemoryRetriever:
    """Situation-aware retriever for push. Reuses the shared buffer (load
    only — never retrieve()), MemoryPreamble, the DINOv2 embedder and the
    past-image loader; scores on push_situation instead of init_L_EE."""

    def __init__(self, buffer: RecapBuffer, top_k: int = 3,
                 image_weight: float = DEFAULT_IMAGE_WEIGHT,
                 state_scale_cm: float = DEFAULT_STATE_SCALE_CM,
                 success_floor_frac: float = DEFAULT_SUCCESS_FLOOR_FRAC,
                 embed_fn: Callable[[bytes], np.ndarray] = _default_embed) -> None:
        self.buffer = buffer
        self.top_k = top_k
        self.image_weight = image_weight
        self.state_scale_cm = state_scale_cm
        self.success_floor_frac = success_floor_frac
        self._embed = embed_fn
        if not buffer._loaded:
            buffer.load()
        logger.info(f"PushMemoryRetriever ready: {len(buffer)} recaps, top_k={top_k}, "
                    f"image_weight={image_weight}, state_scale_cm={state_scale_cm}, "
                    f"success_floor={success_floor_frac:.2f}")

    def retrieve_for_episode(self, init_rgb_bytes: bytes, situation: Sequence[float],
                             exclude_run_ids: Optional[set[str]] = None):
        from aiongenos.memory.retriever import MemoryPreamble, _load_past_image_b64_list
        empty = MemoryPreamble("", [], tuple(), tuple())
        pool = [r for r in self.buffer.all()
                if is_push_record(r) and not (exclude_run_ids and r.run_id in exclude_run_ids)]
        n_foreign = sum(1 for r in self.buffer.all() if not is_push_record(r))
        if n_foreign:
            logger.warning(f"push retrieve: ignored {n_foreign} non-push records in {self.buffer.root}")
        if not pool:
            return empty
        scores = score_push_candidates(pool, situation, self._embed(init_rgb_bytes),
                                       self.image_weight, self.state_scale_cm)
        idx = select_with_success_floor(pool, scores, self.top_k, self.success_floor_frac)
        recs = [pool[j] for j in idx]
        b64s = _load_past_image_b64_list(recs)
        kept = [(r, float(scores[j]), b) for r, j, b in zip(recs, idx, b64s) if b is not None]
        if not kept:
            return empty
        return MemoryPreamble(
            prelude_text=format_push_preamble_text([k[0] for k in kept], [k[1] for k in kept]),
            past_image_base64_list=[k[2] for k in kept],
            retrieved_records=tuple(k[0] for k in kept),
            similarities=tuple(k[1] for k in kept),
        )


def assert_push_only_buffer(buffer: RecapBuffer) -> None:
    """Retrieval has no task filter in the shared buffer: refuse a root that
    already holds non-push (reach/L2) recaps rather than mixing them."""
    foreign = [r.ep_id for r in buffer.all() if not is_push_record(r)]
    if foreign:
        raise ValueError(f"recap root {buffer.root} holds {len(foreign)} non-push recaps "
                         f"(e.g. {foreign[:3]}); use a push-only root")
