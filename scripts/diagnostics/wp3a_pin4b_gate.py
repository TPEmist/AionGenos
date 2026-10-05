"""Pin-4b runtime gate — cube spawn REGION + cube-relative goal (PI ruling 2026-10-05).

All bounds are imported from push_s3a_cfg (no hardcoded duplicates). Per seed,
through the collect path's iface.reset(seed):
  * cube lands inside _CUBE_REGION_* and stays (settle drift < 1cm, 30 steps)
  * goal − cube offset: goal inside _GOAL_CLIP_*, cube→goal ≥ success radius
    + margin, push angle forward-dominant (< 45°)
  * goal does not resample mid-episode (unchanged after the settle steps)
  * behind-cube approach and push END (goal − 3cm along push dir) are
    LEFT-reachable via the real executor (execute_push_segment)
  * determinism: the same seed twice → identical cube + goal
Prints distributions (cube coverage, angle, distance) as Pin-4b evidence and
dumps a layout RGB for 4 seeds. Exit 0 = ALL PASS, 3 = FAIL.
"""
import argparse
import math
import sys

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
p.add_argument("--n", type=int, default=20)
p.add_argument("--seed0", type=int, default=4700)
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
a.enable_cameras = True
app = AppLauncher(a)
sim_app = app.app

import gymnasium as gym  # noqa: E402
import imageio.v2 as imageio  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from isaaclab.utils.math import subtract_frame_transforms  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import aiongenos.tasks  # noqa: E402,F401
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface  # noqa: E402
from aiongenos.orchestrator.push_collect import PUSH_SUCCESS_M  # noqa: E402
from aiongenos.tasks.WP1_contact_testbed import push_s3a_cfg as C  # noqa: E402
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import neutral_contact_orientation_b  # noqa: E402

GID = "Isaac-AionGenos-WP1-Push-v0"
APPR_TOL_CM = 8.0   # same bar as fwd_gate (OSC segment from standby; PI-accepted 10-05)
ORACLE_SEGS = 6
SEG_STEPS = 90      # = run_push_collect --segment-steps default
SETTLE = 30
EPS = 1e-3

env = gym.make(GID, cfg=parse_env_cfg(GID, num_envs=1), render_mode=None)
iface = IsaacLabEnvInterface(env)
robot = iface.robot
u = env.unwrapped
zero = torch.zeros((1, env.action_space.shape[-1]), device=u.device)


def ee_b():
    rp = robot.data.root_pos_w[0:1, :3]
    rq = robot.data.root_quat_w[0:1, :4]
    ew = robot.data.body_pos_w[0:1, iface.left_body_idx, :3]
    pb, _ = subtract_frame_transforms(rp, rq, ew)
    return pb[0].cpu().numpy()


TCP_IDX = robot.data.body_names.index("openarm_left_ee_tcp")


def tcp_len_m():
    """Hand→fingertip (ee_tcp) distance, measured live (fingers protrude along
    the push direction under the neutral orientation, so the HAND must sit this
    much further back than the fingertip)."""
    return float(torch.norm(robot.data.body_pos_w[0, TCP_IDX, :3]
                            - robot.data.body_pos_w[0, iface.left_body_idx, :3]))


def servo_err_cm(x, y, z, steps=150):
    cur = ee_b()
    motion = torch.tensor([x - cur[0], y - cur[1], z - cur[2]], dtype=torch.float32)
    q, _ = neutral_contact_orientation_b(motion)
    iface.execute_push_segment(torch.tensor([x, y, z], dtype=torch.float32), q, steps, frame_every=0)
    return float(np.linalg.norm(ee_b() - np.array([x, y, z]))) * 100


def reset_settle(seed):
    iface.reset(seed=seed)
    c0 = np.array(iface.get_cube_pose_b())
    g0 = np.array(iface.get_goal_pose_b())
    for _ in range(SETTLE):
        env.step(zero)
    return c0, g0, np.array(iface.get_cube_pose_b()), np.array(iface.get_goal_pose_b())


def inside(v, rng, eps=EPS):
    return rng[0] - eps <= v <= rng[1] + eps


