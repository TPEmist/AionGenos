#!/bin/bash
# Phase 4 D11 driver — Amendment 8-10 four-arm training + five-protocol eval.
#
# Runs the full Amendment-locked pipeline:
#   Step 1  extract_historical_retrievals.py → rationale_map.jsonl
#   Step 2  prep — one JSONL per arm × two policies (SFT-only + full-KTO)
#   Step 3  seed-determinism smoke test (Blocker 2, MUST pass)
#   Step 4  sync training bundle to server
#   Step 5  train four SFT-A adapters (arms: A_action_only, A_ctrl_rat,
#           B_main, D_gist), each with per-arm --run-tag
#   Step 6  train four KTO-B adapters on top (composable C.3-B)
#   Step 7  export all eight to GGUF
#   Step 8  reload student for each arm; run 100-ep collect with
#           --eval_template_variant + shared --env_seed_base +
#           (C_retrieval only) --recap_buffer_readonly + frozen buffer.
#
# All five eval protocols use the SAME env_seed_base ⇒ paired McNemar
# stats (Amendment 11).
#
# Usage:
#   bash scripts/training/run_d11_pipeline.sh [--dry-run] [--skip N]
#   ENV: TRAIN_RUNS, D11_LEVEL, D11_NUM_EPISODES, D11_ENV_SEED_BASE,
#        SKIP_D_GIST=1 to drop D_gist (secondary, budget-first-to-cut).
#
# --dry-run     : print commands, execute nothing
# --skip N      : jump directly to step N

set -euo pipefail

# ─────────────────────────── Config ───────────────────────────

: "${TRAIN_RUNS:=6b9ef134 70028c23 18581c81 b74d9f38 0eb35c80 54bcc2d4 aa08bb4c}"

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
# Amendment 11 pin: env_seed_base fixed at 4500. All five eval protocols
# share this; per-ep seed = 4500 + ep_idx.
: "${D11_ENV_SEED_BASE:=4500}"
: "${SKIP_D_GIST:=0}"

TRAINING_SETS_DIR="data/training_sets"
CHECKPOINTS_DIR="checkpoints/d11"
RATIONALE_MAP="${TRAINING_SETS_DIR}/rationale_map.jsonl"

# Frozen buffer snapshot for C_retrieval (Amendment 8 §8.5).
FROZEN_BUFFER_TAR="workspace/frozen_buffers/d10ext_final_buffer.tar.gz"
FROZEN_BUFFER_SHA_EXPECTED="a762386b79e18ce50440d1ff3e7045f6f82f32bd7b05092ac332b9217fb0eb9c"
# Unpacked buffer path used by --recap_buffer_root at eval time.
C_RETRIEVAL_BUFFER_ROOT="workspace/recaps_d10_frozen_c_retrieval"

# Four arms × two files:
#   *_sft_A.jsonl = 992 desirable-only, for SFT phase
#   *_kto_B.jsonl = 992 desirable + 1799 undesirable, for KTO phase
declare -a ARMS=(A_action_only A_ctrl_rat B_main D_gist)

# Per-arm --rationale_source flag for prep_training_data.py
declare -A ARM_TO_SRC=(
  [A_action_only]=none
  [A_ctrl_rat]=native
  [B_main]=retrieval
  [D_gist]=gist_only
)

# Per-arm --eval_template_variant for run_collect.py. D_gist gets its own
# variant (gist_only) — Amendment 12 §12.2 fix for train/eval slot mismatch.
declare -A ARM_TO_VARIANT=(
  [A_action_only]=action_only
  [A_ctrl_rat]=rationale
  [B_main]=rationale_with_gist
  [D_gist]=gist_only
)

REMOTE_HOST="exx@10.80.9.148"
REMOTE_ROOT="/home/exx/CYTu/AionGenos_server"
TEACHER_URL="http://10.80.9.148:18888"
STUDENT_URL="http://10.80.9.148:18889"

