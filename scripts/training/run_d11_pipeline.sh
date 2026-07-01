#!/bin/bash
# Phase 4 D11 driver — end-to-end pipeline from raw ext-run logs to
# trained student LoRA adapter ready for evaluation.
#
# Runs the full C.3-B composable dual-adapter distillation:
#   (1) extract_historical_retrievals.py — build rationale_map.jsonl
#   (2) prep_training_data.py — build SFT dataset (success ep only)
#   (3) prep_training_data.py — build KTO dataset (success + failure)
#   (4) sync training files to server (rsync)
#   (5) train SFT (stage 4-A) on server
#   (6) train KTO (stage 4-B, frozen SFT + trainable KTO) on server
#   (7) export both adapters to GGUF
#   (8) reload student :18889 with dual --lora
#   (9) D11 collect: 100 ep, --no-memory, --use-constrained-decoding
#
# Steps 1-3 are cheap and run local (~5 min). Steps 4-7 run on the server
# (~4h GPU time). Steps 8-9 are local + server orchestration.
#
# Usage:
#   bash scripts/training/run_d11_pipeline.sh [--dry-run] [--skip TO_STEP]
#
# --dry-run     : print the commands but don't execute
# --skip N      : jump directly to step N (assumes prior steps already ran)
#
# Env overrides:
#   TRAIN_RUNS       : space-separated run_ids to include in training data
#                      (default: all memory-augmented runs)
#   D11_LEVEL        : IsaacLab level for D11 collect (default -2, L0a-Left)
#   D11_NUM_EPISODES : number of collect episodes (default 100)

set -euo pipefail

# ─────────────────────────── Config ───────────────────────────

# Memory-augmented runs (exclude D6 baseline 67685984 — no rationale to attach).
# Order matters for logging; use chronological.
: "${TRAIN_RUNS:=6b9ef134 70028c23 18581c81 b74d9f38 0eb35c80 54bcc2d4 aa08bb4c}"

# Log files matching TRAIN_RUNS (parallel arrays keyed by run_id)
declare -A RUN_TO_LOG
RUN_TO_LOG[6b9ef134]="logs/d10_l0a_left_teacher_mem_20260625_132350.log"
RUN_TO_LOG[70028c23]="logs/d10ext1_l0a_left_teacher_mem_20260629_113025.log"
RUN_TO_LOG[18581c81]="logs/d10ext2_l0a_left_teacher_mem_20260629_125805.log"
RUN_TO_LOG[b74d9f38]="logs/d10ext3_l0a_left_teacher_mem_20260630_111227.log"
RUN_TO_LOG[0eb35c80]="logs/d10ext3b_l0a_left_teacher_mem_20260630_125331.log"
RUN_TO_LOG[54bcc2d4]="logs/d10ext4_l0a_left_teacher_mem_20260630_183612.log"
RUN_TO_LOG[aa08bb4c]="logs/d10ext5b_l0a_left_teacher_mem_20260701_134934.log"

: "${D11_LEVEL:=-2}"
: "${D11_NUM_EPISODES:=100}"

TRAINING_SETS_DIR="data/training_sets"
CHECKPOINTS_DIR="checkpoints/v4"
RATIONALE_MAP="${TRAINING_SETS_DIR}/rationale_map.jsonl"
SFT_JSONL="${TRAINING_SETS_DIR}/v4_sft_A.jsonl"
KTO_JSONL="${TRAINING_SETS_DIR}/v4_kto_B.jsonl"

REMOTE_HOST="exx@10.80.9.148"
REMOTE_ROOT="/home/exx/CYTu/AionGenos_server"
TEACHER_URL="http://10.80.9.148:18888"
STUDENT_URL="http://10.80.9.148:18889"

# ─────────────────────────── CLI parsing ───────────────────────────

DRY_RUN=0
SKIP_TO=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=1; shift ;;
    --skip)    SKIP_TO=$2; shift 2 ;;
    *) echo "unknown arg: $1"; exit 1 ;;
  esac
done

run() {
  local step=$1; shift
  echo
  echo "════════ Step $step ════════"
  echo "$ $*"
  if [ "$DRY_RUN" -eq 1 ] || [ "$step" -lt "$SKIP_TO" ]; then
    if [ "$step" -lt "$SKIP_TO" ]; then
      echo "  (skipped, --skip $SKIP_TO)"
    else
      echo "  (dry-run)"
    fi
    return 0
  fi
  eval "$@"
}

check_prereq() {
  # Confirm every declared run_id has a replay dir and a log file
  for rid in $TRAIN_RUNS; do
    [ -d "data/replays/$rid" ] || { echo "MISSING replay dir: data/replays/$rid"; exit 1; }
    local log=${RUN_TO_LOG[$rid]:-}
    if [ -z "$log" ] || [ ! -f "$log" ]; then
      echo "MISSING log for run $rid (expected: $log)"; exit 1
    fi
  done
  echo "  prereq OK: ${#RUN_TO_LOG[@]} runs, all replay dirs + logs present"
}

echo "═══════════════════════════════════════════════════════════"
echo "  D11 Pipeline — Composable dual-LoRA distillation"
echo "═══════════════════════════════════════════════════════════"
echo "  Runs included:      $TRAIN_RUNS"
echo "  Training sets dir:  $TRAINING_SETS_DIR"
echo "  Checkpoints dir:    $CHECKPOINTS_DIR"
echo "  Remote host:        $REMOTE_HOST"
echo "  Dry run:            $DRY_RUN"
echo "  Skip to step:       $SKIP_TO"
echo
check_prereq

