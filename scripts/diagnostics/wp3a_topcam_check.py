"""rung-1b top-down camera check: render front + top views at 4 seeds, verify the
top view sees the cube (yellow) and the goal (green) pixels in every seed; dump
a side-by-side PNG for the PI. Exit 0 = PASS."""
import argparse
import io
import sys

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
a.enable_cameras = True
app = AppLauncher(a)
sim_app = app.app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import aiongenos.tasks  # noqa: E402,F401
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402

GID = "Isaac-AionGenos-WP1-Push-TopCam-v0"
env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
iface = IsaacLabEnvInterface(env)
zero = torch.zeros((1, env.action_space.shape[-1]), device=env.unwrapped.device)
ok = True
rows = []
for seed in range(4700, 4704):
    iface.reset(seed=seed)
    for _ in range(10):
        env.step(zero)
    front = np.array(Image.open(io.BytesIO(iface.get_rgb())).convert("RGB")).astype(int)
    top = np.array(Image.open(io.BytesIO(iface.get_rgb_top())).convert("RGB")).astype(int)
    yellow = ((top[..., 0] > 150) & (top[..., 1] > 150) & (top[..., 2] < 90)).sum()
    green = ((top[..., 1] > top[..., 0] + 40) & (top[..., 1] > top[..., 2] + 20)).sum()
    good = yellow > 20 and green > 20
    ok &= good
    print(f"[TOP] seed{seed}: top-view yellow px={yellow} green px={green} → {'OK' if good else 'FAIL'}", flush=True)
    rows.append(np.concatenate([front, top], axis=1))
Image.fromarray(np.concatenate(rows, axis=0).astype(np.uint8)).save("logs/topcam_views.png")
print("[TOP] front|top per seed → logs/topcam_views.png", flush=True)
print(f"[TOP] ===== {'ALL PASS ✓' if ok else 'FAIL ✗'} =====", flush=True)
env.close()
sim_app.close()
sys.exit(0 if ok else 3)
