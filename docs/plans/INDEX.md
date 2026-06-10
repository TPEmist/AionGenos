# AionGenos — 開發追蹤 INDEX

> Embodied AI 開源研究框架。VLA 物理常識作為 System 2，蒸餾為 LoRA System 1，零示範雙臂任務。
> 計畫全文：[`docs/plans/01_poc_cognitive_evolution_pipeline.md`](docs/plans/01_poc_cognitive_evolution_pipeline.md)
> 最後更新：2026-06-10

---

## 當前狀態

- **Phase**：M7 進度完成；遠端 31B QLoRA + GGUF 熱重載 + multi-round closed-loop + V4 sensory-integration sub-stage（L0a-L/R）+ C3 pre-reach reset pose 全部建好。**正在攻 R1 grounding 弱化**，問題分三層：mirror bias（V4 已解）→ base-frame mismatch（F24-F27 鎖定主因）→ 視覺場景貧瘠（C3 改善中）。
- **Sprint 目標**：在 V4 + C3 改動後**取得 L0a-Left 第一個真實 success replay**，啟動 Stage 4-A 二輪 QLoRA 訓練。
- **最新動作與進展（2026-06-08 ~ 06-10）**：
  1. **V4 落地**（commit `9c9ccdd`）：`Isaac-AionGenos-L0a-{Left,Right}-v0` sub-stage 註冊，`LEVEL_ORDER=(-2,-1,0,1,2,3,4)`，`IsaacLabEnvInterface.execute_command(active_arm)` 強制 hold-in-place 對側手；`docs/plans/sensory_integration_curriculum.md` 設計文件落地。
  2. **首跑 V4 5 ep on L0a-Left**（run 571472d8）：消除 mirror bias（X-flipped 0% in 4/5 ep；對照 V3 是 33-100%）→ F16/F17 確認；但 SR 仍 0/5 → F18 grounding 才是真瓶頸。
  3. **F19 STOP=True 假成功 bug 修好**（commit `53948b4`）：`vlm_stop_premature` 不再記為 success。手動把 false-success replay `571472d8/b0c28c0a` 搬到 failure 區。
  4. **Playback infra 上線**（commit `dcc8be3`）：collect.py 加 `--dump_images_root`；`scripts/diagnostics/playback_episode.py` 工具。
  5. **Reasoning analyser 上線**（commit `191ee0a`）：vlm_thought 完整保留（不再 600 字截斷），新加 `vlm_full_response`、`critic_feedback` 兩欄；`reasoning_analysis.py` 工具產出 token-presence × distance × thought-similarity × coord-volatility 四維 cross-round 報告。
  6. **F24-F27 主因鎖定**（run 67a99349 / 14 round trace + V4 5 ep 視覺檢查）：(a) VLM 全程零 X+/Y+/Z+ 軸向 reasoning，只用 forward / backward / left / right（F24）；(b) thought volatility 0.09 = VLM 真在想新方案（F25）；(c) Z std=1（F18 重發）；(d) 場景灰階 + cube 5×5px + 雙臂遮擋 + camera 角度（F20-F23）。
  7. **C3 pre-reach reset 落地**（commit `ee2de8a`）：`aiongenos/mdp/reset.py` 新加 `reset_joints_to_target_with_offset`；base config target 設左右 `joint2=0.5, joint4=0.8`，view_sanity 12 張取樣選定。Camera 不動（C4 經 view_sanity 證 default 已最佳）。
- **🟡 進行中**：PID 2793645 跑 5 ep L0a-Left + C3 + dump，預計 ~70 min；run id 落盤後查診斷。
- **下一動作優先序**：
  - (P0) 若 L0a-Left SR ≥ 1/5 → 立刻觸發 `04_sync_and_train.sh` 訓 v3 LoRA → reload student → reach_two_cubes (L0) eval
  - (P0) 若仍 0/5 但 best_combined 顯著下降（< 25cm avg）→ 加 5 ep 累積；若 best_combined 持平 → 動 prompt（避開 task 知識注入）或考慮 cube 放大（C5）
  - (P1) reasoning analyser 加跨 ep 跨 run 統計：「VLM 是否在 N ep 後開始用 X+/Y+/Z+ 描述 → 軸向自學是否真會發生」
  - (P2) 增量訓練（每 5 success 觸發 mini-LoRA）— 等首次有 success 才有意義

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
| M7 | L2（首次 RPY）+ L3 stretch | 23–28 | ✅ done | L2 push 任務 + RPY RTT 與 L3 pick & place (6-DoF + active gripper) 全綠 |

