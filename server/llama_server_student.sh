#!/bin/bash
# Launch student llama-server with LoRA adapter
# Deploy on remote server alongside teacher

set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_gemma-4-31B-it-Q4_K_M.gguf}"
MMPROJ_PATH="${MMPROJ_PATH:-/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_mmproj-gemma-4-31B-it-Q8_0.gguf}"
LORA_PATH="${LORA_PATH:-}"  # Empty for initial startup (no LoRA yet)
PORT="${STUDENT_PORT:-18889}"
CTX_SIZE="${CTX_SIZE:-16384}"  # Match teacher. 4K was fine for single-shot
                               # eval, but multi-round closed-loop with
                               # EpisodeConversation blows past 4K after ~3
                               # rounds → 400 Bad Request. Run 54acddc2
                               # (D7 attempt 1) parse-failed 20/20 ep at R4
                               # before this default got raised.

echo "=== Starting Student llama-server ==="
echo "Model:  ${MODEL_PATH}"
echo "MMProj: ${MMPROJ_PATH}"
echo "LoRA:   ${LORA_PATH:-none}"
echo "Port:   ${PORT}"

LORA_FLAG=""
if [ -n "${LORA_PATH}" ]; then
    LORA_FLAG="--lora ${LORA_PATH}"
fi

LLAMA_SERVER_BIN="/home/linuxbrew/.linuxbrew/bin/llama-server"
if [ ! -x "${LLAMA_SERVER_BIN}" ]; then
    LLAMA_SERVER_BIN="/home/exx/CYTu/llama.cpp/build/bin/llama-server"
fi
if [ ! -x "${LLAMA_SERVER_BIN}" ]; then
    LLAMA_SERVER_BIN="llama-server"
fi

"${LLAMA_SERVER_BIN}" \
    --model "${MODEL_PATH}" \
    --mmproj "${MMPROJ_PATH}" \
    ${LORA_FLAG} \
    --port "${PORT}" \
    --ctx-size "${CTX_SIZE}" \
    --n-gpu-layers 99 \
    --split-mode none \
    --image-max-tokens 280 \
    -fa on \
    --reasoning off \
    --reasoning-budget 0 \
    --host 0.0.0.0 \
    --parallel 2 \
    --verbose

