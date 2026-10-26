"""Pin-4c runtime gate — cube spawn REGION + polar cube-relative goal (Spec §2, REVISION 1).
RUN ON GPU BY OPS ONLY. AGENTS NEVER LAUNCH THIS SCRIPT.

All bounds are imported from push_s3a_cfg (single source of truth).
Over N resets (e.g. 200 seeds) it checks, at runtime:
  * goal − cube distance in [0.07, 0.10] m
  * angle in [-theta_max, theta_max] rad
  * angle histogram roughly uniform across bins
  * cube lands inside PIN4C_CUBE_REGION_* and stays (settle drift < 1cm)
  * goal does not resample mid-episode
  * determinism: the same seed twice -> identical cube + goal
Exit 0 = ALL PASS, 3 = FAIL.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import traceback
from typing import Any, Dict, List, Sequence, Tuple


def inside(v: float, rng: Sequence[float], eps: float = 1e-3) -> bool:
    return rng[0] - eps <= v <= rng[1] + eps


def check_pin4c_sample(
    c0: Sequence[float],
    g0: Sequence[float],
    theta_max_rad: float,
    dist_range: Sequence[float],
    cube_region_x: Sequence[float],
    cube_region_y: Sequence[float],
    eps: float = 1e-3,
) -> Dict[str, Any]:
    """Pure CPU checking function for a single (cube, goal) runtime sample."""
    dx = g0[0] - c0[0]
    dy = g0[1] - c0[1]
    dist = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)

    in_cube_x = inside(c0[0], cube_region_x, eps)
    in_cube_y = inside(c0[1], cube_region_y, eps)
    in_dist = inside(dist, dist_range, eps)
    in_angle = abs(angle) <= theta_max_rad + eps

    ok = in_cube_x and in_cube_y and in_dist and in_angle
    return {
        "ok": ok,
        "dist": dist,
        "angle_rad": angle,
        "angle_deg": math.degrees(angle),
        "in_cube_x": in_cube_x,
        "in_cube_y": in_cube_y,
        "in_dist": in_dist,
        "in_angle": in_angle,
    }


def evaluate_pin4c_distribution(
    samples: Sequence[Tuple[Sequence[float], Sequence[float]]],
    theta_max_rad: float,
    dist_range: Sequence[float],
    cube_region_x: Sequence[float],
    cube_region_y: Sequence[float],
    n_bins: int = 6,
) -> Dict[str, Any]:
    """Evaluate uniformity of angle distribution and bounds across N samples."""
    all_ok = True
    angles = []
    dists = []
    cube_xs = []
    cube_ys = []

    for c0, g0 in samples:
        res = check_pin4c_sample(c0, g0, theta_max_rad, dist_range, cube_region_x, cube_region_y)
        if not res["ok"]:
            all_ok = False
        angles.append(res["angle_rad"])
        dists.append(res["dist"])
        cube_xs.append(c0[0])
        cube_ys.append(c0[1])

    # Check uniformity of angle: divide [-theta_max, theta_max] into n_bins
    bin_counts = [0] * n_bins
    span = 2.0 * theta_max_rad
    for ang in angles:
        # Normalized position in [0, 1]
        norm = (ang + theta_max_rad) / span
        b_idx = min(n_bins - 1, max(0, int(norm * n_bins)))
        bin_counts[b_idx] += 1

    expected_per_bin = len(samples) / n_bins if n_bins > 0 else 0
    # For uniformity: check that no bin is completely starved if N is large enough (e.g. N >= 60)
    uniformity_ok = True
    if len(samples) >= 60:
        for c in bin_counts:
            if c < 0.2 * expected_per_bin:  # severely starved bin
                uniformity_ok = False
                all_ok = False

    return {
        "ok": all_ok and uniformity_ok,
        "all_bounds_ok": all_ok,
        "uniformity_ok": uniformity_ok,
        "n_samples": len(samples),
        "bin_counts": bin_counts,
        "dist_min": min(dists) if dists else 0.0,
        "dist_max": max(dists) if dists else 0.0,
        "angle_min_deg": math.degrees(min(angles)) if angles else 0.0,
        "angle_max_deg": math.degrees(max(angles)) if angles else 0.0,
    }


def main():
    from isaaclab.app import AppLauncher
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed0", type=int, default=4700)
    AppLauncher.add_app_launcher_args(parser)
    args = parser.parse_args()
    args.enable_cameras = True

    launcher = None
    sim_app = None
    env = None

    try:
        launcher = AppLauncher(args)
        sim_app = launcher.app

        import gymnasium as gym
        import numpy as np
        import torch
        from isaaclab_tasks.utils import parse_env_cfg
        import aiongenos.tasks  # noqa
        from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
        from aiongenos.tasks.WP1_contact_testbed import push_s3a_cfg as C

        GID = "Isaac-AionGenos-WP1-Push-P4c-v0"
        SETTLE = 30
        env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
        iface = IsaacLabEnvInterface(env)
        zero = torch.zeros((1, env.action_space.shape[-1]), device=env.unwrapped.device)

        def reset_settle(seed):
            iface.reset(seed=seed)
            c0 = np.array(iface.get_cube_pose_b())
            g0 = np.array(iface.get_goal_pose_b())
            for _ in range(SETTLE):
                env.step(zero)
            return c0, g0, np.array(iface.get_cube_pose_b()), np.array(iface.get_goal_pose_b())

        samples = []
        allpass = True
        print(f"[P4C GATE] Running runtime gate for {args.n} resets (seed0={args.seed0})...", flush=True)

        for k in range(args.n):
            seed = args.seed0 + k
            c0, g0, c1, g1 = reset_settle(seed)
            c0b, g0b, _, _ = reset_settle(seed)

            determ = np.linalg.norm(c0 - c0b) * 100 < 0.5 and np.allclose(g0, g0b, atol=1e-5)
            drift = np.linalg.norm(c1[:2] - c0[:2]) * 100
            goal_static = np.allclose(g0, g1, atol=1e-5)

            res = check_pin4c_sample(c0, g0, C.PIN4C_THETA_MAX, C.PIN4C_DIST_RANGE,
                                     C.PIN4C_CUBE_REGION_X, C.PIN4C_CUBE_REGION_Y)
            ok = determ and drift < 1.0 and goal_static and res["ok"]
            if not ok:
                allpass = False
                print(f"[P4C GATE FAIL] seed {seed}: determ={determ} drift={drift:.2f}cm static={goal_static} check={res}", flush=True)
            samples.append((c0, g0))

        dist_eval = evaluate_pin4c_distribution(samples, C.PIN4C_THETA_MAX, C.PIN4C_DIST_RANGE,
                                                C.PIN4C_CUBE_REGION_X, C.PIN4C_CUBE_REGION_Y)
        print(f"[P4C GATE] Evaluated {args.n} resets:", flush=True)
        print(f"  dist range: [{dist_eval['dist_min']:.4f}, {dist_eval['dist_max']:.4f}] m (spec: {C.PIN4C_DIST_RANGE})", flush=True)
        print(f"  angle range: [{dist_eval['angle_min_deg']:.1f}°, {dist_eval['angle_max_deg']:.1f}°] (spec: ±{math.degrees(C.PIN4C_THETA_MAX):.1f}°)", flush=True)
        print(f"  angle bin counts: {dist_eval['bin_counts']} (uniformity_ok={dist_eval['uniformity_ok']})", flush=True)

        if allpass and dist_eval["ok"]:
            print("[P4C GATE] ALL PASS", flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            if env is not None:
                try:
                    env.close()
                except BaseException:
                    pass
            if sim_app is not None:
                try:
                    sim_app.close()
                except BaseException:
                    pass
            sys.exit(0)
        else:
            print("[P4C GATE] FAIL", flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(3)

    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
