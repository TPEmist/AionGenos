# AionGenos — 開發追蹤 INDEX

> Embodied AI 開源研究框架。VLA 物理常識作為 System 2，蒸餾為 LoRA System 1，零示範雙臂任務。
> 計畫全文：[`docs/plans/01_poc_cognitive_evolution_pipeline.md`](docs/plans/01_poc_cognitive_evolution_pipeline.md)
> 最後更新：2026-06-02

---

## 當前狀態

- **Phase**：M7 進度完成，L3 pick & place 成功部署；遠端 QLoRA 訓練環境及 GGUF 熱重載（Reload）管道已全線打通；E4B+LoRA student multi-round L0 closed-loop eval 完成。
- **Sprint 目標**：已成功在遠端 GPU 伺服器驗證 QLoRA 微調流水線（以 E4B 作為 POC 模型成功完成 1 epoch 訓練收斂、GGUF 導出、元數據 patch、並部署熱重載，student:18889 + LoRA `a318eb38` 線上）。**Multi-round closed-loop 機制（Option A）跑通**：兩端 SR=0/5；teacher avg 3.4 round / grounding 31.0/22.8cm；student avg 3.8 round / grounding 38.2/26.9cm / speedup 2.06×。**關鍵發現**：VLM grounding 不只 bias 還是 high variance（同 episode 不同 round 預測互相不一致），純 multi-round 解不了 R1 風險。
- **最新動作與進展（2026-06-04）**：
  1. **遠端 SSH 與伺服器恢復**：遠端 148 主機已重啟，SSH 連線成功修復。已手動重新拉起遠端 Teacher (18888) 與 Student (18889) `llama-server` 服務。
  2. **多輪閉環 & Critic 機制部署**：完成 `collect.py` 與 `eval.py` 同步，整合 stateful `EpisodeConversation` 與 programmatic observable-only critic feedback。
  3. **Context Length 最佳化**：實作 `EpisodeConversation` 對話歷史自動清理機制，僅保留當前最新一輪 User Turn 的影像 `image_url`。
  4. **Teacher CoT Token 預算調升**：`max_tokens` 1024→2048；timeout 60→180s。
  5. **31B teacher 全面替換 + LoRA 410e0f79 線上**。
  6. **Run 85ccf9a4 進行中**（6/10 ep 完成）：6/6 timeout-plateau，**但 best_combined 平均 40 cm，多次單臂 < 15cm（F8 突破信號）**。VLM 在 episode 內顯現真實軸向自學軌跡（F11）。
  7. **診斷工具上線**：`scripts/diagnostics/replay_summary.py`，產出 round-by-round 收斂表與 plateau 分析。
  8. **發現 latency 異常增長（50s→340s/call，F12）**，強烈懷疑 teacher server `n_ctx=2048` 不夠 conversation history。
- **下一動作優先序**：
  - ✅ T-4 teacher n_ctx=16384、T-4b student 確認不擴張、T-8a/b/c/T-8(a)/T-11 全部完成（2026-06-04）
  - (P0) **等當前 5 ep collect (PID 2120953, run ae692e9d) 跑完**（每 ep ~14 min，5 ep 約 70 min）；診斷 EE 多樣性、SR、plateau 觸發點
  - (P1) 若 EE 多樣性足（std ≥ 3 grid/軸）→ 進 P2；若否 → 啟用 Plan B (T-8a-B IK reset)
  - (P1) 若 SR > 0/5 → 立刻觸發 `04_sync_and_train.sh` (T-7) 訓練新 LoRA → reload student → eval
  - (P2) 若仍 SR 0/5 但 best_combined 平均下降 → 加 collect 量；若 best_combined 不變 → 還有更深問題（如 prompt structure / VLM grounding 限制），回頭設計

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

## Curriculum Ladder（5 級）

| Lv | 任務 | 控制模式 | 狀態 |
|---|---|---|---|
| L0 | Bimanual reach to 2 cubes | EE position-only (3D × 2) | ✅ done |
| L1 | Bimanual trace waypoints | EE position chunk | ✅ done |
| L2 | Bimanual push | EE pos + pitch/yaw (5D × 2) | ✅ done |
| L3 | Bimanual pick & place（近物） | EE pos + RPY + gripper (7D × 2) | ✅ done |
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
| T-D2 | 修 env reset→target race | `IsaacLabEnvInterface.reset` 加 zero-action warm-up step | 2026-06-03 |
| T-D3 | 圖片 dump (Q3) | `--dump_images` flag → `data/eval_dumps/{stamp}/{teacher\|student}/{ep_id}/round_NN_{pre,post}.png` + `meta.json` | 2026-06-04 |

**進行中 / 高優先（active）**

