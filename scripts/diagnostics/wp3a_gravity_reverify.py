"""Q1 gravity-on re-verify (pre-committed criteria).

push_s3a now has arm gravity ON + OSC gravity_compensation=True. Re-verify:
  1. STANDBY HOLD: teleport to standby, then command the standby EE pose (hold
     in place) for N steps; PASS if sustained peak τ/limit ≤ 0.85.
  2. NEAR servo: from standby, servo the LEFT EE to rest+12cm (the NEAR test
     that passed pre-gravity); PASS if it reaches (<5cm) and τ/limit ≤ 0.85.
Reports the gravity-on τ (provenance sim-to-real delta vs the pre-gravity 0.75).
Cube physics unchanged. FAIL on hold → Pin-7b (retune pose/gains), logged.

Reads [GRV]. Headless.
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--hold", type=int, default=120)
parser.add_argument("--servo", type=int, default=150)
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
from isaaclab.utils.math import subtract_frame_transforms

GID = "Isaac-AionGenos-WP1-Push-v0"
LIMITS = [40., 40., 27., 27., 7., 7., 7.]


def _p(m): print(f"[GRV] {m}", flush=True)


def main():
    env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    ee_idx = r.body_names.index("openarm_left_hand")
    left_ids, _ = r.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    lim = torch.tensor(LIMITS, device=u.device)
    act_dim = env.action_space.shape[-1]

    # confirm gravity actually on
    dg = r.cfg.spawn.rigid_props.disable_gravity
    gc = u.action_manager._terms["left_arm_action"]._osc.cfg.gravity_compensation
    _p(f"disable_gravity={dg} (expect False); gravity_compensation={gc} (expect True)")

    env.reset(seed=4700)
    ee0 = r.data.body_pos_w[0, ee_idx, :3].clone()

    def base(pw):
        rp = r.data.root_pos_w[0:1, :3]; rq = r.data.root_quat_w[0:1, :4]
        b, _ = subtract_frame_transforms(rp, rq, pw.unsqueeze(0))
        return b[0]

    def act_to(tgt_b):
        a = torch.zeros((u.num_envs, act_dim), device=u.device)
        a[:, 0:3] = tgt_b
        a[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            a[:, 7:13] = 300.0
        return a

    # --- 1. STANDBY HOLD: command the standby EE pose, sustained ---
    standby_b = base(ee0)
    a = act_to(standby_b)
    hold_peak = 0.0; sustained = []
    for i in range(args_cli.hold):
        env.step(a)
        tau = float((r.data.applied_torque[0, lid].abs() / lim).max())
        if i >= 20:  # after settle
            hold_peak = max(hold_peak, tau)
            sustained.append(tau)
    ee_hold = r.data.body_pos_w[0, ee_idx, :3]
    drift = float(torch.norm(ee_hold - ee0) * 100)
    hold_pass = hold_peak <= 0.85
    _p(f"STANDBY HOLD: sustained peak τ/limit={hold_peak:.2f} mean={np.mean(sustained):.2f} "
       f"drift={drift:.1f}cm EE_z={float(ee_hold[2]):.3f} → {'PASS' if hold_pass else 'FAIL (Pin-7b)'}")

    # --- 2. NEAR servo: standby → rest+12cm ---
    env.reset(seed=4700)
    ee0 = r.data.body_pos_w[0, ee_idx, :3].clone()
    near_w = ee0 + torch.tensor([0.12, -0.05, 0.0], device=u.device)
    a = act_to(base(near_w))
    near_peak = 0.0; dmin = 1e9
    for i in range(args_cli.servo):
        env.step(a)
        ee = r.data.body_pos_w[0, ee_idx, :3]
        dmin = min(dmin, float(torch.norm(ee - near_w) * 100))
        if i >= args_cli.servo - 40:
            near_peak = max(near_peak, float((r.data.applied_torque[0, lid].abs() / lim).max()))
    near_pass = dmin < 5.0 and near_peak <= 0.85
    _p(f"NEAR servo: min_err={dmin:.1f}cm peak τ/limit={near_peak:.2f} → {'PASS' if near_pass else 'FAIL'}")

    _p("=== VERDICT ===")
    _p(f"gravity-on τ: hold={hold_peak:.2f} near={near_peak:.2f} "
       f"(pre-gravity reference: standby-first-servo τ≈0.75)")
    if hold_pass and near_pass:
        _p("PASS both → gravity-on standby holds + NEAR servos in budget. gen-0 gravity honest. Proceed Q3.")
    else:
        _p(f"FAIL → hold_pass={hold_pass} near_pass={near_pass}. If hold fails: Pin-7b "
           f"(retune standby pose/gains). Do NOT proceed silently.")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
