"""Free-drive standby-pose tuner for WP1-③a (PI runs on DISPLAY=:0).

Opens the rebuilt push_s3a scene (table + base + cube) with the arm HELD
kinematically, and builds an omni.ui panel with ONE SLIDER PER ARM JOINT. Drag
a slider → the arm moves there immediately and holds (no gravity flop, no
jitter — the reset event is disabled in push_s3a now). The panel shows the
live joint angles; a "PRINT POSE" button dumps the current 7+7 joint dict to
the console in copy-paste form so the PI can hand the good standby back.

Also draws RED spheres at the Pin-4 goal corners so reach can be eyeballed
while tuning.

Run:
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/diagnostics/wp3a_standby_tuner.py --base-z 0.55
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--base-z", type=float, default=None)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import omni.ui as ui
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import subtract_frame_transforms, combine_frame_transforms
import isaaclab.sim as sim_utils
from isaaclab.markers import VisualizationMarkers, VisualizationMarkersCfg

GID = "Isaac-AionGenos-WP1-Push-v0"
# per-joint slider range (rad) — generous, clamped to soft limits at apply
JOINT_RANGE = (-3.5, 2.5)


def _p(m): print(f"[TUNE] {m}", flush=True)


def main():
    cfg = parse_env_cfg(GID, num_envs=1)
    if args_cli.base_z is not None:
        cfg.scene.robot.init_state.pos = (0.0, 0.0, args_cli.base_z)
    for term in ("left_ee_pose", "right_ee_pose"):
        c = getattr(cfg.commands, term, None)
        if c is not None and hasattr(c, "debug_vis"):
            c.debug_vis = False

    # Pin-4 goal corners READ FROM THE CFG (not hardcoded) so the red markers
    # always reflect the actual goal region — the earlier hardcoded 0.40-0.60
    # did NOT track the Pin-4a −60mm inward shift, so the markers looked
    # unmoved. Read the command term's x/y ranges live.
    gr = cfg.commands.left_ee_pose.ranges
    xlo, xhi = gr.pos_x
    ylo, yhi = gr.pos_y
    pin4_corners = [(xlo, ylo), (xlo, yhi), (xhi, ylo), (xhi, yhi),
                    ((xlo + xhi) / 2, (ylo + yhi) / 2)]

    env = gym.make(GID, cfg=cfg, render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    env.reset(seed=4700)

    # arm joint ids/names (exclude fingers/tcp)
    arm_names = [n for n in r.joint_names if "joint" in n and "finger" not in n]
    arm_ids = [r.joint_names.index(n) for n in arm_names]
    # current held target = the Pin-7 standby from init_state
    held = r.data.joint_pos[0].clone()
    held0 = held.clone()  # snapshot for the RESET Pin-7 button
    soft = r.data.soft_joint_pos_limits[0].cpu().numpy()  # (N,2)

    # RED Pin-4 markers
    markers = VisualizationMarkers(VisualizationMarkersCfg(
        prim_path="/Visuals/Pin4Corners",
        markers={"sphere": sim_utils.SphereCfg(radius=0.02,
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.0, 0.0)))}))
    for _ in range(5):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))
    root_p = r.data.root_pos_w[0:1, :3]; root_q = r.data.root_quat_w[0:1, :4]
    cube_b, _ = subtract_frame_transforms(root_p, root_q, u.scene["object"].data.root_pos_w[0:1, :3])
    z_b = float(cube_b[0, 2])
    pts = []
    for (x, y) in pin4_corners:
        pw, _ = combine_frame_transforms(root_p, root_q, torch.tensor([[x, y, z_b]], device=u.device))
        pts.append(pw[0])
    marker_pos = torch.stack(pts)

    _p(f"base z = {float(r.data.root_pos_w[0,2]):.3f}; Pin-4 contact z_b = {z_b:.3f}")
    _p(f"Pin-4 goal region (from cfg): x=[{xlo:.2f},{xhi:.2f}] y=[{ylo:.2f},{yhi:.2f}] "
       f"→ red markers here (Pin-4a −60mm should show x 0.34-0.54)")
    _p(f"tunable arm joints: {arm_names}")

    # ---- omni.ui slider panel ----
    models = {}
    win = ui.Window("Standby Pose Tuner", width=420, height=560)
    with win.frame:
        with ui.VStack(spacing=4):
            ui.Label("Drag a slider → arm moves & holds. PRINT POSE dumps the dict.",
                     height=24, word_wrap=True)
            for jid, jname in zip(arm_ids, arm_names):
                with ui.HStack(height=22):
                    ui.Label(jname.replace("openarm_", ""), width=150)
                    m = ui.SimpleFloatModel(float(held[jid]))
                    lo = max(JOINT_RANGE[0], float(soft[jid, 0]))
                    hi = min(JOINT_RANGE[1], float(soft[jid, 1]))
                    # slider + editable numeric field share ONE model → drag OR
                    # type; both drive the arm. Field is narrow, on the right.
                    ui.FloatSlider(m, min=lo, max=hi)
                    ui.FloatField(m, width=64)
                    models[jid] = m

            def _print_pose():
                q = r.data.joint_pos[0]
                _p("=== CURRENT STANDBY POSE (copy into push_s3a init_state.joint_pos) ===")
                for jid, jname in zip(arm_ids, arm_names):
                    _p(f'    "{jname}": {float(q[jid]):+.3f},')
                _p("=== end ===")

            def _mirror_l_to_r():
                # copy each left joint value to the matching right joint
                # (same-sign convention, per the reset-event target)
                by_name = {n: jid for jid, n in zip(arm_ids, arm_names)}
                for i in range(1, 8):
                    lid = by_name.get(f"openarm_left_joint{i}")
                    rid = by_name.get(f"openarm_right_joint{i}")
                    if lid is not None and rid is not None:
                        models[rid].as_float = models[lid].as_float
                _p("mirrored L→R (same-sign)")

            def _reset_pin7():
                for jid in arm_ids:
                    models[jid].as_float = float(held0[jid])
                _p("reset sliders to Pin-7 standby")

            with ui.HStack(height=30, spacing=6):
                ui.Button("PRINT POSE", clicked_fn=_print_pose)
                ui.Button("MIRROR L→R", clicked_fn=_mirror_l_to_r)
                ui.Button("RESET Pin-7", clicked_fn=_reset_pin7)

    # ---- hold loop: apply slider values kinematically every step ----
    all_ids = list(range(r.data.joint_pos.shape[1]))
    while simulation_app.is_running():
        for jid, m in models.items():
            held[jid] = m.as_float
        r.write_joint_position_to_sim(held.unsqueeze(0), joint_ids=all_ids)
        r.write_data_to_sim()
        u.sim.step(render=True)
        r.update(u.sim.get_physics_dt())
        markers.visualize(translations=marker_pos)
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
