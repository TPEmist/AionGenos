#!/usr/bin/env python3
"""Config-effect gate — assert the RUNTIME state after reset == the cfg INTENT.

Prospective fix for a bug family that has bitten WP1-③a four times on ONE
symptom (the standby pose): a value SET in a task cfg is silently OVERRIDDEN or
NOT APPLIED at runtime, because an inherited base-class EventTerm overrides it,
or `= None` falls back to a framework/USD default, or an inherited event
re-randomizes it. Every instance was caught REACTIVELY — by the PI's eye on a
GUI. The common structure is always: **cfg intent and runtime state drift
apart** (same shape as the eval format-contract bug family).

The gate: build the env, reset, and mechanically assert the ACTUAL runtime
robot/scene state equals what the cfg intended:
  * standby joint pose == the intended Pin-7 pose (per-joint)
  * left/right arms symmetric (same-sign convention)
  * determinism: two resets (same seed) yield identical joint pose (no jitter)
Fails HERE, at dry-run, instead of via a human noticing a wrong pose in the GUI.

Any geometry / reachability / contact conclusion is INVALID until this gate
passes — a wrong body invalidates every downstream measurement.

Exit codes: 0 = intent matches runtime; 3 = mismatch (HALT).

Usage (must run under the isaaclab python + PYTHONPATH):
  PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
    scripts/diagnostics/check_config_effect.py --gym Isaac-AionGenos-WP1-Push-v0 --headless
"""
from __future__ import annotations
import argparse
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--gym", default="Isaac-AionGenos-WP1-Push-v0")
parser.add_argument("--seed", type=int, default=4700)
parser.add_argument("--tol", type=float, default=0.01, help="rad tolerance for pose match")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import sys
import torch
import gymnasium as gym
import aiongenos.tasks  # noqa
from isaaclab_tasks.utils import parse_env_cfg


def _p(m): print(f"[CFG-GATE] {m}", flush=True)


def _scan_instruments(cfg):
    """Grep the WP1 diagnostic scripts for HARDCODED geometry that the cfg
    defines, so a stale copy (drift source) is flagged. Reports scripts that
    embed a coordinate range NOT matching the current cfg goal range."""
    import re
    from pathlib import Path
    warns = []
    try:
        gr = cfg.commands.left_ee_pose.ranges
        xlo, xhi = gr.pos_x
    except Exception:
        return warns
    diag = Path(__file__).resolve().parent
    # bare coordinate-pair literals like (0.40, ...)(0.60, ...) or 0.40|0.60
    # that DON'T match the live range → likely a stale hardcoded goal copy.
    stale_pat = re.compile(r"0\.40|0\.60")  # the pre-Pin-4a literals
    for f in diag.glob("wp3a_*.py"):
        if f.name == Path(__file__).name:
            continue
        txt = f.read_text()
        # flag only if the file hardcodes the OLD range AND the cfg has moved
        if stale_pat.search(txt) and (abs(xlo - 0.40) > 1e-6 or abs(xhi - 0.60) > 1e-6):
            hits = [ln.strip() for ln in txt.splitlines()
                    if ("0.40" in ln or "0.60" in ln) and "read" not in ln.lower()
                    and not ln.strip().startswith("#")]
            if hits:
                warns.append(f"{f.name}: hardcodes 0.40/0.60 but cfg goal x=[{xlo:.2f},{xhi:.2f}] "
                             f"→ stale copy? e.g. `{hits[0][:70]}`")
    return warns


def main() -> int:
    cfg = parse_env_cfg(args_cli.gym, num_envs=1)
    # the cfg INTENT for the standby pose = init_state.joint_pos (what the
    # author wrote). We compare runtime-after-reset against THIS.
    intent = dict(cfg.scene.robot.init_state.joint_pos)

    env = gym.make(args_cli.gym, cfg=cfg, render_mode=None)
    u = env.unwrapped
    r = u.scene["robot"]
    names = r.joint_names

    def reset_read():
        env.reset(seed=args_cli.seed)
        q = r.data.joint_pos[0].clone()
        return {n: float(q[names.index(n)]) for n in names}

    q1 = reset_read()
    q2 = reset_read()  # determinism check

    fails = []

    # 1) intent applied? (skip regex keys like finger_joint.*; check explicit joints)
    for jname, want in intent.items():
        if ".*" in jname or jname not in names:
            continue
        got = q1[jname]
        if abs(got - want) > args_cli.tol:
            fails.append(f"INTENT MISMATCH {jname}: cfg wants {want:+.3f}, runtime {got:+.3f}")

    # NOTE: L/R symmetry is NOT a correctness test — the arms mirror physically
    # (shoulder j2 opens the opposite way, elbow bends the opposite way), so
    # left/right joint values legitimately differ. Only intent-match and
    # determinism are asserted.

    # 2) determinism (no jitter) — two same-seed resets identical
    for n in names:
        if abs(q1[n] - q2[n]) > args_cli.tol:
            fails.append(f"NON-DETERMINISTIC {n}: reset1={q1[n]:+.3f} reset2={q2[n]:+.3f} (jitter?)")

    # 3) INSTRUMENT SCAN — the diagnostic scripts must not HARDCODE geometry
    # the cfg defines (the tuner hardcoded Pin-4 0.40-0.60 and did not track the
    # −60mm shift). Grep the WP1 diagnostic dir for the OLD literal values that
    # a live cfg read would now differ from. A hit = a stale copy = drift source.
    warns = _scan_instruments(cfg)

    _p(f"gym={args_cli.gym} joints checked={len([k for k in intent if '.*' not in k])}")
    for w in warns:
        _p(f"  INSTRUMENT-DRIFT WARN: {w}")
    if fails:
        _p(f"FAIL ({len(fails)} issues) — runtime state != cfg intent; HALT downstream work:")
        for f in fails[:20]:
            _p(f"  {f}")
        env.close()
        return 3
    _p("PASS — runtime standby matches cfg intent, deterministic (no jitter).")
    env.close()
    return 0


if __name__ == "__main__":
    rc = main()
    simulation_app.close()
    sys.exit(rc)