mkdir -p "$TRAINING_SETS_DIR" "$CHECKPOINTS_DIR"

# ─────────────────── Step 1: rationale map ───────────────────

LOG_ARGS=""
for rid in $TRAIN_RUNS; do
  LOG_ARGS="$LOG_ARGS ${RUN_TO_LOG[$rid]}"
done

run 1 "python3 scripts/training/extract_historical_retrievals.py \
  --logs$LOG_ARGS \
  --recap_root workspace/recaps_d10 \
  --out $RATIONALE_MAP"

# ─────────────────── Step 2: SFT dataset (stage 4-A) ───────────────────
#
# Stage 4-A learns "given (image, state, past-lessons) → THOUGHT + action".
# Use per-round samples from SUCCESS episodes only, only progress rounds.
# No KTO label needed here — this is straight SFT.

run 2 "python3 scripts/training/prep_training_data.py \
  --runs $TRAIN_RUNS \
  --out $SFT_JSONL \
  --only_progress_round \
  --rationale_map $RATIONALE_MAP"

# ─────────────────── Step 3: KTO dataset (stage 4-B) ───────────────────
#
# Stage 4-B refines with preference learning. Include failure ep progress
# rounds as undesirable (they show "actions the teacher took that locally
# looked good but globally failed"), success ep progress rounds as desirable.

run 3 "python3 scripts/training/prep_training_data.py \
  --runs $TRAIN_RUNS \
  --out $KTO_JSONL \
  --only_progress_round --include_failures \
  --rationale_map $RATIONALE_MAP"

# ─────────────────── Step 4: sync to server ───────────────────
#
# rsync the two JSONLs + all the images they reference to the server.
# Uses --files-from so we only ship what the trainer will actually load.

run 4 "python3 scripts/training/pack_training_bundle.py \
  --jsonls $SFT_JSONL $KTO_JSONL \
  --out /tmp/d11_bundle.tar.gz \
  && scp /tmp/d11_bundle.tar.gz $REMOTE_HOST:/tmp/ \
  && ssh $REMOTE_HOST 'cd $REMOTE_ROOT && tar xzf /tmp/d11_bundle.tar.gz'"

# ─────────────────── Step 5: SFT training on server ───────────────────

SFT_CKPT="$CHECKPOINTS_DIR/sft_A"
run 5 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  CUDA_VISIBLE_DEVICES=1,2 python3 server_side/train_qlora_gemma4.py \
    --jsonl-path $SFT_JSONL \
    --output-dir $SFT_CKPT \
    --epochs 1 --batch-size 2 --lr 2e-4 \
    2>&1 | tee logs/d11_sft.log'"

# ─────────────────── Step 6: KTO training with frozen SFT (C.3-B) ───────────────────

KTO_CKPT="$CHECKPOINTS_DIR/kto_B"
run 6 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  CUDA_VISIBLE_DEVICES=1,2 python3 server_side/train_qlora_kto.py \
    --jsonl-path $KTO_JSONL \
    --frozen-adapter $SFT_CKPT/final_adapter \
    --output-dir $KTO_CKPT \
    --epochs 1 --batch-size 2 --lr 5e-5 \
    --auto-balance \
    2>&1 | tee logs/d11_kto.log'"

# ─────────────────── Step 7: export both adapters to GGUF ───────────────────
#
# llama.cpp --lora accepts multiple flags; export both then reload student
# with --lora <sft.gguf> --lora <kto.gguf>.

run 7 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  python3 server_side/export_lora_gguf.py \
    --adapter $SFT_CKPT/final_adapter \
    --out data/lora_gguf/v4_sft_A/adapter.gguf \
  && python3 server_side/export_lora_gguf.py \
    --adapter $KTO_CKPT/final_adapter \
    --out data/lora_gguf/v4_kto_B/adapter.gguf'"

# ─────────────────── Step 8: reload student with dual LoRA ───────────────────

run 8 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  bash server_side/reload_student_dual.sh \
    data/lora_gguf/v4_sft_A/adapter.gguf \
    data/lora_gguf/v4_kto_B/adapter.gguf'"

# ─────────────────── Step 9: D11 evaluation collect ───────────────────
#
# 100 ep with:
#   --teacher_url $STUDENT_URL   (routing to student, no memory retrieval)
#   --freeze_level               (same task pinning as ext runs)
#   NO --use_memory              (student is memory-free at inference)
#
# TODO before step 9: wire aiongenos/vlm/constrained_decoding.py into
# stage1_reasoning.py behind a --use_constrained_decoding flag. Without it
# step 9 will run un-constrained inference and student will emit rationale
# tokens at inference (~10× slower). The SR result should still be valid;
# only the "high-Hz" latency claim would need caveating until this lands.

D11_TS=$(date +%Y%m%d_%H%M%S)
D11_LOG="logs/d11_student_v4_${D11_TS}.log"
D11_OUT="data/100ep-d11-student-v4"

run 9 "mkdir -p $D11_OUT && \
  nohup /home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --level $D11_LEVEL \
    --num_episodes $D11_NUM_EPISODES \
    --teacher_url $STUDENT_URL \
    --dump_images_root data/collect_dumps \
    --freeze_level \
    --headless --enable_cameras \
    > $D11_LOG 2>&1 & \
  echo 'D11 collect PID:' \$! && \
  echo 'log: $D11_LOG'"

echo
echo "═══════════════════════════════════════════════════════════"
echo "  D11 pipeline dispatched. Track via:"
echo "    tail -f logs/d11_student_v4_*.log"
echo "    scripts/diagnostics/snapshot_run.py --run <run_id>"
echo "═══════════════════════════════════════════════════════════"
