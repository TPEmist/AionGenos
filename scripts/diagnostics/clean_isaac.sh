#!/bin/bash
# Kill stray isaac diagnostic procs + assert GPU clear. Always exits 0 on a
# successful clean (the recurring footgun: pkill/xargs returning nonzero
# broke && chains / compound commands). Use standalone, never in an && chain.
# Exits 3 only if the GPU is STILL busy after cleanup (a real problem).
set +e
mapfile -t PIDS < <(pgrep -f 'env_isaaclab/bin/python' 2>/dev/null | while read -r p; do
  if tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -qE 'wp1_osc|check_env_seed|osc_'; then echo "$p"; fi
done)
[ "${#PIDS[@]}" -gt 0 ] && { echo "[clean] killing: ${PIDS[*]}"; kill -9 "${PIDS[@]}" 2>/dev/null; sleep 3; }
bash /home/control/AionGenos/scripts/diagnostics/assert_gpu_clear.sh
exit $?
