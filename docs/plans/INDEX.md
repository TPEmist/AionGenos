# AionGenos — 開發追蹤 INDEX

> Embodied AI 開源研究框架。VLA 物理常識作為 System 2，蒸餾為 LoRA System 1，零示範雙臂任務。
> 計畫全文：[`docs/plans/01_poc_cognitive_evolution_pipeline.md`](docs/plans/01_poc_cognitive_evolution_pipeline.md)
> 最後更新：2026-06-02

---

## 當前狀態

- **Phase**：M7 進度推進中
- **Sprint 目標**：L2 push 任務與 RPY 控制已成功接通，L2 環境已成功在 collect 迴圈中完成一輪測試，準備進入 L3 pick & place 任務
- **下一動作**：啟動 L3 任務，設計與註冊 L3 雙臂 pick & place 環境（首次引入 gripper 動作）

---

## Milestones（M0–M7，4 週 / 1 工程師）

| M | 名稱 | Days | 狀態 | 交付物 |
|---|---|---|---|---|
| M0 | Stack 煙霧測試 + Arena install | 1–3 | ✅ done | `00_smoke_vlm.py` / `01_smoke_isaaclab.sh` / `02_smoke_arena.sh` 全綠 |
| M1 | L0 task `reach_two_cubes` + grounding sanity | 4–6 | ✅ done | `Isaac-AionGenos-L0-v0` registered；20 張 sim RGB grounding 誤差 < 8 cm |
| M2 | Stage 1+2 closed-loop on L0 | 7–8 | ✅ done | 第一個 success episode 寫入 replay |
| M3 | Stage 3 critic（observable-only 強制） | 9–10 | ✅ done | 失敗自動 critic + retry；白名單斷言 test 綠 |
| M4 | L0 ≥ 100 success replay + 遠端 trainer 雛形 | 11–13 | ✅ done | QLoRA 1 epoch + GGUF 轉換 + student endpoint reload |
| M5 | Stage 4-A + 4-B + L0 student eval | 14–16 | ✅ done | student :18889 上線；100 ep eval；distillation gap 量化 |
| M6 | Curriculum 機制 + L1 unlock + L1 跑通 | 17–22 | ✅ done | L0 ≥ 60% → 自動 unlock L1；L1 完整 loop 一輪 |
| M7 | L2（首次 RPY）+ L3 stretch | 23–28 | ⬜ pending | L2 push 任務 + RPY round-trip；L4 列為 Phase B |

**POC 交付下限** = M5 + M6 完成

---

## Curriculum Ladder（5 級）

| Lv | 任務 | 控制模式 | 狀態 |
|---|---|---|---|
| L0 | Bimanual reach to 2 cubes | EE position-only (3D × 2) | ✅ done |
| L1 | Bimanual trace waypoints | EE position chunk | ✅ done |
| L2 | Bimanual push | EE pos + pitch/yaw (5D × 2) | ✅ done |
| L3 | Bimanual pick & place（近物） | EE pos + RPY + gripper (7D × 2) | ⬜ M7 stretch |
| L4 | Bimanual handover | 同 L3 + 雙臂協調 | ⬜ Phase B |

**晉級規則**：當前 level success rate ≥ 60% 自動 unlock 下一級；12 hr collect 不到 100 success 標 `curriculum_blocked`。

---

## 系統拓撲（雙機）

| 角色 | 位置 | 狀態 |
|---|---|---|
| Sim Workstation | 本機 RTX A4500 20 GB | ✅ ready（CUDA 12.9 + PyTorch 2.7.1） |
| LLM Workstation | 遠端 135 GB VRAM | ✅ confirmed by user |
| Teacher (`:18888`) | `ggml-org/gemma-4-31B-it-GGUF` on llama-server | ✅ multimodal 已測通 |
| Student (`:18889`) | 同 base + GGUF LoRA | ✅ ready |
| Trainer (Process C) | HF + peft QLoRA | ✅ ready |
| IsaacLab-Arena | `release/0.2.1` Docker | ⬜ M0 安裝 |

---

## 已驗證事實