**POC 交付下限** = M5 + M6 完成

---

## Curriculum Ladder（5 級 + V4 sub-stage）

| Lv | 任務 | 控制模式 | 狀態 |
|---|---|---|---|
| **L0a-L** (-2) | Single-arm reach (左) | EE position-only 3D（右臂 hold-in-place）| ✅ env done / SR 未驗 |
| **L0a-R** (-1) | Single-arm reach (右) | EE position-only 3D（左臂 hold-in-place）| ⏳ env done / 未跑 |
| L0 | Bimanual reach to 2 cubes | EE position-only (3D × 2) | ✅ env done |
| L1 | Bimanual trace waypoints | EE position chunk | ✅ env done |
| L2 | Bimanual push | EE pos + pitch/yaw (5D × 2) | ✅ env done |
| L3 | Bimanual pick & place（近物） | EE pos + RPY + gripper (7D × 2) | ✅ env done |
| L4 | Bimanual handover | 同 L3 + 雙臂協調 | ⬜ Phase B |

**晉級規則**：當前 level success rate ≥ 60% 自動 unlock 下一級（依 `LEVEL_ORDER` 順序）；12 hr collect 不到 100 success 標 `curriculum_blocked`。

**V4 設計理由**：見 `docs/plans/sensory_integration_curriculum.md`。VLM 在 L0 雙臂 reach 表現出強 mirror bias（pred_R = mirror(pred_L)），符合感覺統合理論「single-channel 未穩定就嘗試 dual-channel 會學成 hack」的預測；L0a-L/R 是 plan §2.2 的合法擴展（cumulative training data 仍滿足）。

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
- [x] Level 3 Pick & Place (16D 行動維度、雙夾爪主動控制、SeattleLabTable 桌子與 DexCube 物體生成) 整合測試全數通過

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

## 變更日誌

