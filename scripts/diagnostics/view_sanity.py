"""View-sanity script — render one frame per (reset_pose, camera) candidate.

Useful for C3+C4 (pre-reach arm pose + camera angle) — we don't yet know
which joint setpoint puts the EEs in the right place, and we don't want
to burn 14-min collect runs to find out. This script:

1. Loads the L0a-Left env (single-arm reach on left target).
2. For each candidate (target_joint_pos, camera_offset) pair, monkey-patches
   the env config and resets, then dumps a 256x256 RGB to disk.
3. Names files so you can ``feh`` through them and pick the best.

NOT a complete eval / collect — no VLM calls, no IK servo, just a static
"what does the scene look like at reset" sanity check.

Usage:
    python3 scripts/diagnostics/view_sanity.py \\
        --out_dir data/view_sanity_dumps \\
        [--num_resets_per_pose 3] \\
        [--headless --enable_cameras]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Logging — same shape as run_collect.py so AppLauncher doesn't drop us.
import logging as _logging
_handler = _logging.StreamHandler(sys.stdout)
_handler.setFormatter(_logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
for _name in ("aiongenos", "__main__"):
    _l = _logging.getLogger(_name)
    _l.setLevel(_logging.INFO)
    _l.addHandler(_handler)
    _l.propagate = False

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out_dir", type=Path, default=Path("data/view_sanity_dumps"))
parser.add_argument("--num_resets_per_pose", type=int, default=3,
                    help="How many random resets to sample per candidate pose")
parser.add_argument("--camera_preset", type=str, default="default",
                    choices=("default", "pitch55", "pitch70"),
                    help="Camera preset baked at env-build time. Re-run with "
                         "different presets to compare cameras (each run "
                         "produces its own files).")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import isaaclab.sim as sim_utils
from isaaclab.sensors import CameraCfg

from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.mdp.reset import reset_joints_to_target_with_offset
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.curriculum.ladder import CurriculumLadder
import aiongenos.tasks  # noqa: F401  registers gym envs


# ── Candidate pose dictionaries (joint_name_regex → radians). ─────────
# OpenArm bimanual default is all zeros. Joint geometry roughly:
#   joint1 = shoulder yaw  (positive rotates outward)
#   joint2 = shoulder pitch (positive rotates downward in front)
#   joint3 = upper-arm roll
#   joint4 = elbow pitch (positive flexes)
#   joint5..7 = wrist orientation
#
# We'll only target joint2 (shoulder down) and joint4 (elbow flex) so the
# arms reach forward over the table; everything else stays at default.
CANDIDATE_POSES: dict[str, dict[str, float]] = {
    "P0_default_zero": {},  # asset default — for comparison
    "P1_mild_forward": {
        "openarm_left_joint2": 0.5,
        "openarm_left_joint4": 0.8,
        "openarm_right_joint2": 0.5,
        "openarm_right_joint4": 0.8,
    },
    "P2_strong_forward": {
        "openarm_left_joint2": 0.9,
        "openarm_left_joint4": 1.2,
        "openarm_right_joint2": 0.9,
        "openarm_right_joint4": 1.2,
    },
    "P3_mild_with_yaw_outward": {
        # Slightly fan the elbows outward so the wrists clear each other
        "openarm_left_joint1": 0.3,
        "openarm_left_joint2": 0.5,
        "openarm_left_joint4": 0.8,
        "openarm_right_joint1": -0.3,
        "openarm_right_joint2": 0.5,
        "openarm_right_joint4": 0.8,
    },
}


# Camera (pos, quat) candidates. Quat is wxyz, world convention.
# Current production: pos=(0.1, 0.0, 0.85), rot ≈ (cos(35°/2), 0, sin(35°/2), 0)
#   = (0.95372, 0, 0.30071, 0). That's pitch +35° (looking forward+down).
# We try a steeper downward pitch to keep cube in view center and a
# slightly higher mount.
CANDIDATE_CAMERAS: dict[str, dict] = {
    # Production (current): pitch 35° down. Cube tends to land in lower-left
    # of the frame because of robot-mount + workspace geometry.
    "default": {
        "pos": (0.1, 0.0, 0.85),
        "rot": (0.95372, 0.0, 0.30071, 0.0),
    },
    "pitch55": {
        "pos": (0.05, 0.0, 0.95),
        "rot": (0.90631, 0.0, 0.42262, 0.0),
    },
    "pitch70": {
        "pos": (-0.05, 0.0, 1.0),
        "rot": (0.81915, 0.0, 0.57358, 0.0),
    },
}


def _set_pose(env, target_pose: dict[str, float]) -> None:
    """Live-patch the env's reset event for the next reset (pose only)."""
    unwrapped = env.unwrapped
    cfg = unwrapped.cfg

    cfg.events.reset_robot_joints = EventTerm(
        func=reset_joints_to_target_with_offset,
        mode="reset",
        params={
            "target_joint_pos": target_pose,
            "position_range": (-0.05, 0.05),
            "velocity_range": (0.0, 0.0),
        },
    )
    from isaaclab.managers import EventManager
    unwrapped.event_manager = EventManager(cfg.events, unwrapped)


