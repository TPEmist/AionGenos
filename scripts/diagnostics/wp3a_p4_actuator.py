"""WP1-③a Stage-1 P4 — actuator RUNTIME drive-state (physics balance argument).

At the plateau: τ constant nonzero + velocity ~0 + gravity off + no contact
⇒ a displacement-dependent reaction force ⇒ a spring ⇒ residual joint
stiffness (gains-zeroing silently ineffective on the BI asset). Five rounds
read kinematics/dynamics QUANTITIES; nobody read the actuator DRIVE STATE.

P4 reads RUNTIME values (Rule 8: config INTENT is not trusted, runtime STATE
counts):
  a. actual per-joint stiffness/damping (root_physx_view.get_dof_stiffnesses/
     dampings) — predict: BI arm joints have NONZERO stiffness → convict.
  b. each actuator group's actually-matched joint list — did the zeroing
     regex bite the BI joint names? (s1 panda_joint.* precedent.)
  c. effort limits — is max|τ|=40 exactly a clip value? (minor suspect.)

Runs on BiLeftOnly. Flushed; caller reads [P4].
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


def _p(m):
    print(f"[P4] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-OSC-BiLeftOnly-v0"
    env = gym.make(gym_id, cfg=parse_env_cfg(gym_id, num_envs=1), render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    env.reset(seed=4700)

    names = robot.joint_names
    left_ids, _ = robot.find_joints("openarm_left_joint.*")
    right_ids, _ = robot.find_joints("openarm_right_joint.*")

    # ---- P4a: RUNTIME stiffness/damping (physx view = ground truth) ----
    pv = robot.root_physx_view
    try:
        stiff = pv.get_dof_stiffnesses()[0]
        damp = pv.get_dof_dampings()[0]
        _p("P4a RUNTIME stiffness/damping (physx view):")
        for j in left_ids:
            _p(f"P4a   {names[j]}: stiff={float(stiff[j]):.1f} damp={float(damp[j]):.1f}")
        arm_stiff_max = max(float(stiff[j]) for j in left_ids)
        _p(f"P4a left-arm max stiffness = {arm_stiff_max:.1f} "
           f"→ {'RESIDUAL STIFFNESS PRESENT — CONVICT' if arm_stiff_max > 1e-3 else 'zero (spring absent)'}")
    except Exception as e:
        _p(f"P4a physx-view stiffness read failed ({e}); trying actuator objects")
        arm_stiff_max = None

    # also read via the actuator model objects (what the cfg produced)
    _p("P4a actuator-object view:")
    for gname, act in robot.actuators.items():
        st = act.stiffness
        dm = act.damping
        st_max = float(st.max()) if hasattr(st, "max") else float(st)
        dm_max = float(dm.max()) if hasattr(dm, "max") else float(dm)
        njoints = len(act.joint_indices) if hasattr(act, "joint_indices") else "?"
        _p(f"P4a   group '{gname}': stiff_max={st_max:.1f} damp_max={dm_max:.1f} njoints={njoints}")

    # ---- P4b: which joints each actuator group actually matched ----
    _p("P4b actuator group → matched joints:")
    for gname, act in robot.actuators.items():
        jids = act.joint_indices
        jl = jids.tolist() if hasattr(jids, "tolist") else list(jids)
        jnames = [names[i] for i in jl]
        _p(f"P4b   '{gname}': ids={jl}")
        _p(f"P4b       names={jnames}")

    # ---- P4c: effort limits ----
    try:
        el = pv.get_dof_max_forces()[0]
        _p(f"P4c left-arm effort limits: {[round(float(el[j]),1) for j in left_ids]} (max|τ| seen was 40)")
    except Exception as e:
        _p(f"P4c effort-limit read failed: {e}")

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
