#!/bin/bash
# Launch teacher llama-server with gemma-4-31B-it multimodal
# Deploy on remote server (135 GB VRAM)
#
# Prerequisites:
#   - llama.cpp compiled with CUDA support
#   - gemma-4-31B-it GGUF model downloaded
#   - mmproj-gemma4v projector file downloaded

set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_gemma-4-31B-it-Q4_K_M.gguf}"
MMPROJ_PATH="${MMPROJ_PATH:-/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_mmproj-gemma-4-31B-it-Q8_0.gguf}"
PORT="${TEACHER_PORT:-18888}"
CTX_SIZE="${CTX_SIZE:-16384}"  # Plan recommends 16384 (up from default 2048)

echo "=== Starting Teacher llama-server ==="
echo "Model:   ${MODEL_PATH}"
echo "MMProj:  ${MMPROJ_PATH}"
echo "Port:    ${PORT}"
echo "Context: ${CTX_SIZE}"

LLAMA_SERVER_BIN="/home/linuxbrew/.linuxbrew/bin/llama-server"
if [ ! -x "${LLAMA_SERVER_BIN}" ]; then
    LLAMA_SERVER_BIN="/home/exx/CYTu/llama.cpp/build/bin/llama-server"
fi
if [ ! -x "${LLAMA_SERVER_BIN}" ]; then
    LLAMA_SERVER_BIN="llama-server"
fi

# Reasoning OFF for the teacher: gemma-4's reasoning mode consumes the
# entire output budget on reasoning_content and returns EMPTY content for
# the reflective Stage-4 recap prompt (confirmed 2026-07-14: finish_reason
# "length", completion_tokens=400 all reasoning, content len 0). Stage-1
# terse calls survive reasoning-on, but Stage-4 recap generation does not,
# so every recap silently returned None. The D11 student ran reasoning-off
# for the same reason; the teacher must too for recaps to generate.
"${LLAMA_SERVER_BIN}" \
    --model "${MODEL_PATH}" \
    --mmproj "${MMPROJ_PATH}" \
    --port "${PORT}" \
    --ctx-size "${CTX_SIZE}" \
    --n-gpu-layers 99 \
    --reasoning off \
    --reasoning-budget 0 \
    --host 0.0.0.0 \
    --parallel 1 \
    --verbose
