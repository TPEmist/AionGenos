"""WP1-③a — torque-comfortable contact-band sweep (= redefined reachability).

z from 0.30 downward in 2.5cm steps; XY at 3 points (Pin-4 center + two far
corners — reach demand rises with extension, so the band's lower edge is a
function of XY; the task needs "all sampled XY hold"). Each (x,y,z): servo
to it + hold ≥30 steps; record servo-phase and hold-phase max(τ/limit).

Band lower edge = the lowest z whose HOLD-phase max(τ/limit) ≤ 0.85 at ALL
XY points simultaneously.

Verdict per cell (mechanical, boundary in code — Rule 2 family): <0.85
FEASIBLE / [0.85,1.0) TIGHT / >=1.0 SATURATED.

Runs on the push env (Pin-7 working init). Effort limits real hw
[40,40,27,27,7,7,7]. Flushed; caller reads [TB].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--hold-steps", type=int, default=30)
parser.add_argument("--settle", type=int, default=90)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import base_frame_target_from_world

LIMITS = [40., 40., 27., 27., 7., 7., 7.]


def _classify(r):
    return "FEASIBLE" if r < 0.85 else ("TIGHT" if r < 1.0 else "SATURATED")


def _p(m):
    print(f"[TB] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env = gym.make(gym_id, cfg=parse_env_cfg(gym_id, num_envs=1), render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    left_ids, _ = robot.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    lim = torch.tensor(LIMITS, device=u.device)
    act_dim = env.action_space.shape[-1]

    # 3 XY points: center + two far corners of the Pin-4 region (x .40-.60,
    # y ±.15) reachable by the LEFT arm (left arm favours +y side).
    xy_points = [("center", 0.50, 0.05), ("far-x", 0.60, 0.05), ("far-corner", 0.55, 0.15)]
    zs = [round(0.30 - 0.025 * k, 3) for k in range(11)]  # 0.30 .. 0.05

    def servo_and_hold(x, y, z):
        env.reset(seed=4700)
        tgt = torch.tensor([x, y, z], device=u.device)
        tb = base_frame_target_from_world(u, tgt)
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 0:3] = tb
        action[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            action[:, 7:13] = 300.0
        servo_peak = 0.0; hold_peak = 0.0; dmin = 1e9
        for i in range(args_cli.settle):
            env.step(action)
            r = float((robot.data.applied_torque[0, lid].abs() / lim).max())
            servo_peak = max(servo_peak, r)
            ee = robot.data.body_pos_w[0, ee_idx, :3]
            dmin = min(dmin, float(torch.norm(ee - tgt) * 100))
        for i in range(args_cli.hold_steps):
            env.step(action)
            r = float((robot.data.applied_torque[0, lid].abs() / lim).max())
            hold_peak = max(hold_peak, r)
        return dmin, servo_peak, hold_peak

    band_edge = {}  # xy label -> lowest z with hold<=0.85
    for label, x, y in xy_points:
        _p(f"=== XY {label} (x={x}, y={y}) ===")
        edge = None
        for z in zs:
            dmin, sp, hp = servo_and_hold(x, y, z)
            _p(f"  z={z:.3f}: min_err={dmin:.1f}cm servo_peak={sp:.2f} hold_peak={hp:.2f} [{_classify(hp)}]")
            if hp <= 0.85 and dmin < 6.0:
                edge = z  # keep lowering; edge = lowest still-OK z
        band_edge[label] = edge
        _p(f"  {label} lowest hold<=0.85 z = {edge}")

    edges = [v for v in band_edge.values() if v is not None]
    _p(f"band edges by XY: {band_edge}")
    if len(edges) == len(xy_points):
        # all-XY-satisfied lower edge = the HIGHEST of the per-XY lowest-OK z
        # (the most restrictive corner sets the band bottom for the whole region)
        all_ok_edge = max(edges)
        _p(f"ALL-XY torque-comfortable lower edge = z {all_ok_edge:.3f} "
           f"(most-restrictive corner) → cube contact height should sit here + margin")
    else:
        missing = [k for k, v in band_edge.items() if v is None]
        _p(f"NO comfortable band at some XY: {missing} never held <=0.85 in range → "
           f"even z=0.30 saturates there; region may need shrinking or table raised a lot")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
