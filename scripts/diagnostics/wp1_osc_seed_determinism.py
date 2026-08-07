"""WP1-① acceptance #3 — seed determinism on the OSC test-bed (D11-style).

Two-way check: same seed → identical initial state (ε=1e-4); different seed
→ meaningfully different (≥1e-3). Init determinism depends on the reset RNG,
not the controller, but this confirms the OSC test-bed is paired-eval-ready
(same discipline as the D11/L2 seed smoke). Runs on the s0 OSC env.

All prints flushed; caller reads the [SD] VERDICT line.
"""
from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--seed_a", type=int, default=4700)
parser.add_argument("--seed_b", type=int, default=4701)
parser.add_argument("--epsilon_m", type=float, default=1e-4)
parser.add_argument("--diff_threshold_m", type=float, default=1e-3)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


def _p(m):
    print(f"[SD] {m}", flush=True)


def _init_fingerprint(env):
    """EE + root position fingerprint right after reset (world frame)."""
    robot = env.unwrapped.scene["robot"]
    return robot.data.body_pos_w[0].clone().flatten()


def main() -> None:
    gym_id = "Isaac-AionGenos-OSC-Bisect-S0-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    _p(f"env made ({gym_id})")

    env.reset(seed=args_cli.seed_a); fp_a1 = _init_fingerprint(env)
    env.reset(seed=args_cli.seed_a); fp_a2 = _init_fingerprint(env)
    env.reset(seed=args_cli.seed_b); fp_b = _init_fingerprint(env)

    same = float(torch.norm(fp_a1 - fp_a2).item())
    diff = float(torch.norm(fp_a1 - fp_b).item())
    _p(f"same-seed L2 dist = {same:.2e} m (want < {args_cli.epsilon_m:.0e})")
    _p(f"diff-seed L2 dist = {diff:.2e} m (want >= {args_cli.diff_threshold_m:.0e})")

    same_ok = same < args_cli.epsilon_m
    diff_ok = diff >= args_cli.diff_threshold_m
    _p(f"same-seed determinism: {'PASS' if same_ok else 'FAIL'}")
    _p(f"diff-seed variation:   {'PASS' if diff_ok else 'FAIL'}")
    _p(f"VERDICT {'PASS' if (same_ok and diff_ok) else 'FAIL'} — paired-eval-ready: {same_ok and diff_ok}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
