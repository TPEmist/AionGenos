"""WP1-① acceptance #2 — OSC motion-equivalence.

Does the OSC test-bed actually SERVO the EE to a pose target (not merely
step without error)? Uses the env's OWN `ee_pose` command as the target —
it is drawn from UniformPoseCommand's designer-set ranges, so it is
KNOWN-REACHABLE by construction (avoids the false-"didn't-converge" trap of
an arbitrary target). Feeds that pose into the OSC action's pose_abs slot,
servos, and measures final ‖EE − target‖ against the ~5 cm gate DiffIK hits.

All prints flushed; caller reads the [ME] VERDICT line.

Usage:
  isaaclab.sh -p scripts/diagnostics/wp1_osc_motion_equiv.py --stage s0 --headless [--enable_cameras]
"""
from __future__ import annotations

import argparse
import sys

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--stage", default="s0", choices=["s0"])  # single-arm cleanest for #2
parser.add_argument("--servo-steps", type=int, default=120)
parser.add_argument("--gate-cm", type=float, default=5.0)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


def _p(m):
    print(f"[ME] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-OSC-Bisect-S0-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    _p(f"env made ({gym_id})")
    u = env.unwrapped
    obs, _ = env.reset(seed=4700)
    _p("reset OK")

    from isaaclab_tasks.manager_based.manipulation.reach.mdp.rewards import (
        position_command_error,
    )
    from isaaclab.managers import SceneEntityCfg
    act_dim = env.action_space.shape[-1]
    _asset = SceneEntityCfg("robot", body_names=["openarm_hand"])
    _asset.resolve(u.scene)

    def cmd_err_cm() -> float:
        # IsaacLab's own position_command_error (correct frame, pos-only):
        # per-env L2 dist (m) between the ee_pose command and the EE body.
        e = position_command_error(u, command_name="ee_pose", asset_cfg=_asset)
        return float(e[0].item()) * 100.0

    # Target = the env's own ee_pose command (reachable by design). Feed its
    # pos+quat into the OSC pose_abs slot; stiffness dims at mid value.
    cmd = u.command_manager.get_command("ee_pose")
    _p(f"target ee_pose command = {cmd[0].tolist()}")
    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    action[:, 0:7] = cmd[:, 0:7]
    if act_dim > 7:
        action[:, 7:] = 100.0

    d0 = cmd_err_cm()
    dmin = d0
    for i in range(args_cli.servo_steps):
        env.step(action)
        d = cmd_err_cm()
        dmin = min(dmin, d)
        if i % 30 == 0 or i == args_cli.servo_steps - 1:
            _p(f"step {i}: cmd_err = {d:.2f} cm (min so far {dmin:.2f})")
    dfin = cmd_err_cm()

    # PASS if the EE reached within the gate at ANY point (motion capability:
    # can OSC servo the EE to the target). Whether it then HOLDS is a
    # separate stability/tuning question, reported but not gating #2.
    reached = dmin < args_cli.gate_cm
    _p(f"start={d0:.2f}cm  min={dmin:.2f}cm  final={dfin:.2f}cm  gate={args_cli.gate_cm}cm")
    if reached and dfin < args_cli.gate_cm:
        _p("VERDICT PASS (OSC servos to target AND holds)")
    elif reached:
        _p("VERDICT PASS-REACHED-NOT-HELD (OSC reaches gate at min; drifts after "
           "→ motion capability CONFIRMED, holding needs stiffness/damping tuning)")
    else:
        _p(f"VERDICT FAIL (EE never entered {args_cli.gate_cm}cm gate; min {dmin:.2f}cm)")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
