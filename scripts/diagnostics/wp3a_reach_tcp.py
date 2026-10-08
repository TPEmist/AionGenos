"""WP1-③a reachability of the CURRENT push executor (PI 2026-10-08).

The Pin-4b check (10-05) predates the TCP-target interface and the
rest-orientation command, and used an 8 cm bar on hand targets. This probe
measures what the teacher's commands can actually achieve today. It uses the
same call push_collect makes:
    env.execute_push_segment(tcp_target, command_quat(q_rest, ORI=0), 90, target_is_tcp=True)
from the standby pose (fresh reset per cell). The cube is parked off the table so
it cannot block the arm.

Per cell (x, y) at the cube-centre height _CUBE_REST_Z_B:
  - TCP error after 1, 2 and 3 segments (90 / 180 / 270 steps). Separates
    "slow" (error falls with time) from "unreachable" (error plateaus);
  - orientation error at the end (deg);
  - left-arm joint margin to the soft limits at the end (deg). A joint at its
    limit is the kinematic reason for a plateau.
Grid = the push workspace: cube region − 6 cm (approach behind the cube) to the
goal clip + 2 cm, all bounds imported from push_s3a_cfg (no literal copies).
Usage: isaaclab.sh -p scripts/diagnostics/wp3a_reach_tcp.py --headless [--dx 0.02]
"""
import argparse
import json
import sys

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
p.add_argument("--dx", type=float, default=0.02)
p.add_argument("--seed", type=int, default=5000)
p.add_argument("--zs", default=None, help="comma list of base-frame z; default = cube centre")
p.add_argument("--xs", default=None)
p.add_argument("--ys", default=None)
p.add_argument("--oris", default="0,0,0", help="semicolon list of P,Y,R deg (base axes, as the teacher ORI)")
p.add_argument("--out", default="logs/wp3a_reach_tcp.json")
p.add_argument("--tol_cm", type=float, default=1.0)   # contact-scale bar (cube half-size 2.4 cm)
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
app = AppLauncher(a)
sim_app = app.app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import aiongenos.tasks  # noqa: E402,F401
from aiongenos.orchestrator import push_body as pb  # noqa: E402
from aiongenos.vlm.parser import OriOffset  # noqa: E402
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402
from aiongenos.tasks.WP1_contact_testbed import push_s3a_cfg as C  # noqa: E402

GID = "Isaac-AionGenos-WP1-Push-v0"
SEG = 90                                        # = run_push_collect --segment-steps default
X0 = C._CUBE_REGION_X[0] - 0.06                 # behind the nearest cube
X1 = C._GOAL_CLIP_X[1] + 0.02
Y0 = min(C._CUBE_REGION_Y[0], C._GOAL_CLIP_Y[0]) - 0.04
Y1 = max(C._CUBE_REGION_Y[1], C._GOAL_CLIP_Y[1]) + 0.02
Z = C._CUBE_REST_Z_B

env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
iface = IsaacLabEnvInterface(env)
u = env.unwrapped
robot = iface.robot
cube = u.scene["object"]
LJ = [i for i, n in enumerate(robot.data.joint_names) if n.startswith("openarm_left_joint")]
print(f"[REACH] left joints {[robot.data.joint_names[i] for i in LJ]}", flush=True)


def park_cube():
    st = cube.data.default_root_state.clone()
    st[:, :3] = robot.data.root_pos_w[:, :3] + torch.tensor([0.0, -1.5, 0.05], device=u.device)
    cube.write_root_state_to_sim(st)


def tcp_b():
    return np.array(iface.get_left_tcp_pos_b())


LB = [(i, n) for i, n in enumerate(robot.data.body_names)
      if n.startswith("openarm_left_") and any(k in n for k in ("link6", "link7", "hand", "finger", "tcp"))]


def lowest_left_link():
    """Lowest left wrist/hand/finger body ORIGIN in the base frame (z, name). Origins only:
    a link's geometry can extend below its origin."""
    rz = float(robot.data.root_pos_w[0, 2])
    zs = [(float(robot.data.body_pos_w[0, i, 2]) - rz, n) for i, n in LB]
    return min(zs)