| 日期 | 變更 |
|---|---|
| 2026-06-10 | **C3 pre-reach reset arm pose 落地**（commit `ee2de8a`）：新模組 `aiongenos/mdp/reset.py` 提供 `reset_joints_to_target_with_offset(target_joint_pos: dict, position_range, ...)`；base config target = `{openarm_left/right_joint2: 0.5, joint4: 0.8}`，jitter ±0.2 rad。view_sanity script (12 張 × 3 camera × 4 pose) 取樣選定。Camera 不動。**正在跑 5 ep L0a-Left + C3 + dump（PID 2793645，run id 待落盤）**。 |
| 2026-06-10 | **Reasoning analyser + 完整 thought trace**（commit `191ee0a`）：collect.py meta.json 移除 600 字 thought 截斷，新加 `vlm_full_response` 與 `critic_feedback` 欄；`scripts/diagnostics/reasoning_analysis.py` 提供 token-presence × distance × similarity × coord-volatility 四維 cross-round 報告。執行 V4 ep 67a99349/a047ccbe（14 round）證實 F24（VLM 0 個 X+/Y+/Z+ 軸向 token，全用 forward/left）+ F25（thought sim 0.09 = 不重複）。 |
| 2026-06-10 | **Playback infra**（commit `dcc8be3`）：collect.py 加 `--dump_images_root`；`scripts/diagnostics/playback_episode.py` 工具（人類視覺 + thought 配對）。 |
| 2026-06-10 | **F19 STOP=True 假成功 bug 修好**（commit `53948b4`）：`EpisodeOutcome.VLM_STOP_PREMATURE` 新狀態；collect.py / eval.py 都改成「VLM 出 STOP 但 dist 沒過閾值 → 標 vlm_stop_premature 不是 success」。手動把 false-success replay `571472d8/b0c28c0a` 搬到 failure 區。 |
| 2026-06-10 | **L0a target_color="red" fix**（commit `259bb80`）：先前 `state['target_color']=='green'` 跟視覺紅 cube marker 矛盾。 |
| 2026-06-10 | **collect.py logger 過 IsaacLab AppLauncher fix**（commit `6e32c7d`）：與 05_eval.py 同步。 |
| 2026-06-08 | **V4 sensory-integration sub-stage 落地 + 首跑**（commit `9c9ccdd`）：(a) 新增 `aiongenos/tasks/L0a_single_reach/{__init__.py, single_reach_cfg.py}`；(b) `LEVEL_CONFIGS` 加 -2/-1，新增 `LEVEL_ORDER=(-2,-1,0,1,2,3,4)`；(c) `AionGenosCurriculumManager` 改用 LEVEL_ORDER 替代 `range(max_level+1)`；(d) `IsaacLabEnvInterface.execute_command(active_arm)` 強制 hold-in-place 對側手；(e) 新增 `docs/plans/sensory_integration_curriculum.md` 設計文件（4 個借用的 SI 概念 + 為何 task-agnostic）。**首跑 5 ep on L0a-Left（run 571472d8）**：mirror bias X-flipped 從 V3 33-100% 降到 4/5 ep 的 0%（F16）；right-arm hold mask 100% 工作（F17）；但 SR 仍 0/5 → F18 grounding 才是真瓶頸。 |
| 2026-06-04 | **T-8 task-agnostic 放寬全套上線**：(T-11) 修 collect.py `total_vlm_latency_ms` per-episode 累計 bug — `_write_episode` 改用 `sum(i.latency_ms for i in vlm_interactions)`；(T-8a) `AionGenosReachEnvBaseCfg` 加 `events.reset_robot_joints` 覆蓋使用 `mdp.reset_joints_by_offset` (±0.2 rad)，解 F15 `reset_joints_by_scale` 對 OpenArm 結構性無效（5/7 joint default=0）；(T-8c) `LevelConfig.sim_steps_per_subgoal` 60→30（VLM 1Hz→2Hz，plan §3.5.5 路徑）；(T-8(a)) `max_subgoals_per_episode` 15→25 補回 round 數；(T-8b) plateau 公式改 last-N rolling mean — 現比較「最近 plateau_window=3 round 平均 combined dist」vs「再前 window 平均」，連續 patience=5 round 沒進步才殺。同步更新 collect.py 與 eval.py，加診斷工具 `scripts/diagnostics/check_ee_randomness.py`。**首 ep 驗證**（run ae692e9d / d1417df3）：(1) Latency 修正驗證 — `total_vlm_latency_ms=826s` 等於 sum(per-round) 不再跨 ep 累計；(2) EE 初始位多樣性 — L=(-11,+36,-50) R=(-50,-47,-51)，明顯偏離舊 run 的固定 (-33,±33,-54)；(3) 17 round 才 plateau，新公式給 VLM 更多探索空間；(4) Plan B (IK-based EE reset) 寫成 `aiongenos/curriculum/reset_ik.py` stub 待用 |
| 2026-06-04 | **Image dump + thought 揭示真正根因 — VLM 把螢幕座標當 base frame**。R2/R3 thought：「red cube at (-30, 20, 0)」「red X=-40」，GT 紅 cube_L = (+25, +20, +46)；VLM 看到紅 cube 在畫面左下用螢幕直覺估 X 負，但 base frame `+X = 機器人正前方 / +Y = 機器人左手邊 / +Z = 上`，紅 cube 在機器人左前方 → 實際 X 全正。整套 [-100, 100] 整數網格 prompt 無軸向定義；thought 與 output 數字也不一致（R3 thought X=-40 / output X=-3，差 13×）。**user 否決 prompt 注入軸向**（違反「對新生兒一樣」task-agnostic 原則），改方向：拉高 round 上限 + 改 Stage 3 critic 提供 observable feedback（distance / EE pose 變化）讓 VLM 自己學軸向。新增 `eval.py` 圖片 dump 與 meta.json (`--dump_images` flag)，`scripts/05_eval.py` 加 `--dump_root` |
| 2026-06-03 | **Multi-round closed-loop L0 eval（Q5 Option A 實作後）**：Teacher SR 0/5（avg 3.4 round, plateau:3 / max_rounds:2, grounding err L/R 31.0/22.8cm, final dist 31.6/19.8cm, latency 7434ms/call），Student SR 0/5（avg 3.8 round, plateau:2 / max_rounds:3, grounding err 38.2/26.9cm, final dist 40.8/22.0cm, latency 3614ms/call, **speedup 2.06×**）。Multi-round 機制正確（reset 後 GT 正常、plateau 偵測 work），但 SR 沒救起來（後來 dump 證根因是 prompt 軸向定義缺失）。新增 `LevelConfig.max_subgoals_per_episode` (L0=4) / `subgoal_success_threshold_m` / `plateau_min_progress_m` / `plateau_patience` / `IsaacLabEnvInterface.reset` warm-up step / eval.py multi-round + `_run_episode` |
| 2026-06-03 | **首輪 L0 closed-loop eval（single-shot baseline）** (`scripts/05_eval.py --num_episodes 5 --level 0 --sim_steps 600`)：兩 endpoint 皆 SR 0/5（全 timeout），teacher (31B) 與 student (E4B+LoRA `a318eb38`) grounding error ≈ 32 cm（target range 本身約 30 cm 量級），final dist ≈ 26-34 cm；teacher latency 7689 ms，student 3250 ms（speedup 2.37×；E4B 4.96 GB vs 31B Q4 ~17 GB）。蒸餾沒劣化品質但 **R1 grounding 弱**已實證落地。eval.py 加上 grounding-err / final-dist / outcome-distribution log，05_eval.py 加 `--sim_steps` / `--skip_teacher` / `--skip_student` flag 與 root logger fix |
| 2026-06-03 | 完成 E4B 的端到端蒸餾與熱重載驗證：限制 Lora target_modules 避免音頻塔衝突，解決 llama.cpp 轉檔的 `model.language_model.` 前綴匹配問題，並以 `--split-mode none` 解決 Vulkan 模式下多 GPU 圖分割崩潰，成功運行 student:18889 並返回 status: ok |
| 2026-06-03 | 解決遠端 CUDA 環境驅動衝突、多模態張量截斷填充與 4-bit 量化視覺塔 Dropout 報錯；以 `google/gemma-4-E4B-it` 進行 QLoRA 完整訓練與 GGUF 轉檔、熱重載（Reload）端到端 POC 管道驗證成功；啟動 `gemma-4-31b-it` 權重背景下載 |
| 2026-06-03 | 完成 Level 3 雙手 Pick & Place 環境開發、動作維度接通（16D 控臂 + 夾爪）、桌子與物體生成、並將所有環境單元與整合測試跑通 |
| 2026-06-02 | 初版；POC 計畫定稿；新增 Pi-0.5 對齊的 §3.5 action representation；雙機拓撲確認 |