- [x] `Isaac-Reach-OpenArm-Bi-v0` 註冊存在、雙臂 OpenArm 7-DoF×2 + 雙夾爪
- [x] Gemma-4-31B-GGUF 多模態 OK，能輸出 JSON 與空間座標（紅 quadrant→[-0.5,0.5]、藍→[0.5,-0.5]）
- [x] IsaacLab `CurriculumTermCfg` API 可用（`modify_reward_weight` / `modify_env_param` / `modify_term_cfg`）
- [x] IsaacLab-Arena 是真實官方 repo（NVIDIA isaac-sim org，418⭐，pin `release/0.2.1`）
- [x] RoboTwin 2.0 整合分支提供 ~50 dual-arm tabletop tasks
- [x] Pi-0.5 paper（arxiv 2504.16054）action representation 確認：joint+EE dual-mode、自然語言介面 high↔low、50 Hz / 50-step chunk

---

## Open Questions / 待 user 決策

| # | 議題 | 預設選擇 | 觸發再議條件 |
|---|---|---|---|
| Q1 | Server `n_ctx` 調整 | 請 user 重啟為 `--ctx-size 16384` | M0 前確認 |
| Q2 | Student runtime fallback (A→B) | (A) llama.cpp 同 runtime；blocker 才切 vLLM | M4 GGUF 轉換失敗時切換 |
| Q3 | RPY vs axis-angle | RPY（L2+ 啟用） | ≥ 5% episode 進 near_singularity → 切 axis-angle |
| Q4 | L4 是否進 POC | 否，列為 Phase B | M7 進度超前 1 週才考慮 |

---

## 風險登錄（10 項，全文見 plan §8）

| # | 風險 | 緩解狀態 |
|---|---|---|
| R1 | Gemma-4 對 sim RGB grounding 弱 | ⬜ M1 grounding sanity 驗證 |
| R2 | Server `n_ctx=2048` 過緊 | ⬜ M0 前請 user 調整 |
| R3 | IsaacLab-Arena alpha 不穩 | ⬜ M0 pin `release/0.2.1`，預留 0.5 週 buffer |
| R4 | Gemma-4 vision-LoRA→GGUF 路徑未公開驗證 | ⬜ POC 先 LoRA LM-head 規避 |
| R5 | Curriculum 卡在某 level | ⬜ M6 加 12 hr blocked 機制 |
| R6 | 「無示範原則」誤違反 | ⬜ M0 設置 CI import 白名單 |
| R7 | Critic 偷看 hidden sensor | ⬜ M3 強制白名單斷言 test |
| R8 | Student reload 30 s downtime | ⬜ POC 接受；Phase B 換 vLLM |
| R9 | Replay rsync over WAN 慢 | ⬜ M0 量 RTT |
| R10 | L2+ RPY LLM 推論失準 | ⬜ M7 加 RPY grounding sanity |

---

## 紅線原則（永不違反）

1. **零示範**：禁止 Open-X / LeRobot Hub / RoboCasa demos / RoboTwin demo set 等任何人類軌跡資料
2. **推訓分離**：sim 與 backprop 在獨立 process / machine，replay buffer 交換
3. **標量防護**：所有座標 / 角度走整數 grid，LLM 不看浮點
4. **觀測限制**：Stage 3 critic 只能看可觀測量（RGB、EE pose、gripper open/close、時序衍生 distance），禁止 hidden sensor（contact force、torque、mass 等）

---

## 參考資源

| 類別 | 連結 |
|---|---|
| 計畫全文 | [`docs/plans/01_poc_cognitive_evolution_pipeline.md`](docs/plans/01_poc_cognitive_evolution_pipeline.md) |
| 專案 CLAUDE.md | [`CLAUDE.md`](CLAUDE.md) |
| IsaacLab 本機 | `~/IsaacLab` |
| Pi-0.5 paper | https://arxiv.org/abs/2504.16054 |
| IsaacLab-Arena | https://github.com/isaac-sim/IsaacLab-Arena |
| RoboTwin 2.0 | https://robotwin-platform.github.io |
| OpenVLA-OFT | https://arxiv.org/abs/2502.19645 |
| peft #3129（Gemma-4 QLoRA） | https://github.com/huggingface/peft/pull/3129 |

---

## 變更日誌

| 日期 | 變更 |
|---|---|
| 2026-06-02 | 初版；POC 計畫定稿；新增 Pi-0.5 對齊的 §3.5 action representation；雙機拓撲確認 |
