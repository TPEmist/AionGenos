"""Phase 4 D11 audit report — combine human labels with filter verdicts,
emit filter-vs-human agreement rate + per-stratum confusion matrix.

Reads:
  - manifest.json  (from audit_sample.py, has stratum info + filter verdict)
  - human_labels.csv (from audit_gui.py, has human label per sample)

Emits:
  - stdout table + summary metrics
  - `<out>_report.md` for the paper appendix
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("workspace/d11_audit/report.md"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    manifest_by_sid = {m["sample_id"]: m for m in manifest}

    labels: dict[int, str] = {}
    notes: dict[int, str] = {}
    with args.labels.open() as fp:
        for row in csv.DictReader(fp):
            try:
                sid = int(row["sample_id"])
                labels[sid] = row["human_label"]
                notes[sid] = row.get("human_notes", "")
            except (ValueError, KeyError):
                continue

    # Restrict to samples that both exist in manifest and have a human label
    scored = []
    for sid, human in labels.items():
        m = manifest_by_sid.get(sid)
        if m is None or not human:
            continue
        scored.append({"sid": sid, "human": human, "manifest": m})

    if not scored:
        print("No labeled samples yet.")
        return

    # Build confusion matrix: filter (keep/drop) × human (good/bad/borderline)
    confusion: Counter[tuple[str, str]] = Counter()
    per_stratum: dict[tuple[str, str], Counter[tuple[str, str]]] = defaultdict(Counter)
    for s in scored:
        m = s["manifest"]
        filt = m["filter_verdict"]
        human = s["human"]
        confusion[(filt, human)] += 1
        stratum = (m["outcome"], m["r1_state"])
        per_stratum[stratum][(filt, human)] += 1

    # Agreement rate (exclude borderline from denominator)
    n_clear = sum(v for (f, h), v in confusion.items() if h in ("clearly good", "clearly bad"))
    n_agree = (
        confusion.get(("keep", "clearly good"), 0)
        + confusion.get(("drop", "clearly bad"), 0)
    )
    agreement = n_agree / n_clear if n_clear else 0.0

    # Wilson CI on agreement
    z = 1.96
    p = agreement
    denom = 1 + z * z / max(1, n_clear)
    center = (p + z * z / (2 * max(1, n_clear))) / denom
    half = z * math.sqrt(p * (1 - p) / max(1, n_clear) + z * z / (4 * n_clear * n_clear)) / denom if n_clear else 0

    # Filter-side breakdown
    filter_keep = sum(v for (f, _), v in confusion.items() if f == "keep")
    filter_drop = sum(v for (f, _), v in confusion.items() if f == "drop")

    # Per-side false-positive / false-negative
    # FP = filter kept, human said clearly bad (filter should have dropped)
    # FN = filter dropped, human said clearly good (filter over-drop)
    fp = confusion.get(("keep", "clearly bad"), 0)
    fn = confusion.get(("drop", "clearly good"), 0)
    tp = confusion.get(("keep", "clearly good"), 0)
    tn = confusion.get(("drop", "clearly bad"), 0)

    # Emit report
    lines: list[str] = []
    lines.append("# D11 rationale filter — audit report")
    lines.append("")
    lines.append(f"Labeled samples: **{len(scored)} / {len(manifest)}**")
    lines.append(f"Clearly labeled (excluding borderline): **{n_clear}**")
    lines.append(f"Borderline: **{sum(1 for s in scored if s['human'] == 'borderline')}**")
    lines.append("")
    lines.append(f"## Agreement rate")
    lines.append("")
    lines.append(f"Filter-vs-human agreement (over clearly-labeled): "
                 f"**{agreement*100:.1f}%** (n={n_clear}, "
                 f"Wilson 95% CI [{(center-half)*100:.1f}%, {(center+half)*100:.1f}%])")
    lines.append("")

    lines.append("## Confusion matrix")
    lines.append("")
    lines.append("| filter \\ human | clearly good | clearly bad | borderline | row total |")
    lines.append("|---|---|---|---|---|")
    for f in ("keep", "drop"):
        row = [f"| **{f}**"]
        row_total = 0
        for h in ("clearly good", "clearly bad", "borderline"):
            c = confusion.get((f, h), 0)
            row_total += c
            row.append(str(c))
        row.append(f"**{row_total}**")
        lines.append(" | ".join(row) + " |")
    lines.append("")

    lines.append("## Errors")
    lines.append("")
    lines.append(f"- False positives (filter kept, human said bad): **{fp}**")
    lines.append(f"- False negatives (filter dropped, human said good): **{fn}**")
    lines.append(f"- True positives (both keep): **{tp}**")
    lines.append(f"- True negatives (both drop): **{tn}**")
    lines.append("")

    if agreement >= 0.85:
        lines.append("**Verdict: agreement ≥ 85% — filter is validated as method. "
                     "No LLM judge needed.**")
    elif agreement >= 0.70:
        lines.append("**Verdict: agreement 70-85% — filter usable but marginal. "
                     "Consider LLM-judge escalation on the FP+FN residual "
                     f"({fp+fn} samples).**")
    else:
        lines.append("**Verdict: agreement < 70% — filter fails validation. "
                     "Do NOT use as-is. Revisit rules or escalate to LLM judge.**")
    lines.append("")

    lines.append("## Per-stratum breakdown")
    lines.append("")
    for stratum_key in sorted(per_stratum):
        outcome, r1 = stratum_key
        c = per_stratum[stratum_key]
        n_here = sum(c.values())
        n_clear_here = sum(v for (f, h), v in c.items() if h != "borderline")
        n_agree_here = c.get(("keep", "clearly good"), 0) + c.get(("drop", "clearly bad"), 0)
        agree_here = n_agree_here / n_clear_here if n_clear_here else 0
        lines.append(f"### outcome={outcome}, r1_state={r1}")
        lines.append(f"  n={n_here}, clear={n_clear_here}, agreement={agree_here*100:.1f}%")
        lines.append(f"  keep×good: {c.get(('keep','clearly good'), 0)}, "
                     f"keep×bad: {c.get(('keep','clearly bad'), 0)}, "
                     f"drop×good: {c.get(('drop','clearly good'), 0)}, "
                     f"drop×bad: {c.get(('drop','clearly bad'), 0)}")
        lines.append("")

    # Notes on FP/FN cases
    fp_ids = [s["sid"] for s in scored
              if s["manifest"]["filter_verdict"] == "keep" and s["human"] == "clearly bad"]
    fn_ids = [s["sid"] for s in scored
              if s["manifest"]["filter_verdict"] == "drop" and s["human"] == "clearly good"]
    if fp_ids:
        lines.append("## FP cases (filter kept, human said bad)")
        for sid in fp_ids:
            m = manifest_by_sid[sid]
            lines.append(f"- sample_id={sid} ep={m['ep_id'][:8]} R{m['round_idx']} "
                         f"r1={m['r1_state']} r2={m['r2_state']}"
                         + (f" notes: {notes[sid]}" if notes.get(sid) else ""))
        lines.append("")
    if fn_ids:
        lines.append("## FN cases (filter dropped, human said good)")
        for sid in fn_ids:
            m = manifest_by_sid[sid]
            lines.append(f"- sample_id={sid} ep={m['ep_id'][:8]} R{m['round_idx']} "
                         f"r1={m['r1_state']} r2={m['r2_state']} "
                         f"reject_reason={m['reject_reason']}"
                         + (f" notes: {notes[sid]}" if notes.get(sid) else ""))
        lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines))

    # Also print to stdout
    print("\n".join(lines))
    print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()
