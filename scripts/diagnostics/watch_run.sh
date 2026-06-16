#!/bin/bash
# Background watcher: every <interval>s checks how many episodes have landed
# in data/replays/<RUN_ID>/{success,failure}/. When the count crosses a new
# multiple of <step>, fire scripts/diagnostics/snapshot_run.py.
#
# Usage:  bash scripts/diagnostics/watch_run.sh <RUN_ID> <OUT_DIR> [STEP] [INTERVAL_S]
#
# Stops automatically once <max_eps> snapshots have been emitted, or when
# the parent process is killed (TERM).

set -euo pipefail

RUN_ID="${1:?usage: watch_run.sh <RUN_ID> <OUT_DIR> [step] [interval_s]}"
OUT_DIR="${2:?out dir required}"
STEP="${3:-10}"
INTERVAL="${4:-60}"
MAX_EPS=10000  # safety cap

mkdir -p "$OUT_DIR"
LAST_SNAP=0

while true; do
  # Need both `2>/dev/null` AND `|| true`: under `set -e`, `find` exits
  # non-zero when the parent dir doesn't exist (success/ may not be
  # created until the first success replay). Both forms of robustness
  # are required.
  s=$(find "data/replays/${RUN_ID}/success" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l || true)
  f=$(find "data/replays/${RUN_ID}/failure" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l || true)
  total=$((s + f))

  # snap whenever we cross a new multiple of STEP
  next_threshold=$(( (LAST_SNAP + 1) * STEP ))
  if [ "$total" -ge "$next_threshold" ]; then
    idx=$(( total / STEP ))
    python3 scripts/diagnostics/snapshot_run.py \
      --run "$RUN_ID" \
      --out_dir "$OUT_DIR" \
      --snapshot_idx "$idx"
    LAST_SNAP=$idx
  fi

  # bail if total >= MAX_EPS or parent gone
  if [ "$total" -ge "$MAX_EPS" ]; then
    break
  fi

  sleep "$INTERVAL"
done
