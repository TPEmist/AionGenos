#!/bin/bash
# Launch student llama-server with LoRA adapter
# Deploy on remote server alongside teacher

set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/data/models/gemma-4-31B-it-Q4_K_M.gguf}"
MMPROJ_PATH="${MMPROJ_PATH:-/data/models/mmproj-gemma4v-f16.gguf}"
LORA_PATH="${LORA_PATH:-}"  # Empty for initial startup (no LoRA yet)
PORT="${STUDENT_PORT:-18889}"
CTX_SIZE="${CTX_SIZE:-4096}"  # Student needs less context (no CoT)

echo "=== Starting Student llama-server ==="
echo "Model:  ${MODEL_PATH}"
echo "MMProj: ${MMPROJ_PATH}"
echo "LoRA:   ${LORA_PATH:-none}"
echo "Port:   ${PORT}"

LORA_FLAG=""
if [ -n "${LORA_PATH}" ]; then
    LORA_FLAG="--lora ${LORA_PATH}"
fi

llama-server \
    --model "${MODEL_PATH}" \
    --mmproj "${MMPROJ_PATH}" \
    ${LORA_FLAG} \
    --port "${PORT}" \
    --ctx-size "${CTX_SIZE}" \
    --n-gpu-layers 99 \
    --host 0.0.0.0 \
    --parallel 2 \
    --verbose
