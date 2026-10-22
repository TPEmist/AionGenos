# Memory-Condition Audit (mem1): What the Teacher Actually Receives at Round $r$ (Rung-2′ vs P1 L0a)

**Auditor:** mem1  
**Target:** WP1-③a Rung-2′ pilot (`run_id=71134939`, seeds 5000–5049, memory ON) vs P1 L0a baseline (`aiongenos/orchestrator/collect.py`)  
**Specification:** `/home/control/audit/rung2p_diag/spec.md` (Rule 10 audit)  
**Date:** 2026-10-22  

---

## 1. Executive Summary & Verdict

In Rung-2′ (`run_71134939`), the prompt and context pipeline successfully mirrors P1 L0a's memory mechanics (Round 1 cross-episode memory injection, `EpisodeConversation` sliding-window history with `recent_window=6`, and aggressive stripping of past images). However, the audit reveals **three fundamental discrepancies** between what the teacher received in P1 L0a and what it actually received in Rung-2′:

1. **Top-Down Visual Perception is Transient (Stripped after 1 Round):** While Rung-2′ discloses a top-down camera view (`rgb_top`) alongside the front view for the *current* round, `EpisodeConversation.append_user_turn` strips all `image_url` parts from previous turns (`aiongenos/vlm/client.py:146-150`). Consequently, the teacher has multi-view perception for the current timestep only; historical multi-view context is immediately converted to text-only. Similarly, past retrieved memory images are stripped after Round 1.
2. **100% Negative/Misleading Critic Verdict (547/547 Flat):** In P1, critic feedback evaluated Euclidean distance delta to the reach target ($\Delta d = d_{\text{end}} - d_{\text{start}}$), providing positive reinforcement ("Successful progress") whenever the arm closed in. In Rung-2′, `push_feedback.py:43` evaluates progress on `scalars_now[1]` (`cube_to_goal`), **not** `scalars_now[0]` (`fingertip_to_cube`). Because the cube cannot move before physical contact, every single pre-contact round (547 out of 547 feedback rounds across run 71134939) received the identical flat verdict: `"Result: No significant progress... Try a different direction or larger step size"`. The teacher was told it failed to make progress even while successfully closing distance to the cube.
3. **Bimanual System Prompt Contradiction:** Both P1 and Rung-2′ share the exact same system prompt (`STAGE1_SYSTEM`), which explicitly commands: *"You are a bimanual robot controller... must plan the next sub-goal for both arms."* In Rung-2′ (a single-arm push task with the right arm locked and passive), this prompt conflicts with the user template (`_S1_EEF_PUSH`), creating prompt-level role dissonance.

---

## 2. Comparative Synthesis Table

