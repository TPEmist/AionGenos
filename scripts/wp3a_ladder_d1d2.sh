#!/bin/bash
# WP1-③a ladder on the d1+d2 interface (PI ruling 2026-10-22):
#   rung-1′ (obs 1) → rung-1b′ (obs 1b) → rung-2″ (obs 2), seeds 5000–5049, 50 episodes each.
# Climb to the next rung only if this rung had < 5 successes. After each run,
# wp3a_push_validate.py must pass its HARD checks or the ladder stops.
# Every rung uses the same interface flags and its own fresh recap buffer.
set -u
cd "$(dirname "$0")/.."
PY=/home/control/env_isaaclab/bin/python
TEACHER=http://10.80.9.148:18888
STAMP=$(date +%Y%m%d_%H%M%S)
STATUS=logs/wp3a_ladder_d1d2_${STAMP}.status
echo $$ > logs/wp3a_ladder_d1d2.pid
log() { echo "[ladder $(date +%F' '%T)] $*" | tee -a "$STATUS"; }

for spec in "1:rung1p" "1b:rung1bp" "2:rung2pp"; do
  rung=${spec%%:*}; tag=${spec##*:}
  if ! curl -s -m 10 "$TEACHER/health" | grep -q '"ok"'; then log "teacher not healthy — STOP before $tag"; exit 2; fi
  L=logs/pilot_${tag}_d1d2_$(date +%Y%m%d_%H%M%S).log
  log "start $tag (obs_rung=$rung) → $L"
  PYTHONPATH=$PWD $PY scripts/run_push_collect.py --episodes 50 --seed 5000 --label pilot \
    --obs_rung "$rung" --round_feedback --round_history --frame_convention --verdict_contact_switch \
    --use_memory --recap_buffer_root "workspace/recaps_push_pilot_${tag}_d1d2" \
    --dump_images_root data/collect_dumps --teacher-url "$TEACHER" --headless --enable_cameras > "$L" 2>&1
  rc=$?
  SUMMARY=$(grep -o 'logs/push_smoke_[0-9a-f]*\.json' "$L" | tail -1)
  RUN=$(basename "$SUMMARY" .json); RUN=${RUN#push_smoke_}
  log "$tag exited rc=$rc run_id=${RUN:-NONE}"
  [ -z "$RUN" ] && { log "no summary — STOP"; exit 3; }
  CUDA_VISIBLE_DEVICES= $PY scripts/analysis/wp3a_push_validate.py --run "$RUN" > "logs/validate_${RUN}.txt" 2>&1
  vrc=$?
  log "$tag validate rc=$vrc (logs/validate_${RUN}.txt)"
  [ $vrc -ne 0 ] && { log "HARD check failed — STOP"; exit 4; }
  NS=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['n_success'])" "$SUMMARY")
  log "$tag successes=$NS/50"
  if [ "$NS" -ge 5 ]; then log "≥5 successes at $tag — ladder stops here (PI rule)"; exit 0; fi
done
log "ladder complete (all three rungs < 5 successes)"
