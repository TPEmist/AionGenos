"""Same-hardware inference-cost re-measure (D11 A15 add-on, descriptive).

Spec: docs/handoff/2026-10-05_isaac-cost-remeasure.md and
docs/d11_preregistration.md "A15 add-on (non-inferential)".

Standalone measurement harness. It does NOT edit or re-implement the frozen
pipeline: it imports the live code path and only swaps the HTTP transport.

How prompts are reconstructed
-----------------------------
Replays store no prompt text, so every prompt is REBUILT by running the frozen
pipeline functions on state recovered from disk:

* ``run_stage1`` (aiongenos/pipeline/stage1_reasoning.py) is called UNMODIFIED
  with an ``EpisodeConversation``; it builds the user prompt
  (``get_stage1_prompt`` + critic injection), appends the turn (system fold,
  R1 memory preamble + past images, image stripping, sliding window) and runs
  the parse/retry loop. Only its module-level ``call_vlm_history_sync`` is
  swapped for a recorder that builds the payload with the client's own
  ``EpisodeConversation.to_payload`` and POSTs it raw, so the server ``usage``
  / ``timings`` blocks are kept (the stock client discards them).
* the post-episode recap prompt is built with stage4_recap's own helpers
  (``rounds_from_meta_and_interactions``, ``_select_key_round``,
  ``_classify_outcome``, ``_request_vlm_recap``); its ``call_vlm_sync`` is
  swapped the same way (payload via ``build_chat_request``). The recap is NOT
  persisted (buffer.add is blocked; buffer tree hash asserted pre/post).
* retrieval goes through ``MemoryRetriever.retrieve_for_episode`` unmodified;
  the embedder's ``embed`` and the buffer's ``retrieve`` are wrapped on the
  instance only to time them separately.

State per (episode, round) comes from data/collect_dumps/<run>/<ep>/meta.json:
EE ints = ``actual_left_start`` / ``actual_right_start`` (collect.py sets
these from the same get_state dict the prompt used); critic feedback =
stored verbatim; distance strings = the "started at" values of the NEXT
round's critic feedback (same get_current_distances call, exact), else the
previous round's final distance, else the replay trajectory's first sample
(approximate; per-step ``dist_source`` is recorded). Images are the dumped
round_NN_pre.png / episode_start.png bytes (exactly what get_rgb returned).

Known open-loop differences vs. the live pipeline (recorded in the output):
assistant turns in the conversation history are this harness's own fresh
responses (replays stored only the THOUGHT slot, and nothing for the D11
students), while the critic feedback text still describes the replay's
original predictions.

Step selection (deterministic): episodes in run order (episode_start.png
mtime, verified == log order), rounds 1..min(n_rounds, --max_rounds_per_ep),
until --n_steps steps are taken. Per-episode costs (retrieval, recap) are
amortized per step by the source run's mean rounds/episode over ALL its
episodes.

Usage: see ``--help``; operator sequence in the module report.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import logging
import re
import socket
import statistics
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import httpx

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import aiongenos.pipeline.stage1_reasoning as s1mod  # noqa: E402
import aiongenos.pipeline.stage4_recap as s4mod  # noqa: E402
from aiongenos.config import LevelConfig  # noqa: E402
from aiongenos.curriculum.manager import LEVEL_CONFIGS  # noqa: E402
from aiongenos.orchestrator.collect_common import _active_arm_for_level  # noqa: E402
from aiongenos.vlm import client as vlm_client  # noqa: E402
from aiongenos.vlm.client import EpisodeConversation, build_chat_request  # noqa: E402
from aiongenos.vlm.prompts import get_stage1_system_prompt  # noqa: E402

logger = logging.getLogger("cost_remeasure")

LEVEL = -2  # D10 / D11 L0a-left (run_a15_night.sh / D11 Step 8 --level -2)
DEFAULT_BUFFER = "workspace/recaps_d10_frozen_c_retrieval"
A15_DRIVER = REPO / "scripts/training/run_a15_night.sh"
RUN_COLLECT = REPO / "scripts/run_collect.py"


@dataclass(frozen=True)
class Protocol:
    name: str
    source_run: str
    server: str  # "teacher" | "student"
    variant: Optional[str]  # eval_template_variant (None = legacy teacher)
    memory: bool
    recap: bool
    exclude_source_run: bool  # exclude the source run's own recaps


PROTOCOLS: dict[str, Protocol] = {
    # D10-ext teacher (aa08bb4c): legacy THOUGHT template, memory ON, recap ON.
    # The frozen buffer contains aa08bb4c's own 100 recaps; excluding that run
    # leaves the 447-record buffer the D10 run started from (log line 201).
    "teacher": Protocol("teacher", "aa08bb4c", "teacher", None, True, True, True),
    # D11 A_ctrl_rat (56ee684b): variant rationale, no memory, no recap.
    "student_bare": Protocol("student_bare", "56ee684b", "student", "rationale", False, False, False),
    # D11 C_retrieval (09817322): A_ctrl_rat adapter, frozen readonly buffer.
    "student_retrieval": Protocol(
        "student_retrieval", "09817322", "student", "rationale_with_retrieval", True, False, False,
    ),
}


# ───────────────────────────── recording transport ─────────────────────────────


@dataclass
class Recorder:
    out_fh: Any
    dry_run: bool
    max_calls: int = 0  # 0 = unlimited; hard safety cap on real HTTP LM calls
    n_http: int = 0
    ctx: dict = field(default_factory=dict)
    calls: list = field(default_factory=list)

    def emit(self, rec: dict) -> None:
        self.out_fh.write(json.dumps(rec) + "\n")
        self.out_fh.flush()

    def call(self, url: str, payload: dict, timeout: float, kind: str) -> str:
        """POST ``payload`` raw (mirrors client.call_vlm[_history] retry policy)."""
        text_parts, n_img = _redact(payload)
        body = json.dumps(payload).encode()
        base = {
            "record_type": "call", **self.ctx, "call_kind": kind, "url": url,
            "n_images": n_img, "prompt_text_chars": sum(len(t) for t in text_parts),
            "payload_bytes": len(body), "payload_sha256": hashlib.sha256(body).hexdigest(),
            "temperature": payload.get("temperature"), "max_tokens": payload.get("max_tokens"),
            "prompt_text": "\n".join(text_parts), "dry_run": self.dry_run,
        }
        if self.dry_run:
            content = _synthetic_response(self.ctx, kind)
            rec = {**base, "http_attempt": 0, "status": "dry_run", "wall_s": 0.0,
                   "usage": None, "timings": None, "full_response": content}
            self.calls.append(rec)
            self.emit(rec)
            return content
        endpoint = f"{url.rstrip('/')}/v1/chat/completions"
        last_err: Optional[Exception] = None
        for attempt in range(vlm_client.MAX_RETRIES + 1):
            if self.max_calls and self.n_http >= self.max_calls:
                raise CallCapReached(f"--max_calls {self.max_calls} reached")
            self.n_http += 1
            t0 = time.perf_counter()
            try:
                with httpx.Client(timeout=timeout) as cli:
                    resp = cli.post(endpoint, json=payload)
                wall = time.perf_counter() - t0
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
                last_err = e
                rec = {**base, "http_attempt": attempt, "status": "http_error",
                       "wall_s": time.perf_counter() - t0, "error": repr(e)}
                self.calls.append(rec)
                self.emit(rec)
                continue
            choices = data.get("choices") or []
            content = (choices[0].get("message", {}).get("content", "") if choices else "") or ""
            rec = {**base, "http_attempt": attempt, "status": "ok" if content else "empty",
                   "wall_s": wall, "usage": data.get("usage"), "timings": data.get("timings"),
                   "finish_reason": choices[0].get("finish_reason") if choices else None,
                   "full_response": content}
            self.calls.append(rec)
            self.emit(rec)
            if not choices:
                raise ValueError("No choices in VLM response")
            if not content:
                raise ValueError("Empty content in VLM response")
            return content
        raise last_err  # type: ignore[misc]


class CallCapReached(RuntimeError):
    """Raised when --max_calls is exhausted (BaseException-safe stop of the run)."""


def _redact(payload: dict) -> tuple[list[str], int]:
    texts, n_img = [], 0
    for msg in payload.get("messages", []):
        content = msg.get("content")
        if isinstance(content, str):
            texts.append(f"[{msg['role']}] {content}")
            continue
        for part in content or []:
            if part.get("type") == "text":
                texts.append(f"[{msg['role']}] {part['text']}")
            else:
                n_img += 1
                texts.append(f"[{msg['role']}] <image>")
    return texts, n_img


def _synthetic_response(ctx: dict, kind: str) -> str:
    """Dry-run only: a parseable placeholder so the conversation can advance."""
    if kind == "recap":
        return "dry-run recap lesson."
    lx, ly, lz = ctx.get("stored_left") or (0, 0, 0)
    rx, ry, rz = ctx.get("stored_right") or (0, 0, 0)
    head = "THOUGHT" if ctx.get("variant") is None else "INTRINSIC_RATIONALE"
    return (f"{head}: dry-run placeholder.\nLEFT_TARGET_POS:  X={lx} Y={ly} Z={lz}\n"
            f"RIGHT_TARGET_POS: X={rx} Y={ry} Z={rz}\nSTOP: false")


@contextmanager
def patched_transport(rec: Recorder):
    """Swap ONLY the HTTP functions the frozen modules imported by name."""
    orig_hist, orig_sync = s1mod.call_vlm_history_sync, s4mod.call_vlm_sync

    def hist(url, conversation, temperature=0.7, max_tokens=1024, timeout=300.0):
        payload = conversation.to_payload(temperature=temperature, max_tokens=max_tokens)
        return rec.call(url, payload, timeout, "stage1")

    def sync(url, system_prompt, user_prompt, image_base64=None, image_base64_list=None,
             temperature=0.7, max_tokens=1024, timeout=300.0):
        payload = build_chat_request(system_prompt=system_prompt, user_prompt=user_prompt,
                                     image_base64=image_base64, image_base64_list=image_base64_list,
                                     temperature=temperature, max_tokens=max_tokens)
        return rec.call(url, payload, timeout, "recap")

    s1mod.call_vlm_history_sync, s4mod.call_vlm_sync = hist, sync
    try:
        yield
    finally:
        s1mod.call_vlm_history_sync, s4mod.call_vlm_sync = orig_hist, orig_sync


# ───────────────────────────── replay reconstruction ─────────────────────────────

_STARTED_RE = {
    arm: re.compile(rf"{arm} ARM:.*?started at ([0-9.]+) cm", re.S) for arm in ("LEFT", "RIGHT")
}


@dataclass(frozen=True)
class Episode:
    run_id: str
    ep_idx: int
    ep_id: str
    dump_dir: Path
    meta: dict
    replay: dict


def load_episodes(run_id: str) -> list[Episode]:
    root = REPO / "data/collect_dumps" / run_id
    dirs = sorted((d for d in root.iterdir() if (d / "episode_start.png").exists()),
                  key=lambda d: (d / "episode_start.png").stat().st_mtime)
    eps = []
    for i, d in enumerate(dirs):
        rp = [p for p in (REPO / "data/replays" / run_id / sub / f"{d.name}.json"
                          for sub in ("success", "failure")) if p.exists()]
        if len(rp) != 1:
            raise FileNotFoundError(f"replay json for {run_id}/{d.name}: found {rp}")
        eps.append(Episode(run_id, i, d.name, d, json.loads((d / "meta.json").read_text()),
                           json.loads(rp[0].read_text())))
    return eps


def _dist_cm(meta_rounds: list[dict], k: int, replay: dict) -> tuple[str, str, str]:
    """Distance strings for round k (0-based) as get_state formatted them."""
    if k + 1 < len(meta_rounds) and meta_rounds[k + 1].get("critic_feedback"):
        fb = meta_rounds[k + 1]["critic_feedback"]
        ml, mr = _STARTED_RE["LEFT"].search(fb), _STARTED_RE["RIGHT"].search(fb)
        if ml and mr:
            return ml.group(1), mr.group(1), "next_critic_exact"
    if k > 0:
        prev = meta_rounds[k - 1]
        if prev.get("final_dist_l_cm") is not None and prev.get("final_dist_r_cm") is not None:
            return f"{prev['final_dist_l_cm']:.1f}", f"{prev['final_dist_r_cm']:.1f}", "prev_final"
    d0 = (replay.get("trajectory") or [{}])[0].get("distances") or {}
    return f"{d0.get('dist_red', 0.0) * 100:.1f}", f"{d0.get('dist_blue', 0.0) * 100:.1f}", "traj0_approx"


def build_state(ep: Episode, k: int, level_config: LevelConfig) -> tuple[dict, str]:
    """Rebuild the get_state() dict collect.py fed the prompt at round k (0-based).

    Mirrors IsaacLabEnvInterface.get_state for POSITION_ONLY. The fixed colour
    strings are get_state literals; drift is caught by the instruction gate
    (reconstructed instruction must equal the replay's stored instruction).
    """
    r = ep.meta["rounds"][k]
    lx, ly, lz = r["actual_left_start"]
    rx, ry, rz = r["actual_right_start"]
    dl, dr, src = _dist_cm(ep.meta["rounds"], k, ep.replay)
    state: dict = {
        "left_x": lx, "left_y": ly, "left_z": lz, "right_x": rx, "right_y": ry, "right_z": rz,
        "left_target_color": "red", "right_target_color": "blue",
        "left_trace_shape": "circle", "right_trace_shape": "square",
        "object_color": "yellow",
        "target_color": "red" if level_config.name.startswith("L0a_") else "green",
        "dist_red_cm": dl, "dist_blue_cm": dr,
    }
    try:  # collect.py run_collect_loop, verbatim semantics
        state["instruction"] = level_config.task_instruction_template.format(**state)
    except Exception:
        state["instruction"] = level_config.task_instruction_template
    if state["instruction"] != ep.replay.get("instruction"):
        raise AssertionError(f"instruction gate failed for {ep.ep_id}: "
                             f"{state['instruction']!r} != {ep.replay.get('instruction')!r}")
    return state, src


def select_steps(eps: list[Episode], n_steps: int, max_rounds: int) -> list[tuple[Episode, int]]:
    plan: list[tuple[Episode, int]] = []
    for ep in eps:
        take = min(len(ep.meta["rounds"]), max_rounds, n_steps - sum(n for _, n in plan))
        if take <= 0:
            break
        plan.append((ep, take))
    return plan


# ───────────────────────────── retrieval / recap ─────────────────────────────


def read_retrieval_defaults() -> dict:
    """Read the --memory_* defaults live from scripts/run_collect.py (no copies)."""
    tree = ast.parse(RUN_COLLECT.read_text())
    out = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument"
                and node.args and isinstance(node.args[0], ast.Constant)):
            flag = node.args[0].value
            for kw in node.keywords:
                if kw.arg == "default" and flag.startswith("--memory_"):
                    expr = ast.Expression(kw.value)
                    out[flag[2:]] = eval(compile(expr, "<run_collect default>", "eval"), {"__builtins__": {}})
                if kw.arg == "action" and flag.startswith("--memory_") and kw.value.value == "store_true":
                    out.setdefault(flag[2:], False)
    return out


def make_retriever(buffer_root: Path, defaults: dict):
    from aiongenos.memory.image_embedding import ImageEmbedder
    from aiongenos.memory.recap_buffer import RecapBuffer
    from aiongenos.memory.retriever import MemoryRetriever

    buf = RecapBuffer(root=buffer_root)
    buf.load()

    def _blocked_add(_rec):  # readonly: the harness must never persist recaps
        raise RuntimeError("cost_remeasure: RecapBuffer.add blocked (readonly)")

    buf.add = _blocked_add
    retr = MemoryRetriever(
        buffer=buf, top_k=defaults["memory_top_k"], success_only=defaults["memory_success_only"],
        embedder_device="cpu", image_weight=defaults["memory_image_weight"],
        state_scale_cm=defaults["memory_state_scale_cm"],
        success_floor_frac=defaults["memory_success_floor"],
        success_only_flag_path=defaults["memory_mode_flag_path"],
        success_label_arm=defaults["memory_success_label_arm"],
    )
    t0 = time.perf_counter()
    emb = ImageEmbedder.get(device="cpu")
    load_s = time.perf_counter() - t0
    timing = {"embed_ms": 0.0, "query_ms": 0.0}
    orig_embed, orig_retrieve = emb.embed, buf.retrieve

    def timed_embed(image):
        t = time.perf_counter()
        try:
            return orig_embed(image)
        finally:
            timing["embed_ms"] += (time.perf_counter() - t) * 1000

    def timed_retrieve(**kw):
        t = time.perf_counter()
        try:
            return orig_retrieve(**kw)
        finally:
            timing["query_ms"] += (time.perf_counter() - t) * 1000

    emb.embed, buf.retrieve = timed_embed, timed_retrieve
    return retr, emb, timing, load_s


def timed_retrieval(retr, timing: dict, ep: Episode, exclude: Optional[set]) -> tuple[Any, dict]:
    timing["embed_ms"] = timing["query_ms"] = 0.0
    rgb_start = (ep.dump_dir / "episode_start.png").read_bytes()
    init_L = tuple(int(v) for v in ep.meta["rounds"][0]["actual_left_start"])
    t0 = time.perf_counter()
    pre = retr.retrieve_for_episode(init_rgb_bytes=rgb_start, init_L_EE=init_L, exclude_run_ids=exclude)
    total = (time.perf_counter() - t0) * 1000
    info = {"retrieval_total_ms": total, "retrieval_embed_ms": timing["embed_ms"],
            "retrieval_query_ms": timing["query_ms"],
            "retrieval_other_ms": total - timing["embed_ms"] - timing["query_ms"],
            "retrieved": [r.ep_id for r in pre.retrieved_records],
            "retrieved_runs": sorted({r.run_id for r in pre.retrieved_records}),
            "similarities": list(pre.similarities), "preamble_chars": len(pre.prelude_text)}
    return pre, info


def run_recap(ep: Episode, level_config: LevelConfig, url: str, emb, timing: dict) -> dict:
    """Rebuild + send the post-episode recap exactly as collect -> generate_recap would."""
    active_arm = _active_arm_for_level(level_config)
    traj = ep.replay.get("trajectory") or []
    first, last = (traj[0], traj[-1]) if traj else ({}, {})
    init_L = tuple(first.get("left_ee_pos") or (0, 0, 0))
    final_L = tuple(last.get("left_ee_pos") or (0, 0, 0))
    init_R = tuple(first["right_ee_pos"]) if first.get("right_ee_pos") else None
    final_R = tuple(last["right_ee_pos"]) if last.get("right_ee_pos") else None
    inter = [SimpleNamespace(**i) for i in ep.replay.get("vlm_interactions", [])]
    rounds = s4mod.rounds_from_meta_and_interactions(ep.meta["rounds"], inter, ep.dump_dir, active_arm)
    if not rounds:
        return {"recap": "skipped_no_rounds"}
    outcome = ep.replay["outcome"]
    key_round = s4mod._select_key_round(outcome, rounds)
    outcome_class = s4mod._classify_outcome(outcome, rounds)
    init_p, end_p = ep.dump_dir / "round_01_pre.png", ep.dump_dir / "episode_end.png"
    init_b = init_p.read_bytes() if init_p.exists() else None
    final_b = end_p.read_bytes() if end_p.exists() else None
    key_b = key_round.pre_png.read_bytes() if key_round and key_round.pre_png else None
    timing["embed_ms"] = 0.0  # generate_recap embeds init_pre for the stored record
    from PIL import Image
    import io
    emb.embed(Image.open(io.BytesIO(init_b)).convert("RGB"))
    recap_embed_ms = timing["embed_ms"]
    lesson = s4mod._request_vlm_recap(
        teacher_url=url, outcome=outcome, outcome_class=outcome_class,
        active_arm=active_arm or "left", instruction=level_config.task_instruction_template,
        init_L_EE=init_L, final_L_EE=final_L, init_R_EE=init_R, final_R_EE=final_R,
        rounds=rounds, key_round=key_round, init_bytes=init_b, final_bytes=final_b,
        key_bytes=key_b, max_words=100,
    )
    return {"recap_embed_ms": recap_embed_ms, "recap_outcome_class": outcome_class,
            "recap_ok": bool(lesson)}


# ───────────────────────────── protocol driver ─────────────────────────────


def run_protocol(p: Protocol, args, rec: Recorder, retr_bundle) -> dict:
    level_config = LEVEL_CONFIGS[LEVEL]
    url = args.teacher_url if p.server == "teacher" else args.student_url
    eps = load_episodes(p.source_run)
    plan = select_steps(eps, args.n_steps, args.max_rounds_per_ep)
    mean_rounds = statistics.mean(len(e.meta["rounds"]) for e in eps)
    rec.emit({"record_type": "protocol", "protocol": p.name, "source_run": p.source_run,
              "url": url, "variant": p.variant, "memory": p.memory, "recap": p.recap,
              "n_source_episodes": len(eps), "source_mean_rounds_per_ep": mean_rounds,
              "plan": [[e.ep_idx, e.ep_id, n] for e, n in plan]})
    logger.info(f"[{p.name}] run={p.source_run} url={url} plan="
                f"{[(e.ep_idx, n) for e, n in plan]} mean_rounds/ep={mean_rounds:.2f}")
    if args.warmup and not rec.dry_run:
        rec.ctx = {"protocol": p.name, "warmup": True}
        try:
            rec.call(url, build_chat_request("ping", "ping", max_tokens=1), 300.0, "warmup")
        except Exception as e:  # noqa: BLE001 — warm-up failure is logged, run continues
            logger.warning(f"[{p.name}] warm-up failed: {e}")
    for ep, n_rounds in plan:
        conversation = EpisodeConversation(get_stage1_system_prompt())
        pre_text = pre_imgs = None
        ep_info: dict = {}
        if p.memory:
            retr, _, timing, _ = retr_bundle
            exclude = {p.source_run} if p.exclude_source_run else None
            pre, ep_info = timed_retrieval(retr, timing, ep, exclude)
            if not pre.is_empty:
                pre_text, pre_imgs = pre.prelude_text, pre.past_image_base64_list
        for k in range(n_rounds):
            state, dist_src = build_state(ep, k, level_config)
            stored = (ep.replay.get("vlm_interactions") or [])
            stored_k = stored[k] if k < len(stored) else {}
            rec.ctx = {"protocol": p.name, "source_run": p.source_run, "ep_idx": ep.ep_idx,
                       "ep_id": ep.ep_id, "round": k + 1, "variant": p.variant,
                       "stored_left": stored_k.get("parsed_left_pos"),
                       "stored_right": stored_k.get("parsed_right_pos")}
            n_before = len(rec.calls)
            rgb = (ep.dump_dir / f"round_{k + 1:02d}_pre.png").read_bytes()
            result, _lat, err = s1mod.run_stage1(
                level_config=level_config, teacher_url=url, rgb_bytes=rgb, state=state,
                conversation=conversation, critic_feedback=ep.meta["rounds"][k].get("critic_feedback"),
                max_retries=level_config.max_retry_on_parse_fail,
                memory_preamble_text=pre_text if k == 0 else None,
                memory_preamble_images_b64=pre_imgs if k == 0 else None,
                eval_template_variant=p.variant, scored_arm=None,
            )
            step_calls = rec.calls[n_before:]
            rec.emit({"record_type": "step", **rec.ctx, "dist_source": dist_src,
                      "n_lm_calls": len(step_calls), "parse_ok": result is not None, "error": err,
                      **({k2: v for k2, v in ep_info.items()} if k == 0 else {})})
            if result is None:
                logger.warning(f"[{p.name}] ep{ep.ep_idx} r{k + 1}: {err} -> episode bails (as pipeline)")
                break
        if p.recap:
            _, emb, timing, _ = retr_bundle
            rec.ctx = {"protocol": p.name, "source_run": p.source_run, "ep_idx": ep.ep_idx,
                       "ep_id": ep.ep_id, "round": None, "variant": p.variant}
            info = run_recap(ep, level_config, url, emb, timing)
            rec.emit({"record_type": "episode_recap", **rec.ctx, **info})
    return {"mean_rounds": mean_rounds}


# ───────────────────────────── summary ─────────────────────────────


def summarize(records: list[dict], meta: dict) -> list[dict]:
    rows = []
    for name, m in meta.items():
        calls = [r for r in records if r.get("record_type") == "call" and r.get("protocol") == name
                 and not r.get("warmup")]
        steps = [r for r in records if r.get("record_type") == "step" and r.get("protocol") == name]
        recaps = [r for r in records if r.get("record_type") == "episode_recap" and r.get("protocol") == name]
        retr = [r for r in steps if "retrieval_total_ms" in r]
        S, R = max(len(steps), 1), m["mean_rounds"]

        def tok(kind, key):
            vals = [(c.get("usage") or {}).get(key) for c in calls if c["call_kind"] == kind]
            return sum(v for v in vals if v is not None) if any(v is not None for v in vals) else None

        def per_step(kind_s1, kind_ep):
            if kind_s1 is None:
                return None
            ep_part = (kind_ep / len(recaps) / R) if (recaps and kind_ep is not None) else 0.0
            return kind_s1 / S + ep_part

        s1 = [c for c in calls if c["call_kind"] == "stage1"]
        rc = [c for c in calls if c["call_kind"] == "recap"]

        def tim(key):  # llama-server `timings` block (server-side split of the LM call)
            def total(cs):
                vals = [(c.get("timings") or {}).get(key) for c in cs]
                return sum(v for v in vals if v is not None) if any(v is not None for v in vals) else None
            return per_step(total(s1), total(rc))

        retr_ms = statistics.mean(r["retrieval_total_ms"] for r in retr) if retr else None
        retr_eq = (statistics.mean(r["retrieval_embed_ms"] + r["retrieval_query_ms"] for r in retr)
                   if retr else None)
        rows.append({
            "protocol": name, "steps": len(steps), "episodes": len({s["ep_id"] for s in steps}),
            "recaps": len(recaps), "mean_rounds_per_ep_source": R,
            "stage1_calls_per_step": len(s1) / S,
            "lm_calls_per_step": len(s1) / S + (len(rc) / max(len(recaps), 1) / R if recaps else 0.0),
            "prompt_tok_per_step": per_step(tok("stage1", "prompt_tokens"), tok("recap", "prompt_tokens")),
            "completion_tok_per_step": per_step(tok("stage1", "completion_tokens"),
                                                tok("recap", "completion_tokens")),
            "wall_s_per_step": per_step(sum(c["wall_s"] for c in s1), sum(c["wall_s"] for c in rc)),
            "server_cache_n_per_step": tim("cache_n"),
            "server_prompt_n_per_step": tim("prompt_n"),
            "server_prompt_ms_per_step": tim("prompt_ms"),
            "server_predicted_ms_per_step": tim("predicted_ms"),
            "stage1_prompt_chars_per_step": sum(c["prompt_text_chars"] for c in s1) / S,
            "stage1_images_per_step": sum(c["n_images"] for c in s1) / S,
            "retrieval_ms_per_episode": retr_ms, "retrieval_embed_plus_query_ms": retr_eq,
            "retrieval_ms_per_step_amortized": retr_ms / R if retr_ms is not None else None,
            "parse_fail_steps": sum(1 for s in steps if not s["parse_ok"]),
            "dist_sources": {k: sum(1 for s in steps if s["dist_source"] == k)
                             for k in sorted({s["dist_source"] for s in steps})},
        })
    return rows


def _fmt(v, nd=1):
    return "n/a" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def render_md(rows: list[dict], header: dict) -> str:
    lines = ["# Same-hardware inference cost re-measure (D11 A15 add-on, descriptive)", "",
             f"- generated: {header['ts']}  host: {header['host']}  git: {header['git']}",
             f"- dry_run: {header['dry_run']}  teacher_url: {header['teacher_url']}  "
             f"student_url: {header['student_url']}",
             f"- student /lora-adapters at start: `{header.get('student_lora')}`",
             f"- selection: run order, rounds 1..min(n,{header['max_rounds']}), n_steps={header['n_steps']}",
             "- per-step = stage-1 per step + per-episode recap / source-run mean rounds/ep",
             "", "| protocol | LM calls/step | prompt tok/step | completion tok/step | wall s/step "
             "| retrieval ms/ep (embed+query) | retrieval ms/step amort. |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['protocol']} | {_fmt(r['lm_calls_per_step'], 3)} | {_fmt(r['prompt_tok_per_step'])} "
            f"| {_fmt(r['completion_tok_per_step'])} | {_fmt(r['wall_s_per_step'], 2)} "
            f"| {_fmt(r['retrieval_ms_per_episode'])} ({_fmt(r['retrieval_embed_plus_query_ms'])}) "
            f"| {_fmt(r['retrieval_ms_per_step_amortized'])} |")
    lines += ["", "Detail:", ""]
    for r in rows:
        lines.append(f"- {r['protocol']}: steps={r['steps']} episodes={r['episodes']} recaps={r['recaps']} "
                     f"mean_rounds/ep(source)={r['mean_rounds_per_ep_source']:.2f} "
                     f"stage1 calls/step={r['stage1_calls_per_step']:.3f} "
                     f"stage1 prompt chars/step={r['stage1_prompt_chars_per_step']:.0f} "
                     f"images/step={r['stage1_images_per_step']:.2f} "
                     f"parse_fail_steps={r['parse_fail_steps']} dist_sources={r['dist_sources']} "
                     f"server/step: cache_n={_fmt(r['server_cache_n_per_step'])} "
                     f"prompt_n={_fmt(r['server_prompt_n_per_step'])} "
                     f"prompt_ms={_fmt(r['server_prompt_ms_per_step'])} "
                     f"predicted_ms={_fmt(r['server_predicted_ms_per_step'])}")
    return "\n".join(lines) + "\n"


# ───────────────────────────── main ─────────────────────────────


def tree_hash(root: Path) -> str:
    """Byte-identical to run_a15_night.sh tree_hash() (same shell pipeline)."""
    cmd = "find . -type f | sort | xargs sha256sum | sha256sum | awk '{print $1}'"
    return subprocess.run(["bash", "-c", cmd], cwd=root, capture_output=True, text=True,
                          check=True).stdout.strip()


def _expected_tree_hash() -> Optional[str]:
    m = re.search(r'BUFFER_TREE_EXPECTED="([0-9a-f]{64})"', A15_DRIVER.read_text())
    return m.group(1) if m else None


def _get(url: str, path: str) -> str:
    try:
        return httpx.get(f"{url.rstrip('/')}{path}", timeout=10.0).text.strip()
    except Exception as e:  # noqa: BLE001 — reported in the header, not fatal
        return f"<unreachable: {e!r}>"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--protocol", choices=(*PROTOCOLS, "all"), default="all")
    ap.add_argument("--n_steps", type=int, default=20)
    ap.add_argument("--max_rounds_per_ep", type=int, default=5)
    ap.add_argument("--teacher_url", default="http://10.80.9.148:18888")
    ap.add_argument("--student_url", default="http://10.80.9.148:18889")
    ap.add_argument("--buffer_root", default=DEFAULT_BUFFER)
    ap.add_argument("--out_dir", default="logs")
    ap.add_argument("--warmup", type=int, default=1, help="1 = one tiny text-only call per protocol")
    ap.add_argument("--dry_run", action="store_true", help="build prompts + retrieval, no HTTP")
    ap.add_argument("--max_calls", type=int, default=0,
                    help="hard cap on real LM HTTP calls (0 = unlimited); for smoke tests")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    names = list(PROTOCOLS) if args.protocol == "all" else [args.protocol]
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = (REPO / args.out_dir) if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"cost_remeasure_{ts}{'_dryrun' if args.dry_run else ''}"
    git = subprocess.run(["git", "-C", str(REPO), "describe", "--always", "--dirty"],
                         capture_output=True, text=True).stdout.strip()
    header = {"ts": ts, "host": socket.gethostname(), "git": git, "dry_run": args.dry_run,
              "teacher_url": args.teacher_url, "student_url": args.student_url,
              "n_steps": args.n_steps, "max_rounds": args.max_rounds_per_ep, "protocols": names}

    if not args.dry_run:
        if any(PROTOCOLS[n].server == "student" for n in names):
            header["student_lora"] = _get(args.student_url, "/lora-adapters")
            header["student_models"] = _get(args.student_url, "/v1/models")
            logger.warning("STUDENT /lora-adapters = %s  (operator must have loaded the "
                           "A_ctrl_rat SFT+KTO adapters; this harness never reloads)", header["student_lora"])
        if any(PROTOCOLS[n].server == "teacher" for n in names):
            header["teacher_lora"] = _get(args.teacher_url, "/lora-adapters")
            header["teacher_models"] = _get(args.teacher_url, "/v1/models")
            logger.warning("TEACHER /lora-adapters = %s", header["teacher_lora"])

    buffer_root = REPO / args.buffer_root
    need_mem = any(PROTOCOLS[n].memory or PROTOCOLS[n].recap for n in names)
    retr_bundle = None
    if need_mem:
        header["buffer_tree_pre"] = tree_hash(buffer_root)
        header["buffer_tree_expected"] = _expected_tree_hash()
        if header["buffer_tree_pre"] != header["buffer_tree_expected"]:
            logger.error("buffer tree hash %s != expected %s — refusing", header["buffer_tree_pre"],
                         header["buffer_tree_expected"])
            return 3
        header["retrieval_defaults"] = read_retrieval_defaults()
        retr_bundle = make_retriever(buffer_root, header["retrieval_defaults"])
        header["embedder_load_s"] = retr_bundle[3]
        logger.info("retrieval defaults (live from run_collect.py): %s", header["retrieval_defaults"])

    meta: dict = {}
    with open(f"{stem}.jsonl", "w") as fh:
        rec = Recorder(out_fh=fh, dry_run=args.dry_run, max_calls=args.max_calls)
        rec.emit({"record_type": "header", **header})
        with patched_transport(rec):
            for n in names:
                meta[n] = run_protocol(PROTOCOLS[n], args, rec, retr_bundle)
        if need_mem:
            post = tree_hash(buffer_root)
            rec.emit({"record_type": "footer", "buffer_tree_post": post,
                      "readonly_ok": post == header["buffer_tree_pre"]})
            if post != header["buffer_tree_pre"]:
                logger.error("READONLY GATE FAILED: buffer tree changed")
    records = [json.loads(line) for line in open(f"{stem}.jsonl")]
    rows = summarize(records, meta)
    md = render_md(rows, header)
    Path(f"{stem}.md").write_text(md + "\n```json\n" + json.dumps(rows, indent=1) + "\n```\n")
    print(md)
    print(f"wrote {stem}.jsonl and {stem}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