| Item | P1 L0a Code Path | Rung-2′ Code Path | Same / Different | Concrete Evidence & Re-runnable Command |
| :--- | :--- | :--- | :--- | :--- |
| **System Prompt Text** | `aiongenos/vlm/prompts.py:42-49, 451-452` (`STAGE1_SYSTEM`) | `aiongenos/vlm/prompts.py:42-49, 451-452` (`STAGE1_SYSTEM`) | **Identical** (Byte-for-byte) | Both return `STAGE1_SYSTEM`. `python3 -c "from aiongenos.vlm.prompts import get_stage1_system_prompt as g; print(repr(g()))"` |
| **System Prompt Placement** | Folded into first user turn (`client.py:155` / `client.py:63`) | Folded into first user turn (`client.py:155` / `client.py:63`) | **Identical** | `aiongenos/vlm/client.py:154-155`: `user_content.append({"type": "text", "text": self.system_prompt + "\n\n"})` |
| **Cross-Episode Retrieval Scoring** | `aiongenos/memory/retriever.py:129-139` (`MemoryRetriever`) | `aiongenos/orchestrator/push_memory.py:643-653` (`PushMemoryRetriever`) | **Identical** (Score formula & weights) | Both call `RecapBuffer.retrieve` with $\alpha=0.4$ image weight, $30\,\text{cm}$ state scale, $2/3$ success floor. Query state is init EE grid. |
| **Cross-Episode Retrieval Filtering** | No task filter; joint success floor (`retriever.py:90, 137`) | Push-only filter (`rec.metadata["task"] == "WP1_3a_push"`, `push_memory.py:560, 653`) | **Different** (Scoped root) | `push_memory.py:653, 674-686` enforces push-only root to avoid reach cross-contamination. |
| **Cross-Episode Memory: Number of Recaps** | `top_k = 3` (default) (`retriever.py:70`) | `top_k = 3` (`push_memory.py:618`; CLI default `run_push_collect.py:44`) | **Different in run execution** (0 ramp-up) | Run 71134939 started with empty buffer: Ep 0 had 0, Ep 1 had 1, Ep 2 had 2, Ep 3+ had 3. Check: `python3 -c "import json; d=json.load(open('logs/push_smoke_71134939.json')); print([len(e['memory_hits']) for e in d['episodes'][:5]])"` |
| **Cross-Episode Memory: Images Loaded** | Start front image only (`retriever.py:214`) | Start front image only (`push_memory.py:654` calling `retriever.py:214`) | **Identical** (`init_pre` only) | Both call `_load_past_image_b64_list` which queries `rec.image_anchors.get("init_pre")`. Neither retrieves `init_pre_top` or `final_post`. |
| **Cross-Episode Memory: Injection Rounds** | Round 1 only (`collect.py:285-286`) | Round 1 only (`push_collect.py:267-268`) | **Identical** (R1 only) | Preamble is `None` for all `round_idx > 0`. In R1, fused into `messages[0]`. |
| **Within-Episode History: Structure** | `EpisodeConversation` (`client.py:92`) | `EpisodeConversation` (`client.py:92`) | **Identical** | Both instantiate `EpisodeConversation(get_stage1_system_prompt())` once at ep start (`collect.py:194`, `push_collect.py:259`). |
| **Within-Episode History: Pruning Window** | `DEFAULT_RECENT_WINDOW = 6` (`client.py:109`) | `DEFAULT_RECENT_WINDOW = 6` (`client.py:109`) | **Identical** | Retains `messages[0]` (R1) + last 12 messages (6 pairs). Middle rounds dropped at R8+. |
| **Within-Episode History: Past Image Stripping** | Stripped from all older user turns (`client.py:148-149`) | Stripped from all older user turns (`client.py:148-149`) | **Identical** | `msg["content"] = [p for p in msg["content"] if p["type"] == "text"]`. Strips past front, top, and past memory images from round 2+. |
| **Camera Views in Current Turn** | 1 image (front view `rgb`) (`stage1_reasoning.py:77`) | 2 images (front view `rgb` + top view `rgb_top`) (`stage1_reasoning.py:244-245, 253-259`) | **Different** (Top-down view added) | `push_collect.py:270`: `extra_image_bytes=[rgb_top] if top_view else None`. Rung-2′ provides front + top-down view for current turn. |
| **Camera Views in Older Turns** | None (stripped) | None (stripped) | **Identical** (0 images) | Verified via `verify_mem1.py`: `msg["content"]` stripped in `client.py:149`. Top view is NOT retained in history. |
| **Critic Feedback: Source Code** | `aiongenos/pipeline/stage3_critic.py:183` (`generate_critic_feedback`) | `aiongenos/orchestrator/push_feedback.py:29` (`format_round_feedback`) | **Different** | P1 uses stage3 critic module; Rung-2′ uses dedicated `push_feedback.py`. |
| **Critic Feedback: Active Rounds** | Round $r \ge 2$ (`collect.py:263`) | Round $r \ge 2$ (`push_collect.py:243`) | **Identical** | Both deliver `critic_feedback = None` at Round 1, string report at Round 2+. |
| **Critic Feedback: Arm Scope** | Both arms (`LEFT ARM:` and `RIGHT ARM:`) (`stage3_critic.py:201-208`) | Left arm only (`LEFT ARM:`) (`push_feedback.py:39`) | **Different** | P1 reports target/movement for left & right. Rung-2′ reports left arm only. |
| **Critic Feedback: Distance Metrics** | 1 line: `Euclidean distance to target: started at ... ended at ...` (`prompts.py:361`) | 2 lines: `Fingertip-to-cube distance: ...` and `Cube-to-goal distance: ...` (`prompts.py:388-391`) | **Different** | Rung-2′ discloses two separate task distances (`tip_start/tip_end` and `cg_start/cg_end`). |
| **Critic Feedback: Verdict Criterion** | Arm approach to target: $\Delta = d_{\text{end}} - d_{\text{start}}$ on EE-to-target (`stage3_critic.py:166-179`) | Cube approach to goal: $\Delta = \text{cg}_{\text{end}} - \text{cg}_{\text{start}}$ on cube-to-goal (`push_feedback.py:43, 47-54`) | **Different** (Flawed metric) | `push_feedback.py:43` passes `scalars_start_cm[1], scalars_end_cm[1]` (`cube_to_goal`). Before contact, $\Delta \approx 0 \implies 547/547$ flat verdicts! |
| **User Prompt Template** | `_S1_POS` (`prompts.py:67-71`) | `_S1_EEF_PUSH` (`prompts.py:147-172`) | **Different** | Dual-arm reach vs single-arm push waypoint with orientation and affordance contract. |

