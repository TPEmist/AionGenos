# AionGenos POC — Cognitive Evolution Pipeline on IsaacLab-Arena

## Context

AionGenos 是一個開源研究框架，目標是打破具身智能對人類示範（Behavior Cloning）的依賴。核心思想是把大型 VLA 的世界模型 / 物理常識當作 **System 2（慢速 CoT 推論）**，在 Isaac Lab 模擬器中以 **零示範（Zero-Demonstration）** 方式產生成功軌跡，最後蒸餾進 **System 1（LoRA 直覺反射）**，達成 $O(1)$ 推論延遲的「參數化直覺」。

**重點原則（使用者明訂）**：
1. **無示範原則**：禁止任何人類操作軌跡資料集（不引 Open-X / LeRobot Hub / RoboCasa demos / RoboTwin 自帶 demo set）。
2. **推論與訓練分離**：物理模擬與梯度更新必須在獨立 process / machine，透過 Replay Buffer 交換。
3. **標量防護**：所有座標走歸一化整數 grid，不讓 LLM 看到原始浮點。
4. **Curriculum-driven 通用 loop**：POC 目標不是「解一個任務」，而是「證明 4-stage loop 在難度遞增的 N 個任務上都能 self-bootstrap」。
5. **Benchmark 化**：掛在公開可比的 **IsaacLab-Arena**（NVIDIA 官方，alpha v0.2.1）+ RoboTwin 2.0 dual-arm 整合，產出可被外人驗證的數字。

### 已驗證的環境事實（清楚分本機 / 遠端）

| 元件 | 位置 | 狀態 |
|---|---|---|
| **VLM Teacher Server** | 遠端 `10.80.9.148:18888` | `gemma-4-31B-it-GGUF`，多模態 OK；JSON / 空間 grounding 已測通（紅 quadrant→`[-0.5,0.5]`、藍→`[0.5,-0.5]`）；`n_ctx=2048` 偏緊（建議調為 16384）；外部 URL 抓圖失敗，必須 base64 |
| **遠端 Server VRAM** | 135 GB（user 確認） | 足以做 Gemma-4-31B QLoRA + 同時跑 teacher + student llama-server（peft #3129 確認 Gemma-4 QLoRA 路徑可行；`convert_lora_to_gguf.py` 對純 LM-head adapter OK） |
| **本機 GPU** | RTX A4500 20 GB（18 GB free） | **本機只負責 Isaac Sim 視覺化 / 模擬**；不做 LoRA 訓練；CUDA 12.9 + PyTorch 2.7.1 已就緒 |
| **Isaac Lab** | 本機 `~/IsaacLab` | 已裝、`Isaac-Reach-OpenArm-Bi-v0` 可起；`CurriculumTermCfg` API stable；含 `modify_reward_weight` / `modify_env_param` / `modify_term_cfg` 三個 utility |
| **IsaacLab-Arena** | 待裝 (`github.com/isaac-sim/IsaacLab-Arena`，pin `release/0.2.1`) | 官方確認存在（418⭐，2026-05 active），Docker-only，是 meta-platform；自帶 RoboTwin 2.0 整合分支（50 dual-arm tasks）。Arena 本身**沒有** curriculum → 本 POC 的貢獻面就是補上 curriculum |

---

## 1. 系統拓撲（雙機器，三 process）

```
┌─────────────────────────────────────────────┐  ┌─────────────────────────────────────────────────┐
│ 本機 (RTX A4500 20 GB) — Sim Workstation     │  │ 遠端 (135 GB VRAM) — LLM Workstation             │
│                                             │  │                                                 │
│ Process A: Collector                        │  │ Process B-T: Teacher (llama-server :18888)      │
│  - IsaacLab + IsaacLab-Arena                │  │   gemma-4-31B-it-GGUF + mmproj-gemma4v          │
│  - RoboTwin 2.0 dual-arm tasks              │  │   (multimodal, CoT enabled)                     │
│  - 16 平行 env (POC scale)                   │  │                                                 │
│  - 4-stage loop driver                      │  │ Process B-S: Student (llama-server :18889)      │
│  - 寫 replay 到本機 disk                      │  │   gemma-4-31B + 載入最新 LoRA GGUF              │
│                                             │  │   (no CoT, direct action mapping)               │
└─────────────────────────────────────────────┘  │                                                 │
              │                                  │ Process C: Trainer                              │
              │  rsync over SSH                  │   HF transformers + peft QLoRA                  │
              │  (replay → server)               │   train on success replay                       │
              ▼                                  │   convert_lora_to_gguf.py → adapter.gguf        │
┌─────────────────────────────────────────────┐  │   POST /v1/lora-adapters → reload Student       │
│ Replay Buffer (canonical store)             │  │                                                 │
│ /data/replays/{run_id}/{success,failure}/   │  └─────────────────────────────────────────────────┘
│ {episode_id}.{json,npz}                     │
│ schema_version=1                            │
└─────────────────────────────────────────────┘
```

