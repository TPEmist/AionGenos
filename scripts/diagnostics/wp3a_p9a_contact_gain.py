"""WP1-③a — Pin-9a: contact-phase gain calibration (BEFORE building the
hybrid primitive).

P6 proved the k=300 large-span setpoint OVER-COMMANDS (pre-clip 5-6× limit),
convicting the controller, not the arm. But P6 did NOT yet show that the
CONTACT phase's real regime — pre-contact posture, LOW k, SMALL lead —
lands within the torque budget. That is what the primitive will actually run,
so we must measure the feasible-k band BEFORE building it.

Two stages, one env (push env, Pin-7 init):

  STAGE A — KINEMATIC PLACEMENT (previews the Pin-9 TRANSPORT phase): use the
  EXISTING validated DiffIK math (L2 path) to converge the LEFT EE to the
  pre-contact posture (x≈0.45, z≈0.024) by iterating compute() +
  write_joint_position_to_sim (gravity OFF + arm actuators zeroed → the arm
  stays where placed; no OSC effort involved). This is a legit stand-in for
  the DiffIK transport that Pin-9 will use, and the only way to seat the EE
  at the contact posture on an effort-controlled arm.

  STAGE B — CONTACT-GAIN SWEEP: from the seated posture, set OSC
  motion_stiffness_task = k ∈ {50,100,150,300}. For each k: servo with a
  SMALL 2-3cm setpoint lead along the push direction + hold; record PEAK
  PRE-CLIP |τ_cmd|/limit (Rule 9: this monitor is now PERMANENT — logged every
  step, warn >0.85, flag ≥1.0, so we never need another P6-round to discover
  over-command).

Criterion: find the k band where PRE-CLIP τ_cmd/limit ≤0.85 AND k×lead ≥ ~2N
(a friction budget that can actually move the 0.216 kg cube). k×lead is the
task-space restoring force the impedance produces at the lead distance.
  - band exists → pin k into Pin-9a, build the primitive.
  - all k saturate → the contact posture genuinely exits the envelope; task
    geometry must move IN — but that would be a CORRECTLY-attributed move
    (contact-phase torque), NOT the BRANCH-3 mis-diagnosis (which wrongly
    blamed a full-table single-step OSC servo).

Effort limits real hw [40,40,27,27,7,7,7]. Flushed; caller reads [P9A].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
parser.add_argument("--lead", type=float, default=0.03)      # setpoint lead (m)
parser.add_argument("--servo-steps", type=int, default=90)
parser.add_argument("--hold-steps", type=int, default=30)
parser.add_argument("--place-steps", type=int, default=200)  # DiffIK converge budget
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import torch
import gymnasium as gym
import aiongenos.tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.controllers.differential_ik import DifferentialIKController
from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
from isaaclab.utils.math import subtract_frame_transforms
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import base_frame_target_from_world

LIMITS = [40., 40., 27., 27., 7., 7., 7.]
PRE_CONTACT_W = [0.45, 0.0, 0.024]   # cube side-contact posture (Pin-4 x kept)
PUSH_DIR = [1.0, 0.0, 0.0]           # push +x (toward goal side)
K_SWEEP = [50.0, 100.0, 150.0, 300.0]


def _p(m):
    print(f"[P9A] {m}", flush=True)


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
    term = u.action_manager._terms["left_arm_action"]

    # fixed-base jacobian idx (the verified -1 offset)
    ee_body_idx = ee_idx
    jacobi_ee_idx = ee_body_idx - 1 if robot.is_fixed_base else ee_body_idx

    def ee_pose_w():
        return (robot.data.body_pos_w[0, ee_idx, :3].clone(),
                robot.data.body_quat_w[0, ee_idx, :4].clone())

    def jacobian_left_b():
        # world jacobian for the EE body, left-arm joint columns, base-rotated
        jac_w = robot.root_physx_view.get_jacobians()[:, jacobi_ee_idx, :, :][:, :, left_ids]
        from isaaclab.utils.math import matrix_from_quat, quat_inv
        base_rot = robot.data.root_quat_w
        R = matrix_from_quat(quat_inv(base_rot))
        jac_b = jac_w.clone()
        jac_b[:, :3, :] = torch.bmm(R, jac_w[:, :3, :])
        jac_b[:, 3:, :] = torch.bmm(R, jac_w[:, 3:, :])
        return jac_b

    # ---------- STAGE A: DiffIK kinematic placement (transport preview) ----------
    # CARROT the DiffIK target: EE goal advances <=2cm/step toward pre-contact.
    # A one-shot 52cm target stalls DiffIK (delta valid only locally, then
    # clamped at joint limits). Carroting also faithfully previews the Pin-9
    # TRANSPORT phase (DiffIK servos step-by-step, it does not teleport).
    _p("=== STAGE A: DiffIK kinematic placement to pre-contact (carrot, transport preview) ===")
    env.reset(seed=4700)
    ik = DifferentialIKController(
        DifferentialIKControllerCfg(command_type="position", use_relative_mode=False,
                                    ik_method="dls", ik_params={"lambda_val": 0.05}),
        num_envs=1, device=u.device)
    final_w = torch.tensor(PRE_CONTACT_W, device=u.device)
    STEP_LEAD = 0.02  # DiffIK waypoint advances <=2cm/iter
    place_err = 1e9
    for i in range(args_cli.place_steps):
        ee_p, ee_q = ee_pose_w()
        d = final_w - ee_p
        dist = float(torch.norm(d))
        waypoint_w = (ee_p + d if dist <= STEP_LEAD else ee_p + d / dist * STEP_LEAD).unsqueeze(0)
        root_p = robot.data.root_pos_w[0:1, :3]
        root_q = robot.data.root_quat_w[0:1, :4]
        ee_p_b, _ = subtract_frame_transforms(root_p, root_q, ee_p.unsqueeze(0))
        wp_b, _ = subtract_frame_transforms(root_p, root_q, waypoint_w)
        ik.set_command(wp_b, ee_pos=ee_p_b, ee_quat=ee_q.unsqueeze(0))
        jpos = robot.data.joint_pos[0:1, left_ids]
        jgoal = ik.compute(ee_p_b, ee_q.unsqueeze(0), jacobian_left_b(), jpos)
        # kinematically set the left-arm joints (gravity off → arm holds)
        robot.write_joint_position_to_sim(jgoal, joint_ids=left_ids)
        robot.write_data_to_sim()
        u.sim.step(render=False)
        robot.update(u.sim.get_physics_dt())
        ee_p2, _ = ee_pose_w()
        place_err = float(torch.norm(ee_p2 - final_w) * 100)
        if place_err < 2.0:
            _p(f"  placed in {i+1} DiffIK carrot-iters, EE err={place_err:.2f}cm")
            break
    seated_ok = place_err < 2.0
    _p(f"STAGE A: seated={'OK' if seated_ok else 'FAIL'} final_err={place_err:.2f}cm "
       f"(if FAIL, transport itself needs work before contact-gain is meaningful)")
    seated_jpos = robot.data.joint_pos[0:1, left_ids].clone()

    # ---------- STAGE B: contact-gain sweep ----------
    _p("=== STAGE B: contact-gain sweep (small lead, PRE-CLIP monitor permanent) ===")
    push_dir = torch.tensor(PUSH_DIR, device=u.device)
    push_dir = push_dir / torch.norm(push_dir)
    lead = args_cli.lead
    dec0 = term._osc.cfg.inertial_dynamics_decoupling  # keep True (P6: stabilising)
    band = {}
    for k in K_SWEEP:
        # re-seat to the placed posture each k (fresh, same start)
        robot.write_joint_position_to_sim(seated_jpos, joint_ids=left_ids)
        robot.write_joint_velocity_to_sim(torch.zeros_like(seated_jpos), joint_ids=left_ids)
        robot.write_data_to_sim(); u.sim.step(render=False); robot.update(u.sim.get_physics_dt())
        # set contact stiffness for this sweep point
        term._osc.cfg.motion_stiffness_task = k
        ee_p, _ = ee_pose_w()
        lead_target_w = ee_p + push_dir * lead   # small lead along push dir
        tb = base_frame_target_from_world(u, lead_target_w)
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 0:3] = tb
        action[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            action[:, 7:13] = k    # variable_kp channel tracks k too
        pre_peak = 0.0; post_peak = 0.0; warns = 0; flags = 0
        for i in range(args_cli.servo_steps + args_cli.hold_steps):
            env.step(action)
            pre = float((term._joint_efforts[0].abs() / lim).max())
            post = float((robot.data.applied_torque[0, lid].abs() / lim).max())
            pre_peak = max(pre_peak, pre); post_peak = max(post_peak, post)
            if pre > 0.85:
                warns += 1
            if pre >= 1.0:
                flags += 1
        # task-space restoring force at the lead distance ≈ k * lead (N)
        force_N = k * lead
        ok = pre_peak <= 0.85 and force_N >= 2.0
        _p(f"  k={k:>5.0f}: PRE-clip peak τ_cmd/limit={pre_peak:.2f} POST={post_peak:.2f} "
           f"| k×lead={force_N:.1f}N | warn_steps={warns} flag_steps={flags} "
           f"→ {'FEASIBLE' if ok else ('over-command' if pre_peak>0.85 else 'too-weak(<2N)')}")
        band[k] = {"pre": pre_peak, "force": force_N, "ok": ok}
    term._osc.cfg.inertial_dynamics_decoupling = dec0

    # ---------- verdict ----------
    _p("=== VERDICT ===")
    feasible = [k for k, v in band.items() if v["ok"]]
    if feasible:
        _p(f"CONTACT-GAIN BAND EXISTS: k ∈ {sorted(feasible)} give τ_cmd/limit ≤0.85 "
           f"AND ≥2N restoring force → pin the highest feasible k into Pin-9a, "
           f"build the hybrid primitive with this contact k + lead={lead*100:.0f}cm.")
    else:
        # distinguish the two failure modes for honest attribution
        all_over = all(v["pre"] > 0.85 for v in band.values())
        _p(f"NO feasible k. all_over_command={all_over}. If over-command even at "
           f"k=50 with a {lead*100:.0f}cm lead in the SEATED contact posture → the "
           f"contact posture itself exits the torque envelope → task geometry moves "
           f"IN, but CORRECTLY attributed to contact-phase torque (not BRANCH-3's "
           f"full-table single-step mis-diagnosis). Report to PI with this data.")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
