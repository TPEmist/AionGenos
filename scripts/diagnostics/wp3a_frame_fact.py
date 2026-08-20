"""Minimal fact probe: where ARE things, in world and root frame?

Before reporting Pin-10 (raise table), verify the confound I keep hitting:
is z=0.024 (my sweep target, fed as ROOT-frame) actually at the table/cube
contact height, or am I probing empty space below the table? Reads, no logic.
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
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg
from isaaclab.utils.math import subtract_frame_transforms

GID = "Isaac-AionGenos-WP1-ReachProbe-PosFree-v0"


def _p(m): print(f"[FF] {m}", flush=True)


def main():
    env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    env.reset(seed=4700)
    for _ in range(5):
        env.step(torch.zeros((1, env.action_space.shape[-1]), device=u.device))
    root_p = r.data.root_pos_w[0, :3]
    _p(f"root_pos_w = {[round(float(v),4) for v in root_p]}")
    for nm in ("openarm_left_hand", "openarm_right_hand"):
        bi = r.body_names.index(nm)
        w = r.data.body_pos_w[0, bi, :3]
        b, _ = subtract_frame_transforms(root_p.unsqueeze(0), r.data.root_quat_w[0:1, :4], w.unsqueeze(0))
        _p(f"{nm}: world={[round(float(v),4) for v in w]} root={[round(float(v),4) for v in b[0]]}")
    # scene objects (table / cube if present)
    for key in u.scene.keys() if hasattr(u.scene, "keys") else []:
        pass
    try:
        obj = u.scene["object"]
        cw = obj.data.root_pos_w[0, :3]
        _p(f"scene['object'] world={[round(float(v),4) for v in cw]}")
    except Exception as e:
        _p(f"no scene['object'] ({e})")
    # ground / table prim z: sample the lowest reachable EE z the sim allows —
    # infer table by where the arm rests. Print min EE world z at rest.
    _p("NOTE: cube cfg pos z=0.02 is WORLD; my sweep target z=0.024 was fed "
       "as ROOT. If root_pos_w z != 0, these differ by that offset.")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
