#!/bin/bash
# L2 Stage-1 driver — A_ctrl_rat-L2 train + 2-protocol eval (Amendment 2).
#
# Scope (L2 Amendment 2): L2 tests ONE answerable question — does the
# identical-weights retrieval effect (C_retrieval - A_ctrl_rat) replicate
# on the harder dual-arm pose-reach task? Only A_ctrl_rat is trained;
# C_retrieval reuses its weights + the frozen re-tagged buffer.
# NO B_main / D_gist / A_action_only in Stage 1 (bake-in T1 is
# un-measurable at n=100 / MDE 12-13pp — Amendment 2).
#
# Steps:
#   1  prep A_ctrl_rat-L2 SFT + KTO pools (per-arm, native, from run a6e6c917)
#   2  verify: row-count + SHA pins (Amendment 1 §3 / Step-2.verify carryover)
#   3  seed-determinism smoke (reuse D11 Blocker-2 check, level 2)
#   4  sync bundle to server
#   5  train A_ctrl_rat SFT (stage 4-A) on server GPU (CUDA 1,2)
#   6  train A_ctrl_rat KTO (stage 4-B, composable C.3-B) on server GPU
#   7  export both adapters to GGUF
#   8  eval 2 protocols on A4500 (NIGHT/idle window — LIBERO gate has priority):
#        A_ctrl_rat  : own adapter, no retrieval
#        C_retrieval : A_ctrl_rat adapter + frozen re-tagged buffer,
#                      --use_memory --recap_buffer_readonly
#                      --memory_success_label_arm left (Amendment 1a)
#      both share --env_seed_base (paired), --eval_template_variant rationale
#
# Usage: bash scripts/training/run_l2_stage1_pipeline.sh [--dry-run] [--skip N]

set -euo pipefail

# ─────────────── Config ───────────────
L2_RUN="a6e6c917"                       # the collected L2 dual run (re-tagged buffer)
L2_LEVEL=2
L2_NUM_EPISODES=100
L2_ENV_SEED_BASE=4600                   # distinct from D11's 4500 (Amendment 11 rotation note)
TRAINING_SETS_DIR="data/training_sets"
CHECKPOINTS_DIR="checkpoints/l2"
RATIONALE_MAP="${TRAINING_SETS_DIR}/l2_rationale_map.jsonl"   # historical (log-derived) — Chap 1
PER_ARM_RESCORE="workspace/l2_audit/per_arm_rescore.json"
RECAP_BUFFER="workspace/recaps_l2"      # re-tagged, dual-label (Amendment 1a)

SFT_RAW="${TRAINING_SETS_DIR}/l2_sft_A_ctrl_rat.raw.jsonl"
SFT_JSONL="${TRAINING_SETS_DIR}/l2_sft_A_ctrl_rat.jsonl"
KTO_RAW="${TRAINING_SETS_DIR}/l2_kto_A_ctrl_rat.raw.jsonl"
KTO_JSONL="${TRAINING_SETS_DIR}/l2_kto_A_ctrl_rat.jsonl"

# Expected pool sizes (Amendment 1/2): 56 desirable episode-instances →
# 511 desirable / 1119 undesirable per-arm ROUNDS. SHA pins recorded after
# first prep (Step 2 writes them; re-runs verify).
SFT_EXPECTED_ROWS=511                   # SFT = desirable progress-rounds
KTO_EXPECTED_ROWS=1630                  # KTO = desirable + undesirable rounds (511+1119)

REMOTE_HOST="exx@10.80.9.148"
REMOTE_ROOT="/home/exx/CYTu/AionGenos_server"
STUDENT_URL="http://10.80.9.148:18889"
FROZEN_BUFFER_TAR="workspace/frozen_buffers/l2_recaps_frozen.tar.gz"

DRY_RUN=0; SKIP_TO=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=1; shift ;;
    --skip)    SKIP_TO=$2; shift 2 ;;
    *) echo "unknown arg: $1"; exit 1 ;;
  esac
done

run() {
  local step=$1; shift
  echo; echo "════════ Step $step ════════"; echo "$ $*"
  local step_num=${step%%.*}
  if [ "$DRY_RUN" -eq 1 ] || [ "$step_num" -lt "$SKIP_TO" ]; then
    [ "$step_num" -lt "$SKIP_TO" ] && echo "  (skipped, --skip $SKIP_TO)" || echo "  (dry-run)"
    return 0
  fi
  eval "$@"
}