def joint_margin_deg():
    q = robot.data.joint_pos[0, LJ]
    lim = robot.data.soft_joint_pos_limits[0, LJ]
    m = torch.minimum(q - lim[:, 0], lim[:, 1] - q)
    k = int(torch.argmin(m))
    return float(torch.rad2deg(m[k])), robot.data.joint_names[LJ[k]]


xs = (np.array([float(v) for v in a.xs.split(",")]) if a.xs
      else np.round(np.arange(X0, X1 + 1e-9, a.dx), 3))
ys = (np.array([float(v) for v in a.ys.split(",")]) if a.ys
      else np.round(np.arange(Y0, Y1 + 1e-9, a.dx), 3))
ZS = [float(v) for v in a.zs.split(",")] if a.zs else [Z]
ORIS = [tuple(int(v) for v in o.split(",")) for o in a.oris.split(";")]
print(f"[REACH] grid x {xs[0]}..{xs[-1]} y {ys[0]}..{ys[-1]} z {Z:.3f} ({len(xs)*len(ys)} cells)", flush=True)
rows = []
for x, y, Z, O in [(x, y, z, o) for o in ORIS for z in ZS for x in xs for y in ys]:
    iface.reset(seed=a.seed)
    park_cube()
    q_rest = iface.get_left_hand_quat_b()
    q_cmd = pb.command_quat(q_rest, OriOffset(p=O[0], y=O[1], r=O[2]))
    tgt = torch.tensor([x, y, Z], dtype=torch.float32)
    errs, seg = [], None
    for _ in range(3):
        seg = iface.execute_push_segment(tgt, q_cmd, SEG, frame_every=0, target_is_tcp=True)
        errs.append(float(np.linalg.norm(tcp_b() - np.array([x, y, Z]))) * 100)
    jm, jn = joint_margin_deg()
    clamp = bool((seg.get("table_guard") or {}).get("target_clamp"))
    tf = tcp_b()
    lz, ln = lowest_left_link()
    rows.append({"x": float(x), "y": float(y), "z": float(Z), "ori_pyr": list(O), "tcp_final_b": [round(float(v), 4) for v in tf],
                 "lowest_left_link": [ln, round(lz, 4)],
                 "err_cm": [round(e, 2) for e in errs],
                 "ori_err_deg": seg.get("ori_err_deg_final"), "joint_margin_deg": round(jm, 1),
                 "tightest_joint": jn, "guard_clamp": clamp})
    print(f"[REACH] ori={O} x={x:.3f} y={y:.3f} z={Z:.3f} final_z={tf[2]:.3f} err 1/2/3 seg {errs[0]:5.2f}/{errs[1]:5.2f}/{errs[2]:5.2f} cm "
          f"ori {seg.get('ori_err_deg_final')}° margin {jm:5.1f}° ({jn}) guard {clamp} lowest {ln}@{lz:.3f}", flush=True)


def mark(r):
    e1, _, e3 = r["err_cm"]
    if e1 <= a.tol_cm:
        return "#"      # reached in one round
    if e3 <= a.tol_cm:
        return "+"      # reached, but needs >1 round (slow)
    return "x" if r["joint_margin_deg"] < 2.0 else "o"   # unreachable: joint limit / other


print(f"\n[REACH] map (rows y high→low, cols x low→high; tol {a.tol_cm} cm): "
      "# = 1 round, + = within 3 rounds, x = plateau at a joint limit, o = plateau, no limit", flush=True)
print("        " + " ".join(f"{x:.2f}"[1:] for x in xs), flush=True)
grid = {(r["x"], r["y"]): r for r in rows if r["z"] == ZS[0] and tuple(r["ori_pyr"]) == ORIS[0]}
for y in ys[::-1]:
    print(f"y={y:+.2f} " + "   ".join(mark(grid[(float(x), float(y))]) for x in xs), flush=True)
out = {"zs": ZS, "seg_steps": SEG, "tol_cm": a.tol_cm,
       "cube_region": [C._CUBE_REGION_X, C._CUBE_REGION_Y], "goal_clip": [C._GOAL_CLIP_X, C._GOAL_CLIP_Y],
       "rows": rows}
with open(a.out, "w") as f:
    json.dump(out, f, indent=1)
print(f"[REACH] → {a.out}", flush=True)
env.close()
sim_app.close()
sys.exit(0)
