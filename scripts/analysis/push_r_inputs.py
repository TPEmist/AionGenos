"""WP1-③a push — extract p2_r_tracker inputs (c, s) from push replays ALONE.

Raw material (written by push_collect via push_memory.write_push_episode):
  replay.init_left_ee_pose            EE at reset, base frame (m)
  replay.init_cube_pose["yellow"]     cube at reset, base frame (m)
  replay.metadata["goal_pose_b"]      goal (static per ep), base frame (m)
  replay.metadata["rounds_state"][0]  round-1 eef_target_m + pre-action ee/cube
  replay.vlm_interactions[0]          fallback: parsed_left_pos (int grid) →
                                      metric via metadata["workspace_bounds"]

Raw components exposed per episode (all metric, base frame, XY):
  c_raw = round-1 commanded EEF displacement = target_xy − init_ee_xy
  u     = unit(goal_xy − cube_xy)      (push direction)
  plus cube_xy, goal_xy, cube→goal (dx, dy, dist, angle), ee→cube (dx, dy)

The SCALAR c and s for r are NOT pinned here.
TODO(PI-pin): choose ONE c projection and ONE s feature before gen-0 FREEZE
(wp3a_pilot_plan.md step (e)); the candidates below are exploratory only, and
running all of them on the pilot is a forking-paths search — report all.

Run:
  python3 scripts/analysis/push_r_inputs.py data/replays/<run_id> [--label pilot]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from p2_r_tracker import r_for_generation  # noqa: E402
from aiongenos.vlm.scalar_guard import int_to_metric  # noqa: E402  (fallback path; pure, stdlib)


@dataclass(frozen=True)
class PushRInputs:
    ep_id: str
    run_id: str
    env_seed: Optional[int]
    outcome: str
    label: Optional[str]
    init_ee_xy: tuple[float, float]
    cube_xy: tuple[float, float]
    goal_xy: tuple[float, float]
    r1_target_xy: tuple[float, float]
    c_raw: tuple[float, float]          # target − init EE (m)
    push_dir: tuple[float, float]       # unit(goal − cube)
    cube_to_goal: tuple[float, float]   # goal − cube (m)
    ee_to_cube: tuple[float, float]     # cube − init EE (m)


def _r1_target_xy(ep: dict) -> Optional[tuple[float, float]]:
    rs = (ep.get("metadata") or {}).get("rounds_state") or []
    if rs and rs[0].get("eef_target_m"):
        t = rs[0]["eef_target_m"]
        return float(t[0]), float(t[1])
    vis = [v for v in ep.get("vlm_interactions", []) if v.get("stage") == "stage1_eef"]
    wb = (ep.get("metadata") or {}).get("workspace_bounds")
    if vis and wb:
        x, y, _ = vis[0]["parsed_left_pos"]
        # bounds read from the replay itself, not hard-coded
        return int_to_metric(x, tuple(wb["x"])), int_to_metric(y, tuple(wb["y"]))
    return None


def r_inputs_from_replay(ep: dict) -> Optional[PushRInputs]:
    """(c, s) raw components for one replay dict; None if the episode lacks
    the push init fields (pre-memory replays) or a round-1 action."""
    md = ep.get("metadata") or {}
    ee, cube = ep.get("init_left_ee_pose"), (ep.get("init_cube_pose") or {}).get("yellow")
    goal, tgt = md.get("goal_pose_b"), _r1_target_xy(ep)
    if not (ee and cube and goal and tgt):
        return None
    cg = (goal[0] - cube[0], goal[1] - cube[1])
    n = math.hypot(*cg) or 1.0
    return PushRInputs(
        ep_id=ep["episode_id"], run_id=ep["run_id"], env_seed=ep.get("env_seed"),
        outcome=ep["outcome"], label=md.get("label"),
        init_ee_xy=(ee[0], ee[1]), cube_xy=(cube[0], cube[1]), goal_xy=(goal[0], goal[1]),
        r1_target_xy=tgt, c_raw=(tgt[0] - ee[0], tgt[1] - ee[1]),
        push_dir=(cg[0] / n, cg[1] / n), cube_to_goal=cg,
        ee_to_cube=(cube[0] - ee[0], cube[1] - ee[1]),
    )


def load_push_r_inputs(run_dir: Path, label: Optional[str] = "pilot") -> list[PushRInputs]:
    out = []
    for f in sorted(Path(run_dir).glob("*/*.json")):
        ep = json.loads(f.read_text())
        ri = r_inputs_from_replay(ep)
        if ri is not None and (label is None or ri.label == label):
            out.append(ri)
    return out


# ── EXPLORATORY candidates — TODO(PI-pin): replace by the pinned pair ──
C_CANDIDATES: dict[str, Callable[[PushRInputs], float]] = {
    "c_along_push_dir": lambda e: e.c_raw[0] * e.push_dir[0] + e.c_raw[1] * e.push_dir[1],
    "c_perp_push_dir": lambda e: -e.c_raw[0] * e.push_dir[1] + e.c_raw[1] * e.push_dir[0],
    "c_dx": lambda e: e.c_raw[0],
    "c_dy": lambda e: e.c_raw[1],
}
S_CANDIDATES: dict[str, Callable[[PushRInputs], float]] = {
    "s_push_angle": lambda e: math.atan2(e.cube_to_goal[1], e.cube_to_goal[0]),
    "s_push_dist": lambda e: math.hypot(*e.cube_to_goal),
    "s_cube_y": lambda e: e.cube_xy[1],
    "s_goal_y": lambda e: e.goal_xy[1],
}


def r_for_candidates(eps: list[PushRInputs], n_perm: int = 2000) -> dict[str, dict]:
    """p2_r_tracker.r_for_generation for every (c, s) candidate pair."""
    res = {}
    for cn, cf in C_CANDIDATES.items():
        c = [cf(e) for e in eps]
        for sn, sf in S_CANDIDATES.items():
            res[f"{cn}|{sn}"] = r_for_generation(c, [sf(e) for e in eps], n_perm=n_perm)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--label", default="pilot", help="'' = all labels")
    ap.add_argument("--n_perm", type=int, default=2000)
    ap.add_argument("--dump", action="store_true", help="print raw per-episode components")
    a = ap.parse_args()
    eps = load_push_r_inputs(a.run_dir, a.label or None)
    print(f"[push_r_inputs] {len(eps)} episodes with push init fields in {a.run_dir}")
    if a.dump:
        for e in eps:
            print(json.dumps(asdict(e)))
    if len(eps) < 3:
        print("[push_r_inputs] too few episodes for r")
        return 1
    for k, v in r_for_candidates(eps, a.n_perm).items():
        print(f"  {k:36s} r={v['r']:+.3f} band=({v['band_lo']:+.3f},{v['band_hi']:+.3f}) "
              f"above={v['above_band']} n={v['n']}")
    print("  NOTE: exploratory grid — the confirmatory (c, s) pair is PI-pinned (TODO).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