---

## 3. Field-by-Field Detailed Audit

### (a) Cross-Episode Memory

#### 1. Retrieval Mechanism and Query
* **P1 L0a:** `MemoryRetriever.retrieve_for_episode` (`aiongenos/memory/retriever.py:113-159`). Query: `init_rgb_bytes=rgb_start` (embedded via `ImageEmbedder` using `facebook/dinov2-base` on CPU, 768-dim) and `init_L_EE=(int(left_x), int(left_y), int(left_z))` read from `env.get_state(level_config)` (`collect.py:226-231`).
* **Rung-2′:** `PushMemoryRetriever.retrieve_for_episode` (`aiongenos/orchestrator/push_memory.py:637-665`). Query: `init_rgb_bytes=rgb_start` (same DINOv2 CPU embedder) and `init_tcp_int` (proprioceptive TCP grid coordinates `(int(left_x), int(left_y), int(left_z))` from `init_snap.tcp_int`) (`push_collect.py:218`).
* **Scoring Formula (Identical):**
  $$\text{score} = \alpha \cdot \cos(\mathbf{e}_{\text{query}}, \mathbf{e}_{\text{recap}}) + (1 - \alpha) \cdot \exp\left(-\frac{\|\mathbf{x}_{\text{query}} - \mathbf{x}_{\text{recap}}\|_2}{\text{scale}}\right)$$
  With $\alpha = 0.4$ (`image_weight`) and $\text{scale} = 30.0\,\text{cm}$ (`state_scale_cm`). Both enforce `success_floor_frac = 2/3`.
* **Evidence Command:**
  ```bash
  python3 -c "from aiongenos.orchestrator.push_memory import PushMemoryRetriever, DEFAULT_IMAGE_WEIGHT, DEFAULT_STATE_SCALE_CM, DEFAULT_SUCCESS_FLOOR_FRAC; print(DEFAULT_IMAGE_WEIGHT, DEFAULT_STATE_SCALE_CM, DEFAULT_SUCCESS_FLOOR_FRAC)"
  # Output: 0.4 30.0 0.6666666666666666
  ```

#### 2. Number of Retrieved Records ($K$)
* Configured top-$K$ is 3 in both pipelines (`aiongenos/memory/retriever.py:70`, `aiongenos/orchestrator/push_memory.py:618`).
* **Empirical Execution Difference:** In run `71134939`, `--recap_buffer_root workspace/recaps_push_pilot_rung2p` was initialized empty (`logs/pilot_rung2p_mem_20261015_165913.log:196`). As a result:
  * Episode 0 (`seed=5000`): 0 hits retrieved (`buffer empty`).
  * Episode 1 (`seed=5001`): 1 hit retrieved (`[81a50701] score=0.92`).
  * Episode 2 (`seed=5002`): 2 hits retrieved.
  * Episodes 3–49: 3 hits retrieved.
