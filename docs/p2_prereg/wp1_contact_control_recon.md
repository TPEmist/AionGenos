# WP1 = 閉環接觸控制 — 現成方案盤點(技術偵察一頁)

**Status**: 偵察交付(不動工)。供 WP1 開工裁決。
**Date**: 2026-08-03 (isaac session, master).
**isaac 核實註記(2026-08-03)**:交付前程式驗證了兩個影響裁決的根節點宣稱 ——
(1) 當前全 pipeline 走純 `DifferentialInverseKinematicsActionCfg`(零力控):
✓ 確認(`aiongenos/control/action_modes.py`、`aiongenos/tasks/L2_dual_push/
dual_push_cfg.py:74`);(2) IsaacLab 原生有 `OperationalSpaceControllerActionCfg`
含 wrench 力控:✓ 確認(`IsaacLab/.../mdp/actions/actions_cfg.py:299`,含
`wrench_scale`/`stiffness_scale`/`damping_ratio_scale` 欄位)。grasp 模組的
成熟度/授權宣稱為 agent 的外部調查,未逐一程式驗證(接入時再驗)。

---

> 現況錨定 (repo 實測):L0–L3 全部走 `DifferentialInverseKinematicsActionCfg(command_type="pose", ik_method="dls", use_relative_mode=False)`,純絕對位置 IK servo,**全 pipeline 無任何力/力矩/剛度通道**。Action space 6/14/16 維 = position(+quat)(+1-bit 二值 gripper)。所謂「原語」實為整數格點子目標 + gripper bit (`MetricCommand`/`BimanualCommand`),非符號 verb 詞彙。成功判據 = 雙 EE 落在目標 5 cm 內;`terminated` → `collision`。這正是兩道牆的程式證據:開環 servo + 固定巨集介面。

## 偵察三項

### 1. robosuite / IsaacLab 阻抗控制參數
- **IsaacLab `OperationalSpaceControllerActionCfg`**(`isaaclab.envs.mdp`,底層 `OperationalSpaceController` + `Cfg`)— 成熟度 **research→production**(在 stable API,非 experimental,GPU 向量化,但 rebrand 後才加、track record 短)。**接入成本:低–中** — 就在我們已用的 IsaacLab action-term 體系內,直接把 task cfg 的 `DifferentialInverseKinematicsActionCfg` 換成它。原生支援 `impedance_mode ∈ {fixed, variable, variable_kp}`、`motion_stiffness_task`、`motion_damping_ratio_task`,**且獨有顯式力控**:`contact_wrench_control_axes_task`、`contact_wrench_stiffness_task`(None=開環,否則閉環力控)、`target_types` 收 `"pose"`/`"wrench"`。
- **robosuite `OSC_POSE`** — 成熟度 **production**(原生老功能,RL manipulation 文獻大量引用)。`impedance_mode` 同一套分類、`kp`(預設150)/`damping_ratio`/`kp_limits`。**接入成本:中–高** — robosuite 是另一 sim stack,對本專案僅作參數/範式參照,不建議為它換底盤。
- **關鍵風險**:阻抗增益需 per-task 調(kp/damping),接觸穩定性 vs 追蹤精度取捨;IsaacLab OSC 較新,雙臂 + 我們自訂 openarm URDF 的相容性需 smoke 驗證。

### 2. learned grasp 模組接入成本
- **輸入/輸出橋接:低**(關鍵好消息)。所有模組輸出剛體 SE(3) grasp pose(3×3 R + t)+ width + score,rotation→quaternion 一行 (`scipy Rotation`),**直接對上我們現有的絕對 pose action 介面**(14/16 維的 pos+quat)。唯一實工是 frame transform:輸出在**相機系**,須左乘 camera→base 外參(手眼標定的已知 4×4;graspnetAPI 有 `Grasp.transform(T)`)+ 固定 TCP/approach-depth offset。無需軌跡/速度介面。
- **候選 & 成熟度**:
  - **Contact-GraspNet**(NVlabs,research)— 輸入 depth+intrinsics 最乾淨、直接給 width。**風險/成本:中–高** — TF2.2/CUDA11.1 過時 stack,PointNet2 op 重編,需獨立 env/容器。
  - **GraspNet-baseline**(SJTU,research)— PyTorch1.6 + 自訂 CUDA op;非商用授權。**成本:中**。
  - **AnyGrasp**(production 導向,real-time/tracking)— 效能最佳但 **license-key 閘 + MinkowskiEngine 編譯**,閉權重不可 fine-tune。**成本:高**。
  - **Edge-Grasp-Network / GIGA**(ICRA23/RSS21,research)— **MIT 授權 + 現代 PyTorch + 附權重**,最無授權/依賴摩擦(GIGA 需 TSDF 前端;Edge-Grasp 點雲原生、快)。**成本:低–中,推薦作首選原型**。
- **關鍵風險**:需 GPU 推論(與 IsaacLab 爭 GPU0,見 MEMORY server 佔用);相機系→base 外參在 sim 中須從 IsaacLab camera cfg 取 extrinsic,錯一個 frame 就整批 grasp 歪掉。

