"""WP1-③a pilot report (wp3a_pilot_plan.md step (c) outputs).

Inputs: the push summary JSON (logs/push_smoke_<run>.json), replays
(data/replays/<run>/), recap buffer root. Outputs (stdout + JSON):
  1. success count / SR (MVC floor reading) → mechanical rung decision (< 5 → next rung)
  2. contact summary: episodes / rounds where the cube actually moved
     (contact.first_cube_move not None), anatomy of first contact, TCP→cube min
  3. recap samples (Q7): count, word lengths, 3 verbatim lessons (first/mid/last)
  4. r-estimator variance: every exploratory (c, s) candidate from push_r_inputs,
     with r, permutation band, and bootstrap σ(r) (B resamples of episodes).
  5. recap confabulation (PI 2026-10-06, MVC 4th instance): lessons asserting
     cube motion in episodes where the GT contact report says the cube NEVER
     moved (no round with contact.first_cube_move). Two rates:
       keyword   — any of CONFAB_TERMS anywhere (the PI's literal list; also
                   catches counterfactuals like "to move it toward the zone");
       assertive — a SENTENCE with a motion term that is neither modal/
                   counterfactual ("should", "would", "to move", …) nor negated
                   ("remained", "not", "failed to", …). Heuristic, read the examples.
Pure CPU. Usage:
  python3 scripts/analysis/wp3a_pilot_report.py <run_id> --recap_root workspace/recaps_push_pilot_rung1
  python3 scripts/analysis/wp3a_pilot_report.py <run_id> --confab_only   (prints 5 only, writes nothing)
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p2_r_tracker import spearman  # noqa: E402
from push_r_inputs import load_push_r_inputs, r_for_candidates  # noqa: E402
import push_r_inputs as pri  # noqa: E402

RUNG_THRESHOLD = 5  # wp3a_pilot_plan.md: successes < 5 → next rung (pre-registered)
# rung-2 → rung-3 needs PI consent + Ledger entry (PI 2026-10-07; wp3a_pilot_plan.md)
NEXT_RUNG = {1: "1b", "1b": 2, 2: "STOP → PI re-deliberation (rung-3 = last resort, needs PI consent + Ledger)",
             3: "STOP → escalate to PI"}


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


CONFAB_TERMS = ("pushed", "moved", "shifted", "drifted", "away from the goal", "toward")
_CONFAB_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in CONFAB_TERMS) + r")", re.IGNORECASE)
_MODAL_RE = re.compile(r"\b(should|would|could|might|must|need|needs|ensure|ensuring|if|will|"
                       r"to (move|push|drive|shift|slide)|in order to|so that)\b", re.IGNORECASE)
_NEGATED_RE = re.compile(r"\b(not|never|no|without|remained|remain|stationary|failed to|"
                         r"fail to|did not|didn't|unmoved|motionless)\b", re.IGNORECASE)


def episode_cube_moved(ep: dict) -> bool:
    """GT (offline): did the contact report see the cube start moving in ANY round?"""
    return any((r.get("contact") or {}).get("first_cube_move") for r in ep.get("round_meta", []))


def confab_flags(lesson: str) -> dict:
    """keyword: any CONFAB_TERM. assertive: some sentence has a term and is
    neither modal/counterfactual nor negated."""
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", lesson) if x.strip()]
    assertive = [x for x in sents
                 if _CONFAB_RE.search(x) and not _MODAL_RE.search(x) and not _NEGATED_RE.search(x)]
    return {"keyword": bool(_CONFAB_RE.search(lesson)), "assertive": bool(assertive),
            "assertive_sentences": assertive}


def confabulation_check(eps: list[dict], lessons: dict[str, str], n_examples: int = 3) -> dict:
    """Rates over recaps of episodes whose cube NEVER moved (GT contact report)."""
    still = {e["ep_id"] for e in eps if not episode_cube_moved(e)}
    rows = [(ep_id, t, confab_flags(t)) for ep_id, t in lessons.items() if ep_id in still and t]
    n = len(rows)
    kw = [r for r in rows if r[2]["keyword"]]
    asr = [r for r in rows if r[2]["assertive"]]
    return {"n_recaps": len(lessons), "n_recaps_cube_never_moved": n,
            "terms": list(CONFAB_TERMS),
            "keyword_flagged": len(kw), "keyword_rate": (len(kw) / n) if n else None,
            "assertive_flagged": len(asr), "assertive_rate": (len(asr) / n) if n else None,
            "assertive_examples": [{"ep_id": i, "sentences": f["assertive_sentences"]}
                                   for i, _, f in asr[:n_examples]],
            "keyword_only_examples": [{"ep_id": i, "lesson": t} for i, t, f in kw
                                      if not f["assertive"]][:n_examples]}


def load_lessons(root: Path, run_id: str) -> dict[str, str]:
    return {d.get("ep_id"): d.get("text_lesson") or ""
            for d in (json.loads(p.read_text()) for p in sorted((root / run_id).glob("*.json")))}


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
    ap.add_argument("--confab_only", action="store_true", help="print the confabulation check only")
    args = ap.parse_args()
    summ = json.loads(Path(f"logs/push_smoke_{args.run_id}.json").read_text())
    eps = summ["episodes"]
    confab = confabulation_check(eps, load_lessons(args.recap_root, args.run_id))
    if args.confab_only:
        print(json.dumps(confab, indent=1, ensure_ascii=False))
        return 0
    n_succ = sum(e["outcome"] == "success" for e in eps)
    rung = int(args.rung) if args.rung.isdigit() else args.rung
    out = {"run_id": args.run_id, "n_episodes": len(eps), "successes": n_succ,
           "outcomes": dict(Counter(e["outcome"] for e in eps)),
           "rung_decision": (f"successes {n_succ} < {RUNG_THRESHOLD} → rung {NEXT_RUNG[rung]}"
                             if n_succ < RUNG_THRESHOLD else f"successes {n_succ} ≥ {RUNG_THRESHOLD} → (d) at rung {rung}"),
           "contact": contact_summary(eps),
           "recaps": recap_samples(args.recap_root, args.run_id),
           "recap_confabulation": confab}
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
