"""Interactive scene viewer for WP1-③a table/cube geometry — for the PI to
run on the local display (DISPLAY=:0) and SEE what to tune.

Opens the push_s3a scene in the Isaac Sim GUI with a SeattleLabTable added at
a configurable height, the cube resting on the table top, and prints every
key world/base z so the human eye + the numbers agree. Re-run with different
--table-z / --robot-z to compare; nothing is committed — this is a tuning
sandbox.

Run on the machine with the display:
  /home/control/env_isaaclab/bin/python \
    scripts/diagnostics/wp3a_scene_viewer.py --table-z 0.0 --robot-z 0.0

  # official convention (drop robot instead of raising table):
  ... --table-z 0.0 --robot-z -1.05

The window stays open; close it to exit. Reads the SeattleLabTable bbox so you
see the ACTUAL table-top z, not a guessed one.
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--table-z", type=float, default=0.0,
                    help="Table prim origin world z (SeattleLabTable top is ~1.05m above its origin).")
parser.add_argument("--robot-z", type=float, default=0.0,
                    help="Robot base world z. Official lift drops robot to -1.05.")
parser.add_argument("--cube-clearance", type=float, default=0.02,
                    help="Cube rest height above the measured table top (m).")
# NOTE: do NOT pass --headless; we want the GUI. The push env has a camera,
# so cameras must be enabled — force it on so the caller needn't remember.
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import subtract_frame_transforms
from pxr import Usd, UsdGeom


def _p(m): print(f"[VIEW] {m}", flush=True)


def _bbox_z(stage, path):
    prim = stage.GetPrimAtPath(path)
    if not prim or not prim.IsValid():
        return None
    c = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"], useExtentsHint=True)
    try:
        r = c.ComputeWorldBound(prim).ComputeAlignedRange()
        return float(r.GetMin()[2]), float(r.GetMax()[2])
    except Exception:
        return None


def main():
    # Use the push env (has the dynamic cube + OSC). We add a table by editing
    # the cfg BEFORE make, so the geometry is what ③a will actually use.
    gid = "Isaac-AionGenos-WP1-Push-v0"
    cfg = parse_env_cfg(gid, num_envs=1)

    # add / move a table (AssetBaseCfg) at the requested height
    import isaaclab.sim as sim_utils
    from isaaclab.assets import AssetBaseCfg
    from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
    from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR
    cfg.scene.table = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Table",
        init_state=AssetBaseCfg.InitialStateCfg(pos=[0.5, 0.0, args_cli.table_z],
                                                rot=[0.707, 0.0, 0.0, 0.707]),
        spawn=UsdFileCfg(usd_path=f"{ISAAC_NUCLEUS_DIR}/Props/Mounts/SeattleLabTable/table_instanceable.usd"),
    )
    # optionally drop the robot base (official convention)
    if abs(args_cli.robot_z) > 1e-6:
        try:
            cfg.scene.robot.init_state.pos = (0.0, 0.0, args_cli.robot_z)
        except Exception as e:
            _p(f"could not set robot z: {e}")

    env = gym.make(gid, cfg=cfg, render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    env.reset(seed=4700)
    for _ in range(30):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))

    stage = u.sim.stage
    _p(f"--- config: table_z={args_cli.table_z} robot_z={args_cli.robot_z} ---")
    _p(f"robot base world z = {float(r.data.root_pos_w[0,2]):.4f}")
    for nm in ("openarm_left_hand", "openarm_right_hand"):
        bi = r.body_names.index(nm)
        w = r.data.body_pos_w[0, bi, :3]
        rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
        b, _ = subtract_frame_transforms(rp, rq, w.unsqueeze(0))
        _p(f"{nm}: world={[round(float(v),3) for v in w]} base-rel={[round(float(v),3) for v in b[0]]}")
    tb = _bbox_z(stage, "/World/envs/env_0/Table")
    if tb:
        _p(f"TABLE world bbox z=[{tb[0]:.3f},{tb[1]:.3f}] → TOP z ≈ {tb[1]:.3f}")
        top = tb[1]
    else:
        _p("table bbox not found"); top = None
    try:
        obj = u.scene["object"]
        # place the cube ON the measured table top (keep its x,y) so the view
        # shows a VALID resting cube, not the hardcoded z=0.02 floating one.
        if top is not None:
            cw0 = obj.data.root_pos_w[0, :3].clone()
            new_pose = torch.tensor([[float(cw0[0]), float(cw0[1]), top + args_cli.cube_clearance,
                                      1.0, 0.0, 0.0, 0.0]], device=u.device)
            obj.write_root_pose_to_sim(new_pose)
            for _ in range(10):
                env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))
        cw = obj.data.root_pos_w[0, :3]
        _p(f"cube world (placed on table) = {[round(float(v),3) for v in cw]}")
        if top is not None:
            # base-relative cube z (what the arm must reach)
            rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
            cb, _ = subtract_frame_transforms(rp, rq, cw.unsqueeze(0))
            _p(f"cube base-rel z (arm must reach) = {float(cb[0,2]):.3f} "
               f"(reachable band from posfree sweep ≈ 0.20-0.30 base-rel)")
    except Exception as e:
        _p(f"no cube: {e}")
    _p("=== GUI open. Inspect the table/cube/arm. Close the window to exit. ===")
    _p("Watch: is the cube sitting ON the table top, within the arm's reach?")

    # keep the GUI alive, stepping so it renders, until the user closes it
    while simulation_app.is_running():
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
