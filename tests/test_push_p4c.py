"""Unit tests for Pin-4c geometry, polar sampler math, scripted sweep mode,
preamble arm, and runtime gate (Spec §2, §3, §4, AC1, AC3, AC4, AC5).
Pure CPU tests — no Isaac/GPU.
"""
from __future__ import annotations

import math
import pathlib
from unittest.mock import MagicMock
import gymnasium as gym
import numpy as np
import pytest
import torch

from aiongenos.config import ControlMode, LevelConfig, WorkspaceBounds
from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord
from aiongenos.orchestrator import push_memory as pm
from aiongenos.orchestrator.push_collect import run_push_collect_loop
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome
from aiongenos.tasks.WP1_contact_testbed.cube_relative_goal import (
    CubeRelativePolarCommand,
    CubeRelativePolarCommandCfg,
    compute_polar_goal,
)
from aiongenos.tasks.WP1_contact_testbed import pin4c_constants as C
from scripts.diagnostics.wp3a_pin4c_gate import (
    check_pin4c_sample,
    evaluate_pin4c_distribution,
)


def _png(color=(0, 200, 0), size=(32, 24)) -> bytes:
    from PIL import Image
    import io
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class _FakeUnwrapped:
    def __init__(self, mel=2000):
        self.max_episode_length = mel
        self.episode_length_buf = [0]


class _FakeGym:
    def __init__(self, mel=2000):
        self.unwrapped = _FakeUnwrapped(mel)


class _FakePushEnvP4c:
    """IsaacLabEnvInterface stand-in for Pin-4c testing."""

    Q_REST = torch.tensor([0.0, 0.7071, 0.0, 0.7071])

    def __init__(self, mel=2000, rung="1", goal_sample=None, cube_moves=True):
        self.env = _FakeGym(mel)
        self.push_obs_rung = rung
        self.push_frame_convention = False
        self.cube_quat = [1.0, 0.0, 0.0, 0.0]
        self.seg_calls = []
        self.cube_moves = cube_moves
        self.goal_sample = goal_sample or {
            "theta": 0.0,
            "dist": 0.08,
            "cube_xy": [0.40, 0.10],
        }

    def reset(self, seed=None):
        self.cube = np.array([0.40, 0.10, 0.02])
        self.goal = np.array([0.55, 0.10, 0.02])
        self.tcp = np.array([0.25, 0.20, 0.30])
        self.env.unwrapped.episode_length_buf[0] = 1
        self.rounds = 0

    def get_rgb(self):
        return _png(size=(32, 24))

    def get_rgb_top(self):
        return b""

    def get_state(self, lc):
        g = pm.grid_xyz(self.tcp, lc.workspace_bounds)
        return {"left_x": g[0], "left_y": g[1], "left_z": g[2], "right_x": 0, "right_y": 0,
                "right_z": 0, "left_gripper": "closed (locked)", "frame_block": "",
                "oracle_block": "", "view_block": pm.view_block(self.push_obs_rung)}

    def get_cube_quat_b(self):
        return list(self.cube_quat)

    def get_cube_pose_b(self):
        return self.cube.tolist()

    def get_goal_pose_b(self):
        return self.goal.tolist()

    def get_goal_sample(self):
        return dict(self.goal_sample)

    def get_left_tcp_pos_b(self):
        return self.tcp.tolist()

    def get_left_hand_quat_b(self):
        return self.Q_REST.clone()

    def push_scalars_m(self):
        return (float(np.linalg.norm(self.tcp[:2] - self.cube[:2])),
                float(np.linalg.norm(self.cube[:2] - self.goal[:2])))

    def execute_push_segment(self, target_pos, target_quat, steps, frame_every=0, target_is_tcp=True):
        self.rounds += 1
        self.seg_calls.append(target_pos.clone())
        self.tcp = target_pos.cpu().numpy()
        # Move cube slightly if requested (>1cm so does not trigger plateau)
        if self.cube_moves:
            self.cube[0] += 0.02
        return {
            "tcp_final_b": self.tcp.tolist(),
            "hand_target_b": self.tcp.tolist(),
            "tcp_target_b": self.tcp.tolist(),
            "ori_err_deg_final": 0.0,
            "ori_err_deg": [0.0],
            "min_err_cm": 0.05,
            "tau_warn_steps": 0,
            "tau_flag_steps": 0,
            "tau_peak_preclip": 0.5,
            "tau_peak_postclip": 0.5,
            "contact": {"first_cube_move": None},
        }

    def close(self):
        pass


