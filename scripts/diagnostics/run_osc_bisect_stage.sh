#!/bin/bash
# Single HARDENED entry point for an OSC-bisection / test-bed stage.
# The three process rules are BURNED IN here so they cannot be forgotten:
#
#  (a) PYTHONUNBUFFERED=1 + stdbuf -oL on the launch — flush is now
#      structurally impossible to forget (sterilises the 3× no-flush→
#      false-hang misread).
#  (b) A background monitor writes a heartbeat file every 15s (step marker +
#      timestamp) and, on stage exit, writes a machine VERDICT
#      (PASS/FAIL/HANG) from the log markers + exit code + liveness — NOT
#      from reading stdout "atmosphere". Callers cite the verdict file.
#  (c) Before the requested stage, a known-good BASELINE (L2 DiffIK seed
#      smoke) is run first; baseline RED ⇒ the instrument is broken ⇒ this
#      run's verdicts are void (Rule: re-calibrate after any tool change).
#      Skippable with --no-baseline for rapid same-session repeats once the
#      baseline is green this session.
#
# Usage: run_osc_bisect_stage.sh <stage> [--enable_cameras] [--no-baseline] [extra]
#   stage ∈ {s0,s1,s2,s3,orig,gripzero}
# Returns immediately after dispatch; poll:
#   logs/osc_bisect_<stage>.verdict   (PASS|FAIL|HANG|RUNNING)
#   logs/osc_bisect_<stage>.heartbeat (live step + ts)
#   logs/osc_bisect_<stage>.log       (full stdout)
set -uo pipefail

STAGE="${1:-}"
if [ -z "$STAGE" ]; then echo "usage: $0 <stage> [--enable_cameras] [--no-baseline]"; exit 2; fi
shift

RUN_BASELINE=1
EXTRA_ARGS=()
for a in "$@"; do
  if [ "$a" = "--no-baseline" ]; then RUN_BASELINE=0; else EXTRA_ARGS+=("$a"); fi
done
EXTRA="${EXTRA_ARGS[*]:-}"

REPO=/home/control/AionGenos
ISAAC=/home/control/IsaacLab/isaaclab.sh
LOG="$REPO/logs/osc_bisect_${STAGE}.log"
HB="$REPO/logs/osc_bisect_${STAGE}.heartbeat"
VERDICT="$REPO/logs/osc_bisect_${STAGE}.verdict"
BASELINE_LOG="$REPO/logs/osc_baseline_L2.log"

cd "$REPO" || { echo "[stage] cd fail"; exit 2; }

# ── shared cleanup + GPU gate ──────────────────────────────────────────
_clean_and_gate() {
  local tag="$1"
  echo "[stage] ($tag) cleaning stray isaac procs …"
  mapfile -t PIDS < <(pgrep -f 'env_isaaclab/bin/python' 2>/dev/null | while read -r p; do
    if tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -qE 'wp1_osc_bisect|wp1_osc_smoke|check_env_seed'; then echo "$p"; fi
  done)
  if [ "${#PIDS[@]}" -gt 0 ]; then echo "[stage]   killing: ${PIDS[*]}"; kill -9 "${PIDS[@]}" 2>/dev/null; sleep 3; fi
  bash scripts/diagnostics/assert_gpu_clear.sh
}

# ── (c) baseline re-calibration — known-good L2 DiffIK before the stage ──
if [ "$RUN_BASELINE" -eq 1 ]; then
  if ! _clean_and_gate "baseline"; then echo "[stage] GPU not clear before baseline — HALT"; exit 3; fi
  echo "[stage] (c) baseline: L2 DiffIK seed smoke (instrument check) → $BASELINE_LOG"
  PYTHONUNBUFFERED=1 stdbuf -oL -eL "$ISAAC" -p scripts/diagnostics/check_env_seed_determinism.py \
    --level 2 --headless --enable_cameras --seed_a 4600 --seed_b 4601 > "$BASELINE_LOG" 2>&1
  if grep -q 'overall: PASS' "$BASELINE_LOG" 2>/dev/null; then
    echo "[stage] (c) baseline GREEN — instrument trusted"
  else
    echo "[stage] ✗ (c) baseline RED — INSTRUMENT BROKEN, this run's verdicts are VOID"
    echo "VOID-BASELINE-RED" > "$VERDICT"
    exit 4
  fi
fi

# ── cleanup + gate before the actual stage ─────────────────────────────
if ! _clean_and_gate "stage"; then echo "[stage] GPU not clear — HALT"; exit 3; fi

# ── (a) launch flushed + unbuffered; (b) background monitor writes verdict ─
echo "RUNNING" > "$VERDICT"
: > "$HB"
echo "[stage] launching $STAGE (extra: ${EXTRA:-none}) → $LOG"

setsid bash -c "PYTHONUNBUFFERED=1 stdbuf -oL -eL $ISAAC -p scripts/diagnostics/wp1_osc_bisect.py --stage $STAGE --headless $EXTRA --steps 5 > $LOG 2>&1" </dev/null >/dev/null 2>&1 &
STAGE_PID=$!
disown

# Background monitor: heartbeat every 15s + machine verdict on exit.
# Verdict logic (no stdout atmosphere): STAGE PASS marker → PASS; any
# Traceback/Error → FAIL; process gone w/o PASS → FAIL; log-size flat for
# > STALL_S while proc alive → HANG.
setsid bash -c '
  LOG="'"$LOG"'"; HB="'"$HB"'"; VERDICT="'"$VERDICT"'"; PID='"$STAGE_PID"'
  STALL_S=180; last_size=0; flat=0
  while kill -0 "$PID" 2>/dev/null; do
    sz=$(stat -c%s "$LOG" 2>/dev/null || echo 0)
    step=$(grep -cE "\[bisect" "$LOG" 2>/dev/null || echo 0)
    echo "$(date +%H:%M:%S) size=$sz markers=$step" >> "$HB"
    if [ "$sz" = "$last_size" ]; then flat=$((flat+15)); else flat=0; last_size=$sz; fi
    if grep -q "STAGE PASS" "$LOG" 2>/dev/null; then echo "PASS" > "$VERDICT"; break; fi
    if grep -qE "Traceback|Error:|error running python" "$LOG" 2>/dev/null; then echo "FAIL" > "$VERDICT"; break; fi
    if [ "$flat" -ge "$STALL_S" ]; then echo "HANG" > "$VERDICT"; break; fi
    sleep 15
  done
  # settle: process ended — final classification from markers
  sleep 2
  if grep -q "STAGE PASS" "$LOG" 2>/dev/null; then echo "PASS" > "$VERDICT"
  elif grep -qE "Traceback|Error:|error running python" "$LOG" 2>/dev/null; then echo "FAIL" > "$VERDICT"
  elif [ "$(cat "$VERDICT" 2>/dev/null)" = "RUNNING" ]; then echo "FAIL-NO-PASS-MARKER" > "$VERDICT"; fi
' </dev/null >/dev/null 2>&1 &
disown

sleep 4
if [ -s "$LOG" ]; then echo "[stage] ✓ $STAGE launched — poll $VERDICT / $HB"; exit 0; fi
echo "[stage] ✗ $STAGE log empty after 4s — launch may have failed"; echo "FAIL-LAUNCH" > "$VERDICT"; exit 1
