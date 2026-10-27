"""Pin-4c runtime gate — cube spawn REGION + polar cube-relative goal (Spec §2, REVISION 1).
RUN ON GPU BY OPS ONLY. AGENTS NEVER LAUNCH THIS SCRIPT.

All bounds are imported from push_s3a_cfg (single source of truth).
Over N resets (e.g. 200 seeds) it checks:
  1. HARD check: command term's last_sample (theta, dist) is strictly inside spec (1e-6)
  2. RUNTIME check: post-reset cube/goal angle and dist, with tolerances:
     - angle tolerance: ±1.0° (to account for ~0.7mm post-reset physics shift, R3)
     - dist tolerance: ±2 mm (0.002 m)
  3. Cube lands inside PIN4C_CUBE_REGION_* and stays (settle drift < 1cm)
  4. Goal does not resample mid-episode
  5. Determinism: the same seed twice -> identical cube + goal
Exit 0 = ALL PASS, 1 = FAIL.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Sequence, Tuple


def inside(v: float, rng: Sequence[float], eps: float = 1e-3) -> bool:
    return rng[0] - eps <= v <= rng[1] + eps


def check_pin4c_sample(
    c0: Sequence[float],
    g0: Sequence[float],
    theta_max_rad: float,
    dist_range: Sequence[float],
    cube_region_x: Sequence[float],
    cube_region_y: Sequence[float],
    last_sample: Optional[Dict[str, Any]] = None,
    angle_tol_deg: float = 1.0,
    dist_tol_m: float = 0.002,
    eps: float = 1e-3,
) -> Dict[str, Any]:
    """Check a single (cube, goal) sample using two-layer verification:
      - HARD: command term's last_sample (theta, dist) must be strictly in range (1e-6).
      - RUNTIME: post-reset cube/goal angle & dist with tolerance (±1.0°, ±2 mm).
    """
    dx = g0[0] - c0[0]
    dy = g0[1] - c0[1]
    dist = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    angle_deg = math.degrees(angle)

    # 1. HARD check on last_sample (if provided by sampler term)
    hard_ok = True
    hard_angle_ok = True
    hard_dist_ok = True
    sampled_theta = None
    sampled_dist = None
    if last_sample:
        if "theta" in last_sample and last_sample["theta"] is not None:
            sampled_theta = float(last_sample["theta"])
            hard_angle_ok = abs(sampled_theta) <= theta_max_rad + 1e-6
        if "dist" in last_sample and last_sample["dist"] is not None:
            sampled_dist = float(last_sample["dist"])
            hard_dist_ok = (dist_range[0] - 1e-6 <= sampled_dist <= dist_range[1] + 1e-6)
        hard_ok = hard_angle_ok and hard_dist_ok

    # 2. RUNTIME check on post-reset coordinates
    in_cube_x = inside(c0[0], cube_region_x, eps)
    in_cube_y = inside(c0[1], cube_region_y, eps)

    angle_tol_rad = math.radians(angle_tol_deg)
    in_runtime_angle = abs(angle) <= theta_max_rad + angle_tol_rad
    in_runtime_dist = (dist_range[0] - dist_tol_m <= dist <= dist_range[1] + dist_tol_m)

    in_exact_angle = abs(angle) <= theta_max_rad + 1e-6
    in_exact_dist = (dist_range[0] - 1e-6 <= dist <= dist_range[1] + 1e-6)

    runtime_ok = in_cube_x and in_cube_y and in_runtime_angle and in_runtime_dist
    ok = hard_ok and runtime_ok

    return {
        "ok": ok,
        "hard_ok": hard_ok,
        "runtime_ok": runtime_ok,
        "hard_angle_ok": hard_angle_ok,
        "hard_dist_ok": hard_dist_ok,
        "dist": dist,
        "angle_rad": angle,
        "angle_deg": angle_deg,
        "sampled_theta": sampled_theta,
        "sampled_dist": sampled_dist,
        "in_cube_x": in_cube_x,
        "in_cube_y": in_cube_y,
        "in_dist": in_runtime_dist,
        "in_angle": in_runtime_angle,
        "in_exact_angle": in_exact_angle,
        "in_exact_dist": in_exact_dist,
        "exceeds_exact": (not in_exact_angle) or (not in_exact_dist),
        "exceeds_tolerance": (not in_runtime_angle) or (not in_runtime_dist),
    }


def evaluate_pin4c_distribution(
    samples: Sequence[Any],
    theta_max_rad: float,
    dist_range: Sequence[float],
    cube_region_x: Sequence[float],
    cube_region_y: Sequence[float],
    n_bins: int = 6,
    angle_tol_deg: float = 1.0,
    dist_tol_m: float = 0.002,
    eps: float = 1e-3,
) -> Dict[str, Any]:
    """Evaluate uniformity of angle distribution and bounds across N samples."""
    all_ok = True
    fail_count = 0
    hard_fail_count = 0
    runtime_fail_count = 0
    exceeds_exact_count = 0
    exceeds_tol_count = 0

    angles = []
    dists = []
    cube_xs = []
    cube_ys = []

    for item in samples:
        if isinstance(item, dict):
            c0 = item["c0"]
            g0 = item["g0"]
            last_samp = item.get("last_sample")
        elif len(item) == 3:
            c0, g0, last_samp = item
        else:
            c0, g0 = item[0], item[1]
            last_samp = None

        res = check_pin4c_sample(
            c0=c0,
            g0=g0,
            theta_max_rad=theta_max_rad,
            dist_range=dist_range,
            cube_region_x=cube_region_x,
            cube_region_y=cube_region_y,
            last_sample=last_samp,
            angle_tol_deg=angle_tol_deg,
            dist_tol_m=dist_tol_m,
            eps=eps,
        )

        if not res["ok"]:
            all_ok = False
            fail_count += 1
        if not res["hard_ok"]:
            hard_fail_count += 1
        if not res["runtime_ok"]:
            runtime_fail_count += 1
        if res["exceeds_exact"]:
            exceeds_exact_count += 1
        if res["exceeds_tolerance"]:
            exceeds_tol_count += 1

        angles.append(res["angle_rad"])
        dists.append(res["dist"])
        cube_xs.append(c0[0])
        cube_ys.append(c0[1])

    # Check uniformity of angle: divide [-theta_max, theta_max] into n_bins
    bin_counts = [0] * n_bins
    span = 2.0 * theta_max_rad
    for ang in angles:
        norm = (ang + theta_max_rad) / span
        b_idx = min(n_bins - 1, max(0, int(norm * n_bins)))
        bin_counts[b_idx] += 1

    expected_per_bin = len(samples) / n_bins if n_bins > 0 else 0.0
    chi2 = sum((c - expected_per_bin) ** 2 / expected_per_bin for c in bin_counts) if expected_per_bin > 0 else 0.0

    # Uniformity check: no starved bin (<20% expected) and chi2 below critical value
    uniformity_ok = True
    if len(samples) >= 60:
        for c in bin_counts:
            if c < 0.2 * expected_per_bin:
                uniformity_ok = False
        if chi2 > 20.515:  # chi2 critical value for df=5 at p=0.001
            uniformity_ok = False

    return {
        "ok": all_ok and uniformity_ok,
        "all_bounds_ok": all_ok,
        "uniformity_ok": uniformity_ok,
        "n_samples": len(samples),
        "fail_count": fail_count,
        "hard_fail_count": hard_fail_count,
        "runtime_fail_count": runtime_fail_count,
        "exceeds_exact_count": exceeds_exact_count,
        "exceeds_tolerance_count": exceeds_tol_count,
        "bin_counts": bin_counts,
        "expected_per_bin": expected_per_bin,
        "chi2": chi2,
        "dist_min": min(dists) if dists else 0.0,
        "dist_max": max(dists) if dists else 0.0,
        "angle_min_rad": min(angles) if angles else 0.0,
        "angle_max_rad": max(angles) if angles else 0.0,
        "angle_min_deg": math.degrees(min(angles)) if angles else 0.0,
        "angle_max_deg": math.degrees(max(angles)) if angles else 0.0,
        "cube_x_min": min(cube_xs) if cube_xs else 0.0,
        "cube_x_max": max(cube_xs) if cube_xs else 0.0,
        "cube_y_min": min(cube_ys) if cube_ys else 0.0,
        "cube_y_max": max(cube_ys) if cube_ys else 0.0,
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
            last_samp = None
            u = getattr(env, "unwrapped", env)
            cmd_mgr = getattr(u, "command_manager", None)
            if cmd_mgr is not None and hasattr(cmd_mgr, "get_term"):
                try:
                    term = cmd_mgr.get_term("left_ee_pose")
                    if hasattr(term, "get_last_sample"):
                        last_samp = term.get_last_sample()
                    elif hasattr(term, "last_sample"):
                        last_samp = dict(term.last_sample)
                except Exception:
                    pass
            for _ in range(SETTLE):
                env.step(zero)
            return c0, g0, np.array(iface.get_cube_pose_b()), np.array(iface.get_goal_pose_b()), last_samp

        samples = []
        fail_count = 0
        hard_fail_count = 0
        runtime_fail_count = 0
        exceeds_exact_count = 0
        exceeds_tol_count = 0
        hard_samples_theta = []
        hard_samples_dist = []

        print(f"[P4C GATE] Running runtime gate for {args.n} resets (seed0={args.seed0})...", flush=True)

        for k in range(args.n):
            seed = args.seed0 + k
            c0, g0, c1, g1, last_samp = reset_settle(seed)
            c0b, g0b, _, _, _ = reset_settle(seed)

            determ = np.linalg.norm(c0 - c0b) * 100 < 0.5 and np.allclose(g0, g0b, atol=1e-5)
            drift = np.linalg.norm(c1[:2] - c0[:2]) * 100
            goal_static = np.allclose(g0, g1, atol=1e-5)

            res = check_pin4c_sample(
                c0=c0,
                g0=g0,
                theta_max_rad=C.PIN4C_THETA_MAX,
                dist_range=C.PIN4C_DIST_RANGE,
                cube_region_x=C.PIN4C_CUBE_REGION_X,
                cube_region_y=C.PIN4C_CUBE_REGION_Y,
                last_sample=last_samp,
                angle_tol_deg=1.0,
                dist_tol_m=0.002,
            )
            ok = determ and (drift < 1.0) and goal_static and res["ok"]
            if not ok:
                fail_count += 1
                print(f"[P4C GATE FAIL] seed {seed}: determ={determ} drift={drift:.2f}cm static={goal_static} check={res}", flush=True)

            if not res["hard_ok"]:
                hard_fail_count += 1
            if not res["runtime_ok"]:
                runtime_fail_count += 1
            if res["exceeds_exact"]:
                exceeds_exact_count += 1
            if res["exceeds_tolerance"]:
                exceeds_tol_count += 1

            if res["sampled_theta"] is not None:
                hard_samples_theta.append(res["sampled_theta"])
            if res["sampled_dist"] is not None:
                hard_samples_dist.append(res["sampled_dist"])

            samples.append((c0, g0, last_samp))

        dist_eval = evaluate_pin4c_distribution(
            samples,
            theta_max_rad=C.PIN4C_THETA_MAX,
            dist_range=C.PIN4C_DIST_RANGE,
            cube_region_x=C.PIN4C_CUBE_REGION_X,
            cube_region_y=C.PIN4C_CUBE_REGION_Y,
            n_bins=6,
            angle_tol_deg=1.0,
            dist_tol_m=0.002,
        )

        print("\n" + "=" * 64, flush=True)
        print("[P4C GATE SUMMARY]", flush=True)
        print(f"  Resets evaluated: {args.n}", flush=True)
        print(f"  FAIL count: {fail_count} (HARD fails: {hard_fail_count}, RUNTIME fails: {runtime_fail_count})", flush=True)
        print(f"  Exceeds exact bounds (within tolerance): {exceeds_exact_count}", flush=True)
        print(f"  Exceeds tolerance (angle > ±1.0° or dist > ±2mm): {exceeds_tol_count}", flush=True)
        print(f"  θ (angle) runtime range: [{dist_eval['angle_min_deg']:.2f}°, {dist_eval['angle_max_deg']:.2f}°] "
              f"(spec: ±{math.degrees(C.PIN4C_THETA_MAX):.1f}°, tol: ±1.0°)", flush=True)
        if hard_samples_theta:
            print(f"  θ (angle) sampled range: [{math.degrees(min(hard_samples_theta)):.4f}°, {math.degrees(max(hard_samples_theta)):.4f}°]", flush=True)
        print(f"  d (dist) runtime range:  [{dist_eval['dist_min']*100:.2f}, {dist_eval['dist_max']*100:.2f}] cm "
              f"(spec: [{C.PIN4C_DIST_RANGE[0]*100:.1f}, {C.PIN4C_DIST_RANGE[1]*100:.1f}] cm, tol: ±2mm)", flush=True)
        if hard_samples_dist:
            print(f"  d (dist) sampled range:  [{min(hard_samples_dist)*100:.4f}, {max(hard_samples_dist)*100:.4f}] cm", flush=True)
        print(f"  Cube X range: [{dist_eval['cube_x_min']:.4f}, {dist_eval['cube_x_max']:.4f}] m (spec: {C.PIN4C_CUBE_REGION_X})", flush=True)
        print(f"  Cube Y range: [{dist_eval['cube_y_min']:.4f}, {dist_eval['cube_y_max']:.4f}] m (spec: {C.PIN4C_CUBE_REGION_Y})", flush=True)
        print(f"  Angle histogram (6 bins): {dist_eval['bin_counts']}", flush=True)
        print(f"  Uniformity test: {'PASS' if dist_eval['uniformity_ok'] else 'FAIL'} "
              f"(chi2={dist_eval['chi2']:.2f}, expected/bin={dist_eval['expected_per_bin']:.1f})", flush=True)
        print("=" * 64 + "\n", flush=True)

        if fail_count == 0 and dist_eval["ok"]:
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
            print(f"[P4C GATE] FAIL (fails={fail_count}, dist_eval_ok={dist_eval['ok']})", flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(1)

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
