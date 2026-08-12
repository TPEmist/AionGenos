"""Frame gate (Rule 5, 2026-08-12) — the ONLY sanctioned way to build an OSC
pose_abs target, plus the push_toward primitive.

Two same-frame stalls (WP1-① #2 first attempt; the hold-smoke) came from
hand-writing a WORLD position into a pose_abs slot. OSC pose_abs on the
reach env expects a BASE-FRAME pose (that is why #2 succeeded once it used
the env's own `ee_pose` command, which is base-frame). This module:

  * `base_frame_target_from_world(env, pos_w, quat_w)` — convert a world
    pose to the base frame the OSC action expects, via the robot root
    (the same base-frame convention as _get_ee_poses / _get_target_poses).
  * `assert_command_frame(env)` — a boot-time sanity assert that the reach
    command term exposes a base-frame command (fails loudly if the API
    drifts, so a silent wrong-frame can't recur).
  * `push_toward(env, cube_pos_w, goal_pos_w, arm)` — the push primitive:
    computes the behind-cube approach point (offset along the reversed
    cube→goal vector) and returns the base-frame pose_abs target for the
    pushing EE. The TEACHER only chooses cube+goal; the geometry is here.

Pure functions on torch tensors; no hand-written pose_abs anywhere else.
"""
from __future__ import annotations

import torch
from isaaclab.utils.math import subtract_frame_transforms

# Behind-cube approach offset (m): how far behind the cube (opposite the
# goal direction) the EE aims, so it contacts the cube's far face and pushes
# it toward the goal. ~half a cube + margin.
_APPROACH_OFFSET_M = 0.06
_IDENTITY_QUAT = (1.0, 0.0, 0.0, 0.0)


def base_frame_target_from_world(env, pos_w: torch.Tensor) -> torch.Tensor:
    """World position → base-frame position, via IsaacLab's
    subtract_frame_transforms (Rule 5 sanctioned util). This is the frame the
    OSC pose_abs action consumes — the SAME base frame as the command term's
    `.command` (= pose_command_b) that WP1-① #2 verified works. Full rotation
    handled (NOT a naive world−root subtraction, which drops the root's
    orientation and was the residual frame error in the first hold-smoke)."""
    robot = env.unwrapped.scene["robot"]
    root_p = robot.data.root_pos_w[0:1, :3]
    root_q = robot.data.root_quat_w[0:1, :4]
    pos_b, _ = subtract_frame_transforms(root_p, root_q, pos_w.unsqueeze(0))
    return pos_b[0]


def assert_command_frame(env) -> None:
    """Fail loudly if the command term no longer exposes the expected
    base-frame command API (guards against silent frame drift)."""
    cm = env.unwrapped.command_manager
    term = cm.get_term("left_ee_pose")
    assert hasattr(term, "command"), (
        "frame gate: command term lacks .command (base-frame) — API drift; "
        "do NOT fall back to hand-set world targets (Rule 5)."
    )


def push_toward(env, cube_pos_w: torch.Tensor, goal_pos_w: torch.Tensor):
    """Push primitive. Given cube + goal in WORLD frame, compute the
    behind-cube approach point and return (pose_abs_target_base, info).
    The EE aims at cube minus a step along the (cube→goal) direction, so it
    contacts the far face and drives the cube toward the goal.

    Returns a base-frame position target (the OSC pose_abs consumes base
    frame; quaternion left identity — push is planar, orientation is not the
    controlled DoF here).
    """
    d = goal_pos_w - cube_pos_w
    n = torch.norm(d)
    if float(n) < 1e-6:
        approach_w = cube_pos_w.clone()  # cube already at goal; hold on it
    else:
        approach_w = cube_pos_w - (d / n) * _APPROACH_OFFSET_M
    tgt_b = base_frame_target_from_world(env, approach_w)
    info = {
        "approach_w": approach_w.tolist(),
        "cube_goal_dist_m": float(n),
        "offset_m": _APPROACH_OFFSET_M,
    }
    return tgt_b, info
