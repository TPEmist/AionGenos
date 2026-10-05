"""D11 Amendment 15 (c) — recover the L0a-Left target per paired seed (op pin 5).

D11 replays never stored the absolute target, but every D11 arm reset at
seed 4500+k, so the target is a deterministic function of the seed. This
re-resets the same env (level -2, same builder as run_collect) at each seed
and records the left target + reset EE (base frame, metric and int grid).

Recovery gate (per episode, against each arm's replay): |‖EE_reset − T‖ −
replay trajectory[0].dist_red| reported; < GATE_TOL_M passes. trajectory[0]
is logged during the FIRST execute step, not at reset, so a sub-mm residual
is expected; the distribution is printed so any larger gap is visible.

Output: logs/a15_targets_seed4500.json (consumed by a15_slope_probe.py).
"""
from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--seed_base", type=int, default=4500)
parser.add_argument("--n", type=int, default=100)
parser.add_argument("--level", type=int, default=-2)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import json  # noqa: E402

import numpy as np  # noqa: E402

from aiongenos.config import WorkspaceBounds  # noqa: E402
from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder  # noqa: E402
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402
from aiongenos.vlm.scalar_guard import position_metric_to_int  # noqa: E402

OUT = "logs/a15_targets_seed4500.json"


def main():
    env = ArenaEnvBuilder.build_env(level=args_cli.level, num_envs=1)
    iface = IsaacLabEnvInterface(env)
    robot = iface.robot
    b = WorkspaceBounds()
    rows = []
    for k in range(args_cli.n):
        seed = args_cli.seed_base + k
        iface.reset(seed=seed)
        root = robot.data.root_pos_w[0, :3].cpu().numpy()
        tgt_w, _ = iface._get_target_poses()
        ee_w = robot.data.body_pos_w[0, iface.left_body_idx].cpu().numpy()
        tgt_b, ee_b = tgt_w - root, ee_w - root
        tgt_i, _ = position_metric_to_int(*tgt_b, b.x_bounds, b.y_bounds, b.z_bounds)
        ee_i, _ = position_metric_to_int(*ee_b, b.x_bounds, b.y_bounds, b.z_bounds)
        rows.append({
            "ep_idx": k, "seed": seed,
            "target_b": tgt_b.tolist(), "ee_reset_b": ee_b.tolist(),
            "target_int": list(tgt_i), "ee_reset_int": list(ee_i),
            "dist_reset_m": float(np.linalg.norm(ee_w - tgt_w)),
        })
        print(f"[A15c] seed{seed}: target_b={np.round(tgt_b, 3).tolist()} int={list(tgt_i)} "
              f"dist_reset={rows[-1]['dist_reset_m']:.4f}", flush=True)
    with open(OUT, "w") as f:
        json.dump({"seed_base": args_cli.seed_base, "level": args_cli.level, "rows": rows}, f, indent=1)
    print(f"[A15c] wrote {OUT}", flush=True)
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
