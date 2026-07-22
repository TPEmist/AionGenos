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

DRY_RUN=0; SKIP_TO=0; UNTIL=99
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=1; shift ;;
    --skip)    SKIP_TO=$2; shift 2 ;;
    --until)   UNTIL=$2; shift 2 ;;   # stop after step <= UNTIL (e.g. --until 7 = train+export, no eval)
    *) echo "unknown arg: $1"; exit 1 ;;
  esac
done

# A4500 yield-check: the LOCAL A4500 GPU is shared with the LIBERO line
# (floating schedule: post-fix re-smoke → primitive repair → re-smoke).
# Any local IsaacLab step (seed smoke, eval collect) must WAIT, not race,
# if a libero/robosuite process is live or the A4500 is meaningfully
# occupied. Mechanical, not "I think LIBERO finished".
wait_for_a4500_idle() {
  # Idle test = NO live compute-app on the A4500 AND no libero/robosuite
  # process. This machine idles at ~3000 MiB resident (display server /
  # leftover CUDA context) with ZERO compute-apps, so a memory-threshold
  # test is wrong (it read the 3GB baseline as "busy" and spun 22h once).
  # A real job registers a compute-app; that is the signal to wait on.
  local waited=0
  while true; do
    local live_proc n_apps
    live_proc=$(pgrep -f "libero\|robosuite" | head -1 || true)
    # count only lines containing a digit (empty output → 0; avoids blank
    # lines miscounting, and multi-GPU rows are each a real app row).
    n_apps=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -c '[0-9]' || true)
    n_apps=${n_apps:-0}
    if [ -z "$live_proc" ] && [ "$n_apps" -eq 0 ] 2>/dev/null; then
      echo "  A4500 idle (0 compute-apps, no libero/robosuite proc) — proceeding after ${waited}min wait"
      return 0
    fi
    # Watchdog: a wait is not allowed to be silent (mode-level lesson —
    # the guard once dead-waited 22h unnoticed). Alarm every 2h of waiting.
    if [ "$waited" -gt 0 ] && [ $((waited % 120)) -eq 0 ]; then
      echo "==== ALARM: A4500 yield-check has waited ${waited}min (>2h). Still busy (compute_apps=${n_apps}). Is this expected? ===="
    fi
    echo "  A4500 busy (compute_apps=${n_apps}, libero_proc=${live_proc:-none}) — LIBERO has priority, sleeping 10min (waited ${waited}min)"
    sleep 600; waited=$((waited + 10))
  done
}