def test_polar_sampler_math_no_clamping():
    """AC3 / R1: Pure U(theta) x U(d) polar sampler math has NO clamping."""
    cube = [0.40, 0.10]
    
    # 0 deg: goal along +X
    g0 = compute_polar_goal(cube, 0.0, 0.08)
    assert pytest.approx(g0[0], abs=1e-5) == 0.48
    assert pytest.approx(g0[1], abs=1e-5) == 0.10

    # 90 deg: goal along +Y
    g90 = compute_polar_goal(cube, math.pi / 2, 0.10)
    assert pytest.approx(g90[0], abs=1e-5) == 0.40
    assert pytest.approx(g90[1], abs=1e-5) == 0.20

    # -60 deg: goal along -60 deg
    th = -math.pi / 3
    g_neg = compute_polar_goal(cube, th, 0.07)
    assert pytest.approx(g_neg[0], abs=1e-5) == 0.40 + 0.07 * math.cos(th)
    assert pytest.approx(g_neg[1], abs=1e-5) == 0.10 + 0.07 * math.sin(th)

    # Verify no clamping occurs even for extreme positions
    g_far = compute_polar_goal([0.50, 0.20], math.pi / 4, 0.10)
    assert g_far[0] == 0.50 + 0.10 * math.cos(math.pi / 4)
    assert g_far[1] == 0.20 + 0.10 * math.sin(math.pi / 4)


def test_single_sourced_constants_in_push_s3a_cfg():
    """AC3 / Spec §2: θ_max, dist range and cube box are constants in push_s3a_cfg.py."""
    assert hasattr(C, "PIN4C_THETA_MAX")
    assert hasattr(C, "PIN4C_THETA_RANGE")
    assert hasattr(C, "PIN4C_DIST_RANGE")
    assert hasattr(C, "PIN4C_CUBE_REGION_X")
    assert hasattr(C, "PIN4C_CUBE_REGION_Y")

    assert C.PIN4C_THETA_MAX >= math.radians(60.0)  # PI requirement >= 60°
    assert C.PIN4C_DIST_RANGE == (0.07, 0.10)
    assert C.PIN4C_CUBE_REGION_X[0] >= 0.38  # Hand keep-out floor


def test_gym_environments_registered():
    """R7: Isaac-AionGenos-WP1-Push-P4c-v0 and TopCam variant registered."""
    import aiongenos.tasks  # noqa
    assert "Isaac-AionGenos-WP1-Push-P4c-v0" in gym.envs.registry
    assert "Isaac-AionGenos-WP1-Push-P4c-TopCam-v0" in gym.envs.registry


def test_pin4c_gate_nominal_passes_and_negative_test_fails():
    """AC3: Runtime gate math passes on nominal samples and FAILS on narrowed constants."""
    rng = np.random.RandomState(42)
    # Generate 100 nominal samples
    samples = []
    for _ in range(100):
        cx = rng.uniform(C.PIN4C_CUBE_REGION_X[0], C.PIN4C_CUBE_REGION_X[1])
        cy = rng.uniform(C.PIN4C_CUBE_REGION_Y[0], C.PIN4C_CUBE_REGION_Y[1])
        th = rng.uniform(-C.PIN4C_THETA_MAX, C.PIN4C_THETA_MAX)
        d = rng.uniform(C.PIN4C_DIST_RANGE[0], C.PIN4C_DIST_RANGE[1])
        gx = cx + d * math.cos(th)
        gy = cy + d * math.sin(th)
        samples.append(([cx, cy], [gx, gy]))

    # Nominal check must PASS
    eval_nominal = evaluate_pin4c_distribution(
        samples, C.PIN4C_THETA_MAX, C.PIN4C_DIST_RANGE,
        C.PIN4C_CUBE_REGION_X, C.PIN4C_CUBE_REGION_Y,
    )
    assert eval_nominal["ok"] is True
    assert eval_nominal["all_bounds_ok"] is True

    # Negative test 1: Narrowing theta_max to 45° makes gate check FAIL on nominal samples
    narrow_theta = math.radians(45.0)
    eval_narrow_theta = evaluate_pin4c_distribution(
        samples, narrow_theta, C.PIN4C_DIST_RANGE,
        C.PIN4C_CUBE_REGION_X, C.PIN4C_CUBE_REGION_Y,
    )
    assert eval_narrow_theta["ok"] is False
    assert eval_narrow_theta["all_bounds_ok"] is False

    # Negative test 2: Narrowing dist_range to (0.08, 0.09) makes gate check FAIL
    narrow_dist = (0.08, 0.09)
    eval_narrow_dist = evaluate_pin4c_distribution(
        samples, C.PIN4C_THETA_MAX, narrow_dist,
        C.PIN4C_CUBE_REGION_X, C.PIN4C_CUBE_REGION_Y,
    )
    assert eval_narrow_dist["ok"] is False
    assert eval_narrow_dist["all_bounds_ok"] is False


