"""WP1-③a push — body geometry for the observation/action interface (PI ruling
2026-10-05, revision of the push interface).

Design rule (AionGenos): the model observes IMAGE + PROPRIOCEPTION only. Object
positions are perception, never oracle-fed. Everything here is about the BODY:

* EEF reference point = the TCP (fingertip / contact pad, body
  ``openarm_left_ee_tcp``). State reports the TCP; targets are TCP targets; the
  executor converts TCP ↔ hand (the OSC body) with the hand-local TCP offset
  MEASURED LIVE at reset (never a hardcoded 0.093).
* Orientation: no computed "contact orientation" (that was an opinion — all
  pose decisions belong to the brain). The neutral is the REST orientation of
  the hand (Pin-7a standby, read live after reset), and the teacher's ORI offset
  rotates it about fixed BASE-frame axes:
      R_cmd = Rz(Y) · Ry(P) · Rx(R) · R_rest
  (P about base y, Y about base z, R about base x; right-hand rule, degrees).
* Contact report: TCP / hand-link distances to the cube's oriented box and the
  anatomy of the first link near the cube when it starts moving — numbers in
  place of "please look at the GIF". Link points are body ORIGINS (not meshes):
  a distance is a lower-resolution proxy for contact, labelled as such.

Quaternions are (w, x, y, z), base frame (robot root has identity rotation).
"""
from __future__ import annotations

import math
from typing import Sequence

import torch

TCP_BODY = "openarm_left_ee_tcp"
# Contact-anatomy classes by body-name substring (first match wins). Link
# origins only; "finger" includes the TCP pad.
_ANATOMY = (("finger", "finger"), ("tcp", "finger"), ("hand", "palm"),
            ("link7", "wrist"), ("link6", "wrist"), ("link5", "forearm"))
CUBE_MOVE_EPS_M = 0.002   # displacement that counts as "the cube started moving"


def quat_mul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    aw, ax, ay, az = a.unbind(-1)
    bw, bx, by, bz = b.unbind(-1)
    return torch.stack([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ], dim=-1)


def quat_conj(q: torch.Tensor) -> torch.Tensor:
    return q * torch.tensor([1.0, -1.0, -1.0, -1.0], device=q.device, dtype=q.dtype)


