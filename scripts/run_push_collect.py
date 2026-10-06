"""Driver for the WP1-③a push collect instrument (push_collect.py).

Builds the push env directly via the WP1-Push gym id (NOT via the P1 curriculum
ladder — push is a separate task family), wraps it in IsaacLabEnvInterface, and
runs run_push_collect_loop. For smoke: --episodes small, --label pilot.

Run:
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/run_push_collect.py --episodes 1 --seed 4700 --headless --enable_cameras

Memory-ON pilot (wp3a_pilot_plan.md step (c)):
  ... --episodes 50 --label pilot --use_memory \
      --recap_buffer_root workspace/recaps_push_pilot --headless --enable_cameras
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
# ── cross-episode memory (push_memory; mirrors run_collect.py's flag set) ──
parser.add_argument("--recap_buffer_root", type=str, default=None,
                    help="When set, write a push recap per episode here (and read it for "
                         "--use_memory). PUSH-ONLY root (e.g. workspace/recaps_push_pilot): "
                         "retrieval has no task filter, so never share a root with reach/L2.")
parser.add_argument("--use_memory", action="store_true",
                    help="At round 1 of each ep, retrieve top-K past push recaps and inject "
                         "them as a preamble. Requires --recap_buffer_root.")
parser.add_argument("--recap_buffer_readonly", action="store_true",
                    help="Read memory but persist NO new recaps this run (collect.py A8 §8.5 gate).")
parser.add_argument("--memory_top_k", type=int, default=3, help="Top-K retrieved recaps.")
parser.add_argument("--memory_image_weight", type=float, default=0.4,
                    help="α in score = α·img_cos + (1−α)·state_sim.")
parser.add_argument("--memory_state_scale_cm", type=float, default=30.0,
                    help="state_sim = exp(−‖Δ init TCP grid‖ / scale) — L0a default. The TCP "
                         "starts at the fixed standby, so this term is ≈ constant; the image "
                         "term ranks (observables-only key, PI ruling 2026-10-05).")
parser.add_argument("--obs_rung", type=int, default=1, choices=(1, 2, 3),
                    help="Disclosed scaffold rung (wp3a_pilot_plan.md): 1 = image + proprio only; "
                         "2 = + scalar TCP→cube / cube→goal; 3 = + coordinates. Sets "
                         "env.push_obs_rung; recorded in every replay/summary/recap.")
parser.add_argument("--dump_images_root", type=str, default="data/collect_dumps",
                    help="Per-ep round PNGs + meta.json under {root}/{run_id}/{ep_id}/ "
                         "(memory needs round_01_pre.png as the recap image anchor). '' disables.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import json
import logging
import sys
from pathlib import Path

# AppLauncher reconfigures the root logger (same fix as run_collect.py): put a
# stdout handler on aiongenos.* so push_collect / push_memory INFO lines show.
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
_alog = logging.getLogger("aiongenos")
_alog.setLevel(logging.INFO)
_alog.addHandler(_handler)
_alog.propagate = False
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
    # For the GIF (human-eye gate ONLY — not the training observation): KEEP the
    # GREEN GOAL cuboid visible (the PI must see cube-vs-goal) but hide the
    # obstructing CURRENT-pose RGB axis markers that buried the 4.8cm cube.
    # debug_vis stays True (so the goal cuboid renders); only the current-pose
    # frame markers are made invisible. Rendering only — does NOT affect control
    # or the real observation pipeline.
    if args_cli.gif_frame_every:
        for term in ("left_ee_pose", "right_ee_pose"):
            c = getattr(_cfg.commands, term, None)
            if c is None:
                continue
            if hasattr(c, "current_pose_visualizer_cfg"):
                for m in c.current_pose_visualizer_cfg.markers.values():
                    m.visible = False
    env = gym.make(GID, cfg=_cfg, render_mode=None)
    iface = IsaacLabEnvInterface(env)
    iface.push_obs_rung = args_cli.obs_rung   # shapes get_state's disclosed block

    # Push level config — a minimal LevelConfig carrying the PUSH control mode
    # + instruction + Pin-4a workspace bounds. Not in the P1 curriculum ladder.
    level_config = LevelConfig(
        level=99,
        name="WP1_3a_push",
        control_mode=ControlMode.PUSH_WAYPOINT,
        task_instruction_template="Push the yellow cube onto the green zone on the table.",
        workspace_bounds=WorkspaceBounds(),
    )

    replay = ReplayBuffer(cfg.local_replay_path)
    _p(f"teacher={teacher_url} episodes={args_cli.episodes} label={args_cli.label} obs_rung={args_cli.obs_rung}")

    # Memory wiring (same gate shape as run_collect.py)
    recap_buffer = None
    memory_retriever = None
    dump_root = Path(args_cli.dump_images_root) if args_cli.dump_images_root else None
    if args_cli.recap_buffer_root:
        from aiongenos.memory.recap_buffer import RecapBuffer
        from aiongenos.orchestrator.push_memory import PushMemoryRetriever, assert_push_only_buffer
        recap_buffer = RecapBuffer(root=args_cli.recap_buffer_root)
        recap_buffer.load()
        assert_push_only_buffer(recap_buffer, args_cli.obs_rung)   # no reach/L2 or other-rung recaps
        _p(f"recap buffer {args_cli.recap_buffer_root}: {len(recap_buffer)} existing records"
           f"{' (READONLY)' if args_cli.recap_buffer_readonly else ''}")
        if dump_root is None:
            _p("WARNING: --dump_images_root disabled → recaps have no init_pre anchor and "
               "retrieval will drop every hit")
        if args_cli.use_memory:
            memory_retriever = PushMemoryRetriever(
                buffer=recap_buffer, top_k=args_cli.memory_top_k,
                image_weight=args_cli.memory_image_weight,
                state_scale_cm=args_cli.memory_state_scale_cm,
                obs_rung=args_cli.obs_rung,
            )
            _p(f"memory ON: top_k={args_cli.memory_top_k} img_w={args_cli.memory_image_weight} "
               f"state_scale={args_cli.memory_state_scale_cm}cm")
    elif args_cli.use_memory:
        _p("WARNING: --use_memory ignored (no --recap_buffer_root)")

    summary = run_push_collect_loop(
        env=iface,
        level_config=level_config,
        teacher_url=teacher_url,
        replay=replay,
        num_episodes=args_cli.episodes,
        env_seed_base=args_cli.seed,
        episode_label=args_cli.label,
        recap_buffer=recap_buffer,
        steps_per_segment=args_cli.segment_steps,
        gif_frame_every=args_cli.gif_frame_every,
        memory_retriever=memory_retriever,
        recap_buffer_readonly=args_cli.recap_buffer_readonly,
        dump_images_root=dump_root,
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
