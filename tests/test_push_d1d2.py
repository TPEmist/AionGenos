"""Tests for WP1-3a interface fixes d1 (frame convention) and d2 (verdict contact switch).

Authority: Spec §1, §2, §5 and REVISION 1 (R1, R2, R3, R4, R5, R6, R8).

§1.1 Direction Ground Truth Evidence:
  - +X points forward, away from the robot base, toward the table:
    In meta.json static_scene_b, the table x-range is [0.169, 0.951] m while the
    robot base is at x=0.0; the cube is located at x≈0.39 m.
  - +Y is the robot's LEFT:
    In logs/wp3a_reach_real.log and robot kinematics, the left shoulder (openarm_left_link2)
    has base-frame coordinate y=+0.15 m; the left arm drives the TCP.
  - +Z is UP:
    In meta.json static_scene_b, the table surface is at z=0.444 m, which is higher
    than the ground plane at z=-0.55 m.
"""

from __future__ import annotations

import copy
import importlib
import json
import pathlib
import re
import tempfile
import numpy as np
import pytest
import torch

from aiongenos.config import ControlMode, LevelConfig, WorkspaceBounds
from aiongenos.orchestrator import push_collect as pc
from aiongenos.orchestrator import push_memory as pm
from aiongenos.orchestrator.push_feedback import format_round_feedback
from aiongenos.pipeline import stage1_reasoning as s1
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.vlm import prompts
from tests.test_push_memory import _FakePushEnv, _lc, _Parsed


def test_p1_reach_path_untouched():
    """AC6: Git diff must not touch collect.py or stage3_critic.py."""
    import subprocess
    root = pathlib.Path(__file__).resolve().parent.parent
    diff_names = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD"], cwd=str(root)
    ).decode().splitlines()
    diff_cached = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"], cwd=str(root)
    ).decode().splitlines()
    all_diffs = set(diff_names + diff_cached)
    for f in all_diffs:
        # P1 reach path files: collect.py and stage3_critic.py
        p = pathlib.Path(f)
        assert p.name != "collect.py", f"P1 reach collect.py must stay untouched: {f}"
        assert p.name != "stage3_critic.py", f"stage3_critic.py must stay untouched: {f}"


# ── AC1 & R8: Byte-identical Golden Matrix Regression ───────────────────────

def test_golden_matrix_byte_identical_when_flags_off():
    """AC1 / R8: With both new flags off, prompts and feedback are byte-identical
    to the golden captured from unmodified commit 26c9fc4 across the full 16-combination matrix:
    rung in {1, 1b, 2, 3} x history in {off, on} x feedback in {off, on}.
    """
    golden_path = pathlib.Path(__file__).resolve().parent / "golden" / "golden_matrix.json"
    assert golden_path.exists(), f"Golden matrix file not found: {golden_path}"
    with open(golden_path, "r", encoding="utf-8") as f:
        goldens = json.load(f)

    # 1. Standalone prompts
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
        rendered = prompts.get_stage1_prompt(_lc(), state)
        assert rendered == goldens["standalone_prompts"][f"rung_{r}"], f"Prompt mismatch on rung {r}"

    # 2. Standalone feedbacks
    assert format_round_feedback((45, 8, 48), (22, 50, -14), (47, 8, 48)) == goldens["standalone_feedbacks"]["proprio_only"]
    assert format_round_feedback((45, 8, 48), (22, 50, -14), (47, 8, 48), (18.0, 8.2), (10.1, 5.2)) == goldens["standalone_feedbacks"]["progress"]
    assert format_round_feedback((45, 8, 48), (22, 50, -14), (47, 8, 48), (18.0, 8.2), (10.1, 9.5)) == goldens["standalone_feedbacks"]["regress"]
    assert format_round_feedback((45, 8, 48), (22, 50, -14), (47, 8, 48), (18.0, 8.2), (10.1, 8.0)) == goldens["standalone_feedbacks"]["flat"]

    # 3. 16-entry matrix
    for r in ["1", "1b", "2", "3"]:
        for hist in [False, True]:
            for fb in [False, True]:
                key = f"rung={r}__hist={hist}__fb={fb}"
                expected = goldens["matrix"][key]
                round_calls = []

                def fake_sync(url, system_prompt, user_prompt, **kw):
                    round_calls.append({"user_prompt": user_prompt})
                    return "THOUGHT: push.\nLEFT_TARGET_POS: X=45 Y=8 Z=48\nSTOP: false"

                def fake_history(url, conversation, **kw):
                    user_texts = [
                        c["text"]
                        for m in conversation.messages if m["role"] == "user"
                        for c in m["content"] if c["type"] == "text"
                    ]
                    round_calls.append({"user_prompt": user_texts[-1] if user_texts else ""})
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
                            env, _lc(), "http://fake", rp, 1,
                            round_feedback=fb,
                            round_history=hist,
                            frame_convention=False,
                            verdict_contact_switch=False,
                        )
                        rm = summary["episodes"][0]["round_meta"]
                        assert round_calls[0]["user_prompt"] == expected["round1_user_prompt"], f"Round 1 prompt mismatch on {key}"
                        assert rm[0].get("round_feedback") == expected["round1_feedback"], f"Round 1 feedback mismatch on {key}"
                        assert round_calls[1]["user_prompt"] == expected["round2_user_prompt"], f"Round 2 prompt mismatch on {key}"
                        assert rm[1].get("round_feedback") == expected["round2_feedback"], f"Round 2 feedback mismatch on {key}"
                finally:
                    s1.call_vlm_sync = orig_sync
                    s1.call_vlm_history_sync = orig_hist