run() {
  local step=$1; shift
  local step_num=${step%%.*}
  if [ "$step_num" -gt "$UNTIL" ]; then return 0; fi   # --until upper bound
  echo; echo "════════ Step $step ════════"; echo "$ $*"
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
  --rationale_source native --per_arm_l2 --sft_desirable_only \
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
  [ "$fail" -eq 1 ] && {
    echo "Step 2.verify FAILED — HALT. Do NOT edit the pin to pass."
    echo "  A mismatch means one of two things to UNDERSTAND, not bypass:"
    echo "   (a) filter semantic drift — flags_only_a6 silently dropped rows"
    echo "       (it must be structural zero-drop; check filter policy), or"
    echo "   (b) prep non-determinism — investigate before trusting any output."
    exit 2
  }
  echo "  ✓ verified"
fi

# ─────────────── Step 3: seed-determinism smoke (level 2) ───────────────
# Local A4500 step — yield to LIBERO first.
if [ "$DRY_RUN" -eq 0 ] && [ "$SKIP_TO" -le 3 ]; then
  echo; echo "──── A4500 yield-check before Step 3 (seed smoke) ────"; wait_for_a4500_idle
fi
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

# ─────────────── Step 7: export GGUF (STOCK converter + arch patch) ───────────────
# TWO defects in this llama.cpp checkout (see server_side/gguf_tools/README.md,
# diagnosed 2026-07-21) mean the plain export_lora_gguf.py produces UNLOADABLE
# GGUFs (arch=gemma3, transposed lora tensors). The recipe below reproduces
# D11's known-good orientation:
#   (1) stock converter — else-transpose reverted (convert_lora_STOCK.py in the
#       llama.cpp dir so convert_hf_to_gguf imports as sibling). get_lora_A_B()
#       already returns llama.cpp orientation; the local else re-transposed it.
#   (2) byte-patch general.architecture gemma3->gemma4 (no GEMMA4 arch constant
#       exists in this checkout; base model GGUF is gemma4, so adapter must be).
# KTO save is C.3-B composable → nested final_adapter/kto/ (has top-level
# config); SFT save is flat in final_adapter/.
STOCK_CONV="/home/exx/CYTu/llama.cpp/convert_lora_STOCK.py"
VENV_PY="/home/exx/CYTu/test_zone/gemma3-bbox-finetune/.venv/bin/python"
GBASE='$(python3 -c "from huggingface_hub import snapshot_download; print(snapshot_download('"'"'google/gemma-4-31b-it'"'"', local_files_only=True))")'
run 7 "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && GBASE=$GBASE && \
  $VENV_PY $STOCK_CONV $SFT_CKPT/final_adapter \
    --outfile data/lora_gguf/l2_A_ctrl_rat_sft/adapter.gguf --base \$GBASE && \
  $VENV_PY $STOCK_CONV $KTO_CKPT/final_adapter/kto \
    --outfile data/lora_gguf/l2_A_ctrl_rat_kto/adapter.gguf --base \$GBASE && \
  python3 server_side/gguf_tools/patch_arch_gemma3to4.py \
    data/lora_gguf/l2_A_ctrl_rat_sft/adapter.gguf \
    data/lora_gguf/l2_A_ctrl_rat_kto/adapter.gguf'"
# Step-7 completion assert — NOT just existence: verify arch=gemma4 AND
# ffn_down.lora_a=[21504,16] (the exact failure this step fixes). A gemma3 tag
# or [16,21504] orientation means the recipe regressed → HALT before eval.
if [ "$DRY_RUN" -eq 0 ] && [ 7 -le "$UNTIL" ] && [ "$SKIP_TO" -le 7 ]; then
  echo; echo "──── Step 7 assert: both GGUFs gemma4 + correct orientation ────"
  ok=$(ssh "$REMOTE_HOST" "cd $REMOTE_ROOT && for g in data/lora_gguf/l2_A_ctrl_rat_sft/adapter.gguf data/lora_gguf/l2_A_ctrl_rat_kto/adapter.gguf; do \
      python3 server_side/gguf_tools/read_gguf_meta.py \$g; done" 2>&1)
  echo "$ok" | grep -E '###|arch=|ffn_down'
  n_g4=$(echo "$ok" | grep -c 'arch=gemma4')
  n_orient=$(echo "$ok" | grep -c 'ffn_down.weight.lora_a  dims=\[21504, 16\]')
  if [ "$n_g4" = "2" ] && [ "$n_orient" = "2" ]; then
    echo "  ✓ both GGUFs gemma4 + [21504,16] (matches D11)"
  else
    echo "  ✗ GGUF arch/orientation wrong (gemma4=$n_g4/2, orient=$n_orient/2) — HALT."
    echo "    See server_side/gguf_tools/README.md. Do NOT eval broken adapters."
    exit 4
  fi
fi

# ─────────────── Step 8: 2-protocol eval (A4500 night window) ───────────────
# Freeze buffer snapshot for C_retrieval (tree-hash gate, Amendment 1a).
run "8.buffer_freeze" "mkdir -p $(dirname $FROZEN_BUFFER_TAR) && \
  tar --sort=name -czf $FROZEN_BUFFER_TAR -C $RECAP_BUFFER . && \
  ( cd $RECAP_BUFFER && find . -type f | sort | xargs sha256sum ) | sha256sum | awk '{print \$1}' > workspace/l2_audit/frozen_buffer.sha256 && \
  echo \"frozen L2 buffer tree_hash=\$(cat workspace/l2_audit/frozen_buffer.sha256)\""

# ── Permanent format-contract gate (Amendment 3 §7) ──
# BEFORE the simulator boots, prove the EVAL parser accepts the TRAINING
# target. This kills the train/eval-format-mismatch bug family (4th incident:
# L2 eval parsed both arms for a single-arm-trained model) at dry-run instead
# of at episode 1. Resident step; runs for every eval config.
if [ "$DRY_RUN" -eq 0 ] && [ "$SKIP_TO" -le 8 ] && [ 8 -le "$UNTIL" ]; then
  echo; echo "──── Step 8.contract — eval parser accepts training target? (scored_arm=left) ────"
  python3 scripts/diagnostics/check_eval_format_contract.py \
    --sft-jsonl "$SFT_JSONL" --level "$L2_LEVEL" \
    --scored-arm left --variant rationale --n 3 \
    || { echo "  ✗ format-contract FAILED — HALT (see Amendment 3 §7). Fix eval parser/template, not training data."; exit 5; }
fi

# Local A4500 eval steps — yield to LIBERO before the collects.
if [ "$DRY_RUN" -eq 0 ] && [ "$SKIP_TO" -le 8 ] && [ 8 -le "$UNTIL" ]; then
  echo; echo "──── A4500 yield-check before Step 8 (eval collects) ────"; wait_for_a4500_idle
fi

# reload student once with A_ctrl_rat's dual adapters (both protocols share weights)
run "8.reload" "ssh $REMOTE_HOST 'cd $REMOTE_ROOT && \
  bash server_side/reload_student_dual.sh \
    data/lora_gguf/l2_A_ctrl_rat_sft/adapter.gguf \
    data/lora_gguf/l2_A_ctrl_rat_kto/adapter.gguf'"

# NOTE (sequencing bug fixed): isaaclab.sh forks its python child and returns
# early, so the previous `nohup ... && echo` fired both protocols CONCURRENTLY
# (two Isaac sims racing one A4500 + interleaving on the --parallel 1 student).
# Both protocols now run FOREGROUND (no nohup, no &) so `run` blocks until each
# python truly exits — Protocol 2 cannot start until Protocol 1's 100 episodes
# finish. Amendment 3: --eval_scored_arm left (per-arm eval; right arm frozen).

# Protocol 1: A_ctrl_rat bare (no retrieval), left-scored
run "8.A_ctrl_rat.collect" "mkdir -p data/100ep-l2-A_ctrl_rat && \
  /home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --level $L2_LEVEL --num_episodes $L2_NUM_EPISODES \
    --teacher_url $STUDENT_URL --dump_images_root data/collect_dumps --freeze_level \
    --env_seed_base $L2_ENV_SEED_BASE --eval_template_variant rationale \
    --eval_scored_arm left \
    --headless --enable_cameras 2>&1 | tee logs/l2_eval_A_ctrl_rat_\$(date +%Y%m%d_%H%M%S).log && \
  echo 'L2 A_ctrl_rat eval done'"

# Protocol 2: C_retrieval (same weights + frozen re-tagged buffer, arm-aligned floor), left-scored
run "8.C_retrieval.collect" "mkdir -p data/100ep-l2-C_retrieval && \
  /home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --level $L2_LEVEL --num_episodes $L2_NUM_EPISODES \
    --teacher_url $STUDENT_URL --dump_images_root data/collect_dumps --freeze_level \
    --env_seed_base $L2_ENV_SEED_BASE --eval_template_variant rationale_with_retrieval \
    --recap_buffer_root $RECAP_BUFFER --use_memory --recap_buffer_readonly \
    --memory_success_label_arm left --eval_scored_arm left \
    --headless --enable_cameras 2>&1 | tee logs/l2_eval_C_retrieval_\$(date +%Y%m%d_%H%M%S).log && \
  echo 'L2 C_retrieval eval done'"

echo; echo "═══════════════════════════════════════════════════════════"
echo "  L2 Stage-1 done. Primary contrast: C_retrieval − A_ctrl_rat (identical-weights)."
echo "  Analyse via d11_mcnemar.py (run_ids param) + d11_exploratory.py (L2 R1 per-arm)."
echo "  Amendment 2 expansion criterion: sig+same-dir → Stage 2 (add A_action_only)."
echo "═══════════════════════════════════════════════════════════"
