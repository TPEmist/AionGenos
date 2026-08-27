"""Diagnose why the carrot transport servo doesn't move the arm to approach.

Per-5-step trace (PI spec): ee_b, written setpoint (full vec), action vector
(all slots: pose + stiffness), τ_cmd/limit, and servo_err computed in BOTH
frames (base-vs-base AND world-vs-base) so the 66 vs 27 discrepancy is one
glance to resolve.

Pre-committed 3-branch:
  A. setpoint has |Δz|≈0.65 OR a cross-frame compare shows up → FRAME bug.
  B. stiffness slots == 0 → FORCE bug (impedance slots not written).
  C. frame ok + force ok + EE crawling correctly → lead/stiffness tuning.

Headless. Reads [TRACE].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=150)
parser.add_argument("--lead", type=float, default=0.03)
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
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import push_segment_from_waypoint

GID = "Isaac-AionGenos-WP1-Push-v0"
LIMITS = [40., 40., 27., 27., 7., 7., 7.]


def _p(m): print(f"[TRACE] {m}", flush=True)


def main():
    env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
    iface = IsaacLabEnvInterface(env)
    u = env.unwrapped
    r = iface.robot
    ee_idx = iface.left_body_idx
    left_ids, _ = r.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    lim = torch.tensor(LIMITS, device=u.device)
    act_dim = env.action_space.shape[-1]
    term = u.action_manager._terms.get("left_arm_action")

    env.reset(seed=4700)
    for _ in range(10):
        env.step(torch.zeros((1, act_dim), device=u.device))

    root = r.data.root_pos_w[0, :3]
    # compute approach the SAME way push_collect does
    cube_b = iface.get_cube_pose_b()
    goal_b = iface.get_goal_pose_b()
    cube_t = torch.tensor(cube_b, dtype=torch.float32)
    wp = torch.tensor([goal_b[0], goal_b[1], cube_b[2]], dtype=torch.float32)
    approach_b, target_b, contact_quat_b, info = push_segment_from_waypoint(cube_t, wp)
    tb = approach_b.to(u.device)
    qb = contact_quat_b.to(u.device)
    _p(f"approach_b(target)={[round(float(v),3) for v in tb]} cube_b={[round(v,3) for v in cube_b]}")
    _p(f"contact_quat_b={[round(float(v),3) for v in qb]} (f(push_dir), NOT identity)")
    _p(f"action_dim={act_dim} lead={args_cli.lead}")

    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    action[:, 3:7] = qb   # primitive-computed contact orientation
    if act_dim >= 13:
        action[:, 7:10] = 300.0   # position stiffness (firm)
        action[:, 10:13] = 60.0   # orientation stiffness (soft)

    for step in range(args_cli.steps):
        ee_w = r.data.body_pos_w[0, ee_idx, :3]
        ee_b_transl = ee_w - root                       # translation-only base
        # carrot setpoint (as execute_push_segment does)
        d = tb - ee_b_transl
        dist = float(torch.norm(d))
        setpoint = tb if dist <= args_cli.lead else ee_b_transl + d / dist * args_cli.lead
        action[:, 0:3] = setpoint
        env.step(action)

        if step % 5 == 0 or step == args_cli.steps - 1:
            # τ pre-clip
            pre = float((term._joint_efforts[0].abs() / lim).max()) if term is not None and hasattr(term, "_joint_efforts") else -1
            post = float((r.data.applied_torque[0, lid].abs() / lim).max())
            # servo_err in BOTH frames
            ee_w2 = r.data.body_pos_w[0, ee_idx, :3]
            ee_b2 = ee_w2 - root
            err_base = float(torch.norm(ee_b2 - tb) * 100)      # base-vs-base (correct)
            err_world = float(torch.norm(ee_w2 - tb) * 100)     # world-vs-base (cross-frame, wrong)
            sp = [round(float(v), 3) for v in setpoint]
            _p(f"s{step:3d}: ee_b={[round(float(v),3) for v in ee_b2]} setpoint={sp} "
               f"stiff={float(action[0,7]):.0f} τpre={pre:.2f} τpost={post:.2f} "
               f"err_base={err_base:.1f} err_world={err_world:.1f}")

    _p("=== 3-branch check: |Δz| in setpoint? stiffness=0? which err matches 66? ===")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
