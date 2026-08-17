"""WP1-③a diagnosis Step 0b — mass-matrix sub-block sanity on the BI robot.

The interleaved-index hypothesis: OSC takes M-sub-block by joint_ids; if the
BI joint ordering is interleaved and some layer assumes contiguous, the
sub-block is wrong. Direct check (no servo, no guessing which layer):
  - print the BI articulation's joint NAMES in order + the left/right ids
    find_joints resolves.
  - pull the full generalized mass matrix, extract the left-arm 7×7 sub-block
    the way OSC does (M[:, ids, :][:, :, ids]); check it is symmetric,
    positive-diagonal, and that the ids actually map to the left joints
    (name check). A garbled sub-block (asymmetric / cross-arm entries
    nonzero / ids hitting right-arm joints) is direct evidence.
Runs on the BiLeftOnly env (BI robot). Flushed; caller reads [MM].
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
    print(f"[MM] {m}", flush=True)


def main() -> None:
    gym_id = "Isaac-AionGenos-OSC-BiLeftOnly-v0"
    env_cfg = parse_env_cfg(gym_id, num_envs=1)
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    u = env.unwrapped
    robot = u.scene["robot"]
    env.reset(seed=4700)

    # joint name order (does BI interleave?)
    names = robot.joint_names
    _p(f"BI joint_names (in articulation order):")
    for i, nm in enumerate(names):
        _p(f"   [{i:2d}] {nm}")

    left_ids, left_names = robot.find_joints("openarm_left_joint.*")
    right_ids, right_names = robot.find_joints("openarm_right_joint.*")
    _p(f"left ids  = {left_ids}  names={left_names}")
    _p(f"right ids = {right_ids} names={right_names}")
    interleaved = sorted(left_ids) != list(range(min(left_ids), max(left_ids) + 1))
    _p(f"left ids contiguous? {'NO — INTERLEAVED' if interleaved else 'yes'}")

    # full generalized mass matrix, then the left sub-block the OSC way
    M = robot.root_physx_view.get_generalized_mass_matrices()[0]  # (nDoF,nDoF)
    _p(f"full M shape = {tuple(M.shape)}")
    lid = torch.tensor(left_ids, device=M.device)
    Msub = M[lid][:, lid]  # M[:,ids,:][:,:,ids] equivalent
    sym_err = float((Msub - Msub.T).abs().max())
    diag = torch.diagonal(Msub)
    _p(f"left 7×7 sub-block: diag={[round(float(d),4) for d in diag.tolist()]}")
    _p(f"   symmetric? max|M-Mᵀ|={sym_err:.2e}  (should be ~0)")
    _p(f"   diag all positive? {bool((diag > 0).all())}")

    # cross-arm coupling: entries between a left id and a right id in full M
    rid = torch.tensor(right_ids, device=M.device)
    cross = M[lid][:, rid]
    _p(f"left×right cross-block max|M|={float(cross.abs().max()):.2e} "
       f"(fixed-base 2 arms → should be ~0 = block-diagonal)")

    # verdict
    ok = sym_err < 1e-3 and bool((diag > 0).all())
    _p(f"VERDICT sub-block {'LOOKS VALID (symmetric, pos-diag) → index selection OK, culprit elsewhere' if ok else 'MALFORMED → index/ordering IS the bug'}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