# ── AC2 & §1: d1 Frame Convention Line ──────────────────────────────────────

def test_d1_frame_convention_renders_exactly_once_with_computed_units():
    """AC2: When frame_convention is True, exactly one FRAME line is rendered,
    with units computed from live WorkspaceBounds. Changing bounds changes units (no literal).
    
    §1.1 Direction evidence:
      - +X forward, away from base: table x in static_scene_b [0.169, 0.951]m, cube at x≈0.39m
      - +Y robot's left: left shoulder y=+0.15m in logs/wp3a_reach_real.log; left arm drives TCP
      - +Z up: table top z=0.444m > ground z=-0.55m in static_scene_b
    """
    bounds = WorkspaceBounds(x_bounds=(-0.3, 0.6), y_bounds=(-0.4, 0.4), z_bounds=(0.0, 0.7))
    line = prompts.format_frame_convention_line(bounds)
    assert line == "FRAME (base frame, same grid as the numbers above): +X = forward, away from the robot base; +Y = the robot's left; +Z = up. One grid unit = 0.45 cm in X, 0.40 cm in Y, 0.35 cm in Z."

    # Verify no hardcoded literals: changing bounds changes units
    custom_bounds = WorkspaceBounds(x_bounds=(-1.0, 1.0), y_bounds=(-0.5, 0.5), z_bounds=(-0.2, 0.8))
    custom_line = prompts.format_frame_convention_line(custom_bounds)
    assert custom_line == "FRAME (base frame, same grid as the numbers above): +X = forward, away from the robot base; +Y = the robot's left; +Z = up. One grid unit = 1.00 cm in X, 0.50 cm in Y, 0.50 cm in Z."
    assert custom_line != line

    # Negative check: must NOT contain positions of cube/goal/table or image mapping or strategy
    for forbidden in ["cube", "goal", "table", "disc", "image", "up in the image", "strategy"]:
        assert forbidden not in line.lower()


def test_d1_missing_frame_block_does_not_raise_keyerror():
    """R4: get_stage1_prompt must not raise KeyError when caller state lacks frame_block."""
    state_without_frame_block = {
        "instruction": "push", "left_x": 10, "left_y": 20, "left_z": -5,
        "right_x": 0, "right_y": 0, "right_z": 0,
        "left_gripper": "closed (locked)", "oracle_block": "", "view_block": "",
    }
    rendered = prompts.get_stage1_prompt(_lc(), state_without_frame_block)
    assert "FRAME" not in rendered
    assert "LEFT_GRIPPER = closed (locked)\n\nThe yellow cube" in rendered


def test_d1_in_push_collect_loop(tmp_path, monkeypatch):
    """When frame_convention=True in push_collect_loop, frame_block appears in prompt,
    is recorded in summary and meta.json."""
    calls = []
    pc_mod = importlib.import_module("aiongenos.orchestrator.push_collect")

    def fake(lc, url, rgb, state, **kw):
        calls.append(state)
        return _Parsed(), 10.0, None
    monkeypatch.setattr(pc_mod, "run_stage1_eef", fake)

    env = _FakePushEnv(rung="1")
    summary = pc_mod.run_push_collect_loop(
        env, _lc(), "http://fake", ReplayBuffer(tmp_path / "rp"), 1,
        dump_images_root=tmp_path / "dumps",
        frame_convention=True,
    )
    assert summary["frame_convention"] is True
    assert summary["frame_line"] is not None
    assert summary["frame_line"].startswith("FRAME (base frame, same grid as the numbers above):")
    assert calls[0]["frame_block"] == summary["frame_line"] + "\n"

    # Check dump meta
    ep_id = summary["episodes"][0]["ep_id"]
    meta_path = tmp_path / "dumps" / summary["run_id"] / ep_id / "meta.json"
    with open(meta_path) as f:
        meta_data = json.load(f)
    assert meta_data["frame_convention"] is True
    assert meta_data["frame_line"] == summary["frame_line"]


# ── AC3 & §2: d2 Contact-Switched P1 Verdict ────────────────────────────────

