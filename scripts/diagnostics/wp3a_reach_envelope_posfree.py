"""WP1-③a — CONFOUND-KILLER reachability sweep (PI: 先純診斷,不預設歸屬).

The human-eye gate (2026-08-20) refuted the "z-wall" reading: the wall is
LATERAL (arm can't get its finger across to y=0), likely compounded by the
held-orientation constraint pinning the wrist. This sweep kills BOTH confounds
I baked into the first sweep:

  1. ORIENTATION FREED: uses the PosFree env (DiffIK command_type="position"),
     so IK solves position only and the wrist is free — tests pure positional
     reachability ("can the EE reach the point AT ALL, any orientation?").
  2. FULL y RANGE, BOTH ARMS: sweeps y ∈ {-0.20..+0.20}, not just y=0, for the
     LEFT and RIGHT arm separately — so lateral reach is measured, not assumed,
     and arm-assignment can EMERGE from the envelope (no pre-set ownership).

Maps the true (x,y,z) reachability envelope. Baseline-first (self-referential,
per the fixed instrument). Records min_err + error vector + pinned joint.
Dumps a compact per-arm envelope table + GIFs (RED cube = true target) for a
follow-up human-eye check.

No task-geometry decision here — just the map. Effort irrelevant (kinematics).
Flushed; caller reads [RP].
"""
from __future__ import annotations
import argparse
import os
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=150)
parser.add_argument("--out", type=str, default="logs/reach_posfree")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np
import torch
import imageio.v2 as imageio
from isaaclab.utils.math import subtract_frame_transforms
from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder  # noqa: F401 (registers)
import aiongenos.tasks  # noqa: F401 (WP1 registry)
import gymnasium as gym
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.pipeline.stage2_attempt import BimanualCommand, MetricCommand

GYM_ID = "Isaac-AionGenos-WP1-ReachProbe-PosFree-v0"
XS = [0.25, 0.35, 0.45]
YS = [-0.20, -0.10, 0.0, 0.10, 0.20]
ZS = [0.024, 0.10, 0.30]
REACH_TOL_CM = 3.0


def _p(m):
    print(f"[RP] {m}", flush=True)


