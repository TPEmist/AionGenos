"""WP1-① OSC bisection smoke — parameterised by --stage {s0,s1,s2,s3}.

Builds UP from the official OSC reach env (s0 = +openarm single arm) toward
our full test-bed, one variable per stage. Prints all robot body names on
first reset (resolves the EE-body-name uncertainty empirically, not by
guess). Single AppLauncher (the dup-AppLauncher bug is not repeated here).

PASS = reaches "STAGE PASS" after reset + N steps with no stall.
Stall detection is the caller's job (Rule 2: check GPU/CPU/log-size over a
window); this script just prints bracketed markers so the caller can see
exactly how far it got.

Usage:
  isaaclab.sh -p scripts/diagnostics/wp1_osc_bisect.py --stage s0 --headless [--enable_cameras]
"""

from __future__ import annotations

import argparse
import sys

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--stage", choices=["s0", "s1", "s2", "s3"], default="s0")
parser.add_argument("--steps", type=int, default=5)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import aiongenos.tasks  # noqa: F401  registers gym ids
from isaaclab_tasks.utils import parse_env_cfg

_STAGE_GYM = {
    "s0": "Isaac-AionGenos-OSC-Bisect-S0-v0",
    "s1": "Isaac-AionGenos-OSC-Bisect-S1-v0",
    "s2": "Isaac-AionGenos-OSC-Bisect-S2-v0",
    "s3": "Isaac-AionGenos-OSC-Bisect-S3-v0",
}


def main() -> None:
    gym_id = _STAGE_GYM.get(args_cli.stage)
    if gym_id is None:
        print(f"[bisect] stage {args_cli.stage} not yet wired — s0 first", flush=True)
        return
    print(f"[bisect:{args_cli.stage}] cfg parse …", flush=True)
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    print(f"[bisect:{args_cli.stage}] env made ✓", flush=True)

    # Print body names — resolves EE-body-name empirically.
    robot = env.unwrapped.scene["robot"]
    print(f"[bisect:{args_cli.stage}] robot body_names = {robot.body_names}", flush=True)

    obs, _ = env.reset(seed=4700)
    print(f"[bisect:{args_cli.stage}] reset OK ✓", flush=True)

    act_dim = env.action_space.shape[-1]
    ok = 0
    for _ in range(args_cli.steps):
        action = torch.zeros((env.unwrapped.num_envs, act_dim), device=env.unwrapped.device)
        env.step(action)
        ok += 1
    print(f"[bisect:{args_cli.stage}] stepped {ok}/{args_cli.steps} ✓", flush=True)
    print(f"[bisect:{args_cli.stage}] STAGE PASS (action_dim={act_dim})", flush=True)
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