def test_scripted_blind_sweep_mode_no_vlm_call(tmp_path, monkeypatch):
    """AC4 / §3: Scripted blind sweep executes sequence, records scripted_end, NO VLM call."""
    env = _FakePushEnvP4c()
    lc = LevelConfig(level=99, name="push", control_mode=ControlMode.PUSH_WAYPOINT,
                     task_instruction_template="Push.", workspace_bounds=WorkspaceBounds())
    replay = ReplayBuffer(tmp_path / "replay")

    # Mock VLM function to ensure it is NEVER called
    mock_vlm = MagicMock()
    mock_vlm.side_effect = RuntimeError("VLM was called during scripted policy!")
    monkeypatch.setattr("aiongenos.orchestrator.push_collect.run_stage1_eef", mock_vlm)

    scripted_targets = [(40, 20, 50), (60, 20, 50), (80, 20, 50)]

    summary = run_push_collect_loop(
        env=env,
        level_config=lc,
        teacher_url="http://dummy:1234",
        replay=replay,
        num_episodes=1,
        env_seed_base=5000,
        dump_images_root=tmp_path / "dumps",
        scripted_targets=scripted_targets,
    )

    # 1. VLM was NEVER called
    mock_vlm.assert_not_called()

    # 2. Exactly 3 scripted targets executed
    assert len(env.seg_calls) == 3
    assert summary["episodes"][0]["rounds"] == 3

    # 3. Outcome is scripted_end
    assert summary["episodes"][0]["outcome"] == "scripted_end"

    # 4. Flags contain scripted_policy
    assert "scripted_policy" in summary["episodes"][0].get("round_meta", [{}])[0].get("flags", []) or \
           summary["scripted_policy"] is True

    # Check dump meta
    meta_files = list((tmp_path / "dumps").glob("*/*/meta.json"))
    assert len(meta_files) == 1
    import json
    with open(meta_files[0]) as fp:
        meta = json.load(fp)
    assert meta["outcome"] == "scripted_end"
    assert "scripted_policy" in meta["flags"]
    assert meta["scripted_policy"] is True


def test_preamble_coords_off_omits_coords_and_redacts_lessons():
    """AC5 / §4 / R2 / R9: Coords-off arm removes coordinate fields and redacts lesson coordinates."""
    # Create record with coordinates planted in lesson
    rec = RecapRecord(
        ep_id="ep1",
        run_id="run1",
        outcome="success",
        is_success=True,
        image_anchors={},
        text_lesson="Target was (40, 20, 50). Push forward along X=50 with Y=20.",
        state_anchor={
            "init_L_EE": [25, 20, 30],
            "r1_eef_target_int": [40, 20, 50],
            "r1_tcp_reached_int": [40, 20, 50],
            "round_count": 2,
        },
        image_embedding=[0.1] * 512,
        metadata={"task": pm.PUSH_TASK_TAG, "obs_rung": "1"},
    )

    # 1. When coords on (default):
    text_on = pm.format_push_preamble_text([rec], [0.85], obs_rung="1", preamble_coords="on")
    assert "start TCP  =" in text_on
    assert "round-1 target =" in text_on
    assert "your round-1 fingertip (TCP) target" in text_on
    assert "(40, 20, 50)" in text_on
    assert "X=50" in text_on
    assert "[coordinates omitted]" not in text_on

    # 2. When coords off:
    text_off, redactions = pm.format_push_preamble_text([rec], [0.85], obs_rung="1", preamble_coords="off", return_redactions=True)
    # Coordinate fields omitted
    assert "start TCP  =" not in text_off
    assert "round-1 target =" not in text_off
    # R9 neutral header verbatim
    assert "PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see the scene at its start, the outcome, and a short lesson you wrote afterwards. Use these to choose a better target for the current scene." in text_off
    assert "your round-1 fingertip (TCP) target" not in text_off

    # Lesson coordinates redacted with [coordinates omitted] at render time
    assert "(40, 20, 50)" not in text_off
    assert "X=50" not in text_off
    assert "Y=20" not in text_off
    assert "[coordinates omitted]" in text_off
    assert redactions == 3

    # Stored record lesson is UNCHANGED
    assert "(40, 20, 50)" in rec.text_lesson


