"""WP1-③a — BI working-pose servo verification + repair-spec data (PI spec).

On the BiLeftPosed env (BI robot, left OSC term, LEFT arm at a BI-legal
raised working pose):
  1. NEAR target (EE_start ± ~12cm): does the left EE servo? (the UNI-
     equivalent "near servo" proposition)
  2a. per-joint |τ|/limit ratio time-series — is any joint riding its
      limit even for a NEAR target? (zero margin → push contact re-saturates)
  2b. effort demand to reach TABLE height (z≈0.03) — the actual ③a motion;
      near-servo passing ≠ down-to-table passing. Geometry-vs-torque split.

Effort limits (verified real hw, openarm.py datasheets): [40,40,27,27,7,7,7].
Flushed; caller reads [V].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import base_frame_target_from_world


def _p(m):
    print(f"[V] {m}", flush=True)


def _servo(env, u, robot, ee_idx, left_ids, tgt_w, steps=150):
    act_dim = env.action_space.shape[-1]
    tgt_b = base_frame_target_from_world(u, tgt_w)
    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    action[:, 0:3] = tgt_b
    action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)
    if act_dim >= 13:
        action[:, 7:13] = 300.0
    limits = torch.tensor([40., 40., 27., 27., 7., 7., 7.], device=u.device)
    dmin = 1e9
    max_ratio_final = None
    for i in range(steps):
        env.step(action)
        ee = robot.data.body_pos_w[0, ee_idx, :3]
        dmin = min(dmin, float(torch.norm(ee - tgt_w).item()) * 100)
        if i >= steps - 10:  # last-10-step ratio (settle)
            tau = robot.data.applied_torque[0, torch.tensor(left_ids, device=u.device)].abs()
            ratio = (tau / limits)
            max_ratio_final = [round(float(x), 2) for x in ratio.tolist()]
    ee_f = robot.data.body_pos_w[0, ee_idx, :3]
    return dmin, float(torch.norm(ee_f - tgt_w) * 100), max_ratio_final


def main() -> None:
    gym_id = "Isaac-AionGenos-OSC-BiLeftPosed-v0"
    env = gym.make(gym_id, cfg=parse_env_cfg(gym_id, num_envs=1), render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    left_ids, _ = robot.find_joints("openarm_left_joint.*")
    env.reset(seed=4700)
    ee0 = robot.data.body_pos_w[0, ee_idx, :3].clone()
    _p(f"EE_start(working pose) = {[round(x,3) for x in ee0.tolist()]}")

    # 1 + 2a: NEAR target (start + 12cm forward/side, same height)
    near = ee0 + torch.tensor([0.12, -0.05, 0.0], device=u.device)
    dmin, dfin, ratio = _servo(env, u, robot, ee_idx, left_ids, near)
    _p(f"NEAR target {[round(x,3) for x in near.tolist()]}: min_err={dmin:.1f}cm final={dfin:.1f}cm")
    _p(f"NEAR per-joint |τ|/limit (last steps) = {ratio}  (>=~0.95 = riding limit)")
    near_ok = dmin < 5.0
    near_riding = ratio is not None and max(ratio) >= 0.95
    _p(f"NEAR servo: {'PASS' if near_ok else 'FAIL'}; margin: {'ZERO (a joint rides limit)' if near_riding else 'healthy'}")

    # 2b: down-to-table target (z≈0.03) — the real ③a motion
    env.reset(seed=4700)
    table = torch.tensor([float(ee0[0]), float(ee0[1]), 0.03], device=u.device)
    dmin2, dfin2, ratio2 = _servo(env, u, robot, ee_idx, left_ids, table)
    _p(f"TABLE target {[round(x,3) for x in table.tolist()]}: min_err={dmin2:.1f}cm final={dfin2:.1f}cm")
    _p(f"TABLE per-joint |τ|/limit (last steps) = {ratio2}")
    table_ok = dmin2 < 5.0
    table_sat = ratio2 is not None and max(ratio2) >= 0.95
    _p(f"TABLE reach: {'PASS' if table_ok else 'FAIL'}; {'SATURATED (torque-limited, not geometry)' if table_sat else 'not saturated'}")

    # branch verdict
    if near_ok and table_ok and not near_riding:
        v = "BRANCH-1: near ✓ + table ✓ + margin healthy → fix = init pose one-liner (Pin-7)"
    elif near_ok and not table_ok and table_sat:
        v = "BRANCH-2: near ✓ but table SATURATES → init + effort-limit/posture (7N·m is real hw)"
    elif not near_ok:
        v = "BRANCH-3: near FAILS → mechanism verdict overturned, re-discuss"
    else:
        v = f"MIXED: near_ok={near_ok} table_ok={table_ok} near_riding={near_riding} table_sat={table_sat}"
    _p(f"VERDICT {v}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