### 3. twist / press 原語實作路徑
- **press(受力下壓):需力控回饋** — 純運動學會複製「撞進物體被彈開」的第一道牆。正解是**依賴項目 1 的阻抗/wrench 通道**(`contact_wrench_stiffness_task` 對 z 軸設限力),而非加軌跡。**成本:中,但 gated on WP1-①**。
- **twist(繞軸轉):混合** — 幾何上可純運動學擴充(繞鉸鏈軸的參數化弧線軌跡:軸位置+半徑+Δθ),但要真正「轉開爐旋鈕」須沿弧施非零切向力矩 → 仍需阻抗控制讓 EE 順從鉸鏈約束。**成本:中–高**。
- **介面工作**:兩者都要擴 `MetricCommand`/`BimanualCommand` schema(新增 axis/angle 或 force-target 欄位)+ Stage1/Stage2 解析 + train/eval format-contract(見 MEMORY:此為 4× 復發 bug 家族,務必先跑 format-contract gate)。
- **關鍵風險**:VLM teacher 需能表達新自由度的整數化參數;scalar_guard 量化須擴充且不破壞既有 position/rpy 契約。

## 技術路線建議 (優先序 + 依賴鏈)

1. **① IsaacLab OSC 阻抗控制** — **先做,解鎖最多**。它同時打掉第一道牆(接觸精度)並為 press/twist 提供力控基座。是 ③ 的硬依賴,且對 ② 的抓取穩定性(順從接觸不彈飛)也有正面外部性。**依賴鏈根節點**。
2. **③ twist/press 原語** — 緊跟 ①(press 完全 gated on ① 的 wrench 通道;twist 幾何部分可與 ① 並行預研)。
3. **② learned grasp** — 相對獨立(輸出橋接已驗證為低成本),可與 ①/③ **並行**;但抓取「不彈飛」的最終品質仍受益於 ① 的順從接觸。建議先接 MIT 授權的 Edge-Grasp 做可行性,避免 AnyGrasp/GraspNet 授權談判。

依賴圖:`① OSC ──→ ③ press/twist`;`② grasp ∥ (受益於 ①)`。

## 成本估計 (相對量級,不用工時)

| 項 | 相對複雜度 | 依賴鏈長度 | 是否需新訓練 |
|---|---|---|---|
| ① OSC 阻抗 | 低–中(換 action term + 調增益) | 根節點,0 前置 | 否(控制器換裝,teacher prompt 端可能需重述) |
| ② learned grasp | 中(推論環境 + frame 外參 + GPU 調度) | 短(獨立,橋接已知) | 否(用預訓練權重;Edge-Grasp 附 MIT 權重) |
| ③ twist/press | 中–高(schema + 解析 + format-contract + 力控整合) | 最長(gated on ①) | 可能(VLM 需學新自由度參數化;視 distill 策略) |

## 開工裁決 — PI 已拍板(2026-08-03)

**Q1(控制器換裝範圍)→ 只在新接觸任務(L4+/LIBERO 類)引入 OSC;
L0–L3 保持 DiffIK,不回換。**
理由:P1 全部數字綁 DiffIK provenance,回換作廢可比性、重跑 provenance
零科學收益;position 任務不需力控,按任務族分配控制器是正當設計。
**配套規則(寫死):** 任何新任務**收第一筆資料前,控制器選擇先 pin 進
provenance**,不允許「先跑跑看」的懸置。→ 控制器選擇進 format-contract /
provenance gate,與 train/eval 契約同級。

**Q2(grasp 授權)→ MIT Edge-Grasp,帶預先承諾的升級規則。**
Edge-Grasp 先行,**gate smoke 定生死**;若 fail **且診斷指向 grasp 模組
本身(非介面/frame transform)**,AnyGrasp 作為 **disclosed exception**
重議。理由:端到端可複現是本研究線的品牌資產,license-gated 閉權重元件
與之相斥;但 minimum-competence floor 的風險真實,故升級路徑**現在寫死
而非到時即興**([[minimum-viable-competence-law]] 的 grasp 面)。

**Q3(twist 驗收)→ 物理達成。**
驗收判準 = **環境自身的 success predicate**(hinge joint qpos 變化,如爐子
的 ≥0.5 rad),**不用幾何軌跡替代**。理由:Gate 2 驗屍的教訓正是「EE 幾何
到位、力矩為零、hinge 不動」—— 幾何驗收會在 primitive 層重演它。**接受 ③
真正 gated on ①(wrench 通道),不用驗收定義鬆動去繞。**

---

## 與 P2 prereg 的交會點(isaac 補註)

P2 prereg 骨架 §6 第 3 項的未決問題(P2 任務套件是否需要接觸控制 unlock)由本偵察回答:**若 P2 要一個「條件結構豐富到值得逐代固化」的任務,①OSC 是最低成本入口** —— 推壓的所需力方向依接觸幾何而非僅目標位置(l2_prereg 已預見「push 比 reach 帶更多條件結構」),接觸控制正好放大 conditional 成分,是 r-tracking 有訊號可爬的前提。裁決問題 1(換裝範圍)直接影響 P2 是否重用 L2-family 任務或另起 L4+ 接觸任務。
