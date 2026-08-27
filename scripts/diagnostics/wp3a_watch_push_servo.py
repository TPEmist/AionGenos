"""GUI: watch the carrot-transport push servo (PI, DISPLAY=:0) — see WHERE the
arm gets stuck (is it stuck below the table on the way to approach, as the PI
suspects, or something else?).

Same carrot servo as execute_push_segment, GUI open. RED sphere = approach
point (behind cube, where EE must reach). Prints live EE position + err each
few steps. Watch the arm's path from standby to the red sphere.

Run:
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/diagnostics/wp3a_watch_push_servo.py --lead 0.03
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--lead", type=float, default=0.03)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import combine_frame_transforms
import isaaclab.sim as sim_utils
from isaaclab.markers import VisualizationMarkers, VisualizationMarkersCfg
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import push_segment_from_waypoint

GID = "Isaac-AionGenos-WP1-Push-v0"
LIMITS = [40., 40., 27., 27., 7., 7., 7.]


def _p(m): print(f"[WATCH] {m}", flush=True)


def main():
    cfg = parse_env_cfg(GID, num_envs=1)
    for t in ("left_ee_pose", "right_ee_pose"):
        c = getattr(cfg.commands, t, None)
        if c is not None and hasattr(c, "debug_vis"):
            c.debug_vis = False
    env = gym.make(GID, cfg=cfg, render_mode=None)
    iface = IsaacLabEnvInterface(env)
    u = env.unwrapped
    r = iface.robot
    ee_idx = iface.left_body_idx
    left_ids, _ = r.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    lim = torch.tensor(LIMITS, device=u.device)
    act_dim = env.action_space.shape[-1]
    term = u.action_manager._terms.get("left_arm_action")

    marker = VisualizationMarkers(VisualizationMarkersCfg(prim_path="/Visuals/Approach",
        markers={"s": sim_utils.SphereCfg(radius=0.03,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.0, 0.0)))}))

    env.reset(seed=4700)
    for _ in range(10):
        env.step(torch.zeros((1, act_dim), device=u.device))
    root = r.data.root_pos_w[0, :3]
    cube_b = iface.get_cube_pose_b()
    goal_b = iface.get_goal_pose_b()
    cube_t = torch.tensor(cube_b, dtype=torch.float32)
    wp = torch.tensor([goal_b[0], goal_b[1], cube_b[2]], dtype=torch.float32)
    approach_b, _, contact_quat_b, _ = push_segment_from_waypoint(cube_t, wp)
    tb = approach_b.to(u.device)
    qb = contact_quat_b.to(u.device)
    rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
    appr_w, _ = combine_frame_transforms(rp, rq, tb.unsqueeze(0))
    marker_pos = appr_w

    _p(f"RED sphere = approach point (base {[round(float(v),3) for v in tb]}); watch the arm reach it.")
    _p(f"contact orientation (f push_dir) = {[round(float(v),3) for v in qb]} (NOT identity/gripper-sky)")
    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    action[:, 3:7] = qb   # primitive contact orientation
    if act_dim >= 13:
        action[:, 7:10] = 300.0   # position stiffness (firm)
        action[:, 10:13] = 60.0   # orientation stiffness (soft)

    step = 0
    while simulation_app.is_running():
        ee_b = r.data.body_pos_w[0, ee_idx, :3] - root
        d = tb - ee_b
        dist = float(torch.norm(d))
        setpoint = tb if dist <= args_cli.lead else ee_b + d / dist * args_cli.lead
        action[:, 0:3] = setpoint
        env.step(action)
        marker.visualize(translations=marker_pos)
        step += 1
        if step % 15 == 0:
            ee_w = r.data.body_pos_w[0, ee_idx, :3]
            err = float(torch.norm((ee_w - root) - tb) * 100)
            pre = float((term._joint_efforts[0].abs() / lim).max()) if term is not None and hasattr(term, "_joint_efforts") else -1
            _p(f"s{step}: EE_world_z={float(ee_w[2]):.3f} err_to_approach={err:.1f}cm τpre={pre:.2f} (table top≈0.994)")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