# Amendment 12 §12.1 canonical training-set pins (first 24 hex of SHA-256).
# Filename convention: v_final_{sft,kto}_${arm}.jsonl (canonical, post-filter).
declare -A ARM_TO_SHA_KTO=(
  [A_action_only]="f30a3c3011bcb4b9208754ee"
  [A_ctrl_rat]="870df21da5c64a9cbfb7678f"
  [B_main]="98c4ffca1715f20c7a3191a1"
  [D_gist]="4091ebc175c2c1b712d489d1"
)
declare -A ARM_TO_SHA_SFT=(
  [A_action_only]="e2572d16071519ca4f984f7c"
  [A_ctrl_rat]="39adb1640cec9eb831e028a3"
  [B_main]="ce7434ed7b227a31a032a765"
  [D_gist]="6a2436a056752513ec389e9e"
)

# ─────────────────────────── CLI ───────────────────────────

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
  # Extract leading integer of step label so "2.A_ctrl_rat.sft" compares as 2.
  # This is what makes --skip N resumable through the per-arm loops (fix for
  # dry-run bug "line 113: integer expression expected").
  local step_num=${step%%.*}
  if [ "$DRY_RUN" -eq 1 ] || [ "$step_num" -lt "$SKIP_TO" ]; then
    [ "$step_num" -lt "$SKIP_TO" ] && echo "  (skipped, --skip $SKIP_TO)" || echo "  (dry-run)"
    return 0
  fi
  eval "$@"
}

check_prereq() {
  # Amendment 12 §12.1: prereq covers replay dirs, logs, frozen buffer.
  # Training-set JSONL SHA verification moves to a separate gate that runs
  # AFTER Step 2 has generated them (verify_training_shas). This split
  # avoids the previous bug where prereq validated stale fallback files
  # while Step 2 then silently regenerated fresh ones that never got gated.
  for rid in $TRAIN_RUNS; do
    [ -d "data/replays/$rid" ] || { echo "MISSING replay dir: data/replays/$rid"; exit 1; }
    local log=${RUN_TO_LOG[$rid]:-}
    if [ -z "$log" ] || [ ! -f "$log" ]; then
      echo "MISSING log for run $rid (expected: $log)"; exit 1
    fi
  done
  echo "  prereq OK: ${#RUN_TO_LOG[@]} runs"

  # Frozen buffer SHA (C_retrieval) — files that already exist can be gated
  # right now; missing file is now a hard exit (Amendment 12 §12.4: same
  # gate two severities is a smell, MISSING is stricter than mismatch).
  if [ ! -f "$FROZEN_BUFFER_TAR" ]; then
    echo "  MISSING frozen buffer tar: $FROZEN_BUFFER_TAR — C_retrieval cannot run, aborting."
    exit 2
  fi
  local bs=$(sha256sum "$FROZEN_BUFFER_TAR" | awk '{print $1}')
  if [ "$bs" = "$FROZEN_BUFFER_SHA_EXPECTED" ]; then
    echo "  frozen buffer: sha=$bs ✓"
  else
    echo "  frozen buffer: sha=$bs EXPECTED=$FROZEN_BUFFER_SHA_EXPECTED ✗"; exit 2
  fi
}

# Amendment 12 §12.1 / 13 §13.1 gate — two-stage validation of every
# training-set JSONL Step 2 produced:
#   (a) row count sentinel: sft = SFT_EXPECTED_ROWS (992),
#                            kto = KTO_EXPECTED_ROWS (2791).
#       Cheap, and gives a readable error if filter drops rows silently.
#   (b) sha256 pin verification (first 24 hex).
# Called between Step 2 and Step 3. Non-zero exit = pipeline halt.
SFT_EXPECTED_ROWS=992
KTO_EXPECTED_ROWS=2791