* **Evidence Command:**
  ```bash
  python3 -c "import json; from collections import Counter; d=json.load(open('logs/push_smoke_71134939.json')); print(Counter([len(e['memory_hits']) for e in d['episodes']]))"
  # Output: Counter({3: 47, 0: 1, 1: 1, 2: 1})
  ```

#### 3. Modality: Text vs Images
Both pipelines inject a multimodal preamble containing a formatted text block AND a list of base64 PNGs:
* **Which Images are Retrieved?** ONLY `round_01_pre.png` (the initial front camera view)!
  * `aiongenos/memory/retriever.py:214`: `path = rec.image_anchors.get("init_pre")`.
  * `aiongenos/orchestrator/push_memory.py:654`: calls `_load_past_image_b64_list([h[0] for h in hits])`.
  * Even though Rung-2′ recaps store `init_pre_top`, `final_post`, `final_post_top`, and `key_round_post` (`push_memory.py:510-518`), **none** of these are loaded or sent to the teacher during retrieval. Cross-episode memory is strictly monocular start-state image retrieval.
* **Preamble Text Disclosures:**
  * P1: `_format_preamble_text` (`retriever.py:173-208`) presents `init L_EE`, `final L_EE`, `final distance`, `outcome`, `rounds`, and `lesson`.
  * Rung-2′: `format_push_preamble_text` (`push_memory.py:571-610`) presents `start TCP`, `round-1 target`, `cube→goal = ... cm at start, ... cm at end (disclosed)` (because `obs_rung="2"`, level $\ge 2$), `outcome (class: ...)`, and `lesson`.
* **Evidence Command:**
  ```bash
  python3 -c "import inspect; from aiongenos.memory.retriever import _load_past_image_b64_list; print(inspect.getsource(_load_past_image_b64_list))"
  ```

#### 4. Round-by-Round Injection Behavior
* Memory is explicitly passed **only at Round 1** (`round_idx == 0`).
  * P1: `collect.py:285-286`:
    ```python
    r1_preamble_text = memory_preamble_text if round_idx == 0 else None
    r1_preamble_imgs = memory_preamble_images_b64 if round_idx == 0 else None
    ```
  * Rung-2′: `push_collect.py:267-268`:
    ```python
    memory_preamble_text = memory_text if r1_conv is not None and round_idx == 0 else None
    memory_preamble_images_b64 = memory_imgs if r1_conv is not None and round_idx == 0 else None
    ```
* **Destruction of Memory Images at Round 2:** In both pipelines, when `append_user_turn` is invoked at Round 2 (`client.py:146-150`), it loops through all existing messages and strips all `image_url` elements. Therefore, starting in Round 2, the teacher no longer sees the past retrieved images; only the text description in `messages[0]` persists!

---

### (b) Within-Episode History

#### 1. EpisodeConversation Architecture & Pruning
* Both pipelines use `EpisodeConversation` (`aiongenos/vlm/client.py:92-182`).
* **Sliding Window:** `DEFAULT_RECENT_WINDOW = 6` (`client.py:109`).
  * `_prune_to_window` (`client.py:116-130`) preserves `messages[0]` (Round 1 user turn with folded system prompt) + the tail of $2 \times 6 = 12$ messages (6 recent user/assistant pairs).
  * **Rounds 1–7:** No pruning occurs ($1 + 2 \times 6 = 13 \le 13$). All turns are kept.
  * **Round 8+:** Pruning activates. Rounds 2 through $r - 6$ are discarded.
  * **Artifact:** Because `messages[0]` has `role="user"` and `tail` begins with `role="user"`, the pruned payload contains **two consecutive user messages** (`messages[0]` and `messages[1]`).
* **Evidence Command:**
  ```bash
  PYTHONPATH=/home/control/AionGenos python3 /home/control/audit/rung2p_diag/scratch_mem1/verify_mem1.py | grep "roles="
  ```

