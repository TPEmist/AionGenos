"""push_memory.py — cross-episode memory (recap → buffer → retrieval) for the
WP1-③a PUSH collect instrument (push_collect.py).

Observation rule (PI ruling 2026-10-05): the model sees IMAGE +
PROPRIOCEPTION only. Object positions are perception, never oracle-fed. GT
cube/goal values appear ONLY in offline records (replay metadata, round_meta,
recap ``metadata["offline_gt"]``) and the success predicate — never in a model
input (stage-1 prompt, recap prompt, retrieval key, preamble). The disclosed
scaffold ladder (``obs_rung``, set on the env as ``push_obs_rung``) is the one
pre-registered exception, applied identically to the recap and the preamble:
  rung 1: proprioception + images only (outcome shown as success/failure);
  rung 2: + scalar TCP→cube and cube→goal distances (the P1 L0a condition,
          prompts.py _S1_POS_HEAD: EE positions + scalar EE→target distance);
  rung 3: + cube/goal grid coordinates and cube displacement.

Why a separate module: the shared memory substrate (stage4_recap,
RecapBuffer, MemoryRetriever) is frozen with the P1 submission (a D11 night
batch imports it; equivalence is ledgered in
docs/p2_prereg/dual_collect_equivalence_ledger.md). Push re-uses its PIECES
unedited — RecapRecord + RecapBuffer.add/retrieve (storage + the L0a combined
score), call_vlm_sync, ImageEmbedder (DINOv2 key), MemoryPreamble +
_load_past_image_b64_list, _trim_to_word_limit — and adds only the push-
semantic parts: a rung-gated PUSH recap prompt, a rung-gated push preamble,
the per-episode dump dir, and replay augmentation (init_* + metadata) without
changing _write_episode's signature.

Retrieval key = observables only, exactly the L0a design: DINOv2 embedding of
the start image + init proprioception (init TCP grid as ``init_L_EE``). The
TCP starts at the fixed Pin-7a standby, so the state term is ≈ constant and the
image term carries the ranking — said plainly in the ledger.

Every deviation from the L0/L2 path is a ledger entry (dual_collect_equivalence_ledger.md,
"Push cross-episode memory", items 6–25).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import numpy as np

from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord
from aiongenos.vlm.scalar_guard import position_metric_to_int

logger = logging.getLogger(__name__)

PUSH_TASK_TAG = "WP1_3a_push"
PUSH_RECAP_PROMPT_VERSION = "push_recap_v2_obs_rung"
OBS_RUNGS = (1, 2, 3)
# Retrieval defaults = the L0a/D10 MemoryRetriever defaults (same formula,
# same buffer.retrieve). state_scale_cm stays 30: the key is the init TCP grid,
# which sits at the fixed standby every episode, so Δ≈0 and state_sim≈1 for
# all candidates at ANY scale — ranking is decided by the image term.
DEFAULT_IMAGE_WEIGHT = 0.4
DEFAULT_STATE_SCALE_CM = 30.0
DEFAULT_SUCCESS_FLOOR_FRAC = 2.0 / 3.0
# near-miss (offline class): best cube→goal within this multiple of the success radius
NEAR_MISS_RADIUS_MULT = 1.5


def _check_rung(obs_rung: int) -> int:
    r = int(obs_rung)
    if r not in OBS_RUNGS:
        raise ValueError(f"obs_rung must be one of {OBS_RUNGS}, got {obs_rung}")
    return r


def _r4(xs: Sequence[float]) -> list[float]:
    return [round(float(v), 4) for v in xs]


def _int_or_none(v: Any) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def grid_xyz(m: Sequence[float], bounds) -> list[int]:
    """Metric base-frame point → the SAME integer grid the teacher sees."""
    (x, y, z), _ = position_metric_to_int(float(m[0]), float(m[1]), float(m[2]),
                                          bounds.x_bounds, bounds.y_bounds, bounds.z_bounds)
    return [int(x), int(y), int(z)]


# ─────────────────────────── state snapshots ───────────────────────────


@dataclass(frozen=True)
class PushStateSnapshot:
    """Pre-action push state, base frame. tcp_* = PROPRIOCEPTION (model-
    visible; tcp_int is exactly the stage-1 LEFT_EE_POS). cube_*/goal_* = GT,
    OFFLINE ONLY (r-tracking, predicate, rung-gated disclosure)."""

    tcp_b: tuple[float, float, float]
    tcp_int: tuple[Optional[int], Optional[int], Optional[int]]
    cube_b: tuple[float, float, float]
    goal_b: tuple[float, float, float]
    cube_int: tuple[int, int]
    goal_int: tuple[int, int]

    @property
    def cube_goal_dist_cm(self) -> float:
        return float(np.linalg.norm(np.array(self.cube_b[:2]) - np.array(self.goal_b[:2]))) * 100.0

    def offline_situation(self) -> list[float]:
        """[cube_x, cube_y, goal_x, goal_y] (m) — OFFLINE analysis only."""
        return _r4([self.cube_b[0], self.cube_b[1], self.goal_b[0], self.goal_b[1]])


def snapshot_push_state(env, level_config, state: Optional[dict] = None) -> PushStateSnapshot:
    """Read the push state. Pass ``state`` if the caller already called
    env.get_state this step. TCP grid comes from get_state (what the teacher
    is shown); TCP metric from get_left_tcp_pos_b."""
    st = state if state is not None else env.get_state(level_config)
    b = level_config.workspace_bounds
    cube_b, goal_b = _r4(env.get_cube_pose_b()), _r4(env.get_goal_pose_b())
    cg, gg = grid_xyz(cube_b, b), grid_xyz(goal_b, b)
    return PushStateSnapshot(
        tcp_b=tuple(_r4(env.get_left_tcp_pos_b())),
        tcp_int=(_int_or_none(st.get("left_x")), _int_or_none(st.get("left_y")), _int_or_none(st.get("left_z"))),
        cube_b=tuple(cube_b), goal_b=tuple(goal_b),
        cube_int=(cg[0], cg[1]), goal_int=(gg[0], gg[1]),
    )


def snapshot_to_round_fields(snap: PushStateSnapshot) -> dict[str, Any]:
    """Per-round pre-action state for round_meta. EE start = TCP (the A-spec
    EEF reference point). cube/goal = GT, offline only."""
    return {
        "ee_start_b": list(snap.tcp_b),           # TCP, metric
        "ee_start_int": list(snap.tcp_int),       # TCP, grid (= stage-1 LEFT_EE_POS)
        "cube_b_pre": list(snap.cube_b),          # GT offline
        "goal_b_pre": list(snap.goal_b),          # GT offline
        "cube_goal_dist_m_pre": round(snap.cube_goal_dist_cm / 100.0, 4),   # GT offline
    }


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
    """_write_episode(replay, *write_args) + push init fields + metadata.
    init_left_ee_pose = the init TCP (EEF reference point = TCP)."""
    from aiongenos.orchestrator.collect_common import _write_episode
    update = {
        "init_cube_pose": {"yellow": list(init.cube_b)},
        "init_left_ee_pose": list(init.tcp_b),
        "env_seed": env_seed,
        "metadata": metadata,
    }
    _write_episode(_AugmentingReplay(replay, update), *write_args)


def replay_rounds_state(round_meta: list[dict]) -> list[dict[str, Any]]:
    """Compact per-round state for replay metadata (so (c, s) are computable
    from the replay alone — scripts/analysis/push_r_inputs.py)."""
    keys = ("round", "ee_start_b", "cube_b_pre", "goal_b_pre", "eef_target_int",
            "eef_target_m", "tcp_final_b", "ori_offset_deg", "cube_disp_m", "cube_goal_dist_m")
    return [{k: rm.get(k) for k in keys} for rm in round_meta]


# ─────────────────────────── outcome class (offline) ───────────────────────────


def classify_push_outcome(outcome: str, init_dist_cm: float, round_dists_cm: Sequence[float],
                          round_disps_cm: Sequence[float], success_cm: float,
                          min_disp_cm: float) -> str:
    """Push analogue of stage4_recap._classify_outcome, on GT cube→goal (cm).
    OFFLINE label; shown to the model only at obs_rung ≥ 2.
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


