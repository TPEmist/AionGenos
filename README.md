# AionGenos — Zero-Demonstration Cognitive Evolution for Embodied Intelligence

AionGenos breaks the dependency on human demonstrations (Behavior Cloning) in embodied AI.
A large VLA's world model acts as **System 2 (slow CoT reasoning)** to generate success
trajectories in simulation with **zero demonstrations**, then distills them into **System 1
(LoRA parametric intuition)** for O(1) inference latency.

> 📍 進度與決策追蹤請看 [`docs/plans/INDEX.md`](docs/plans/INDEX.md)
> 📋 完整 POC 計畫見 [`docs/plans/01_poc_cognitive_evolution_pipeline.md`](docs/plans/01_poc_cognitive_evolution_pipeline.md)

---

## Architecture

```
┌──────────────────────────────────┐  ┌──────────────────────────────────────┐
│ Local (RTX A4500) — Sim          │  │ Remote 10.80.9.148 (135 GB) — LLM    │
│                                  │  │                                      │
│ Process A: Collector (本機)      │  │ Process B-T: Teacher (:18888)        │
│  - IsaacLab + Arena              │  │  gemma-4-31B-it-GGUF multimodal      │
│  - 4-stage cognitive loop        │  │                                      │
│  - data/replays/{run_id}/...     │  │ Process B-S: Student (:18889)        │
│  - data/eval_dumps/...           │  │  base + LoRA GGUF (hot reload)       │
│                                  │  │                                      │
│  Eval: scripts/05_eval.py        │  │ Process C: Trainer (on-demand)       │
│  Collect: scripts/run_collect.py │  │  HF + peft QLoRA → GGUF export       │
└──────────────────────────────────┘  └──────────────────────────────────────┘
            │  rsync over SSH                ▲   POST /v1/lora-adapters
            └──────────────────►─────────────┘
```

## 4-Stage Cognitive Evolution Pipeline

| Stage | Name | Description |
|-------|------|-------------|
| **1** | Reasoning | VLM sees RGB + state → CoT → integer sub-goals |
| **2** | Attempt | IK servo executes sub-goals in sim |
| **3** | Learning | On failure: critic diagnoses using observable-only data (RGB + EE pose + distance, **no hidden sensors**) |
| **4** | Intuition | Success trajectories → QLoRA distillation → O(1) student |

## Curriculum (5 Levels)

| Lv | Task | Control | Status |
|----|------|---------|--------|
| L0 | Bimanual reach | Position-only (3-DoF × 2) | ✅ env ready, eval ongoing |
| L1 | Trajectory following | Position-only (3-DoF × 2) | ✅ env ready |
| L2 | Push block | Position + 2-DoF RPY | ✅ env ready |
| L3 | Pick & place | Position + RPY + gripper | ✅ env ready |
| L4 | Block handover | Full bimanual coordination | ⬜ Phase B |

Advance rule: success rate ≥ 60% unlocks next level.

---

## 🚀 Operating the System

四個獨立的能力區塊：**(A) 啟動 servers**、**(B) 跑 collect 收 success replay**、**(C) 跑 eval 比較 teacher vs student**、**(D) 觸發 train + reload**。

### Prerequisites

```bash
# 本機
cd /home/control/AionGenos
pip install -e ".[dev]"

# 確認 IsaacLab 可用
ls /home/control/IsaacLab/isaaclab.sh

# 確認遠端 SSH 通
ssh exx@10.80.9.148 "echo OK"
```

環境變數（預設值已寫進 `aiongenos/config.py`，這裡僅列可覆寫項）：

| 變數 | 預設 | 用途 |
|---|---|---|
| `TEACHER_URL` | `http://10.80.9.148:18888` | Stage 1/3 VLM endpoint |
| `STUDENT_URL` | `http://10.80.9.148:18889` | 蒸餾後 student endpoint |
| `LOCAL_REPLAY_PATH` | `./data/replays` | 本機 replay buffer 路徑 |
| `REMOTE_HOST` / `REMOTE_USER` | `10.80.9.148` / `exx` | 遠端 server |
| `REMOTE_REPLAY_PATH` | `~/CYTu/AionGenos_server/data/replays` | rsync 目的 |

---

### (A) 啟動 / 重啟遠端 servers

兩個 `llama-server` process 跑在遠端，腳本在 `server/` 下。

**Teacher (`:18888`)** — `ggml-org/gemma-4-31B-it-GGUF`，多模態 + CoT 開啟：

```bash
# 在遠端 10.80.9.148 上跑（不在本機）
ssh exx@10.80.9.148
cd ~/CYTu/AionGenos_server
bash server/llama_server_teacher.sh
# 關鍵 flag：--ctx-size 應 ≥ 16384（plan §M0 Q1；config 預設目前未強制）
```

**Student (`:18889`)** — base GGUF + LoRA adapter，**支援熱重載**：