---
## TODOs

**已完成（done）**

| # | 任務 | 細節 | 完成日 |
|---|---|---|---|
| T-D1 | eval.py multi-round closed-loop 機制 | `_run_episode` round loop / plateau 偵測 / outcome 分布 logging / `LevelConfig.max_subgoals_per_episode` 等欄位 | 2026-06-03 |
| T-D2 | 修 env reset→target race | `IsaacLabEnvInterface.reset` 加 zero-action warm-up step（V3 後改為 hold-in-place）| 2026-06-04 |
| T-D3 | eval 圖片 dump (Q3) | `--dump_images` flag + `meta.json` | 2026-06-04 |
| T-D4 | T-8 task-agnostic 放寬全套（T-8a/b/c + max_subgoals 25→40 + T-11 latency bug fix） | 詳見變更日誌 2026-06-04 | 2026-06-04 |
| T-D5 | V4 sensory-integration sub-stage L0a-L/R | `aiongenos/tasks/L0a_single_reach/` + `LEVEL_ORDER` + `active_arm` mask | 2026-06-08 |
| T-D6 | V4 首跑 5 ep on L0a-Left（run 571472d8） | F16-F18：mirror 消除但 grounding 仍是瓶頸 | 2026-06-08 |
| T-D7 | F19 STOP=True 假成功 bug 修 | `EpisodeOutcome.VLM_STOP_PREMATURE` + 手動清 false-success replay | 2026-06-10 |
| T-D8 | Playback infra（collect.py `--dump_images_root` + `playback_episode.py`） | 詳見變更日誌 | 2026-06-10 |
| T-D9 | Reasoning analyser + 完整 thought trace（不截斷 + new fields）| `reasoning_analysis.py` 四維 cross-round 報告 | 2026-06-10 |
| T-D10 | C3 pre-reach reset arm pose | `reset_joints_to_target_with_offset({joint2:0.5, joint4:0.8}, ±0.2)` | 2026-06-10 |

**進行中 / 高優先（active）**