def _build_env_with_camera(camera_preset: str):
    """Build the L0a-Left env, optionally overriding the camera offset."""
    gym_id = CurriculumLadder.get_gym_id(-2)
    env_cfg = parse_env_cfg(gym_id, num_envs=1, use_fabric=True)

    if camera_preset != "default":
        cam_cfg_lookup = CANDIDATE_CAMERAS[camera_preset]
        env_cfg.scene.camera = CameraCfg(
            prim_path="{ENV_REGEX_NS}/Robot/Camera",
            update_period=0.0,
            height=256,
            width=256,
            data_types=["rgb"],
            spawn=sim_utils.PinholeCameraCfg(
                focal_length=12.0,
                focus_distance=400.0,
                horizontal_aperture=45.0,
                clipping_range=(0.1, 1.0e5),
            ),
            offset=CameraCfg.OffsetCfg(
                pos=cam_cfg_lookup["pos"],
                rot=cam_cfg_lookup["rot"],
                convention="world",
            ),
        )
        logger.info(f"Camera preset applied: {camera_preset} {cam_cfg_lookup}")
    else:
        logger.info("Camera preset: default (production)")

    env = gym.make(gym_id, cfg=env_cfg)
    return env


def main() -> None:
    args_cli.out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output dir: {args_cli.out_dir.resolve()}")
    logger.info(f"Camera preset: {args_cli.camera_preset}")

    env = _build_env_with_camera(args_cli.camera_preset)
    env_iface = IsaacLabEnvInterface(env)
    manifest: list[dict] = []
    cam_name = args_cli.camera_preset

    try:
        for pose_name, pose_dict in CANDIDATE_POSES.items():
            _set_pose(env, pose_dict)

            for sample in range(args_cli.num_resets_per_pose):
                env_iface.reset()
                rgb = env_iface.get_rgb()
                if not rgb:
                    logger.warning(f"  empty RGB for {pose_name} #{sample}")
                    continue
                fname = f"cam-{cam_name}__{pose_name}__sample{sample:02d}.png"
                out = args_cli.out_dir / fname
                out.write_bytes(rgb)

                try:
                    l_pos, r_pos, _, _ = env_iface._get_ee_poses()
                    ee_info = {
                        "left_ee_b_m": [float(v) for v in l_pos],
                        "right_ee_b_m": [float(v) for v in r_pos],
                    }
                except Exception:
                    ee_info = {}

                manifest.append({
                    "file": str(out.name),
                    "camera": cam_name,
                    "pose": pose_name,
                    "pose_dict": pose_dict,
                    "sample": sample,
                    **ee_info,
                })
                logger.info(f"  wrote {out.name}  EE={ee_info}")

        manifest_path = args_cli.out_dir / f"manifest_cam-{cam_name}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        logger.info(f"Done. Manifest at {manifest_path}")
    finally:
        env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
