"""Table-collision guard runtime check: command TCP targets INTO the table
volume and just outside it; the guard must clamp the first (TCP stays ≥ top +
margin) and leave the second untouched. Exit 0 = PASS, 3 = FAIL."""
import argparse
import sys

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
a.enable_cameras = True
app = AppLauncher(a)
sim_app = app.app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import aiongenos.tasks  # noqa: E402,F401
from aiongenos.orchestrator import push_body as pb  # noqa: E402
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402

GID = "Isaac-AionGenos-WP1-Push-v0"
env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
iface = IsaacLabEnvInterface(env)
ok = True
iface.reset(seed=4700)
box = pb.measure_table_box_b(env, iface.robot)
print(f"[TG] table box (base) x={box['x']} y={box['y']} top_z={box['top_z']:.4f}", flush=True)
cases = [("into table", (0.40, 0.20, box["top_z"] - 0.06), True),
         ("before edge, low", (box["x"][0] - 0.05, 0.10, box["top_z"] - 0.06), False)]
for name, tgt, expect in cases:
    iface.reset(seed=4700)
    q = iface.get_left_hand_quat_b()
    seg = iface.execute_push_segment(torch.tensor(tgt, device=q.device), q, 150, target_is_tcp=True)
    tg = seg["table_guard"]
    clamped = tg["target_clamp"] is not None
    tcp_z = seg["tcp_final_b"][2]
    good = clamped == expect and (not expect or tcp_z >= box["top_z"] + pb.TABLE_GUARD_MARGIN_M - 0.01)
    ok &= good
    print(f"[TG] {name}: target={tgt} clamped={clamped} (expect {expect}) setpoint_clamps={tg['setpoint_clamp_steps']} "
          f"tcp_final_z={tcp_z:.3f} → {'OK' if good else 'FAIL'}", flush=True)
print(f"[TG] ===== {'ALL PASS ✓' if ok else 'FAIL ✗'} =====", flush=True)
env.close()
sim_app.close()
sys.exit(0 if ok else 3)
