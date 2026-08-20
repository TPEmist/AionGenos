"""WP1-③a — P6: pre-clip commanded torque + controller-variant ablation.

BRANCH-3 ("12cm comfort zone → shrink domain") was REJECTED: it contradicts
DiffIK's 3-month full-table record on the SAME arm/table. Same hardware
reaching x=0.6 under DiffIK but saturating under OSC ⇒ the ceiling is almost
certainly the CONTROLLER, not the arm. Nine rounds never read the deciding
number: the torque OSC COMMANDS *before* the actuator clips it to the effort
limit.

Path (verified in task_space_actions.py):
  _osc.compute(...) → term._joint_efforts (PRE-CLIP commanded torque)
  → set_joint_effort_target(...) → actuator clips → robot.data.applied_torque
So term._joint_efforts / limit = the pre-clip ratio (what we never read);
robot.data.applied_torque / limit = the post-clip ratio (=1.0 when saturated,
what all nine rounds read).

(a) PRE-CLIP READ: servo the two P5 dead points (far-horizontal 0.50/0/0.30,
    far+low/cube 0.45/0/0.024); log peak |τ_cmd|/limit (pre-clip) AND
    post-clip, both arms' left term.
    Predict: |τ_cmd| >> limit (orders of magnitude) → NUMERICAL BLOW-UP
    convicts the controller, "small workspace" VOID. If τ_cmd ≈ limit×1.1 →
    genuinely just short, workspace story survives.

(b) ABLATION: same two points, turn OFF inertial_dynamics_decoupling
    (+ nullspace_control="none" as the paired control). The decoupling term
    is M_task = inv(J M^-1 J^T) — the Λ-inverse that blows up near the reach
    boundary. Predict: with it OFF, the far targets become reachable with
    HEALTHY τ.

Both run on the push env (Pin-7 init). Effort limits real hw
[40,40,27,27,7,7,7]. Flushed; caller reads [P6].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=150)
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
POINTS = [("a far-horizontal", [0.50, 0.0, 0.30]),
          ("b far+low(cube)", [0.45, 0.0, 0.024])]


def _p(m):
    print(f"[P6] {m}", flush=True)


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
    term = u.action_manager._terms["left_arm_action"]  # OSC action term (left)

    def servo(final_w, steps):
        """Direct servo to the world target; record peak pre-clip and
        post-clip |τ|/limit for the LEFT arm, plus min EE error."""
        env.reset(seed=4700)
        tb = base_frame_target_from_world(u, torch.tensor(final_w, device=u.device))
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 0:3] = tb
        action[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            action[:, 7:13] = 300.0
        pre_peak = 0.0; post_peak = 0.0; dmin = 1e9; pre_at_min = None
        final = torch.tensor(final_w, device=u.device)
        for i in range(steps):
            env.step(action)
            # PRE-CLIP: what OSC commanded this step (term._joint_efforts)
            pre = (term._joint_efforts[0].abs() / lim).max()
            pre_peak = max(pre_peak, float(pre))
            # POST-CLIP: what the actuator actually applied
            post = (robot.data.applied_torque[0, lid].abs() / lim).max()
            post_peak = max(post_peak, float(post))
            ee = robot.data.body_pos_w[0, ee_idx, :3]
            d = float(torch.norm(ee - final) * 100)
            if d < dmin:
                dmin = d
                pre_at_min = float(pre)
        return dmin, pre_peak, post_peak, pre_at_min

    # ---------- (a) PRE-CLIP READ, baseline controller (P5 config) ----------
    _p("=== (a) PRE-CLIP read — baseline OSC (decoupling=True, nullspace=center) ===")
    dec0 = term._osc.cfg.inertial_dynamics_decoupling
    ns0 = term._osc.cfg.nullspace_control
    _p(f"baseline cfg: inertial_dynamics_decoupling={dec0} nullspace_control={ns0}")
    base_res = {}
    for label, fw in POINTS:
        dmin, pre, post, pre_min = servo(fw, args_cli.steps)
        base_res[label[0]] = (dmin, pre, post)
        verdict = ("BLOW-UP (pre>>limit)" if pre > 3.0 else
                   ("just-short (pre~limit)" if pre <= 1.5 else "moderate-over"))
        _p(f"{label} {fw}: min_err={dmin:.1f}cm  PRE-clip peak |τ_cmd|/limit={pre:.2f}"
           f"  POST-clip peak={post:.2f}  → {verdict}")

    # ---------- (b) ABLATION: decoupling OFF + nullspace none ----------
    _p("=== (b) ABLATION — inertial_dynamics_decoupling=False, nullspace_control='none' ===")
    term._osc.cfg.inertial_dynamics_decoupling = False
    term._osc.cfg.nullspace_control = "none"
    abl_res = {}
    for label, fw in POINTS:
        dmin, pre, post, pre_min = servo(fw, args_cli.steps)
        abl_res[label[0]] = (dmin, pre, post)
        reach = dmin < 6.0
        healthy = post < 0.85
        _p(f"{label} {fw}: min_err={dmin:.1f}cm  PRE-clip peak={pre:.2f}"
           f"  POST-clip peak={post:.2f}  → reach={'OK' if reach else 'FAIL'}"
           f" τ={'HEALTHY' if healthy else ('TIGHT' if post<1.0 else 'SATURATED')}")
    # restore
    term._osc.cfg.inertial_dynamics_decoupling = dec0
    term._osc.cfg.nullspace_control = ns0

    # ---------- joint verdict ----------
    _p("=== VERDICT ===")
    blowup = any(base_res[k][1] > 3.0 for k in base_res)
    ablation_helps = all(abl_res[k][0] < 6.0 and abl_res[k][2] < 0.85 for k in abl_res)
    _p(f"pre-clip blow-up (baseline any pre>3×limit): {blowup}")
    _p(f"ablation reaches+healthy (both points): {ablation_helps}")
    if blowup or ablation_helps:
        _p("VERDICT: CONTROLLER-numerical (OSC Λ-inverse singular blow-up near "
           "reach boundary) — NOT a hardware/workspace limit. 'Small comfort "
           "zone' VOID; Pin-4 geometry vindicated (matches DiffIK's full-table "
           "reach). → hybrid control (DiffIK transport + OSC contact) is the "
           "design answer, Pin-9.")
    else:
        _p("VERDICT: ablation did NOT rescue AND no pre-clip blow-up → the "
           "workspace story is not yet refuted by P6; escalate (re-examine "
           "jacobian/mass-matrix conditioning directly).")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