verify_training_shas() {
  echo
  echo "════════ Step 2.verify — row count + SHA (post-filter) ════════"
  local fail=0
  for arm in "${ARMS[@]}"; do
    [ "$SKIP_D_GIST" = "1" ] && [ "$arm" = "D_gist" ] && continue

    local sft_f="${TRAINING_SETS_DIR}/v_final_sft_${arm}.jsonl"
    local kto_f="${TRAINING_SETS_DIR}/v_final_kto_${arm}.jsonl"

    for pair in "sft:$sft_f:${ARM_TO_SHA_SFT[$arm]}:$SFT_EXPECTED_ROWS" \
                "kto:$kto_f:${ARM_TO_SHA_KTO[$arm]}:$KTO_EXPECTED_ROWS"; do
      IFS=: read kind f want want_n <<< "$pair"
      if [ ! -f "$f" ]; then
        echo "  ${arm}.${kind}: MISSING $f — pipeline aborts"; fail=1; continue
      fi
      # (a) Row-count sentinel — human-readable early failure. Amendment 8
      # §8.6 invariant: every arm × split has the same fixed row count.
      # If this fails, filter is dropping rows (drop_policy semantic drift?)
      # or prep skipped rows (rationale_map miss?) — either way the four
      # arms no longer share the same 2791-row pool.
      local got_n=$(wc -l < "$f")
      if [ "$got_n" != "$want_n" ]; then
        echo "  ${arm}.${kind}: rows=$got_n EXPECTED=$want_n ✗ — "\
"row count drifted, filter or prep is dropping rows silently"
        fail=1
        continue
      fi
      # (b) SHA pin — final byte-level check.
      local got=$(sha256sum "$f" | awk '{print $1}' | cut -c 1-24)
      if [ "$got" = "$want" ]; then
        echo "  ${arm}.${kind}: rows=$got_n ✓  sha=$got ✓"
      else
        echo "  ${arm}.${kind}: rows=$got_n ✓  sha=$got EXPECTED=$want ✗"; fail=1
      fi
    done
  done
  if [ "$fail" -eq 1 ]; then
    echo "Step 2.verify FAILED — pinned files drifted. Aborting before Step 3."
    exit 2
  fi
  echo "  All training-set row-count + SHA pins verified ✓"
}

echo "═══════════════════════════════════════════════════════════"
echo "  D11 Pipeline — Amendment 8-10 four-arm training + five-protocol eval"
echo "═══════════════════════════════════════════════════════════"
echo "  Runs:               $TRAIN_RUNS"
echo "  Arms (train):       ${ARMS[*]}"
echo "  Env seed base:      $D11_ENV_SEED_BASE  (per-ep seed = base + ep_idx)"
echo "  Level:              $D11_LEVEL"
echo "  Episodes per arm:   $D11_NUM_EPISODES"
echo "  SKIP_D_GIST:        $SKIP_D_GIST"
echo "  Dry run:            $DRY_RUN"
echo "  Skip-to:            $SKIP_TO"
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

# ─────────────────── Step 2: per-arm training-set generation ───────────────────
#
# Filename convention (Amendment 12 §12.1):
#   ${TRAINING_SETS_DIR}/v_final_{sft,kto}_${arm}.jsonl  (post-filter, canonical)
#
# Two-stage pipeline per arm × per split:
#   prep_training_data → *.raw.jsonl   (fresh from replay + rationale_map)
#   filter_rationale   → *.jsonl       (advisory flags added; drop_policy=flags_only_a6)

