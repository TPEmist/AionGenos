# Development Tracking — Terminal Cheat Sheet

This is the reference for monitoring AionGenos training/evaluation jobs from a
plain terminal. No Claude / agent loop needed.

Conventions used everywhere below:

- Long-running collect/eval processes are launched in the background with
  `nohup ... &`. We persist two pointer files per job to `/tmp` so any
  shell can find the process and its log later:
  - `/tmp/aiongenos_<TAG>_pid.txt` — the PID (one number, one line)
  - `/tmp/aiongenos_<TAG>_log.txt` — absolute path to the run's log file
- `<TAG>` is a short label (e.g. `v4c3`, `v3`, `v4pb`). When launching a new
  background job, pick a fresh tag and write both files; the recipes below
  read whichever one you ask about.
- Replays land under `data/replays/{run_id}/{success,failure}/*.json` with a
  pair of `*_start.png` / `*_end.png` PNGs.
- Per-round playback dumps (when `--dump_images_root` is passed to
  `run_collect.py`) land under `data/collect_dumps/{run_id}/{ep_id}/`.

---

## 1. Is anything running right now?

```bash
ps -ef | grep -E "run_collect|run_eval|isaaclab.*scripts" | grep -v grep
```

Empty → nothing alive. With output → that's the process(es) currently using
Isaac Sim.

## 2. Track a specific job by tag

Find tags:

```bash
ls /tmp/aiongenos_*_pid.txt
```

Then for one of them (example `TAG=v4c3`):

```bash
TAG=v4c3
PID=$(cat /tmp/aiongenos_${TAG}_pid.txt)
LOG=$(cat /tmp/aiongenos_${TAG}_log.txt)

ps -p "$PID" -o pid,etime,stat,pcpu,pmem    # alive? for how long?
echo "Log: $LOG"
```

`ps` empty output ⇒ process exited. `etime` is wall-clock since launch
(`HH:MM:SS` or `D-HH:MM:SS`).

## 3. Episode / round progress (from the log)

```bash
LOG=$(cat /tmp/aiongenos_v4c3_log.txt)

# follow the log live (Ctrl-C to stop watching, doesn't affect the job)
tail -f "$LOG"

# all per-round VLM events, no Isaac Sim spam
grep -E "Episode|Round|outcome|grounding|Critic Feedback|Stage 1 OK" "$LOG" | tail -20

# how many VLM calls so far?
grep -c "Stage 1 OK" "$LOG"
```

## 4. Replay landing

```bash
# newest run on disk
LATEST=$(ls -t data/replays/ | head -1); echo "Run: $LATEST"

# count of episodes for that run
ls data/replays/$LATEST/success/*.json 2>/dev/null | wc -l
ls data/replays/$LATEST/failure/*.json 2>/dev/null | wc -l

# all runs sorted newest-first
ls -lt --time-style=full-iso data/replays/ | head -10
```

## 5. Diagnostics on a finished run

```bash
RUN=0602e905   # whatever run id you want to inspect

# round-by-round table + aggregate (steps_per_round = LevelConfig.sim_steps_per_subgoal,
# currently 30; pass whatever the run actually used)
python3 scripts/diagnostics/replay_summary.py --run $RUN --steps_per_round 30

# only summary (no per-round detail)
python3 scripts/diagnostics/replay_summary.py --run $RUN --steps_per_round 30 --episodes_only

# initial-EE pose diversity (T-8a sanity)
python3 scripts/diagnostics/check_ee_randomness.py --run $RUN

# reasoning trace (axis token usage, thought similarity, coord volatility)
# defaults to latest dump, or pass --run / --episode
python3 scripts/diagnostics/reasoning_analysis.py --dump_root data/collect_dumps
python3 scripts/diagnostics/reasoning_analysis.py --dump_root data/collect_dumps --show_thoughts
python3 scripts/diagnostics/reasoning_analysis.py --dump_root data/collect_dumps --show_critic
```

## 6. View an episode's per-round images

```bash
RUN=0602e905
EP=$(ls -t data/collect_dumps/$RUN/ | head -1)

# files for that episode (start, end, round_NN_pre/post, meta.json)
ls data/collect_dumps/$RUN/$EP/

# image viewer (pick whichever is installed)
xdg-open data/collect_dumps/$RUN/$EP/round_01_pre.png
feh data/collect_dumps/$RUN/$EP/round_*_pre.png
eog data/collect_dumps/$RUN/$EP/round_05_post.png

# text playback (round-by-round VLM I/O paired with PNG paths)
python3 scripts/diagnostics/playback_episode.py --dump_root data/collect_dumps --run $RUN --episode $EP
```

## 7. Server health & LoRA mount

```bash
curl -s http://10.80.9.148:18888/health             # teacher
curl -s http://10.80.9.148:18889/health             # student
curl -s http://10.80.9.148:18889/lora-adapters      # should list 410e0f79
curl -s http://10.80.9.148:18888/props \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('teacher n_ctx=', d['default_generation_settings']['n_ctx'])"
```

If `/lora-adapters` returns `[]`, re-mount via the server-side reload script:

