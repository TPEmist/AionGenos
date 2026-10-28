#!/bin/bash
# PI 2026-10-28 item 1: memory time-axis pilot. Continuous lives on the (e) lesson-only interface, Pin-4c.
set -u
cd "$(dirname "$0")/.."
PY=/home/control/env_isaaclab/bin/python; TEACHER=http://10.80.9.148:18888
STATUS=logs/wp3a_life_runs_$(date +%Y%m%d_%H%M%S).status
log() { echo "[life $(date +%F' '%T)] $*" | tee -a "$STATUS"; }
for spec in "5000:life1" "5300:life2"; do
  seed=${spec%%:*}; tag=${spec##*:}
  curl -s -m 10 "$TEACHER/health" | grep -q '"ok"' || { log "teacher down — STOP before $tag"; exit 2; }
  L=logs/pilot_${tag}_p4c_lesson_$(date +%Y%m%d_%H%M%S).log; log "start $tag seed=$seed eps=300 → $L"
  PYTHONPATH=$PWD $PY scripts/run_push_collect.py --episodes 300 --seed "$seed" --label pilot --obs_rung 1 \
    --geometry pin4c --preamble_coords off --round_feedback --round_history --frame_convention --verdict_contact_switch \
    --use_memory --recap_buffer_root "workspace/recaps_push_${tag}_p4c_lesson" \
    --dump_images_root data/collect_dumps --teacher-url "$TEACHER" --headless --enable_cameras > "$L" 2>&1
  SUMMARY=$(grep -o 'logs/push_smoke_[0-9a-f]*\.json' "$L" | tail -1); RUN=$(basename "$SUMMARY" .json); RUN=${RUN#push_smoke_}
  log "$tag run_id=${RUN:-NONE}"; [ -z "$RUN" ] && { log "no summary — STOP"; exit 3; }
  CUDA_VISIBLE_DEVICES= $PY scripts/analysis/wp3a_push_validate.py --run "$RUN" > "logs/validate_${RUN}.txt" 2>&1; v=$?
  log "$tag validate rc=$v"; [ $v -ne 0 ] && { log "HARD fail — STOP"; exit 4; }
  log "$tag successes=$($PY -c "import json,sys;print(json.load(open(sys.argv[1]))['n_success'])" "$SUMMARY")/300"
done
log "both lives done"
