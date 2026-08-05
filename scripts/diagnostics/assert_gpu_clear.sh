#!/bin/bash
# Mechanical gate (WP1 diagnosis lesson, 2026-08-05): before launching any
# IsaacLab job, ASSERT the GPU has zero compute-apps — do not trust the eye.
# Same guard philosophy as "a wait must have an alarm": a cleanup must have
# an assertion. Exits 0 if clear, 3 (HALT) if any compute-app is live.
#
# Usage: bash scripts/diagnostics/assert_gpu_clear.sh && <launch isaac job>
set -uo pipefail
n=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -c '[0-9]')
n=${n:-0}
if [ "$n" -eq 0 ]; then
  echo "[gpu-gate] ✓ 0 compute-apps — clear to launch"
  exit 0
fi
echo "[gpu-gate] ✗ $n compute-app(s) still live — HALT (clean leftovers first):"
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null | sed 's/^/    /'
exit 3