echo "═══════════════════════════════════════════════════════════"
echo "  L2 Stage-1 — A_ctrl_rat train + 2-protocol eval (Amendment 2)"
echo "═══════════════════════════════════════════════════════════"
echo "  L2 run:        $L2_RUN   level=$L2_LEVEL   env_seed_base=$L2_ENV_SEED_BASE"
echo "  Scope:         A_ctrl_rat only; C_retrieval reuses it (identical-weights)"
echo "  Buffer:        $RECAP_BUFFER (re-tagged dual-label, Amendment 1a)"
echo "  Rationale map: $RATIONALE_MAP (log-derived historical — Chap 1)"
echo "  Dry run:       $DRY_RUN   Skip-to: $SKIP_TO"
echo

# ─────────────── Step 1: prep A_ctrl_rat-L2 pools (per-arm, native) ───────────────
run "1.sft.prep" "python3 scripts/training/prep_training_data.py \
  --runs $L2_RUN --out $SFT_RAW \
  --only_progress_round \
  --rationale_source native --per_arm_l2 \
  --per_arm_rescore $PER_ARM_RESCORE"
run "1.sft.filter" "python3 scripts/training/filter_rationale_deterministic.py \
  --in $SFT_RAW --out $SFT_JSONL --drop_policy flags_only_a6 && rm -f $SFT_RAW"

run "1.kto.prep" "python3 scripts/training/prep_training_data.py \
  --runs $L2_RUN --out $KTO_RAW \
  --only_progress_round --include_failures \
  --rationale_source native --per_arm_l2 \
  --per_arm_rescore $PER_ARM_RESCORE"
run "1.kto.filter" "python3 scripts/training/filter_rationale_deterministic.py \
  --in $KTO_RAW --out $KTO_JSONL --drop_policy flags_only_a6 && rm -f $KTO_RAW"

# ─────────────── Step 2: row-count + SHA verify (pin on first run) ───────────────
if [ "$DRY_RUN" -eq 0 ] && [ "$SKIP_TO" -lt 5 ]; then
  echo; echo "════════ Step 2.verify — row count + SHA ════════"
  sft_n=$(wc -l < "$SFT_JSONL"); kto_n=$(wc -l < "$KTO_JSONL")
  echo "  SFT rows=$sft_n (expect $SFT_EXPECTED_ROWS)  KTO rows=$kto_n (expect $KTO_EXPECTED_ROWS)"
  fail=0
  [ "$sft_n" = "$SFT_EXPECTED_ROWS" ] || { echo "  SFT row drift ✗"; fail=1; }
  [ "$kto_n" = "$KTO_EXPECTED_ROWS" ] || { echo "  KTO row drift ✗"; fail=1; }
  sft_sha=$(sha256sum "$SFT_JSONL" | cut -c1-24); kto_sha=$(sha256sum "$KTO_JSONL" | cut -c1-24)
  echo "  SFT sha=$sft_sha  KTO sha=$kto_sha"
  L2_PIN="workspace/l2_audit/train_shas.txt"
  if [ -f "$L2_PIN" ]; then
    if ! grep -q "$sft_sha" "$L2_PIN" || ! grep -q "$kto_sha" "$L2_PIN"; then
      echo "  SHA drift vs pin ($L2_PIN) ✗"; fail=1
    else echo "  SHA matches pin ✓"; fi
  else
    printf "sft %s\nkto %s\n" "$sft_sha" "$kto_sha" > "$L2_PIN"
    echo "  first run — pinned to $L2_PIN"
  fi
  [ "$fail" -eq 1 ] && { echo "Step 2.verify FAILED"; exit 2; }
  echo "  ✓ verified"
fi

# ─────────────── Step 3: seed-determinism smoke (level 2) ───────────────
SEED_B=$((L2_ENV_SEED_BASE + 1))
run 3 "/home/control/IsaacLab/isaaclab.sh -p \
  scripts/diagnostics/check_env_seed_determinism.py \
  --level $L2_LEVEL --headless --enable_cameras \
  --seed_a $L2_ENV_SEED_BASE --seed_b $SEED_B \
  2>&1 | tee logs/l2_seed_determinism.log"

# ─────────────── Step 4: sync bundle ───────────────
run 4 "python3 scripts/training/pack_training_bundle.py \
  --jsonls $SFT_JSONL $KTO_JSONL --out /tmp/l2_bundle.tar.gz \
  && scp /tmp/l2_bundle.tar.gz $REMOTE_HOST:/tmp/ \
  && ssh $REMOTE_HOST 'cd $REMOTE_ROOT && tar xzf /tmp/l2_bundle.tar.gz'"