**HTTP 介面**：
- Collector → Teacher：`POST :18888/v1/chat/completions`（base64 RGB + Stage1 / Stage3 prompt）
- Collector → Student（Eval 階段）：`POST :18889/v1/chat/completions`（直接出座標）
- Trainer → Student：`POST :18889/v1/lora-adapters`（hot scale，但載入新 GGUF 仍需 server restart；POC 接受 30 s downtime / checkpoint）

**為什麼不在本機 finetune**：使用者明示遠端 server 負責 infra/finetune；本機 20 GB 不可能放 31B QLoRA（最低 24-32 GB 起跳）。POC 的職責邊界清楚切分。

---

## 2. Benchmark 與 Curriculum 設計

### 2.1 Benchmark：IsaacLab-Arena + RoboTwin 2.0

- 安裝 IsaacLab-Arena `release/0.2.1`（Docker，pin commit；alpha 期間 API 不穩，不追 main）。
- 啟用 RoboTwin 2.0 整合分支，給 ~50 個 dual-arm tabletop tasks。
- 評估時報出 RoboTwin 公開 leaderboard 兼容指標（success rate per task）。
- 與其他 leaderboard entries 的差異化：**他們都是 demo-heavy（10-100 demo / task），AionGenos 是 zero-demo**。這就是貢獻。

### 2.2 Curriculum Ladder（5 級，由淺入深）

> Level 細節在 M1 對 RoboTwin 2.0 task list inspection 之後拍板；以下為設計骨架。

| Lv | 描述 | 控制元素 | 候選 RoboTwin task |
|---|---|---|---|
| **L0** | Bimanual reach 兩個有顏色目標物 | task-space ΔEE × 2 | 自製 `reach_two_cubes`（基於 `Isaac-Reach-OpenArm-Bi-v0`） |
| **L1** | Bimanual follow trajectory（VLM 給 waypoint 序列） | ΔEE 序列 | RoboTwin `dual_arm_trace` 或自製 |
| **L2** | Bimanual contact / push 一物到目標區 | ΔEE + 接觸 | RoboTwin `dual_push_block` |
| **L3** | Bimanual near grasp（單臂抓近物） | ΔEE + binary gripper | RoboTwin `pick_place_close` |
| **L4** | Bimanual coordinated grasp / handover | 雙臂協調 | RoboTwin `block_handover` |

**晉級規則（明確、可驗證）**：
- Level $n$ 達 success rate ≥ 60%（teacher zero-shot）才 unlock Level $n+1$。
- Level $n+1$ 訓練資料 = 現 level success replay + 上一級 success replay（cumulative）。
- 任一 level 12 hr collector 跑不到 100 success → 標記為 `curriculum_blocked`，停 loop 報告。

**Curriculum 機制實作**：用 `isaaclab.managers.CurriculumTermCfg` + `modify_env_param` 在達標後自動切換 task config（不需要重啟 sim）。`AionGenosCurriculumManager`（自寫）追蹤每 level 的 success rate 並決定 advance / hold。

### 2.3 為什麼 curriculum 是 POC 的核心而非 nice-to-have

- 使用者明確要求：「**workflow and loop 任何任務應該都是可以在有限時間內學習的，這才是目標**」。
- IsaacLab-Arena 沒有自帶任務難度 curriculum（只有 RoboCasa 那種 task collection）→ 這正是 AionGenos 的主張：「我們不只解一個任務，我們提供 self-bootstrapping 機制」。
- POC 的單一最重要 deliverable = **同一份 codebase 在 5 個 level 上輪流跑通而不需要為每個 task 寫專屬 prompt / 專屬 reward**。Prompt / reward 是 task-agnostic 模板 + 從 task config 自動填值。

---

## 3. 四階段認知演化管線（核心架構）

完全按使用者規格實作，且 **task-agnostic** —— 同一份程式碼用在 L0~L4 所有任務。

### Stage 1 — Reasoning（Zero-Shot Planning）
- 輸入：當前 RGB（128×128 base64 PNG）+ task 模板填好的 instruction（例：`"Push the [red cube] to the [green pad] using both arms cooperatively"`）+ 可觀測狀態 summary（EE pose、gripper open/close）
- Teacher Prompt（task-agnostic 模板）：
  ```
  You are a bimanual robot. You see the scene below.
  TASK: {instruction_filled_from_task_cfg}
  CURRENT STATE:
    LEFT_EE = (X={...}, Y={...}, Z={...})  # 整數 [-100,100]
    RIGHT_EE = (X={...}, Y={...}, Z={...})
    LEFT_GRIPPER = {open|closed}
    RIGHT_GRIPPER = {open|closed}

  Reason step-by-step about the next sub-goal:
  THOUGHT: <one paragraph physics reasoning>
  LEFT_TARGET: X=<int> Y=<int> Z=<int>
  RIGHT_TARGET: X=<int> Y=<int> Z=<int>
  LEFT_GRIPPER_NEXT: <open|closed>
  RIGHT_GRIPPER_NEXT: <open|closed>
  STOP: <true|false>
  ```