| # | 任務 | 緣由 | 細節 | 狀態 |
|---|---|---|---|---|
| **T-12** | **C3 5 ep L0a-Left 實測**（pre-reach reset 在跑） | C3 commit 完成；驗證 EE Z std + reasoning trace 是否轉用 X/Y/Z + SR 是否突破 0 | PID 2793645，run id 待落盤；跑完跑 `replay_summary.py` + `reasoning_analysis.py` + `check_ee_randomness.py` | **🟡 in-flight** |
| **T-7** | collect ≥1 success replay → 觸發 Stage 4-A 二輪訓練 | M5 後續；C3 + V4 後預期可有 success | `scripts/run_collect.py` → `scripts/04_sync_and_train.sh` → reload student → eval 比較 SR | blocked by T-12 |
| T-9 | 增量訓練：每 N success episode 觸發 mini-LoRA | F11 顯示 episode 內 VLM 在學軸向但跨 episode 不延續 | (a) 每 5 success ep 觸發 04_sync_and_train.sh；(b) train script 改支援 incremental（從 410e0f79 base 接續）；(c) student 自動 reload；(d) 後續 collect 用更新後的 student 形成正向循環 | **idea / blocked by T-7** |
| T-13 | reasoning analyser 跨 ep 統計：「VLM 是否在 N ep 後出現 X+/Y+/Z+ 軸向 token」 | F24 證 14 round 內 0 軸向 token；想知道是否多 ep 累積後會自然湧現（self-emergence proof）| reasoning_analysis.py 加 `--cross_run` 模式，掃整 run 目錄產 ep×round 大表 | open |
| T-3 | Grounding sanity baseline (plan §M1) | 量化 bias / variance；現在 C3 改完視覺後是好時機 | `scripts/grounding_sanity.py`：固定 reset state，不執行動作只重複 query 20 次；報告 mean / std / GT | open |
| T-5 | collect.py 同步 multi-round | 已隨 V4/T-D5 對齊，但 collect 結尾 critic retry 邏輯需要 review | 已並用 EpisodeConversation；critic 邏輯已併入 round loop | mostly done / 待 audit |
| T-6 | E4B student 是否退役？ | 目前 student=31B+LoRA `410e0f79`，E4B 暫不用；future Stage 4-B CoT-strip 仍需小模型 | 等 31B 訓練收斂後再決定；若 31B 速度可接受可暫不退 | open / low |
| T-8a-B | randomize 初始 EE pose — Plan B fallback | C3 已用 task-space target，joint Z 自由度仍小；若 C3 後 Z std 仍 < 3 grid 才用 IK reset | `aiongenos/curriculum/reset_ik.py` stub 已寫 | scaffolded / deferred |

**已取消 / 暫緩（cancelled / deferred）**

| # | 任務 | 否決原因 |
|---|---|---|
| X-1 | Q6 absolute/delta mode 切換 | 違反 task-agnostic（依 GT distance 切換是場外資訊）；改用「拉高 round 數 + critic feedback」（T-1）取代 |
| X-2 | prompt 加 axis convention | user 否決：違反「對新生兒一樣」原則，等於把任務特定知識手工注入 → Q9 |
| X-3 | image-relative bbox + 反投影 | 同上 task-specific 過重 |
| X-4 | RGB 飽和度增強 | user 確認原圖人眼可辨 |
| X-5 | 修 camera 視角 | F4 已降級 — R2+ 已可見，R1 偶爾被手臂擋只是次要 |