def test_d2_verdict_contact_switch_logic(tmp_path, monkeypatch):
    """AC3 / R1 / R2 / R3:
    d2 on behind --verdict_contact_switch:
      - Pre-contact: verdict uses fingertip->cube (scalars[0]).
      - First round with contact (switching round): judged on fingertip->cube (approach that made contact gets PROGRESS).
      - Post-contact: verdict uses cube->goal (scalars[1]).
      - Sticky: remains cube->goal afterwards.
      - Round 1 feedback is None, verdict_metric is None.
      - Templates remain byte-identical P1 templates.
    """
    pc_mod = importlib.import_module("aiongenos.orchestrator.push_collect")
    feedback_seen = []

    def fake(lc, url, rgb, state, **kw):
        feedback_seen.append(kw.get("critic_feedback"))
        return _Parsed(), 10.0, None
    monkeypatch.setattr(pc_mod, "run_stage1_eef", fake)

    # Env where:
    # Round 1: no motion (motion(1)=0.0), no contact. Tip moves closer.
    # Round 2: makes first contact! (motion(2)=0.015). Tip approaches cube.
    # Round 3: post-contact push! (motion(3)=0.015). Cube moves toward goal.
    # Round 4: continuing post-contact push.
    env = _FakePushEnv(rung="2", motion=lambda r: 0.015 if r >= 2 else 0.0)

    # Override contact report to have first_cube_move only on round 2
    orig_exec = env.execute_push_segment
    def exec_override(target, quat, steps, frame_every=0, target_is_tcp=False):
        res = orig_exec(target, quat, steps, frame_every, target_is_tcp)
        # In round 1: force no contact
        if env.rounds == 1:
            res["contact"]["first_cube_move"] = None
            res["contact"]["cube_disp_vec_cm"] = [0.0, 0.0, 0.0]
        return res
    env.execute_push_segment = exec_override

    summary = pc_mod.run_push_collect_loop(
        env, _lc(), "http://fake", ReplayBuffer(tmp_path / "rp"), 1,
        steps_per_segment=90,
        round_feedback=True,
        verdict_contact_switch=True,
    )

    rm = summary["episodes"][0]["round_meta"]
    # 1. Round 1 feedback is None, verdict_metric is None
    assert rm[0]["round_feedback"] is None
    assert rm[0]["verdict_metric"] is None

    # 2. Round 2 feedback: describes round 1 (pre-contact).
    # Cube did not move (8.2 -> 8.2), but fingertip moved closer (18.0 -> 7.8 cm).
    # Under d2, verdict must be PROGRESS based on tip_cube (drop of 10.2 cm)!
    fb2 = rm[1]["round_feedback"]
    assert rm[1]["verdict_metric"] == "tip_cube"
    assert "Result: Successful progress. Left arm moved 10.2 cm closer to target." in fb2

    # 3. Round 3 feedback: describes round 2 (first round with contact).
    # Per R1: judged on tip_cube! (approach that made contact gets judged on approach)
    assert rm[2]["verdict_metric"] == "tip_cube"

    # 4. Round 4 feedback: describes round 3 (post-contact, contact happened strictly before round 3 in round 2).
    # Per R1: uses cube_goal!
    assert rm[3]["verdict_metric"] == "cube_goal"


# ── AC4: Logging Additions ──────────────────────────────────────────────────

def test_logging_additions_cube_quat_and_verdict_metric(tmp_path, monkeypatch):
    """AC4: cube_quat_b_pre and verdict_metric are logged in round_meta;
    frame_line, frame_convention, verdict_contact_switch logged in ep_meta."""
    pc_mod = importlib.import_module("aiongenos.orchestrator.push_collect")
    monkeypatch.setattr(pc_mod, "run_stage1_eef", lambda *a, **k: (_Parsed(), 10.0, None))

    env = _FakePushEnv(rung="2")
    env.cube_quat = [0.7071, 0.0, 0.7071, 0.0]
    summary = pc_mod.run_push_collect_loop(
        env, _lc(), "http://fake", ReplayBuffer(tmp_path / "rp"), 1,
        dump_images_root=tmp_path / "dumps",
        round_feedback=True,
        frame_convention=True,
        verdict_contact_switch=True,
    )
    rm = summary["episodes"][0]["round_meta"]
    assert rm[0]["cube_quat_b_pre"] == [0.7071, 0.0, 0.7071, 0.0]
    assert rm[0]["verdict_metric"] is None
    assert rm[1]["verdict_metric"] in ("tip_cube", "cube_goal")

    # Check meta.json
    ep_id = summary["episodes"][0]["ep_id"]
    meta_file = tmp_path / "dumps" / summary["run_id"] / ep_id / "meta.json"
    with open(meta_file) as f:
        meta = json.load(f)
    assert meta["frame_convention"] is True
    assert meta["verdict_contact_switch"] is True
    assert "cube_quat_b_pre" in meta["rounds"][0]
    assert "verdict_metric" in meta["rounds"][0]
