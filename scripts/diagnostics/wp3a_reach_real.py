"""WP1-③a reach check WITH THE CUBE IN PLACE (PI 2026-10-15; replaces the
cube-parked wp3a_reach_tcp.py reading, which the PI rejected).

Per seed (the pilot seeds), through the same executor the pilot uses
(execute_push_segment, TCP target, rest orientation, 90-step rounds):
  phase A: 3 rounds to the APPROACH point = 1 cm behind the cube's rear face
           along cube→goal, at cube-centre height;
  phase B: 3 rounds to the PUSH END = goal − cube half-size along cube→goal.
After every round, measured in the world (no target-vs-TCP self-reference):
  - finger GEOMETRY (collision mesh points of both left fingers) → cube box
    min distance, and whether the cube moved;
  - cube→goal distance;
  - elbow joint4 (0 = fully straight; standby 1.78 rad) and the joint closest
    to its limit;
  - shoulder (link2 origin) → TCP distance;
  - lowest point of wrist link7 geometry vs table top.
Reach sphere: for each seed, one extra reset drives the TCP 1 m out along
shoulder→push-end and records the maximum shoulder→TCP distance reached.
**UNRELIABLE (2026-10-15 run).** With the carrot servo and joint limits the
arm can stall or fold (one seed ended at the joint4 limit, folded), so R_max
came out below distances the arm had actually reached. Do NOT read it as the
reach radius. Use the measured shoulder→TCP at the push end, plus the
straight-chain length (link2→link4→link6→TCP), instead.
Outputs: logs/wp3a_reach_real.json and one GIF per seed
(logs/reach_real_seed<k>.gif, front | top, round strip).
Usage: isaaclab.sh -p scripts/diagnostics/wp3a_reach_real.py --headless --enable_cameras [--seeds 5000,5018]
"""
import argparse
import json
import sys

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
p.add_argument("--seeds", default="5000,5001,5002,5018,5043")
p.add_argument("--frame_every", type=int, default=9)
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
a.enable_cameras = True
app = AppLauncher(a)
sim_app = app.app

import gymnasium as gym  # noqa: E402
import imageio.v2 as imageio  # noqa: E402
import numpy as np  # noqa: E402
import omni.usd  # noqa: E402
import torch  # noqa: E402
from isaaclab.utils.math import quat_apply, quat_apply_inverse  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

import aiongenos.tasks  # noqa: E402,F401
from aiongenos.orchestrator import push_body as pb  # noqa: E402
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402
from aiongenos.orchestrator.push_gif import compose_frame  # noqa: E402
from aiongenos.tasks.WP1_contact_testbed import push_s3a_cfg as C  # noqa: E402

GID = "Isaac-AionGenos-WP1-Push-TopCam-v0"
SEG = 90
ROUNDS = 3
TABLE_TOP_B = C._TABLE_TOP_Z - C._ROBOT_BASE_Z
HALF = C._CUBE_HALF_H

env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
iface = IsaacLabEnvInterface(env)
u = env.unwrapped
dev = u.device
robot = iface.robot
cube = u.scene["object"]
names = robot.data.body_names
jnames = robot.data.joint_names
LJ = [i for i, n in enumerate(jnames) if n.startswith("openarm_left_joint")]
J4 = jnames.index("openarm_left_joint4")
SH = names.index("openarm_left_link2")
stage = omni.usd.get_context().get_stage()


