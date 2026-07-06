"""Phase 4 D11 audit — draw a stratified blinded sample from the filter's
per-sample verdict CSV.

Reads a `<jsonl>.reasons.csv` produced by
`filter_rationale_deterministic.py`, plus the original JSONL for the
target_response text and image_path. Emits a shuffled manifest of
50-100 samples (default 60) stratified across:

  - outcome (success vs failure) × 2
  - r1_state (consistent vs inconsistent) × 2
  - (implicitly, arm labels are blinded — the reasons.csv does not
    carry an arm identifier and this manifest strips run_id from
    display purposes at audit time)

Vacuous rationales are dropped from the audit pool — the filter's
Rule-3 decision is unambiguous and doesn't need human validation.

Output: JSON manifest
    [
      {"sample_id": int, "jsonl_row": int,
       "ep_id": str, "round_idx": int,
       "outcome": str, "kto_label": str,
       "r1_state": str, "r2_state": str,
       "filter_verdict": "keep" | "drop",
       "reject_reason": str}
    ]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasons_csv", type=Path, required=True,
                        help="e.g. /tmp/v4_kto_B.filtered.jsonl.reasons.csv")
    parser.add_argument("--jsonl", type=Path, required=True,
                        help="Original JSONL that produced the reasons CSV.")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output manifest JSON path.")
    parser.add_argument("--n_per_cell", type=int, default=15,
                        help="Target samples per stratum cell (4 cells total = ~60 samples).")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for stratified sampling. Fixed by "
                             "convention so audit is reproducible.")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Load JSONL rows keyed by (ep_id, round_idx) for later lookup.
    jsonl_by_key: dict[tuple[str, int], dict] = {}
    with args.jsonl.open() as fp:
        for i, line in enumerate(fp):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            key = (r.get("ep_id", ""), r.get("round_idx", 0))
            r["_jsonl_row"] = i
            jsonl_by_key[key] = r

    # Load reasons CSV
    reasons: list[dict[str, Any]] = []
    with args.reasons_csv.open() as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            reasons.append(row)

    # Filter out vacuous rows — Rule 3 is unambiguous.
    reasons = [r for r in reasons if r["rule_3_vacuity"] != "vacuous_no_spatial_token"]

    # Stratify: outcome × r1_state
    strata: dict[tuple[str, str], list] = defaultdict(list)
    for row in reasons:
        outcome = row["outcome"]
        r1 = row["rule_1_direction"]
        if outcome not in ("success", "failure"):
            continue
        if r1 not in ("consistent", "inconsistent"):
            continue  # skip no_claim_parseable
        strata[(outcome, r1)].append(row)

    # Sample from each stratum
    manifest: list[dict] = []
    sample_id = 0
    for cell_key in [("success", "consistent"),
                     ("success", "inconsistent"),
                     ("failure", "consistent"),
                     ("failure", "inconsistent")]:
        pool = strata.get(cell_key, [])
        take = min(len(pool), args.n_per_cell)
        chosen = rng.sample(pool, take) if take else []
        for row in chosen:
            key = (row["ep_id"], int(row["round_idx"]))
            src = jsonl_by_key.get(key)
            if src is None:
                continue
            manifest.append({
                "sample_id": sample_id,
                "jsonl_row": src["_jsonl_row"],
                "ep_id": row["ep_id"],
                "round_idx": int(row["round_idx"]),
                "outcome": row["outcome"],
                "kto_label": row["kto_label"],
                "r1_state": row["rule_1_direction"],
                "r2_state": row["rule_2_gt"],
                "filter_verdict": "keep" if row["keep"].lower() == "true" else "drop",
                "reject_reason": row["reject_reason"],
                # Data needed for the audit UI (blinded — no run_id or arm hint)
                "image_path": src.get("image_path", ""),
                "state": src.get("state", {}),
                "parsed_left_pos": src.get("parsed_left_pos"),
                "target_response": src.get("target_response", ""),
            })
            sample_id += 1

    # Shuffle so auditor doesn't see stratum-block ordering
    rng.shuffle(manifest)
    # Reassign sample_id in shuffled order
    for i, m in enumerate(manifest):
        m["sample_id"] = i

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as fp:
        json.dump(manifest, fp, indent=2)

    print(f"Wrote {len(manifest)} samples → {args.out}")
    print(f"Seed: {args.seed} (pre-registered — do not change without amendment)")
    print()
    print("Stratum counts in manifest:")
    from collections import Counter
    strat_counts = Counter((m["outcome"], m["r1_state"]) for m in manifest)
    for k, v in sorted(strat_counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
