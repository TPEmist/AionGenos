"""Amendment 5 residual audit — sample the 66 Rule-1 drops that constitute
the v4 filter's entire actual drop surface (Rule 2 is being demoted to
flag; Rule 3 fires zero times; Rule 1 fixed is the only rule that
actually drops samples on the desirable side).

The v2 audit sampled from v1 (pre-fix) drops; the amendment-4 audit
sampled Rule-2 drops and Rule-1 flip-to-keeps. Neither audited the
final v4 drop set. 12-15 samples from the 66 residual R1 drops is the
minimum audit surface for the filter that will actually be applied.

Uniform blinded sample. No stratification because:
  (a) 66 samples is a small pool; further stratification would give
      <5 per cell and yield unstable per-stratum stats.
  (b) The audit answers a single primary question — precision of
      R1-fixed on the drop side — so a uniform sample suffices.

Seed=44 (different from earlier audits' 42 and 43).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v3_reasons_csv", type=Path, required=True)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n", type=int, default=15)
    parser.add_argument("--seed", type=int, default=44)
    args = parser.parse_args()

    rng = random.Random(args.seed)

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

    # Exclude keys already audited in previous rounds — the v4 filter's
    # residual drop set must be independently validated.
    seen_keys: set[tuple[str, int]] = set()
    for prev in ("manifest.json", "manifest_amendment4.json"):
        p = args.out.parent / prev
        if p.exists():
            for m in json.loads(p.read_text()):
                seen_keys.add((m["ep_id"], m["round_idx"]))

    with args.v3_reasons_csv.open() as f:
        rows = [row for row in csv.DictReader(f)]

    # Under Amendment 5's revised policy, the v4 filter drops a desirable
    # sample only when Rule 1 says inconsistent (Rule 2 is a flag not a
    # drop; Rule 3 didn't fire). These are the samples whose fate is
    # decided by the currently-fielded filter.
    pool = [
        row for row in rows
        if row["kto_label"] == "desirable"
        and row["rule_1_direction"] == "inconsistent"
        and (row["ep_id"], int(row["round_idx"])) not in seen_keys
    ]
    print(f"Residual R1-drop pool (desirable, unaudited): {len(pool)}")

    take = min(args.n, len(pool))
    chosen = rng.sample(pool, take) if take else []

    manifest = []
    for i, row in enumerate(chosen):
        key = (row["ep_id"], int(row["round_idx"]))
        src = jsonl_by_key.get(key)
        if src is None:
            continue
        manifest.append({
            "sample_id": i,
            "audit_batch": "amendment5_residual",
            "jsonl_row": src["_jsonl_row"],
            "ep_id": key[0],
            "round_idx": key[1],
            "outcome": row["outcome"],
            "kto_label": row["kto_label"],
            "v3_verdict": "drop",  # all in the pool are R1-drops
            "v3_r1_state": row["rule_1_direction"],
            "v3_r2_state": row["rule_2_gt"],
            "reject_reason": row["reject_reason"],
            "image_path": src.get("image_path", ""),
            "state": src.get("state", {}),
            "parsed_left_pos": src.get("parsed_left_pos"),
            "target_response": src.get("target_response", ""),
            "filter_verdict": "drop",
        })

    rng.shuffle(manifest)
    for i, m in enumerate(manifest):
        m["sample_id"] = i

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as fp:
        json.dump(manifest, fp, indent=2)

    print(f"Wrote {len(manifest)} samples → {args.out}")


if __name__ == "__main__":
    main()
