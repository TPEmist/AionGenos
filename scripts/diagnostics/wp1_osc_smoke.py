"""WP1-① OSC test-bed smoke — boot the OSC bimanual env, step a few
motion-only (pose_abs) actions, confirm the controller swap does not crash
and the action space is well-formed.

This is the ① smoke of docs/p2_prereg/wp1_controller_provenance.md:
NOT a contact test (wrench axes are all 0 at this stage); it validates that
OperationalSpaceControllerActionCfg boots on the openarm bimanual URDF and
accepts pose targets. Contact behaviour is WP1-③.

Usage (A4500, IsaacLab python):
  /home/control/IsaacLab/isaaclab.sh -p scripts/diagnostics/wp1_osc_smoke.py --headless
"""

from __future__ import annotations

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=20)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import aiongenos.tasks  # noqa: F401  (registers the gym ids)
from isaaclab_tasks.utils import parse_env_cfg


def main() -> None:
    gym_id = "Isaac-AionGenos-WP1-Contact-v0"
    # IsaacLab convention (mirrors arena_adapter.py): parse the cfg from the
    # registry, then pass it to gym.make(cfg=...). gym.make alone does not
    # supply the required `cfg` arg to ManagerBasedRLEnv.
    env_cfg = parse_env_cfg(gym_id, num_envs=1, use_fabric=True)
    print(f"[smoke] cfg parsed OK", flush=True)  # flush: C-layer crash on
    # the next line leaves NO python traceback, so these prints are the only
    # way to localise WHERE it died (2026-08-03: first run died silently
    # after sim build, no traceback → suspected OSC solver C++ crash on
    # first step; these flushed markers bracket make/reset/step to pin it).
    env = gym.make(gym_id, cfg=env_cfg, render_mode=None)
    print(f"[smoke] env made: {gym_id}", flush=True)
    print(f"[smoke] action_space:      {env.action_space}")
    print(f"[smoke] observation_space: {type(env.observation_space).__name__}")

    obs, _ = env.reset(seed=4700)
    act_dim = env.action_space.shape[-1]
    print(f"[smoke] reset OK. action dim = {act_dim}")

    # Motion-only: feed a small constant pose_abs-style action and confirm
    # the env steps without controller/solver error. We do NOT assert task
    # success here — the ① acceptance (motion-equivalence to DiffIK) is a
    # separate tracking check; this smoke just proves the swap boots + steps.
    ok_steps = 0
    for i in range(args_cli.steps):
        action = torch.zeros((env.unwrapped.num_envs, act_dim), device=env.unwrapped.device)
        obs, rew, term, trunc, info = env.step(action)
        ok_steps += 1

    print(f"[smoke] stepped {ok_steps}/{args_cli.steps} OSC steps with no crash")
    print(f"[smoke] VERDICT: OSC bimanual test-bed BOOTS + STEPS ✓ "
          f"(action dim {act_dim}; motion-only, wrench axes off)")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