def quat_rotate(q: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    qv = torch.cat([torch.zeros_like(v[..., :1]), v], dim=-1)
    return quat_mul(quat_mul(q, qv), quat_conj(q))[..., 1:]


def _axis_quat(axis: Sequence[float], deg: float, like: torch.Tensor) -> torch.Tensor:
    half = math.radians(deg) * 0.5
    ax = torch.tensor(axis, device=like.device, dtype=like.dtype)
    return torch.cat([torch.tensor([math.cos(half)], device=like.device, dtype=like.dtype),
                      ax * math.sin(half)])


def base_offset_quat(p_deg: float, y_deg: float, r_deg: float, like: torch.Tensor) -> torch.Tensor:
    """Rz(Y)·Ry(P)·Rx(R) about fixed BASE axes."""
    qz = _axis_quat((0, 0, 1), y_deg, like)
    qy = _axis_quat((0, 1, 0), p_deg, like)
    qx = _axis_quat((1, 0, 0), r_deg, like)
    return quat_mul(quat_mul(qz, qy), qx)


def command_quat(q_rest: torch.Tensor, ori=None) -> torch.Tensor:
    """Commanded hand orientation: rest orientation, optionally rotated by the
    teacher's base-axis ORI offset (P, Y, R in degrees). No other source."""
    if ori is None or not (ori.p or ori.y or ori.r):
        return q_rest.clone()
    q = quat_mul(base_offset_quat(ori.p, ori.y, ori.r, q_rest), q_rest)
    return q / torch.norm(q)


def quat_angle_deg(q_a: torch.Tensor, q_b: torch.Tensor) -> float:
    """Geodesic angle between two orientations (degrees)."""
    d = float(torch.abs(torch.sum(q_a * q_b)).clamp(max=1.0))
    return math.degrees(2.0 * math.acos(d))


def tcp_offset_local(robot, hand_idx: int, tcp_idx: int) -> torch.Tensor:
    """Hand-local TCP offset, measured live: R_hand^T (p_tcp − p_hand)."""
    p_h = robot.data.body_pos_w[0, hand_idx, :3]
    p_t = robot.data.body_pos_w[0, tcp_idx, :3]
    q_h = robot.data.body_quat_w[0, hand_idx, :4]
    return quat_rotate(quat_conj(q_h), p_t - p_h)


def hand_target_from_tcp(tcp_target_b: torch.Tensor, q_cmd: torch.Tensor,
                         offset_local: torch.Tensor) -> torch.Tensor:
    """Hand (OSC body) position that places the TCP at tcp_target under q_cmd."""
    return tcp_target_b - quat_rotate(q_cmd, offset_local)


def point_to_box_dist(p_w: torch.Tensor, box_pos_w: torch.Tensor, box_quat_w: torch.Tensor,
                      half: float) -> float:
    """Distance (m) from a point to an oriented cube (0 if inside)."""
    local = quat_rotate(quat_conj(box_quat_w), p_w - box_pos_w)
    excess = (local.abs() - half).clamp(min=0.0)
    return float(torch.norm(excess))


def anatomy_of(body_name: str) -> str:
    n = body_name.lower()
    for key, cls in _ANATOMY:
        if key in n:
            return cls
    return "other"


def left_contact_bodies(robot) -> list[tuple[int, str]]:
    """(index, name) of left-arm bodies used for the contact report."""
    out = []
    for i, n in enumerate(robot.data.body_names):
        ln = n.lower()
        if "left" in ln and anatomy_of(n) != "other":
            out.append((i, n))
    return out


# ── Static-scene collision safety guard (PI ruling 2026-10-05; SAFETY, not
# knowledge) ─────────────────────────────────────────────────────────────────
# Any real arm has a "never command into the static scene" interlock. The guard
# covers STATIC colliders only — awkward-but-free poses (e.g. below table-top
# height outside the table footprint) are NOT blocked: they waste rounds, are
# observable, and are the model's to learn. Static colliders, all MEASURED from
# the live USD stage (world-aligned bboxes → base frame), never hardcoded:
#   * table: a TCP point over the footprint below top + margin is LIFTED to
#     top + margin (the bbox spans the legs, so only the top slab is a face);
#   * robot body (torso/column link, fixed to the base): a point inside the
#     inflated box is projected to the NEAREST face outside it;
#   * ground plane: z is raised to ground + margin.
# The scene has no separate stand prim (the base is fixed at its height); if
# one is added it must be listed in STATIC_BOXES to be guarded.
TABLE_GUARD_MARGIN_M = 0.010
STATIC_BOXES = ("Robot/openarm_body_link",)   # projected to nearest face
_ENV = "/World/envs/env_0"


def _bbox_b(stage, path: str, root):
    from pxr import Usd, UsdGeom

    prim = stage.GetPrimAtPath(path)
    if not prim.IsValid():
        raise RuntimeError(f"static collider prim not found: {path}")
    rng = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"],
                            useExtentsHint=True).ComputeWorldBound(prim).ComputeAlignedRange()
    lo, hi = rng.GetMin(), rng.GetMax()
    return ([float(lo[i] - root[i]) for i in range(3)], [float(hi[i] - root[i]) for i in range(3)])


def measure_static_scene_b(env, robot) -> dict:
    import omni.usd

    stage = omni.usd.get_context().get_stage()
    root = robot.data.root_pos_w[0, :3].cpu().numpy()
    tlo, thi = _bbox_b(stage, f"{_ENV}/Table", root)
    boxes = {rel: _bbox_b(stage, f"{_ENV}/{rel}", root) for rel in STATIC_BOXES}
    ground_z = float(-root[2])   # /World/ground plane at world z = 0
    ground = stage.GetPrimAtPath("/World/ground")
    if not ground.IsValid():
        raise RuntimeError("ground prim not found: /World/ground")
    return {"table": {"x": (tlo[0], thi[0]), "y": (tlo[1], thi[1]), "top_z": thi[2]},
            "boxes": boxes, "ground_z": ground_z}


def scene_guard(p_b: torch.Tensor, scene_b: dict, margin: float = TABLE_GUARD_MARGIN_M):
    """Return (guarded point, list of collider names that clamped it)."""
    q = p_b.clone()
    hits = []
    t = scene_b["table"]
    if t["x"][0] <= float(q[0]) <= t["x"][1] and t["y"][0] <= float(q[1]) <= t["y"][1] \
            and float(q[2]) < t["top_z"] + margin:
        q[2] = t["top_z"] + margin
        hits.append("table")
    for name, (lo, hi) in scene_b["boxes"].items():
        lo_m = [v - margin for v in lo]
        hi_m = [v + margin for v in hi]
        if all(lo_m[i] <= float(q[i]) <= hi_m[i] for i in range(3)):
            # nearest face of the inflated box
            moves = [(float(q[i]) - lo_m[i], i, lo_m[i]) for i in range(3)] + \
                    [(hi_m[i] - float(q[i]), i, hi_m[i]) for i in range(3)]
            _, ax, val = min(moves)
            q[ax] = val
            hits.append(name)
    if float(q[2]) < scene_b["ground_z"] + margin:
        q[2] = scene_b["ground_z"] + margin
        hits.append("ground")
    return q, hits
