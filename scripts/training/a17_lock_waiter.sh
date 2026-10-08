#!/bin/bash
# Start run_a17_night.sh inside the night window once the PI's A17 lock commit
# ("docs(d11): A17 LOCK…") is in HEAD's history. Re-invokes the (idempotent)
# driver every night until both protocols are in the manifest, then exits.
# Liveness = PID file (Rule 2).
cd "$(dirname "$0")/../.."
echo $$ > logs/a17_waiter.pid
while :; do
  h=$((10#$(date +%H)))
  if [ "$h" -ge 18 ] || [ "$h" -le 1 ]; then
    SHA=$(git log --format=%h --grep='^docs(d11): A17 LOCK' -1 HEAD)
    if [ -n "$SHA" ]; then
      echo "[a17-waiter $(date +%T)] lock $SHA found — starting driver"
      A17_LOCK_SHA="$SHA" bash scripts/training/run_a17_night.sh
      echo "[a17-waiter $(date +%T)] driver exited ($?)"
      n=$(grep -c '"protocol":"a17_' logs/a17_manifest.jsonl 2>/dev/null || echo 0)
      [ "$n" -ge 2 ] && { echo "[a17-waiter] both protocols done — exit"; rm -f logs/a17_waiter.pid; exit 0; }
      while [ $((10#$(date +%H))) -ge 18 ] || [ $((10#$(date +%H))) -le 1 ]; do sleep 300; done
    fi
  fi
  sleep 60
done
