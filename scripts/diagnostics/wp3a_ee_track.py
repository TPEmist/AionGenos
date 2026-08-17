"""WP1-③a EE-tracking probe — where does the EE actually GO vs the target?

Answers the user's kinematic question with NUMBERS (not a GIF read): for a
few targets, print the commanded world pose, the base-frame target actually
sent, the robot ROOT pose, and where the left EE settles (world). If the EE
runs FORWARD/straight toward a NEAR+LOW target instead of bending in, the
numbers show it (EE settles far in +x, or at the wrong xy) — a controller/
IK-direction problem, not reach. Also prints joint angles at settle so a
"straight arm" vs "bent arm" is legible numerically (near-zero elbow = straight).

Flushed; caller reads [TRACK].
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
    print(f"[TRACK] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    left_jids = [0, 2, 4, 6, 8, 10, 12]  # from inert_diag STEP1
    act_dim = env.action_space.shape[-1]
    half = act_dim // 2

    env.reset(seed=4700)
    root_w = robot.data.root_pos_w[0, :3]
    _p(f"robot ROOT world pos = {[round(x,3) for x in root_w.tolist()]}")
    ee_start = robot.data.body_pos_w[0, ee_idx, :3]
    _p(f"left EE start world = {[round(x,3) for x in ee_start.tolist()]}")

    # A near+low target (user says this should need a BENT elbow) and a
    # comfortable mid target, for contrast.
    for label, tgt_w in [
        ("NEAR+LOW (0.50,0,0.05)", torch.tensor([0.50, 0.0, 0.05], device=u.device)),
        ("MID      (0.50,0,0.30)", torch.tensor([0.50, 0.0, 0.30], device=u.device)),
        ("FAR+MID  (0.65,0,0.30)", torch.tensor([0.65, 0.0, 0.30], device=u.device)),
    ]:
        env.reset(seed=4700)
        tgt_b = base_frame_target_from_world(u, tgt_w)
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 0:3] = tgt_b
        action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)
        if half > 7:
            action[:, 7:half] = 300.0
        for _ in range(120):
            env.step(action)
        ee_w = robot.data.body_pos_w[0, ee_idx, :3]
        err = float(torch.norm(ee_w - tgt_w).item()) * 100.0
        jpos = robot.data.joint_pos[0, left_jids]
        _p(f"{label}: tgt_world={[round(x,3) for x in tgt_w.tolist()]} "
           f"tgt_base={[round(x,3) for x in tgt_b.tolist()]}")
        _p(f"    EE settled world={[round(x,3) for x in ee_w.tolist()]}  err={err:.1f}cm")
        _p(f"    left joint angles(rad)={[round(float(a),2) for a in jpos.tolist()]}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
