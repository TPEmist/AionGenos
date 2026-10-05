"""Watch the reach-confirm probe LIVE (GUI) so the PI can SEE why a Pin-4a
target reads 'stuck': is the arm frozen mid-path (DiffIK convergence / local
minimum from the tucked rest) or genuinely at kinematic full-stretch?

Same instrument as wp3a_reach_confirm_newgeom (L2 DiffIK, orientation-free,
new geometry) but with the GUI open and ONE target at a time. A RED sphere
marks the target (READ FROM CFG Pin-4a range — no hardcoded copy). The arm
servos from its rest toward the target; watch whether it stalls short or
reaches full extension. Prints live EE error each burst.

Run:
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/diagnostics/wp3a_reach_watch.py --arm left --tx 0.34 --ty 0.15
  (tx/ty default to the NEAR corner of Pin-4a; try the far corner --tx 0.54)
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--arm", choices=["left", "right"], default="left")
parser.add_argument("--tx", type=float, default=None, help="target x (default: Pin-4a near edge)")
parser.add_argument("--ty", type=float, default=None, help="target y (default: +0.15)")
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
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.pipeline.stage2_attempt import BimanualCommand, MetricCommand
from aiongenos.tasks.WP1_contact_testbed.push_s3a_cfg import _CUBE_REST_Z, _ROBOT_BASE_Z

GID = "Isaac-AionGenos-WP1-ReachProbe-NewGeom-v0"
Z_CONTACT_B = round(_CUBE_REST_Z - _ROBOT_BASE_Z, 4)


def _p(m): print(f"[WATCH] {m}", flush=True)


def main():
    cfg = parse_env_cfg(GID, num_envs=1)
    gr = cfg.commands.left_ee_pose.ranges
    xlo, xhi = gr.pos_x
    ylo, yhi = gr.pos_y
    tx = args_cli.tx if args_cli.tx is not None else xlo   # near edge
    ty = args_cli.ty if args_cli.ty is not None else yhi
    for term in ("left_ee_pose", "right_ee_pose"):
        c = getattr(cfg.commands, term, None)
        if c is not None and hasattr(c, "debug_vis"):
            c.debug_vis = False

    env = gym.make(GID, cfg=cfg, render_mode=None)
    u = env.unwrapped
    iface = IsaacLabEnvInterface(env)
    r = iface.robot
    body_idx = iface.left_body_idx if args_cli.arm == "left" else iface.right_body_idx

    markers = VisualizationMarkers(VisualizationMarkersCfg(
        prim_path="/Visuals/ReachTarget",
        markers={"sphere": sim_utils.SphereCfg(radius=0.03,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.0, 0.0)))}))

    iface.reset(seed=4700)
    for _ in range(5):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))

    def ee_b():
        rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
        ew = r.data.body_pos_w[0:1, body_idx, :3]
        b, _ = subtract_frame_transforms(rp, rq, ew)
        return b[0].cpu().numpy()

    # target marker in world
    rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
    tgt_w, _ = combine_frame_transforms(rp, rq, torch.tensor([[tx, ty, Z_CONTACT_B]], device=u.device))
    marker_pos = tgt_w

    _p(f"arm={args_cli.arm} target(base)=({tx:.2f},{ty:.2f},{Z_CONTACT_B}) [Pin-4a from cfg x=[{xlo:.2f},{xhi:.2f}]]")
    _p(f"rest EE(base) = {np.round(ee_b(),3).tolist()}")
    _p("=== GUI open. RED sphere = target. Watch: arm stalls short (convergence)")
    _p("    or reaches full stretch (kinematic)? Live EE error prints each burst. ===")

    lb, rb, _, _ = iface._get_ee_poses()
    if args_cli.arm == "left":
        cmd = BimanualCommand(left=MetricCommand(position=(tx, ty, Z_CONTACT_B)),
                              right=MetricCommand(position=tuple(float(v) for v in rb)))
    else:
        cmd = BimanualCommand(left=MetricCommand(position=tuple(float(v) for v in lb)),
                              right=MetricCommand(position=(tx, ty, Z_CONTACT_B)))
    tgt = np.array([tx, ty, Z_CONTACT_B])
    burst = 0
    while simulation_app.is_running():
        iface.execute_command(cmd, steps=5, active_arm=args_cli.arm)
        markers.visualize(translations=marker_pos)
        burst += 1
        if burst % 6 == 0:
            d = float(np.linalg.norm(ee_b() - tgt)) * 100
            _p(f"burst {burst}: EE err = {d:.1f}cm")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
