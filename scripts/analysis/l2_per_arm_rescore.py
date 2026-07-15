"""L2 per-arm re-score (L2 Amendment 1 §3 + buffer re-tag data source).

Full-population per-arm success table over the L2 run's 100 episodes,
scored from replay ground truth (best-in-episode ‖EE−pose_goal‖ < thr).
Emits:
  - per-arm desirable instance counts (feeds Step-2.verify pin)
  - per-episode (left_reached, right_reached) map → buffer re-tag source
Threshold = subgoal_success_threshold_m (0.05 m, registered).
"""
from __future__ import annotations
import json, glob, sys
from pathlib import Path

RUN = sys.argv[1] if len(sys.argv) > 1 else "a6e6c917"
THR = 0.05

def episode_files(run):
    return sorted(glob.glob(f"data/replays/{run}/success/*.json")
                  + glob.glob(f"data/replays/{run}/failure/*.json"))

rows = []
for f in episode_files(RUN):
    d = json.load(open(f))
    traj = d["trajectory"]
    dl = min(t["distances"]["dist_red"] for t in traj)
    dr = min(t["distances"]["dist_blue"] for t in traj)
    left_ok = dl < THR
    right_ok = dr < THR
    rows.append({
        "episode_id": d["episode_id"],
        "outcome_joint": d["outcome"],
        "best_dist_L": round(dl, 4),
        "best_dist_R": round(dr, 4),
        "left_reached": left_ok,
        "right_reached": right_ok,
    })

n = len(rows)
nL = sum(r["left_reached"] for r in rows)
nR = sum(r["right_reached"] for r in rows)
n_any = sum(r["left_reached"] or r["right_reached"] for r in rows)
n_both = sum(r["left_reached"] and r["right_reached"] for r in rows)
n_desirable_instances = nL + nR  # per-arm instances (left + right)

print(f"L2 run {RUN}: n={n} episodes, threshold={THR}m")
print(f"  left  reached goal: {nL}/{n} ({100*nL/n:.0f}%)")
print(f"  right reached goal: {nR}/{n} ({100*nR/n:.0f}%)")
print(f"  ≥1 arm (per-arm-any): {n_any}/{n}")
print(f"  both arms (best-in-ep): {n_both}/{n}")
print(f"  PER-ARM DESIRABLE INSTANCES (L+R): {n_desirable_instances}  ← Step-2.verify pin target")

out = {
    "run_id": RUN, "n_episodes": n, "threshold_m": THR,
    "left_reached": nL, "right_reached": nR,
    "per_arm_any": n_any, "both": n_both,
    "per_arm_desirable_instances": n_desirable_instances,
    "per_episode": {r["episode_id"]: {
        "left_reached": r["left_reached"], "right_reached": r["right_reached"],
        "best_dist_L": r["best_dist_L"], "best_dist_R": r["best_dist_R"],
        "outcome_joint": r["outcome_joint"],
    } for r in rows},
}
outp = Path("workspace/l2_audit/per_arm_rescore.json")
outp.write_text(json.dumps(out, indent=2))
print(f"\nWrote → {outp}")