for arm in "${ARMS[@]}"; do
  [ "$SKIP_D_GIST" = "1" ] && [ "$arm" = "D_gist" ] && continue

  src="${ARM_TO_SRC[$arm]}"

  SFT_RAW="${TRAINING_SETS_DIR}/v_final_sft_${arm}.raw.jsonl"
  SFT_JSONL="${TRAINING_SETS_DIR}/v_final_sft_${arm}.jsonl"
  KTO_RAW="${TRAINING_SETS_DIR}/v_final_kto_${arm}.raw.jsonl"
  KTO_JSONL="${TRAINING_SETS_DIR}/v_final_kto_${arm}.jsonl"

  # SFT-A (992 desirable, --only_progress_round, no failures)
  run "2.${arm}.sft.prep" "python3 scripts/training/prep_training_data.py \
    --runs $TRAIN_RUNS \
    --out $SFT_RAW \
    --only_progress_round \
    --rationale_map $RATIONALE_MAP \
    --rationale_source $src \
    --restrict_to_retrievable"
  run "2.${arm}.sft.filter" "python3 scripts/training/filter_rationale_deterministic.py \
    --in $SFT_RAW --out $SFT_JSONL --drop_policy flags_only_a6 \
    && rm -f $SFT_RAW"

  # KTO-B (992 desirable + 1799 undesirable)
  run "2.${arm}.kto.prep" "python3 scripts/training/prep_training_data.py \
    --runs $TRAIN_RUNS \
    --out $KTO_RAW \
    --only_progress_round --include_failures \
    --rationale_map $RATIONALE_MAP \
    --rationale_source $src \
    --restrict_to_retrievable"
  run "2.${arm}.kto.filter" "python3 scripts/training/filter_rationale_deterministic.py \
    --in $KTO_RAW --out $KTO_JSONL --drop_policy flags_only_a6 \
    && rm -f $KTO_RAW"
done

