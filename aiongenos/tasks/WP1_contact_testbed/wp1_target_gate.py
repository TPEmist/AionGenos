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

# Pin-7a reference orientation (base frame, w,x,y,z): the standby EE pose. Per
# PI ruling it is NOT the command basis — the neutral frame is defined
# GEOMETRICALLY from the motion direction (below); Pin-7a only resolves the
# wrist-winding gauge (when multiple orientations satisfy the geometry, pick the
# one nearest Pin-7a). Executor never sees a literal quat.
_PIN7A_QUAT = (-0.217, -0.658, 0.226, -0.685)


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


def _mat_to_quat(R):
    """3x3 rotation matrix (base) → quat (w,x,y,z), pure-torch (Shepperd)."""
    m = R
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if float(t) > 0:
        s = torch.sqrt(t + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif float(m[0, 0]) > float(m[1, 1]) and float(m[0, 0]) > float(m[2, 2]):
        s = torch.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif float(m[1, 1]) > float(m[2, 2]):
        s = torch.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = torch.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    q = torch.stack([w, x, y, z])
    return q / torch.norm(q)


# Which EE local axes map to the neutral frame axes. The neutral frame is
# (x_n = push heading on table, z_n = up, y_n = z_n × x_n). We want the EE's
# CONTACT-FACE NORMAL to point along −x_n (face the cube, along the push) and
# the palm flat on the table. The mapping of EE-local → neutral axes is
# calibrated so that at push=+x the result is the wrist-winding nearest Pin-7a
# (gauge choice). Columns of R_be = neutral-frame axes expressed as the EE
# body axes' images. Verified/adjusted in-sim by wp3a probes.
def neutral_contact_orientation_b(push_dir: torch.Tensor,
                                  prev_x_n: "torch.Tensor | None" = None):
    """Neutral contact EE orientation (base-frame quat w,x,y,z) computed
    GEOMETRICALLY from the push direction (PI spec 2026-10-01):
      x_n = push_dir projected to the table plane, unit
      z_n = table normal (base +z, up)
      y_n = z_n × x_n
    Contact-face normal along −x_n (face the cube, along push), palm flat on the
    table. Degenerate (|push_dir_xy|≈0 → hold / pure-vertical): reuse prev_x_n
    (hysteresis) to avoid a frame flip / wrist snap.

    Returns (quat_b, x_n) — x_n is returned so the caller can thread it as
    prev_x_n next segment and record it (per-round raw material)."""
    z_n = torch.tensor([0.0, 0.0, 1.0], dtype=push_dir.dtype, device=push_dir.device)
    xy = push_dir.clone()
    xy[2] = 0.0
    n = float(torch.norm(xy))
    if n < 1e-6:
        if prev_x_n is not None:
            x_n = prev_x_n
        else:
            x_n = torch.tensor([1.0, 0.0, 0.0], dtype=push_dir.dtype, device=push_dir.device)
    else:
        x_n = xy / n
    # The EE body's local +Z axis is the GRIPPER FINGER / CONTACT direction
    # (measured in-sim: openarm_left_ee_tcp offset = [0,0,+0.093] in hand-local
    # → +Z points out of the fingers). So the EE local +Z column must point
    # along the CONTACT direction = −x_n (the fingers face the cube, into the
    # push). The EE local +X was wrongly used before → fingers pointed at the
    # ceiling, the wrist did the pushing (PI human-eye catch 2026-10-02).
    #
    # Build R_be with columns = EE body (X, Y, Z) axes expressed in base:
    #   Z_col (fingers)  = −x_n            (point fingers into the push)
    #   X_col            = chosen so the palm/hand lies flat (use z_n up as a
    #                       reference), re-orthogonalized.
    z_col = -x_n                               # fingers point into the push
    # X_col ⟂ z_col, as close to table-up (z_n) as possible → palm flat
    x_col = z_n - torch.dot(z_n, z_col) * z_col
    if float(torch.norm(x_col)) < 1e-6:        # z_col ∥ z_n (vertical push) → fall back
        x_col = torch.tensor([1.0, 0.0, 0.0], dtype=push_dir.dtype, device=push_dir.device)
    x_col = x_col / torch.norm(x_col)
    y_col = torch.linalg.cross(z_col, x_col)
    y_col = y_col / torch.norm(y_col)
    x_col = torch.linalg.cross(y_col, z_col)   # re-orthogonalize
    R = torch.stack([x_col, y_col, z_col], dim=1)  # columns = EE X,Y,Z in base
    q = _mat_to_quat(R)
    return q, x_n


def contact_orientation_b(push_dir: torch.Tensor) -> torch.Tensor:
    """Back-compat shim (returns just the quat) for probes that call the old
    name; the primitive uses neutral_contact_orientation_b for the (quat, x_n)."""
    q, _ = neutral_contact_orientation_b(push_dir)
    return q


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


def _euler_zyx_to_quat(p_deg, y_deg, r_deg, device, dtype):
    """ORI offset (degrees) → quat, applied in the neutral frame in z-y-x order
    (A-spec v2: p=pitch about y_n, y=yaw about z_n, r=roll about x_n). Returns
    the OFFSET quat (to be composed with the neutral orientation)."""
    import math as _m
    def axis_quat(axis, deg):
        a = torch.tensor(deg * _m.pi / 180.0 * 0.5, device=device, dtype=dtype)
        c, s = torch.cos(a), torch.sin(a)
        v = torch.tensor(axis, device=device, dtype=dtype) * s
        return torch.stack([c, v[0], v[1], v[2]])
    qz = axis_quat([0, 0, 1], y_deg)   # yaw about z_n
    qy = axis_quat([0, 1, 0], p_deg)   # pitch about y_n
    qx = axis_quat([1, 0, 0], r_deg)   # roll about x_n
    return _quat_mul(_quat_mul(qz, qy), qx)   # z-y-x order


def push_segment_from_waypoint(cube_pos_b: torch.Tensor, waypoint_b: torch.Tensor,
                               ori_offset_deg=None, prev_x_n=None):
    """WP1-③a per-round push primitive (base frame). The teacher emits a cube
    WAYPOINT (where it wants the cube to end up); this primitive:
      1. clamps the requested cube displacement to the per-round lead budget
         (≤8cm) — a far waypoint is a segmented-push input, not an error;
      2. computes the behind-cube APPROACH point (opposite the push direction);
      3. computes the NEUTRAL contact orientation geometrically from the push
         direction (neutral_contact_orientation_b), then composes the teacher's
         optional ORI OFFSET (p,y,r degrees, z-y-x in the neutral frame).
    Returns (approach_b, clamped_target_b, contact_quat_b, info). All control
    lives here; the converter only translates. Pure tensor math, NO sim.

    ori_offset_deg: (p,y,r) in degrees or None (None → neutral). prev_x_n:
    previous segment's neutral x-axis, threaded for degenerate-direction
    hysteresis. info carries r-tracking raw material (disp, clamp, push_dir,
    x_n, whether ORI was applied)."""
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

    neutral_q, x_n = neutral_contact_orientation_b(push_dir, prev_x_n=prev_x_n)
    if ori_offset_deg is not None and any(abs(v) > 1e-6 for v in ori_offset_deg):
        off = _euler_zyx_to_quat(ori_offset_deg[0], ori_offset_deg[1], ori_offset_deg[2],
                                 push_dir.device, push_dir.dtype)
        contact_quat_b = _quat_mul(neutral_q, off)   # neutral ∘ offset
        contact_quat_b = contact_quat_b / torch.norm(contact_quat_b)
        ori_applied = True
    else:
        contact_quat_b = neutral_q
        ori_applied = False
    info = {
        "requested_disp_m": n,
        "clamped_disp_m": min(n, _LEAD_BUDGET_M),
        "was_clamped": clamped,
        "push_dir": push_dir.tolist(),
        "x_n": x_n.tolist(),
        "approach_b": approach_b.tolist(),
        "target_b": target_b.tolist(),
        "contact_quat_b": contact_quat_b.tolist(),
        "ori_offset_deg": list(ori_offset_deg) if ori_offset_deg is not None else None,
        "ori_applied": ori_applied,
        "lead_budget_m": _LEAD_BUDGET_M,
    }
    return approach_b, target_b, contact_quat_b, info