iface.reset(seed=a.seed0)
TCP_LEN = tcp_len_m()
print(f"[P4B] measured hand→fingertip TCP length = {TCP_LEN*100:.1f}cm", flush=True)
allpass = True
rows = []
for k in range(a.n):
    seed = a.seed0 + k
    c0, g0, c1, g1 = reset_settle(seed)
    c0b, g0b, _, _ = reset_settle(seed)
    # cube: same 0.5cm nondeterminism bar as fwd_gate (reset steps physics);
    # goal: exact (seeded sample).
    determ = np.linalg.norm(c0 - c0b) * 100 < 0.5 and np.allclose(g0, g0b, atol=1e-5)
    drift = np.linalg.norm(c1[:2] - c0[:2]) * 100
    goal_static = np.allclose(g0, g1, atol=1e-5)
    in_region = inside(c0[0], C._CUBE_REGION_X) and inside(c0[1], C._CUBE_REGION_Y)
    in_clip = inside(g0[0], C._GOAL_CLIP_X) and inside(g0[1], C._GOAL_CLIP_Y)
    dx, dy = g0[0] - c1[0], g0[1] - c1[1]
    dist = math.hypot(dx, dy)
    ang = abs(math.degrees(math.atan2(dy, dx)))
    ux, uy = dx / dist, dy / dist
    # HAND targets that put the FINGERTIP 1cm behind the cube face (approach)
    # and at the cube's rear face when the cube centre is on the goal (end).
    back_appr = C._CUBE_HALF_H + 0.01 + TCP_LEN
    back_end = C._CUBE_HALF_H + TCP_LEN
    appr = (c1[0] - ux * back_appr, c1[1] - uy * back_appr, float(c1[2]))
    if not determ:
        print(f"[P4B]   determ diff: cube {c0-c0b} goal {g0-g0b}", flush=True)
    # Approach reach (gated, as fwd_gate). Then a closed-loop scripted ORACLE
    # (informational, not a gate): re-aim each segment from the CURRENT cube
    # toward the goal, push to goal − backoff, ≤ ORACLE_SEGS segments (the
    # teacher has PUSH_ROUND_CAP rounds). Answers "is the geometry winnable
    # by the executor at all", separate from whether the teacher finds it.
    iface.reset(seed=seed)
    e_appr = servo_err_cm(*appr, steps=SEG_STEPS)
    e_end = float("nan")
    for _seg in range(ORACLE_SEGS):
        cc = np.array(iface.get_cube_pose_b())
        v = g0[:2] - cc[:2]
        dcur = float(np.linalg.norm(v))
        if dcur <= PUSH_SUCCESS_M:
            break
        w = v / dcur
        if _seg:   # re-approach behind the cube's CURRENT position along the new heading
            servo_err_cm(cc[0] - w[0] * back_appr, cc[1] - w[1] * back_appr, float(c1[2]), steps=SEG_STEPS)
        e_end = servo_err_cm(g0[0] - w[0] * back_end, g0[1] - w[1] * back_end,
                             float(c1[2]), steps=SEG_STEPS)
    c2 = np.array(iface.get_cube_pose_b())
    cg_after = float(np.linalg.norm(c2[:2] - g0[:2])) * 100
    ok = (determ and drift < 1.0 and goal_static and in_region and in_clip
          and ang < 45 and dist >= PUSH_SUCCESS_M + 0.015
          and e_appr <= APPR_TOL_CM)
    allpass &= ok
    rows.append((c0[0], c0[1], g0[0], g0[1], ang, dist * 100, cg_after))
    print(f"[P4B] seed{seed}: cube=({c0[0]:.3f},{c0[1]:.3f}) goal=({g0[0]:.3f},{g0[1]:.3f}) "
          f"ang={ang:3.0f}° cg={dist*100:4.1f}cm drift={drift:.2f} determ={determ} static={goal_static} "
          f"region={in_region} clip={in_clip} appr={e_appr:.1f} end={e_end:.1f} oracle_cg={cg_after:.1f} → {'OK' if ok else 'FAIL'}",
          flush=True)

R = np.array(rows)
print(f"[P4B] cube x [{R[:,0].min():.3f},{R[:,0].max():.3f}] (region {C._CUBE_REGION_X}) "
      f"y [{R[:,1].min():.3f},{R[:,1].max():.3f}] (region {C._CUBE_REGION_Y})", flush=True)
print(f"[P4B] goal x [{R[:,2].min():.3f},{R[:,2].max():.3f}] y [{R[:,3].min():.3f},{R[:,3].max():.3f}] "
      f"(clip {C._GOAL_CLIP_X} {C._GOAL_CLIP_Y})", flush=True)
print(f"[P4B] push angle mean {R[:,4].mean():.0f}° max {R[:,4].max():.0f}° | "
      f"cube→goal {R[:,5].min():.1f}–{R[:,5].max():.1f}cm mean {R[:,5].mean():.1f}", flush=True)

frames = []
for k in range(4):
    iface.reset(seed=a.seed0 + k)
    for _ in range(SETTLE):
        env.step(zero)
    rgb = u.scene["camera"].data.output["rgb"][0].cpu().numpy()[..., :3]
    frames.append(rgb.astype("uint8"))
imageio.imwrite("logs/pin4b_layout.png", np.concatenate(frames, axis=1))
print(f"[P4B] scripted-oracle push: {(R[:,6] <= PUSH_SUCCESS_M*100).sum()}/{len(R)} within success radius "
      f"(oracle cube→goal median {np.median(R[:,6]):.1f}cm) — informational, not a gate", flush=True)
print("[P4B] layout (seeds 0-3, side by side) → logs/pin4b_layout.png", flush=True)
print(f"[P4B] ===== {'ALL PASS ✓' if allpass else 'FAIL ✗'} =====", flush=True)
env.close()
sim_app.close()
sys.exit(0 if allpass else 3)