- 解析器嚴格 regex 抽欄位；解析失敗最多 2 次 retry，失敗 → episode 標記 `vlm_parse_fail` 並繼續下一個 reset。
- `aiongenos/vlm/prompts.py` 統一管理模板，task config 用 `format_map` 填欄位 → 全部 5 個 level 共用同一個 prompt 模板。

### Stage 2 — Attempt（Heuristic Exploration）
- 反 normalize 整數 → metric → 餵 `DifferentialInverseKinematicsActionCfg` 跑 60 sim step（≈1 s）。
- gripper next state 由 `BinaryJointPositionActionCfg`（IsaacLab 既有）執行。
- 過程中 5 Hz 抓 RGB 序列、EE 位置、gripper 狀態、success / failure / collision flag。
- 結束標籤：`success` / `timeout` / `collision` / `out_of_workspace` / `object_lost`（針對 grasp tasks）。

### Stage 3 — Learning（Self-Reflection via **Observable State Only**）⚠️ 嚴格限制
**只在失敗時觸發**。新一次 VLM call，輸入嚴格白名單：

| 類別 | 允許 | 禁止 |
|---|---|---|
| 視覺 | rollout 開始 / 結束 RGB | semantic mask、depth、point cloud |
| 軌跡 | EE position 時序（normalized int）、gripper open/close 序列 | contact force、joint torque、motor current、applied wrench、friction coefficient |
| 衍生 | EE-到-物件 Euclidean distance 時序、物件 pose 變化（觀測自 RGB 推得的） | 物件 mass、inertia、material |

**Critic Prompt（task-agnostic 模板）**：
```
You are a physics-grounded critic. The robot just attempted "{task_instruction}"
and FAILED with reason: {failure_label}. Below is what an EXTERNAL OBSERVER
could see — no hidden sensors. Diagnose the most likely failure cause and
propose a corrected sub-goal sequence for retry.

[RGB before] [RGB after]
TRAJECTORY (normalized integer coords):
  t=0.0: LEFT_EE=(...), RIGHT_EE=(...), LG=open, RG=open, dist_red=..., dist_green=...
  t=0.2: ...
  t=1.0: ...

DIAGNOSIS: ...
REVISED_LEFT_TARGET: ...
REVISED_RIGHT_TARGET: ...
REVISED_LEFT_GRIPPER: ...
REVISED_RIGHT_GRIPPER: ...
```

- 修正後的 plan 重跑 Stage 2；成功 → 寫 `success` replay。
- **強制執行**：`tests/test_critic_observable_only.py` 對 Stage 3 input dict 做 schema 白名單斷言（任何 hidden sensor 鍵 → fail）。

### Stage 4 — Intuition（Distillation to Parametric Memory）

**4-A. BC with CoT preserved**（Stage 4-A）：
- Trainer process (遠端) 從 success replay 取 (RGB, instruction, full_response_with_THOUGHT) tuples。
- HF Gemma-4-31B + peft QLoRA（rank=16，4-bit quant base）按 peft #3129 monkey-patch 路徑訓練。
- `convert_lora_to_gguf.py` 轉成 GGUF adapter，`scp` 到 student llama-server，重啟以 `--lora <path>` 載入。

**4-B. CoT-strip refinement**（Stage 4-B）：
- 同一 LoRA 二次微調：loss mask 把 `THOUGHT:` 區段全 0，只在 `LEFT_TARGET / RIGHT_TARGET / *_GRIPPER` 算 loss。
- 推論時 prompt 末端直接給 `LEFT_TARGET:`，模型必須跳過 CoT 直接生座標 → 達成 $O(1)$ 直覺反射目標。

**4-C. DPO refinement (stretch, 只在 4-A/4-B 全達標後做)**：
- 從 replay 的 (success_traj, fail_traj) 配對，用 `trl.DPOTrainer` 細修同一 LoRA。
- POC 不依賴此項；M7 stretch。

**為什麼 student 與 teacher 是同一個 base 模型？**：
1. 使用者偏好統一 runtime（llama.cpp）。
2. 蒸餾不需要跨架構（同 base + LoRA delta 即可），CoT-strip 在 task 等價條件下會嚴格降延遲（teacher 出 ~1000 token，student 出 ~30 token，linear in token 數）。
3. 135 GB VRAM 可同時放 base × 2（teacher 18 GB GGUF + student 18 GB GGUF + train workspace ~50 GB），餘裕大。

