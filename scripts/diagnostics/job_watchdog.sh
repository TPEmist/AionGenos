#!/bin/bash
# Job watchdog + heartbeat — the mode-level fix for silent failures.
# Three times this pipeline was bitten by failures that were not logic
# errors but errors nobody was told about (full_response unsaved, recap
# empty-response, guard dead-wait 22h). Rule: anything that WAITS must
# have an alarm, and every background job emits a heartbeat.
#
# Usage: job_watchdog.sh <pid> <logfile> <label> [stall_alarm_min=120] [progress_regex]
#   Emits a heartbeat line every 30min: alive + last progress line.
#   If the log's last-modified time hasn't advanced in >stall_alarm_min,
#   OR the pid dies unexpectedly, prints a loud ALARM block.
set -uo pipefail
PID=$1; LOG=$2; LABEL=$3; STALL_MIN=${4:-120}; PROG_RE=${5:-"Step|loss|Episode|Saving|adapter|Collect loop|epoch"}
HB="logs/watchdog_${LABEL}.log"
echo "[watchdog $LABEL] start pid=$PID log=$LOG stall_alarm=${STALL_MIN}min $(date '+%F %T')" | tee -a "$HB"
last_size=0; stall_start=$(date +%s)
while true; do
  sleep 1800  # 30 min heartbeat
  now=$(date +%s)
  if ! kill -0 "$PID" 2>/dev/null; then
    if grep -qE "Collect loop execution complete|adapter.gguf|Stage-1 done|complete" "$LOG" 2>/dev/null; then
      echo "[watchdog $LABEL] ✓ pid $PID exited after completion marker $(date '+%F %T')" | tee -a "$HB"
    else
      echo "==== ALARM [$LABEL] pid $PID DIED with no completion marker $(date '+%F %T') ====" | tee -a "$HB"
      tail -15 "$LOG" | sed 's/^/  /' | tee -a "$HB"
    fi
    break
  fi
  cur_size=$(stat -c %s "$LOG" 2>/dev/null || echo 0)
  last_prog=$(grep -oE "$PROG_RE.*" "$LOG" 2>/dev/null | tail -1 | head -c 120)
  if [ "$cur_size" -gt "$last_size" ]; then
    last_size=$cur_size; stall_start=$now
    echo "[watchdog $LABEL] alive $(date '+%F %T') | $last_prog" | tee -a "$HB"
  else
    stalled_min=$(( (now - stall_start) / 60 ))
    if [ "$stalled_min" -ge "$STALL_MIN" ]; then
      echo "==== ALARM [$LABEL] log SILENT ${stalled_min}min (>${STALL_MIN}) — possible dead-wait/hang $(date '+%F %T') ====" | tee -a "$HB"
      echo "  last progress: $last_prog" | tee -a "$HB"
      stall_start=$now  # re-arm so it re-alarms each interval, doesn't spam every 30min
    else
      echo "[watchdog $LABEL] alive(quiet ${stalled_min}min) $(date '+%F %T') | $last_prog" | tee -a "$HB"
    fi
  fi
done
