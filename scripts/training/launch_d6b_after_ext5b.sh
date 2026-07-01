#!/bin/bash
# Auto-launch D6b (no-memory + Fix 1/3 ablation) after D10-ext-5b finishes.
#
# Polls the ext-5b PID; when it exits, kicks off D6b immediately with
# identical L0a-Left / 100 ep / freeze_level config but WITHOUT --use_memory.
#
# Rationale: teacher --parallel 1 slot means we can't run two collects in
# parallel without doubling both wall-clocks. Serial dispatch keeps ext-5b
# clean and starts D6b the moment ext-5b's teacher slot frees up.

set -euo pipefail

EXT5B_PID_FILE="/tmp/aiongenos_d10ext5b_pid.txt"
POLL_INTERVAL=60  # seconds between checks

if [ ! -f "$EXT5B_PID_FILE" ]; then
    echo "ERROR: $EXT5B_PID_FILE missing — cannot follow ext-5b" >&2
    exit 1
fi

EXT5B_PID=$(cat "$EXT5B_PID_FILE")
echo "Watching ext-5b PID $EXT5B_PID..."
while kill -0 "$EXT5B_PID" 2>/dev/null; do
    sleep "$POLL_INTERVAL"
done
echo "ext-5b has exited. Launching D6b in 30s..."
sleep 30

cd /home/control/AionGenos

# Sanity: teacher up
CODE=$(curl -s --max-time 3 -o /dev/null -w "%{http_code}" http://10.80.9.148:18888/health 2>/dev/null || echo "000")
if [ "$CODE" != "200" ]; then
    echo "ERROR: teacher endpoint returning HTTP $CODE — abort D6b launch" >&2
    exit 1
fi

TS=$(date +%Y%m%d_%H%M%S)
LOG="logs/d6b_l0a_left_no_memory_fix_${TS}.log"
OUT_DIR="data/100ep-d6b-no-memory-fix"
mkdir -p "$OUT_DIR"

echo
echo "=== Launching D6b ==="
echo "  Config: L0a-Left, 100 ep, freeze_level, Fix 1/3 ACTIVE, NO memory"
echo "  Log:    $LOG"
echo "  Out:    $OUT_DIR"
echo

nohup /home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
  --level -2 \
  --num_episodes 100 \
  --teacher_url http://10.80.9.148:18888 \
  --dump_images_root data/collect_dumps \
  --freeze_level \
  --headless --enable_cameras \
  > "$LOG" 2>&1 &
PID=$!
echo $PID > /tmp/aiongenos_d6b_pid.txt
echo "$LOG"   > /tmp/aiongenos_d6b_log_path.txt
echo "$OUT_DIR" > /tmp/aiongenos_d6b_out_dir.txt
echo "D6b PID: $PID"

echo "Waiting for run_id..."
for i in $(seq 1 25); do
    sleep 10
    RUN=$(grep -oE "run_id=[a-f0-9]{8}" "$LOG" 2>/dev/null | head -1 | sed 's/run_id=//')
    if [ -n "$RUN" ]; then
        echo "  run_id = $RUN (after ${i}0s)"
        echo "$RUN" > /tmp/aiongenos_d6b_run_id.txt
        break
    fi
done

RUN=$(cat /tmp/aiongenos_d6b_run_id.txt 2>/dev/null)
if [ -z "$RUN" ]; then
    echo "ERROR: run_id never appeared. Last log lines:"
    tail -10 "$LOG"
    exit 1
fi

# Launch watcher (no adaptive mode flag needed — no memory in play)
nohup bash scripts/diagnostics/watch_run_adaptive.sh \
    "$RUN" "$OUT_DIR" /tmp/aiongenos_d6b_dummy_flag 10 60 \
    > "$OUT_DIR/watcher.log" 2>&1 &
W=$!
echo $W > /tmp/aiongenos_d6b_watcher_pid.txt
echo "Watcher PID: $W"

echo
echo "=== D6b started successfully ==="
echo "  Track via: tail -f $LOG"
