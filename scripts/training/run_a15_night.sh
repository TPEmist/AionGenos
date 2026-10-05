#!/bin/bash
# D11 Amendment 15 — protocols (a)+(b), 4 × 100 ep, night-only serial batch.
#
# Mirrors run_d11_pipeline_v2.sh Step 8 exactly (same run_collect flags, same
# frozen buffer + readonly tree-hash gate); only the adapter/variant per
# protocol differs (A15 operational pins 1–3). Night window: a new protocol is
# only STARTED between NIGHT_START_H and NIGHT_LAST_START_H (a started arm runs
# to completion). Idempotent: protocols whose log shows completion are skipped,
# so re-launching each evening resumes the queue.
#
# Usage: bash scripts/training/run_a15_night.sh [--dry-run] [--ignore-window]

set -euo pipefail
cd "$(dirname "$0")/../.."

DRY_RUN=0; IGNORE_WINDOW=0
for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=1 ;;
    --ignore-window) IGNORE_WINDOW=1 ;;
    *) echo "unknown arg $arg" >&2; exit 1 ;;
  esac
done

A15_LOCK_SHA="989a753"
: "${NIGHT_START_H:=18}"        # may start a protocol from 18:00 ...
: "${NIGHT_LAST_START_H:=1}"    # ... until 01:59 (≈10 h arm → done by day)

REMOTE_HOST="exx@10.80.9.148"
REMOTE_ROOT="/home/exx/CYTu/AionGenos_server"
STUDENT_URL="http://10.80.9.148:18889"

FROZEN_BUFFER_TAR="workspace/frozen_buffers/d10ext_final_buffer.tar.gz"
FROZEN_BUFFER_SHA_EXPECTED="a762386b79e18ce50440d1ff3e7045f6f82f32bd7b05092ac332b9217fb0eb9c"
BUFFER_ROOT="workspace/recaps_d10_frozen_c_retrieval"
BUFFER_TREE_EXPECTED="7d4f3f9e93d99b7199a9f2dc4bebe2de2a3fd62cac4dc69d78a294f10e432ec7"
MANIFEST="logs/a15_manifest.jsonl"

declare -a PROTOCOLS=(a_base_ret b_action_only_ret b_B_main_ret b_D_gist_ret)
declare -A ADAPTER_ARM=(
  [a_base_ret]=""                 # no adapter (pin 1)
  [b_action_only_ret]=A_action_only
  [b_B_main_ret]=B_main
  [b_D_gist_ret]=D_gist
)
declare -A VARIANT=(
  [a_base_ret]=rationale_with_retrieval
  [b_action_only_ret]=action_only
  [b_B_main_ret]=rationale_with_gist
  [b_D_gist_ret]=gist_only
)

say() { echo "[A15 $(date +%H:%M:%S)] $*"; }

tree_hash() {
  ( cd "$BUFFER_ROOT" && find . -type f | sort | xargs sha256sum ) | sha256sum | awk '{print $1}'
}

in_window() {
  [ "$IGNORE_WINDOW" -eq 1 ] && return 0
  local h; h=$((10#$(date +%H)))
  [ "$h" -ge "$NIGHT_START_H" ] || [ "$h" -le "$NIGHT_LAST_START_H" ]
}

protocol_done() {
  local f
  for f in logs/a15_"$1"_*.log; do
    [ -f "$f" ] && grep -q "Collect loop execution complete" "$f" && return 0
  done
  return 1
}

# ── pre-flight: lock is in history, buffer pinned ──
git merge-base --is-ancestor "$A15_LOCK_SHA" HEAD \
  || { say "A15 lock $A15_LOCK_SHA not an ancestor of HEAD — refusing to run"; exit 3; }
TAR_SHA=$(sha256sum "$FROZEN_BUFFER_TAR" | awk '{print $1}')
[ "$TAR_SHA" = "$FROZEN_BUFFER_SHA_EXPECTED" ] || { say "buffer tarball sha mismatch: $TAR_SHA"; exit 3; }
[ "$(tree_hash)" = "$BUFFER_TREE_EXPECTED" ] || { say "buffer tree hash mismatch before run"; exit 3; }
say "pre-flight OK (lock $A15_LOCK_SHA, buffer tar + tree hash pinned)"

for prot in "${PROTOCOLS[@]}"; do
  if protocol_done "$prot"; then say "$prot already complete — skip"; continue; fi
  if ! in_window; then say "outside night window — stop before $prot (re-launch tonight)"; exit 0; fi

  arm=${ADAPTER_ARM[$prot]}
  if [ -z "$arm" ]; then
    RELOAD="ssh $REMOTE_HOST 'cd $REMOTE_ROOT && bash server_side/reload_student_base.sh'"
  else
    RELOAD="ssh $REMOTE_HOST 'cd $REMOTE_ROOT && bash server_side/reload_student_dual.sh \
      data/lora_gguf/d11_${arm}_sft/adapter.gguf data/lora_gguf/d11_${arm}_kto/adapter.gguf'"
  fi
  TS=$(date +%Y%m%d_%H%M%S)
  LOG="logs/a15_${prot}_${TS}.log"
  COLLECT="/home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --level -2 --num_episodes 100 --teacher_url $STUDENT_URL \
    --dump_images_root data/collect_dumps --freeze_level --env_seed_base 4500 \
    --eval_template_variant ${VARIANT[$prot]} \
    --recap_buffer_root $BUFFER_ROOT --use_memory --recap_buffer_readonly \
    --headless --enable_cameras"

  if [ "$DRY_RUN" -eq 1 ]; then
    say "DRY $prot"; echo "  $RELOAD"; echo "  $COLLECT > $LOG"; continue
  fi

  say "$prot: reload student (adapter=${arm:-none})"
  eval "$RELOAD"
  say "$prot: collect → $LOG"
  $COLLECT > "$LOG" 2>&1
  POST=$(tree_hash)
  RUN_ID=$(grep -oE "run_id[=: ]+[0-9a-f]{8}" "$LOG" | head -1 | grep -oE "[0-9a-f]{8}$" || echo unknown)
  printf '{"protocol":"%s","lock_sha":"%s","head":"%s","log":"%s","run_id":"%s","adapter_arm":"%s","variant":"%s","buffer_tree_post":"%s","finished":"%s"}\n' \
    "$prot" "$A15_LOCK_SHA" "$(git rev-parse --short HEAD)" "$LOG" "$RUN_ID" "${arm:-none}" \
    "${VARIANT[$prot]}" "$POST" "$(date -Iseconds)" >> "$MANIFEST"
  [ "$POST" = "$BUFFER_TREE_EXPECTED" ] || { say "READONLY GATE FAILED after $prot"; exit 3; }
  say "$prot done (run $RUN_ID), readonly gate OK"
done
say "queue empty"