---

## 3.5 Action Representation（參考 SOTA Pi-0.5 / OpenVLA-OFT / RDT）

**SOTA 對齊**（基於 Pi-0.5 paper 2504.16054 + Pi-0.5 blog）：
- Pi-0.5 同一模型訓練 **joint pose 與 EE pose 兩種模式**，透過 prompt token `<control_mode>joint/end_effector<control_mode>` 切換
- High-level 介面 = 自然語言文字 subtask（"pick up the pillow"）
- Low-level 介面 = 50-step / 1 s action chunk，50 Hz 控制
- Pi-0.5 沒在 paper body 明說 rotation 表示（在 Appendix A-E）；OpenVLA / RT-2 用 **離散 bin 化的 RPY 或 axis-angle**；Diffusion Policy 系列用 **6D continuous rotation (Zhou et al. 2019)**

**AionGenos POC 受限於 GGUF runtime → 必須輸出離散 token**，因此採以下分層設計：

### 3.5.1 控制模式選擇（隨 curriculum level 演進）

| Level | 任務性質 | 控制模式 | 維度 / 臂 | 旋轉表示 | 理由 |
|---|---|---|---|---|---|
| **L0** Reach | 純位置到位，gripper 不開合 | EE position-only | 3 (x,y,z) | 無，wrist 固定 top-down approach | 與 Pi-0.5 EE pose mode 對齊；reach 任務不需 wrist 角度，最大化 LLM 物理推論成功率 |
| **L1** Trace | 多 waypoint 追蹤 | EE position-only × N waypoints | 3 × N | 無 | 同 L0；改成 sub-goal 序列（action chunk = 3-5 個 waypoint） |
| **L2** Push | 接觸 + 推 | EE position + **2-DoF approach angle** (pitch, yaw) | 5 (x,y,z,pitch,yaw) | Pitch/Yaw 兩軸（roll 對推任務無用，省 1 DoF；參考 OpenVLA 的整數 bin 思路） | 推任務需控制 EE 接觸面方向但 roll 對結果無關；2-DoF 比 full 3-DoF Euler 更易 LLM 推論 |
| **L3** Pick & Place | 抓近物 + 放下 | EE position + **3-DoF Euler RPY** + binary gripper | 6 + 1 (x,y,z,r,p,y,grip) | **Euler RPY** 整數化 | RPY 對 LLM 直覺（三個獨立角度）；gimbal lock 在 tabletop manipulator workspace 鮮少觸發；gripper 僅 open/close 1 bit |
| **L4** Handover | 雙臂協調 + 接觸交接 | EE position + Euler RPY + binary gripper × 2 臂 | (6+1) × 2 = 14 | Euler RPY | 同 L3 但雙臂需要 sync 時序；POC stretch |

> **Joint-space mode 不在 POC 範圍**。理由：Pi-0.5 雖也訓 joint，但需要大量 demo 學 joint inverse mapping；AionGenos zero-demo 從 EE 入手更容易讓 VLM 物理常識落地。Joint mode 留 Phase B 用 OpenVLA-OFT recipe 訓。

### 3.5.2 Rotation 表示為何選 Euler RPY 而非其他

| 表示 | LLM 整數化友善度 | 連續性 | Gimbal lock | 雙覆蓋 | NN regression 數學 | POC 採用 |
|---|---|---|---|---|---|---|
| Euler RPY | ★★★★★（3 個獨立整數）| ✗（mod 2π 跳變） | ✗（pitch=±90° 退化） | ✓ 唯一 | ★★ | **L2+** |
| Quaternion (xyzw) | ★★（4D + 單位範數約束）| ✓ | ✓ 無 | ✗ q ≡ -q | ★★★ | ✗ |
| Axis-angle (rx,ry,rz) | ★★★★（3D, magnitude=angle）| ✓（限 \|θ\| < π） | ✓ | ✗ | ★★★ | 候選 |
| 6D continuous (Zhou 2019) | ★（6D 浮點向量，連續無間斷）| ✓ | ✓ | ✓ | ★★★★★ | ✗（LLM 出 6 個獨立整數很容易違反 SO(3) 約束） |
| Rotation matrix 9D | ✗ | ✓ | ✓ | ✓ | ★★★★ | ✗ |

**結論**：POC 採 **Euler RPY 整數化（[-100, 100] 對映 [-π, π]）**。理由：
1. LLM CoT 推論「左臂 wrist 翻 -45 度抓杯子」是直覺的；6D rot 寫不出來
2. Tabletop bimanual workspace 中 pitch ≈ ±90° 的 gimbal lock 邊界很少進入（手臂 wrist 角度通常 |pitch| < 60°）
3. 採 ZYX 內旋 (yaw → pitch → roll) 慣例，與 Isaac Lab 的 `transforms_utils.matrix_from_euler` 對齊
4. POC 不需 student 「regress」rotation；它仍輸出**離散整數 token**，loss 走 cross-entropy 而非 L2