#### 2. Image Stripping Behavior (`client.py:146-150`)
`aiongenos/vlm/client.py:146-150` states:
```python
# Strip/remove image_url from all existing user messages to conserve context window
for msg in self.messages:
    if msg["role"] == "user" and isinstance(msg["content"], list):
        msg["content"] = [part for part in msg["content"] if part["type"] == "text"]
```
* At Round $r$, **every single past user turn** is stripped of images.
* Past user turns contain only their prompt text (and critic feedback text, if applicable).
* **Only the current user turn** (`messages[-1]`) contains active `image_url` objects.

#### 3. Top-Down Camera View Retention
* **Current Round:**
  * P1 L0a: Monocular front view only (`rgb`). No top-down view is captured or passed.
  * Rung-2′: Front view (`rgb`) + top-down view (`rgb_top`) are BOTH included in `messages[-1]["content"]` (`push_collect.py:270`, `stage1_reasoning.py:253-259`).
* **Older Rounds:**
  * Rung-2′ older rounds do **NOT** retain the top-down view. Because `client.py:149` strips all `image_url` parts indiscriminately, past top-down views are discarded at the exact same moment as past front views.
* **Evidence Command:**
  ```bash
  python3 -c "
  from aiongenos.pipeline.stage1_reasoning import run_stage1_eef
  import inspect; print(inspect.getsource(run_stage1_eef)[1100:1500])
  "
  ```

---

### (c) Critic Feedback

#### 1. Injection Header and Active Rounds
* In both P1 and Rung-2′, critic feedback is `None` in Round 1 and active in all rounds $r \ge 2$.
* When present, it is appended to the user prompt prefixed with:
  `\n\n### CRITIC FEEDBACK FROM PREVIOUS ROUND:\n` (`CRITIC_FEEDBACK_INJECTION_HEADER`, `prompts.py:381`).
* The body starts with `DIAGNOSTIC REPORT FOR PREVIOUS ROUND:` (`CRITIC_FEEDBACK_HEADER`, `prompts.py:355`).

#### 2. Arm Scope and Distance Reporting
* **P1 L0a (`stage3_critic.py:183-209`):**
  * Reports BOTH `LEFT ARM:` and `RIGHT ARM:`.
  * Reports target coordinate, actual movement start $\to$ end, and a single distance line:
    `Euclidean distance to target: started at {d_start:.1f} cm, ended at {d_end:.1f} cm`.
* **Rung-2′ (`push_feedback.py:29-45`):**
  * Reports `LEFT ARM:` only.
  * Replaces the single distance line with two disclosed scalar distances (`PUSH_FEEDBACK_DIST_LINES`, `prompts.py:388-391`):
    ```text
    Fingertip-to-cube distance: started at {tip_start:.1f} cm, ended at {tip_end:.1f} cm
    Cube-to-goal distance: started at {cg_start:.1f} cm, ended at {cg_end:.1f} cm
    ```

#### 3. The 100% Flat Verdict Discrepancy
* **P1 Verdict Logic:** Evaluates arm-to-target delta $\Delta d = d_{\text{end}} - d_{\text{start}}$.
  * $\Delta d < -1.0\,\text{cm} \implies$ `"Result: Successful progress. Left arm moved {abs_delta:.1f} cm closer to target."`
  * $\Delta d > +1.0\,\text{cm} \implies$ `"Result: Regression. Left arm moved {delta:.1f} cm further from target. Adjust prediction direction."`
  * $|\Delta d| \le 1.0\,\text{cm} \implies$ `"Result: No significant progress..."`