def predicate_outcome(outcome: str) -> str:
    """The rung-1 outcome the model may see: the success predicate's verdict."""
    return "success" if outcome == "success" else "failure"


def select_push_key_round(outcome_class: str, round_dists_cm: Sequence[float],
                          obs_rung: int = 1) -> Optional[int]:
    """1-based round whose END scene is the key image (None on success).
    rung 1: middle round (choosing by GT distance would leak GT through the
    image choice). rung ≥ 2: near_miss → closest, wrong_direction → furthest,
    else middle (stage4_recap's policy, on cube→goal)."""
    n = len(round_dists_cm)
    if n == 0 or outcome_class == "success":
        return None
    if obs_rung >= 2 and outcome_class == "near_miss":
        return int(np.argmin(round_dists_cm)) + 1
    if obs_rung >= 2 and outcome_class == "wrong_direction":
        return int(np.argmax(round_dists_cm)) + 1
    return n // 2 + 1 if n > 1 else 1


def key_round_post_png(ep_dump_dir: Optional[Path], key_round: Optional[int], n_rounds: int) -> Optional[Path]:
    """The scene AFTER round k = round_{k+1}_pre.png (no sim step between).
    None for the last round — its post scene IS episode_end (final image)."""
    if ep_dump_dir is None or key_round is None or key_round >= n_rounds:
        return None
    cand = Path(ep_dump_dir) / f"round_{key_round + 1:02d}_pre.png"
    return cand if cand.exists() else None


