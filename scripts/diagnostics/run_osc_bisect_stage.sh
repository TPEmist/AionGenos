#!/bin/bash
# Single entry point for an OSC-bisection stage. Buys out the repeated
# pkill/&&-chain footguns (2026-08-05 efficiency lesson): explicit per-step
# exit-code checks, no && chains, cleanup+GPU-assert+launch in one place.
#
# Usage: run_osc_bisect_stage.sh <stage s0|s1|s2|s3> [--enable_cameras] [extra args]
# Runs detached (setsid), tails nothing — poll logs/osc_bisect_<stage>.log.
set -uo pipefail

STAGE="${1:-}"
if [ -z "$STAGE" ]; then echo "usage: $0 <s0|s1|s2|s3> [--enable_cameras]"; exit 2; fi
shift
EXTRA="$*"

REPO=/home/control/AionGenos
ISAAC=/home/control/IsaacLab/isaaclab.sh
LOG="$REPO/logs/osc_bisect_${STAGE}.log"

cd "$REPO" || { echo "[stage] cd fail"; exit 2; }

# Step 1 — kill any lingering bisect/smoke isaac python (match the actual
# interpreter path, not the script name, so job-tmp path variants are caught).
echo "[stage] cleaning stray isaac bisect procs …"
mapfile -t PIDS < <(pgrep -f 'env_isaaclab/bin/python' 2>/dev/null | while read -r p; do
  if tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q 'wp1_osc_bisect\|wp1_osc_smoke'; then echo "$p"; fi
done)
if [ "${#PIDS[@]}" -gt 0 ]; then
  echo "[stage]   killing: ${PIDS[*]}"
  kill -9 "${PIDS[@]}" 2>/dev/null
  sleep 3
fi

# Step 2 — assert GPU clear (mechanical gate). HALT if not.
if ! bash scripts/diagnostics/assert_gpu_clear.sh; then
  echo "[stage] GPU not clear after cleanup — HALT (inspect stray procs)."
  exit 3
fi

# Step 3 — launch the stage detached.
echo "[stage] launching $STAGE (extra: ${EXTRA:-none}) → $LOG"
setsid bash -c "$ISAAC -p scripts/diagnostics/wp1_osc_bisect.py --stage $STAGE --headless $EXTRA --steps 5 > $LOG 2>&1" </dev/null >/dev/null 2>&1 &
disown
sleep 4
if [ -s "$LOG" ]; then
  echo "[stage] ✓ $STAGE launched (log growing)"
  exit 0
else
  echo "[stage] ✗ $STAGE log empty after 4s — launch may have failed"
  exit 1
fi