* **Rung-2′ Verdict Logic (`push_feedback.py:43, 47-54`):**
  ```python
  def format_round_feedback(..., scalars_start_cm, scalars_end_cm):
      ...
      if scalars_start_cm is not None:
          parts.append(PUSH_FEEDBACK_DIST_LINES.format(...))
          parts.append(_p1_verdict(scalars_start_cm[1], scalars_end_cm[1])) # <--- INDEX 1 EVALUATED!
  ```
  * `scalars_start_cm[0]` is `tip_start` (fingertip-to-cube distance).
  * `scalars_start_cm[1]` is `cg_start` (**cube-to-goal distance**).
  * The verdict evaluates $\Delta = \text{cg}_{\text{end}} - \text{cg}_{\text{start}}$!
  * **Flaw:** Until the robot physically collides with the cube with sufficient force, the cube remains stationary ($\Delta = 0.0\,\text{cm}$).
  * **Result across all 50 episodes of run 71134939:** Out of **547 total feedback rounds**, exactly **547 (100.0%)** received the flat verdict:
    `Result: No significant progress (still X.X cm from target). Try a different direction or larger step size.`
  * Even when the robot moved its fingertip from $8.8\,\text{cm}$ to $4.7\,\text{cm}$ from the cube (approaching closer by $4.1\,\text{cm}$), the feedback told the model: **"No significant progress. Try a different direction or larger step size."**
* **Evidence Command:**
  ```bash
  python3 -c "
  import json
  d = json.load(open('logs/push_smoke_71134939.json'))
  v = [rm['round_feedback'].strip().splitlines()[-1] for ep in d['episodes'] for rm in ep['round_meta'] if rm.get('round_feedback')]
  print('Total feedback rounds:', len(v))
  print('Unique verdicts:', set(x.split('(')[0].strip() for x in v))
  "
  # Output: Total feedback rounds: 547
  # Output: Unique verdicts: {'Result: No significant progress'}
  ```

---

### (d) System Prompt & User Prompt Structure

#### 1. System Prompt Byte Verification
`aiongenos/vlm/prompts.py:42-49`:
```text
You are a bimanual robot controller. You receive a camera image of the scene and must plan the next sub-goal for both arms.
Rules:
- All coordinates are integers in [-100, 100].
- Never output floating point numbers for coordinates.
- Reason step-by-step about the physics before giving targets.
- Output your response in the EXACT format specified below.
```
* Returned by `get_stage1_system_prompt()` in both P1 and Rung-2′.
* **Semantic Contradiction in Rung-2′:** In Rung-2′, the task is strictly single-arm pushing (`CONTROL_MODE: left_eef_waypoint_ori_optional`), yet the system prompt instructs the model that it is controlling both arms.

#### 2. User Prompt Template Comparison
* **P1 L0a (`_S1_POS`, `prompts.py:67-71`):**
  * `TASK: Move your LEFT end-effector to the red target. Your right arm is held still — you do not control it.`
  * `CONTROL_MODE: end_effector_position_only`
  * State: `LEFT_EE_POS`, `RIGHT_EE_POS`, `LEFT_EE_TO_RED_CUBE`, `RIGHT_EE_TO_BLUE_CUBE`.
  * Target output format:
    ```text
    THOUGHT: <one paragraph physics reasoning>
    LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>
    RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>
    STOP: <true|false>
    ```
* **Rung-2′ (`_S1_EEF_PUSH`, `prompts.py:147-172`):**
  * `TASK: Push the yellow cube onto the green zone on the table.`
  * `CONTROL_MODE: left_eef_waypoint_ori_optional`
  * State: `LEFT_EE_POS = (X, Y, Z) # left fingertip (TCP)`, `RIGHT_EE_POS`, `LEFT_GRIPPER = closed (locked)`.
  * Scaffold (`oracle_block` via `isaaclab_env_interface.py:478-480`):
    ```text
    SCAFFOLD (oracle-measured, disclosed):
      LEFT_TIP_TO_CUBE = {tip_cube * 100:.1f} cm
      CUBE_TO_GOAL     = {cube_goal * 100:.1f} cm
    ```
  * View block (`push_memory.py:60`): `The last image is a top-down view of the current scene.`
  * Affordance contract: Explains closed gripper, push only, no grasp/lift.
  * Orientation instructions: Explains optional `LEFT_TARGET_ORI: P=<int> Y=<int> R=<int>` in fixed base-frame axes.
  * Target output format:
    ```text
    THOUGHT: <one paragraph physics reasoning>
    LEFT_TARGET_POS: X=<int> Y=<int> Z=<int>        (required; fingertip/TCP, base-frame integers on the SAME grid as CURRENT STATE — not cm)
    LEFT_TARGET_ORI: P=<int> Y=<int> R=<int>        (OPTIONAL; integer degrees about base axes, applied to the rest orientation; omit for rest)
    STOP: <true|false>
    ```

