"""WP1-③a — P5 δ-clamp setpoint probe (PI spec, jumps the queue before any
domain-shrink).

HYPOTHESIS: the band sweep + side-push both commanded the ABSOLUTE far target
in ONE step (action[:,0:3] = far_target). OSC then sees an instantaneous
position error = the whole span (30-45cm); impedance force = K·(huge error)
→ torque saturates. That may be a SETPOINT-SPAN ARTIFACT, not the arm's real
torque envelope.

FIX (primitive-layer): clamp each commanded setpoint to ≤δ ahead of the
CURRENT EE (δ=3cm to start). A far target is walked in as a chain of small
δ-steps — the carrot. This is what push_toward / the L0a IK servo should do
anyway. OSC's position error stays bounded by δ → impedance force bounded.

Re-tests the two representative "saturated" points from the band sweep:
  a. far-horizontal (0.50, 0, 0.30) — the band sweep's dead point
  b. far+low       (0.45, 0, 0.024) — cube position, 1a's dead point
then HOLD ≥30 steps at each; records PER-STEP max(τ/limit) throughout.

Pre-committed 3-branch verdict (mechanical):
  - a AND b both ≤0.85 → "small comfort zone" VOID; it was a setpoint-span
    artifact. Pin-4 geometry kept; only open item = contact-force budget WHEN
    pushing WITH the cube (7N·m's real job) → re-run 1b with cube.
  - a ≤0.85 but b >0.85 → height constraint is REAL, horizontal was artifact
    → re-sweep the contact-height band in clamp mode.
  - neither ≤0.85 → "comfort zone x~0.2" confirmed by elimination → domain
    shrink (with its P2 scientific cost on the table).

Effort limits (verified real hw): [40,40,27,27,7,7,7]. Flushed; reads [P5].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--delta", type=float, default=0.03)  # setpoint clamp (m)
parser.add_argument("--hold-steps", type=int, default=30)
parser.add_argument("--max-steps", type=int, default=400)  # walk-in budget
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import base_frame_target_from_world

LIMITS = [40., 40., 27., 27., 7., 7., 7.]


def _classify(r):
    return "FEASIBLE" if r < 0.85 else ("TIGHT" if r < 1.0 else "SATURATED")


def _p(m):
    print(f"[P5] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env = gym.make(gym_id, cfg=parse_env_cfg(gym_id, num_envs=1), render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    left_ids, _ = robot.find_joints("openarm_left_joint.*")
    lid = torch.tensor(left_ids, device=u.device)
    lim = torch.tensor(LIMITS, device=u.device)
    act_dim = env.action_space.shape[-1]
    delta = args_cli.delta

    def clamped_servo(final_w):
        """Walk the setpoint in as ≤delta-ahead waypoints; hold at target.
        Returns (reached, min_err_cm, walk_peak, hold_peak, n_walk_steps)."""
        env.reset(seed=4700)
        final = torch.tensor(final_w, device=u.device)
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            action[:, 7:13] = 300.0
        walk_peak = 0.0; dmin = 1e9; reached = False; nwalk = 0
        for i in range(args_cli.max_steps):
            ee = robot.data.body_pos_w[0, ee_idx, :3]
            d = final - ee
            dist = float(torch.norm(d))
            # carrot: setpoint = current EE + min(delta, dist) toward final
            step_vec = d if dist <= delta else d / dist * delta
            waypoint_w = ee + step_vec
            action[:, 0:3] = base_frame_target_from_world(u, waypoint_w)
            env.step(action)
            r = float((robot.data.applied_torque[0, lid].abs() / lim).max())
            walk_peak = max(walk_peak, r)
            ee2 = robot.data.body_pos_w[0, ee_idx, :3]
            dmin = min(dmin, float(torch.norm(ee2 - final) * 100))
            nwalk = i + 1
            if float(torch.norm(ee2 - final)) < 0.02:  # within 2cm → arrived
                reached = True
                break
        # HOLD at the final target (setpoint = final, error already ≤2cm)
        action[:, 0:3] = base_frame_target_from_world(u, final)
        hold_peak = 0.0
        for i in range(args_cli.hold_steps):
            env.step(action)
            r = float((robot.data.applied_torque[0, lid].abs() / lim).max())
            hold_peak = max(hold_peak, r)
        return reached, dmin, walk_peak, hold_peak, nwalk

    _p(f"delta(setpoint clamp) = {delta*100:.1f}cm; hold={args_cli.hold_steps} steps")
    pts = [("a far-horizontal", [0.50, 0.0, 0.30]),
           ("b far+low(cube)", [0.45, 0.0, 0.024])]
    res = {}
    for label, fw in pts:
        reached, dmin, wp, hp, nw = clamped_servo(fw)
        peak = max(wp, hp)
        _p(f"{label} {fw}: reached={reached} min_err={dmin:.1f}cm "
           f"walk_peak={wp:.2f} hold_peak={hp:.2f} (walk {nw} steps) "
           f"→ walk[{_classify(wp)}] hold[{_classify(hp)}]")
        res[label[0]] = {"reached": reached, "dmin": dmin, "peak": peak,
                         "walk": wp, "hold": hp}

    a_ok = res["a"]["reached"] and res["a"]["peak"] <= 0.85 and res["a"]["dmin"] < 6.0
    b_ok = res["b"]["reached"] and res["b"]["peak"] <= 0.85 and res["b"]["dmin"] < 6.0
    _p(f"a_ok(clamp)={a_ok}  b_ok(clamp)={b_ok}")
    if a_ok and b_ok:
        v = ("BRANCH-1: both ≤0.85 under clamp → 'small comfort zone' was a "
             "SETPOINT-SPAN ARTIFACT. Pin-4 geometry KEPT. Next: measure "
             "contact-force budget pushing WITH the cube (1b clamp-mode).")
    elif a_ok and not b_ok:
        v = ("BRANCH-2: far-horizontal OK but far+low SATURATES under clamp → "
             "HEIGHT constraint is REAL, horizontal was artifact → re-sweep "
             "contact-height band in clamp mode.")
    else:
        v = ("BRANCH-3: clamp does NOT save it → 'comfort zone x~0.2' confirmed "
             "by elimination → domain shrink (P2 context-space cost on the table).")
    _p(f"VERDICT {v}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