---
## 重要發現
| 編號 | 內容 | 發現原因 | 細節 | 衍生todo項目 | 登錄時間 | 最後更新 | 狀態 |
|---|---|---|---|---|---|---|---|
|F1| Multi-round 沒救 SR；VLM grounding 主要是 high variance 而非 bias | 跑 5 ep × teacher+student multi-round eval（max 4 round / ep）；Ep1 R1 right_dist=10.6cm 接近 success，R2 同 VLM 把目標移到完全不同位置 → dist 退到 31.5cm；多次重複此 pattern | 同一物體在連續 round 的座標預測互相不一致；teacher 與 student 都有此問題，但 student grounding err 累積比 teacher 多 7 cm（38 vs 31） | #03 grounding variance 對策、#04 bias/variance 分離量化 | 2026-06-03 | 2026-06-03 | active |
|F2| 蒸餾本身沒劣化品質 | 兩端 grounding error 在 single-shot 條件下幾乎一致（32 vs 33cm） | 確認 LoRA `a318eb38` 訓練流程沒有引入額外 error，瓶頸完全在 base VLM 對 sim RGB 的 grounding 能力 | 等 31B base 切回後重驗（#05） | 2026-06-03 | 2026-06-03 | active |
|F3| Multi-round Plateau 偵測有效 | 5 ep 中 plateau:3 + max_rounds:2，無 episode 浪費全部 4 round | 連 2 round best_combined 進步 < 1cm 就跳出，平均省 0.6 round / ep；省下的 VLM call 數可分配給下一 episode | — | 2026-06-03 | 2026-06-03 | active |
|F4| R1 VLM 看到的是接近空桌面（次要） | `round_01_pre.png` cube 被機器人手臂遮住大半；R2/R3 看得到 cube 後仍估錯方位 | 不是主因，主因見 F5。R1 fallback 之後 R2+ 看到場景但仍系統性錯估方位 | — | 2026-06-03 | 2026-06-03 | secondary |
|F5| **真正根因：VLM 座標系 mismatch — 把螢幕座標當 robot base frame** | R2 thought：「red cube at (-30, 20, 0)」；R3 thought：「red X=-40」；GT 紅 cube_L = (+25, +20, +46) **X 全正**。VLM 看到紅 cube 在畫面左下 → 用螢幕直覺估 X=-30/-40（負），但真實 base frame `+X = 機器人正前方`、`+Y = 機器人左手邊`、`+Z = 上`，紅 cube 在機器人左前方 → 真實全正 | prompt 沒告訴 VLM 軸向：`X=` 是哪一軸？對應螢幕哪個方向？整套[-100,100]整數網格定義不明 | #16 prompt 加 axis convention；或 #17 改用 image-relative bbox | 2026-06-03 | 2026-06-03 | **CRITICAL** |
|F5b| VLM thought 與最終 output 矛盾 | R3 thought 說 X=-40，output 是 X=-3（差 13×）；R2 thought (-30,20,0) → output (1,8,35) | VLM 自己也搞不清 thought 用的座標 vs `[-100,100]` 整數網格的關係，無 calibration | 同 #16 prompt 強化 | 2026-06-03 | 2026-06-03 | active |
|F6| R1 grounding 7.6 cm 是巧合而非真實能力 | VLM 對稱 fallback 輸出 (24, ±16, 35) 恰好接近 GT (25, ±20, 42) 對稱結構 | 之前以為「R1 已近 success」是好兆頭，實際是運氣；之前提的 Q6/Q7 設計建在錯誤的 finding F1 上 | Q6/Q7 暫緩，先解 F4 | 2026-06-03 | 2026-06-03 | active |
|F7| 之前 multi-round high variance 推論被 F4 推翻 | 既然 R1 是 fallback、R2+ 才看到實景，「不同 round 預測不一致」其實是「fallback 跳到實際估計」的單次跳躍而非真 variance | 真正的 variance 量化需要在「目標可見」前提下做（plan §M1 grounding sanity） | #14 grounding sanity baseline | 2026-06-03 | 2026-06-03 | active |
|F8| **31B + critic feedback 已多次接近成功**，純差最後一公里 | run 85ccf9a4（6/10 ep 完成）：a6d8a98c R5 R-arm dist=10.3cm（離 success 5.3cm）；2cc6efdb R7 R-arm=12.7cm、R11 雙臂 15.7/18.8cm；0b96a2ac R6 雙臂 17.8/22.0cm | best_combined 平均 40.2cm，多次單臂進入 < 15cm 區間；不是「VLM 完全錯」而是「微調精度不足」。`scripts/diagnostics/replay_summary.py` 工具產出 | 放寬 success threshold 0.05→0.08；或加 stage5 fine-tune step | 2026-06-04 | 2026-06-04 | **active / breakthrough signal** |
|F9| **best_combined 後的 round 把好位置丟了**（true plateau false alarm） | 2cc6efdb R11 雙臂 dist 15.7/18.8（best），R12 VLM 出新絕對 target (35,±35,-40)，IK 60 step 把臂從 R11 終點拉走 → R12 end 33.5/42.0 | VLM 不知道「上 round 已很接近，這 round 應該微調而非重新 plan」；當前 EpisodeConversation 雖然有 history，VLM 看不出 success threshold 的概念 | 給 VLM 顯式提示「若 dist < 10cm 應微調 (delta ≤ 5)」；或 plateau patience 改成 monotone-improvement-vs-rolling-window 而非 best_combined | 2026-06-04 | 2026-06-04 | active |
|F10| Plateau patience=5 提早殺 episode | 6/6 episode 最後 3 round 仍有顯著動作（>2cm 變化），但 best_combined 停滯就被 plateau 切斷 | 例：a6d8a98c best=33.8 在 R5 達成、R6-11 都沒再破，但 R5/R7 R-arm 仍從 9 → 24 → 28 變動（VLM 沒卡住，是 best 公式太嚴）。當前 plateau_patience=5 應該至少改 8-10，或改用「last-N rounds 平均改善」 | T-1 拉高 round 上限不夠，還要鬆綁 plateau；T-8 新增 | 2026-06-04 | 2026-06-04 | active |
|F11| VLM 在 episode 內顯示真實學習軌跡 | a6d8a98c thought 序列：R1 (-20,15,-45) → R5 (-30,20,-60) → R11 (-35,17,-60)，X 收斂、Y 微調、Z 加深；2cc6efdb 從 R1 (-15,20,-30) 學到 R11/12 (30/35, ±35, -40)，X 從負翻正（軸向自學成功） | 證 critic feedback 系統有效；代表 success replay 一旦取得，蒸餾資料品質會非常高（含完整 reasoning trace）。但這些直覺**目前每 episode 從零開始**，因為沒有跨 episode 跑增量訓練 | T-7 一個 success episode 落盤後立即觸發 04_sync_and_train.sh；T-9 增量訓練思路 | 2026-06-04 | 2026-06-04 | active |
|F12| ~~Latency 異常增長 50s→340s/call~~ **REVOKED**：診斷工具 bug | 用 `total_vlm_latency_ms` 除以 round 數，但 collect.py 把 `total_vlm_latency_ms` 當 process-cumulative 累計器，沒每 episode 重置，導致越後面 episode 顯示越長 avg/call。實際每 round latency = 45-58s 全程穩定 | 修正：診斷工具改用 sum(per-round latency_ms)。teacher 確認 n_ctx=16384 已就緒，**不需重啟** | — | 2026-06-04 | 2026-06-04 | **revoked** |
|F13| Teacher n_ctx=16384 已就緒、但 student n_ctx=2048（per-slot 1024） | `curl :18888/props` & `:18889/props` 確認 | collect 階段只用 teacher → 不影響當前；之後 eval student 時必須升級 student | T-4b：student n_ctx 升級至 8192（CTX_SIZE 環境變數重啟 18889） | 2026-06-04 | 2026-06-04 | active |
|F14| **collect.py `total_vlm_latency_ms` 累計沒重置** | F12 root cause：collect.py 把同一 stat 物件跨 episode 累積，replay 寫入時直接寫 stat 累計值 | replay 欄位 `total_vlm_latency_ms` 不能信，必須改用 sum 個別 `interaction.latency_ms` | T-11 修 collect.py per-episode reset；補 sanity test | 2026-06-04 | 2026-06-04 | **bug** |
|F15| **`reset_joints_by_scale` 對 OpenArm 結構性無效**（重大隱性 bug） | 10/10 ep 初始 EE 全在 (-33,±33,-54)，最大差異 1-3 grid（≤1cm）。原因：OpenArm default joint pos 中 joint2/5/6/7/finger 預設值=0，scale 函數是「乘」default → 0×任何=0；只有 joint1/3/4 (1.57/-1.57/1.57) 會被擾動但落到 EE 也只是小位移 | 結果：之前所有 collect / eval 全是「同一張視覺場景」訓練，根本沒驗證泛化。Plan §M1 grounding sanity 標準（20 張多樣 RGB）實質沒滿足 | T-8a 換 `reset_joints_by_offset`（offset 而非 scale）解決 | 2026-06-04 | 2026-06-04 | **CRITICAL bug** |
|F16| **V4 sub-stage 完全消除 mirror bias** | run 571472d8 5 ep on L0a-Left：4/5 ep X-flipped 0%；對照 V3 同等條件 33-100% | 證實「mirror bias 是 dual-arm 任務 above-competence 的副產品」(SI 假說)；single-arm task 隔離後就消失 | F18 grounding 才是真瓶頸 | 2026-06-08 | 2026-06-08 | **active / V4 win** |
|F17| **Hold-in-place mask 100% 正常工作** | run 571472d8 5 ep × 全 round 右臂預測都被 `IsaacLabEnvInterface.execute_command(active_arm)` 強制覆寫成 init pose；replay 中 vlm_right_pos_int 任意但 sim 中 EE 不動 | 證實 `active_arm` 機制可用於後續 task 中任何「該臂不該動」的子任務 | — | 2026-06-08 | 2026-06-08 | **active** |
|F18| **mirror bias 解除後 SR 仍 0/5 → grounding 才是真瓶頸** | run 571472d8 SR 0/5；4 個真 timeout 的 final_L 都 22-42 cm；F8 之前看到的 best_combined 改善是 V3 + critic feedback 合力，不是 V4 直接貢獻 | 把問題從複合（mirror+grounding）拆成單純（grounding only），下一步討論才能聚焦 | F24-F27 主因深挖 | 2026-06-08 | 2026-06-08 | **active** |
|F19| **STOP=True 假成功 bug** | 571472d8/b0c28c0a outcome=success rounds=1 final L=37.1cm（離閾值很遠）；collect.py 看到 stage1.stop=True 就無條件 SUCCESS，未驗距離 → false-success 會污染訓練資料 | commit `53948b4` 修：新增 `EpisodeOutcome.VLM_STOP_PREMATURE`；保留真 SUCCESS 分支（dist 過閾值才算）。手動把該 ep 改 outcome 並搬到 failure/。 | T-7 訓練前再 audit 全部 success replay | 2026-06-10 | 2026-06-10 | **fixed** |
|F20| **場景全灰階、cube 5×5 px** | 5 個 V4 ep start/end PNG (256²)：天空淺灰 / 地面深灰 / 機器人黑白；唯一非灰物件 = 紅 cube ≈ 0.4% 影像面積 | VLM 從稀疏視覺找小紅點 + 估 base frame 座標，太難。Plan §M0 場景設計沒考慮 grounding sanity 條件 | C5 cube 放大；C1 桌面（暫緩） | 2026-06-10 | 2026-06-10 | **active / 視覺層** |
|F21| **Cube 永遠在「畫面左下偏左」** | 5/5 ep cube 出現在影像 (x≈70-90, y≈140-180)；但 GT base frame X 全正、Y 0.15-0.25。代表 camera 角度讓 base frame `+X = 畫面下、+Y = 畫面左` | VLM 用螢幕直覺映射「畫面左下 = 負座標」必然錯估方向 | C4 camera 調整（已試 pitch55/70 但 default 仍最佳） | 2026-06-10 | 2026-06-10 | **active / 視覺層** |
|F22| **Reset 雙臂大幅遮擋畫面下 1/3** | 4/5 ep start frame 機器人手臂佔畫面下半，cube 在下半時常被自己手臂擋住 | reset 預設姿勢直立，wrist 在 camera 視線下方 | C3 pre-reach 改 reset arm 到前伸姿勢（已實作） | 2026-06-10 | 2026-06-10 | **C3 fix in flight** |
|F23| **Reset 姿勢非 reach-ready** | OpenArm default joint pos 全 0 → 雙臂垂直；reach 前方 cube 必須先大幅 shoulder pitch | VLM 第一個 round 必然只是把臂往前甩，浪費 round 預算 | C3 改 `joint2=0.5, joint4=0.8` | 2026-06-10 | 2026-06-10 | **C3 fix in flight** |
|F24| **VLM 全程零 base-frame 軸向 reasoning** | run 67a99349/a047ccbe 14 round trace：thought 中 X+/X-/Y+/Y-/Z+/Z- token 命中 0/0/0/0/0/1；forward/backward/left/right 命中 67 次 | VLM 完全用螢幕語言、不用 base frame 軸向描述空間。即使 critic feedback 給整數座標 delta，thought 仍轉譯成方向詞而不是反思軸向 | 等 reasoning analyser 跨 ep 統計：是否會在 N ep 後出現軸向 token | 2026-06-10 | 2026-06-10 | **CRITICAL / F5 實證** |
|F25| **VLM 確實在思考新假設，不是 stuck** | thought consecutive similarity mean=0.09（極低）；regression / progress / correction / self_critique token 在多 round 出現 | critic feedback 真的被消化（thought 提及上 round 數值）；問題不在 prompt 設計 / context, 在 base VLM grounding 本身 | — | 2026-06-10 | 2026-06-10 | **active / 樂觀** |
|F26| **VLM 探索範圍合理但收斂不到位** | 14 round 中 best_L=26.6cm @ R8（接近 GT），R9-14 仍找不到比這更近的位置 | 不是 VLM 找不到方向，是 [-100,100] 整數網格 + 5cm 閾值下，要從「方向粗估」進到「精修」缺乏精度工具 | C5 閾值放寬 / cube 放大都會改變這個動力 | 2026-06-10 | 2026-06-10 | **active** |
|F27| **VLM 本質誤解：螢幕「左下」不等於 base frame 「X 負 Y 正」** | thought R3：「cube is in negative X region」；GT X 全正。VLM 看「畫面下方」直覺映射到「X 負」，但 base frame `+X = forward = 畫面下方` | F5 的具體實證；多輪 critic feedback 仍未矯正這個認知 → 證明 zero-demo + 純 observable feedback 不足以教軸向 | C3 改善視覺後再驗一次；若仍 0/5 則需重新討論 prompt 邊界 | 2026-06-10 | 2026-06-10 | **CRITICAL** |


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
