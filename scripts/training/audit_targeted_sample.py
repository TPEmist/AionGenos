"""Targeted re-audit manifest for Rule 1 v2 (Amendment 4).

Amendment 4 v2 (2026-07-07) reworked Rule 1's sentence classifier to
extract direction claims only from current-intent sentences. The random-
stratified v2 audit (60 samples, agreement 74.5%) can't tell us whether
the fix worked or over-corrected — its stratum defined by the old Rule 1
verdict is now obsolete. We need a targeted sample that hits the two
questions the general audit can't answer:

  1. Is the Rule-2 (GT contradict) drop precision high? — sample from
     Rule-2 drops (8 samples). If nearly all are clearly bad, Rule 2 is
     validated.
  2. Did the Rule 1 v2 fix over-correct? — sample from previously-dropped
     samples that flipped to keep after the fix (5 samples). If nearly
     all are clearly good, the fix works and didn't create false keeps.

Output: same JSON manifest format as audit_sample.py (so audit_gui.py can
re-use unchanged).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1_reasons_csv", type=Path, required=True,
                        help="Original filter reasons CSV (pre-Amendment-4 fix).")
    parser.add_argument("--v3_reasons_csv", type=Path, required=True,
                        help="Post-Amendment-4 filter reasons CSV.")
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n_rule2_drops", type=int, default=8)
    parser.add_argument("--n_flip_to_keep", type=int, default=5)
    parser.add_argument("--seed", type=int, default=43,
                        help="Different seed from initial audit (42) to prevent "
                             "resampling the same v1 audit rows.")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Load JSONL rows keyed by (ep_id, round_idx)
    jsonl_by_key = {}
    with args.jsonl.open() as fp:
        for i, line in enumerate(fp):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            key = (r.get("ep_id", ""), r.get("round_idx", 0))
            r["_jsonl_row"] = i
            jsonl_by_key[key] = r

    # Load previous audit manifest to know which samples were already audited
    # (we don't want to include them again — that would just re-test what we know)
    prev_audit_keys: set[tuple[str, int]] = set()
    prev_manifest_path = args.out.parent / "manifest.json"
    if prev_manifest_path.exists():
        for m in json.loads(prev_manifest_path.read_text()):
            prev_audit_keys.add((m["ep_id"], m["round_idx"]))

    # Load reasons CSVs
    def _load_reasons(p):
        d = {}
        with p.open() as f:
            for row in csv.DictReader(f):
                key = (row["ep_id"], int(row["round_idx"]))
                d[key] = row
        return d

    v1 = _load_reasons(args.v1_reasons_csv)
    v3 = _load_reasons(args.v3_reasons_csv)

    # Cell 1: v3 drops that are Rule-2 (GT contradict). These carry the
    # residual filter authority after Amendment 4.
    rule2_drop_pool = [
        key for key, row in v3.items()
        if row["keep"].lower() == "false"
        and row["rule_2_gt"] == "contradicts_gt"
        and key not in prev_audit_keys
    ]

    # Cell 2: v3 kept BUT v1 dropped — the samples the Amendment 4 fix
    # rescued. Test whether the rescue was warranted.
    flip_to_keep_pool = [
        key for key, row in v3.items()
        if row["keep"].lower() == "true"
        and v1.get(key, {}).get("keep", "").lower() == "false"
        and key not in prev_audit_keys
    ]

    print(f"Pool sizes (after excluding previously audited):")
    print(f"  Rule-2 drops:   {len(rule2_drop_pool)}")
    print(f"  Flip-to-keep:   {len(flip_to_keep_pool)}")

    take_r2 = min(args.n_rule2_drops, len(rule2_drop_pool))
    take_fk = min(args.n_flip_to_keep, len(flip_to_keep_pool))
    chosen_r2 = rng.sample(rule2_drop_pool, take_r2) if take_r2 else []
    chosen_fk = rng.sample(flip_to_keep_pool, take_fk) if take_fk else []

    manifest = []
    for i, key in enumerate(chosen_r2 + chosen_fk):
        src = jsonl_by_key.get(key)
        if src is None:
            continue
        v3row = v3[key]
        v1row = v1.get(key, {})
        manifest.append({
            "sample_id": i,
            "audit_batch": "amendment4_targeted",
            "audit_cell": "rule2_drop" if key in chosen_r2 else "flip_to_keep",
            "jsonl_row": src["_jsonl_row"],
            "ep_id": key[0],
            "round_idx": key[1],
            "outcome": v3row["outcome"],
            "kto_label": v3row["kto_label"],
            "v1_verdict": "keep" if v1row.get("keep", "").lower() == "true" else "drop",
            "v3_verdict": "keep" if v3row["keep"].lower() == "true" else "drop",
            "v3_r1_state": v3row["rule_1_direction"],
            "v3_r2_state": v3row["rule_2_gt"],
            "reject_reason": v3row["reject_reason"],
            # Blinded audit fields
            "image_path": src.get("image_path", ""),
            "state": src.get("state", {}),
            "parsed_left_pos": src.get("parsed_left_pos"),
            "target_response": src.get("target_response", ""),
            "filter_verdict": "keep" if v3row["keep"].lower() == "true" else "drop",
        })

    rng.shuffle(manifest)
    for i, m in enumerate(manifest):
        m["sample_id"] = i

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as fp:
        json.dump(manifest, fp, indent=2)

    print(f"Wrote {len(manifest)} samples → {args.out}")
    print(f"  {take_r2} Rule-2 drops + {take_fk} flip-to-keep")


if __name__ == "__main__":
    main()
