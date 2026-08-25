"""WP1-③a — verify the REAL rollout question: after reset teleports the arm to
standby, does the FIRST OSC servo command hold the arm and start pushing?

The "standby collapses under zero-action" finding is a NON-problem for real
rollout: rollout never sends zero action — every step has a teacher command,
so OSC drives the arm from the teleport moment on (no idle gap to collapse in).
The real question (PI): teleport → send a push servo → does the arm stabilise
from standby and move the cube?

Uses the push_s3a env (real OSC bimanual, real cube-on-table, Pin-7a standby,
Pin-4a goal). Reads cube + goal, computes the behind-cube approach with
push_toward_base, servos the LEFT arm there, then drives through the cube
toward the goal. Records: does the EE reach the approach point, does |τ|/limit
stay in budget, does the cube MOVE.

Reads [PFS]. Headless.
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--settle", type=int, default=120)
parser.add_argument("--push", type=int, default=150)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np
import torch
import gymnasium as gym
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import subtract_frame_transforms
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import (
    base_frame_target_from_world, push_toward_base,
)

GID = "Isaac-AionGenos-WP1-Push-v0"
LIMITS = [40., 40., 27., 27., 7., 7., 7.]


def _p(m): print(f"[PFS] {m}", flush=True)


def main():
    env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    cube = u.scene["object"]
    ee_idx = r.body_names.index("openarm_left_hand")
    left_ids, _ = r.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    lim = torch.tensor(LIMITS, device=u.device)
    act_dim = env.action_space.shape[-1]

    env.reset(seed=4700)
    ee0 = r.data.body_pos_w[0, ee_idx, :3].clone()
    _p(f"reset→standby: L-EE world={[round(float(v),3) for v in ee0]} (teleport target)")

    # cube + goal (base frame). goal = left_ee_pose command term.
    cube_w = cube.data.root_pos_w[0, :3].clone()
    cube_b = base_frame_target_from_world(u, cube_w)
    goal_term = u.command_manager.get_term("left_ee_pose")
    goal_b = goal_term.command[0, :3].clone()  # base-frame goal (pose_command_b)
    approach_b, info = push_toward_base(cube_b, goal_b)
    _p(f"cube_w={[round(float(v),3) for v in cube_w]} goal_b={[round(float(v),3) for v in goal_b]}")
    _p(f"approach_b (behind cube)={[round(float(v),3) for v in approach_b]} cube→goal={info['cube_goal_dist_m']:.3f}m")

    def servo_to(tgt_b, steps, phase):
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 0:3] = tgt_b
        action[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            action[:, 7:13] = 300.0
        peak = 0.0; dmin = 1e9
        for i in range(steps):
            env.step(action)
            ee = r.data.body_pos_w[0, ee_idx, :3]
            tgt_w_now = None
            dmin = min(dmin, float(torch.norm(ee - _b2w(tgt_b)) * 100))
            if i >= steps - 40:
                pk = float((r.data.applied_torque[0, lid].abs() / lim).max())
                peak = max(peak, pk)
        return dmin, peak

    def _b2w(pb):
        # base→world for distance measurement
        from isaaclab.utils.math import combine_frame_transforms
        rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
        pw, _ = combine_frame_transforms(rp, rq, pb.unsqueeze(0))
        return pw[0]

    # PHASE 1: from standby, servo to the behind-cube approach point
    d_appr, peak_appr = servo_to(approach_b, args_cli.settle, "approach")
    ee_after = r.data.body_pos_w[0, ee_idx, :3].clone()
    held = float(ee_after[2]) > 0.99  # did the arm stay up (not collapse below table)?
    _p(f"PHASE1 approach: min_err={d_appr:.1f}cm peak τ/limit={peak_appr:.2f} "
       f"EE_z={float(ee_after[2]):.3f} ({'HELD up' if held else 'COLLAPSED below table'})")

    # PHASE 2: drive through the cube toward the goal (push)
    cube_before = cube.data.root_pos_w[0, :3].clone()
    d_push, peak_push = servo_to(goal_b, args_cli.push, "push")
    cube_after = cube.data.root_pos_w[0, :3].clone()
    cube_moved = float(torch.norm(cube_after - cube_before) * 100)
    _p(f"PHASE2 push: peak τ/limit={peak_push:.2f} cube_moved={cube_moved:.1f}cm")

    # verdict
    peak_all = max(peak_appr, peak_push)
    reached = d_appr < 6.0
    _p("=== VERDICT ===")
    if held and reached and cube_moved > 2.0 and peak_all <= 1.0:
        _p(f"PASS: from standby, first servo HELD the arm + reached cube + pushed it "
           f"{cube_moved:.1f}cm (τ/limit {peak_all:.2f}). standby-collapse was a "
           f"non-problem; real rollout works. → proceed to Pin-9a/smoke.")
    else:
        _p(f"NEEDS WORK: held={held} reached_approach={reached} "
           f"cube_moved={cube_moved:.1f}cm peak_τ={peak_all:.2f}. "
           f"If not held → standby genuinely needs active maintenance; if reached "
           f"but no push → contact/force issue; if τ>1 → saturation.")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