**邊界處理**：
- Round-trip: int → metric → quat → int 對稱性測試在 `tests/test_scalar_guard.py`
- |pitch| > 80° 觸發警告（接近 gimbal lock），episode 標記 `near_singularity`，replay 額外標籤供後分析
- L4 若 handover 對 wrist 旋轉太敏感 → fallback 改 axis-angle（對稱觸發條件 ≥ 5% episode 進入 lock zone）

### 3.5.3 Action Chunk 策略（隨 level 演進）

- **L0/L1**：single sub-goal（每 1 s 一個 (x,y,z) 目標，由 IK servo），完全對應使用者 §1 的「VLM 推論 sub-goal、低階 servo 過去」設計
- **L2**：single sub-goal + approach pitch/yaw
- **L3/L4**：sub-goal 序列 chunk（≤ 3 個 sub-goal，類比 Pi-0.5 的 1 秒 chunk 但離散化）；中間 1 個 sub-goal 完成才看下一個

> POC **不**模仿 Pi-0.5 的 50-step continuous flow-matching chunk —— GGUF runtime 不能輸出連續向量。離散整數 sub-goal 是 LLM-only constraint 下的合理近似。

### 3.5.4 Prompt 結構升級（task-agnostic 模板，按 level 自動填）

```
TASK: {instruction}
CONTROL_MODE: end_effector_pose_with_rpy   # L2+；L0/L1 為 end_effector_position_only

CURRENT STATE:
  LEFT_EE_POS  = (X={x_int}, Y={y_int}, Z={z_int})
  LEFT_EE_RPY  = (R={r_int}, P={p_int}, Y={y_int})        # L2+ only
  LEFT_GRIPPER = {open|closed}                            # L3+ only
  RIGHT_EE_POS = (X=..., Y=..., Z=...)
  RIGHT_EE_RPY = (R=..., P=..., Y=...)                    # L2+ only
  RIGHT_GRIPPER = ...                                     # L3+ only

THOUGHT: ...
LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>
LEFT_TARGET_RPY:  R=<int> P=<int> Y=<int>                 # L2+ only
LEFT_GRIPPER_NEXT: <open|closed>                          # L3+ only
RIGHT_TARGET_POS: ...
RIGHT_TARGET_RPY: ...
RIGHT_GRIPPER_NEXT: ...
STOP: <true|false>
```

`aiongenos/vlm/prompts.py` 用 task config 的 `control_mode` 欄位自動選 prompt 變體（L0/L1 simplified vs L2+ full），保持 task-agnostic 性質。

### 3.5.5 Isaac Lab 控制器對接

- L0/L1 (position only): `DifferentialInverseKinematicsActionCfg(controller=DifferentialIKControllerCfg(command_type="position", use_relative_mode=False))`
- L2+ (pos + RPY): `DifferentialInverseKinematicsActionCfg(controller=DifferentialIKControllerCfg(command_type="pose", use_relative_mode=False))`，VLM 輸出 RPY 後 `aiongenos/control/rotation.py` 轉成 quaternion 餵 IK
- L3+ gripper: `BinaryJointPositionActionCfg`（IsaacLab 既有）
- 控制頻率：VLM 出 sub-goal **1 Hz**；IK servo 內部 **60 Hz**；模擬步 120 Hz、decimation=2

> 對齊 Pi-0.5 的「low-level 50 Hz」量級。POC 1 Hz sub-goal 是 conservative 起點，M5 後若 student 達標可調整為 2-5 Hz。

---

## 4. 標量防護（Scalar Guard）

VLM 對連續浮點 token 化非常糟（`0.234` 跟 `0.235` 在 token 層幾乎隨機）。POC 一律走 **歸一化整數網格**：

**位置軸**（L0+，所有 level 都用）

| 軸 | metric range（per task config） | int range | 解析度 |
|---|---|---|---|
| X | `task.workspace.x_bounds` (m) | `[-100, 100]` | (max-min)/200 |
| Y | `task.workspace.y_bounds` | `[-100, 100]` | |
| Z | `task.workspace.z_bounds` | `[-100, 100]` | |

**旋轉軸**（L2+ 啟用）

| 軸 | metric range | int range | 解析度 |
|---|---|---|---|
| Roll  (R) | `[-π, π]` | `[-100, 100]` | π/100 ≈ 1.8° |
| Pitch (P) | `[-π/2, π/2]` | `[-100, 100]` | π/200 ≈ 0.9°；\|P\|>80→`near_singularity` flag |
| Yaw   (Y) | `[-π, π]` | `[-100, 100]` | π/100 ≈ 1.8° |

