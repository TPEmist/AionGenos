"""L2 Amendment 1a: add per-arm dual labels to recap buffer from replay GT.

Adds left_reached / right_reached to each recap (from
per_arm_rescore.json). Keeps is_success (joint) untouched for reference.
Idempotent: re-running produces identical bytes.
"""
from __future__ import annotations
import json, glob
from pathlib import Path

rescore = json.load(open("workspace/l2_audit/per_arm_rescore.json"))
per_ep = rescore["per_episode"]

n_tagged = n_missing = 0
for f in glob.glob("workspace/recaps_l2/*/*.json"):
    r = json.load(open(f))
    epid = r["ep_id"]
    if epid not in per_ep:
        n_missing += 1
        continue
    pe = per_ep[epid]
    # add dual labels; keep joint is_success as-is
    r["left_reached"] = pe["left_reached"]
    r["right_reached"] = pe["right_reached"]
    r["_retag_amendment"] = "L2-1a"  # provenance marker
    Path(f).write_text(json.dumps(r, indent=2, sort_keys=True))
    n_tagged += 1

print(f"re-tagged {n_tagged} recaps; {n_missing} missing from re-score map")
# verify: how many now have a reached arm
tagged=[json.load(open(f)) for f in glob.glob("workspace/recaps_l2/*/*.json")]
any_reached=sum(1 for r in tagged if r.get("left_reached") or r.get("right_reached"))
joint=sum(1 for r in tagged if r.get("is_success"))
print(f"  joint is_success=True: {joint}")
print(f"  ≥1 arm reached (new dual-label): {any_reached}")
