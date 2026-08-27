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

# Per-round lead budget (m): the primitive clamps the requested cube waypoint
# displacement to this. A far PUSH_TO is NOT an error — it's the natural input
# to a segmented push: this round moves ≤8cm, the teacher re-plans next round
# from the new state. The clamp lives HERE (control budget), NOT in the parser
# (which only checks workspace bounds / format).
_LEAD_BUDGET_M = 0.08

# Contact-orientation reference basis (base frame, w,x,y,z): the Pin-7a standby
# EE orientation, measured in-sim (a sensible palm-toward-workspace pose the PI
# tuned). The contact orientation is this basis ROTATED about world-z to align
# the palm with the per-round push heading (see contact_orientation_b). The
# basis is a reference, not a hard-coded command — the executor never sees a
# literal quat; it gets the computed, direction-dependent orientation.
_CONTACT_QUAT_BASIS = (-0.217, -0.658, 0.226, -0.685)


def _quat_mul(a, b):
    """Hamilton product (w,x,y,z), pure-torch, no sim import."""
    aw, ax, ay, az = a[0], a[1], a[2], a[3]
    bw, bx, by, bz = b[0], b[1], b[2], b[3]
    return torch.stack([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ])


def contact_orientation_b(push_dir: torch.Tensor) -> torch.Tensor:
    """Contact EE orientation (base frame quat w,x,y,z) as a FUNCTION of the
    per-round push direction: the Pin-7a basis rotated about world-z so the
    palm faces the push heading. Direction-dependence is deterministic
    mechanical geometry (primitive-owned, Ledger entry b); the choice among
    equivalent orientations is gauge (0 bits). Degenerate push_dir → basis."""
    basis = torch.tensor(_CONTACT_QUAT_BASIS, dtype=push_dir.dtype, device=push_dir.device)
    if float(torch.norm(push_dir[:2])) < 1e-6:
        return basis
    heading = torch.atan2(push_dir[1], push_dir[0])   # world-z angle of push
    half = heading * 0.5
    zrot = torch.stack([torch.cos(half), torch.zeros_like(half),
                        torch.zeros_like(half), torch.sin(half)])  # rot about +z
    q = _quat_mul(zrot, basis)
    return q / torch.norm(q)


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


def push_toward_base(cube_pos_b: torch.Tensor, goal_pos_b: torch.Tensor):
    """Push primitive, all in BASE frame (the frame OSC pose_abs consumes).
    Given cube + goal in base frame, compute the behind-cube approach point
    (offset along the reversed cube→goal direction) — the EE contacts the
    cube's far face and drives it toward the goal. Returns (approach_b, info).

    All-base-frame avoids a base→world→base round-trip: the cube is
    converted to base once by the caller (via base_frame_target_from_world),
    the goal is already base (the command term's `.command`), and the result
    feeds the pose_abs action directly.
    """
    d = goal_pos_b - cube_pos_b
    n = torch.norm(d)
    if float(n) < 1e-6:
        approach_b = cube_pos_b.clone()  # cube at goal; hold on it
    else:
        approach_b = cube_pos_b - (d / n) * _APPROACH_OFFSET_M
    info = {"approach_b": approach_b.tolist(), "cube_goal_dist_m": float(n),
            "offset_m": _APPROACH_OFFSET_M}
    return approach_b, info


def push_segment_from_waypoint(cube_pos_b: torch.Tensor, waypoint_b: torch.Tensor):
    """WP1-③a per-round push primitive (base frame). The teacher emits a cube
    WAYPOINT (where it wants the cube to end up); this primitive:
      1. clamps the requested cube displacement to the per-round lead budget
         (≤8cm) — a far waypoint is a segmented-push input, not an error;
      2. computes the behind-cube APPROACH point (opposite the push direction)
         so the EE contacts the cube's near face and drives it toward the
         (clamped) waypoint.
    Returns (approach_b, clamped_target_b, info). All control lives here; the
    converter only translates (x,y)→this call. Pure tensor math, NO sim — the
    converter's unit test runs without Isaac.

    info carries the r-tracking raw material: requested vs clamped displacement,
    whether it was clamped, and the push direction."""
    d = waypoint_b - cube_pos_b
    n = float(torch.norm(d))
    clamped = n > _LEAD_BUDGET_M
    if n < 1e-6:
        target_b = cube_pos_b.clone()          # degenerate: waypoint == cube
        push_dir = torch.zeros_like(cube_pos_b)
        approach_b = cube_pos_b.clone()
    else:
        push_dir = d / n
        seg = min(n, _LEAD_BUDGET_M)            # clamp to lead budget
        target_b = cube_pos_b + push_dir * seg  # clamped cube target this round
        approach_b = cube_pos_b - push_dir * _APPROACH_OFFSET_M  # behind cube
    contact_quat_b = contact_orientation_b(push_dir)  # f(push_dir), palm→heading
    info = {
        "requested_disp_m": n,
        "clamped_disp_m": min(n, _LEAD_BUDGET_M),
        "was_clamped": clamped,
        "push_dir": push_dir.tolist(),
        "approach_b": approach_b.tolist(),
        "target_b": target_b.tolist(),
        "contact_quat_b": contact_quat_b.tolist(),
        "lead_budget_m": _LEAD_BUDGET_M,
    }
    return approach_b, target_b, contact_quat_b, info
