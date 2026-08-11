"""WP1-③a scene + physics + HOLD acceptance smoke.

Before any teacher scaffolding: confirm the push scene (1) boots with the
dynamic cube, (2) the cube is a real dynamic RigidObject (has mass, will
move under contact), and (3) the OSC controller HOLDS the EE at a contact
target for >= N steps (Pin 1 gate — the fix for #2's reach-then-drift).

All prints flushed; caller reads [PUSH] VERDICT.

Usage:
  isaaclab.sh -p scripts/diagnostics/wp3a_push_smoke.py --headless --enable_cameras
"""
from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--hold-steps", type=int, default=30)   # Pin 1: N=30
parser.add_argument("--hold-tol-cm", type=float, default=5.0)
parser.add_argument("--servo-steps", type=int, default=150)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


def _p(m):
    print(f"[PUSH] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    u = env.unwrapped
    _p(f"env made ({gym_id})")

    # (2) cube is a real dynamic RigidObject
    cube = u.scene["object"]
    m = float(cube.root_physx_view.get_masses()[0].sum().item())
    _p(f"cube present: mass={m:.4f} kg (dynamic: {m > 0})")

    obs, _ = env.reset(seed=4700)
    _p("reset OK")
    cube0 = cube.data.root_pos_w[0, :3].clone()
    _p(f"cube init pos_w = {cube0.tolist()}")

    robot = u.scene["robot"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    act_dim = env.action_space.shape[-1]

    # Drive the left EE toward the cube (a real contact target) and hold.
    # Target = cube position + a small approach offset; feed into pose_abs.
    tgt = cube0.clone()
    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    # single-arm action layout mirrors s0 (pose_abs[7] + stiffness[6]); the
    # push env's left arm term — set its pose_abs pos to the cube.
    # NOTE: action here is the FULL bimanual action; left arm occupies the
    # first half. We set the left-arm pose_abs target to the cube pose.
    half = act_dim // 2
    action[:, 0:3] = tgt
    action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)  # identity quat
    if half > 7:
        action[:, 7:half] = 300.0  # left stiffness

    hold_run = 0
    hold_ok = False
    dmin = 1e9
    for i in range(args_cli.servo_steps):
        env.step(action)
        ee = robot.data.body_pos_w[0, ee_idx, :3]
        d_cm = float(torch.norm(ee - tgt).item()) * 100.0
        dmin = min(dmin, d_cm)
        if d_cm <= args_cli.hold_tol_cm:
            hold_run += 1
            if hold_run >= args_cli.hold_steps:
                hold_ok = True
        else:
            hold_run = 0
        if i % 30 == 0 or i == args_cli.servo_steps - 1:
            _p(f"step {i}: EE→target {d_cm:.2f}cm  hold_run={hold_run}")

    cube_moved = float(torch.norm(cube.data.root_pos_w[0, :3] - cube0).item()) * 100.0
    _p(f"cube moved {cube_moved:.2f} cm during servo (contact made: {cube_moved > 1.0})")
    _p(f"min EE→target {dmin:.2f}cm; hold >= {args_cli.hold_steps} steps within "
       f"{args_cli.hold_tol_cm}cm: {hold_ok}")
    _p(f"VERDICT {'PASS' if hold_ok else 'FAIL-HOLD'} — "
       f"{'scene boots, cube dynamic, EE holds at contact target' if hold_ok else 'holds insufficient — tune stiffness before ③b'}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
