# QA1 Instrument Audit Report: Rung-2′ Pipeline Verification

**Auditor:** qa1  
**Target Run:** `71134939` (rung-2′, seeds 5000–5049, memory ON, top view ON)  
**Verification Date:** 2026-10-22  
**Rules Complied:** Read-only access to repo, zero edits to git/codebase, CPU-only testing, zero Isaac/GPU jobs.

---

## 1. Pytest Execution (`tests/test_push_memory.py`)

### 1.1 Command and Execution Result
To obey the rule against touching repo files (avoiding `__pycache__` and `.pytest_cache` contamination in `/home/control/AionGenos`), test files and scripts were copied to scratch:
```bash
mkdir -p /home/control/audit/rung2p_diag/scratch_qa1
cp -r /home/control/AionGenos/tests /home/control/audit/rung2p_diag/scratch_qa1/tests
cp -r /home/control/AionGenos/scripts /home/control/audit/rung2p_diag/scratch_qa1/scripts
```

**Re-runnable execution command (CPU environment):**
```bash
PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python -m pytest -q /home/control/audit/rung2p_diag/scratch_qa1/tests/test_push_memory.py
```

**Result:**
```
.....................................                                    [100%]
37 passed in 1.71s
```
**Does it require Isaac Sim / GPU?**
**No.** All 37 tests run 100% on CPU without Isaac Sim or GPU. The test harness relies entirely on fakes and mocks:
- `_FakeGym` / `_FakeUnwrapped` ([`tests/test_push_memory.py:279-287`](file:///home/control/AionGenos/tests/test_push_memory.py#L279-L287))
- `_FakePushEnv` ([`tests/test_push_memory.py:289-365`](file:///home/control/AionGenos/tests/test_push_memory.py#L289-L365))
- `_patch_stage1` ([`tests/test_push_memory.py:373-382`](file:///home/control/AionGenos/tests/test_push_memory.py#L373-L382))

*(Note on system Python `/usr/bin/python3 3.10` vs `/home/control/env_isaaclab/bin/python 3.11`: Running with `/usr/bin/python3` yields 36 passed, 1 failed at line 485 `test_gif_tag_in_bottom_strip` due to PIL 9.0.1 GIF palette quantization color-mapping differences vs PIL 11.3.0 in `env_isaaclab`. The unit test logic itself is completely sound).*

---

## 2. Independent Reconstruction of Round 5 Prompt

We independently reconstructed the Round 5 prompt for episode `01b82183-43e` (seed 5004, run `71134939`).

### 2.1 Code Paths Followed
1. Loop management and round history: [`aiongenos/orchestrator/push_collect.py:241-272`](file:///home/control/AionGenos/aiongenos/orchestrator/push_collect.py#L241-L272)
2. Diagnostic feedback formatting: [`aiongenos/orchestrator/push_feedback.py:27-46`](file:///home/control/AionGenos/aiongenos/orchestrator/push_feedback.py#L27-L46)
3. Memory preamble generation: [`aiongenos/orchestrator/push_memory.py:171-209`](file:///home/control/AionGenos/aiongenos/orchestrator/push_memory.py#L171-L209)
4. Multi-turn sliding conversation & image stripping: [`aiongenos/vlm/client.py:26-95, 230-260`](file:///home/control/AionGenos/aiongenos/vlm/client.py#L26-L95)
5. User prompt and system prompt formatting: [`aiongenos/vlm/prompts.py:80-110, 160-180`](file:///home/control/AionGenos/aiongenos/vlm/prompts.py#L80-L110)

### 2.2 Structure of Reconstructed Round 5 Payload (`/v1/chat/completions`)
At Round 5, the model payload contains exactly **9 messages** (4 completed rounds of user/assistant turns + current Round 5 user prompt).

| Index | Role | Type / Content Summary | Image Count | Image Sources | Text Chars |
|---|---|---|---|---|---|
| `[0]` | user | System prompt folded + Round 1 Preamble (3 past recaps) + Round 1 User Prompt | **0** | Older images stripped | 5,098 |
| `[1]` | assistant | Round 1 response (`THOUGHT` + `LEFT_TARGET_POS: X=44 Y=20 Z=53` + `STOP: false`) | **0** | N/A | 782 |
| `[2]` | user | Round 2 prompt + Round 1 Critic Feedback | **0** | Older images stripped | 2,178 |
| `[3]` | assistant | Round 2 response (`THOUGHT` + `LEFT_TARGET_POS: X=44 Y=5 Z=53` + `STOP: false`) | **0** | N/A | 730 |
| `[4]` | user | Round 3 prompt + Round 2 Critic Feedback | **0** | Older images stripped | 2,175 |
| `[5]` | assistant | Round 3 response (`THOUGHT` + `LEFT_TARGET_POS: X=44 Y=30 Z=53` + `STOP: false`) | **0** | N/A | 830 |
| `[6]` | user | Round 4 prompt + Round 3 Critic Feedback | **0** | Older images stripped | 2,177 |
| `[7]` | assistant | Round 4 response (`THOUGHT` + `LEFT_TARGET_POS: X=44 Y=0 Z=53` + `STOP: false`) | **0** | N/A | 755 |
| `[8]` | user | **Round 5 Current Prompt**: Front View + Top View + Current State + Feedback | **2** | `round_05_pre.png`, `round_05_pre_top.png` | 2,175 |

### 2.3 Image Handling Verification
- **Which images are sent at Round 5?**
  **EXACTLY TWO IMAGES:**
  1. `data/collect_dumps/71134939/01b82183-43e/round_05_pre.png` (front view)
  2. `data/collect_dumps/71134939/01b82183-43e/round_05_pre_top.png` (top-down view)
- **Are older images kept?**
  **NO.** [`aiongenos/vlm/client.py:61-64`](file:///home/control/AionGenos/aiongenos/vlm/client.py#L61-L64) explicitly strips image elements whenever a new user turn is appended:
  ```python
  for msg in self.messages:
      if msg["role"] == "user" and isinstance(msg["content"], list):
          msg["content"] = [part for part in msg["content"] if part["type"] == "text"]
  ```
  Consequently, all 3 memory recap images and the front/top images from rounds 1–4 are stripped from history prior to dispatching Round 5.

### 2.4 Verbatim Text of Round 5 User Message (`[8]`)
```
TASK: Push the yellow cube onto the green zone on the table.
CONTROL_MODE: left_eef_waypoint_ori_optional

CURRENT STATE (proprioception, base-frame integers, same grid as your output):
  LEFT_EE_POS  = (X=44, Y=0, Z=53)   # left fingertip (TCP)
  RIGHT_EE_POS = (X=0, Y=0, Z=0)
  LEFT_GRIPPER = closed (locked)
SCAFFOLD (oracle-measured, disclosed):
  LEFT_TIP_TO_CUBE = 9.3 cm
  CUBE_TO_GOAL     = 8.8 cm
The last image is a top-down view of the current scene.

The yellow cube and the green zone (flat green disc on the table) are seen in
the image; their positions are not given as numbers.
AFFORDANCE CONTRACT: the cube must end up on the green zone, moved BY PUSHING.
The gripper is held CLOSED for the entire task and CANNOT open, close, grasp,
or lift. Your ONLY action each round is one left end-effector target: a
fingertip (TCP) position (REQUIRED) and an optional orientation offset. The
next round shows the new image and state.

ORIENTATION (OPTIONAL) — LEFT_TARGET_ORI: integer degrees rotating the hand's
REST orientation about FIXED BASE-frame axes, applied as Rz(Y)·Ry(P)·Rx(R):
  P = about the base Y axis
  Y = about the base Z axis (vertical)
  R = about the base X axis
  Signs follow the right-hand rule about the positive axis. Omitted → rest
  orientation.

THOUGHT: <one paragraph physics reasoning>
LEFT_TARGET_POS: X=<int> Y=<int> Z=<int>        (required; fingertip/TCP, base-frame integers on the SAME grid as CURRENT STATE — not cm)
LEFT_TARGET_ORI: P=<int> Y=<int> R=<int>        (OPTIONAL; integer degrees about base axes, applied to the rest orientation; omit for rest)
STOP: <true|false>

### CRITIC FEEDBACK FROM PREVIOUS ROUND:
DIAGNOSTIC REPORT FOR PREVIOUS ROUND:
  LEFT ARM:
    Target coordinate was predicted at: X=44 Y=0 Z=53
    Actual movement: from X=44 Y=30 Z=53 to X=44 Y=0 Z=53
    Fingertip-to-cube distance: started at 4.7 cm, ended at 9.3 cm
    Cube-to-goal distance: started at 8.8 cm, ended at 8.8 cm
    Result: No significant progress (still 8.8 cm from target). Try a different direction or larger step size. STOP only when the task's success criterion is met — do not stop because previous rounds showed no progress.
```

### 2.5 Feedback & History Confirmation
- **Feedback byte match:** The reconstructed critic feedback matches the `round_feedback` recorded in `data/collect_dumps/71134939/01b82183-43e/meta.json` byte-for-byte.
- **Physical observable consistency:**
  - Round 4 predicted target: `[44, 0, 53]`
  - Start TCP round 4: `[44, 30, 53]`; End TCP / Start TCP round 5: `[44, 0, 53]`
  - Fingertip box distance: `4.7 cm` at R4 start $\to$ `9.3 cm` at R5 start
  - Cube-to-goal distance: `8.8 cm` at R4 start $\to$ `8.8 cm` at R5 start
  - Verdict: Cube did not move $\ge 1.0\text{ cm}$, correctly triggering `CRITIC_FEEDBACK_FLAT`.

---

## 3. Negative Test: Mutation Detection

We tested whether our independent reconstruction catches data corruption or instrument bugs.

### Mutation A: Feedback Value Tampering
- **Mutation:** In `meta.json` Round 5 `round_feedback`, mutate `Target coordinate was predicted at: X=44` to `X=40` (simulating controller/logging mismatch).
- **Detection:** Recomputing `format_round_feedback()` from Round 4 target `r4['eef_target_int']` and Round 5 initial TCP `r5['ee_start_int']` raises `AssertionError`.
- **Validation Script:** [`/home/control/audit/rung2p_diag/scratch_qa1/test_mutation.py`](file:///home/control/audit/rung2p_diag/scratch_qa1/test_mutation.py)
```bash
PYTHONPATH=/home/control/AionGenos:/home/control/audit/rung2p_diag/scratch_qa1 /home/control/env_isaaclab/bin/python /home/control/audit/rung2p_diag/scratch_qa1/test_mutation.py
```
Output:
```
Clean data verification: PASSED (byte-for-byte feedback match)
Negative test A PASSED (Target coordinate mutation detected by reconstruction!)
```
*(This is identical to how `/home/control/audit/rung2p_diag/negrun/v.py NEG` detects the deliberate mutation in `negrun/data/collect_dumps/NEG/01b82183-43e/meta.json`).*

### Mutation B: Image Context Leak (Broken Client Image Stripping)
- **Mutation:** If a regression in `EpisodeConversation.append_user_turn` failed to strip prior images, historical images from Round 1 (including cross-episode memory images) would leak into Round 5 context.
- **Detection:** The reconstruction asserts `total_images == 2`. Injecting even 1 leaked image increases image count to 3, failing the assertion:
```
Verified image count at round 5: 2 (exactly 2: round_05 front + round_05 top)
Negative test B PASSED (Unstripped image leak detected: count=3 != 2)
```

---

## 4. Re-runnable Command Summary

| Check | Command |
|---|---|
| Run unit tests (CPU only) | `PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python -m pytest -q /home/control/audit/rung2p_diag/scratch_qa1/tests/test_push_memory.py` |
| Reconstruct Round 5 prompt | `PYTHONPATH=/home/control/AionGenos /home/control/env_isaaclab/bin/python /home/control/audit/rung2p_diag/scratch_qa1/reconstruct.py 01b82183-43e` |
| Execute Negative Test | `PYTHONPATH=/home/control/AionGenos:/home/control/audit/rung2p_diag/scratch_qa1 /home/control/env_isaaclab/bin/python /home/control/audit/rung2p_diag/scratch_qa1/test_mutation.py` |
