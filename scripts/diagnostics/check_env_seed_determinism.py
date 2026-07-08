"""Blocker 2 smoke test: is env.reset(seed=...) actually deterministic?

Amendment 11 (upcoming) will pin env_seed_base for D11 eval collects.
The paired-samples design that gives T1 its statistical power assumes
env.reset(seed=k) produces byte-identical initial world state every
time. IsaacLab's randomization (joint offsets, target resampling) may
route through a different RNG stream than the top-level seed argument.

This script runs a 10-minute test:

  1. Reset with seed=S, capture (left_ee, right_ee, red_target,
     blue_target). Reset again with same S, assert values match within
     epsilon.
  2. Reset with seed=S' ≠ S, assert at least one component differs by
     >> epsilon (guards against "seed silently ignored, everything
     deterministic anyway" false positive).

Verdict must PASS before D11 arm collects launch. If FAIL, the paired
design is a mirage and the env_seed_base plumbing needs to reach
deeper (e.g. torch.manual_seed / np.random.seed / IsaacLab env
manager) before any real collect starts.

Usage (inside IsaacLab):
    /home/control/IsaacLab/isaaclab.sh -p \\
      scripts/diagnostics/check_env_seed_determinism.py \\
      --level -2 --headless --enable_cameras
"""

from __future__ import annotations

import argparse
import logging
import sys

# Setup logging BEFORE AppLauncher steals the root handler.
import logging as _logging
_handler = _logging.StreamHandler(sys.stdout)
_handler.setFormatter(_logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
for _name in ("aiongenos", "__main__"):
    _l = _logging.getLogger(_name)
    _l.setLevel(_logging.INFO)
    _l.addHandler(_handler)
    _l.propagate = False
logger = logging.getLogger(__name__)


from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--level", type=int, default=-2,
                    help="Curriculum level (default -2 = L0a-Left, same as D11).")
parser.add_argument("--seed_a", type=int, default=4500,
                    help="Primary test seed (default matches Amendment 11 pin).")
parser.add_argument("--seed_b", type=int, default=4501,
                    help="Alternate seed to prove seed actually varies output.")
parser.add_argument("--epsilon_m", type=float, default=1e-4,
                    help="L1 tolerance (metres) for same-seed determinism.")
parser.add_argument("--diff_threshold_m", type=float, default=1e-3,
                    help="Min per-axis divergence between two different seeds "
                         "to declare seed is 'meaningful' (defends against "
                         "silently-ignored-seed false positive).")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np  # noqa: E402
import torch  # noqa: E402
from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder  # noqa: E402
from aiongenos.orchestrator import IsaacLabEnvInterface  # noqa: E402


def _fingerprint(env_if: IsaacLabEnvInterface) -> dict:
    """Snapshot fields that should be seed-controlled."""
    l_ee, r_ee, l_q, r_q = env_if._get_ee_poses()
    l_tgt, r_tgt = env_if._get_target_poses()
    return {
        "left_ee":    np.asarray(l_ee, dtype=np.float64),
        "right_ee":   np.asarray(r_ee, dtype=np.float64),
        "left_quat":  np.asarray(l_q,  dtype=np.float64),
        "right_quat": np.asarray(r_q,  dtype=np.float64),
        "left_target":  np.asarray(l_tgt, dtype=np.float64),
        "right_target": np.asarray(r_tgt, dtype=np.float64),
    }


def _l1(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a - b).sum())


def _report(label: str, a: dict, b: dict) -> tuple[bool, list[tuple[str, float]]]:
    """Return (all_match, per-key L1 distances)."""
    per_key: list[tuple[str, float]] = []
    for k in a:
        per_key.append((k, _l1(a[k], b[k])))
    total = sum(d for _, d in per_key)
    all_match = total < args_cli.epsilon_m
    logger.info(f"[{label}] total L1 = {total:.6e}")
    for k, d in per_key:
        logger.info(f"  {k:14s} L1={d:.6e}")
    return all_match, per_key


def main() -> None:
    logger.info("Building environment...")
    env = ArenaEnvBuilder.build_env(level=args_cli.level, num_envs=1)
    env_if = IsaacLabEnvInterface(env)

    logger.info(f"=== Trial 1: seed={args_cli.seed_a} (first pass) ===")
    env_if.reset(seed=args_cli.seed_a)
    fp_a1 = _fingerprint(env_if)
    for k, v in fp_a1.items():
        logger.info(f"  {k:14s} = {v.round(6).tolist()}")

    logger.info(f"=== Trial 2: seed={args_cli.seed_a} (second pass, MUST match) ===")
    env_if.reset(seed=args_cli.seed_a)
    fp_a2 = _fingerprint(env_if)
    same_seed_match, per_key_same = _report("SAME-SEED", fp_a1, fp_a2)

    logger.info(f"=== Trial 3: seed={args_cli.seed_b} (different, MUST differ) ===")
    env_if.reset(seed=args_cli.seed_b)
    fp_b = _fingerprint(env_if)
    _, per_key_diff = _report("DIFF-SEED", fp_a1, fp_b)

    diff_seed_varies = any(d >= args_cli.diff_threshold_m for _, d in per_key_diff)

    logger.info("")
    logger.info("─────────────── VERDICT ───────────────")
    logger.info(f"  same-seed determinism (want match, ε={args_cli.epsilon_m}): "
                f"{'PASS ✓' if same_seed_match else 'FAIL ✗'}")
    logger.info(f"  diff-seed variation (want >= {args_cli.diff_threshold_m}): "
                f"{'PASS ✓' if diff_seed_varies else 'FAIL ✗ (seed silently ignored)'}")
    overall = same_seed_match and diff_seed_varies
    logger.info(f"  overall: {'PASS ✓ — paired-samples design is valid' if overall else 'FAIL ✗ — DO NOT dispatch D11'}")

    env.close()
    simulation_app.close()
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
