#!/bin/bash
# Launch teacher llama-server with gemma-4-31B-it multimodal
# Deploy on remote server (135 GB VRAM)
#
# Prerequisites:
#   - llama.cpp compiled with CUDA support
#   - gemma-4-31B-it GGUF model downloaded
#   - mmproj-gemma4v projector file downloaded

set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/data/models/gemma-4-31B-it-Q4_K_M.gguf}"
MMPROJ_PATH="${MMPROJ_PATH:-/data/models/mmproj-gemma4v-f16.gguf}"
PORT="${TEACHER_PORT:-18888}"
CTX_SIZE="${CTX_SIZE:-16384}"  # Plan recommends 16384 (up from default 2048)

echo "=== Starting Teacher llama-server ==="
echo "Model:   ${MODEL_PATH}"
echo "MMProj:  ${MMPROJ_PATH}"
echo "Port:    ${PORT}"
echo "Context: ${CTX_SIZE}"

llama-server \
    --model "${MODEL_PATH}" \
    --mmproj "${MMPROJ_PATH}" \
    --port "${PORT}" \
    --ctx-size "${CTX_SIZE}" \
    --n-gpu-layers 99 \
    --host 0.0.0.0 \
    --parallel 2 \
    --verbose
