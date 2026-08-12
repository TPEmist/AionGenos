"""WP1-③a scene+physics + HOLD gate smoke — frame-gated (Rule 5).

Order (PI spec): scene+physics acceptance (already GREEN) → this uses the
push_toward PRIMITIVE (behind-cube approach, base-frame target via the frame
gate) to drive the pushing EE, then tests the ≥30-step HOLD gate on a
correct-frame target. No hand-written world pose_abs anywhere (Rule 5).

All prints flushed; caller reads [PUSH] VERDICT.
"""
from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--hold-steps", type=int, default=30)
parser.add_argument("--hold-tol-cm", type=float, default=5.0)
parser.add_argument("--servo-steps", type=int, default=200)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import (
    assert_command_frame, base_frame_target_from_world, push_toward_base,
)


def _p(m):
    print(f"[PUSH] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    u = env.unwrapped
    _p(f"env made ({gym_id})")

    cube = u.scene["object"]
    m = float(cube.root_physx_view.get_masses()[0].sum().item())
    _p(f"cube mass={m:.4f} kg (dynamic: {m > 0})")

    obs, _ = env.reset(seed=4700)
    assert_command_frame(u)  # Rule 5 boot assert
    _p("reset OK + frame gate asserted")

    robot = u.scene["robot"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    act_dim = env.action_space.shape[-1]
    half = act_dim // 2

    cube0_w = cube.data.root_pos_w[0, :3].clone()
    # cube → base frame (sanctioned util). goal = left_ee_pose command,
    # re-purposed as the CUBE goal; `.command` is BASE frame (Rule 5 source,
    # the frame #2 verified — NOT pose_command_w which reads 0 pre-update).
    cube0_b = base_frame_target_from_world(u, cube0_w)
    goal_b = u.command_manager.get_term("left_ee_pose").command[0, :3].clone()
    _p(f"cube_b={[round(x,3) for x in cube0_b.tolist()]}  goal_b(.command)={[round(x,3) for x in goal_b.tolist()]}")

    # push_toward primitive, all base frame: behind-cube approach point.
    tgt_b, info = push_toward_base(cube0_b, goal_b)
    _p(f"push_toward: approach_b={[round(x,3) for x in info['approach_b']]} cube→goal={info['cube_goal_dist_m']*100:.1f}cm")

    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    action[:, 0:3] = tgt_b
    action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)
    if half > 7:
        action[:, 7:half] = 300.0  # left-arm stiffness

    hold_run = 0; hold_ok = False; dmin = 1e9
    for i in range(args_cli.servo_steps):
        env.step(action)
        ee_b = robot.data.body_pos_w[0, ee_idx, :3] - robot.data.root_pos_w[0, :3]
        d_cm = float(torch.norm(ee_b - tgt_b).item()) * 100.0
        dmin = min(dmin, d_cm)
        hold_run = hold_run + 1 if d_cm <= args_cli.hold_tol_cm else 0
        if hold_run >= args_cli.hold_steps:
            hold_ok = True
        if i % 40 == 0 or i == args_cli.servo_steps - 1:
            _p(f"step {i}: EE→approach {d_cm:.2f}cm hold_run={hold_run}")

    cube_moved = float(torch.norm(cube.data.root_pos_w[0, :3] - cube0_w).item()) * 100.0
    _p(f"cube moved {cube_moved:.2f}cm (contact: {cube_moved > 1.0})")
    _p(f"min EE→approach {dmin:.2f}cm; hold≥{args_cli.hold_steps} within {args_cli.hold_tol_cm}cm: {hold_ok}")
    _p(f"VERDICT {'PASS' if hold_ok else 'FAIL-HOLD'}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
