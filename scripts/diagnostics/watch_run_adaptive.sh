#!/bin/bash
# Adaptive watcher — Phase 4 R4.
#
# L1 observation: every <interval>s, count success/failure in
#   data/replays/<RUN_ID>/{success,failure}/*.json, compute sliding 10-ep SR,
#   emit snapshot every <step> eps (uses scripts/diagnostics/snapshot_run.py).
#
# L2 adaptive mode flag (success-only retrieval during SR dip):
#   - if last sliding-10 SR is <5% for 2 consecutive windows,
#     write "success_only" to <MODE_FLAG_PATH>. The collect process reads
#     it before each retrieve() and filters to success ep only.
#   - when sliding-10 SR recovers to >=10%, write "mixed" to clear the flag.
#
# L3 stall: if sliding-10 SR <5% for 3 consecutive windows, touch
#   <STALL_FLAG_PATH> for human inspection. The watcher does NOT pause
#   the collect process — that is a manual decision.
#
# Usage:
#   bash watch_run_adaptive.sh <RUN_ID> <OUT_DIR> <MODE_FLAG_PATH> [STEP] [INTERVAL_S]

set -euo pipefail

RUN_ID="${1:?usage: watch_run_adaptive.sh <RUN_ID> <OUT_DIR> <MODE_FLAG_PATH> [step] [interval_s]}"
OUT_DIR="${2:?out dir required}"
MODE_FLAG_PATH="${3:?mode flag path required}"
STEP="${4:-10}"
INTERVAL="${5:-60}"
MAX_EPS=10000
STALL_FLAG_PATH="${OUT_DIR}/STALLED.flag"

mkdir -p "$OUT_DIR"
mkdir -p "$(dirname "$MODE_FLAG_PATH")"

LAST_SNAP=0
FIRST_FIRED=0
# Sliding-SR state across watcher invocations
WINDOW_SIZE=10
DIP_THRESHOLD=5     # SR below this counts as a dip
RECOVERY_THRESHOLD=10
DIP_STREAK=0
LAST_MODE="mixed"

JSON_LOG="$OUT_DIR/watcher_metrics.jsonl"

write_mode() {
  local mode="$1"
  if [ "$mode" != "$LAST_MODE" ]; then
    echo -n "$mode" > "$MODE_FLAG_PATH"
    LAST_MODE="$mode"
    echo "[$(date -Is)] mode flip: -> $mode  (DIP_STREAK=$DIP_STREAK)" >> "$OUT_DIR/watcher.log"
  fi
}

# Init: clear mode flag to "mixed" so we start in normal retrieval
write_mode "mixed"

while true; do
  s=$(find "data/replays/${RUN_ID}/success" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l || true)
  f=$(find "data/replays/${RUN_ID}/failure" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l || true)
  total=$((s + f))

  # Build chronological list of ep outcomes (by replay mtime)
  # Sliding-10 SR = success count in last 10 episodes
  if [ "$total" -gt 0 ]; then
    sliding_succ=$(
      {
        find "data/replays/${RUN_ID}/success" -maxdepth 1 -name '*.json' \
             -printf '%T@ s\n' 2>/dev/null || true
        find "data/replays/${RUN_ID}/failure" -maxdepth 1 -name '*.json' \
             -printf '%T@ f\n' 2>/dev/null || true
      } | sort -n | tail -n "$WINDOW_SIZE" | awk '$2=="s"' | wc -l
    )
    sliding_window=$total
    if [ "$total" -gt "$WINDOW_SIZE" ]; then
      sliding_window=$WINDOW_SIZE
    fi
    sliding_sr=$(( 100 * sliding_succ / sliding_window ))
    cum_sr=$(( 100 * s / total ))
  else
    sliding_succ=0
    sliding_window=0
    sliding_sr=0
    cum_sr=0
  fi

  # JSON metric line for offline analysis
  echo "{\"ts\":\"$(date -Is)\",\"total\":$total,\"succ\":$s,\"fail\":$f,\"cum_sr\":$cum_sr,\"sliding_succ\":$sliding_succ,\"sliding_window\":$sliding_window,\"sliding_sr\":$sliding_sr,\"mode\":\"$LAST_MODE\",\"dip_streak\":$DIP_STREAK}" \
    >> "$JSON_LOG"

  # Snapshot trigger (existing logic)
  if [ "$FIRST_FIRED" -eq 0 ] && [ "$total" -ge 1 ]; then
    python3 scripts/diagnostics/snapshot_run.py \
      --run "$RUN_ID" --out_dir "$OUT_DIR" --snapshot_idx 0
    FIRST_FIRED=1
  fi
  next_threshold=$(( (LAST_SNAP + 1) * STEP ))
  if [ "$total" -ge "$next_threshold" ]; then
    idx=$(( total / STEP ))
    python3 scripts/diagnostics/snapshot_run.py \
      --run "$RUN_ID" --out_dir "$OUT_DIR" --snapshot_idx "$idx"
    LAST_SNAP=$idx
  fi

  # L2/L3 logic only after we have a full sliding window
  if [ "$sliding_window" -ge "$WINDOW_SIZE" ]; then
    if [ "$sliding_sr" -lt "$DIP_THRESHOLD" ]; then
      DIP_STREAK=$((DIP_STREAK + 1))
      if [ "$DIP_STREAK" -ge 2 ]; then
        write_mode "success_only"
      fi
      if [ "$DIP_STREAK" -ge 3 ]; then
        if [ ! -f "$STALL_FLAG_PATH" ]; then
          echo "[$(date -Is)] STALL detected: ${DIP_STREAK} consecutive <${DIP_THRESHOLD}% sliding windows" \
            > "$STALL_FLAG_PATH"
          echo "[$(date -Is)] L3 STALL flag written: $STALL_FLAG_PATH" >> "$OUT_DIR/watcher.log"
        fi
      fi
    elif [ "$sliding_sr" -ge "$RECOVERY_THRESHOLD" ]; then
      DIP_STREAK=0
      write_mode "mixed"
    fi
    # In-between: hold whatever the current mode is, don't reset streak
  fi

  if [ "$total" -ge "$MAX_EPS" ]; then
    break
  fi
  sleep "$INTERVAL"
done
