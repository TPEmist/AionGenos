"""OSC servo-tracking probe across bisection stages — isolate why bimanual
OSC fails to servo while single-arm (#2) succeeds.

Drives the LEFT arm to a reachable target and measures EE tracking, on:
  --stage s0  (single arm, official base)   → expect track (#2: 2cm)
  --stage s1  (DUAL arm, two OSC terms, official base, NO camera)
  --stage push(dual arm + cube + camera)    → observed 26cm off

Same target-build path (frame gate) for all. If s1 fails like push → the
two-OSC-terms-on-one-articulation interaction is the cause (independent of
cube/camera). If s1 tracks → the fault is push-env-specific.

Flushed; caller reads [TRK].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--stage", choices=["s0", "s1", "push"], default="s1")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import base_frame_target_from_world

_GYM = {
    "s0": "Isaac-AionGenos-OSC-Bisect-S0-v0",
    "s1": "Isaac-AionGenos-OSC-Bisect-S1-v0",
    "push": "Isaac-AionGenos-WP1-Push-v0",
}
_EE = {"s0": "openarm_hand", "s1": "openarm_left_hand", "push": "openarm_left_hand"}


def _p(m):
    print(f"[TRK:{args_cli.stage}] {m}", flush=True)


def main() -> None:
    gym_id = _GYM[args_cli.stage]
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    ee_idx = robot.body_names.index(_EE[args_cli.stage])
    act_dim = env.action_space.shape[-1]
    _p(f"env made; action_dim={act_dim}, ee={_EE[args_cli.stage]}")

    env.reset(seed=4700)
    root_w = robot.data.root_pos_w[0, :3]
    ee0 = robot.data.body_pos_w[0, ee_idx, :3]
    _p(f"root={[round(x,3) for x in root_w.tolist()]} EE_start={[round(x,3) for x in ee0.tolist()]}")

    # A comfortably reachable target in front of the LEFT arm (world frame).
    tgt_w = torch.tensor([0.45, 0.10, 0.30], device=u.device)
    tgt_b = base_frame_target_from_world(u, tgt_w)
    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    # LEFT arm always occupies action[0:...]; single-arm dim=13, dual=26.
    action[:, 0:3] = tgt_b
    action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)
    # fill the LEFT term's stiffness slot (indices 7..12 for a 13-dim term)
    left_dim = 13 if act_dim >= 13 else act_dim
    if left_dim > 7:
        action[:, 7:left_dim] = 300.0

    dmin = 1e9
    for i in range(120):
        env.step(action)
        ee = robot.data.body_pos_w[0, ee_idx, :3]
        d = float(torch.norm(ee - tgt_w).item()) * 100.0
        dmin = min(dmin, d)
    ee_f = robot.data.body_pos_w[0, ee_idx, :3]
    _p(f"target_world={[round(x,3) for x in tgt_w.tolist()]} target_base={[round(x,3) for x in tgt_b.tolist()]}")
    _p(f"EE settled={[round(x,3) for x in ee_f.tolist()]}  final_err={float(torch.norm(ee_f-tgt_w))*100:.1f}cm  min_err={dmin:.1f}cm")
    _p(f"VERDICT {'TRACKS' if dmin < 5.0 else 'NO-TRACK'} (min_err {dmin:.1f}cm vs 5cm gate)")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
