"""WP1-③a Pin-4c reachability scan with cube in place (Spec §1, REVISION 1 R4/R6).
Adapter from scripts/diagnostics/wp3a_reach_real.py.
RUN ON GPU BY OPS ONLY. AGENTS NEVER LAUNCH THIS SCRIPT.

Grid:
  - cube centre x in {0.34, 0.37, ..., 0.52}, y in {-0.02, 0.01, ..., 0.22} (3 cm step)
  - direction theta in {-90°, -75°, ..., +90°} (15° step) relative to +X
  - push distance d in {0.07, 0.10} m

Per configuration:
  1. Transit (R4): flies at standby z + 0.05 m to the point above the approach point,
     then descends to approach point at cube-centre z.
     Approach variants tried sequentially until success:
       V1: offset=1.0cm, yaw=0
       V2: offset=2.5cm, yaw=0
       V3: offset=2.5cm, yaw=theta (LEFT_TARGET_ORI Y=theta via push_body.command_quat)
       V4: offset=4.0cm, yaw=theta
     Check whether cube was disturbed during approach (>5 mm movement -> failure).
  2. Push: push to goal - u*half at cube-centre z.
     Each stage gets <= 3 rounds (execute_push_segment, TCP target, rest orientation, 90 steps).
  3. Outcome (R6): success = final cube->goal <= 5 cm in the world AND approach not disturbed.
     Record telemetry: min finger->cube, joint-limit margin, tau saturation, table guard clamps,
     pre-push displacement in cm, winning variant id, and elapsed time in seconds.
  4. Robustness:
     - Wall-clock timeout per variant (--variant_timeout_s, default: 180s).
     - NaN/non-finite state check after each stage -> recorded as 'nan' failure and reset.
     - Incremental checkpoint saving after every config.
     - --resume support to skip already-completed configs from existing JSON.

Outputs:
  logs/wp3a_reach_scan_p4c.json
  logs/wp3a_reach_scan_p4c_theta*.png (heatmaps if matplotlib available)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

# 3 solvable dry-run configurations
DRY_RUN_CONFIGS: list[tuple[float, float, int, float]] = [
    (0.40, 0.10, 0, 0.10),
    (0.40, 0.10, 60, 0.07),
    (0.40, 0.10, -60, 0.07),
]

# Approach variants tried sequentially until success
APPROACH_VARIANTS: list[dict[str, Any]] = [
    {"id": "V1", "offset_m": 0.010, "use_yaw": False},
    {"id": "V2", "offset_m": 0.025, "use_yaw": False},
    {"id": "V3", "offset_m": 0.025, "use_yaw": True},
    {"id": "V4", "offset_m": 0.040, "use_yaw": True},
]

CUBE_KEEP_OUT_X = 0.38  # hand keep-out at reset


class VariantTimeoutError(Exception):
    """Raised when an approach variant exceeds the wall-clock timeout."""
    pass


def _sigalrm_handler(signum, frame):
    raise VariantTimeoutError("Variant wall-clock timeout exceeded")


def is_on_table(pt_b: Sequence[float]) -> bool:
    """Check table bounds in base frame: x in [0.18, 0.90], y in [-0.45, 0.45]."""
    return 0.18 <= pt_b[0] <= 0.90 and -0.45 <= pt_b[1] <= 0.45


def filter_config(cx: float, cy: float, th_deg: int | float, d: float) -> str | None:
    """Returns skip reason if config should be skipped, else None."""
    if cx < CUBE_KEEP_OUT_X:
        return "hand_keepout"
    th_rad = math.radians(th_deg)
    gx = cx + d * math.cos(th_rad)
    gy = cy + d * math.sin(th_rad)
    if not is_on_table((gx, gy)):
        return "goal_off_table"
    return None


def parse_custom_configs(raw_str: str) -> list[tuple[float, float, int, float]]:
    """Parse custom configs string in format: 'x,y,th_deg,d;x,y,th_deg,d;...'"""
    configs = []
    items = [item.strip() for item in raw_str.split(";") if item.strip()]
    for item in items:
        parts = [p.strip() for p in item.split(",") if p.strip()]
        if len(parts) != 4:
            raise ValueError(f"Each config must have 4 comma-separated values (x,y,theta_deg,d), got: '{item}'")
        cx = float(parts[0])
        cy = float(parts[1])
        th_deg = int(round(float(parts[2])))
        d = float(parts[3])
        configs.append((cx, cy, th_deg, d))
    return configs


def parse_grid_override(raw_str: str, round_digits: int = 3) -> list[float]:
    """Parse comma-separated float grid, e.g. '0.34, 0.37, 0.40'."""
    return [round(float(p.strip()), round_digits) for p in raw_str.split(",") if p.strip()]


def save_checkpoint(output_path: str | Path, data: dict[str, Any]):
    """Incrementally and atomically write checkpoint JSON to disk."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = p.with_suffix(p.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)
        fp.flush()
        os.fsync(fp.fileno())
    tmp_path.replace(p)


