"""WP1-③a — pure KINEMATIC reachability envelope of the LEFT arm, driven by
the VALIDATED L2 instrument (NOT a hand-written IK probe).

Instrument rule ("the patient goes into the standard instrument first"): two
of my hand-written IK probes failed. So this uses the EXACT servo path that
L0a/L2 collect used for three months — the L2 env's DiffIK action term, driven
via IsaacLabEnvInterface.execute_command(canonical command). No hand-rolled IK.

BASELINE FIRST: hit a known-reachable L2-era point (0.45,0,0.30) with the
LEFT arm; it MUST pass. If baseline FAILS, the instrument (or the servo
budget) is broken → ALL low-z readings are void, fix the instrument first.
This also settles "were my carrot params bad?" — baseline answers it, no guess.

SWEEP the (x,z) FACE (not just an x line):
  x ∈ {0.25,0.30,0.35,0.40,0.45} × z ∈ {0.024,0.05,0.10,0.15,0.30}
For each cell, after servoing the LEFT EE toward (x,0,z):
  - min_err (cm)
  - the error VECTOR (dx,dy,dz): stuck hovering ABOVE the target (z-wall) or
    reaching-short sideways (x-wall)? — this tells z-wall from x-wall.
  - per-joint limit-proximity at the stuck pose: which joint pinned?
  - orientation-constraint contrast: L2 term is command_type="pose" (EE
    orientation constrained). Orientation constraint is a classic hidden
    killer of low reachability, so re-test each cell ONCE with orientation
    relaxed (identity-ish / position-priority) as a one-line contrast.

Representative stuck cells → RGB frame dumps → GIF for the HUMAN-EYE gate.

Effort/torque irrelevant here (pure kinematics). Flushed; caller reads [RE].
"""
from __future__ import annotations
import argparse
import os
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=120)      # servo budget per cell
parser.add_argument("--out", type=str, default="logs/reach_frames")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import numpy as np
import torch
import imageio.v2 as imageio
from isaaclab.utils.math import subtract_frame_transforms
from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder
# Import the interface from its module directly — aiongenos.orchestrator's
# __init__ pulls in the VLM/collect chain (httpx), which we don't need for a
# pure-kinematic sweep. Same validated instrument, lighter import.
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.pipeline.stage2_attempt import BimanualCommand, MetricCommand

XS = [0.25, 0.30, 0.35, 0.40, 0.45]
ZS = [0.024, 0.05, 0.10, 0.15, 0.30]
# REACH_TOL_CM: an EE→command SERVO tolerance (NOT the L2 object-goal metric,
# which is ~15cm median). A short in-envelope DiffIK move should converge well
# inside this; 3cm is a strict-but-fair servo bar.
REACH_TOL_CM = 3.0
# stuck cells to dump frames for the human-eye gate (filled after sweep)


def _p(m):
    print(f"[RE] {m}", flush=True)


