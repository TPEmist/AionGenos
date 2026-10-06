"""WP1-③a pilot report (wp3a_pilot_plan.md step (c) outputs).

Inputs: the push summary JSON (logs/push_smoke_<run>.json), replays
(data/replays/<run>/), recap buffer root. Outputs (stdout + JSON):
  1. success count / SR (MVC floor reading) → mechanical rung decision (< 5 → next rung)
  2. contact summary: episodes / rounds where the cube actually moved
     (contact.first_cube_move not None), anatomy of first contact, TCP→cube min
  3. recap samples (Q7): count, word lengths, 3 verbatim lessons (first/mid/last)
  4. r-estimator variance: every exploratory (c, s) candidate from push_r_inputs,
     with r, permutation band, and bootstrap σ(r) (B resamples of episodes).
Pure CPU. Usage:
  python3 scripts/analysis/wp3a_pilot_report.py <run_id> --recap_root workspace/recaps_push_pilot_rung1
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p2_r_tracker import spearman  # noqa: E402
from push_r_inputs import load_push_r_inputs, r_for_candidates  # noqa: E402
import push_r_inputs as pri  # noqa: E402

RUNG_THRESHOLD = 5  # wp3a_pilot_plan.md: successes < 5 → next rung (pre-registered)
NEXT_RUNG = {1: "1b", "1b": 2, 2: 3, 3: "STOP → escalate to PI"}


def contact_summary(eps: list[dict]) -> dict:
    ep_touched, anat, tip_min, rounds_moved, rounds_total, guard = 0, Counter(), [], 0, 0, 0
    for e in eps:
        touched = False
        best = 1e9
        for r in e.get("round_meta", []):
            rounds_total += 1
            c = r.get("contact") or {}
            fm = c.get("first_cube_move")
            if c.get("tcp_to_cube_min_cm") is not None:
                best = min(best, c["tcp_to_cube_min_cm"])
            if fm:
                rounds_moved += 1
                anat[fm["anatomy"]] += 1
                touched = True
            tg = r.get("table_guard") or {}
            if tg.get("target_clamp"):
                guard += 1
        ep_touched += touched
        if best < 1e9:
            tip_min.append(best)
    return {"episodes": len(eps), "episodes_cube_moved": ep_touched,
            "rounds_cube_moved": rounds_moved, "rounds_total": rounds_total,
            "first_contact_anatomy": dict(anat),
            "tcp_to_cube_min_cm_per_ep": {"median": st.median(tip_min) if tip_min else None,
                                          "min": min(tip_min) if tip_min else None,
                                          "eps_within_1cm": sum(t <= 1.0 for t in tip_min)},
            "scene_guard_target_clamps": guard}


def recap_samples(root: Path, run_id: str) -> dict:
    recs = sorted((root / run_id).glob("*.json"), key=lambda p: p.stat().st_mtime)
    lessons = []
    for p in recs:
        d = json.loads(p.read_text())
        lessons.append((d.get("ep_id"), d.get("text_lesson") or ""))
    words = [len(t.split()) for _, t in lessons]
    pick = [lessons[i] for i in sorted({0, len(lessons) // 2, len(lessons) - 1}) if lessons]
    return {"n_recaps": len(lessons), "words_median": st.median(words) if words else None,
            "n_empty": sum(w == 0 for w in words), "samples": pick}


def bootstrap_sigma(eps, c_fn, s_fn, B: int = 1000, seed: int = 11) -> float | None:
    rng = random.Random(seed)
    rs = []
    for _ in range(B):
        bs = [eps[rng.randrange(len(eps))] for _ in eps]
        c = [c_fn(e) for e in bs]
        s = [s_fn(e) for e in bs]
        if len(set(c)) > 1 and len(set(s)) > 1:
            rs.append(spearman(c, s))
    return st.pstdev(rs) if len(rs) > 1 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("--recap_root", type=Path, default=Path("workspace/recaps_push_pilot_rung1"))
    ap.add_argument("--rung", default="1")
    args = ap.parse_args()
    summ = json.loads(Path(f"logs/push_smoke_{args.run_id}.json").read_text())
    eps = summ["episodes"]
    n_succ = sum(e["outcome"] == "success" for e in eps)
    rung = int(args.rung) if args.rung.isdigit() else args.rung
    out = {"run_id": args.run_id, "n_episodes": len(eps), "successes": n_succ,
           "outcomes": dict(Counter(e["outcome"] for e in eps)),
           "rung_decision": (f"successes {n_succ} < {RUNG_THRESHOLD} → rung {NEXT_RUNG[rung]}"
                             if n_succ < RUNG_THRESHOLD else f"successes {n_succ} ≥ {RUNG_THRESHOLD} → (d) at rung {rung}"),
           "contact": contact_summary(eps),
           "recaps": recap_samples(args.recap_root, args.run_id)}
    r_eps = load_push_r_inputs(Path(f"data/replays/{args.run_id}"), label="pilot")
    cands = r_for_candidates(r_eps)
    sig = {}
    for cn, c_fn in pri.C_CANDIDATES.items():
        for sn, s_fn in pri.S_CANDIDATES.items():
            sig[f"{cn}|{sn}"] = bootstrap_sigma(r_eps, c_fn, s_fn)
    out["r_estimator"] = {"n_eps": len(r_eps), "candidates": cands, "bootstrap_sigma_r": sig,
                          "note": "exploratory grid — c/s not PI-pinned; report all (forking paths)"}
    Path(f"logs/pilot_report_{args.run_id}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
