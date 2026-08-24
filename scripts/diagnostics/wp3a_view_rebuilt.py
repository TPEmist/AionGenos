"""Interactive viewer of the REBUILT WP1-③a scene (for the PI, DISPLAY=:0).

The arm is FROZEN at the Pin-7 standby pose every step (kinematically held via
write_joint_position_to_sim), so it does NOT flop to a gravity-collapsed,
self-intersecting rest — you see the real standby the task uses. The noisy
default command-axis visualizers are disabled. Only the meaningful things
remain: table, cube-on-table, the arm at standby, and RED spheres at the Pin-4
goal-region corners (where the cube must be pushed).

Watch the horizontal GAP between the hands and the red spheres — that is the
"arm can't reach Pin-4" finding. Adjust --base-z to compare heights (the PI's
suggestion: base is likely 100-150mm too high; try 0.50 / 0.55 vs 0.65).

Run (window stays open; close it to exit):
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/diagnostics/wp3a_view_rebuilt.py --base-z 0.55
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--base-z", type=float, default=None,
                    help="Override robot base world z (default: use push_s3a's 0.65).")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import subtract_frame_transforms, combine_frame_transforms
import isaaclab.sim as sim_utils
from isaaclab.markers import VisualizationMarkers, VisualizationMarkersCfg

GID = "Isaac-AionGenos-WP1-Push-v0"
PIN4_CORNERS = [(0.40, -0.15), (0.40, 0.15), (0.60, -0.15), (0.60, 0.15), (0.50, 0.0)]


def _p(m): print(f"[VIEW] {m}", flush=True)


def main():
    cfg = parse_env_cfg(GID, num_envs=1)
    # optional base-z override for height comparison
    if args_cli.base_z is not None:
        cfg.scene.robot.init_state.pos = (0.0, 0.0, args_cli.base_z)
    # disable the noisy default command-axis visualizers (goal + current pose)
    for term in ("left_ee_pose", "right_ee_pose"):
        c = getattr(cfg.commands, term, None)
        if c is not None:
            if hasattr(c, "debug_vis"):
                c.debug_vis = False

    env = gym.make(GID, cfg=cfg, render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]

    # RED spheres at Pin-4 corners
    markers = VisualizationMarkers(VisualizationMarkersCfg(
        prim_path="/Visuals/Pin4Corners",
        markers={"sphere": sim_utils.SphereCfg(
            radius=0.02,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.0, 0.0)))}))

    env.reset(seed=4700)
    # capture the Pin-7 standby joint pose to HOLD it every step
    standby_q = r.data.joint_pos[0:1, :].clone()
    all_joint_ids = list(range(r.data.joint_pos.shape[1]))
    for _ in range(10):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))

    obj = u.scene["object"]
    root_p = r.data.root_pos_w[0:1, :3]
    root_q = r.data.root_quat_w[0:1, :4]
    cube_b, _ = subtract_frame_transforms(root_p, root_q, obj.data.root_pos_w[0:1, :3])
    z_b = float(cube_b[0, 2])
    world_pts = []
    for (x, y) in PIN4_CORNERS:
        pw, _ = combine_frame_transforms(root_p, root_q, torch.tensor([[x, y, z_b]], device=u.device))
        world_pts.append(pw[0])
    marker_pos = torch.stack(world_pts)

    _p(f"robot base world z = {float(r.data.root_pos_w[0,2]):.3f} "
       f"({'overridden' if args_cli.base_z is not None else 'push_s3a default'})")
    for nm in ("openarm_left_hand", "openarm_right_hand"):
        bi = r.body_names.index(nm)
        w = r.data.body_pos_w[0, bi, :3]
        b, _ = subtract_frame_transforms(root_p, root_q, w.unsqueeze(0))
        _p(f"{nm} standby: world={[round(float(v),3) for v in w]} base-rel={[round(float(v),3) for v in b[0]]}")
    _p(f"cube contact z_b (base) = {z_b:.3f}; Pin-4 corners at that height = RED spheres")
    _p("=== GUI open. Arm HELD at Pin-7 standby (no gravity flop). RED = Pin-4 goal corners.")
    _p("    Gap between hands and red spheres = the reach miss. Close window to exit. ===")

    # hold the standby pose kinematically every step (no flop, no self-collide)
    while simulation_app.is_running():
        r.write_joint_position_to_sim(standby_q, joint_ids=all_joint_ids)
        r.write_data_to_sim()
        u.sim.step(render=True)
        r.update(u.sim.get_physics_dt())
        markers.visualize(translations=marker_pos)
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
