"""Amendment 5 §5.1 follow-up analysis — Rule 2 flags as diagnostic
for teacher's language-vs-action decoupling.

Rule 2 (GT geometric contradict) fires 45 times on the desirable side
of v4_kto_B. Amendment 5 demoted it from drop to flag. Now analyze:

  (a) Which axis's spatial claim contradicts GT (x / y / z distribution)?
  (b) Is the axis-error sign consistent (systematic bias) or random?
  (c) Do Rule-2-flagged samples correlate with the R1 ΔX bias measured
      in D6 / D10-ext (baseline: −23.5 → −15.8 cm decay)?

If (a) + (b) show systematic X-axis inversion in the language layer
while the action-layer ΔX is unbiased, this becomes a mechanistic
finding attachable to the paper's R1-bias probe: "the teacher's
natural-language X-axis semantics are systematically inverted; the
action head compensates internally; distilling only the action loses
the compensation and reproduces the language error."

Run after Amendment 5's residual audit lands (does not block training,
but should be in paper draft before submission).

Input: v4_kto_B.filtered.jsonl (with rule2_flag field), reasons CSV,
       and any of the D6/D10-ext replay dirs for R1-bias measurement.
Output: markdown report + plot(s).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


# Reuse the direction claim parser from the filter module.
_CUBE_CLAIM_PATTERNS = [
    (re.compile(r"cube\s+(?:is\s+)?(?:located\s+)?(?:to\s+the\s+)?left\s+of", re.IGNORECASE), "x", -1),
    (re.compile(r"cube\s+(?:is\s+)?(?:located\s+)?(?:to\s+the\s+)?right\s+of", re.IGNORECASE), "x", +1),
    (re.compile(r"cube\s+(?:is\s+)?(?:further\s+)?forward", re.IGNORECASE), "y", +1),
    (re.compile(r"cube\s+(?:is\s+)?(?:further\s+)?back", re.IGNORECASE), "y", -1),
    (re.compile(r"cube\s+(?:is\s+)?higher", re.IGNORECASE), "z", +1),
    (re.compile(r"cube\s+(?:is\s+)?lower", re.IGNORECASE), "z", -1),
]


def _extract_own_thought(target_response: str) -> str:
    lines = target_response.split("\n")
    b = None
    for i, ln in enumerate(lines):
        if ln.startswith("  (") and "] " in ln:
            b = i
    if b is None:
        return target_response
    return "\n".join(lines[b + 1:]).lstrip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasons_csv", type=Path, required=True,
                        help="e.g. /tmp/v4_kto_B.filtered_v3.jsonl.reasons.csv")
    parser.add_argument("--jsonl", type=Path, required=True,
                        help="Original v4_kto_B.jsonl.")
    parser.add_argument("--out", type=Path,
                        default=Path("workspace/d11_audit/rule2_flag_analysis.md"))
    args = parser.parse_args()

    # Load reasons + JSONL together, filter to R2-contradicts + desirable.
    with args.reasons_csv.open() as f:
        reasons = {(r["ep_id"], int(r["round_idx"])): r for r in csv.DictReader(f)}

    flagged_samples = []
    with args.jsonl.open() as f:
        for line in f:
            r = json.loads(line)
            key = (r["ep_id"], r["round_idx"])
            row = reasons.get(key)
            if row is None:
                continue
            if row["rule_2_gt"] != "contradicts_gt":
                continue
            if row["kto_label"] != "desirable":
                continue
            r["_r2_debug"] = row["r2_debug"]
            flagged_samples.append(r)

    print(f"Loaded {len(flagged_samples)} R2-contradict + desirable samples")
    if not flagged_samples:
        print("Nothing to analyze."); return

    # Per-axis contradiction distribution
    axis_counter: Counter = Counter()
    sign_by_axis: dict[str, Counter] = {"x": Counter(), "y": Counter(), "z": Counter()}
    for s in flagged_samples:
        try:
            dbg = json.loads(s["_r2_debug"])
        except (json.JSONDecodeError, TypeError):
            continue
        axis = dbg.get("axis")
        if axis is None:
            continue
        axis_counter[axis] += 1
        cs = dbg.get("claim_sign")
        gd = dbg.get("gt_delta")
        if cs is not None and gd is not None:
            gs = 1 if gd > 0 else -1
            # For each flagged sample, record: rationale claimed +1 / GT was -1 (or vice versa)
            sign_by_axis[axis][(cs, gs)] += 1

    # Report
    lines = ["# Rule-2 flag analysis — teacher language-vs-action decoupling"]
    lines.append("")
    lines.append(f"Total desirable samples with rule2_flag: **{len(flagged_samples)}**")
    lines.append("")

    lines.append("## Per-axis GT contradiction distribution")
    lines.append("")
    lines.append("| axis | count | fraction |")
    lines.append("|---|---|---|")
    for a in ("x", "y", "z"):
        n = axis_counter.get(a, 0)
        pct = 100 * n / len(flagged_samples) if flagged_samples else 0
        lines.append(f"| {a} | {n} | {pct:.1f}% |")
    lines.append("")

    lines.append("## Sign inversion pattern per axis")
    lines.append("")
    lines.append("(claim_sign vs gt_sign)")
    for a in ("x", "y", "z"):
        c = sign_by_axis[a]
        if not c:
            continue
        lines.append(f"### axis={a}")
        lines.append("")
        lines.append("| claimed | GT actual | count |")
        lines.append("|---|---|---|")
        for (cs, gs), n in c.most_common():
            lines.append(f"| {cs:+d} | {gs:+d} | {n} |")
        lines.append("")

    # Diagnostic-level interpretation
    lines.append("## Interpretation heuristics")
    lines.append("")
    dominant = axis_counter.most_common(1)
    if dominant:
        top_axis, top_n = dominant[0]
        top_frac = top_n / len(flagged_samples)
        if top_frac > 0.5:
            lines.append(f"- Rule-2 flags concentrate on axis {top_axis} "
                         f"({top_frac*100:.0f}% of flagged samples). If a single "
                         f"sign-inversion pattern dominates, this is direct evidence "
                         f"for **systematic axis-specific language-layer bias**.")
        else:
            lines.append(f"- Rule-2 flags are distributed across axes "
                         f"(dominant axis: {top_axis} at {top_frac*100:.0f}%). "
                         f"This is more consistent with **random rationale noise** than "
                         f"systematic linguistic bias.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nReport → {args.out}")


if __name__ == "__main__":
    main()
