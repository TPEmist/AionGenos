#!/bin/bash
# Reload student llama-server (port 18889) serving the BASE GGUF with NO LoRA
# adapter (D11 Amendment 15 protocol (a)). Identical launch flags to
# reload_student_dual.sh except --lora is omitted — a restart, not a scale-0
# hot-swap, so "no adapter" is unambiguous.
#
# Usage:
#   bash reload_student_base.sh
#
# Env:
#   MODEL_PATH   : base GGUF path (default: gemma-4-31B Q4_K_M)
#   MMPROJ_PATH  : projector path
#   STUDENT_PORT : port (default 18889)
#   CTX_SIZE     : context (default 16384)

set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_gemma-4-31B-it-Q4_K_M.gguf}"
MMPROJ_PATH="${MMPROJ_PATH:-/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_mmproj-gemma-4-31B-it-Q8_0.gguf}"
PORT="${STUDENT_PORT:-18889}"
CTX_SIZE="${CTX_SIZE:-16384}"

echo "=== Reloading Student server (BASE, no adapter) ==="
echo "Model:    $MODEL_PATH"
echo "MMProj:   $MMPROJ_PATH"
echo "Port:     $PORT"
echo "CTX:      $CTX_SIZE"
echo "Adapters: none"

# Kill any existing student
if pgrep -f "llama-server.*--port $PORT" >/dev/null; then
    echo
    echo "Stopping existing llama-server on port $PORT..."
    pkill -f "llama-server.*--port $PORT" || true
    sleep 3
fi

LLAMA_SERVER_BIN="/home/linuxbrew/.linuxbrew/bin/llama-server"
if [ ! -x "$LLAMA_SERVER_BIN" ]; then
    LLAMA_SERVER_BIN="/home/exx/CYTu/llama.cpp/build/bin/llama-server"
fi
if [ ! -x "$LLAMA_SERVER_BIN" ]; then
    LLAMA_SERVER_BIN="llama-server"
fi

mkdir -p data/logs
LOG_FILE="data/logs/student_reload_base_$(date +%Y%m%d_%H%M%S).log"

echo
echo "Launching student server..."
nohup "$LLAMA_SERVER_BIN" \
    --model "$MODEL_PATH" \
    --mmproj "$MMPROJ_PATH" \
    --port "$PORT" \
    --ctx-size "$CTX_SIZE" \
    --n-gpu-layers 99 \
    --split-mode none \
    --image-max-tokens 280 \
    -fa on \
    --reasoning off \
    --reasoning-budget 0 \
    --host 0.0.0.0 \
    --parallel 1 \
    > "$LOG_FILE" 2>&1 &
STUDENT_PID=$!
echo "Student PID: $STUDENT_PID (log: $LOG_FILE)"

# Wait for health check
echo -n "Waiting for /health OK..."
for i in $(seq 1 24); do
    sleep 5
    CODE=$(curl -s --max-time 3 -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/health" 2>/dev/null || echo "000")
    if [ "$CODE" = "200" ]; then
        echo " READY (after $((i * 5))s)"
        break
    fi
    echo -n "."
done

if [ "$CODE" != "200" ]; then
    echo
    echo "ERROR: student did not come up. Last log lines:"
    tail -20 "$LOG_FILE"
    exit 1
fi

# Verify adapter list from /lora-adapters endpoint
echo
echo "=== Loaded adapters (from /lora-adapters) ==="
curl -s "http://127.0.0.1:$PORT/lora-adapters" | python3 -m json.tool 2>/dev/null || \
    curl -s "http://127.0.0.1:$PORT/lora-adapters"
if curl -s "http://127.0.0.1:$PORT/lora-adapters" | grep -q '"path"'; then
    echo "ERROR: adapters present on a base-only server" >&2
    exit 1
fi
echo
echo "Reload complete (base, no adapter verified)."