# ─────────────────── Step 2b: SHA gate against Amendment 12 pin ───────────────────
# Amendment 12 §12.1 / 13 §13.1 gate placement — between Step 2 and Step 3.
# Runs unless the user explicitly requested to jump past training itself
# (--skip 5+). Dry-run shows the gate placement + verifies against files
# on disk so that the failure surface is discoverable pre-flight, not at
# midnight when the pipeline crashes at hour 12.
if [ "$SKIP_TO" -lt 5 ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    echo
    echo "════════ Step 2.verify (would run here in real invocation) ════════"
    echo "  (dry-run: skipping actual sha256 hashing)"
  else
    verify_training_shas
  fi
fi

# ─────────────────── Step 3: Blocker 2 — seed determinism smoke test ───────────────────
#
# Must PASS before dispatching real collects; exit code 1 aborts pipeline.

SEED_B_VAL=$((D11_ENV_SEED_BASE + 1))
run 3 "/home/control/IsaacLab/isaaclab.sh -p \
  scripts/diagnostics/check_env_seed_determinism.py \
  --level $D11_LEVEL --headless --enable_cameras \
  --seed_a $D11_ENV_SEED_BASE --seed_b $SEED_B_VAL \
  2>&1 | tee logs/d11_seed_determinism.log"

# ─────────────────── Step 4: sync to server ───────────────────
# Bundle every arm's SFT + KTO JSONLs plus rationale_map.

BUNDLE_INPUTS=""
for arm in "${ARMS[@]}"; do
  [ "$SKIP_D_GIST" = "1" ] && [ "$arm" = "D_gist" ] && continue
  BUNDLE_INPUTS="$BUNDLE_INPUTS ${TRAINING_SETS_DIR}/v_final_sft_${arm}.jsonl ${TRAINING_SETS_DIR}/v_final_kto_${arm}.jsonl"
done

run 4 "python3 scripts/training/pack_training_bundle.py \
  --jsonls $BUNDLE_INPUTS \
  --out /tmp/d11_bundle.tar.gz \
  && scp /tmp/d11_bundle.tar.gz $REMOTE_HOST:/tmp/ \
  && ssh $REMOTE_HOST 'cd $REMOTE_ROOT && tar xzf /tmp/d11_bundle.tar.gz'"

# ─────────────────── Step 5: SFT training per arm ───────────────────

for arm in "${ARMS[@]}"; do
  [ "$SKIP_D_GIST" = "1" ] && [ "$arm" = "D_gist" ] && continue

  SFT_JSONL="${TRAINING_SETS_DIR}/v_final_sft_${arm}.jsonl"
  SFT_CKPT="$CHECKPOINTS_DIR/${arm}/sft_A"
  run "5.${arm}" "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
    CUDA_VISIBLE_DEVICES=1,2 python3 server_side/train_qlora_gemma4.py \
      --jsonl-path $SFT_JSONL \
      --output-dir $SFT_CKPT \
      --run-tag ${arm}.sft \
      --epochs 1 --batch-size 2 --lr 2e-4 \
      2>&1 | tee logs/d11_${arm}_sft.log'"
done

# ─────────────────── Step 6: KTO training per arm (C.3-B on top of arm's SFT) ───────────────────

for arm in "${ARMS[@]}"; do
  [ "$SKIP_D_GIST" = "1" ] && [ "$arm" = "D_gist" ] && continue

  KTO_JSONL="${TRAINING_SETS_DIR}/v_final_kto_${arm}.jsonl"
  SFT_CKPT="$CHECKPOINTS_DIR/${arm}/sft_A"
  KTO_CKPT="$CHECKPOINTS_DIR/${arm}/kto_B"
  run "6.${arm}" "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
    CUDA_VISIBLE_DEVICES=1,2 python3 server_side/train_qlora_kto.py \
      --jsonl-path $KTO_JSONL \
      --frozen-adapter $SFT_CKPT/final_adapter \
      --output-dir $KTO_CKPT \
      --run-tag ${arm}.kto \
      --epochs 1 --batch-size 2 --lr 5e-5 \
      --auto-balance \
      2>&1 | tee logs/d11_${arm}_kto.log'"
done

# ─────────────────── Step 7: export all adapters to GGUF ───────────────────

for arm in "${ARMS[@]}"; do
  [ "$SKIP_D_GIST" = "1" ] && [ "$arm" = "D_gist" ] && continue

  SFT_CKPT="$CHECKPOINTS_DIR/${arm}/sft_A"
  KTO_CKPT="$CHECKPOINTS_DIR/${arm}/kto_B"
  run "7.${arm}" "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
    python3 server_side/export_lora_gguf.py \
      --adapter $SFT_CKPT/final_adapter \
      --out data/lora_gguf/d11_${arm}_sft/adapter.gguf \
    && python3 server_side/export_lora_gguf.py \
      --adapter $KTO_CKPT/final_adapter \
      --out data/lora_gguf/d11_${arm}_kto/adapter.gguf'"
done

# ─────────────────── Step 8: five eval protocols ───────────────────
#
# For each PROTOCOL_i:
#   - reload student with the appropriate adapter pair (dual --lora)
#   - run 100-ep collect with --eval_template_variant + --env_seed_base
#   - C_retrieval only: --use_memory --recap_buffer_readonly + frozen buffer
#
# All five collects share --env_seed_base=$D11_ENV_SEED_BASE so ep_idx=k
# produces identical initial pose across arms → paired McNemar stats.

# Prepare frozen buffer for C_retrieval eval (Amendment 8 §8.5).
# Record pre-collect file count so the readonly gate can be verified after
# C_retrieval collect finishes.
BUFFER_TREE_HASH_FILE="/tmp/d11_c_retrieval_buffer_tree.sha256"
# Amendment 12 §12.3: record tree hash (sorted per-file sha256 aggregate) so
# a same-count overwrite of an existing recap is caught by the post-collect
# gate. File-count alone would miss it. Escape \$(cat) so the shell that
# runs `eval` (not the shell that builds the command string) reads the file
# post-unpack.
run "8.frozen_buffer_unpack" "rm -rf $C_RETRIEVAL_BUFFER_ROOT && \
  mkdir -p $C_RETRIEVAL_BUFFER_ROOT && \
  tar xzf $FROZEN_BUFFER_TAR -C $C_RETRIEVAL_BUFFER_ROOT && \
  ( cd $C_RETRIEVAL_BUFFER_ROOT && find . -type f | sort | xargs sha256sum ) \
    | sha256sum | awk '{print \$1}' > $BUFFER_TREE_HASH_FILE && \
  echo \"C_retrieval buffer unpacked to $C_RETRIEVAL_BUFFER_ROOT — tree_hash=\$(cat $BUFFER_TREE_HASH_FILE)\""

# Adapter-set → collect loop map. C_retrieval reuses A_ctrl_rat's adapter.
declare -A PROTOCOL_TO_ARM=(
  [A_action_only]=A_action_only
  [A_ctrl_rat]=A_ctrl_rat
  [B_main]=B_main
  [D_gist]=D_gist
  [C_retrieval]=A_ctrl_rat
)
declare -A PROTOCOL_TO_VARIANT=(
  [A_action_only]=action_only
  [A_ctrl_rat]=rationale
  [B_main]=rationale_with_gist
  [D_gist]=gist_only
  [C_retrieval]=rationale_with_retrieval
)
declare -a PROTOCOLS=(A_action_only A_ctrl_rat B_main D_gist C_retrieval)

for prot in "${PROTOCOLS[@]}"; do
  [ "$SKIP_D_GIST" = "1" ] && [ "$prot" = "D_gist" ] && continue

  base_arm=${PROTOCOL_TO_ARM[$prot]}
  variant=${PROTOCOL_TO_VARIANT[$prot]}

  # Reload student with this arm's SFT + KTO adapters.
  run "8.${prot}.reload" "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
    bash server_side/reload_student_dual.sh \
      data/lora_gguf/d11_${base_arm}_sft/adapter.gguf \
      data/lora_gguf/d11_${base_arm}_kto/adapter.gguf'"

  D11_TS=$(date +%Y%m%d_%H%M%S)
  D11_LOG="logs/d11_${prot}_${D11_TS}.log"
  D11_OUT="data/100ep-d11-${prot}"

  # C_retrieval adds --use_memory + --recap_buffer_readonly + frozen buffer.
  if [ "$prot" = "C_retrieval" ]; then
    MEM_ARGS="--recap_buffer_root $C_RETRIEVAL_BUFFER_ROOT --use_memory --recap_buffer_readonly"
  else
    MEM_ARGS=""
  fi

  run "8.${prot}.collect" "mkdir -p $D11_OUT && \
    nohup /home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
      --level $D11_LEVEL \
      --num_episodes $D11_NUM_EPISODES \
      --teacher_url $STUDENT_URL \
      --dump_images_root data/collect_dumps \
      --freeze_level \
      --env_seed_base $D11_ENV_SEED_BASE \
      --eval_template_variant $variant \
      $MEM_ARGS \
      --headless --enable_cameras \
      > $D11_LOG 2>&1 && \
    echo 'D11 $prot collect done → $D11_LOG'"

  # Amendment 12 §12.3 readonly gate — assert tree hash unchanged pre vs
  # post (catches same-count overwrites, which file-count alone would miss).
  # Fails hard (exit 3) if any write slipped through; that would invalidate
  # C_retrieval as a frozen-external-memory comparator.
  if [ "$prot" = "C_retrieval" ]; then
    run "8.${prot}.readonly_check" "PRE=\$(cat $BUFFER_TREE_HASH_FILE); \
      POST=\$( ( cd $C_RETRIEVAL_BUFFER_ROOT && find . -type f | sort | xargs sha256sum ) | sha256sum | awk '{print \$1}' ); \
      echo \"pre=\$PRE post=\$POST\"; \
      [ \"\$PRE\" = \"\$POST\" ] || { echo \"READONLY GATE FAILED — buffer tree hash changed during C_retrieval eval\"; exit 3; }"
  fi
done

echo
echo "═══════════════════════════════════════════════════════════"
echo "  D11 pipeline complete. Analyse via:"
echo "    tail logs/d11_*.log"
echo "    scripts/diagnostics/snapshot_run.py --run <run_id>"
echo "    (Amendment 11) McNemar per-pair against paired ep_idx outcome"
echo "═══════════════════════════════════════════════════════════"