# ─────────────── Step 5: SFT (server GPU 1,2) ───────────────
SFT_CKPT="$CHECKPOINTS_DIR/A_ctrl_rat/sft_A"
run 5 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  CUDA_VISIBLE_DEVICES=1,2 python3 server_side/train_qlora_gemma4.py \
    --jsonl-path $SFT_JSONL --output-dir $SFT_CKPT --run-tag L2.A_ctrl_rat.sft \
    --epochs 1 --batch-size 2 --lr 2e-4 2>&1 | tee logs/l2_A_ctrl_rat_sft.log'"

# ─────────────── Step 6: KTO composable C.3-B (server GPU 1,2) ───────────────
KTO_CKPT="$CHECKPOINTS_DIR/A_ctrl_rat/kto_B"
run 6 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  CUDA_VISIBLE_DEVICES=1,2 python3 server_side/train_qlora_kto.py \
    --jsonl-path $KTO_JSONL --frozen-adapter $SFT_CKPT/final_adapter \
    --output-dir $KTO_CKPT --run-tag L2.A_ctrl_rat.kto \
    --epochs 1 --batch-size 2 --lr 5e-5 --auto-balance \
    2>&1 | tee logs/l2_A_ctrl_rat_kto.log'"

# ─────────────── Step 7: export GGUF ───────────────
run 7 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  python3 server_side/export_lora_gguf.py \
    --checkpoint-dir $SFT_CKPT/final_adapter --output data/lora_gguf/l2_A_ctrl_rat_sft/adapter.gguf \
  && python3 server_side/export_lora_gguf.py \
    --checkpoint-dir $KTO_CKPT/final_adapter --output data/lora_gguf/l2_A_ctrl_rat_kto/adapter.gguf'"

# ─────────────── Step 8: 2-protocol eval (A4500 night window) ───────────────
# Freeze buffer snapshot for C_retrieval (tree-hash gate, Amendment 1a).
run "8.buffer_freeze" "mkdir -p $(dirname $FROZEN_BUFFER_TAR) && \
  tar --sort=name -czf $FROZEN_BUFFER_TAR -C $RECAP_BUFFER . && \
  ( cd $RECAP_BUFFER && find . -type f | sort | xargs sha256sum ) | sha256sum | awk '{print \$1}' > workspace/l2_audit/frozen_buffer.sha256 && \
  echo \"frozen L2 buffer tree_hash=\$(cat workspace/l2_audit/frozen_buffer.sha256)\""

# reload student once with A_ctrl_rat's dual adapters (both protocols share weights)
run "8.reload" "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  bash server_side/reload_student_dual.sh \
    data/lora_gguf/l2_A_ctrl_rat_sft/adapter.gguf \
    data/lora_gguf/l2_A_ctrl_rat_kto/adapter.gguf'"

# Protocol 1: A_ctrl_rat bare (no retrieval)
run "8.A_ctrl_rat.collect" "mkdir -p data/100ep-l2-A_ctrl_rat && \
  nohup /home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --level $L2_LEVEL --num_episodes $L2_NUM_EPISODES \
    --teacher_url $STUDENT_URL --dump_images_root data/collect_dumps --freeze_level \
    --env_seed_base $L2_ENV_SEED_BASE --eval_template_variant rationale \
    --headless --enable_cameras > logs/l2_eval_A_ctrl_rat_\$(date +%Y%m%d_%H%M%S).log 2>&1 && \
  echo 'L2 A_ctrl_rat eval done'"

# Protocol 2: C_retrieval (same weights + frozen re-tagged buffer, arm-aligned floor)
run "8.C_retrieval.collect" "mkdir -p data/100ep-l2-C_retrieval && \
  nohup /home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --level $L2_LEVEL --num_episodes $L2_NUM_EPISODES \
    --teacher_url $STUDENT_URL --dump_images_root data/collect_dumps --freeze_level \
    --env_seed_base $L2_ENV_SEED_BASE --eval_template_variant rationale_with_retrieval \
    --recap_buffer_root $RECAP_BUFFER --use_memory --recap_buffer_readonly \
    --memory_success_label_arm left \
    --headless --enable_cameras > logs/l2_eval_C_retrieval_\$(date +%Y%m%d_%H%M%S).log 2>&1 && \
  echo 'L2 C_retrieval eval done'"

echo; echo "═══════════════════════════════════════════════════════════"
echo "  L2 Stage-1 done. Primary contrast: C_retrieval − A_ctrl_rat (identical-weights)."
echo "  Analyse via d11_mcnemar.py (run_ids param) + d11_exploratory.py (L2 R1 per-arm)."
echo "  Amendment 2 expansion criterion: sig+same-dir → Stage 2 (add A_action_only)."
echo "═══════════════════════════════════════════════════════════"