# ─────────────────────────── rung-gated disclosure ───────────────────────────


def disclosed_values(obs_rung: int, init: PushStateSnapshot, round_meta: list[dict]) -> dict[str, Any]:
    """The GT-derived values the model MAY see at this rung — the single
    source for both the recap prompt and the stored preamble fields. Empty at
    rung 1."""
    rung = _check_rung(obs_rung)
    out: dict[str, Any] = {}
    if rung >= 2:
        out["init_cube_goal_dist_cm"] = round(init.cube_goal_dist_cm, 1)
        out["round_cube_goal_dist_cm"] = [round(rm["cube_goal_dist_m"] * 100, 1) for rm in round_meta]
        out["round_tcp_to_cube_min_cm"] = [
            (rm.get("contact") or {}).get("tcp_to_cube_min_cm") for rm in round_meta]
    if rung >= 3:
        out["init_cube_int"] = list(init.cube_int)
        out["goal_int"] = list(init.goal_int)
        out["round_cube_disp_cm"] = [round(rm["cube_disp_m"] * 100, 1) for rm in round_meta]
    return out


# ─────────────────────────── recap prompt (MODEL INPUT) ───────────────────────────


def build_push_recap_system_prompt(max_words: int, obs_rung: int = 1) -> str:
    rung = _check_rung(obs_rung)
    seen = ("your own per-round fingertip (TCP) targets and where the TCP actually went"
            + (", plus the disclosed distances listed below" if rung >= 2 else ""))
    where = ("The cube and the green zone positions are ONLY what you see in the images.\n"
             if rung < 3 else "")
    return (
        "You are a robot reviewing your own past PUSH episode. Your left "
        "end-effector is a rigid pushing tool (gripper held closed, it cannot "
        "grasp); its reference point is the fingertip (TCP). The task was to "
        "push the yellow cube onto the green goal zone. You will see the scene "
        "at the start, at the end, and optionally one key mid-episode scene, "
        f"together with {seen}.\n"
        f"{where}"
        "\n"
        "Your goal is to write a short lesson that a future-you, facing a similar "
        "scene, can reuse when choosing the FIRST target.\n"
        "\n"
        "STRICT RULES:\n"
        f"  - Output {max_words} words MAX, plain prose, single paragraph.\n"
        "  - Do NOT output a LEFT_TARGET_POS / LEFT_TARGET_ORI line or a plan for\n"
        "    this episode. This is a reflection, not an action.\n"
        "  - Say where your round-1 target was relative to the cube and the green\n"
        "    zone as you see them in the images, and what the cube did.\n"
        "  - Name ONE concrete adjustment, in your own words, that would have moved\n"
        "    the cube toward the zone — or, on success, what made it work.\n"
        "  - You MAY cite the numbers given below; they are physical facts.\n"
        "  - Finish with one sentence that starts with 'LESSON:'.\n"
    )


