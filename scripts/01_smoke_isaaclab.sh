#!/bin/bash
# M0 Smoke Test: Isaac Lab headless 100-step run
# Verifies IsaacLab + OpenArm Bi-reach works without crash.
#
# Usage:
#   bash scripts/01_smoke_isaaclab.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ISAACLAB_DIR="${HOME}/IsaacLab"

echo "=== AionGenos M0: Isaac Lab Smoke Test ==="
echo "IsaacLab dir: ${ISAACLAB_DIR}"

if [ ! -d "${ISAACLAB_DIR}" ]; then
    echo "❌ IsaacLab not found at ${ISAACLAB_DIR}"
    exit 1
fi

echo "Running Isaac-Reach-OpenArm-Bi-v0 headless for 100 steps..."

cd "${ISAACLAB_DIR}"

# Use isaaclab.sh to run with the correct Python/conda env
./isaaclab.sh -p -m isaaclab.scripts.run_env \
    --task "Isaac-Reach-OpenArm-Bi-v0" \
    --num_envs 2 \
    --headless \
    --max_iterations 100 \
    2>&1 | tail -20

EXIT_CODE=${PIPESTATUS[0]}

if [ ${EXIT_CODE} -eq 0 ]; then
    echo "✅ Isaac Lab smoke test PASSED"
else
    echo "❌ Isaac Lab smoke test FAILED (exit code: ${EXIT_CODE})"
    exit 1
fi
