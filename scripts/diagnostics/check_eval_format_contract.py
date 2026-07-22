#!/usr/bin/env python3
"""Format-contract gate — assert the EVAL parser accepts the TRAINING target.

This is the permanent, prospective fix for a bug family that has bitten the
project four times (B_main prose target; D_gist variant mis-selection; driver
Step-9 missing --eval_template_variant; L2 eval parsing both arms for a
single-arm-trained model). Every prior instance was caught reactively — by
crashing at episode 1 (or mid-run). The common structure is always the same:
**the eval-side parser and the training-side target format drift apart.**

The gate: take a few VERBATIM training-target rows from the SFT JSONL and feed
each through the EXACT eval parser configuration (control mode + variant +
scored_arm) the upcoming eval will use. If the student learned to emit a shape
the eval parser cannot read, this fails HERE — at dry-run, before the simulator
boots — instead of at episode 1.

Exit codes: 0 = contract holds; 3 = mismatch (HALT the eval).

Usage:
  check_eval_format_contract.py --sft-jsonl <path> --level <N> \
      [--scored-arm left|right] [--variant rationale] [--n 3]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Repo root on path so this runs from any cwd (the driver invokes it via ssh /
# absolute paths). scripts/diagnostics/ → repo root is two parents up.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import the SAME parser the eval uses — no reimplementation, or the gate
# would test a copy instead of the real contract.
from aiongenos.config import LEVEL_CONFIGS, ControlMode
from aiongenos.vlm.parser import parse_stage1


def _parser_flags(level):
    """Mirror run_stage1's control-mode → parser-flag derivation exactly."""
    cm = level.control_mode
    has_rpy = cm in (ControlMode.POSITION_RPY_2DOF, ControlMode.POSITION_RPY_GRIPPER)
    rpy_2dof = cm == ControlMode.POSITION_RPY_2DOF
    has_gripper = cm == ControlMode.POSITION_RPY_GRIPPER
    return has_rpy, has_gripper, rpy_2dof


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sft-jsonl", required=True, help="training SFT jsonl (source of verbatim targets)")
    ap.add_argument("--level", type=int, required=True)
    ap.add_argument("--scored-arm", choices=("left", "right"), default=None,
                    help="L2 Amendment 3 per-arm eval: parse only this arm.")
    ap.add_argument("--variant", default=None,
                    help="eval_template_variant (informational; the parser contract "
                         "depends on control_mode + scored_arm, not the variant text).")
    ap.add_argument("--n", type=int, default=3, help="number of target rows to check.")
    args = ap.parse_args()

    if args.level not in LEVEL_CONFIGS:
        print(f"  ✗ unknown level {args.level}", file=sys.stderr)
        return 3
    level = LEVEL_CONFIGS[args.level]
    has_rpy, has_gripper, rpy_2dof = _parser_flags(level)

    p = Path(args.sft_jsonl)
    if not p.exists():
        print(f"  ✗ SFT jsonl not found: {p}", file=sys.stderr)
        return 3

    rows = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if len(rows) >= args.n:
                break
    if not rows:
        print(f"  ✗ no rows in {p}", file=sys.stderr)
        return 3

    print(f"  format-contract: level={args.level} ({level.control_mode.value}) "
          f"scored_arm={args.scored_arm} variant={args.variant} — "
          f"feeding {len(rows)} verbatim training targets through the eval parser")

    fails = 0
    for i, row in enumerate(rows):
        target = row.get("target_response")
        if not target:
            print(f"    row {i}: ✗ no target_response field")
            fails += 1
            continue
        # A training target has no STOP-less trailing? The SFT target always
        # ends with a STOP line (single- and dual-arm alike), which the parser
        # requires — so a clean parse proves the full contract.
        try:
            parse_stage1(
                target,
                has_rpy=has_rpy,
                has_gripper=has_gripper,
                rpy_2dof=rpy_2dof,
                scored_arm=args.scored_arm,
            )
            arm = row.get("scored_arm", "?")
            print(f"    row {i} (scored_arm={arm}): ✓ parses")
        except Exception as e:
            print(f"    row {i}: ✗ EVAL PARSER REJECTS TRAINING TARGET → {e}")
            print(f"        target[:200]={target[:200]!r}")
            fails += 1

    if fails:
        print(f"  ✗ format-contract FAILED ({fails}/{len(rows)}) — HALT before eval.")
        print("    The student was trained to emit a shape the eval parser cannot read.")
        print("    Fix the eval parser/template to match the training target — do NOT")
        print("    change the training data to satisfy a broken eval contract.")
        return 3
    print(f"  ✓ format-contract holds ({len(rows)}/{len(rows)}) — eval parser accepts training targets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
