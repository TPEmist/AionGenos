"""WP1-③a inert-EE diagnosis — Steps 0/1/2 in one run (by discriminating power).

Step 0: applied_torque after a step (all-zero → upstream action/impedance;
        nonzero-but-inert → force cancelled/mis-scaled). + confirm
        disable_gravity (robot gravity is OFF, so no-drift is EXPECTED).
Step 1: each OSC term's resolved joint IDs (left/right disjoint + correct?).
Step 2: action-dim slice map — which indices feed which term; is the left
        term's IMPEDANCE slot actually non-zero in the smoke's action?

All flushed; caller reads [DIAG] lines.
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
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import (
    base_frame_target_from_world, push_toward_base,
)


def _p(m):
    print(f"[DIAG] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Push-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    _p(f"env made; robot dof={robot.num_joints}")

    # Step 0 premise: gravity state.
    dg = env_cfg.scene.robot.spawn.rigid_props.disable_gravity
    _p(f"STEP0 premise: robot disable_gravity={dg} → no-drift is {'EXPECTED' if dg else 'UNEXPECTED (something still holds PD)'}")

    # Step 1: each action term's resolved joint IDs.
    am = u.action_manager
    _p(f"STEP1 action terms: {list(am._terms.keys())}")
    for name, term in am._terms.items():
        jids = getattr(term, "_joint_ids", None)
        if jids is None:
            jids = getattr(term, "joint_ids", "?")
        try:
            jids_list = jids.tolist() if hasattr(jids, "tolist") else list(jids)
        except Exception:
            jids_list = str(jids)
        _p(f"STEP1   term '{name}': action_dim={term.action_dim} joint_ids={jids_list}")

    # Step 2: action-dim slice map.
    act_dim = env.action_space.shape[-1]
    _p(f"STEP2 total action_dim={act_dim}; per-term dims={[t.action_dim for t in am._terms.values()]}")

    env.reset(seed=4700)
    cube = u.scene["object"]
    cube_b = base_frame_target_from_world(u, cube.data.root_pos_w[0, :3])
    goal_b = u.command_manager.get_term("left_ee_pose").command[0, :3]
    tgt_b, _ = push_toward_base(cube_b, goal_b)

    # Build action the SAME way the smoke does, then inspect per-term slices.
    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    half = act_dim // 2
    action[:, 0:3] = tgt_b
    action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)
    if half > 7:
        action[:, 7:half] = 300.0
    # dump each term's slice of this action
    off = 0
    for name, term in am._terms.items():
        d = term.action_dim
        sl = action[0, off:off + d]
        _p(f"STEP2   term '{name}' gets action[{off}:{off+d}] = {[round(x,2) for x in sl.tolist()]}")
        off += d

    # Step 0: torque after a step.
    ee_idx = robot.body_names.index("openarm_left_hand")
    ee0 = robot.data.body_pos_w[0, ee_idx, :3].clone()
    for _ in range(20):
        env.step(action)
    tau = robot.data.applied_torque[0]
    ee1 = robot.data.body_pos_w[0, ee_idx, :3]
    moved_cm = float(torch.norm(ee1 - ee0).item()) * 100.0
    _p(f"STEP0 applied_torque: max|τ|={float(tau.abs().max()):.4f} sum|τ|={float(tau.abs().sum()):.4f}")
    _p(f"STEP0 per-joint |τ|: {[round(float(x),3) for x in tau.abs().tolist()]}")
    _p(f"STEP0 EE moved {moved_cm:.2f}cm over 20 steps")
    _p(f"VERDICT: torque {'ALL-ZERO → upstream (action/impedance)' if float(tau.abs().max()) < 1e-6 else 'NONZERO → force cancelled/mis-scaled'}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