`aiongenos/vlm/scalar_guard.py`：
- `metric_to_int(coord, bounds) -> int` / `int_to_metric(value, bounds) -> float`
- `rpy_to_int(rpy_rad) -> (r,p,y)` / `int_to_rpy(int_triple) -> rpy_rad` / `rpy_to_quat(...)` （ZYX 內旋慣例）
- 邊界 clamp，越界即標 `out_of_workspace` / `near_singularity`
- Round-trip 對稱性、gimbal-lock zone、邊界測試在 `tests/test_scalar_guard.py`

`aiongenos/control/rotation.py`：負責整數 RPY ↔ Isaac Lab IK 介面要的 quaternion 轉換（單一 source of truth，避免散落）。

> Prompt / parser / replay 統一走整數，**LLM 不會看到任何小數點**。task 切換時，bounds 與 control_mode 從 `aiongenos/tasks/{level}/cfg.py` 讀取，自動套用。

---

## 5. 檔案結構（在 `/home/control/AionGenos/` 下新增）

```
AionGenos/
├── CLAUDE.md                       (existing — 不動)
├── AionGenos.code-workspace        (existing — 不動)
├── README.md                       (新增：架構、雙機 setup、quickstart)
├── pyproject.toml                  (本機 deps：isaaclab + Pillow + httpx + numpy + pytest；不引 peft/trl，避免誘導本機 train)
├── server/                         (遠端 server 部署 manifest，靠 scp 過去用)
│   ├── pyproject.toml              (peft + trl + transformers + bitsandbytes + accelerate)
│   ├── llama_server_teacher.sh
│   ├── llama_server_student.sh
│   └── README_server.md
├── .env.example                    (TEACHER_URL=http://10.80.9.148:18888, STUDENT_URL=http://10.80.9.148:18889, REMOTE_REPLAY_PATH=...)
├── aiongenos/
│   ├── __init__.py
│   ├── config.py                   (workspace bounds、URL、replay path、curriculum thresholds)
│   ├── tasks/
│   │   ├── __init__.py             (gym.register 所有 5 個 level)
│   │   ├── base/                   (共用 scene、camera、IK、reward template)
│   │   ├── L0_reach_two_cubes/
│   │   ├── L1_dual_trace/
│   │   ├── L2_dual_push/
│   │   ├── L3_pick_place_close/
│   │   └── L4_block_handover/
│   ├── curriculum/
│   │   ├── manager.py              (AionGenosCurriculumManager — success-rate gating)
│   │   ├── ladder.py               (5-level definition + advance rules)
│   │   └── arena_adapter.py        (對接 IsaacLab-Arena ArenaEnvBuilder)
│   ├── vlm/
│   │   ├── client.py               (httpx async, base64 helper, retry policy)
│   │   ├── prompts.py              (task-agnostic Stage1 / Stage3 模板)
│   │   ├── parser.py               (regex 抽欄位 + Pydantic 驗證)
│   │   └── scalar_guard.py
│   ├── control/
│   │   ├── rotation.py             (RPY ↔ quaternion，ZYX 內旋；單一 source of truth)
│   │   └── action_modes.py         (per-level control_mode 切換 + IK config builder)
│   ├── pipeline/
│   │   ├── stage1_reasoning.py
│   │   ├── stage2_attempt.py
│   │   ├── stage3_critic.py
│   │   └── stage4_distill_remote_trigger.py  (HTTP / ssh hook 觸發遠端 trainer)
│   ├── replay/
│   │   ├── schema.py               (TypedDict + JSON schema, schema_version=1)
│   │   ├── buffer.py               (atomic write + iterator)
│   │   ├── filter.py               (success/failure 過濾)
│   │   └── sync.py                 (rsync wrapper to remote)
│   ├── orchestrator/
│   │   ├── collect.py              (本機；4-stage loop + curriculum advance)
│   │   ├── eval.py                 (本機；評估 student endpoint)
│   │   └── remote_train_trigger.py (本機 → 遠端 trainer 啟動)
│   └── eval/
│       └── metrics.py              (per-level success rate、teacher latency vs student latency、distillation gap)
├── server_side/                    (遠端 server 上的 trainer 程式，scp 過去執行)
│   ├── train_qlora_gemma4.py       (HF + peft QLoRA, monkey-patch peft #3129)
│   ├── export_lora_gguf.py         (call llama.cpp convert_lora_to_gguf.py)
│   └── reload_student.sh           (kill -HUP llama-server-student + 重新 --lora)
├── scripts/
│   ├── 00_smoke_vlm.py             (Phase 0：base64 grounding sanity)
│   ├── 01_smoke_isaaclab.sh        (跑 Isaac-Reach-OpenArm-Bi-Play-v0)
│   ├── 02_smoke_arena.sh           (跑 IsaacLab-Arena example task)
│   ├── 03_collect.py               (跑 collect.py)
│   ├── 04_sync_and_train.sh        (rsync replay → ssh trigger remote train)
│   └── 05_eval.py
├── tests/
│   ├── test_scalar_guard.py            (含 RPY round-trip + gimbal-lock zone)
│   ├── test_rotation.py                (RPY ↔ quat 數值對稱性、ZYX 慣例驗證)
│   ├── test_vlm_parser.py              (各 level prompt 變體解析)
│   ├── test_replay_buffer.py
│   ├── test_critic_observable_only.py  (✓ 強制白名單)
│   ├── test_curriculum_manager.py      (advance gating + cumulative replay)
│   ├── test_action_modes.py            (per-level control_mode 切換正確性)
│   └── test_env_registers.py
└── data/                           (gitignored)
    ├── replays/
    └── eval_reports/
```

