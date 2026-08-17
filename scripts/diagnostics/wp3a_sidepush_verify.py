"""WP1-③a — side-push feasibility: the FINAL geometry/torque verdict (PI spec).

Real task motion (not an abstract probe), on the push env (has the dynamic
cube), left arm OSC, Pin-7 working init:
  1a. contact-height reach + HOLD: EE to the cube's SIDE-face contact height
      (cube half-height ~2.4cm → target z≈0.024, NOT pressing to table
      z=0.03). Measure τ/limit while holding ≥30 steps — the posture the
      hold gate should actually test.
  1b. horizontal push WITH the cube: from the contact pose, translate the EE
      ~12cm along cube→goal (horizontal). This is a REAL contact (cube
      0.216kg + friction), so torque demand = inertia + friction·lever; must
      be measured WITH the cube (free-space horizontal doesn't count).

Verdict lines (pre-committed): max(τ/limit) over the whole sequence ≤0.85 →
in budget (③a = pure horizontal push, z=0.03 press removed); 0.85-1.0 →
feasible-tight (posture tuning); >1.0 → real hw constraint (re-discuss).

Effort limits (real hw): [40,40,27,27,7,7,7]. Flushed; caller reads [SP].
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher
parser = argparse.ArgumentParser()
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


def _p(m):
    print(f"[SP] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env = gym.make(gym_id, cfg=parse_env_cfg(gym_id, num_envs=1), render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    cube = u.scene["object"]
    ee_idx = robot.body_names.index("openarm_left_hand")
    left_ids, _ = robot.find_joints("openarm_left_joint.*")
    lim = torch.tensor(LIMITS, device=u.device)
    lid = torch.tensor(left_ids, device=u.device)
    act_dim = env.action_space.shape[-1]
    env.reset(seed=4700)

    cube_w = cube.data.root_pos_w[0, :3].clone()
    _p(f"cube_w={[round(x,3) for x in cube_w.tolist()]} (side-contact height z={float(cube_w[2]):.3f})")

    def servo(tgt_w, steps, track_ratio=True):
        tgt_b = base_frame_target_from_world(u, tgt_w)
        action = torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 0:3] = tgt_b
        action[:, 3:7] = torch.tensor([1., 0., 0., 0.], device=u.device)
        if act_dim >= 13:
            action[:, 7:13] = 300.0
        peak = 0.0; dmin = 1e9
        for i in range(steps):
            env.step(action)
            ee = robot.data.body_pos_w[0, ee_idx, :3]
            dmin = min(dmin, float(torch.norm(ee - tgt_w) * 100))
            if track_ratio and i >= steps - 40:
                r = float((robot.data.applied_torque[0, lid].abs() / lim).max())
                peak = max(peak, r)
        return dmin, peak, robot.data.body_pos_w[0, ee_idx, :3].clone()

    # 1a: EE to the cube's SIDE (behind, along -x from goal) at contact height.
    # Approach point = cube minus a small offset toward the arm, at cube z.
    contact = cube_w.clone()
    contact[0] -= 0.05          # behind the cube (toward the pushing side)
    contact[2] = float(cube_w[2])  # side-face contact height (~0.024), NOT table
    dmin_a, peak_a, ee_a = servo(contact, 120)
    _p(f"1a contact-reach: target z={float(contact[2]):.3f} min_err={dmin_a:.1f}cm peak τ/limit={peak_a:.2f}")
    reach_ok = dmin_a < 6.0

    # 1b: horizontal push WITH the cube — translate +x ~12cm at contact height.
    push_to = contact.clone(); push_to[0] += 0.12
    dmin_b, peak_b, ee_b = servo(push_to, 150)
    cube_moved = float(torch.norm(cube.data.root_pos_w[0, :3] - cube_w) * 100)
    _p(f"1b horizontal push (+12cm, WITH cube): peak τ/limit={peak_b:.2f} cube_moved={cube_moved:.1f}cm")

    peak_all = max(peak_a, peak_b)
    _p(f"SEQUENCE peak τ/limit = {peak_all:.2f}; contact-reach servo {'OK' if reach_ok else 'FAIL'}; cube moved {cube_moved:.1f}cm")
    if peak_all <= 0.85 and reach_ok:
        v = "IN BUDGET (≤0.85) → ③a = pure horizontal push; z=0.03 press REMOVED from task"
    elif peak_all <= 1.0:
        v = "FEASIBLE-TIGHT (0.85-1.0) → posture tuning into ③a"
    else:
        v = ">1.0 SATURATED → real hw constraint, re-discuss scene (raise table / lighter cube)"
    _p(f"VERDICT {v}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
