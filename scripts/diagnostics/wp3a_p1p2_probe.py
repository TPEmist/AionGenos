"""WP1-③a Stage-1 extension P1+P2 in one run (per PI spec 2026-08-17).

P1 (body-index): print each OSC term's resolved EE body name+index; at the
    servo plateau, compute distance from EVERY link to the target — if some
    OTHER body sits on the target, the culprit is body resolution.
P2 (init near-singular): left-arm Jacobian condition number / min singular
    value at the init (hanging) pose vs a BI-LEGAL raised pose (limits read
    from the asset, not guessed). init σ_min→0 while raised is fine ⇒
    culprit 1 (init singular).

Runs on BiLeftOnly (BI robot, one left OSC term). Flushed; caller reads [P].
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


def _p(m):
    print(f"[P] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-OSC-BiLeftOnly-v0"
    env = gym.make(gym_id, cfg=parse_env_cfg(gym_id, num_envs=1), render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    act_dim = env.action_space.shape[-1]
    env.reset(seed=4700)

    # ---- P1: OSC term body resolution ----
    am = u.action_manager
    for name, term in am._terms.items():
        bidx = getattr(term, "_ee_body_idx", getattr(term, "_body_idx", "?"))
        jbidx = getattr(term, "_jacobi_ee_body_idx", getattr(term, "_jacobi_body_idx", "?"))
        _p(f"P1 term '{name}': body_idx={bidx} jacobi_body_idx={jbidx}")

    left_ids, _ = robot.find_joints("openarm_left_joint.*")
    lim = robot.data.joint_pos_limits[0]  # (nDoF,2)
    _p(f"P1 left joint limits: " + ", ".join(
        f"j{j}[{float(lim[j,0]):.2f},{float(lim[j,1]):.2f}]" for j in left_ids))

    # drive left EE to a reachable target, find the servo plateau, then
    # measure EVERY body's distance to the target.
    tgt_w = torch.tensor([0.45, 0.10, 0.30], device=u.device)
    tgt_b = base_frame_target_from_world(u, tgt_w)
    action = torch.zeros((u.num_envs, act_dim), device=u.device)
    action[:, 0:3] = tgt_b
    action[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0], device=u.device)
    if act_dim >= 13:
        action[:, 7:13] = 300.0
    for _ in range(120):
        env.step(action)
    body_pos = robot.data.body_pos_w[0]  # (nBodies,3)
    dists = torch.norm(body_pos - tgt_w, dim=-1) * 100.0
    order = torch.argsort(dists)
    _p("P1 nearest bodies to target at plateau (name: cm):")
    for k in order[:4].tolist():
        _p(f"P1   {robot.body_names[k]}: {float(dists[k]):.1f}cm")
    ee_name = "openarm_left_hand"
    ee_k = robot.body_names.index(ee_name)
    nearest = robot.body_names[int(order[0])]
    _p(f"P1 VERDICT: nearest body = '{nearest}'; tracked EE '{ee_name}' at {float(dists[ee_k]):.1f}cm "
       f"→ {'BODY-RESOLUTION BUG (wrong body on target)' if nearest != ee_name and float(dists[int(order[0])]) < 5 else 'EE is the tracked body (not a body-resolution bug)'}")

    # ---- P2: Jacobian conditioning at init (hanging) vs a legal raised pose ----
    def jac_cond(qpos_dict):
        # set joints, step once to refresh, read left-arm jacobian
        env.reset(seed=4700)
        # apply qpos via write_joint_state
        jids = torch.tensor(left_ids, device=u.device)
        q = robot.data.joint_pos.clone()
        for j, val in qpos_dict.items():
            q[0, j] = val
        robot.write_joint_state_to_sim(q, torch.zeros_like(q))
        for _ in range(3):
            u.sim.step(render=False); robot.update(u.sim.get_physics_dt())
        # left-arm jacobian — MATCH the OSC term's indexing exactly:
        # fixed-base → jacobi_body_idx = body_idx - 1, jacobi_joint_ids =
        # joint_ids (task_space_actions.py:77-79). Using the raw body index
        # (my first bug) reads the wrong row → σ=0.
        ee_k = robot.body_names.index("openarm_left_hand")
        jbody = ee_k - 1 if robot.is_fixed_base else ee_k
        jac_full = robot.root_physx_view.get_jacobians()[0]  # (nBody-?, 6, nDoF or +6)
        J = jac_full[jbody][:, left_ids]  # 6 x 7
        sv = torch.linalg.svdvals(J)
        return float(sv.min()), float(sv.max()), float(sv.max() / (sv.min() + 1e-12))

    # legal raised pose: each left joint at 60% toward its upper limit from 0
    raised = {}
    for j in left_ids:
        lo, hi = float(lim[j, 0]), float(lim[j, 1])
        raised[j] = max(lo, min(hi, 0.4 * hi + 0.1 * lo))  # in-limits, non-zero
    smin_i, smax_i, cond_i = jac_cond({j: 0.0 for j in left_ids})
    smin_r, smax_r, cond_r = jac_cond(raised)
    _p(f"P2 init(hanging, q=0): σ_min={smin_i:.4f} σ_max={smax_i:.3f} cond={cond_i:.1f}")
    _p(f"P2 raised(in-limits):  σ_min={smin_r:.4f} σ_max={smax_r:.3f} cond={cond_r:.1f}")
    _p(f"P2 VERDICT: {'INIT NEAR-SINGULAR (σ_min≈0 at init, fine when raised) → culprit=init pose' if smin_i < 0.02 and smin_r > 2*smin_i else 'init not markedly singular vs raised → culprit NOT init pose'}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
