"""GUI: watch the REAL push from standby (PI, DISPLAY=:0).

Reset teleports the arm to standby, then — with NO idle gap — servos the LEFT
arm to the behind-cube approach point and drives through the cube toward the
goal, all via OSC (impedance control). This is the same hand-written geometry
the probe uses (NO model/VLM yet — I play the teacher by fixing cube+goal; the
move logic is OSC servoing to a target I compute with push_toward_base).

Watch: does the arm hold from standby (not collapse), reach behind the cube,
and push it? Prints live EE error + cube displacement.

Run:
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/diagnostics/wp3a_watch_push.py
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--settle", type=int, default=140)
parser.add_argument("--push", type=int, default=200)
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
from isaaclab.utils.math import subtract_frame_transforms, combine_frame_transforms
import isaaclab.sim as sim_utils
from isaaclab.markers import VisualizationMarkers, VisualizationMarkersCfg
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import (
    base_frame_target_from_world, push_toward_base,
)

GID = "Isaac-AionGenos-WP1-Push-v0"
LIMITS = [40., 40., 27., 27., 7., 7., 7.]


def _p(m): print(f"[PUSH] {m}", flush=True)


def main():
    cfg = parse_env_cfg(GID, num_envs=1)
    for term in ("left_ee_pose", "right_ee_pose"):
        c = getattr(cfg.commands, term, None)
        if c is not None and hasattr(c, "debug_vis"):
            c.debug_vis = False
    env = gym.make(GID, cfg=cfg, render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    cube = u.scene["object"]
    ee_idx = r.body_names.index("openarm_left_hand")
    left_ids, _ = r.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    lim = torch.tensor(LIMITS, device=u.device)
    act_dim = env.action_space.shape[-1]

    # markers: RED = approach point, GREEN = goal
    m_appr = VisualizationMarkers(VisualizationMarkersCfg(prim_path="/Visuals/Approach",
        markers={"s": sim_utils.SphereCfg(radius=0.025,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.0, 0.0)))}))
    m_goal = VisualizationMarkers(VisualizationMarkersCfg(prim_path="/Visuals/Goal",
        markers={"s": sim_utils.SphereCfg(radius=0.025,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.0, 1.0, 0.0)))}))

    env.reset(seed=4700)
    cube_w = cube.data.root_pos_w[0, :3].clone()
    cube_b = base_frame_target_from_world(u, cube_w)
    goal_b = u.command_manager.get_term("left_ee_pose").command[0, :3].clone()
    approach_b, info = push_toward_base(cube_b, goal_b)

    rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
    appr_w, _ = combine_frame_transforms(rp, rq, approach_b.unsqueeze(0))
    goal_w, _ = combine_frame_transforms(rp, rq, goal_b.unsqueeze(0))
    m_appr.visualize(translations=appr_w)
    m_goal.visualize(translations=goal_w)

    _p(f"standby EE_z={float(r.data.body_pos_w[0,ee_idx,2]):.3f}; cube_w={[round(float(v),3) for v in cube_w]}")
    _p(f"approach_b={[round(float(v),3) for v in approach_b]} goal_b={[round(float(v),3) for v in goal_b]}")
    _p("=== GUI: RED=approach(behind cube), GREEN=goal. Phase1 servo to RED, Phase2 push toward GREEN ===")

    def action_to(tgt_b):
        a = torch.zeros((u.num_envs, act_dim), device=u.device)
        a[:, 0:3] = tgt_b
        a[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            a[:, 7:13] = 300.0
        return a

    cube0 = cube.data.root_pos_w[0, :3].clone()
    phase, step = "approach", 0
    a = action_to(approach_b)
    while simulation_app.is_running():
        env.step(a)
        m_appr.visualize(translations=appr_w); m_goal.visualize(translations=goal_w)
        step += 1
        ee = r.data.body_pos_w[0, ee_idx, :3]
        if phase == "approach":
            d = float(torch.norm(ee - appr_w[0]) * 100)
            if step % 20 == 0:
                _p(f"[approach] step {step}: EE→RED err={d:.1f}cm EE_z={float(ee[2]):.3f}")
            if step >= args_cli.settle:
                phase, step = "push", 0
                a = action_to(goal_b)
                _p("--- switch to PUSH (drive toward GREEN goal) ---")
        else:
            moved = float(torch.norm(cube.data.root_pos_w[0, :3] - cube0) * 100)
            tau = float((r.data.applied_torque[0, lid].abs() / lim).max())
            if step % 20 == 0:
                _p(f"[push] step {step}: cube_moved={moved:.1f}cm τ/limit={tau:.2f}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
