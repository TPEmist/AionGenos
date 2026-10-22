# Comparator Audit: Rung-2 (`3e8c52d4`) vs Rung-2′ (`71134939`) Z-Distribution and Height Anchoring

**Auditor Role:** `prose_disc`  
**Date:** 2026-10-22  
**Target Runs:** Rung-2 (`3e8c52d4`) vs Rung-2′ (`71134939`), evaluated on paired seeds 5000–5049 (50 episodes each).  
**Core Question Under Test:** Test the pre-registered claim in [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md#L2323): *"With history and feedback, the teacher anchors on its current Z and corrects only x/y."* Does Rung-2′'s z-anchoring appear from Round 2 onward (as a history effect)?

---

## 1. Executive Summary & Verdict on the Core Claim

### Primary Verdict: PARTIALLY REFUTED, PARTIALLY CONFIRMED (A Dual Mechanism)

1. **Origin of Height Anchoring is NOT History/Feedback (REFUTED):**
   - In Rung-2′, **46/50 episodes (92.0%) ALREADY target $Z=53$ in Round 1** (mean $Z=52.66$, median $53.0$).
   - In Round 1, **no within-episode history exists** (turn 0 of `EpisodeConversation`) and **no critic feedback exists** (`prev_fb is None`, 0/50 round-1 feedbacks).
   - Furthermore, in Rung-2 (`3e8c52d4`), Round 1 targets also started high (mean $Z=50.76$, 50.0% at $Z=53$, 100% at $Z \ge 45$), and for the initial seeds 5000–5007 before cross-episode memory accumulated, **both runs chose $Z=53$ at 100% (8/8 seeds)**.
   - Therefore, the claim that history/feedback *caused* the agent to anchor at $Z=53$ is empirically **false regarding the root origin**. The initial height anchor is an artifact of the standby proprioception prompt default (`CURRENT STATE: LEFT_EE_POS = (44, 35, 53)`).

2. **Persistence and Inability to Escape is Driven by History + Feedback (CONFIRMED):**
   - While Round 1 starts high in both runs, **Rung-2 and Rung-2′ diverge radically at Round 2**:
     - **Rung-2 (stateless):** At Round 2, $Z=53$ collapses from **50.0% to 2.0% (1/50)**. 72.0% of episodes drop directly into the cube-contact height band $Z \in [30, 40]$ (mean $Z$ drops from 50.76 to 30.86, median drops to 30.0). Over rounds 2–12, $Z=53$ is chosen only **1 time out of 544 rounds (0.18%)**. Across the full run, Rung-2 episodes exhibit active vertical exploration (mean 6.44 unique $Z$ values per episode; 0/50 episodes keep $Z$ constant).
     - **Rung-2′ (history + feedback ON):** At Round 2, **90.0% (45/50) remain frozen at $Z=53$**. Over rounds 2–12, $Z=53$ accounts for **463 / 547 rounds (84.64%)**. In **38/50 episodes (76.0%)**, the model commands $Z=53$ for all 12 rounds without a single vertical change. In **41/50 episodes (82.0%)**, $Z$ has zero variation across all rounds.
   - **The Mechanism of the Lock-in:** The 3D Euclidean scalar distance feedback (`Fingertip-to-cube distance`) paired with top-down camera imagery acts as a **false gradient trap**. Standby $Z=53$ hovers ~4.3 cm above the cube top ($Z \approx 49.2$). When the teacher moves in $(X, Y)$, the 3D scalar distance fluctuates (e.g. 5.9 cm $\to$ 5.6 cm), giving the illusion of approach. The multi-turn conversation context locks the teacher into iteratively responding to the critic's generic prompt (*"Try a different direction or larger step size"*) within the 2D plane, reinforcing the belief that the remaining ~4.5 cm gap is an $XY$ misalignment rather than a vertical gap.

---

## 2. Provenance, Artifact Verification, and Scope

- **Rung-2 Run ID:** `3e8c52d4`
  - Documented: [wp3a_push_provenance.md:2003](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md#L2003)
  - Data paths: `data/collect_dumps/3e8c52d4/` (50 episodes, 594 rounds), `logs/push_smoke_3e8c52d4.json`
  - Flags: `obs_rung="2"`, `memory_on=True`, `top_view=True`, `round_feedback=False`, `round_history=False`
- **Rung-2′ Run ID:** `71134939`
  - Documented: [wp3a_push_provenance.md:2277](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md#L2277)
  - Data paths: `data/collect_dumps/71134939/` (50 episodes, 597 rounds), `logs/push_smoke_71134939.json`
  - Flags: `obs_rung="2"`, `memory_on=True`, `top_view=True`, `round_feedback=True`, `round_history=True`
- **Seeds:** Exactly 5000–5049 in both runs (50 paired episodes).
- **Physical Coordinates:** Workspace bounds $Z \in [0.0, 0.7]$ m. Standby TCP is $Z_{\text{int}}=53 \implies Z=0.5355$ m. Table surface is $Z=0.444$ m, cube center is $Z=0.4682$ m (half-height 0.024 m), cube top is $Z=0.4922$ m. Cube contact band is $Z_{\text{int}} \in [30, 40] \implies Z \in [0.455, 0.490]$ m.

### Reproducible Verification Command
```bash
python3 /home/control/audit/rung2p_diag/scratch_prose_disc/compare_z.py
```

---

## 3. Aggregate Statistical Comparison

| Metric | Rung-2 (`3e8c52d4`) | Rung-2′ (`71134939`) | Difference / Significance |
|---|:---:|:---:|---|
| **Total Evaluated Rounds** | 594 | 597 | 50 paired seeds |
| **All-Round Target $Z=53$ Count (%)** | 26 / 594 (**4.38%**) | 509 / 597 (**85.26%**) | +80.88% mass at standby height |
| **All-Round Target $Z \in [30, 40]$ (%)** | 317 / 594 (**53.37%**) | 13 / 597 (**2.18%**) | Contact band wiped out in Rung-2′ |
| **Episodes with 100% Rounds at $Z=53$** | 0 / 50 (**0.0%**) | 38 / 50 (**76.0%**) | 38 seeds never varied from standby |
| **Episodes with Zero $Z$ Variation** | 0 / 50 (**0.0%**) | 41 / 50 (**82.0%**) | 38 at Z=53, 2 at Z=50, 1 at Z=45 |
| **Unique $Z$ Target Values per Ep (Mean $\pm$ Std)** | **6.44 $\pm$ 1.64** (min 3, max 10) | **1.32 $\pm$ 0.84** (min 1, max 5) | Active vertical search vs frozen |
| **Round 1 Target $Z=53$ (%)** | 25 / 50 (**50.0%**) | 46 / 50 (**92.0%**) | Both runs start high (100% $Z \ge 45$) |
| **Round 1 Target $Z$ (Mean / Median)** | 50.76 / 51.5 | 52.66 / 53.0 | Standby proprioception anchor |
| **Round 2 Target $Z=53$ (%)** | 1 / 50 (**2.0%**) | 45 / 50 (**90.0%**) | **Rung-2 escapes; Rung-2′ locks in** |
| **Round 2 Target $Z \in [30, 40]$ (%)** | 36 / 50 (**72.0%**) | 0 / 50 (**0.0%**) | Rung-2 immediately seeks table |
| **Rounds 2–12 Target $Z=53$ (%)** | 1 / 544 (**0.18%**) | 463 / 547 (**84.64%**) | Total divergence post-Round 1 |
| **Rounds 2–12 Target $Z$ (Mean / Median)** | 21.32 / 30.0 | 51.90 / 53.0 | $\Delta Z_{\text{median}} = 23$ grid units (~16 cm) |

---

## 4. Round-by-Round Dynamics (R01 to R12)

The transition between Round 1 and Round 2 exposes the core mechanism:

| Round | Rung-2 Mean (Std) [Med] | Rung-2 % $Z=53$ | Rung-2 % $Z \in [30,40]$ | Rung-2′ Mean (Std) [Med] | Rung-2′ % $Z=53$ | Rung-2′ % $Z \in [30,40]$ |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **R01** | 50.76 (2.63) [51.5] | 50.0% | 0.0% | 52.66 (1.31) [53.0] | 92.0% | 0.0% |
| **R02** | **30.86 (10.46) [30.0]** | **2.0%** | **72.0%** | **52.50 (1.69) [53.0]** | **90.0%** | **0.0%** |
| **R03** | 29.32 (12.29) [35.0] | 0.0% | 68.0% | 52.50 (1.69) [53.0] | 90.0% | 0.0% |
| **R04** | 25.32 (15.12) [30.0] | 0.0% | 66.0% | 52.50 (1.69) [53.0] | 90.0% | 0.0% |
| **R05** | 23.46 (16.54) [30.0] | 0.0% | 58.0% | 52.44 (1.72) [53.0] | 88.0% | 0.0% |
| **R06** | 22.98 (18.40) [30.0] | 0.0% | 70.0% | 52.44 (1.72) [53.0] | 88.0% | 0.0% |
| **R07** | 20.36 (18.83) [30.0] | 0.0% | 54.0% | 52.18 (2.64) [53.0] | 86.0% | 2.0% |
| **R08** | 18.94 (20.76) [30.0] | 0.0% | 52.0% | 51.56 (4.17) [53.0] | 82.0% | 4.0% |
| **R09** | 18.31 (21.12) [30.0] | 0.0% | 55.1% | 51.64 (3.63) [53.0] | 82.0% | 4.0% |
| **R10** | 15.78 (21.79) [30.0] | 0.0% | 51.0% | 51.34 (4.47) [53.0] | 80.0% | 6.0% |
| **R11** | 14.27 (24.49) [24.0] | 0.0% | 45.8% | 51.18 (4.52) [53.0] | 77.6% | 6.1% |
| **R12** | 14.23 (24.17) [22.5] | 0.0% | 47.9% | 50.58 (7.18) [53.0] | 77.1% | 4.2% |

### Key Observations:
1. **Round 1 establishes the initial $Z=53$ anchor in both runs.**
   In Rung-2, for seeds 5000–5007 (the first 8 episodes run), 8/8 (100%) targeted $Z=53$. Across all 50 seeds, 100% of Rung-2 Round 1 targets were at $Z \ge 45$. In Rung-2′, 46/50 (92%) targeted $Z=53$.
2. **Round 2 is the bifurcation point.**
   In Rung-2, 36/50 (72%) immediately dropped into the cube height band $Z \in [30, 40]$, and only 1 episode stayed at $Z=53$. In Rung-2′, 45/50 (90%) stayed locked at $Z=53$, and 0% reached the contact band.

---

## 5. Seed-by-Seed Comparative Table (Seeds 5000–5049)

Data extracted from `data/collect_dumps/{3e8c52d4, 71134939}/*/meta.json` via `/home/control/audit/rung2p_diag/scratch_prose_disc/compare_z.py`:

| Seed | R2 Rds | R2 R1 | R2 R2 | R2 Mean | R2 Med | R2 Uniq | R2 All=53 | R2′ Rds | R2′ R1 | R2′ R2 | R2′ Mean | R2′ Med | R2′ Uniq | R2′ All=53 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **5000** | 8 | 53 | 30 | 13.50 | 15.0 | 5 | False | 12 | 53 | 45 | 39.92 | 41.0 | 4 | False |
| **5001** | 12 | 53 | 30 | 30.50 | 30.0 | 7 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5002** | 12 | 53 | 35 | 35.25 | 36.0 | 6 | False | 12 | 53 | 53 | 43.33 | 53.0 | 5 | False |
| **5003** | 12 | 53 | 36 | 24.50 | 20.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5004** | 12 | 53 | 10 | 2.58 | 0.0 | 8 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5005** | 12 | 53 | 15 | 34.00 | 35.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5006** | 12 | 53 | 10 | 18.50 | 10.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5007** | 12 | 53 | 36 | 10.83 | 10.0 | 7 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5008** | 12 | 50 | 20 | -13.75 | -22.5 | 9 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5009** | 12 | 45 | 35 | 33.83 | 35.5 | 7 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5010** | 12 | 50 | 30 | 14.17 | 5.0 | 4 | False | 11 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5011** | 12 | 50 | 30 | -1.42 | -10.0 | 9 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5012** | 12 | 48 | 45 | 15.75 | 7.5 | 7 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5013** | 12 | 50 | 10 | 29.50 | 30.0 | 5 | False | 12 | 53 | 53 | 48.00 | 50.5 | 4 | False |
| **5014** | 12 | 53 | 35 | 33.42 | 35.5 | 7 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5015** | 12 | 53 | 35 | 32.50 | 30.0 | 5 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5016** | 12 | 53 | 50 | 35.75 | 30.0 | 4 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5017** | 12 | 53 | 53 | 38.08 | 38.0 | 8 | False | 12 | 53 | 53 | 51.67 | 53.0 | 2 | False |
| **5018** | 10 | 50 | 40 | 32.00 | 32.5 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5019** | 12 | 53 | 30 | 33.42 | 30.0 | 3 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5020** | 12 | 53 | 50 | 29.92 | 30.0 | 6 | False | 12 | 50 | 50 | 50.00 | 50.0 | 1 | False (all 50) |
| **5021** | 12 | 50 | 10 | 35.17 | 36.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5022** | 12 | 53 | 30 | 30.17 | 30.0 | 8 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5023** | 12 | 50 | 40 | 32.25 | 30.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5024** | 12 | 53 | 35 | 33.17 | 36.0 | 6 | False | 12 | 53 | 53 | 52.00 | 53.0 | 2 | False |
| **5025** | 12 | 53 | 36 | 30.33 | 30.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5026** | 12 | 50 | 20 | -7.75 | -10.0 | 9 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5027** | 12 | 50 | 40 | 33.92 | 30.0 | 5 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5028** | 12 | 53 | 30 | 35.08 | 36.0 | 4 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5029** | 12 | 50 | 30 | 33.42 | 36.5 | 8 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5030** | 12 | 50 | 30 | 24.83 | 30.0 | 7 | False | 12 | 45 | 45 | 45.00 | 45.0 | 1 | False (all 45) |
| **5031** | 12 | 48 | 30 | 34.50 | 35.5 | 5 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5032** | 12 | 53 | 36 | 27.92 | 31.0 | 9 | False | 12 | 53 | 53 | 52.67 | 53.0 | 2 | False |
| **5033** | 12 | 45 | 30 | 21.25 | 20.0 | 4 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5034** | 12 | 45 | 40 | 34.00 | 36.5 | 10 | False | 12 | 50 | 50 | 49.17 | 50.0 | 2 | False |
| **5035** | 12 | 53 | 36 | 26.42 | 25.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5036** | 12 | 53 | 30 | 32.50 | 33.5 | 5 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5037** | 12 | 50 | 10 | 11.00 | 7.0 | 4 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5038** | 12 | 48 | 30 | 32.92 | 30.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5039** | 12 | 50 | 20 | 20.58 | 15.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5040** | 12 | 53 | 40 | 19.83 | 25.0 | 9 | False | 12 | 53 | 53 | 51.00 | 50.0 | 2 | False |
| **5041** | 12 | 45 | 30 | 21.67 | 27.5 | 5 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5042** | 12 | 53 | 30 | -6.58 | -20.0 | 8 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5043** | 12 | 48 | 40 | 36.67 | 36.5 | 7 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5044** | 12 | 53 | 30 | -18.50 | -30.0 | 9 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5045** | 12 | 48 | 30 | 31.33 | 32.0 | 6 | False | 10 | 50 | 50 | 50.00 | 50.0 | 1 | False (all 50) |
| **5046** | 12 | 50 | 40 | 35.92 | 36.0 | 7 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5047** | 12 | 53 | 30 | 30.42 | 30.0 | 5 | False | 12 | 53 | 53 | 51.33 | 53.0 | 2 | False |
| **5048** | 12 | 48 | 35 | 11.92 | 17.5 | 9 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |
| **5049** | 12 | 45 | 10 | 20.83 | 20.0 | 6 | False | 12 | 53 | 53 | 53.00 | 53.0 | 1 | **True** |

---

## 6. Detailed Code Path & Mechanistic Audit

### Code Path 1: The Initial Height Anchor ($Z=53$) is Prompt-Driven
- **File & Lines:** [push_collect.py:240-270](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L240-L270), [prompts.py:147-172](file:///home/control/AionGenos/aiongenos/vlm/prompts.py#L147-L172).
- At Round 1, the prompt explicitly reveals:
  ```
  CURRENT STATE (proprioception, base-frame integers, same grid as your output):
    LEFT_EE_POS  = (X=44, Y=35, Z=53)   # left fingertip (TCP)
  ```
- Because neither run receives critic feedback at Round 1 (`push_collect.py:242` requires `prev_fb is not None`), the VLM has no history and naturally treats $Z=53$ as the baseline height, modifying only $X$ and $Y$ to align with the cube. This explains why **100% of the first 8 seeds (5000–5007) in both runs chose $Z=53$ at Round 1**.

### Code Path 2: Stateless vs Multi-turn Reasoning at Round 2
- **File & Lines:** [push_collect.py:257-268](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L257-L268), [stage1_reasoning.py:247-276](file:///home/control/AionGenos/aiongenos/pipeline/stage1_reasoning.py#L247-L276).
- **Rung-2 Path:**
  `round_history=False` $\implies$ at Round 2, `r1_conv = None` $\implies$ `conversation = None`.
  `stage1_reasoning.py:269-276` calls `call_vlm_sync` as a fresh single-turn prompt.
  - *Thought at Seed 5000 R2:* *"Currently, the left end-effector is at (35, 45, 53), which is above and to the side of the cube. I need to bring the left end-effector down to the table level and position it behind the yellow cube to initiate a push..."* $\implies$ commands target $Z=30$.
  - *Thought at Seed 5001 R2:* *"Since the cube is currently at a lower Z-height than the current TCP (Z=53), I must lower the arm to contact the side of the cube."* $\implies$ commands target $Z=30$.
  - Because each round is evaluated de novo, the model perceives that it is hovering in mid-air and commands a plunge to table level ($Z \in [30, 40]$).
- **Rung-2′ Path:**
  `round_history=True` $\implies$ `conversation = ep_conv`.
  `stage1_reasoning.py:264-268` calls `call_vlm_history_sync` with the full multi-turn trajectory.
  - The model sees its previous turn ("LEFT_TARGET_POS: X=44 Y=20 Z=53") and the new user message containing the diagnostic report.

### Code Path 3: The 3D Scalar Distance Trap
- **File & Lines:** [push_feedback.py:29-54](file:///home/control/AionGenos/aiongenos/orchestrator/push_feedback.py#L29-L54), [isaaclab_env_interface.py:482-495](file:///home/control/AionGenos/aiongenos/orchestrator/isaaclab_env_interface.py#L482-L495).
- In `isaaclab_env_interface.py:489-493`:
  `tip_cube` is computed via `_pb.point_to_box_dist` — a **3D Euclidean distance** from the fingertip pad to the cube box.
- Standby TCP height is $Z=0.5355$ m; cube top is $Z=0.4922$ m.
  The minimum vertical distance when TCP is directly above the cube is $0.5355 - 0.4922 = 0.0433$ m (**4.33 cm**).
- When the robot moves in $(X, Y)$ at $Z=53$, the 3D distance reported in feedback changes:
  - *Seed 5001 Round 2 feedback:* `Fingertip-to-cube distance: started at 5.2 cm, ended at 4.5 cm`.
  - *Seed 5007 Round 2 feedback:* `Fingertip-to-cube distance: started at 5.6 cm, ended at 4.7 cm`.
- The multi-turn assistant reads this report and concludes that its planar movement was effective and brought the fingertip closer to the cube!
  - *Seed 5001 R2 Thought:* *"The previous move brought the TCP closer to the cube (from 5.2 cm to 4.5 cm)... I will increase the Y-coordinate to ensure the fingertip makes contact..."*
  - *Seed 5007 R2 Thought:* *"In the previous round, I moved the TCP from Y=35 to Y=30, which reduced the distance to the cube from 5.6 cm to 4.7 cm... I need to move the TCP further forward (decreasing Y) to make direct contact..."*
- Because the top-down camera (`camera_top`) looks along $-Z$, the vertical gap of 4.3 cm is visually invisible from above. The model believes the remaining 4.5 cm is a horizontal gap and spends all subsequent rounds oscillating in $X$ and $Y$ at $Z=53$.

### Code Path 4: Cross-Episode Memory Differences
- In Rung-2 (`workspace/recaps_push_pilot_rung2_r2/3e8c52d4/`), 8 out of 50 recaps explicitly mentioned lowering $Z$ or table height (e.g. *"lower the Z-height to table level"*). As episodes completed, subsequent episodes (starting at Seed 5008) retrieved these lessons in their Round 1 preamble, causing Round 1 targets to shift down ($Z=50, 48, 45$).
- In Rung-2′ (`workspace/recaps_push_pilot_rung2p/71134939/`), because 38/50 episodes never moved in $Z$, only 1 out of 50 recaps mentioned height/Z. The memory buffer had no signal to break the $Z=53$ bias.

---

## 7. Direct Resolution of the Task Questions

1. **What is the per-seed Z distribution for Rung-2 vs Rung-2′?**
   - Rung-2: Mean $Z=23.80$, median $Z=30.0$, 53.4% of all rounds in contact band $[30, 40]$, only 4.38% at $Z=53$. 0/50 episodes have constant $Z$.
   - Rung-2′: Mean $Z=51.97$, median $Z=53.0$, only 2.18% in contact band $[30, 40]$, 85.26% at $Z=53$. 41/50 episodes (82.0%) have zero $Z$ variation (38 all-53, 2 all-50, 1 all-45).
2. **Does Rung-2′'s z-anchoring appear from Round 2 onward (history effect)?**
   - **No for initial appearance:** 92.0% (46/50) of episodes are *already* anchored at $Z=53$ at Round 1, before any history or feedback exists.
   - **Yes for permanence / lock-in:** At Round 2, Rung-2 escapes to table height ($Z=30$ mode, only 2% at $Z=53$), whereas Rung-2′ remains locked at $Z=53$ (90% at $Z=53$) due to the multi-turn conversational trap and 3D scalar distance false gradient.
3. **Test of the claim: "history/feedback caused height anchoring":**
   - **Refuted as to inception:** Standby proprioception default caused the initial $Z=53$ target.
   - **Confirmed as to entrapment:** History and scalar feedback prevented the agent from ever correcting its height error, creating the 0/50 failure mode where the gripper waved helplessly 4.3 cm above the cube.