def test_pin4c_placeholder_rejection(tmp_path):
    """rev1 MINOR: run_push_collect_loop with geometry='pin4c' rejects execution when constants are placeholder."""
    fake_env = _FakePushEnvP4c()
    b = WorkspaceBounds(x_bounds=(0.2, 0.8), y_bounds=(-0.4, 0.4), z_bounds=(-0.1, 0.5))
    lc = LevelConfig(level=99, name="push", control_mode=ControlMode.PUSH_WAYPOINT,
                     task_instruction_template="Push.", workspace_bounds=b)
    replay = ReplayBuffer(tmp_path / "replay")

    # 1. When PIN4C_DERIVED_FROM is None, raises RuntimeError
    orig_derived = C.PIN4C_DERIVED_FROM
    try:
        C.PIN4C_DERIVED_FROM = None
        with pytest.raises(RuntimeError, match="Pin-4c geometry constants are provisional placeholders"):
            run_push_collect_loop(
                env=fake_env,
                level_config=lc,
                teacher_url="http://mock:18888",
                replay=replay,
                num_episodes=1,
                geometry="pin4c",
                scripted_targets=[(40, 20, 50)],
                dump_images_root=str(tmp_path / "dumps"),
            )

        # 2. When PIN4C_DERIVED_FROM is set, execution proceeds
        C.PIN4C_DERIVED_FROM = "logs/wp3a_p4c_derived.json"
        summary = run_push_collect_loop(
            env=fake_env,
            level_config=lc,
            teacher_url="http://mock:18888",
            replay=replay,
            num_episodes=1,
            geometry="pin4c",
            scripted_targets=[(40, 20, 50)],
            dump_images_root=str(tmp_path / "dumps_set"),
        )
        assert summary["geometry"] == "pin4c"
    finally:
        C.PIN4C_DERIVED_FROM = orig_derived


def test_cube_relative_polar_command_num_envs_guard():
    """rev1 MINOR: CubeRelativePolarCommand raises NotImplementedError when num_envs > 1 or multiple env_ids."""
    cfg = CubeRelativePolarCommandCfg()
    cfg.object_name = "object"
    cfg.theta_range = (-1.0, 1.0)
    cfg.dist_range = (0.07, 0.10)

    # Multi-env env object
    multi_env = MagicMock()
    multi_env.num_envs = 4
    with pytest.raises(NotImplementedError, match="currently only supports num_envs=1"):
        CubeRelativePolarCommand(cfg=cfg, env=multi_env)

    # Single-env env object
    single_env = MagicMock()
    single_env.num_envs = 1
    cmd = CubeRelativePolarCommand(cfg=cfg, env=single_env)

    # Multi-env resample env_ids
    with pytest.raises(NotImplementedError, match="currently only supports single-env resets"):
        cmd._resample_command([0, 1, 2])


def test_reach_scan_dry_run_and_custom_configs():
    """AC2 / Rework 2: reach scan dry-run has 3 solvable configs and --configs parser works."""
    from scripts.diagnostics.wp3a_reach_scan_p4c import (
        DRY_RUN_CONFIGS,
        filter_config,
        parse_custom_configs,
    )

    # 1. Check dry run configs: exactly 3 solvable configs
    assert len(DRY_RUN_CONFIGS) == 3
    expected_configs = [
        (0.40, 0.10, 0, 0.10),
        (0.40, 0.10, 60, 0.07),
        (0.40, 0.10, -60, 0.07),
    ]
    assert DRY_RUN_CONFIGS == expected_configs

    # Verify each dry-run config is NOT skipped
    for cx, cy, th_deg, d in DRY_RUN_CONFIGS:
        reason = filter_config(cx, cy, th_deg, d)
        assert reason is None, f"Config {cx, cy, th_deg, d} was skipped for reason: {reason}"

    # 2. Check skip reasons:
    # x = 0.34 < 0.38 -> hand_keepout
    assert filter_config(0.34, 0.10, 0, 0.10) == "hand_keepout"
    # goal off table -> goal_off_table
    assert filter_config(0.40, 0.10, 0, 0.80) == "goal_off_table"

    # 3. Check custom configs parser
    parsed = parse_custom_configs("0.40, 0.10, 0, 0.10; 0.45, 0.15, -45, 0.07")
    assert parsed == [(0.40, 0.10, 0, 0.10), (0.45, 0.15, -45, 0.07)]

    # Malformed configs raise ValueError
    with pytest.raises(ValueError, match="Each config must have 4 comma-separated values"):
        parse_custom_configs("0.40, 0.10, 0")