def _fmt3(v: Sequence[Any]) -> str:
    return f"(X={v[0]}, Y={v[1]}, Z={v[2]})"


def _fmt2(v: Sequence[Any]) -> str:
    return f"(X={v[0]}, Y={v[1]})"


def _fmt_ori(ori: Optional[Sequence[Any]]) -> str:
    return f"(P={ori[0]}, Y={ori[1]}, R={ori[2]})" if ori is not None else "rest"


def build_push_recap_user_prompt(*, instruction: str, outcome: str, outcome_class: str,
                                 init: PushStateSnapshot, round_meta: list[dict], bounds,
                                 obs_rung: int, success_cm: float, key_round: Optional[int],
                                 has_final_image: bool, has_key_image: bool,
                                 max_words: int) -> str:
    """Rung-gated. rung 1 contains ONLY: task, predicate outcome, round count,
    per-round TCP target vs TCP reached + ORI (proprioception), images."""
    rung = _check_rung(obs_rung)
    disc = disclosed_values(rung, init, round_meta)
    n = len(round_meta)
    p: list[str] = [f"TASK: {instruction}"]
    if rung >= 2:
        p.append(f"OUTCOME: {outcome}  (class: {outcome_class})")
        p.append(f"SUCCESS_RULE: cube centre within {success_cm:.1f} cm of the goal centre")
    else:
        p.append(f"OUTCOME: {predicate_outcome(outcome)}")
    p += [f"ROUND_COUNT: {n}", "",
          "INITIAL STATE (Image 1; proprioception, base-frame integer grid, same grid as your actions):",
          f"  LEFT_TCP_POS = {_fmt3(init.tcp_int)}"]
    if rung >= 3:
        p += [f"  CUBE_POS     = {_fmt2(disc['init_cube_int'])}   (disclosed)",
              f"  GOAL_POS     = {_fmt2(disc['goal_int'])}   (disclosed)"]
    if rung >= 2:
        p.append(f"  CUBE_TO_GOAL = {disc['init_cube_goal_dist_cm']:.1f} cm   (disclosed)")
    if round_meta:
        p += ["", "PER ROUND — YOUR TCP TARGET vs WHERE THE TCP WENT (grid):"]
        for i, rm in enumerate(round_meta):
            reached = grid_xyz(rm["tcp_final_b"], bounds) if rm.get("tcp_final_b") else None
            line = (f"  R{rm['round']}: target {_fmt3(rm['eef_target_int'])} ORI {_fmt_ori(rm.get('ori_offset_deg'))}"
                    f" → TCP reached {_fmt3(reached) if reached else '?'}")
            if rung >= 2:
                tc = disc["round_tcp_to_cube_min_cm"][i]
                line += (f"; closest TCP→cube {tc:.1f} cm" if tc is not None else "")
                line += f"; cube→goal after {disc['round_cube_goal_dist_cm'][i]:.1f} cm"
            if rung >= 3:
                line += f"; cube moved {disc['round_cube_disp_cm'][i]:.1f} cm"
            p.append(line)
    if has_final_image:
        p += ["", "FINAL STATE: Image 2"]
    if has_key_image and key_round is not None:
        p += [f"KEY SCENE: Image {3 if has_final_image else 2}, right after round {key_round}"]
    p += ["", f"Now write your ≤{max_words}-word lesson for future-you, ending with 'LESSON: ...'."]
    return "\n".join(p)