def body_local_points(body: str, stride: int = 20) -> torch.Tensor:
    """Collision-mesh points in the BODY frame (static relative transform)."""
    bp = stage.GetPrimAtPath(f"/World/envs/env_0/Robot/{body}")
    mb = np.array(UsdGeom.Xformable(bp).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    out = []
    for sub in Usd.PrimRange(bp, Usd.TraverseInstanceProxies()):
        if sub.IsA(UsdGeom.Mesh) and "collision" in str(sub.GetPath()):
            pts = np.array(UsdGeom.Mesh(sub).GetPointsAttr().Get(), dtype=float)[::stride]
            mm = np.array(UsdGeom.Xformable(sub).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
            out.append((np.c_[pts, np.ones(len(pts))] @ (mm @ np.linalg.inv(mb)))[:, :3])
    return torch.tensor(np.concatenate(out), dtype=torch.float32, device=dev)


iface.reset(seed=int(a.seeds.split(",")[0]))
GEOM = {b: body_local_points(b) for b in ("openarm_left_left_finger", "openarm_left_right_finger",
                                           "openarm_left_link7")}


def world_points(body: str) -> torch.Tensor:
    k = names.index(body)
    pts = GEOM[body]
    return quat_apply(robot.data.body_quat_w[0, k].expand(len(pts), 4), pts) + robot.data.body_pos_w[0, k]


def finger_to_cube_cm() -> float:
    pw = torch.cat([world_points("openarm_left_left_finger"), world_points("openarm_left_right_finger")])
    c, q = cube.data.root_pos_w[0, :3], cube.data.root_quat_w[0, :4]
    loc = quat_apply_inverse(q.expand(len(pw), 4), pw - c)
    d = torch.clamp(loc.abs() - HALF, min=0.0).norm(dim=1)
    return float(d.min()) * 100


def b(v_w: torch.Tensor) -> np.ndarray:
    return (v_w - robot.data.root_pos_w[0, :3]).cpu().numpy()


def state(cube0_b, goal_b) -> dict:
    tcp = np.array(iface.get_left_tcp_pos_b())
    sh = b(robot.data.body_pos_w[0, SH])
    c = np.array(iface.get_cube_pose_b())
    q = robot.data.joint_pos[0, LJ]
    lim = robot.data.soft_joint_pos_limits[0, LJ]
    marg = torch.rad2deg(torch.minimum(q - lim[:, 0], lim[:, 1] - q))
    k = int(torch.argmin(marg))
    return {"tcp_b": tcp.round(4).tolist(), "finger_to_cube_cm": round(finger_to_cube_cm(), 2),
            "cube_moved_cm": round(float(np.linalg.norm(c[:2] - cube0_b[:2])) * 100, 2),
            "cube_goal_cm": round(float(np.linalg.norm(c[:2] - goal_b[:2])) * 100, 2),
            "elbow_j4_rad": round(float(robot.data.joint_pos[0, J4]), 3),
            "shoulder_tcp_cm": round(float(np.linalg.norm(tcp - sh)) * 100, 1),
            "tightest_joint": [jnames[LJ[k]], round(float(marg[k]), 1)],
            "wrist_low_above_table_cm": round((float(world_points("openarm_left_link7")[:, 2].min())
                                              - float(robot.data.root_pos_w[0, 2]) - TABLE_TOP_B) * 100, 2)}


report = {}
for seed in [int(s) for s in a.seeds.split(",")]:
    iface.reset(seed=seed)
    cube0 = np.array(iface.get_cube_pose_b())
    goal = np.array(iface.get_goal_pose_b())
    dirv = (goal[:2] - cube0[:2]) / np.linalg.norm(goal[:2] - cube0[:2])
    z = float(cube0[2])
    appr = np.array([*(cube0[:2] - dirv * (HALF + 0.01)), z])
    end = np.array([*(goal[:2] - dirv * HALF), z])
    sh0 = b(robot.data.body_pos_w[0, SH])
    q_rest = iface.get_left_hand_quat_b()
    q_cmd = pb.command_quat(q_rest, None)
    rows, gif = [], []
    for phase, tgt in (("A_approach", appr), ("B_push_end", end)):
        for rnd in range(ROUNDS):
            seg = iface.execute_push_segment(torch.tensor(tgt, dtype=torch.float32), q_cmd, SEG,
                                             frame_every=a.frame_every, target_is_tcp=True)
            ff = seg.get("frames") or []
            tf = seg.get("frames_top") or [b""] * len(ff)
            s = state(cube0, goal)
            s.update({"phase": phase, "round": rnd + 1, "target_b": tgt.round(4).tolist(),
                      "tcp_err_cm": round(float(np.linalg.norm(np.array(s["tcp_b"]) - tgt)) * 100, 2),
                      "first_cube_move": (seg.get("contact") or {}).get("first_cube_move"),
                      "guard": (seg.get("table_guard") or {}).get("target_clamp")})
            rows.append(s)
            tag = (f"seed{seed} {phase} R{rnd+1} finger-cube {s['finger_to_cube_cm']}cm "
                                      f"cube moved {s['cube_moved_cm']}cm j4 {s['elbow_j4_rad']}")
            # scripted probe, no model in the loop → both panels are PI-only views
            gif += [compose_frame(f, t, tag, front_fed=False, top_fed=False) for f, t in zip(ff, tf)]
            print(f"[REAL] seed{seed} {phase} R{rnd+1} tgt {tgt.round(3)} tcp {s['tcp_b']} err {s['tcp_err_cm']}cm "
                  f"finger→cube {s['finger_to_cube_cm']}cm moved {s['cube_moved_cm']}cm cube→goal {s['cube_goal_cm']}cm "
                  f"j4 {s['elbow_j4_rad']} sh→tcp {s['shoulder_tcp_cm']}cm tight {s['tightest_joint']} "
                  f"wrist-table {s['wrist_low_above_table_cm']}cm guard {bool(s['guard'])}", flush=True)
    imageio.mimsave(f"logs/reach_real_seed{seed}.gif", gif, duration=0.12)
    # reach sphere along shoulder→push-end
    iface.reset(seed=seed)
    cube.write_root_state_to_sim(torch.cat([robot.data.root_pos_w[:, :3] + torch.tensor([0, -1.5, 0.05], device=dev),
                                            cube.data.default_root_state[:, 3:]], dim=1))
    far = sh0 + (end - sh0) / np.linalg.norm(end - sh0) * 1.0
    rmax = 0.0
    for _ in range(4):
        iface.execute_push_segment(torch.tensor(far, dtype=torch.float32), q_cmd, SEG, frame_every=0, target_is_tcp=True)
        rmax = max(rmax, float(np.linalg.norm(np.array(iface.get_left_tcp_pos_b()) - sh0)) * 100)
    sphere = {"shoulder_b": sh0.round(4).tolist(), "R_max_toward_end_cm": round(rmax, 1),
              "shoulder_to_approach_cm": round(float(np.linalg.norm(appr - sh0)) * 100, 1),
              "shoulder_to_push_end_cm": round(float(np.linalg.norm(end - sh0)) * 100, 1),
              "j4_at_Rmax": round(float(robot.data.joint_pos[0, J4]), 3)}
    print(f"[REAL] seed{seed} SPHERE {sphere}", flush=True)
    report[seed] = {"cube0_b": cube0.round(4).tolist(), "goal_b": goal.round(4).tolist(),
                    "approach_b": appr.round(4).tolist(), "push_end_b": end.round(4).tolist(),
                    "rounds": rows, "sphere": sphere}
with open("logs/wp3a_reach_real.json", "w") as f:
    json.dump(report, f, indent=1, default=str)
print("[REAL] → logs/wp3a_reach_real.json", flush=True)
env.close()
sim_app.close()
sys.exit(0)