def load_completed_keys(json_path: str | Path) -> tuple[set[tuple[float, float, int, float]], list[dict], list[dict]]:
    """Load completed config keys and existing results/skipped from a checkpoint JSON."""
    completed_keys = set()
    results = []
    skipped = []
    p = Path(json_path)
    if not p.exists():
        return completed_keys, results, skipped
    try:
        with open(p, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        results = data.get("results", [])
        skipped = data.get("skipped", [])
        for r in results:
            key = (round(float(r["cube_x"]), 3), round(float(r["cube_y"]), 3),
                   int(round(float(r["theta_deg"]))), round(float(r["dist"]), 3))
            completed_keys.add(key)
        for s in skipped:
            cfg = s.get("config")
            if cfg and len(cfg) >= 4:
                key = (round(float(cfg[0]), 3), round(float(cfg[1]), 3),
                       int(round(float(cfg[2]))), round(float(cfg[3]), 3))
                completed_keys.add(key)
    except Exception as e:
        print(f"[SCAN RESUME WARNING] Could not parse {json_path}: {e}", flush=True)
    return completed_keys, results, skipped


def check_state_finite(robot: Any, cube: Any, iface: Any) -> bool:
    """Check if robot joint positions and cube pose are finite (no NaN / Inf)."""
    try:
        import torch
        if hasattr(robot, "data") and hasattr(robot.data, "joint_pos"):
            q = robot.data.joint_pos[0]
            if not bool(torch.all(torch.isfinite(q))):
                return False
        if hasattr(cube, "data") and hasattr(cube.data, "root_pos_w"):
            pos = cube.data.root_pos_w[0]
            if not bool(torch.all(torch.isfinite(pos))):
                return False
        if hasattr(iface, "get_cube_pose_b"):
            c_b = torch.as_tensor(iface.get_cube_pose_b(), dtype=torch.float32)
            if not bool(torch.all(torch.isfinite(c_b))):
                return False
        if hasattr(iface, "get_left_tcp_pos_b"):
            tcp_b = torch.as_tensor(iface.get_left_tcp_pos_b(), dtype=torch.float32)
            if not bool(torch.all(torch.isfinite(tcp_b))):
                return False
        return True
    except Exception:
        return False


def run_config_variants(
    iface: Any,
    dev: Any,
    robot: Any,
    cube: Any,
    cx: float,
    cy: float,
    th_deg: int | float,
    d: float,
    variant_timeout_s: float = 180.0,
    half: float = 0.024,
    seg: int = 90,
    rounds_stage: int = 3,
    success_dist_m: float = 0.05,
    variants: Sequence[dict[str, Any]] = APPROACH_VARIANTS,
    finger_to_cube_fn: Optional[Callable[[], float]] = None,
    joint_margin_fn: Optional[Callable[[], tuple[str, float]]] = None,
    config_idx: int = 0,
    z_cube: float = 0.024,
    cube_spawn_z: float = 0.03,
    robot_base_z: float = 0.65,
) -> dict[str, Any]:
    """Execute approach variants sequentially for a single (cube, theta, d) configuration."""
    import numpy as np
    import torch
    from aiongenos.orchestrator import push_body as pb
    from aiongenos.vlm.parser import OriOffset

    t_config_start = time.time()
    th_rad = math.radians(th_deg)
    ux = math.cos(th_rad)
    uy = math.sin(th_rad)
    gx = cx + d * ux
    gy = cy + d * uy

    variants_tried = []
    winning_variant = None

    has_alarm = hasattr(signal, "SIGALRM") and hasattr(signal, "alarm")

    for v_idx, var in enumerate(variants):
        v_id = var["id"]
        offset_m = var["offset_m"]
        yaw_deg = th_deg if var["use_yaw"] else 0

        t_var_start = time.time()
        timed_out = False
        nan_detected = False
        failure_reason = None

        old_handler = None
        if has_alarm and variant_timeout_s > 0:
            try:
                old_handler = signal.signal(signal.SIGALRM, _sigalrm_handler)
                signal.alarm(max(1, int(math.ceil(variant_timeout_s))))
            except (ValueError, AttributeError):
                pass

        try:
            if time.time() - t_var_start > variant_timeout_s:
                raise VariantTimeoutError("Timeout before starting variant")

            # Reset env and cube/goal before each variant attempt
            iface.reset(seed=4700 + config_idx * 10 + v_idx)
            z_standby = float(iface.get_left_tcp_pos_b()[2])
            q_rest = iface.get_left_hand_quat_b()

            ori = OriOffset(p=0, y=int(round(yaw_deg)), r=0) if yaw_deg != 0 else None
            q_cmd = pb.command_quat(q_rest, ori)

            # Place cube and goal: write pose (7-dim) and zero velocity (6-dim)
            cube_pose_w = torch.tensor([[cx, cy, cube_spawn_z + robot_base_z, 1.0, 0.0, 0.0, 0.0]],
                                       device=dev, dtype=torch.float32)
            cube_vel_w = torch.zeros((1, 6), device=dev, dtype=torch.float32)
            cube.write_root_pose_to_sim(cube_pose_w)
            cube.write_root_velocity_to_sim(cube_vel_w)
            goal_b = [gx, gy, z_cube]

            # Approach point: cube - u*(half + offset_m)
            appr_xy = (cx - ux * (half + offset_m), cy - uy * (half + offset_m))
            transit_high = np.array([appr_xy[0], appr_xy[1], z_standby + 0.05])
            appr_pt = np.array([appr_xy[0], appr_xy[1], z_cube])
            push_end = np.array([gx - ux * half, gy - uy * half, z_cube])

            # Stage 1: fly high above approach point
            iface.execute_push_segment(torch.tensor(transit_high, dtype=torch.float32), q_cmd, seg, frame_every=0, target_is_tcp=True)
            if not check_state_finite(robot, cube, iface):
                nan_detected = True
                failure_reason = "nan"
                raise FloatingPointError("Non-finite state after Stage 1")

            if time.time() - t_var_start > variant_timeout_s:
                raise VariantTimeoutError("Timeout after Stage 1")

            # Stage 2: descend to approach point
            tau_warn_max = 0
            tau_flag_max = 0
            target_clamps = 0
            min_finger_dist = 999.0

            for _ in range(rounds_stage):
                if time.time() - t_var_start > variant_timeout_s:
                    raise VariantTimeoutError("Timeout during Stage 2")
                res_seg = iface.execute_push_segment(torch.tensor(appr_pt, dtype=torch.float32), q_cmd, seg, frame_every=0, target_is_tcp=True)
                tau_warn_max = max(tau_warn_max, res_seg.get("tau_warn_steps", 0))
                tau_flag_max = max(tau_flag_max, res_seg.get("tau_flag_steps", 0))
                if (res_seg.get("table_guard") or {}).get("target_clamp"):
                    target_clamps += 1
                if finger_to_cube_fn is not None:
                    min_finger_dist = min(min_finger_dist, finger_to_cube_fn())

            if not check_state_finite(robot, cube, iface):
                nan_detected = True
                failure_reason = "nan"
                raise FloatingPointError("Non-finite state after Stage 2")

            c_now = np.array(iface.get_cube_pose_b())
            cube_moved_pre = float(np.linalg.norm(c_now[:2] - np.array([cx, cy])))
            cube_moved_pre_cm = round(cube_moved_pre * 100.0, 2)
            disturbed_approach = (cube_moved_pre > 0.005)  # > 5mm disturbed

            # Stage 3: push to end
            for _ in range(rounds_stage):
                if time.time() - t_var_start > variant_timeout_s:
                    raise VariantTimeoutError("Timeout during Stage 3")
                res_seg = iface.execute_push_segment(torch.tensor(push_end, dtype=torch.float32), q_cmd, seg, frame_every=0, target_is_tcp=True)
                tau_warn_max = max(tau_warn_max, res_seg.get("tau_warn_steps", 0))
                tau_flag_max = max(tau_flag_max, res_seg.get("tau_flag_steps", 0))
                if (res_seg.get("table_guard") or {}).get("target_clamp"):
                    target_clamps += 1
                if finger_to_cube_fn is not None:
                    min_finger_dist = min(min_finger_dist, finger_to_cube_fn())

            if not check_state_finite(robot, cube, iface):
                nan_detected = True
                failure_reason = "nan"
                raise FloatingPointError("Non-finite state after Stage 3")

            c_final = np.array(iface.get_cube_pose_b())
            final_cube_goal_dist = float(np.linalg.norm(c_final[:2] - np.array(goal_b[:2])))
            tight_joint, marg_deg = joint_margin_fn() if joint_margin_fn else ("none", 0.0)

            # Success requires final cube->goal <= 5cm AND not disturbed during approach
            v_success = (final_cube_goal_dist <= success_dist_m) and (not disturbed_approach)
            if not v_success and failure_reason is None:
                failure_reason = "disturbed_approach" if disturbed_approach else "goal_distance"

        except VariantTimeoutError:
            timed_out = True
            failure_reason = "timeout"
            v_success = False
            final_cube_goal_dist = 9.99
            disturbed_approach = True
            cube_moved_pre_cm = 99.9
            tight_joint, marg_deg = ("timeout", 0.0)
            tau_warn_max = 0
            tau_flag_max = 0
            target_clamps = 0
            min_finger_dist = 999.0
        except FloatingPointError:
            nan_detected = True
            failure_reason = "nan"
            v_success = False
            final_cube_goal_dist = 9.99
            disturbed_approach = True
            cube_moved_pre_cm = 99.9
            tight_joint, marg_deg = ("nan", 0.0)
            tau_warn_max = 0
            tau_flag_max = 0
            target_clamps = 0
            min_finger_dist = 999.0
        finally:
            if has_alarm and variant_timeout_s > 0:
                try:
                    signal.alarm(0)
                    if old_handler is not None:
                        signal.signal(signal.SIGALRM, old_handler)
                except (ValueError, AttributeError):
                    pass

            if timed_out or nan_detected:
                # Full clean reset on timeout or NaN before continuing
                try:
                    iface.reset(seed=4700 + config_idx * 10 + v_idx + 999)
                except Exception:
                    pass

        var_elapsed = round(time.time() - t_var_start, 2)
        v_res = {
            "variant": v_id,
            "offset_m": offset_m,
            "yaw_deg": yaw_deg,
            "success": v_success,
            "failure_reason": failure_reason,
            "disturbed_approach": disturbed_approach,
            "pre_push_cube_displacement_cm": cube_moved_pre_cm,
            "final_cube_goal_m": round(final_cube_goal_dist, 4),
            "min_finger_to_cube_cm": round(min_finger_dist, 2),
            "tightest_joint": [tight_joint, marg_deg],
            "tau_warn_steps_max": tau_warn_max,
            "tau_flag_steps_max": tau_flag_max,
            "target_clamps": target_clamps,
            "elapsed_s": var_elapsed,
        }
        variants_tried.append(v_res)

        if v_success:
            winning_variant = v_res
            break

    overall_success = (winning_variant is not None)
    variant_used = winning_variant["variant"] if winning_variant else None
    best_v = winning_variant or variants_tried[-1]
    config_elapsed_s = round(time.time() - t_config_start, 2)

    return {
        "cube_x": cx,
        "cube_y": cy,
        "theta_deg": th_deg,
        "dist": d,
        "goal_x": round(gx, 4),
        "goal_y": round(gy, 4),
        "success": overall_success,
        "variant_used": variant_used,
        "disturbed_approach": best_v["disturbed_approach"],
        "pre_push_cube_displacement_cm": best_v["pre_push_cube_displacement_cm"],
        "final_cube_goal_m": best_v["final_cube_goal_m"],
        "min_finger_to_cube_cm": best_v["min_finger_to_cube_cm"],
        "tightest_joint": best_v["tightest_joint"],
        "tau_warn_steps_max": best_v["tau_warn_steps_max"],
        "tau_flag_steps_max": best_v["tau_flag_steps_max"],
        "target_clamps": best_v["target_clamps"],
        "elapsed_s": config_elapsed_s,
        "variants_tried": variants_tried,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry_run", action="store_true", help="Run 3 solvable sanity-check configurations")
    p.add_argument("--configs", type=str, default=None, help="Custom configurations: 'x,y,th_deg,d;...'")
    p.add_argument("--x_grid", type=str, default=None, help="Override X grid: '0.34,0.37,0.40,...'")
    p.add_argument("--y_grid", type=str, default=None, help="Override Y grid: '-0.02,0.01,0.04,...'")
    p.add_argument("--theta_grid", type=str, default=None, help="Override theta deg grid: '-90,-60,-30,0,30,60,90'")
    p.add_argument("--variant_timeout_s", type=float, default=180.0, help="Wall-clock timeout in seconds per approach variant (default: 180s)")
    p.add_argument("--resume", action="store_true", help="Resume from existing output JSON, skipping completed configs")
    p.add_argument("--output", type=str, default="logs/wp3a_reach_scan_p4c.json")
    from isaaclab.app import AppLauncher
    AppLauncher.add_app_launcher_args(p)
    a = p.parse_args()
    a.enable_cameras = True

    sim_app = None
    env = None

    try:
        app = AppLauncher(a)
        sim_app = app.app

        import gymnasium as gym  # noqa: E402
        import numpy as np  # noqa: E402
        import torch  # noqa: E402
        from isaaclab.utils.math import quat_apply, quat_apply_inverse  # noqa: E402
        from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
        from pxr import Usd, UsdGeom  # noqa: E402
        import omni.usd  # noqa: E402

        import aiongenos.tasks  # noqa: E402,F401
        from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402
        from aiongenos.tasks.WP1_contact_testbed import push_s3a_cfg as C  # noqa: E402

        GID = "Isaac-AionGenos-WP1-Push-TopCam-v0"
        SEG = 90
        ROUNDS_STAGE = 3
        SUCCESS_DIST_M = 0.05
        HALF = C._CUBE_HALF_H

        # Grid definitions (default)
        X_GRID = [round(0.34 + i * 0.03, 3) for i in range(7)]   # 0.34 to 0.52
        Y_GRID = [round(-0.02 + i * 0.03, 3) for i in range(9)]  # -0.02 to 0.22
        THETA_DEG = list(range(-90, 91, 15))                      # -90 to +90, step 15
        DIST_GRID = [0.07, 0.10]

        x_grid = parse_grid_override(a.x_grid) if a.x_grid else X_GRID
        y_grid = parse_grid_override(a.y_grid) if a.y_grid else Y_GRID
        theta_grid = [int(round(t)) for t in parse_grid_override(a.theta_grid, round_digits=0)] if a.theta_grid else THETA_DEG

        env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
        iface = IsaacLabEnvInterface(env)
        u = env.unwrapped
        dev = u.device
        robot = iface.robot
        cube = u.scene["object"]
        names = robot.data.body_names
        jnames = robot.data.joint_names
        LJ = [i for i, n in enumerate(jnames) if n.startswith("openarm_left_joint")]
        stage = omni.usd.get_context().get_stage()

        def body_local_points(body: str, stride: int = 20) -> torch.Tensor:
            bp = stage.GetPrimAtPath(f"/World/envs/env_0/Robot/{body}")
            mb = np.array(UsdGeom.Xformable(bp).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
            out = []
            for sub in Usd.PrimRange(bp, Usd.TraverseInstanceProxies()):
                if sub.IsA(UsdGeom.Mesh) and "collision" in str(sub.GetPath()):
                    pts = np.array(UsdGeom.Mesh(sub).GetPointsAttr().Get(), dtype=float)[::stride]
                    mm = np.array(UsdGeom.Xformable(sub).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
                    out.append((np.c_[pts, np.ones(len(pts))] @ (mm @ np.linalg.inv(mb)))[:, :3])
            return torch.tensor(np.concatenate(out), dtype=torch.float32, device=dev)

        iface.reset(seed=4700)
        GEOM = {b: body_local_points(b) for b in ("openarm_left_left_finger", "openarm_left_right_finger",
                                                   "openarm_left_link7")}

        def world_points(body: str) -> torch.Tensor:
            k = names.index(body)
            pts = GEOM[body]
            return quat_apply(robot.data.body_quat_w[0, k].expand(len(pts), 4), pts) + robot.data.body_pos_w[0, k]

        def finger_to_cube_cm() -> float:
            pw = torch.cat([world_points("openarm_left_left_finger"), world_points("openarm_left_right_finger")])
            c, q = cube.data.root_pos_w[0, :3], cube.data.root_quat_w[0, :4]
            loc = quat_apply_inverse(q.expand(len(pw), 4), pw - c)
            d = torch.clamp(loc.abs() - HALF, min=0.0).norm(dim=1)
            return float(d.min()) * 100

        def get_joint_margin_deg() -> tuple[str, float]:
            q = robot.data.joint_pos[0, LJ]
            lim = robot.data.soft_joint_pos_limits[0, LJ]
            marg = torch.rad2deg(torch.minimum(q - lim[:, 0], lim[:, 1] - q))
            k = int(torch.argmin(marg))
            return jnames[LJ[k]], round(float(marg[k]), 1)

        completed_keys = set()
        results = []
        skipped = []

        if a.resume and Path(a.output).exists():
            completed_keys, results, skipped = load_completed_keys(a.output)
            print(f"[SCAN RESUME] Resuming from {a.output}: found {len(completed_keys)} completed configs ({len(results)} results, {len(skipped)} skipped)", flush=True)

        if a.configs:
            configs = parse_custom_configs(a.configs)
            print(f"[SCAN] Using {len(configs)} custom configurations from --configs", flush=True)
        elif a.dry_run:
            configs = list(DRY_RUN_CONFIGS)
            print(f"[SCAN] Using {len(configs)} dry-run configurations: {configs}", flush=True)
        else:
            configs = []
            for cx in x_grid:
                for cy in y_grid:
                    for th_deg in theta_grid:
                        for d in DIST_GRID:
                            configs.append((cx, cy, th_deg, d))
            print(f"[SCAN] Total grid configurations: {len(configs)} (X={len(x_grid)}, Y={len(y_grid)}, theta={len(theta_grid)})", flush=True)

        out_data = {
            "x_grid": x_grid,
            "y_grid": y_grid,
            "theta_deg_grid": theta_grid,
            "dist_grid": DIST_GRID,
            "results": results,
            "skipped": skipped,
        }

        for idx, (cx, cy, th_deg, d) in enumerate(configs):
            cfg_key = (round(cx, 3), round(cy, 3), int(round(th_deg)), round(d, 3))
            if cfg_key in completed_keys:
                print(f"[SCAN {idx+1}/{len(configs)}] ({cx}, {cy}, th={th_deg}°, d={d}) -> SKIPPED (already completed in checkpoint)", flush=True)
                continue

            skip_reason = filter_config(cx, cy, th_deg, d)
            if skip_reason is not None:
                skipped.append({"config": (cx, cy, th_deg, d), "reason": skip_reason})
                completed_keys.add(cfg_key)
                save_checkpoint(a.output, out_data)
                print(f"[SCAN {idx+1}/{len(configs)}] ({cx}, {cy}, th={th_deg}°, d={d}) -> SKIPPED ({skip_reason}) [0.0s]", flush=True)
                continue

            rec = run_config_variants(
                iface=iface,
                dev=dev,
                robot=robot,
                cube=cube,
                cx=cx,
                cy=cy,
                th_deg=th_deg,
                d=d,
                variant_timeout_s=a.variant_timeout_s,
                half=HALF,
                seg=SEG,
                rounds_stage=ROUNDS_STAGE,
                success_dist_m=SUCCESS_DIST_M,
                variants=APPROACH_VARIANTS,
                finger_to_cube_fn=finger_to_cube_cm,
                joint_margin_fn=get_joint_margin_deg,
                config_idx=idx,
                z_cube=C._CUBE_REST_Z_B,
                cube_spawn_z=C._CUBE_SPAWN_Z,
                robot_base_z=C._ROBOT_BASE_Z,
            )

            results.append(rec)
            completed_keys.add(cfg_key)
            save_checkpoint(a.output, out_data)

            overall_success = rec["success"]
            variant_used = rec["variant_used"]
            v_str = f"variant={variant_used}" if overall_success else f"all {len(rec['variants_tried'])} variants failed"
            print(
                f"[SCAN {idx+1}/{len(configs)}] ({cx}, {cy}, th={th_deg}°, d={d}) -> "
                f"success={overall_success} ({v_str}, dist={rec['final_cube_goal_m']*100:.1f}cm, "
                f"disp={rec['pre_push_cube_displacement_cm']:.2f}cm, disturbed={rec['disturbed_approach']}) "
                f"[{rec['elapsed_s']:.1f}s]",
                flush=True,
            )

        save_checkpoint(a.output, out_data)
        print(f"[SCAN] Saved {len(results)} records to {a.output}", flush=True)

        n_total = len(configs)
        n_skipped = len(skipped)
        n_tested = len(results)
        n_success = sum(1 for r in results if r.get("success", False))
        sr = (n_success / n_tested * 100.0) if n_tested > 0 else 0.0

        print(
            f"[SCAN SUMMARY] Total configs: {n_total}, Tested: {n_tested}, "
            f"Success: {n_success} ({sr:.1f}%), Skipped: {n_skipped}",
            flush=True,
        )

        if not a.dry_run and len(results) == 0:
            print("[SCAN ERROR] Scan produced 0 results (all configurations were skipped). Failing scan.", flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(2)

        # Clean shutdown only on success
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