```bash
# 在遠端 10.80.9.148 上跑
cd ~/CYTu/AionGenos_server
LORA_PATH=/path/to/adapter.gguf bash server/llama_server_student.sh
# 已實證跑通：
#   --split-mode none  (Vulkan 多 GPU 圖分割崩潰的解法)
#   --image-max-tokens 280
#   --ctx-size 4096
```

**健康檢查**：

```bash
curl -s http://10.80.9.148:18888/v1/models   # teacher 模型 id
curl -s http://10.80.9.148:18889/v1/models   # student 模型 id
curl -s http://10.80.9.148:18889/lora-adapters   # 確認 LoRA 已掛載
```

---

### (B) Collect — 跑 4-stage loop 收 success replay

```bash
cd /home/control/AionGenos
/home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --num_episodes 200 \
    --level 0 \
    --headless --enable_cameras
```

每 episode：Stage 1 (VLM 規劃) → Stage 2 (IK 執行) → 失敗則 Stage 3 (critic) → 寫入 replay。

**輸出**：

```
data/replays/{run_id}/
├── success/{ep_id}.json     # 成功 episode 含完整 trajectory + VLM thought
├── success/{ep_id}_start.png
├── success/{ep_id}_end.png
└── failure/{ep_id}.json     # 失敗 episode（保留供 Stage 3 critic + DPO 用）
```

> ⚠️ Curriculum 自動晉級：當前 level success rate ≥ 60% 自動 unlock 下一級；
> 12 hr collect 不到 100 success 會標 `curriculum_blocked` 並停 loop。
> 詳見 `aiongenos/curriculum/manager.py`。

---

### (C) Eval — multi-round closed-loop benchmark

跑 `scripts/05_eval.py` 在 IsaacLab 對 teacher / student endpoints 做 closed-loop 評估，
**eval 用 multi-round**（每 episode 內 VLM 看視覺反饋逐輪修正，不是 single-shot）。

```bash
cd /home/control/AionGenos

# 完整：5 ep × {teacher, student}，dump 全部 round 的 RGB pre/post + meta.json
/home/control/IsaacLab/isaaclab.sh -p scripts/05_eval.py \
    --num_episodes 5 \
    --level 0 \
    --sim_steps 600 \
    --dump_images \
    --headless --enable_cameras

# 只跑 teacher：
/home/control/IsaacLab/isaaclab.sh -p scripts/05_eval.py \
    --num_episodes 5 --level 0 --sim_steps 600 --skip_student \
    --headless --enable_cameras
```

**主要 flag**：

| Flag | 說明 |
|---|---|
| `--num_episodes N` | 評估 episode 數（每端點） |
| `--level 0..4` | curriculum level |
| `--sim_steps 600` | 每 sub-goal IK servo step 數（60 = 1s, 600 = 10s） |
| `--skip_teacher` / `--skip_student` | 只跑單端點 |
| `--dump_images` | 每 round 存 `pre.png` + `post.png` + `meta.json`（含 VLM thought / GT / dist） |
| `--dump_root data/eval_dumps` | dump 根目錄（預設） |

**輸出 (with `--dump_images`)**：

```
data/eval_dumps/L{level}_{stamp}/
├── teacher/ep_001_xxxxxx/
│   ├── round_01_pre.png   # VLM 看的圖
│   ├── round_01_post.png  # IK 執行完的圖
│   ├── round_02_pre.png   ...
│   └── meta.json          # per-round VLM 預測 / GT / dist / thought
└── student/ep_001_xxxxxx/...
```

**Multi-round 終止條件**：
1. 雙臂 final_dist 都 < `subgoal_success_threshold_m` (5cm) → success
2. VLM 自己輸出 `STOP=true` → vlm_stop
3. 連 `plateau_patience` (2) round best_combined 進步 < `plateau_min_progress_m` (1cm) → plateau
4. 達到 `max_subgoals_per_episode` (L0=4) → max_rounds

詳細結構在 `aiongenos/orchestrator/eval.py:_run_episode`，對應 config 在 `aiongenos/config.py:LevelConfig`。

---

### (D) Train + Reload — Stage 4 distillation pipeline

把本機 success replay sync 到遠端、觸發 QLoRA fine-tune、轉 GGUF、reload student server。
**全部一鍵 in `scripts/04_sync_and_train.sh`**：

```bash
cd /home/control/AionGenos

# 用最新 run_id（自動偵測 data/replays/ 下最新目錄）：
python3 scripts/04_sync_and_train.sh --base-model google/gemma-4-E4B-it

# 指定 run_id + SSH key：
python3 scripts/04_sync_and_train.sh \
    --run-id 20260603-e4b-r1 \
    --base-model google/gemma-4-E4B-it \
    --ssh-key ~/.ssh/aiongenos_remote
```

**底層三步**（在 `aiongenos/replay/sync.py` + `aiongenos/pipeline/stage4_distill_remote_trigger.py`）：

1. **rsync** local replay → remote `~/CYTu/AionGenos_server/data/replays/{run_id}/`
2. **SSH 觸發遠端 QLoRA training**（`server_side/train_qlora_gemma4.py`）
   - 限制 LoRA `target_modules` 避開音頻塔（plan 已實證 fix）
   - 4-bit quant base + rank=16 LoRA
