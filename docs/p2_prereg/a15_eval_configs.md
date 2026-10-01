# A15 inference-batch eval configs (prepared ahead of the amendment commit)

> Prepared 2026-10-01 ahead of the paper session's A15 (four-protocol inference
> batch). This records the exact eval invocations so that, once A15 lands on
> master, (a)+(b) can be queued as a 400-ep night batch and (c) the slope probe
> runs on CPU during the day. Build is not blocked; collect.py logic untouched.

## Baseline config: NO adapter + frozen buffer (pure base GGUF)

"No adapter" = the STUDENT server (student_url) serves the **base GGUF with no
LoRA adapter loaded** — this is a server-side choice (which model the
llama-server loads), not an eval-script flag. "Frozen buffer" = no new recaps
written during eval; retrieval (if any) reads a point-in-time snapshot only.

**Pure-base, no-memory eval (the A15 baseline arm):**
```bash
# Student server (on 148) must be launched serving the BASE GGUF, no adapter:
#   bash server/llama_server_student.sh   (with the base model path, no --lora)
# Then, per level:
PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
  scripts/05_eval.py \
  --level <L> --num_episodes <N> \
  --skip_teacher \
  --student_url http://10.80.9.148:18889 \
  --headless --enable_cameras
# NO --recap_buffer_root (→ no memory injection); frozen by omission.
```

## (a)+(b) 400-ep night batch — queue after A15 commit lands

The four protocols × levels/episode counts that sum to 400 are defined by the
A15 amendment (not yet on master). When it lands, each arm is an invocation of
the pattern above with its protocol-specific flags (adapter on/off,
--recap_buffer_root present/absent, --recap_buffer_readonly for the frozen
snapshot arm). Queue serially (single GPU) overnight.

**Pending A15:** the exact protocol→flag mapping. This doc is the harness; the
amendment supplies the protocol list. I will fill the concrete 4 invocations
when A15 commit is on master (the PI will re-ping).

## (c) R1' slope probe — CPU, daytime, on existing replay

The r-tracking slope probe runs on already-collected replay (no sim, no GPU):
```bash
PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python \
  scripts/analysis/p2_r_tracker.py --replay <existing_replay_dir> --slope
```
(confirm the exact p2_r_tracker flags against its --help before running; it is
the CPU slope/permutation estimator.)

## GPU scheduling note

A15 (a)+(b) are night batches on the single GPU; (c) is CPU daytime. Neither
conflicts with the WP1-③a push build (which uses the GPU interactively during
the day for short probe runs). The night batch starts after the build's last
daytime GPU run is clear.
