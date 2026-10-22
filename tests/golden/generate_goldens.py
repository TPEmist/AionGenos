"""Generate golden strings for byte-identical regression tests.

Authority: Spec REVISION 1 R8.
Captured from unmodified commit 26c9fc4e3e015e00032297204afa988f3e7f976b (26c9fc4).
Matrix: rung in {1, 1b, 2, 3} x history in {off, on} x feedback in {off, on}.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

# Ensure workspace root is in sys.path
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import torch

from aiongenos.config import LevelConfig, WorkspaceBounds, ControlMode
from aiongenos.orchestrator import push_collect as pc
from aiongenos.orchestrator import push_memory as pm
from aiongenos.orchestrator.push_feedback import format_round_feedback
from aiongenos.pipeline import stage1_reasoning as s1
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.vlm import prompts
from tests.test_push_memory import _FakePushEnv, _lc, _Parsed


def get_commit_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "26c9fc4e3e015e00032297204afa988f3e7f976b"


def capture_all() -> dict:
    commit_sha = get_commit_sha()
    goldens = {
        "commit_sha": commit_sha,
        "matrix": {},
        "standalone_prompts": {},
        "standalone_feedbacks": {},
    }

    # 1. Standalone prompts across rungs 1, 1b, 2, 3
    base_state = {
        "instruction": "Push the yellow cube onto the green zone on the table.",
        "left_x": 22, "left_y": 50, "left_z": -14,
        "right_x": 1, "right_y": -50, "right_z": -14,
        "left_gripper": "closed (locked)",
        "oracle_block": "",
    }
    for r in ["1", "1b", "2", "3"]:
        state = dict(base_state)
        state["view_block"] = pm.view_block(r)
        if pm.oracle_level(r) >= 2:
            lines = [
                "SCAFFOLD (oracle-measured, disclosed):",
                "  LEFT_TIP_TO_CUBE = 18.0 cm",
                "  CUBE_TO_GOAL     = 8.2 cm",
            ]
            if pm.oracle_level(r) >= 3:
                lines += [
                    "  CUBE_POS     = (X=56, Y=25)",
                    "  GOAL_POS     = (X=73, Y=30)",
                    "  TIP_TO_CUBE  = (dX=34, dY=-25)",
                    "  CUBE_TO_GOAL = (dX=17, dY=5)",
                ]
            state["oracle_block"] = "\n".join(lines) + "\n"
        prompt_txt = prompts.get_stage1_prompt(_lc(), state)
        goldens["standalone_prompts"][f"rung_{r}"] = prompt_txt

    # 2. Standalone feedbacks
    # Proprio only (rung 1/1b)
    fb_proprio = format_round_feedback(
        prev_target_int=(45, 8, 48),
        tcp_start_int=(22, 50, -14),
        tcp_end_int=(47, 8, 48),
    )
    # Rung 2: progress (cube->goal drops from 8.2 to 5.2 cm)
    fb_prog = format_round_feedback(
        prev_target_int=(45, 8, 48),
        tcp_start_int=(22, 50, -14),
        tcp_end_int=(47, 8, 48),
        scalars_start_cm=(18.0, 8.2),
        scalars_end_cm=(10.1, 5.2),
    )
    # Rung 2: regress (cube->goal increases from 8.2 to 9.5 cm)
    fb_reg = format_round_feedback(
        prev_target_int=(45, 8, 48),
        tcp_start_int=(22, 50, -14),
        tcp_end_int=(47, 8, 48),
        scalars_start_cm=(18.0, 8.2),
        scalars_end_cm=(10.1, 9.5),
    )
    # Rung 2: flat (cube->goal unchanged at 8.2 to 8.0 cm)
    fb_flat = format_round_feedback(
        prev_target_int=(45, 8, 48),
        tcp_start_int=(22, 50, -14),
        tcp_end_int=(47, 8, 48),
        scalars_start_cm=(18.0, 8.2),
        scalars_end_cm=(10.1, 8.0),
    )
    goldens["standalone_feedbacks"] = {
        "proprio_only": fb_proprio,
        "progress": fb_prog,
        "regress": fb_reg,
        "flat": fb_flat,
    }

    # 3. Full matrix: 4 rungs x 2 histories x 2 feedbacks = 16 combinations
    for r in ["1", "1b", "2", "3"]:
        for hist in [False, True]:
            for fb in [False, True]:
                key = f"rung={r}__hist={hist}__fb={fb}"
                round_calls = []

                def fake_sync(url, system_prompt, user_prompt, **kw):
                    round_calls.append({
                        "mode": "sync",
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                    })
                    return "THOUGHT: push.\nLEFT_TARGET_POS: X=45 Y=8 Z=48\nSTOP: false"

                def fake_history(url, conversation, **kw):
                    user_texts = []
                    for m in conversation.messages:
                        if m["role"] == "user":
                            for c in m["content"]:
                                if c["type"] == "text":
                                    user_texts.append(c["text"])
                    round_calls.append({
                        "mode": "history",
                        "user_prompt": user_texts[-1] if user_texts else "",
                        "all_user_texts": user_texts,
                    })
                    return "THOUGHT: push.\nLEFT_TARGET_POS: X=45 Y=8 Z=48\nSTOP: false"

                orig_sync = s1.call_vlm_sync
                orig_hist = s1.call_vlm_history_sync
                s1.call_vlm_sync = fake_sync
                s1.call_vlm_history_sync = fake_history

                try:
                    with tempfile.TemporaryDirectory() as td:
                        rp = ReplayBuffer(pathlib.Path(td) / "rp")
                        env = _FakePushEnv(rung=r)
                        summary = pc.run_push_collect_loop(
                            env, _lc(), "http://fake-teacher", rp, 1,
                            round_feedback=fb,
                            round_history=hist,
                        )
                        rm = summary["episodes"][0]["round_meta"]
                        goldens["matrix"][key] = {
                            "round1_user_prompt": round_calls[0]["user_prompt"],
                            "round1_feedback": rm[0].get("round_feedback"),
                            "round2_user_prompt": round_calls[1]["user_prompt"],
                            "round2_feedback": rm[1].get("round_feedback"),
                        }
                finally:
                    s1.call_vlm_sync = orig_sync
                    s1.call_vlm_history_sync = orig_hist

    return goldens


if __name__ == "__main__":
    out_dir = pathlib.Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "golden_matrix.json"
    print(f"Capturing goldens from commit {get_commit_sha()}...")
    data = capture_all()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data['matrix'])} matrix entries to {out_path}")