---

## 6. 里程碑（4 週 / 1 工程師為前提）

| M | 名稱 | Deliverable | Day |
|---|---|---|---|
| **M0** | Stack 煙霧測試 + Arena install | 本機 `scripts/00_smoke_vlm.py` 綠；`scripts/01_smoke_isaaclab.sh` 綠；`scripts/02_smoke_arena.sh` 用 Docker 跑通 Arena Franka Lift example | 1–3 |
| **M1** | L0 task `reach_two_cubes` 上線 + grounding sanity | `Isaac-AionGenos-L0-v0` 可 `gym.make`；20 張 sim RGB 餵 teacher，cube 中心 grounding 誤差 < 8 cm | 4–6 |
| **M2** | Stage 1+2 closed-loop 在 L0 跑通 | teacher 看圖 → 出 (LEFT, RIGHT) → IsaacLab 執行 → 第一個 success episode → replay 寫入 | 7–8 |
| **M3** | Stage 3 critic 上線（observable-only 強制） | 失敗自動觸發 critic、修正 retry；`test_critic_observable_only.py` 強制 schema 白名單 | 9–10 |
| **M4** | L0 success replay ≥ 100 + 遠端 trainer 雛形 | 本機 collector 12 hr 達標；遠端 server 跑通 1 epoch QLoRA + convert→GGUF→reload student | 11–13 |
| **M5** | Stage 4-A + 4-B 完整一輪 + L0 student eval | student endpoint :18889 上線；100 ep eval；報告 student SR vs teacher SR、latency ratio | 14–16 |
| **M6** | Curriculum 機制 + L1 unlock + L1 跑通 | `AionGenosCurriculumManager` 接通；L0 達 60% → 自動 unlock L1；L1 完成 collect→train→eval 一輪（仍 position-only） | 17–22 |
| **M7** | L2 解鎖（**首次啟用 RPY 軸**）+ L3 stretch | L2 push 任務含 pitch/yaw 控制；`rotation.py` round-trip 通過；L3 完整 control_mode（pos+RPY+gripper）若時間允許；L4 列為 Phase B | 23–28 |

POC 交付標準 = **M5 + M6 完成**：證明 (a) 4-stage loop 在 L0 上產生可量測的蒸餾 gap；(b) curriculum 機制可自動 unlock 下一 level 並重跑 loop。L2~L4 是 stretch，反映「framework generality」。

---

## 7. 驗證方法（端到端）

**煙霧測試**（M0）：
- `python scripts/00_smoke_vlm.py` → 餵合成圖、要求 JSON、回 2 個合法 (X,Y,Z) 整數座標
- `bash scripts/01_smoke_isaaclab.sh` → headless 100 step OpenArm Bi-reach 不 crash
- `bash scripts/02_smoke_arena.sh` → IsaacLab-Arena Docker 起得來，example task 成功 reset

**單元測試**（每 commit）：
- `pytest tests/` 全綠
- `test_critic_observable_only.py` 必須 強制斷言 hidden sensor 不入 prompt

**整合測試**（每 milestone）：
- M2：肉眼確認 RGB / EE / VLM action 對應
- M4：遠端 train log 顯示 loss 收斂 + GGUF reload 成功 + student endpoint 200 OK
- M5：`scripts/05_eval.py` 報出 (teacher_SR, student_SR, latency_ratio)
- M6：L0 → L1 自動 unlock log + L1 重跑 loop 全綠

**目標數字**：
- L0 teacher SR **≥ 60%**（unlock L1 門檻）；不達 → R1 應變
- L0 student SR **≥ 0.7 × teacher_SR**；inference latency **≤ 200 ms / step**（teacher 估 1.5–3 s / step） → distillation gap 量化
- M7 結束時 curriculum 至少推進至 L2 以上

不達 L0 ≥ 60% → 不是蒸餾的問題，是 sim-render 上 VLM grounding 不夠。觸發 §8 R1 應變。

---

