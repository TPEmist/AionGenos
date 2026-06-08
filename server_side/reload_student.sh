#!/bin/bash
# Reload student llama-server with the new LoRA adapter
# Usage: bash reload_student.sh /path/to/adapter.gguf

set -euo pipefail

LORA_PATH="${1:-}"
PORT="${STUDENT_PORT:-18889}"
LOG_DIR="data/logs"

if [ -z "${LORA_PATH}" ]; then
    echo "Error: No LoRA adapter path provided." >&2
    echo "Usage: bash reload_student.sh /path/to/adapter.gguf" >&2
    exit 1
fi

echo "=== Reloading Student Server ==="
echo "LoRA adapter: ${LORA_PATH}"
echo "Port:         ${PORT}"

# 1. Ensure log directory exists
mkdir -p "${LOG_DIR}"

# 2. Kill existing student server running on this port
echo "Stopping any llama-server running on port ${PORT}..."
pkill -f "llama-server.*--port ${PORT}" || true
if command -v fuser &>/dev/null; then
    fuser -k "${PORT}/tcp" || true
fi

# Give it a moment to release the port
sleep 2

# 3. Locate student launch script
LAUNCH_SCRIPT="server/llama_server_student.sh"
if [ ! -f "${LAUNCH_SCRIPT}" ]; then
    LAUNCH_SCRIPT="../server/llama_server_student.sh"
fi
if [ ! -f "${LAUNCH_SCRIPT}" ]; then
    LAUNCH_SCRIPT="$(dirname "$0")/../server/llama_server_student.sh"
fi

if [ ! -f "${LAUNCH_SCRIPT}" ]; then
    echo "Error: Could not locate server/llama_server_student.sh" >&2
    exit 1
fi

# 4. Start student server in background
echo "Launching student server via ${LAUNCH_SCRIPT}..."
export LORA_PATH="${LORA_PATH}"
export STUDENT_PORT="${PORT}"

nohup bash "${LAUNCH_SCRIPT}" > "${LOG_DIR}/student_reload.log" 2>&1 &

echo "Student server spawned in background. Logs: ${LOG_DIR}/student_reload.log"
sleep 2

# 5. Check if it is running
if pgrep -f "llama-server.*--port ${PORT}" >/dev/null; then
    echo "Student server reload initiated successfully."
else
    echo "Warning: Student server process does not appear to be running." >&2
    echo "Please check ${LOG_DIR}/student_reload.log for errors." >&2
fi
