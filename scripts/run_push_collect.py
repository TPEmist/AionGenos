"""Driver for the WP1-③a push collect instrument (push_collect.py).

Builds the push env directly via the WP1-Push gym id (NOT via the P1 curriculum
ladder — push is a separate task family), wraps it in IsaacLabEnvInterface, and
runs run_push_collect_loop. For smoke: --episodes small, --label pilot.

Run:
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/run_push_collect.py --episodes 1 --seed 4700 --headless --enable_cameras
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--episodes", type=int, default=1)
parser.add_argument("--seed", type=int, default=4700)
parser.add_argument("--label", type=str, default="pilot", choices=["pilot", "confirmatory"])
parser.add_argument("--teacher-url", type=str, default="http://10.80.9.148:18888")
parser.add_argument("--segment-steps", type=int, default=90)
parser.add_argument("--gif-frame-every", type=int, default=0,
                    help=">0: capture an RGB frame every N servo steps → logs/push_gif_<run>.gif (human-eye gate)")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import json
import gymnasium as gym
import aiongenos.tasks  # noqa (registers WP1-Push)
from isaaclab_tasks.utils import parse_env_cfg
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.orchestrator.push_collect import run_push_collect_loop
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.config import AionGenosConfig, LevelConfig, ControlMode, WorkspaceBounds

GID = "Isaac-AionGenos-WP1-Push-v0"


def _p(m): print(f"[PUSHCOL] {m}", flush=True)


def main():
    cfg = AionGenosConfig()
    teacher_url = args_cli.teacher_url or cfg.teacher_url

    _cfg = parse_env_cfg(GID, num_envs=1)
    # For the GIF (human-eye gate ONLY — not the training observation), disable
    # the command-pose debug visualizers (big RGB axes + goal cuboids) that
    # obstruct the small 4.8cm cube. Does NOT affect control or the real
    # observation pipeline — purely the rendered frames for the PI to inspect.
    if args_cli.gif_frame_every:
        for term in ("left_ee_pose", "right_ee_pose"):
            c = getattr(_cfg.commands, term, None)
            if c is not None and hasattr(c, "debug_vis"):
                c.debug_vis = False
    env = gym.make(GID, cfg=_cfg, render_mode=None)
    iface = IsaacLabEnvInterface(env)

    # Push level config — a minimal LevelConfig carrying the PUSH control mode
    # + instruction + Pin-4a workspace bounds. Not in the P1 curriculum ladder.
    level_config = LevelConfig(
        level=99,
        name="WP1_3a_push",
        control_mode=ControlMode.PUSH_WAYPOINT,
        task_instruction_template="Push the yellow cube onto the green goal marker.",
        workspace_bounds=WorkspaceBounds(),
    )

    replay = ReplayBuffer(cfg.local_replay_path)
    _p(f"teacher={teacher_url} episodes={args_cli.episodes} label={args_cli.label}")

    summary = run_push_collect_loop(
        env=iface,
        level_config=level_config,
        teacher_url=teacher_url,
        replay=replay,
        num_episodes=args_cli.episodes,
        env_seed_base=args_cli.seed,
        episode_label=args_cli.label,
        recap_buffer=None,   # smoke: defer recap buffer; trigger-check separately
        steps_per_segment=args_cli.segment_steps,
        gif_frame_every=args_cli.gif_frame_every,
    )
    _p(f"SUMMARY run_id={summary['run_id']} success={summary['n_success']}/{args_cli.episodes}")
    for ep in summary["episodes"]:
        _p(f"  ep {ep['ep_id'][:8]} outcome={ep['outcome']} rounds={ep['rounds']}")
    # dump the full per-round records for inspection
    out = f"logs/push_smoke_{summary['run_id']}.json"
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    _p(f"per-round records → {out}")
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