# ─────────────────────────── recap record ───────────────────────────


def build_push_recap_record(*, ep_id: str, run_id: str, outcome: str, outcome_class_gt: str,
                            obs_rung: int, label: str, instruction: str, init: PushStateSnapshot,
                            final: Optional[PushStateSnapshot], round_meta: list[dict], bounds,
                            anchors: dict[str, str], text_lesson: str,
                            embedding: Sequence[float], key_round: Optional[int]) -> RecapRecord:
    """Same RecapRecord schema the shared buffer/retriever load.
    state_anchor = model-visible fields only (it feeds the preamble):
    init_L_EE = the init TCP grid (retrieval state key, L0a design).
    metadata["offline_gt"] = GT, NEVER read by the retriever or preamble."""
    rung = _check_rung(obs_rung)
    dists_cm = [round(rm["cube_goal_dist_m"] * 100, 2) for rm in round_meta]
    r1 = round_meta[0] if round_meta else {}
    state_anchor: dict[str, Any] = {
        "init_L_EE": list(init.tcp_int),
        "final_L_EE": list(final.tcp_int) if final is not None else None,
        "ee_reference": "tcp",
        "round_count": len(round_meta),
        "active_arm": "left",
        "obs_rung": rung,
        "outcome_class": outcome_class_gt if rung >= 2 else predicate_outcome(outcome),
        "r1_eef_target_int": r1.get("eef_target_int"),
        "r1_ori_offset_deg": r1.get("ori_offset_deg"),
        "r1_tcp_reached_int": grid_xyz(r1["tcp_final_b"], bounds) if r1.get("tcp_final_b") else None,
        "disclosed": disclosed_values(rung, init, round_meta),
    }
    offline_gt = {
        "NOTE": "GT — offline analysis only; never a model input, never read by retrieval",
        "init_cube_b": list(init.cube_b),
        "goal_b": list(init.goal_b),
        "situation": init.offline_situation(),
        "init_cube_goal_dist_cm": round(init.cube_goal_dist_cm, 2),
        "round_cube_goal_dist_cm": dists_cm,
        "round_cube_disp_cm": [round(rm["cube_disp_m"] * 100, 2) for rm in round_meta],
        "final_cube_goal_dist_cm": dists_cm[-1] if dists_cm else None,
        "best_cube_goal_dist_cm": min(dists_cm) if dists_cm else None,
        "outcome_class": outcome_class_gt,
        "r1_contact": r1.get("contact"),
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
            "obs_rung": rung,
            "recap_prompt_version": PUSH_RECAP_PROMPT_VERSION,
            "offline_gt": offline_gt,
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
                    obs_rung: int, label: str, instruction: str, init: PushStateSnapshot,
                    final: Optional[PushStateSnapshot], round_meta: list[dict], bounds,
                    ep_dump_dir: Optional[Path], rgb_start: Optional[bytes],
                    rgb_end: Optional[bytes], teacher_url: str, success_cm: float,
                    min_disp_cm: float, max_words: int = 100,
                    vlm_call: Callable[..., str] = _default_vlm,
                    embed_fn: Callable[[bytes], np.ndarray] = _default_embed) -> Optional[RecapRecord]:
    """Build + persist the push recap for one episode (always, any outcome)."""
    rung = _check_rung(obs_rung)
    if not round_meta:
        logger.info(f"  push recap({ep_id}): no rounds (parse fail?), skip")
        return None
    dists = [rm["cube_goal_dist_m"] * 100 for rm in round_meta]
    disps = [rm["cube_disp_m"] * 100 for rm in round_meta]
    oc_gt = classify_push_outcome(outcome, init.cube_goal_dist_cm, dists, disps, success_cm, min_disp_cm)
    key_round = select_push_key_round(oc_gt, dists, rung)

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
        instruction=instruction, outcome=outcome, outcome_class=oc_gt, init=init,
        round_meta=round_meta, bounds=bounds, obs_rung=rung, success_cm=success_cm,
        key_round=key_round, has_final_image=bool(final_png), has_key_image=bool(key_png),
        max_words=max_words)
    lesson = request_push_recap_text(
        teacher_url=teacher_url, system_prompt=build_push_recap_system_prompt(max_words, rung),
        user_prompt=user_prompt, images_png=images, max_words=max_words, vlm_call=vlm_call)
    if not lesson:
        logger.warning(f"  push recap({ep_id}): VLM returned empty, skip")
        return None
    rec = build_push_recap_record(
        ep_id=ep_id, run_id=run_id, outcome=outcome, outcome_class_gt=oc_gt, obs_rung=rung,
        label=label, instruction=instruction, init=init, final=final, round_meta=round_meta,
        bounds=bounds, anchors=anchors, text_lesson=lesson, embedding=embed_fn(init_png),
        key_round=key_round)
    path = recap_buffer.add(rec)
    logger.info(f"  push recap({ep_id}): saved → {path} ({len(lesson.split())} words, "
                f"rung={rung}, class_gt={oc_gt})")
    return rec


