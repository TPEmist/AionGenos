#!/bin/bash
# Start run_a17_night.sh inside the night window once the PI's A17 lock commit
# ("docs(d11): A17 LOCK…") is in HEAD's history. Liveness = PID file (Rule 2).
cd "$(dirname "$0")/../.."
echo $$ > logs/a17_waiter.pid
while :; do
  h=$((10#$(date +%H)))
  if [ "$h" -ge 18 ] || [ "$h" -le 1 ]; then
    SHA=$(git log --format=%h --grep='^docs(d11): A17 LOCK' -1 HEAD)
    if [ -n "$SHA" ]; then
      echo "[a17-waiter $(date +%T)] lock $SHA found — starting driver"
      A17_LOCK_SHA="$SHA" exec bash scripts/training/run_a17_night.sh
    fi
  fi
  sleep 60
done
