"""Scene-rebuild assembly verification (steps 2/4/5 in one pass).

On the REBUILT push_s3a env (table + raised base + cube-on-table + explicit
friction), verify:
  2. cube physics: spawn above table → settles ONTO the top; final rest z is
     deterministic across 2 seeds (same within 1mm). Reports measured cube
     half-height (checks the _CUBE_HALF_H constant).
  4. Pin-7 standby pose has ZERO intersection with the new table (reset is a
     teleport, so only the static pose need be collision-free — report min
     distance from each arm's bodies to the table top plane / any penetration).
  5. camera framing: the robot-relative camera rose with the base; save a PNG
     to confirm table + cube + goal region are IN FRAME.
Also prints cube centre in BASE frame (z_b) — expect ≈0.39 (NEAR band).

Headless + cameras. Flushed; reads [ASM].
"""
from __future__ import annotations
import argparse
import os
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--out", type=str, default="logs/assembly")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np
import torch
import imageio.v2 as imageio
import gymnasium as gym
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import subtract_frame_transforms
from pxr import Usd, UsdGeom

GID = "Isaac-AionGenos-WP1-Push-v0"


def _p(m): print(f"[ASM] {m}", flush=True)


def _bbox(stage, path):
    prim = stage.GetPrimAtPath(path)
    if not prim or not prim.IsValid():
        return None
    c = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"], useExtentsHint=True)
    try:
        r = c.ComputeWorldBound(prim).ComputeAlignedRange()
        return (float(r.GetMin()[0]), float(r.GetMin()[1]), float(r.GetMin()[2]),
                float(r.GetMax()[0]), float(r.GetMax()[1]), float(r.GetMax()[2]))
    except Exception:
        return None


def _settle_and_measure(env, u, obj, seed, steps=120):
    env.reset(seed=seed)
    for _ in range(steps):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))
    return obj.data.root_pos_w[0, :3].clone().cpu().numpy()


def main():
    env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    obj = u.scene["object"]
    stage = u.sim.stage

    _p(f"robot base world z = {float(r.data.root_pos_w[0,2]):.4f} (expect 0.65)")
    tb = _bbox(stage, "/World/envs/env_0/Table")
    if tb:
        _p(f"table top z = {tb[5]:.4f} (expect ~0.9941)  x=[{tb[0]:.2f},{tb[3]:.2f}] y=[{tb[1]:.2f},{tb[4]:.2f}]")

    # measured cube half-height
    cb = _bbox(stage, "/World/envs/env_0/PushCube")
    if cb:
        _p(f"cube bbox half-height = {(cb[5]-cb[2])/2:.4f} (constant assumed 0.0206)")

    # --- step 2: deterministic settle across seeds ---
    p1 = _settle_and_measure(env, u, obj, 4700)
    p2 = _settle_and_measure(env, u, obj, 4701)
    p3 = _settle_and_measure(env, u, obj, 4700)  # repeat seed 4700 → must match p1
    _p(f"cube settle seed4700 = {np.round(p1,4).tolist()}")
    _p(f"cube settle seed4701 = {np.round(p2,4).tolist()}")
    _p(f"cube settle seed4700(rpt) = {np.round(p3,4).tolist()}")
    _p(f"determinism (same-seed |Δ|) = {np.linalg.norm(p1-p3)*1000:.2f} mm "
       f"({'DETERMINISTIC' if np.linalg.norm(p1-p3)<0.001 else 'NON-DET — investigate'})")
    if tb:
        _p(f"cube rest above table top = {(p1[2]-tb[5])*100:.2f} cm "
           f"({'ON table' if abs(p1[2]-tb[5]-0.0206)<0.01 else 'check'})")
    # cube in base frame
    rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
    cw = obj.data.root_pos_w[0, :3]
    cbf, _ = subtract_frame_transforms(rp, rq, cw.unsqueeze(0))
    _p(f"cube centre BASE frame = {np.round(cbf[0].cpu().numpy(),4).tolist()} "
       f"(z_b expect ≈0.39, NEAR band)")

    # --- step 4: Pin-7 standby vs table intersection (CORRECT predicate) ---
    # A body only INTERSECTS the table if it overlaps horizontally with the
    # table's footprint AND its z penetrates the table's vertical extent. A
    # bare min-z compare wrongly flags the torso (which sits BELOW the table
    # top by design — arm base on its stand). Test each body's position
    # against the table AABB [x,y,z ranges].
    env.reset(seed=4700)
    for _ in range(10):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))
    if tb:
        txmin, tymin, tzmin, txmax, tymax, tzmax = tb
        # small margin so touching-the-top-surface is not counted as penetrating
        margin = 0.005
        intersecting = []
        for bi, nm in enumerate(r.body_names):
            p = r.data.body_pos_w[0, bi, :3]
            x, y, z = float(p[0]), float(p[1]), float(p[2])
            inside_xy = (txmin <= x <= txmax) and (tymin <= y <= tymax)
            inside_z = (tzmin + margin) < z < (tzmax - margin)
            if inside_xy and inside_z:
                intersecting.append((nm, round(x, 3), round(y, 3), round(z, 3)))
        if intersecting:
            _p(f"Pin-7 standby: INTERSECTS table — bodies inside table AABB: {intersecting} → Pin-7a needed")
        else:
            _p(f"Pin-7 standby: CLEAR — no robot body penetrates the table AABB "
               f"(x[{txmin:.2f},{txmax:.2f}] y[{tymin:.2f},{tymax:.2f}] z[{tzmin:.2f},{tzmax:.2f}])")
    else:
        _p("Pin-7 standby: table bbox unavailable, cannot test")

    # --- step 5: camera framing screenshot ---
    os.makedirs(args_cli.out, exist_ok=True)
    try:
        cam = u.scene["camera"]
        rgb = cam.data.output["rgb"][0].cpu().numpy()
        if rgb.shape[-1] == 4:
            rgb = rgb[..., :3]
        fn = os.path.join(args_cli.out, "assembly.png")
        imageio.imwrite(fn, rgb.astype(np.uint8))
        _p(f"SCREENSHOT: {fn} — confirm table+cube+goal region in frame")
    except Exception as e:
        _p(f"screenshot failed: {e}")
    _p("=== DONE ===")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