# ─────────────────────────── retrieval (MODEL INPUT) ───────────────────────────


def is_push_record(rec: RecapRecord) -> bool:
    return (rec.metadata or {}).get("task") == PUSH_TASK_TAG


_PUSH_PREAMBLE_HEADER = (
    "PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see "
    "the scene at its start, your round-1 fingertip (TCP) target, the outcome, and "
    "a short lesson you wrote afterwards. Use these to choose a better target for "
    "the current scene.\n"
)


def format_push_preamble_text(records: Sequence[RecapRecord], scores: Sequence[float],
                              obs_rung: int = 1) -> str:
    """Rung-gated: a record's ``disclosed`` values are printed only up to the
    CURRENT run's rung (a rung-3 record never leaks coordinates into rung 1)."""
    rung = _check_rung(obs_rung)
    if not records:
        return ""
    parts: list[str] = [_PUSH_PREAMBLE_HEADER]
    for i, (rec, s) in enumerate(zip(records, scores), start=1):
        sa = rec.state_anchor
        disc = sa.get("disclosed") or {}
        parts += ["", f"[PAST EPISODE {i}] (similarity={s:.3f})",
                  f"  Image {i}: the scene at the start of that episode"]
        if sa.get("init_L_EE"):
            parts.append(f"  start TCP  = {_fmt3(sa['init_L_EE'])}")
        if sa.get("r1_eef_target_int"):
            reached = sa.get("r1_tcp_reached_int")
            parts.append(f"  round-1 target = {_fmt3(sa['r1_eef_target_int'])} ORI {_fmt_ori(sa.get('r1_ori_offset_deg'))}"
                         + (f" → TCP reached {_fmt3(reached)}" if reached else ""))
        if rung >= 3 and disc.get("init_cube_int") and disc.get("goal_int"):
            parts.append(f"  cube start = {_fmt2(disc['init_cube_int'])}   goal = {_fmt2(disc['goal_int'])}   (disclosed)")
        if rung >= 2 and disc.get("init_cube_goal_dist_cm") is not None:
            rd = disc.get("round_cube_goal_dist_cm") or []
            parts.append(f"  cube→goal  = {disc['init_cube_goal_dist_cm']:.1f} cm at start"
                         + (f", {rd[-1]:.1f} cm at end" if rd else "") + "   (disclosed)")
        if rung >= 2:
            parts.append(f"  outcome    = {rec.outcome}  (class: {sa.get('outcome_class', rec.outcome)})")
        else:
            parts.append(f"  outcome    = {predicate_outcome(rec.outcome)}")
        if sa.get("round_count") is not None:
            parts.append(f"  rounds     = {sa['round_count']}")
        parts.append(f"  lesson     : {rec.text_lesson.strip()}")
    parts += ["", "─── END OF PAST EPISODES ───", "",
              "The LAST image below is the CURRENT scene you must act on. Use the past "
              "lessons above to choose your target for this current scene."]
    return "\n".join(parts)