---

## 4. Exact Wire Payload Comparison at Round 1 vs Round 5

To synthesize the exact differences in what the teacher VLM receives across rounds, the following table compares Round 1 and Round 5:

| Property | Round 1 (P1 L0a) | Round 1 (Rung-2′) | Round 5 (P1 L0a) | Round 5 (Rung-2′) |
| :--- | :--- | :--- | :--- | :--- |
| **Total Messages in Payload** | 1 (`user`) | 1 (`user`) | 9 (`user, asst, user, asst, user, asst, user, asst, user`) | 9 (`user, asst, user, asst, user, asst, user, asst, user`) |
| **System Prompt Location** | In `messages[0]` text prefix | In `messages[0]` text prefix | In `messages[0]` text prefix | In `messages[0]` text prefix |
| **Past Memory Text** | In `messages[0]` text prefix | In `messages[0]` text prefix | Preserved in `messages[0]` text | Preserved in `messages[0]` text |
| **Past Memory Images** | 3 front images in `messages[0]` | 0–3 front images in `messages[0]` | **0 images** (stripped from `messages[0]`) | **0 images** (stripped from `messages[0]`) |
| **Current Scene Images** | 1 image (front RGB) | 2 images (front RGB + top RGB) | 1 image (front RGB in `messages[8]`) | 2 images (front RGB + top RGB in `messages[8]`) |
| **Older Scene Images** | N/A | N/A | **0 images** (all stripped) | **0 images** (all stripped, including past top views) |
| **Critic Feedback** | `None` | `None` | In `messages[8]` user text: reports left & right arm, reach distance, approach progress | In `messages[8]` user text: reports left arm, tip & goal distance, **100% flat verdict** |
| **Action Output Required** | `LEFT_TARGET_POS`, `RIGHT_TARGET_POS` | `LEFT_TARGET_POS`, optional `LEFT_TARGET_ORI` | `LEFT_TARGET_POS`, `RIGHT_TARGET_POS` | `LEFT_TARGET_POS`, optional `LEFT_TARGET_ORI` |

---

## 5. Verification Commands & Re-producibility Suite

All claims in this report can be verified using the following bash one-liners:

1. **Verify memory preamble images only load `init_pre`:**
   ```bash
   grep -n -C 5 'rec.image_anchors.get("init_pre")' aiongenos/memory/retriever.py
   ```
2. **Verify older image stripping in `EpisodeConversation`:**
   ```bash
   sed -n '146,151p' aiongenos/vlm/client.py
   ```
3. **Verify top-down image insertion into conversation:**
   ```bash
   sed -n '253,260p' aiongenos/pipeline/stage1_reasoning.py
   ```
4. **Verify critic verdict evaluates cube-to-goal (`scalars[1]`), not TCP (`scalars[0]`):**
   ```bash
   sed -n '40,45p' aiongenos/orchestrator/push_feedback.py
   ```
5. **Verify 547/547 flat verdicts in run 71134939:**
   ```bash
   python3 -c "import json; d=json.load(open('logs/push_smoke_71134939.json')); v=[rm['round_feedback'].splitlines()[-1] for ep in d['episodes'] for rm in ep['round_meta'] if rm.get('round_feedback')]; print('Total:', len(v), 'Flat:', sum('No significant progress' in x for x in v))"
   ```
6. **Verify memory hits distribution in run 71134939:**
   ```bash
   python3 -c "import json; from collections import Counter; d=json.load(open('logs/push_smoke_71134939.json')); print(Counter([len(e['memory_hits']) for e in d['episodes']]))"
   ```
