# Behavioural Analysis of Rung-2′ Teacher Thoughts (`prose_res`)

- **Author / Role**: `prose_res` (Behaviour Analyst)
- **Target Run**: `71134939` (rung-2′, seeds 5000–5049, memory ON, 50 episodes, 597 rounds)
- **Reference Spec**: [`/home/control/audit/rung2p_diag/spec.md`](file:///home/control/audit/rung2p_diag/spec.md)
- **Code Path Grounding**:
  - Prompt construction: [`aiongenos/vlm/prompts.py:147-172`](file:///home/control/AionGenos/aiongenos/vlm/prompts.py#L147-L172) (`_S1_EEF_PUSH`), [`push_feedback.py:29-45`](file:///home/control/AionGenos/aiongenos/orchestrator/push_feedback.py#L29-L45)
  - Coordinate normalization: [`aiongenos/vlm/scalar_guard.py:47-105`](file:///home/control/AionGenos/aiongenos/vlm/scalar_guard.py#L47-L105)
  - Top-down camera extrinsics: [`aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py:346-377`](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L346-L377)
  - Push collection loop: [`aiongenos/orchestrator/push_collect.py:234-280`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L234-L280)
- **Verification Script**: [`/home/control/audit/rung2p_diag/scratch_prose_res/classify_thoughts.py`](file:///home/control/audit/rung2p_diag/scratch_prose_res/classify_thoughts.py)

---

## 1. Executive Summary & Diagnostic Verdict

The 0/50 failure on rung-2′ is **NOT** a physical controller tracking failure or an Isaac simulation glitch. It is a **dual cognitive failure induced by an observational asymmetry and prompt ambiguity**:

1. **The Z=53 Air-Swiping Ceiling (Altitude Blindness)**:
   - In robot base coordinates ([`aiongenos/config.py:45`](file:///home/control/AionGenos/aiongenos/config.py#L45), bounds $Z \in [0.0, 0.7]$ m):
     - Table surface: $Z = 0.444\text{ m}$ (integer $\approx 27$).
     - Cube center: $Z = 0.468\text{ m}$ (integer $\approx 34$), cube top edge: $Z = 0.492\text{ m}$ (integer $\approx 41$).
     - Initial Left TCP: $Z = 0.5356\text{ m}$ (integer $53$), which is **$4.36\text{ cm}$ above the top of the cube**.
   - In **509 / 597 rounds (85.3%)**, the model emits targets at $Z=53$. In **117 rounds (19.6%)**, the model explicitly writes that $Z=53$ is the cube position, contact height, or push plane.
   - Because the prompt ([`prompts.py:147-172`](file:///home/control/AionGenos/aiongenos/vlm/prompts.py#L147-L172)) reveals only proprioception for TCP and no vertical coordinates for the table or cube, the VLM treats the task as a 2D planar problem, hovering permanently $4.3\text{ cm}$ above the cube and swiping the empty air.

2. **The Transverse Axis Inversion (Pushing Sideways)**:
   - Across all 50 episodes, the required vector from cube to goal is almost purely along **$+X$ (robot forward)**:
     - $\Delta X = +7.2\text{ to }+9.8\text{ cm}$ (median $+8.6\text{ cm}$).
     - $\Delta Y = -3.9\text{ to }+3.8\text{ cm}$ (median $+0.6\text{ cm}$).
   - The top-down camera ([`push_s3a_cfg.py:347`](file:///home/control/AionGenos/aiongenos/tasks/WP1_contact_testbed/push_s3a_cfg.py#L347)) is oriented such that image "up" is $+X$.
   - However, in **370 / 597 rounds (62.0%)**, the VLM explicitly states that the goal is in the $\pm Y$ direction (e.g., "forward in the negative Y direction"), treating $Y$ as depth and $X$ as lateral alignment. The robot sweeps lateral arcs across the table, moving perpendicular to the goal.

3. **Instrument False Positive in `validate.py`**:
   - [`/home/control/audit/rung2p_diag/validate.py:22`](file:///home/control/audit/rung2p_diag/validate.py#L22) reported `521/597` rounds mentioning height/Z/descend.
   - This was an instrument artifact: `validate.py` used `r"\bz\b|z=|lower|descend|height|down|above"`, which matched `down` in `"top-down view"` (**489 rounds**) and `lower` in `"lower Y coordinate"` (**140+ rounds**).
   - In reality, substantive reasoning about the vertical dimension occurred in only **25 / 597 rounds (4.2%)**.

---

## 2. Classification Table of all 597 `vlm_thought` Texts

Classification executed via [`/home/control/audit/rung2p_diag/scratch_prose_res/classify_thoughts.py`](file:///home/control/audit/rung2p_diag/scratch_prose_res/classify_thoughts.py) over all 50 episodes of run `71134939`:

| Category | Classification Criterion | Count | Pct (%) | Key Mechanism / Findings |
|---|---|:---:|:---:|---|
| **(i) Reasons about Z at all** | **Substantive vertical reasoning** (debates height, vertical axis, table level, clearance, swiping air, adjusting Z) | **25** | **4.2%** | Extremely rare. 95.8% of rounds treat task as purely 2D planar motion. |
| | **Broad Z mention** (includes 3D coordinate tuples `(X, Y, Z)` or `Z=<int>`) | **187** | **31.3%** | Mostly reciting proprioceptive state `(44, 35, 53)`. |
| | *Flawed regex in `validate.py:22`* | *521* | *87.3%* | *Instrument artifact (matches "top-down view" [489] and "lower Y" [140+]).* |
| **(ii) Believes Z=53 is cube/contact height** | **Explicit verbal belief** (states cube is at Z=53, or claims Z=53 penetrates/collides/pushes cube) | **117** | **19.6%** | VLM explicitly hallucinated that the cube volume lies at Z=53. |
| | **Action-anchored belief** (emits `LEFT_TARGET_POS` with $Z=53$) | **509** | **85.3%** | Rigid anchor: TCP never descends from initial standby height ($0.5355\text{ m}$). |
| **(iii) Axis or scale misunderstanding** | **Axis contradiction** (asserts $\pm Y$ means forward/toward goal; confuses $X$ and $Y$) | **370** | **62.0%** | Treats $Y$ as forward depth; actual goal is at $+X$ (median $+8.6\text{ cm}$). |
| | **Scale misunderstanding** (confuses coordinate units with cm) | **1** | **0.2%** | Treats 45 integer units as equivalent to $8.9\text{ cm}$ (actual: 45 units = $18\text{ cm}$). |
| | **Combined axis or scale misunderstanding** | **370** | **62.0%** | Dominant failure mode in 2D planning. |
| **(iv) Uses fingertip→cube distance correctly** | **Cites fingertip→cube distance / cm** in thought | **555** | **93.0%** | Actively consumes scalar feedback every round. |
| | **Directional tracking matches feedback $\Delta$** (closer $\leftrightarrow$ decreased, further/overshot $\leftrightarrow$ increased) | **360** | **60.3%** | Logically tracks whether it approached or receded based on distance numbers. |
| | **The 4.0–4.5 cm Z-offset plateau trap** (interprets 3D distance floor as XY gap) | **110** | **18.4%** | Believes $4.3\text{ cm}$ gap is horizontal; moves horizontally into empty air. |
| **(v) Mentions memory / past episodes** | **Cross-episode memory in Round 1** (preamble-driven) | **49** | **98.0%** of R1 (49/50) | **100%** of episodes that received preamble (49/49) referenced past episodes. (Seed 5000 had empty buffer). |
| | **Cross-episode memory across all rounds** | **56** | **9.4%** | Concentrated on Round 1; rarely persists past Round 2. |
| | **Within-episode history** (references earlier rounds/feedback in current episode) | **161** | **27.0%** | Analyzes previous moves within the episode ("previous push to Y=10 failed"). |

---

## 3. Detailed Analysis & Verbatim Quotes by Category

### (i) Reasons about Z at all
- **Code Path & Data**: [`aiongenos/vlm/prompts.py:147-172`](file:///home/control/AionGenos/aiongenos/vlm/prompts.py#L147-L172). The prompt states: `LEFT_EE_POS = (X={left_x}, Y={left_y}, Z={left_z})   # left fingertip (TCP)`. It never mentions the vertical height of the table or cube.
- **Finding**: In 410 / 597 rounds (68.7%), Z is never mentioned at all. In 162 rounds, Z appears only passively within coordinate strings like `(44, 35, 53)`. Only 25 rounds (4.2%) show genuine reasoning about the vertical axis.
- **Why `validate.py` Reported 521/597**:
  - Command: `python3 -c "import json, glob, re; eps=[json.load(open(f)) for f in glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json')]; print(sum(1 for e in eps for r in e['rounds'] if 'top-down' in r.get('vlm_thought','')))"` $\rightarrow$ **489 rounds**.
  - `validate.py:22` had `re.search(r"\bz\b|z=|lower|descend|height|down|above", t)`. The word boundary `\bdown\b` caught `"top-down view"`, and `\blower\b` caught `"lower Y"`.

#### Verbatim Quotes (Category i):
1. **Seed 5002, Round 8** ([`data/collect_dumps/71134939/d8cb241c-b71/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/d8cb241c-b71/meta.json))
   - *State*: start `[40, 60, 53]`, emitted target `[44, 30, 30]`.
   - *Quote*:
     > "Despite multiple attempts to push the cube by moving from Y=30 to Y=60/70, the cube has not moved, and the fingertip-to-cube distance increases, meaning the TCP is missing the cube entirely. Looking at the images, the TCP is clearly too high (Z=53) to make contact with the cube's face on the table. The robot is effectively "swiping" the air above the cube. To initiate a push, I must lower the Z-coordinate of the TCP to be level with the cube's center of mass. I will reset the TCP to a position behind the cube (Y=30) and significantly lower the Z-height to Z=30 to ensure a physical collision occurs during the forward push."
   - *Analysis*: The VLM explicitly diagnoses the vertical failure ("swiping the air above the cube", "too high (Z=53)") and lowers target Z to 30.

2. **Seed 5034, Round 8** ([`data/collect_dumps/71134939/098e3ccb-fdd/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/098e3ccb-fdd/meta.json))
   - *State*: start `[41, 25, 50]`, emitted target `[41, 40, 48]`.
   - *Quote*:
     > "Despite moving the TCP from Y=15 to Y=25, the distance to the cube remained exactly 4.0 cm and the cube did not move. This indicates that I am still not making physical contact with the object; I am likely just grazing it or the TCP is slightly offset in the X or Z axis. Looking at the images, the TCP is very close, but the 'no progress' report suggests I need to be more aggressive with the target position to ensure a deep overlap with the cube's volume. I will shift the target further forward and slightly adjust the X coordinate to ensure I hit the center of the cube's face, and I will lower the Z slightly to ensure the push is happening against the side of the cube rather than potentially riding over the top."
   - *Analysis*: The model recognizes that remaining at $4.0\text{ cm}$ means it is potentially "riding over the top" of the cube and attempts to "lower the Z slightly" (to 48).

---

### (ii) Believes Z=53 is cube/contact height
- **Code Path & Kinematics**:
  - [`aiongenos/vlm/scalar_guard.py:81-105`](file:///home/control/AionGenos/aiongenos/vlm/scalar_guard.py#L81-L105): $Z_{\text{metric}} = 0.0 + \frac{Z_{\text{int}} + 100}{200} \times 0.7\text{ m}$.
  - At $Z_{\text{int}} = 53$: $Z = 0.5355\text{ m}$.
  - Actual cube top in base frame: $Z = 0.4920\text{ m}$ (int $\approx 41$).
  - Actual table top: $Z = 0.444\text{ m}$ (int $\approx 27$).
- **Finding**: 509 out of 597 rounds (85.3%) target $Z=53$. In 117 rounds (19.6%), the model asserts in words that $Z=53$ is the cube's position, the position directly behind the cube, or the position where pushing contact occurs.

#### Verbatim Quotes (Category ii):
1. **Seed 5021, Round 1** ([`data/collect_dumps/71134939/e66dfd5f-7f7/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/e66dfd5f-7f7/meta.json))
   - *State*: start `[44, 35, 53]`, emitted target `[40, 20, 53]`.
   - *Quote*:
     > "The cube is located roughly around (X=40, Y=10, Z=53) and the goal is further along the Y-axis (around Y=0). To initiate a push, I need to move the TCP to a position that forces it to collide with the back of the cube. Placing the target at (X=40, Y=20, Z=53) will place the TCP behind the cube's volume, ensuring that the subsequent movement toward the goal results in a direct push."
   - *Analysis*: The model explicitly attributes $Z=53$ as the 3D coordinate of the cube, believing that targeting $Z=53$ places the TCP directly behind the cube's volume.

2. **Seed 5046, Round 7** ([`data/collect_dumps/71134939/0daea799-a29/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/0daea799-a29/meta.json))
   - *State*: start `[48, 15, 53]`, emitted target `[48, 50, 53]`.
   - *Quote*:
     > "The current position (X=48, Y=15, Z=53) has brought the TCP to within 4.4 cm of the cube. Looking at the top-down view, the TCP is now perfectly aligned behind the cube and ready to push toward the green zone. However, because the cube has not moved yet, I need to push forward through the cube to translate it... I will target a forward push along the Y-axis..."
   - *Analysis*: The model asserts that being at $(48, 15, 53)$ means it is "perfectly aligned behind the cube and ready to push", unaware that it is hovering $4.3\text{ cm}$ above the cube.

---

### (iii) Axis or scale misunderstanding
- **Code Path & Kinematics**:
  - Robot base frame kinematics: $+X$ points forward from robot base toward table center/goal; $+Y$ points leftward across the table; $+Z$ points upward.
  - Actual cube to goal displacement: $\Delta X = +8.6\text{ cm}$ (median), $\Delta Y = +0.6\text{ cm}$ (median). Pushing requires driving $+X$.
  - Top camera optical configuration ([`push_s3a_cfg.py:347`](file:///home/control/AionGenos/data/collect_dumps/71134939/01b82183-43e/meta.json)): `_TOPCAM_ROT_WORLD = (0.70711, 0.0, 0.70711, 0.0) ... image top = robot forward (+x)`.
- **Finding**: In 370 / 597 rounds (62.0%), the model claims that pushing toward the green goal is along the $Y$ axis (decreasing $Y$ or increasing $Y$). The model confuses the 2D image vertical axis (top of image) with the base $Y$ axis, sweeping laterally and never driving $+X$.

#### Verbatim Quotes (Category iii):
1. **Seed 5004, Round 4** ([`data/collect_dumps/71134939/01b82183-43e/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/01b82183-43e/meta.json))
   - *State*: start `[44, 30, 53]`, emitted target `[44, 0, 53]`.
   - *Quote*:
     > "The TCP is currently at (44, 30, 53) and is 4.7 cm from the cube. Looking at the top-down view, the cube is directly in front of the left arm and the green zone is further ahead. To push the cube, the TCP must move forward (decreasing Y) to physically intersect the cube's volume and then continue moving forward to push it toward the goal. Since previous attempts at Y=20 and Y=5 failed to move the cube, it's likely the TCP was either too far to the side or didn't have enough overlap. I will move the TCP forward to a position that definitely intersects the cube (around Y=15) and then push through to Y=0 in a single motion to ensure a strong push toward the green zone."
   - *Analysis*: Explicitly states that "forward toward the goal" = "decreasing Y". Decreasing $Y$ moves the robot arm sideways across the table, not forward.

2. **Seed 5018, Round 5** ([`data/collect_dumps/71134939/53a8ae38-9be/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/53a8ae38-9be/meta.json))
   - *State*: start `[44, 55, 53]`, emitted target `[44, 30, 53]`.
   - *Quote*:
     > "My previous attempts to move to the 'rear' of the cube have consistently increased the distance to the object, which indicates that my mental model of the base-frame coordinate system is inverted along the Y-axis. In the base frame, a smaller Y value means moving further forward (toward the goal), whereas I assumed it meant moving backward. Looking at the top-down image, the green goal zone is located at a smaller Y value than the cube, which means that to push the cube into the goal, the TCP must start at a Y value that is *larger* than the cube's position and move toward smaller Y values. Currently, at Y=55, the distance is 12.0 cm, confirming that Y=55 is too far 'behind' the cube. I will move the TCP forward to Y=30 to establish contact with the rear face of the cube."
   - *Analysis*: The VLM explicitly reflects on its axis confusion ("mental model of the base-frame coordinate system is inverted along the Y-axis"), but doubles down on believing that $Y$ is the push axis toward the goal.

3. **Seed 5014, Round 6 (Scale & Axis Misunderstanding)** ([`data/collect_dumps/71134939/335805fc-4db/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/335805fc-4db/meta.json))
   - *State*: start `[44, 45, 53]`, emitted target `[44, 0, 53]`.
   - *Quote*:
     > "The TCP is now at (44, 45, 53), which is 5.4 cm from the cube. The top-down image confirms that the TCP is positioned directly behind the yellow cube, and the green goal is straight ahead along the negative Y-axis. To ensure the cube is pushed onto the goal, I must execute a deep push that forces the TCP to move from behind the cube, through its volume, and well past it toward the goal... I will target Y=0, which will force the arm to travel a distance of 45 units, guaranteeing contact and providing sufficient force to push the cube across the remaining 8.9 cm to the green zone."
   - *Analysis*: The model equates traveling 45 integer coordinate units with pushing across $8.9\text{ cm}$ (actual: 45 units in $Y$ is $18.0\text{ cm}$).

---

### (iv) Uses fingertip→cube distance correctly
- **Code Path & Data**:
  - Distance scalar definition: [`push_collect.py:241`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L241) and [`push_feedback.py:38-44`](file:///home/control/AionGenos/aiongenos/orchestrator/push_feedback.py#L38-L44).
  - Feedback text: `Fingertip-to-cube distance: started at {tip_start:.1f} cm, ended at {tip_end:.1f} cm`.
- **Finding**:
  - In 555 / 597 rounds (93.0%), the thought cites the distance scalar.
  - In 360 / 597 rounds (60.3%), the model directionally interprets the feedback delta correctly (recognizing that an increase in distance means it overshot or moved in the wrong direction, while a decrease means it got closer).
  - **The 4.3 cm Z-Plateau Blind Spot**: In 110 rounds (18.4%), the distance reaches the range $3.8\text{--}4.7\text{ cm}$. The model assumes this is a horizontal XY gap and attempts to push forward across the table to close it. In reality, $4.35\text{ cm}$ is the vertical distance between the TCP pad ($Z=0.5355$) and the cube top ($Z=0.4920$). The TCP is already horizontally aligned above the cube, so horizontal motion pushes thin air.

#### Verbatim Quotes (Category iv):
1. **Seed 5004, Round 2 (Correct Directional Tracking)** ([`data/collect_dumps/71134939/01b82183-43e/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/01b82183-43e/meta.json))
   - *State*: start `[44, 20, 53]`, emitted target `[44, 5, 53]`. Feedback reported: `started at 4.9 cm, ended at 4.7 cm`.
   - *Quote*:
     > "The previous action moved the TCP from Y=35 to Y=20, but the fingertip-to-cube distance only decreased slightly (4.9 cm to 4.7 cm) and the cube did not move. This indicates that the TCP is still not intersecting the cube's volume. Looking at the top-down view, the cube is positioned further 'forward' (lower Y value) than my previous target. To initiate a push, I need to move the TCP deeper into the scene to actually make physical contact with the back face of the cube. I will decrease the Y coordinate significantly to ensure the TCP reaches the cube's position, and I will maintain the X coordinate to keep the push aligned with the goal zone."
   - *Analysis*: The model accurately evaluates the 0.2 cm decrease reported by the feedback and logically reasons about why the cube did not move.

2. **Seed 5004, Round 3 (Correct Overshoot Detection)** ([`data/collect_dumps/71134939/01b82183-43e/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/01b82183-43e/meta.json))
   - *State*: start `[44, 5, 53]`, emitted target `[44, 30, 53]`. Feedback reported: `started at 4.7 cm, ended at 7.6 cm`.
   - *Quote*:
     > "The previous movement to Y=5 actually increased the distance between the TCP and the cube (from 4.7 cm to 7.6 cm), meaning I moved too far past the cube or in the wrong direction relative to its actual position. Looking at the top-down image, the cube is located between the robot's current TCP position and the green zone. To push the cube forward into the green zone, I need to be positioned *behind* the cube. Since moving to Y=20 was too far and Y=5 was even further away in the wrong direction, the cube must be located at a higher Y value than I previously thought. I will move the TCP back to a position that is slightly behind the cube's visual center..."
   - *Analysis*: The model correctly deduces from the distance increase ($4.7 \rightarrow 7.6\text{ cm}$) that it moved away/overshot and retreats.

---

### (v) Mentions memory/past episodes
- **Code Path & Injection Mechanism**:
  - Memory injection: [`aiongenos/orchestrator/push_collect.py:216-232, 264-268`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L216-L232).
  - Injected on **Round 1 ONLY** (`round_idx == 0 and memory_text`).
- **Finding**:
  - In Round 1, **49 out of 50 episodes (98.0%)** explicitly mention past episodes or memory retrieval.
  - The single episode that did not mention memory in Round 1 was **Seed 5000**, where the memory buffer was initially empty (`memory_preamble: False`, [`data/collect_dumps/71134939/d6c8b9ae-c17/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/d6c8b9ae-c17/meta.json)).
  - For all 49 episodes where the memory preamble was injected (`seeds 5001–5049`), the model explicitly cited past episodes in **100% of cases (49/49)**.
  - In rounds 2–12, memory mentions drop sharply (only 7 mentions across 547 rounds), but within-episode history is cited in 161 rounds (27.0%).

#### Verbatim Quotes (Category v):
1. **Seed 5004, Round 1 (Cross-Episode Memory via Preamble)** ([`data/collect_dumps/71134939/01b82183-43e/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/01b82183-43e/meta.json))
   - *State*: start `[44, 35, 53]`, emitted target `[44, 20, 53]`.
   - *Quote*:
     > "Looking at the top-down view, the yellow cube is located between the robot and the green goal zone. To move the cube toward the goal, I must apply a force in the direction of the green zone. Based on the past episodes, simply moving the TCP near the cube is insufficient; I must position the TCP directly behind the cube (relative to the goal) and ensure the path intersects the cube's volume to initiate a physical push. Currently, the left TCP is at (44, 35, 53) and the cube is approximately 4.9 cm away. I will target a position slightly behind the cube's center to ensure a direct push forward toward the green zone, avoiding the mistakes of Episodes 1, 2, and 3 where the TCP missed the object."
   - *Analysis*: The model explicitly cites retrieved past episodes ("Episodes 1, 2, and 3") and applies the lesson that merely hovering near the cube fails. However, because memory also originated from runs stuck at $Z=53$, it reinforced the false belief that failure was due to lateral alignment rather than height.

2. **Seed 5042, Round 1 (Cross-Episode Memory via Preamble)** ([`data/collect_dumps/71134939/0891f8c7-424/meta.json`](file:///home/control/AionGenos/data/collect_dumps/71134939/0891f8c7-424/meta.json))
   - *State*: start `[44, 35, 53]`, emitted target `[44, 40, 53]`.
   - *Quote*:
     > "Based on the top-down view, the yellow cube is located between the robot and the green goal zone. To push the cube into the zone, I must position the left end-effector directly behind the cube relative to the goal. In previous episodes, targets like (44, 32, 53) or (44, 25, 53) failed because they either didn't make contact or were positioned in front of the cube. Looking at the current state, the left TCP is at (44, 35, 53). To establish a firm pushing vector toward the green zone (which is further 'up' or in the negative Y direction relative to the cube's current position), I need to move the TCP to a position that is slightly behind the cube's center and aligned with the goal. I will target a position that ensures contact and a direct push."
   - *Analysis*: Specifically quotes coordinate targets from retrieved past episodes ("(44, 32, 53) or (44, 25, 53)"), proving that memory retrieval effectively reached the VLM's context.

---

## 4. Re-runnable Verification Commands

All claims, metrics, and quotes in this report are verifiable via the following commands:

```bash
# 1. Run the full classifier script across all 597 rounds:
python3 /home/control/audit/rung2p_diag/scratch_prose_res/classify_thoughts.py

# 2. Verify that 509/597 rounds target Z=53:
python3 -c "import glob, json; eps=glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'); rs=[r for f in eps for r in json.load(open(f))['rounds']]; print('Targets Z=53:', sum(1 for r in rs if r['eef_target_int'][2]==53), '/', len(rs))"

# 3. Verify the validate.py false-positive breakdown ('top-down' vs substantive Z):
python3 -c "import glob, json, re; eps=glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'); rs=[r.get('vlm_thought','') for f in eps for r in json.load(open(f))['rounds']]; print('Mentions top-down:', sum(1 for t in rs if 'top-down' in t.lower())); print('Mentions height/altitude/vertical:', sum(1 for t in rs if re.search(r'\b(height|altitude|vertical)\b', t, re.I)))"

# 4. Verify Ground Truth Cube->Goal displacement (median +8.6 cm in X, +0.6 cm in Y):
python3 -c "import glob, json, statistics as st; eps=glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'); r0s=[json.load(open(f))['rounds'][0] for f in eps]; dxs=[r['goal_b_pre'][0]-r['cube_b_pre'][0] for r in r0s]; dys=[r['goal_b_pre'][1]-r['cube_b_pre'][1] for r in r0s]; print(f'dX median: {st.median(dxs)*100:.1f} cm; dY median: {st.median(dys)*100:.1f} cm')"

# 5. Verify 100% Round-1 memory preamble utilization (49/49 with preamble):
python3 -c "import glob, json, re; eps=[json.load(open(f)) for f in sorted(glob.glob('/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json'))]; r1=[e['rounds'][0] for e in eps]; print('R1 with preamble:', sum(1 for r in r1 if r.get('memory_preamble'))); print('R1 mentioning past episodes:', sum(1 for r in r1 if re.search(r'past.*episode|previous.*episode|episodes?\s+\d+|past.*failure', r.get('vlm_thought',''), re.I)))"
```