class PushMemoryRetriever:
    """Push retriever = the SHARED RecapBuffer.retrieve (L0a combined score:
    α·DINOv2 cos + (1−α)·exp(−‖Δ init_L_EE‖/scale), success floor) with the
    init TCP grid as init_L_EE, plus the push-worded, rung-gated preamble."""

    def __init__(self, buffer: RecapBuffer, top_k: int = 3,
                 image_weight: float = DEFAULT_IMAGE_WEIGHT,
                 state_scale_cm: float = DEFAULT_STATE_SCALE_CM,
                 success_floor_frac: float = DEFAULT_SUCCESS_FLOOR_FRAC,
                 obs_rung: int = 1,
                 embed_fn: Callable[[bytes], np.ndarray] = _default_embed) -> None:
        self.buffer = buffer
        self.top_k = top_k
        self.image_weight = image_weight
        self.state_scale_cm = state_scale_cm
        self.success_floor_frac = success_floor_frac
        self.obs_rung = _check_rung(obs_rung)
        self._embed = embed_fn
        if not buffer._loaded:
            buffer.load()
        logger.info(f"PushMemoryRetriever ready: {len(buffer)} recaps, top_k={top_k}, "
                    f"image_weight={image_weight}, state_scale_cm={state_scale_cm}, "
                    f"success_floor={success_floor_frac:.2f}, obs_rung={self.obs_rung}")

    def retrieve_for_episode(self, init_rgb_bytes: bytes, init_tcp_int: Sequence[int],
                             exclude_run_ids: Optional[set[str]] = None):
        from aiongenos.memory.retriever import MemoryPreamble, _load_past_image_b64_list
        empty = MemoryPreamble("", [], tuple(), tuple())
        if len(self.buffer) == 0:
            return empty
        hits = self.buffer.retrieve(
            query_init_L_EE=tuple(int(v) for v in init_tcp_int),
            query_image_embedding=self._embed(init_rgb_bytes),
            fine_k=self.top_k, exclude_run_ids=exclude_run_ids,
            image_weight=self.image_weight, state_scale_cm=self.state_scale_cm,
            success_floor_frac=self.success_floor_frac,
        )
        foreign = [h for h in hits if not is_push_record(h[0])]
        if foreign:   # the run script refuses mixed roots; defensive only
            logger.warning(f"push retrieve: dropped {len(foreign)} non-push hits from {self.buffer.root}")
        hits = [h for h in hits if is_push_record(h[0])]
        b64s = _load_past_image_b64_list([h[0] for h in hits])
        kept = [(r, float(s), b) for (r, s), b in zip(hits, b64s) if b is not None]
        if not kept:
            return empty
        return MemoryPreamble(
            prelude_text=format_push_preamble_text([k[0] for k in kept], [k[1] for k in kept],
                                                   self.obs_rung),
            past_image_base64_list=[k[2] for k in kept],
            retrieved_records=tuple(k[0] for k in kept),
            similarities=tuple(k[1] for k in kept),
        )


def assert_push_only_buffer(buffer: RecapBuffer, obs_rung: int) -> None:
    """Retrieval has no task filter in the shared buffer: refuse a root that
    holds non-push (reach/L2) recaps or push recaps from another obs_rung (their
    lessons were written under a different disclosure level)."""
    rung = _check_rung(obs_rung)
    foreign = [r.ep_id for r in buffer.all() if not is_push_record(r)]
    if foreign:
        raise ValueError(f"recap root {buffer.root} holds {len(foreign)} non-push recaps "
                         f"(e.g. {foreign[:3]}); use a push-only root")
    other = [r.ep_id for r in buffer.all() if (r.metadata or {}).get("obs_rung") != rung]
    if other:
        raise ValueError(f"recap root {buffer.root} holds {len(other)} recaps from another "
                         f"obs_rung (e.g. {other[:3]}); use one root per rung")
