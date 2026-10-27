#!/bin/bash
# PI 2026-10-26 items 3+4: rung-1′ on Pin-4c (= (e) coords-ON arm) then (e) lesson-only arm (coords OFF).
# Same interface (d1+d2, history+feedback, memory ON), seeds 5000–5049, 50 eps each, fresh separate buffers.
set -u
cd "$(dirname "$0")/.."
PY=/home/control/env_isaaclab/bin/python; TEACHER=http://10.80.9.148:18888
STATUS=logs/wp3a_p4c_arms_$(date +%Y%m%d_%H%M%S).status
log() { echo "[arms $(date +%F' '%T)] $*" | tee -a "$STATUS"; }
for spec in "on:rung1p_p4c_coords" "off:rung1p_p4c_lesson"; do
  pc=${spec%%:*}; tag=${spec##*:}
  curl -s -m 10 "$TEACHER/health" | grep -q '"ok"' || { log "teacher down — STOP before $tag"; exit 2; }
  L=logs/pilot_${tag}_$(date +%Y%m%d_%H%M%S).log; log "start $tag preamble_coords=$pc → $L"
  PYTHONPATH=$PWD $PY scripts/run_push_collect.py --episodes 50 --seed 5000 --label pilot --obs_rung 1 \
    --geometry pin4c --preamble_coords "$pc" --round_feedback --round_history --frame_convention --verdict_contact_switch \
    --use_memory --recap_buffer_root "workspace/recaps_push_${tag}" \
    --dump_images_root data/collect_dumps --teacher-url "$TEACHER" --headless --enable_cameras > "$L" 2>&1
  SUMMARY=$(grep -o 'logs/push_smoke_[0-9a-f]*\.json' "$L" | tail -1); RUN=$(basename "$SUMMARY" .json); RUN=${RUN#push_smoke_}
  log "$tag run_id=${RUN:-NONE}"; [ -z "$RUN" ] && { log "no summary — STOP"; exit 3; }
  CUDA_VISIBLE_DEVICES= $PY scripts/analysis/wp3a_push_validate.py --run "$RUN" > "logs/validate_${RUN}.txt" 2>&1; v=$?
  log "$tag validate rc=$v"; [ $v -ne 0 ] && { log "HARD fail — STOP"; exit 4; }
  python3 scripts/analysis/wp3a_rho_segments.py "$RUN" > "logs/rho_${RUN}.txt" 2>&1
  log "$tag successes=$($PY -c "import json,sys;print(json.load(open(sys.argv[1]))['n_success'])" "$SUMMARY")/50"
done
log "both arms done"
