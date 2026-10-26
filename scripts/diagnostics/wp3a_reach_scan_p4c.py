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
     Approach point: cube - u*(half + 1 cm).
     Check whether cube was disturbed during approach (>5 mm movement -> failure).
  2. Push: push to goal - u*half at cube-centre z.
     Each stage gets <= 3 rounds (execute_push_segment, TCP target, rest orientation, 90 steps).
  3. Outcome (R6): success = final cube->goal <= 5 cm in the world.
     Record telemetry: min finger->cube, joint-limit margin, tau saturation, table guard clamps.

Outputs:
  logs/wp3a_reach_scan_p4c.json
  logs/wp3a_reach_scan_p4c_theta*.png (heatmaps if matplotlib available)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Sequence

# 3 solvable dry-run configurations
DRY_RUN_CONFIGS: list[tuple[float, float, int, float]] = [
    (0.40, 0.10, 0, 0.10),
    (0.40, 0.10, 60, 0.07),
    (0.40, 0.10, -60, 0.07),
]

CUBE_KEEP_OUT_X = 0.38  # hand keep-out at reset


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry_run", action="store_true", help="Run 3 solvable sanity-check configurations")
    p.add_argument("--configs", type=str, default=None, help="Custom configurations: 'x,y,th_deg,d;...'")
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
        from aiongenos.orchestrator import push_body as pb  # noqa: E402
        from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402
        from aiongenos.tasks.WP1_contact_testbed import push_s3a_cfg as C  # noqa: E402

        GID = "Isaac-AionGenos-WP1-Push-TopCam-v0"
        SEG = 90
        ROUNDS_STAGE = 3
        SUCCESS_DIST_M = 0.05
        HALF = C._CUBE_HALF_H

        # Grid definitions
        X_GRID = [round(0.34 + i * 0.03, 3) for i in range(7)]   # 0.34 to 0.52
        Y_GRID = [round(-0.02 + i * 0.03, 3) for i in range(9)]  # -0.02 to 0.22
        THETA_DEG = list(range(-90, 91, 15))                      # -90 to +90, step 15
        DIST_GRID = [0.07, 0.10]

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

        results = []
        skipped = []

        if a.configs:
            configs = parse_custom_configs(a.configs)
            print(f"[SCAN] Using {len(configs)} custom configurations from --configs", flush=True)
        elif a.dry_run:
            configs = list(DRY_RUN_CONFIGS)
            print(f"[SCAN] Using {len(configs)} dry-run configurations: {configs}", flush=True)
        else:
            configs = []
            for cx in X_GRID:
                for cy in Y_GRID:
                    for th_deg in THETA_DEG:
                        for d in DIST_GRID:
                            configs.append((cx, cy, th_deg, d))
            print(f"[SCAN] Total grid configurations: {len(configs)}", flush=True)

        for idx, (cx, cy, th_deg, d) in enumerate(configs):
            skip_reason = filter_config(cx, cy, th_deg, d)
            if skip_reason is not None:
                skipped.append({"config": (cx, cy, th_deg, d), "reason": skip_reason})
                print(f"[SCAN {idx+1}/{len(configs)}] ({cx}, {cy}, th={th_deg}°, d={d}) -> SKIPPED ({skip_reason})", flush=True)
                continue

            th_rad = math.radians(th_deg)
            ux = math.cos(th_rad)
            uy = math.sin(th_rad)
            gx = cx + d * ux
            gy = cy + d * uy

            iface.reset(seed=4700 + idx)
            z_standby = float(iface.get_left_tcp_pos_b()[2])
            z_cube = C._CUBE_REST_Z_B
            q_rest = iface.get_left_hand_quat_b()
            q_cmd = pb.command_quat(q_rest, None)

            # Place cube and goal: write pose (7-dim) and zero velocity (6-dim)
            cube_pose_w = torch.tensor([[cx, cy, C._CUBE_SPAWN_Z + C._ROBOT_BASE_Z, 1.0, 0.0, 0.0, 0.0]],
                                       device=dev, dtype=torch.float32)
            cube_vel_w = torch.zeros((1, 6), device=dev, dtype=torch.float32)
            cube.write_root_pose_to_sim(cube_pose_w)
            cube.write_root_velocity_to_sim(cube_vel_w)
            goal_b = [gx, gy, z_cube]

            # Approach point
            appr_xy = (cx - ux * (HALF + 0.01), cy - uy * (HALF + 0.01))
            # R4: Transit flies at standby z + 0.05m to above approach point, then descends to cube-centre z
            transit_high = np.array([appr_xy[0], appr_xy[1], z_standby + 0.05])
            appr_pt = np.array([appr_xy[0], appr_xy[1], z_cube])
            push_end = np.array([gx - ux * HALF, gy - uy * HALF, z_cube])

            # Stage 1: fly high above approach point
            iface.execute_push_segment(torch.tensor(transit_high, dtype=torch.float32), q_cmd, SEG, frame_every=0, target_is_tcp=True)

            # Stage 2: descend to approach point
            tau_warn_max = 0
            tau_flag_max = 0
            target_clamps = 0
            min_finger_dist = 999.0

            for _ in range(ROUNDS_STAGE):
                seg = iface.execute_push_segment(torch.tensor(appr_pt, dtype=torch.float32), q_cmd, SEG, frame_every=0, target_is_tcp=True)
                tau_warn_max = max(tau_warn_max, seg.get("tau_warn_steps", 0))
                tau_flag_max = max(tau_flag_max, seg.get("tau_flag_steps", 0))
                if (seg.get("table_guard") or {}).get("target_clamp"):
                    target_clamps += 1
                min_finger_dist = min(min_finger_dist, finger_to_cube_cm())

            c_now = np.array(iface.get_cube_pose_b())
            cube_moved_pre = float(np.linalg.norm(c_now[:2] - np.array([cx, cy])))
            disturbed_approach = (cube_moved_pre > 0.005)  # > 5mm disturbed

            # Stage 3: push to end
            for _ in range(ROUNDS_STAGE):
                seg = iface.execute_push_segment(torch.tensor(push_end, dtype=torch.float32), q_cmd, SEG, frame_every=0, target_is_tcp=True)
                tau_warn_max = max(tau_warn_max, seg.get("tau_warn_steps", 0))
                tau_flag_max = max(tau_flag_max, seg.get("tau_flag_steps", 0))
                if (seg.get("table_guard") or {}).get("target_clamp"):
                    target_clamps += 1
                min_finger_dist = min(min_finger_dist, finger_to_cube_cm())

            c_final = np.array(iface.get_cube_pose_b())
            final_cube_goal_dist = float(np.linalg.norm(c_final[:2] - np.array(goal_b[:2])))
            tight_joint, marg_deg = get_joint_margin_deg()

            # R6: success = outcome only (cube->goal <= 5cm) AND not disturbed during approach
            success = (final_cube_goal_dist <= SUCCESS_DIST_M) and (not disturbed_approach)

            rec = {
                "cube_x": cx,
                "cube_y": cy,
                "theta_deg": th_deg,
                "dist": d,
                "goal_x": round(gx, 4),
                "goal_y": round(gy, 4),
                "success": success,
                "disturbed_approach": disturbed_approach,
                "final_cube_goal_m": round(final_cube_goal_dist, 4),
                "min_finger_to_cube_cm": round(min_finger_dist, 2),
                "tightest_joint": [tight_joint, marg_deg],
                "tau_warn_steps_max": tau_warn_max,
                "tau_flag_steps_max": tau_flag_max,
                "target_clamps": target_clamps,
            }
            results.append(rec)

            if a.dry_run or len(configs) <= 10 or idx % 50 == 0 or idx == len(configs) - 1:
                print(
                    f"[SCAN {idx+1}/{len(configs)}] ({cx}, {cy}, th={th_deg}°, d={d}) -> "
                    f"success={success} (dist={final_cube_goal_dist*100:.1f}cm, disturbed={disturbed_approach})",
                    flush=True,
                )

        out_data = {
            "x_grid": X_GRID,
            "y_grid": Y_GRID,
            "theta_deg_grid": THETA_DEG,
            "dist_grid": DIST_GRID,
            "results": results,
            "skipped": skipped,
        }
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        with open(a.output, "w") as fp:
            json.dump(out_data, fp, indent=2)
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
