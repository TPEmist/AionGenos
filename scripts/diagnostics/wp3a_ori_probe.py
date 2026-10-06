"""WP1-③a 6D pose-path end-to-end probe (PI ruling 2026-10-05, Rule 6).

Commands the push executor exactly as push_collect does (rest orientation from
the live standby pose, base-axis ORI offset via push_body.command_quat, TCP
target) for: rest, P=+45, Y=+30, R=+30 — each from a fresh reset, holding the
TCP at its rest position. Records per probe: orientation tracking error (deg,
final + mean of last 20 steps), the ACHIEVED rotation of the hand relative to
rest decomposed about base axes, TCP position error, pre-clip τ peak. Also
checks the TCP direction actually turned: angle between the rest finger axis
(hand→TCP) and the achieved one vs the commanded rotation angle.

Exit 0 = every probe within ORI_TOL_DEG of command and τ pre-clip < 1.0; 3 = FAIL.
"""
import argparse
import math
import sys
from types import SimpleNamespace

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
p.add_argument("--steps", type=int, default=150)
p.add_argument("--seed", type=int, default=4700)
p.add_argument("--probes", default="", help="extra probes, e.g. 'Y-30:0,-30,0;Y+15:0,15,0'")
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
ORI_TOL_DEG = 8.0
TAU_SETTLE = 20   # reset transient window, reported separately (rest probe = baseline)
PROBES = [("rest", 0, 0, 0), ("P+45", 45, 0, 0), ("Y+30", 0, 30, 0), ("R+30", 0, 0, 30)]

for _spec in filter(None, a.probes.split(";")):
    _n, _v = _spec.split(":")
    PROBES.append((_n, *[int(t) for t in _v.split(",")]))

env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
iface = IsaacLabEnvInterface(env)
r = iface.robot
tcp_idx = r.find_bodies(pb.TCP_BODY)[0][0]
hand = iface.left_body_idx


def finger_axis_b():
    v = r.data.body_pos_w[0, tcp_idx, :3] - r.data.body_pos_w[0, hand, :3]
    return v / torch.norm(v)


allpass = True
for name, P, Y, R in PROBES:
    iface.reset(seed=a.seed)
    q_rest = iface.get_left_hand_quat_b()
    ax_rest = finger_axis_b()
    tcp0 = torch.tensor(iface.get_left_tcp_pos_b(), device=q_rest.device)
    ori = SimpleNamespace(p=P, y=Y, r=R)
    q_cmd = pb.command_quat(q_rest, ori)
    seg = iface.execute_push_segment(tcp0, q_cmd, a.steps, target_is_tcp=True)
    q_now = iface.get_left_hand_quat_b()
    cmd_angle = pb.quat_angle_deg(q_cmd, q_rest)
    got_angle = pb.quat_angle_deg(q_now, q_rest)
    # achieved relative rotation in base axes: q_rel = q_now ⊗ q_rest⁻¹
    q_rel = pb.quat_mul(q_now, pb.quat_conj(q_rest))
    w, x, y, z = [float(v) for v in q_rel]
    ang = 2 * math.acos(max(-1.0, min(1.0, abs(w))))
    s = math.sin(ang / 2) or 1.0
    sign = 1.0 if w >= 0 else -1.0
    axis = [round(sign * x / s, 2), round(sign * y / s, 2), round(sign * z / s, 2)]
    finger_turn = math.degrees(math.acos(max(-1.0, min(1.0, float(torch.dot(ax_rest, finger_axis_b()))))))
    tcp_err = float(torch.norm(torch.tensor(iface.get_left_tcp_pos_b(), device=tcp0.device) - tcp0)) * 100
    tail = seg["ori_err_deg"][-20:]
    err_final = seg["ori_err_deg_final"]
    tau = seg["tau_pre_per_step"]
    sat_steps = [i for i, t in enumerate(tau) if t >= 1.0]
    tau_after = max(tau[TAU_SETTLE:]) if len(tau) > TAU_SETTLE else float("nan")
    ok = err_final <= ORI_TOL_DEG and tau_after < 1.0
    allpass &= ok
    print(f"[ORI] {name:5s}: cmd {cmd_angle:5.1f}° got {got_angle:5.1f}° about base axis {axis} | "
          f"track err final {err_final:.1f}° last20 mean {sum(tail)/len(tail):.1f}° | "
          f"finger axis turned {finger_turn:.1f}° | TCP pos err {tcp_err:.1f}cm | "
          f"τ pre-clip peak {seg['tau_peak_preclip']:.2f} (saturated steps {sat_steps[:6]}{'…' if len(sat_steps) > 6 else ''}; "
          f"peak after step {TAU_SETTLE} {tau_after:.2f}) → {'OK' if ok else 'FAIL'}", flush=True)

print(f"[ORI] ===== {'ALL PASS ✓' if allpass else 'FAIL ✗'} =====", flush=True)
env.close()
sim_app.close()
sys.exit(0 if allpass else 3)