def main() -> None:
    os.makedirs(args_cli.out, exist_ok=True)
    cfg = parse_env_cfg(GYM_ID, num_envs=1)
    env = gym.make(GYM_ID, cfg=cfg, render_mode=None)
    iface = IsaacLabEnvInterface(env)
    robot = iface.robot
    u = env.unwrapped
    left_idx = iface.left_body_idx
    right_idx = iface.right_body_idx
    arms = {
        "L": {"body": left_idx, "ids": robot.find_joints("openarm_left_joint.*")[0],
              "names": robot.find_joints("openarm_left_joint.*")[1], "term": "left_ee_pose"},
        "R": {"body": right_idx, "ids": robot.find_joints("openarm_right_joint.*")[0],
              "names": robot.find_joints("openarm_right_joint.*")[1], "term": "right_ee_pose"},
    }
    for a in arms.values():
        a["jlim"] = robot.data.soft_joint_pos_limits[0, torch.tensor(a["ids"], device=u.device)].cpu().numpy()

    def ee_pos_b(body_idx):
        root_p = robot.data.root_pos_w[0:1, :3]; root_q = robot.data.root_quat_w[0:1, :4]
        ee_w = robot.data.body_pos_w[0:1, body_idx, :3]
        pos_b, _ = subtract_frame_transforms(root_p, root_q, ee_w)
        return pos_b[0].cpu().numpy()

    def joint_prox(arm):
        q = robot.data.joint_pos[0, torch.tensor(arm["ids"], device=u.device)].cpu().numpy()
        lo, hi = arm["jlim"][:, 0], arm["jlim"][:, 1]
        span = np.maximum(hi - lo, 1e-6)
        frac = (q - lo) / span
        prox = np.maximum(1.0 - frac, frac)
        return prox

    def mark_goal(term_name, x, y, z):
        # PosFree IK ignores orientation; visualizer still needs a quat — use
        # identity purely for the marker. Position is what matters.
        try:
            t = u.command_manager.get_term(term_name)
            t.pose_command_b[:, 0] = x; t.pose_command_b[:, 1] = y; t.pose_command_b[:, 2] = z
            t.pose_command_b[:, 3] = 1.0; t.pose_command_b[:, 4:7] = 0.0
        except Exception as e:
            _p(f"WARN mark {term_name}: {e}")

    def servo_arm_to(arm_key, x, y, z):
        """Drive ONE arm to (x,y,z) via position-free DiffIK; the other holds.
        PosFree action_dim: L2 pose was 14; position mode → 6 (3+3). Interface
        builds dim-6 as [left_xyz, right_xyz]."""
        arm = arms[arm_key]
        iface.reset(seed=4700)
        lb, rb, _, _ = iface._get_ee_poses()
        if arm_key == "L":
            left_cmd = MetricCommand(position=(x, y, z))
            right_cmd = MetricCommand(position=tuple(float(v) for v in rb))
        else:
            left_cmd = MetricCommand(position=tuple(float(v) for v in lb))
            right_cmd = MetricCommand(position=(x, y, z))
        cmd = BimanualCommand(left=left_cmd, right=right_cmd)
        target = np.array([x, y, z]); dmin = 1e9; vec = None
        for _ in range(args_cli.steps // 10):
            mark_goal(arm["term"], x, y, z)
            iface.execute_command(cmd, steps=10, active_arm=("left" if arm_key == "L" else "right"))
            lp = ee_pos_b(arm["body"])
            d = float(np.linalg.norm(lp - target)) * 100
            if d < dmin:
                dmin = d; vec = (lp - target) * 100
        prox = joint_prox(arm); pj = int(np.argmax(prox))
        return dmin, vec, arm["names"][pj], float(prox[pj])

    # ---------- action dim sanity ----------
    _p(f"env={GYM_ID} action_dim={env.action_space.shape[-1]} (position mode → expect 6)")

    # ---------- BASELINE (self-referential, per arm) ----------
    ok_all = True
    for k in ("L", "R"):
        iface.reset(seed=4700)
        e0 = ee_pos_b(arms[k]["body"])
        d, v, pj, pv = servo_arm_to(k, float(e0[0]) + 0.05, float(e0[1]), float(e0[2]))
        pas = d < REACH_TOL_CM
        ok_all = ok_all and pas
        _p(f"BASELINE {k}: EE0={np.round(e0,3).tolist()} +5cm x → min_err={d:.1f}cm "
           f"vec={np.round(v,1).tolist()} {'PASS' if pas else 'FAIL'}")
    if not ok_all:
        _p("BASELINE FAIL → instrument broken; readings VOID.")
        env.close(); return
    _p("BASELINE PASS (both arms) → position-free instrument valid.")

    # ---------- SWEEP: per arm, full (x,y,z) ----------
    grid = {}
    for k in ("L", "R"):
        _p(f"=== ARM {k}: (x,y,z) envelope, orientation-FREE ===")
        for z in ZS:
            for y in YS:
                for x in XS:
                    d, v, pj, pv = servo_arm_to(k, x, y, z)
                    reach = d < REACH_TOL_CM
                    grid[(k, x, y, z)] = {"d": d, "v": np.round(v, 1).tolist(),
                                          "reach": reach, "pin": pj, "pv": round(pv, 2)}
                    _p(f"  {k} x={x:.2f} y={y:+.2f} z={z:.3f}: min_err={d:.1f}cm "
                       f"vec={np.round(v,1).tolist()} {'REACH' if reach else 'stuck'} "
                       f"pin={pj}({pv:.2f})")

    # ---------- envelope summary: reachable y-range per (arm,z), and low-z ----
    _p("=== ENVELOPE SUMMARY (reachable y per arm,x,z) ===")
    for k in ("L", "R"):
        for z in ZS:
            for x in XS:
                ys = [y for y in YS if grid[(k, x, y, z)]["reach"]]
                span = f"[{min(ys):+.2f},{max(ys):+.2f}]" if ys else "NONE"
                _p(f"  {k} x={x:.2f} z={z:.3f}: reachable y = {span}")
    # the money question: is low-z (0.024) reachable ANYWHERE once orientation is free?
    lowz_reach = [(k, x, y) for (k, x, y, z), c in grid.items() if z == 0.024 and c["reach"]]
    _p(f"=== LOW-Z (0.024) reachable cells (orientation-free): {len(lowz_reach)} ===")
    for k, x, y in sorted(lowz_reach):
        _p(f"  reachable: arm={k} x={x:.2f} y={y:+.2f} z=0.024")
    if not lowz_reach:
        _p("  NONE — low z unreachable even orientation-free & across full y → "
           "genuine kinematic floor (THEN raise-table is earned, clean).")
    else:
        _p("  low z IS reachable once orientation-free → held-orientation was a "
           "confound; place contact workspace at these (arm,x,y) cells, NOT raise table.")

    # ---------- GIFs: 3 representative low-z cells (reachable if any, else stuck) ----------
    picks = lowz_reach[:3] if lowz_reach else [(k, x, y) for (k, x, y, z) in
             [key for key in grid if key[3] == 0.024]][:3]
    _p(f"=== GIFs for {len(picks)} low-z cells (human-eye follow-up) ===")
    for k, x, y in picks:
        arm = arms[k]
        iface.reset(seed=4700)
        lb, rb, _, _ = iface._get_ee_poses()
        if k == "L":
            cmd = BimanualCommand(left=MetricCommand(position=(x, y, 0.024)),
                                  right=MetricCommand(position=tuple(float(v) for v in rb)))
        else:
            cmd = BimanualCommand(left=MetricCommand(position=tuple(float(v) for v in lb)),
                                  right=MetricCommand(position=(x, y, 0.024)))
        frames = []
        for _ in range(args_cli.steps // 5):
            mark_goal(arm["term"], x, y, 0.024)
            iface.execute_command(cmd, steps=5, active_arm=("left" if k == "L" else "right"))
            png = iface.get_rgb()
            if png:
                frames.append(imageio.imread(png))
        if frames:
            fn = os.path.join(args_cli.out, f"posfree_{k}_x{int(x*100)}_y{int(y*100)}.gif")
            imageio.mimsave(fn, frames, duration=0.1)
            _p(f"  GIF: {fn}")
    _p("=== DONE ===")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