## 8. 已識別風險與應變

| # | 風險 | 緩解 |
|---|---|---|
| **R1** | Gemma-4 對 sim-rendered RGB grounding 弱 | M1 加 grounding sanity（20 張手工 label）；誤差 > 8 cm 即觸發：(a) prompt 加 few-shot ICL，(b) 縮小 workspace（讓相對位置更明顯），(c) 換到 Qwen2.5-VL-72B |
| **R2** | Server `n_ctx=2048` 對 CoT + 圖太緊 | M0 請 user 把 server 重啟為 `--ctx-size 16384`，否則 CoT 限 200 tok、圖 64×64 |
| **R3** | IsaacLab-Arena alpha 不穩 | pin `release/0.2.1`，預留 0.5 週應對 breakage；fallback 到純 IsaacLab 內建 + RoboTwin 2.0 直接 import |
| **R4** | Gemma-4 vision-LoRA → GGUF 路徑未公開驗證 | POC 第一輪只 LoRA LM-head（不動 vision tower），peft #3129 已驗；萬一 vision tower 必須調整 → fallback 維持 vision tower frozen |
| **R5** | Curriculum advance 永遠卡在某 level | 12 hr collect 不到 100 success → 標 `curriculum_blocked` 並停 loop 報告（不 silent fail） |
| **R6** | 「無示範原則」被無意違反 | `pyproject.toml` 嚴守白名單；CI `import_check` 確保 `lerobot` / `octo` / `openx` / `robotwin demo set` 沒被 import |
| **R7** | Critic 偷看 hidden sensor | `test_critic_observable_only.py` 白名單斷言 |
| **R8** | Student 重啟造成 30 s downtime / checkpoint | Eval 階段 OK，accept；Production 升級用 vLLM hot-load（Phase B） |
| **R9** | rsync replay over WAN 慢 | M0 量測 RTT；> 100 Mbps 可接受。慢 → 改 NFS / SSHFS mount，或 Trainer 反向 pull |
| **R10** | L2+ 啟用 RPY 後 LLM 對 wrist 角度物理推論失準 | M7 加 grounding sanity 對 RPY 軸（手工 20 個 rollout 看 VLM 提的 pitch/yaw 是否合理）；連續 ≥ 5% episode 進入 `near_singularity` zone → fallback 改 axis-angle 表示（同樣 3D 整數，但無 gimbal lock 退化） |

---

## 9. 階段邊界與不做事項

**這份計畫不包含**：
- ❌ 真機部署（POC 純 sim）
- ❌ 任何 human demonstration 資料集 / Behavior Cloning bootstrap（永遠禁止）
- ❌ Concurrent collector + trainer（POC 為 sequential phases；Phase B 升級）
- ❌ 在本機做 LoRA 訓練（一律遠端 135 GB server）
- ❌ Sim2Real domain randomization 完整版（POC 只做 reset 隨機化）
- ❌ Curriculum L4（block_handover）不列為 POC must-have，僅 stretch

**POC 完成後的 Phase B**：
1. 完成 L4 並挑戰 RoboTwin 2.0 leaderboard 公開分數
2. Collector / Trainer 改成真正並行（vLLM + ZMQ）
3. 把 critic 反饋寫成 reward 訊號，啟動 PPO refinement
4. 把 vision tower 也納入 LoRA delta（待 Gemma-4 mmproj LoRA 路徑成熟）

---

## 10. 已確認的關鍵決策

**Student runtime（已決定）**：

- **預設走 (A)：teacher 與 student 同 llama.cpp runtime**
  - 兩個 llama-server，teacher :18888（不動）、student :18889 載 GGUF LoRA
  - 第一輪只 LoRA **LM-head（不動 vision tower）**，規避 Gemma-4 vision-LoRA→GGUF 未公開驗證的 R4
  - 接受 checkpoint reload 30 s downtime（POC 是 sequential phase，eval 階段才 reload）

- **Fallback 觸發條件 → 切換到 (B) Student=vLLM**：
  - **Trigger 1**：M4 `convert_lora_to_gguf.py` 對 Gemma-4 LoRA 轉檔失敗（ValueError / shape mismatch / 無法載入）
  - **Trigger 2**：M4 student endpoint 載入轉好的 GGUF LoRA 但輸出明顯錯亂（loss 收斂但 inference 出 garbage）
  - **Trigger 3**：M5 vision tower 必須納入 LoRA（觀察到無 vision-LoRA 蒸餾完全 collapse）
  - 任一觸發 → 切到 vLLM + HF 原生權重 + peft hot-load 路徑；teacher 不動
  - Fallback 切換預估成本：1.5 工作天（vLLM install、startup script、調 student URL 即可）

切換決策必須記錄到 `docs/decisions/student-runtime.md`，附觸發條件 log，作為 POC 報告附件。