```bash
ssh exx@10.80.9.148 'cd /home/exx/CYTu/AionGenos_server && bash server_side/reload_student.sh /home/exx/CYTu/AionGenos_server/data/lora_gguf/410e0f79/adapter.gguf'
```

## 8. Git status

```bash
git log --oneline -10
git status -s
git log --since="3 days ago" --oneline
git diff --stat HEAD~1..HEAD       # what changed in the last commit
```

## 9. One-shot status snapshot

Paste this whole block when you want the full picture in one screen:

```bash
{
  echo "=== Time: $(date) ==="

  echo "=== Active sim/collect processes ==="
  ps -ef | grep -E "run_collect|run_eval|isaaclab.*scripts" | grep -v grep \
    || echo "(none)"

  echo "=== Pointer-tracked jobs ==="
  for p in /tmp/aiongenos_*_pid.txt; do
    [ -e "$p" ] || continue
    tag=$(basename "$p" _pid.txt | sed 's/^aiongenos_//')
    pid=$(cat "$p")
    if ps -p "$pid" >/dev/null 2>&1; then
      etime=$(ps -p "$pid" -o etime= | tr -d ' ')
      echo "  $tag: pid=$pid ALIVE ($etime)"
    else
      echo "  $tag: pid=$pid exited"
    fi
  done

  echo "=== Latest replay run ==="
  LATEST=$(ls -t data/replays/ 2>/dev/null | head -1)
  echo "  $LATEST"
  if [ -n "$LATEST" ]; then
    s=$(ls data/replays/$LATEST/success/*.json 2>/dev/null | wc -l)
    f=$(ls data/replays/$LATEST/failure/*.json 2>/dev/null | wc -l)
    echo "  success=$s  failure=$f"
  fi

  echo "=== Endpoints ==="
  curl -s --max-time 3 http://10.80.9.148:18888/health || echo "(teacher down)"
  echo
  curl -s --max-time 3 http://10.80.9.148:18889/health || echo "(student down)"
  echo

  echo "=== Last 3 commits ==="
  git log --oneline -3
} 2>&1
```

Save it as a shell function if you do this often:

```bash
# ~/.bashrc
aiongenos_status() {
  cd /home/control/AionGenos && {
    # paste the block above
    :
  }
}
```

## 10. When something is stuck

- **VLM call hung** (e.g. teacher unresponsive but `ps` says process alive):
  the process will eventually time out (`DEFAULT_TIMEOUT=300s` per call,
  `MAX_RETRIES=2`) and either resume or fail the round. If you want to bail
  out early: `kill <PID>` (gentle) or `kill -9 <PID>` (hard). Replay JSONs
  for already-completed episodes are persisted, so a kill mid-run only
  loses the in-flight episode.

- **Disk space**: `du -sh data/replays/ data/collect_dumps/ data/eval_dumps/ logs/`
  — replays + dumps grow ~20-40 MB per episode (PNGs dominate).

- **GPU stuck**: `nvidia-smi`. If the local A4500 is pinned at 100% with no
  active sim process, that's typically a leftover kit-app worker; restart
  the shell or reboot the machine.

- **Permissions / mid-run repair of a JSON file**: replays are plain JSON,
  hand-editable. Done once already (see commit `53948b4` notes).

---

## Job-launch templates (copy-paste)

### A. Background L0a-Left collect with image dump

```bash
TAG=v4c3
LOG=logs/v4_C3_$(date +%Y%m%d_%H%M%S).log
PYTHONUNBUFFERED=1 nohup /home/control/IsaacLab/isaaclab.sh -p \
  scripts/run_collect.py --num_episodes 5 --level=-2 \
  --dump_images_root data/collect_dumps \
  --headless --enable_cameras > "$LOG" 2>&1 &
PID=$!
echo "$PID" > /tmp/aiongenos_${TAG}_pid.txt
echo "$LOG" > /tmp/aiongenos_${TAG}_log.txt
echo "Launched $TAG  pid=$PID  log=$LOG"
```

(Change `--level=-2` to `0..4` for other levels; `-1` for L0a-Right.)

### B. View-sanity (no VLM, just RGB dump under different reset poses)

```bash
TAG=vs
LOG=logs/view_sanity_$(date +%Y%m%d_%H%M%S).log
PYTHONUNBUFFERED=1 nohup /home/control/IsaacLab/isaaclab.sh -p \
  scripts/diagnostics/view_sanity.py \
  --out_dir data/view_sanity_dumps \
  --num_resets_per_pose 3 \
  --camera_preset default \
  --headless --enable_cameras > "$LOG" 2>&1 &
PID=$!
echo "$PID" > /tmp/aiongenos_${TAG}_pid.txt
echo "$LOG" > /tmp/aiongenos_${TAG}_log.txt
```

### C. Stop a job cleanly

```bash
TAG=v4c3
PID=$(cat /tmp/aiongenos_${TAG}_pid.txt)
kill "$PID"                # SIGTERM, gives Isaac Sim time to flush
sleep 5
ps -p "$PID" >/dev/null 2>&1 && kill -9 "$PID"   # if still alive
```