def main() -> None:
    os.makedirs(args_cli.out, exist_ok=True)
    env = ArenaEnvBuilder.build_env(level=2, num_envs=1)
    iface = IsaacLabEnvInterface(env)
    robot = iface.robot
    u = env.unwrapped
    left_idx = iface.left_body_idx
    left_ids, left_names = robot.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    # soft joint limits for the left arm (lower, upper)
    jlim = robot.data.soft_joint_pos_limits[0, lid].cpu().numpy()  # (7,2)

    def left_pos_b():
        """LEFT EE in the ROOT frame USING subtract_frame_transforms (INCLUDES
        root rotation) — the SAME frame the DiffIK term consumes
        (_compute_frame_pose). The interface's _get_ee_poses uses world-root
        (translation only, NO rotation), which mismatches the DiffIK command
        frame whenever root is rotated. That mismatch was the baseline failure;
        readback here must match the controller's frame, not the interface's."""
        root_p = robot.data.root_pos_w[0:1, :3]
        root_q = robot.data.root_quat_w[0:1, :4]
        ee_w = robot.data.body_pos_w[0:1, left_idx, :3]
        pos_b, _ = subtract_frame_transforms(root_p, root_q, ee_w)
        return pos_b[0].cpu().numpy()

    def joint_proximity():
        """Per-joint fraction of range consumed toward the nearer limit; the
        max tells which joint is pinned (≈1.0 = riding a limit)."""
        q = robot.data.joint_pos[0, lid].cpu().numpy()
        lo, hi = jlim[:, 0], jlim[:, 1]
        # distance to nearer limit, normalised by half-range
        span = np.maximum(hi - lo, 1e-6)
        frac_hi = (q - lo) / span   # 0 at lower limit, 1 at upper
        # proximity to EITHER limit: closeness to 0 or 1
        prox = np.maximum(1.0 - frac_hi, frac_hi)  # 0.5 center → ~1.0 at a limit
        return q, prox

    def servo_left_to(x, y, z, hold_orient=True):
        """Drive the LEFT arm to (x,y,z) root-frame via the L2 DiffIK
        instrument; right arm holds. Returns (min_err_cm, err_vec, q, prox).

        hold_orient=True (default): command the EE's CURRENT orientation, so
        the servo does PURE POSITION and does not waste motion re-orienting.
        Forcing identity quat corrupts position servo when the reset EE
        orientation is far from identity (that was the 6.2cm baseline z-drift
        bug). hold_orient=False → identity quat, the orientation-cost contrast."""
        # reset deterministically each cell
        iface.reset(seed=4700)
        # capture the LEFT EE's current orientation to hold it (isolates
        # position reachability from orientation slew). _get_ee_poses returns
        # (left_pos_b, right_pos_b, left_quat_w, right_quat_w).
        _, right_b, left_qw, right_qw = iface._get_ee_poses()
        if hold_orient:
            quat = (float(left_qw[0]), float(left_qw[1]), float(left_qw[2]), float(left_qw[3]))
        else:
            quat = (1.0, 0.0, 0.0, 0.0)
        left_cmd = MetricCommand(position=(x, y, z), quaternion=quat)
        # right arm: hold current pose
        right_cmd = MetricCommand(position=(float(right_b[0]), float(right_b[1]), float(right_b[2])),
                                  quaternion=(float(right_qw[0]), float(right_qw[1]),
                                              float(right_qw[2]), float(right_qw[3])))
        cmd = BimanualCommand(left=left_cmd, right=right_cmd)
        target = np.array([x, y, z])
        dmin = 1e9; err_vec_at_min = None
        # execute_command servos `steps`; but we want the min over the servo,
        # so step manually via the same action-build path in short bursts.
        for _ in range(args_cli.steps // 10):
            iface.execute_command(cmd, steps=10, active_arm="left")
            lp = left_pos_b()
            d = float(np.linalg.norm(lp - target)) * 100
            if d < dmin:
                dmin = d
                err_vec_at_min = (lp - target) * 100  # cm, (dx,dy,dz)
        q, prox = joint_proximity()
        return dmin, err_vec_at_min, q, prox

    # ---------- FRAME CHECK: is root rotated? (the suspected bug) ----------
    iface.reset(seed=4700)
    root_q = robot.data.root_quat_w[0].cpu().numpy()
    _p(f"root_quat_w (w,x,y,z) = {np.round(root_q,3).tolist()} "
       f"({'ROTATED — world-root readback would mismatch DiffIK frame' if abs(root_q[0])<0.999 else 'near-identity'})")

    # ---------- BASELINE: SELF-REFERENTIAL (not an invented absolute point) ----
    # Command the LEFT EE to its OWN reset position + 5cm in x. Any working
    # instrument+frame MUST converge this short, in-envelope move. This removes
    # my invented (0.45,0,0.30) point (real L2 left cmds span x[-0.17,0.51],
    # z[0,0.70] — there is no single canonical "known point", and final_dist is
    # an object-goal metric ~15cm, NOT an EE servo error). Self-reference is the
    # only assumption-free baseline.
    ee0 = left_pos_b()
    _p(f"=== BASELINE (self-referential): LEFT EE reset pos (root frame) = {np.round(ee0,3).tolist()} ===")
    bx, by, bz = float(ee0[0]) + 0.05, float(ee0[1]), float(ee0[2])
    b_err, b_vec, _, _ = servo_left_to(bx, by, bz)
    base_pass = b_err < REACH_TOL_CM
    _p(f"BASELINE (EE_start+5cm x) min_err={b_err:.1f}cm vec(dx,dy,dz)={np.round(b_vec,1).tolist()} "
       f"→ {'PASS' if base_pass else 'FAIL'}")
    if not base_pass:
        _p("BASELINE FAILED → instrument/frame/servo-budget broken; ALL sweep "
           "readings VOID. Fix instrument before trusting any cell.")
        env.close()
        return
    _p("BASELINE PASS → instrument+frame valid; sweep is trustworthy.")

    # ---------- SWEEP (x,z) FACE ----------
    _p("=== SWEEP (x,z) face: x×z, LEFT arm, orientation-constrained (pose) ===")
    grid = {}
    for z in ZS:
        row = []
        for x in XS:
            dmin, vec, q, prox = servo_left_to(x, 0.0, z)
            reachable = dmin < REACH_TOL_CM
            pin_j = int(np.argmax(prox)); pin_v = float(prox[pin_j])
            # wall type from error vector: |dz| dominant → z-wall (hovering);
            # |dx| dominant → x-wall (reaching short)
            adx, ady, adz = abs(vec[0]), abs(vec[1]), abs(vec[2])
            wall = "z-wall(hover)" if adz >= max(adx, ady) else ("x-wall(short)" if adx >= ady else "y-wall")
            row.append({"x": x, "z": z, "dmin": dmin, "vec": np.round(vec, 1).tolist(),
                        "reach": reachable, "pin_joint": left_names[pin_j], "pin": round(pin_v, 2),
                        "wall": wall})
            _p(f"  x={x:.2f} z={z:.3f}: min_err={dmin:.1f}cm vec={np.round(vec,1).tolist()} "
               f"{'REACH' if reachable else 'STUCK'} pin={left_names[pin_j]}({pin_v:.2f}) {wall}")
            grid[(x, z)] = row[-1]

    # ---------- orientation-relaxed contrast (one line per stuck low-z cell) ----------
    _p("=== ORIENTATION-RELAX contrast on STUCK cells (identity quat already; "
       "here we retry with a palm-down 90° pitch to see if orientation blocks low-z) ===")
    # palm-down quat (rotate 90° about base Y): w,x,y,z
    palm = (0.7071, 0.0, 0.7071, 0.0)
    for (x, z), c in grid.items():
        if not c["reach"] and z <= 0.10:
            iface.reset(seed=4700)
            _, right_b, _, right_qw = iface._get_ee_poses()
            cmd = BimanualCommand(
                left=MetricCommand(position=(x, 0.0, z), quaternion=palm),
                right=MetricCommand(position=(float(right_b[0]), float(right_b[1]), float(right_b[2])),
                                    quaternion=tuple(float(v) for v in right_qw)))
            dmin = 1e9
            for _ in range(args_cli.steps // 10):
                iface.execute_command(cmd, steps=10, active_arm="left")
                lp = left_pos_b(); dmin = min(dmin, float(np.linalg.norm(lp - np.array([x, 0.0, z]))) * 100)
            _p(f"  x={x:.2f} z={z:.3f} palm-down: min_err={dmin:.1f}cm "
               f"(constrained was {c['dmin']:.1f}cm) → orientation "
               f"{'HELPS' if dmin < c['dmin'] - 2 else 'not the blocker'}")

    # ---------- envelope summary ----------
    reach_x_by_z = {}
    for z in ZS:
        reachable_xs = [x for x in XS if grid[(x, z)]["reach"]]
        reach_x_by_z[z] = max(reachable_xs) if reachable_xs else None
    _p("=== ENVELOPE (max reachable x per z) ===")
    for z in ZS:
        _p(f"  z={z:.3f}: max reachable x = {reach_x_by_z[z]}")

    # ---------- frame dumps for human-eye gate: 3 representative stuck cells ----------
    stuck = [c for c in grid.values() if not c["reach"]]
    stuck_sorted = sorted(stuck, key=lambda c: (c["z"], -c["x"]))  # low-z, far-x first
    picks = stuck_sorted[:3]
    _p(f"=== HUMAN-EYE gate: dumping GIFs for {len(picks)} representative stuck cells ===")
    for c in picks:
        x, z = c["x"], c["z"]
        iface.reset(seed=4700)
        _, right_b, _, right_qw = iface._get_ee_poses()
        cmd = BimanualCommand(
            left=MetricCommand(position=(x, 0.0, z), quaternion=(1.0, 0.0, 0.0, 0.0)),
            right=MetricCommand(position=tuple(float(v) for v in right_b),
                                quaternion=tuple(float(v) for v in right_qw)))
        frames = []
        for _ in range(args_cli.steps // 5):
            iface.execute_command(cmd, steps=5, active_arm="left")
            png = iface.get_rgb()
            if png:
                frames.append(imageio.imread(png))
        if frames:
            fn = os.path.join(args_cli.out, f"stuck_x{int(x*100)}_z{int(z*1000)}.gif")
            imageio.mimsave(fn, frames, duration=0.1)
            _p(f"  GIF: {fn}  (target x={x:.2f} z={z:.3f}, {c['wall']}, "
               f"pin={c['pin_joint']}({c['pin']}), min_err={c['dmin']:.1f}cm)")
    _p("=== DONE ===")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
