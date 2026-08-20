"""Screenshot + fact dump of the L3 pick-place scene (has a table) so the PI
can VISUALLY confirm the correct table/cube/arm geometry — not my inference.

Reads: table prim top z, cube rest z, both EE rest z, robot base z. Saves the
head-camera RGB to a PNG.
"""
from __future__ import annotations
import argparse
import os
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--out", type=str, default="logs/l3_scene")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np
import torch
import imageio.v2 as imageio
import gymnasium as gym
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
import isaaclab.sim as sim_utils
from pxr import Usd, UsdGeom, UsdPhysics  # noqa

GID = "Isaac-AionGenos-L3-v0"


def _p(m): print(f"[L3] {m}", flush=True)


def _prim_world_bbox_z(stage, prim_path):
    """Return (min_z, max_z) world of a prim's bbox, or None."""
    prim = stage.GetPrimAtPath(prim_path)
    if not prim or not prim.IsValid():
        return None
    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"], useExtentsHint=True)
    try:
        b = bbox_cache.ComputeWorldBound(prim)
        rng = b.ComputeAlignedRange()
        return float(rng.GetMin()[2]), float(rng.GetMax()[2])
    except Exception as e:
        return None


def main():
    env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    env.reset(seed=4700)
    # settle a few steps so objects rest
    for _ in range(30):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))

    _p(f"robot base world z = {float(r.data.root_pos_w[0,2]):.4f}")
    for nm in ("openarm_left_hand", "openarm_right_hand"):
        bi = r.body_names.index(nm)
        w = r.data.body_pos_w[0, bi, :3]
        _p(f"{nm} rest world = {[round(float(v),4) for v in w]}")
    try:
        obj = u.scene["object"]
        cw = obj.data.root_pos_w[0, :3]
        _p(f"cube (object) rest world = {[round(float(v),4) for v in cw]}")
    except Exception as e:
        _p(f"no object: {e}")

    # table top z from USD bbox
    stage = u.sim.stage
    tp = _prim_world_bbox_z(stage, "/World/envs/env_0/Table")
    if tp:
        _p(f"TABLE world bbox z = [{tp[0]:.4f}, {tp[1]:.4f}]  → TOP SURFACE z ≈ {tp[1]:.4f}")
    else:
        _p("table bbox not found at /World/envs/env_0/Table (trying alt paths)")
        for alt in ("/World/envs/env_0/Table/table_instanceable", "/World/envs/env_0"):
            tp2 = _prim_world_bbox_z(stage, alt)
            if tp2:
                _p(f"  {alt} bbox z = [{tp2[0]:.4f},{tp2[1]:.4f}]")

    # screenshot from head camera
    os.makedirs(args_cli.out, exist_ok=True)
    try:
        cam = u.scene["camera"]
        rgb = cam.data.output["rgb"][0].cpu().numpy()
        if rgb.shape[-1] == 4:
            rgb = rgb[..., :3]
        fn = os.path.join(args_cli.out, "l3_scene.png")
        imageio.imwrite(fn, rgb.astype(np.uint8))
        _p(f"SCREENSHOT saved: {fn}")
    except Exception as e:
        _p(f"screenshot failed: {e}")
    _p("=== DONE ===")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