| # | 任務 | 緣由 | 細節 | 狀態 |
|---|---|---|---|---|
| T-1 | 拉高 round 上限 + critic feedback 化 | user 哲學決定（Q9）：靠多輪 + critic 自我修正讓 VLM 自學軸向，禁止 prompt 注入軸向 | 已實作：max_subgoals=15, plateau_patience=5；critic feedback 每 round 注入 EpisodeConversation；run 85ccf9a4 6 ep 證明軸向自學成立（F11） | **done（基本機制）** |
| T-2 | Q7 — Round 間 conversation memory | VLM 每 round 從零開始；T-1 critic feedback 必須跨 round 累積才有意義 | 已實作：`EpisodeConversation` 含 image_url 自動清理，僅保留最新一輪 image | **done** |
| T-8 | task-agnostic 放寬組合 | 撐起 R2-R3 修正能力，給 VLM 學軸向直覺空間 | 拆成 T-8a/b/c + ep 加長，全 task-agnostic | **done（已實裝）** |
| T-8a | randomize 初始 EE pose — Plan A | F15：`reset_joints_by_scale` 對 OpenArm 結構性無效（5/7 joint default=0）| `AionGenosReachEnvBaseCfg.events.reset_robot_joints` 改用 `mdp.reset_joints_by_offset`，position_range ±0.2 rad，clamp 到 joint limits | **done** — 首 ep 驗 EE 初始位明顯偏離 fixed point |
| T-8a-B | randomize 初始 EE pose — Plan B fallback | 若 Plan A joint-space 隨機後 IK 仍偏到不自然姿態 | `aiongenos/curriculum/reset_ik.py` stub 已寫；task-space 隨機 EE 用 `DifferentialIKController` solve；trade-off：每 reset +5-10ms vs joint-space near-zero | scaffolded / **deferred until Plan A 證不夠** |
| T-8b | plateau 公式 last-N rolling mean | F10：best_combined monotone 公式把 VLM 振盪當 plateau | `eval._run_episode` & `collect._run_episode` 都改：比較最近 `plateau_window=3` round 平均 vs 再前 window 平均，差 < `plateau_min_progress=1cm` 才算停滯，連續 `plateau_patience=5` round 沒進步才殺 | **done** — 首 ep 跑 17 round 才 plateau |
| T-8c | sub-goal 60→30 step | VLM 1Hz→2Hz，plan §3.5.5 路徑；給 VLM 更密視覺反饋 | `LevelConfig.sim_steps_per_subgoal` 60→30，等價 0.5s/round | **done** |
| T-8(a) | 單 ep 加長 max_subgoals 15→25 | T-8c 把 sec/round 砍半後補回 round 預算 | `LevelConfig.max_subgoals_per_episode` 15→25 全 level | **done** |
| T-4 | Teacher server `n_ctx`=16384 確認 | 透過 `:18888/props` 直接查得，已是 16384 不需重啟；F12 latency 爆炸是診斷工具 bug 不是真問題 | 驗證指令：`curl -s http://10.80.9.148:18888/props \| python3 -c "import sys,json,d=json.load(sys.stdin);print(d['default_generation_settings']['n_ctx'])"` | **done** |
| T-4b | ~~Student server n_ctx 升級~~ | user 否決：student 用 `--reasoning off --reasoning-budget 0` 輸出短，2048 ctx 足夠（不像 teacher 要承受長 CoT） | — | **cancelled** |
| T-11 | 修 collect.py `total_vlm_latency_ms` per-episode 沒重置 bug | F14：CollectStats 物件跨 episode 累積，replay 欄位不能信 | `aiongenos/orchestrator/collect.py` 在 `for ep_idx` 開頭 reset `stats.total_vlm_latency_ms=0`；或寫 `episode.total_vlm_latency_ms = sum(i.latency_ms for i in vlm_interactions)` | **open / 高優先 (lossless data fix)** |
| T-3 | Grounding sanity baseline (plan §M1) | 量化 bias / variance，當前用 GT 距離但模型只看 RGB → sanity-check 必須在 prompt 改後 | `scripts/grounding_sanity.py`：固定 reset state，不執行動作只重複 query 20 次；報告 mean / std / GT | open / blocked by T-1 |
| T-4 | Teacher server `n_ctx` 加大至 16384 | T-2 conversation memory 需要 ≥16K context；plan §M0 Q1 早已標記 | 請 user 重啟 `:18888` teacher 加 `--ctx-size 16384` | awaiting user |
| T-5 | collect.py 同步 multi-round | eval.py 已 multi-round，collect 仍 single-shot+1 critic retry → 訓練資料分布不對齊 | 把 `run_collect_loop` Stage 1 包進 round loop，重用 eval 的 `_run_episode` 終止邏輯 | open / blocked by T-1 |
| T-6 | 切回 31B teacher 重 baseline | 目前 student=E4B+LoRA `a318eb38`；31B base 下載完成後重跑 5-10 ep eval | check `~/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF*.gguf` 完整 | open |
| T-7 | collect 寫 ≥100 success replay 啟動 Stage 4-A 二輪 | M5 後續，blocked by T-8（rules 鬆綁後才能取得 success） | `scripts/run_collect.py` → `scripts/04_sync_and_train.sh` → reload student → eval 比較 SR | blocked by T-8 |
| T-9 | 增量訓練：每 N success episode 觸發 mini-LoRA 增量更新 | F11 顯示 episode 內 VLM 在學軸向但跨 episode 不延續；越早把直覺進權重越好 | (a) 每 5 success episode 觸發 04_sync_and_train.sh；(b) train script 改支援 incremental（從 410e0f79 base 接續而非 from-scratch）；(c) student 自動 reload；(d) 後續 collect 用更新後的 student 收集更多 success 形成正向循環 | **idea / blocked by T-7** |
| T-10 | 診斷工具：`scripts/diagnostics/replay_summary.py` | 看 round-by-round 收斂、plateau 觸發點、latency 趨勢 | 已實作；用法 `python3 scripts/diagnostics/replay_summary.py [--run RUN]` | **done** |

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