3. **SSH 觸發遠端 export + reload**（`server_side/export_lora_gguf.py` + `reload_student.sh`）
   - `convert_lora_to_gguf.py`（需 patch `model.language_model.` prefix，已修）
   - 重啟 `:18889` 加 `--lora <new_path>`
   - 預期 30s downtime（POC 接受，Phase B 換 vLLM）

**Reload 完成驗證**：

```bash
curl -s http://10.80.9.148:18889/lora-adapters | jq
# 應看到新 LoRA path
```

---

## 🔁 完整 POC 一輪流程（從零到 student 上線）

```bash
# 0. 確認 servers 健康（A）
curl -s http://10.80.9.148:18888/v1/models
curl -s http://10.80.9.148:18889/v1/models

# 1. Smoke test
python3 scripts/00_smoke_vlm.py
bash scripts/01_smoke_isaaclab.sh

# 2. Collect 一輪 success replay（B）
/home/control/IsaacLab/isaaclab.sh -p scripts/run_collect.py \
    --num_episodes 200 --level 0 --headless --enable_cameras

# 3. 確認 success replay 數量
ls data/replays/$(ls -t data/replays | head -1)/success/ | wc -l   # 預期 ≥ 100

# 4. Sync + train + reload student（D）
python3 scripts/04_sync_and_train.sh --base-model google/gemma-4-E4B-it

# 5. Eval 比較 teacher vs student（C）
/home/control/IsaacLab/isaaclab.sh -p scripts/05_eval.py \
    --num_episodes 10 --level 0 --sim_steps 600 \
    --dump_images --headless --enable_cameras

# 6. 看結果（terminal 會印 distillation gap）
# - SR ratio (student / teacher) ≥ 0.70 為 M5 達標
# - Latency ratio ≤ 0.13 為 M5 達標（200ms / 1500ms）
# - 視覺檢查：開啟 data/eval_dumps/L0_*/teacher/ep_*/round_NN_pre.png
```

---

## 🧪 當前狀態速覽（2026-06-04）

- **跑通**：multi-round eval (Q5 Option A)、E4B+LoRA student 熱重載、L0-L3 環境
- **Open question**：L0 SR=0/5 — 已用 image dump + thought 分析發現根因是
  **VLM 把螢幕座標當成 robot base frame**（紅 cube 在畫面左 → VLM 估 X=-30，
  但 base frame 中該 cube 真實 X=+25）
- **方向（user 哲學澄清）**：禁止 prompt 注入軸向（違反 task-agnostic 原則），改用
  **拉高 round 上限 + Stage 3 critic 給 observable feedback** 讓 VLM 自學。詳見
  [`docs/plans/INDEX.md`](docs/plans/INDEX.md) TODO `T-1`。

---

## Key Design Principles

1. **Zero demonstrations** — No human teleoperation data ever used
2. **Inference/training separation** — Sim and gradient updates in separate processes
3. **Scalar guard** — All coordinates as normalized integers [-100, 100], no floats for LLM
4. **Curriculum-driven** — Same codebase, same prompts across all difficulty levels
5. **Observable-only critic** — Stage 3 never uses hidden sensors
6. **Task-agnostic learning** — 不在 prompt 注入任務特定知識（如座標軸定義）；
   靠 multi-round + critic feedback 讓 VLM 自學

## Project Structure

```
AionGenos/
├── aiongenos/
│   ├── config.py              # LevelConfig, ScalarGuard, CurriculumConfig
│   ├── vlm/                   # client (httpx), prompts, parser, scalar_guard
│   ├── control/               # Rotation (RPY↔quat), command_converter
│   ├── replay/                # Episode schema, buffer, rsync
│   ├── curriculum/            # ladder, manager, arena_adapter
│   ├── pipeline/              # stage1_reasoning, stage2_attempt, stage3_critic, stage4_distill_remote_trigger
│   ├── orchestrator/          # collect, eval (multi-round), isaaclab_env_interface
│   ├── eval/                  # metrics (SR, latency, distillation gap)
│   └── tasks/                 # IsaacLab env configs L0-L3
├── scripts/
│   ├── 00_smoke_vlm.py        # M0 grounding sanity
│   ├── 01_smoke_isaaclab.sh   # M0 sim launch check
│   ├── 04_sync_and_train.sh   # Stage 4 一鍵 sync+train+reload
│   ├── 05_eval.py             # multi-round eval (含 --dump_images)
│   └── run_collect.py         # 4-stage collect loop
├── server/                    # llama-server 啟動腳本（teacher / student）
├── server_side/               # 遠端訓練腳本（train_qlora / export_lora_gguf / reload_student）
├── docs/plans/                # POC 計畫全文 + INDEX 進度追蹤
└── data/
    ├── replays/{run_id}/...   # collect 輸出
    └── eval_dumps/{stamp}/... # eval --dump_images 輸出
```

## License

Unknown
