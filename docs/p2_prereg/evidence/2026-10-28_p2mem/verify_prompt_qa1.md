# QA Verification Report: External Prompt & Harness Review (`prompt_external_review.md`)

- **Target File**: `/home/control/AionGenos/docs/p2_prereg/prompt_external_review.md`
- **Verifier Role**: QA Verifier (`qa1`)
- **Date**: 2026-10-28
- **Status**: **PASS (with 1 minor erratum noted)**
- **Audit Scope**:
  1. §2 reconstruction of AionGenos prompt pipeline vs codebase and CPU rendering of Pin-4c rung-1 lesson-only (rounds 1, 2, 8).
  2. §1 external prompt citations sampled (Voyager, Gemini 4 Argon, Anthropic) vs primary sources.
  3. §3 item-by-item provenance citations for "差異能否解釋我們的觀察".

---

## 1. §2 Pipeline Reconstruction vs Code & CPU Rendering Verification

### 1.1 Code Alignment Check

| Component | Code Location | Review Doc Section | Code vs Doc Alignment | Verification Notes |
|---|---|---|---|---|
| **System Prompt** | `aiongenos/vlm/prompts.py:42-49`, `480-481` | §2.1 (lines 340–350) | **EXACT MATCH** | `STAGE1_SYSTEM` text is byte-for-byte identical. Delivery mechanism (co-locating in Turn 0 user text block for llama-server vision token injection per `client.py:53-63, 152-155`) is accurately documented. |
| **Stage-1 Push User Prompt** | `aiongenos/vlm/prompts.py:147-172`, `181` | §2.2 (lines 352–384) | **EXACT MATCH** | `_S1_EEF_PUSH` text is byte-for-byte identical. |
| **Dynamic Placeholders** | `isaaclab_env_interface.py:196-198, 460-505`, `run_push_collect.py:164` | §2.2 (lines 385–412) | **EXACT MATCH** | `{instruction}`, `{left_x/y/z}` (TCP mapped via `position_metric_to_int`), `{right_x/y/z}` (hand pose from `get_state` retained), `{left_gripper}`, `{frame_block}`, `{oracle_block}`, `{view_block}` accurately traced. |
| **Frame Convention Line (`d1`)** | `aiongenos/vlm/prompts.py:394-411` | §2.2 (lines 394–399) | **EXACT MATCH** | With `bounds = WorkspaceBounds((-0.3, 0.6), (-0.4, 0.4), (0.0, 0.7))` and `grid_span = 200`: `ux = 0.45 cm`, `uy = 0.40 cm`, `uz = 0.35 cm`. Text rendered by `format_frame_convention_line(bounds)` matches verbatim. |
| **Memory Preamble** | `aiongenos/orchestrator/push_memory.py:564-638` | §2.3 (lines 413–444) | **EXACT MATCH** | `_PUSH_PREAMBLE_HEADER` and `_PUSH_PREAMBLE_HEADER_NOCOORDS` match verbatim. `COORD_PATTERN` regex and replacement with `[coordinates omitted]` match verbatim. Standby TCP `(-40, 26, 53)` and `state_sim ≈ 1.0` (compressing scores to `0.960–0.998`) correctly traced. |
| **Per-Round Feedback** | `push_feedback.py:29-66`, `prompts.py:355-391` | §2.4 (lines 445–468) | **PASS (1 minor typo in doc)** | At `obs_rung="1"`, feedback contains proprioception only; distance and verdict lines are omitted even if `--verdict_contact_switch` (`d2`) is passed. **Minor Doc Erratum**: In §2.4 line 463 (example template for `obs_rung >= 2`), the doc shows `to X={ex} Y={ey} Z={sz}` instead of `Z={ez}`. Line 454 (rung 1) is correct (`Z={ez}`). |
| **Multi-Turn Window & Image Stripping** | `client.py:92-182`, `stage1_reasoning.py:247-260` | §2.5 (lines 469–489) | **EXACT MATCH** | Image stripping loop in `append_user_turn` strips all prior images on Round 2+, leaving Turn 0 text pointing to nonexistent images. `DEFAULT_RECENT_WINDOW = 6` retains Turn 0 + last 12 messages. Round 8+ pruning boundary drops Round 1 assistant response, leaving consecutive `"role": "user"` turns. |

---

### 1.2 Actual CPU Python Rendering Test (Pin-4c Rung-1 Lesson-Only)

Executed test script (`/home/control/audit/p2mem/scratch_prose_disc/render_p4c_test.py`) with `PYTHONPATH=/home/control/AionGenos python3` on CPU, using real records from `workspace/recaps_push_rung1p_p4c_lesson/3786f4e5` under exact Pin-4c rung-1 lesson-only configuration (`obs_rung="1"`, `preamble_coords="off"`, `frame_convention=True`, `round_feedback=True`, `round_history=True`).

#### Round 1 Rendering Verification:
- **`conversation.messages` count**: `1` (single `"role": "user"` message).
- **Parts breakdown in Turn 0**:
  1. `[0] text`: `STAGE1_SYSTEM + "\n\n"` (357 chars).
  2. `[1] text`: Preamble text (2380 chars), beginning:
     ```text
     PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see the scene at its start, the outcome, and a short lesson you wrote afterwards. Use these to choose a better target for the current scene.


     [PAST EPISODE 1] (similarity=0.985)
       Image 1: the scene at the start of that episode
       outcome    = failure
       rounds     = 3
       lesson     : In the first round, my target was placed well in front...
     ```
     *(Header omits `your round-1 fingertip (TCP) target`; no `start TCP` or `round-1 target` coordinate lines; lessons present).*
  3. `[2..4] image_url`: 3 past episode start images (`preamble_image_base64_list`).
  4. `[5] image_url`: Current round-1 front camera RGB image (`image_base64`).
  5. `[6] text`: User prompt `_S1_EEF_PUSH` populated with state (`left_x=-40, left_y=26, left_z=53`, `left_gripper=closed (locked)`, `frame_block`, empty `oracle_block` and `view_block`).
- **Conclusion**: Matches §2.3 and §2.5 exactly.

#### Round 2 Rendering Verification:
- **`conversation.messages` count**: `3` (Turn 0 user, Turn 1 assistant, Turn 2 user).
- **Image stripping on Turn 0**:
  - `Turn 0 part types`: `['text', 'text', 'text']`.
  - **All 3 past images and the Round-1 scene image were completely stripped** from Turn 0 by `client.py:148-150`.
  - Turn 0 retains text referring to `"Image 1: the scene at the start of that episode"` although no images exist in Turn 0.
- **Round 2 user turn content**:
  - `Turn 2 part types`: `['image_url', 'text']` (only the current Round-2 front camera image is present).
  - Feedback injected into user prompt:
    ```text
    ### CRITIC FEEDBACK FROM PREVIOUS ROUND:
    DIAGNOSTIC REPORT FOR PREVIOUS ROUND:
      LEFT ARM:
        Target coordinate was predicted at: X=50 Y=0 Z=40
        Actual movement: from X=-40 Y=26 Z=53 to X=51 Y=-1 Z=38
    ```
  - Confirmed: **Zero distance lines and zero verdict lines** (verdict contact switch `d2` is inactive because `obs_rung < 2`).
- **Conclusion**: Matches §2.4 and §2.5 exactly.

#### Round 8 Rendering Verification:
- **Sliding window pruning trigger**:
  - After Round 7 assistant turn: `len(messages)` reached 14 (`> 2 * 6 + 1 = 13`).
  - `_prune_to_window()` retained `messages[0]` + `messages[-12:]` (`tail`).
  - Because `tail[0]` was Round 2's user turn (`"role": "user"`), Round 1's assistant turn (`messages[1]`) was dropped.
  - At Round 8: message roles sequence was:
    `['user', 'user', 'assistant', 'user', 'assistant', 'user', 'assistant', 'user', 'assistant', 'user', 'assistant', 'user', 'assistant', 'user']`.
  - `messages[0]` (Turn 0) is immediately followed by `messages[1]` (Round 2 user turn), creating **consecutive user turns**.
- **Conclusion**: Matches §2.5 line 488 claim exactly.

---

## 2. §1 External Prompt Quotations Spot-Check (3 Sentences Each)

All quotations were checked against the fetched primary source repositories, blog posts, and research papers.

### 2.1 Voyager (`MineDojo/Voyager` Repository)

| Sample # | Target File & Line Range | Quoted Text in Review Doc | Verbatim Primary Source Fetch | Result |
|---|---|---|---|---|
| **V1** | `voyager/prompts/curriculum.txt:1-3` | `"You are a helpful assistant that tells me the next immediate task to do in Minecraft. My ultimate goal is to discover as many diverse things as possible, accomplish as many diverse tasks as possible and become the best Minecraft player in the world."` | Fetched from `raw.githubusercontent.com/MineDojo/Voyager/main/voyager/prompts/curriculum.txt:1` | **CONFIRMED VERBATIM** |
| **V2** | `voyager/prompts/action_template.txt:1` | `"You are a helpful assistant that writes Mineflayer javascript code to complete any Minecraft task specified by me."` | Fetched from `raw.githubusercontent.com/MineDojo/Voyager/main/voyager/prompts/action_template.txt:1` | **CONFIRMED VERBATIM** |
| **V3** | `voyager/prompts/critic.txt:1` | `"You are an assistant that assesses my progress of playing Minecraft and provides useful guidance."` | Fetched from `raw.githubusercontent.com/MineDojo/Voyager/main/voyager/prompts/critic.txt:1` | **CONFIRMED VERBATIM** |
| *Auxiliary* | `voyager/agents/skill.py:120-128` | Docs & scores loop: `for doc, _ in docs_and_scores: skills.append(...)` (score `_` discarded) | Fetched from `voyager/agents/skill.py:126` | **CONFIRMED VERBATIM** |

### 2.2 Gemini 4 Argon (`developers.googleblog.com/gemini-4-argon-for-robotics`)

| Sample # | Section / Anchor | Quoted Text in Review Doc | Verbatim Primary Source Fetch | Result |
|---|---|---|---|---|
| **A1** | `Unlocking robot control with Argon` → `2. Zero-shot control` (Prompt) | `"Task: Get the robot arm to reorient the mug upright and put the napkin inside the mug."` | Fetched from blog HTML (Zero-shot control code block line 3) | **CONFIRMED VERBATIM** |
| **A2** | `2. Zero-shot control` → `## Visual Coordinate Reference` | `"`+X` (UP in image): Away from robot base \| `-X` (DOWN): Towards robot base"` | Fetched from blog HTML (Visual Coordinate Reference line 1) | **CONFIRMED VERBATIM** |
| **A3** | `Unlocking Real2Sim with Argon` → `1. Robot view to simulation` (Prompt) | `"No sim cheating: task objects may move only through real MuJoCo contact with the robot hands and the environment (mj_step)."` | Fetched from blog HTML (Real2Sim prompt block line 1) | **CONFIRMED VERBATIM** |
| *Auxiliary* | `3. Omni control` (Prompt) | `"Keep inactive hands retracted and avoid blocking the camera's view of objects in the workspace."` | Fetched from blog HTML (Omni control bullet 2) | **CONFIRMED VERBATIM** |

### 2.3 Anthropic ("Claude plays robotics", `anthropic.com/research/claude-plays-robotics`)

| Sample # | Section / Anchor | Quoted Text in Review Doc | Verbatim Primary Source Fetch | Result |
|---|---|---|---|---|
| **C1** | `§07 Appendix` → `Prompts`, para 1 | `"We did not tune prompts separately for each model. Each interface used one fixed prompt template. At trial time, the template was filled with task-specific details such as joint count, robot mass, force limits, and observation fields."` | Fetched from article body `§07 Appendix -> Prompts` | **CONFIRMED VERBATIM** |
| **C2** | `§03 Direct control is bad, but improving` → `Low-level manipulation`, para 4 | `"It is never given the objects’ coordinates directly, so it must first identify the relevant objects from vision and then use that information to decide how the hand should move next."` | Fetched from article body `§03 -> Low-level manipulation` | **CONFIRMED VERBATIM** |
| **C3** | `§05 What’s the bottleneck?` → `Is visual perception the bottleneck?`, para 5 | `"The cursor tool, by contrast, gives every model a large uplift on manipulation—for Mythos Preview, success on the 10-task subset goes from 6% to 32%."` | Fetched from article body `§05 -> Is visual perception the bottleneck?` | **CONFIRMED VERBATIM** |
| *Auxiliary* | `§07 Appendix` → `Vision inputs` → `Keeping prior frames`, para 1 | `"All published vision cells kept prior frames in context."` | Fetched from article body `§07 Appendix` | **CONFIRMED VERBATIM** |

---

## 3. §3 Provenance Citations Verification ("差異能否解釋我們的觀察")

Every provenance citation in §3 was cross-checked against `/home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md`, `wp3a_rung2p_diagnosis_2026-10-22.md`, and raw run logs in `logs/push_smoke_*.json`.

| §3 Item | Claim & Mechanism | Provenance Anchor Cited in Doc | Primary Source Verification | Verdict |
|---|---|---|---|---|
| **3.1 Identity Framing** | System prompt says "bimanual … both arms" and gives `RIGHT_EE_POS` while push is single-arm left. Did not cause output format failures (0 dual-arm failures in runs `71134939`, `611a3e2a`, `663c049a`, `3786f4e5`), but adds distractor tokens. | `wp3a_rung2p_diagnosis_2026-10-22.md` §1a (line 32) | `diagnosis` line 32 explicitly lists 4 differences from P1 including `"that the system prompt says 'bimanual … both arms'"`. Run logs verify 0/1085 total rounds emitted `RIGHT_TARGET`. | **VERIFIED ACCURATE** |
| **3.2 Memory Preamble Presentation** | Explains `(e)` coordinate-copying collapse and height locking. `611a3e2a` copied `[40,20,50]` 35/40 times; `663c049a` (coords ON) copied `[60,10,53]` 37/49 times (SR=3/50, 10 unique R1 targets, 161/183 Z=53 rounds); `3786f4e5` (coords OFF) raised unique R1 targets 10→42, cut Z=53 rounds 161→37, raised SR 3→13/50 (Fisher two-sided $p=0.012$). | `wp3a_push_provenance.md` lines 2382–2388, 2463–2476 | All metrics and values in `push_provenance.md` lines 2382–2388 and 2463–2476 match exactly. Table in line 2466–2470 has exact figures. | **VERIFIED ACCURATE** |
| **3.3 Feedback Form & Outcome Verification** | 1. Active misdirection in `rung-2′` (`71134939`): 547/547 rounds read "No significant progress" on `cube_goal` before contact.<br>2. Recap confabulation: 44% at rung-1 (`e4aebf36`), 42% at rung-1b (`30f15f0c`) vs 0% at rung-2 (`3e8c52d4`).<br>3. `rung-1′` premature STOPs (9) and plateaus (30) in `611a3e2a`. | `wp3a_rung2p_diagnosis_2026-10-22.md` §2.1 (lines 36–38); `wp3a_push_provenance.md` lines 1880–1885, 1931–1933, 2065–2068, 2324–2327, 2379 | `diagnosis` lines 36–38 confirms 547/547 rounds. `push_provenance.md` lines 1880–1885 (rung-1), 1931–1933 (rung-1b 42% vs 44%), and 2065–2068 (rung-2 true confabulation 0/48) match exact percentages. | **VERIFIED ACCURATE** |
| **3.4 History Handling & Image Retention** | Seed-paired comparison (seeds 5000–5049): `rung-2` (stateless) had 53% contact band $Z \in [30, 40]$ and Round-2 $Z=53$ in 1/50 eps; `rung-2′` (history ON) collapsed contact band to 2%, Round-2 $Z=53$ in 45/50 eps, and 509/597 rounds (85%) stayed locked at $Z=53$. | `wp3a_rung2p_diagnosis_2026-10-22.md` §2.4 (lines 47–53); `wp3a_push_provenance.md` lines 2315–2323 | Table in `diagnosis` lines 49–53 matches table in review doc byte-for-byte (53% vs 2%, 1/50 vs 45/50). Line 2315 confirms 509/597 rounds (85%) at $z=0.535\text{ m}$. | **VERIFIED ACCURATE** |
| **3.5 Output Format & Reasoning Budget** | In `71134939`, free-form `THOUGHT` rationalized vertical hover error as planar XY error in 83% of rounds; real vertical reasoning occurred in only 25–46/597 rounds (4–8%). Context bloat F30/F43. | `wp3a_rung2p_diagnosis_2026-10-22.md` §1 (lines 20–21), §2.3 (line 46); `client.py:95-99` | `diagnosis` line 21 confirms 25–46/597 rounds (4–8%). Line 46 confirms 83% planar rationalization. `client.py:95-99` documents F30/F43 context bloat. | **VERIFIED ACCURATE** |
| **3.6 Exploration vs. Exploitation** | Memorized blind sweep: `611a3e2a` copied `[40,20,50]` 35/40 times; `663c049a` copied `[60,10,53]` 37/49 times under `2/3` success floor. `3786f4e5` raised unique targets to 42. | `wp3a_push_provenance.md` lines 2382–2388, 2466–2476 | Matches `push_provenance.md` exact counts and descriptions. | **VERIFIED ACCURATE** |
| **3.7 Grounding Aids, Action Primitives & Pausing** | 1. Pre-`d1` axis inversion in `71134939` (536/597 Y-dominant, 62–64% thoughts calling Y forward) fixed by `d1` in `611a3e2a` (74/155 cite +X forward).<br>2. `rung-1b` (`30f15f0c`) got 0/50 and clustered at X=0 (68%) due to lack of image-to-grid mapping.<br>3. Remaining low stimulus tracking in Pin-4c (`3786f4e5`: $\rho_X = -0.098$, $\rho_Y = +0.278$).<br>4. Rejection of `d3-i` on 2026-10-22. | `wp3a_rung2p_diagnosis_2026-10-22.md` §2.2 (lines 39–42); `wp3a_push_provenance.md` lines 1928–1930, 2343, 2361–2364, 2389, 2469 | `diagnosis` lines 39–42 confirms 536/597 and 62–64%. `push_provenance.md` line 2389 confirms 74/155. Line 1928–1930 confirms grid-centre/zero clustering. Lines 2361–2364 confirms `d3-i` rejection verbatim. | **VERIFIED ACCURATE** |

---

## 4. Summary & QA Recommendation

1. **§2 Code Fidelity**: Fully verified. Code references, function names, prompt templates, and execution mechanics correspond accurately to the current codebase (`aiongenos/vlm/prompts.py`, `push_memory.py`, `push_feedback.py`, `client.py`, `stage1_reasoning.py`). CPU test rendering confirmed Turn 0 layout, Round 2 image stripping, and Round 8 consecutive user turns.
2. **§1 External Citations**: All sampled sentences from Voyager repo, Gemini 4 Argon blog, and Anthropic article exist verbatim in primary sources.
3. **§3 Provenance Traceability**: All cited figures, percentages, run IDs, and diagnosis references match the underlying provenance logs and diagnostic ledgers.
4. **Minor Action Item**: Correct the single typo in §2.4 line 463 (`Z={sz}` → `Z={ez}`) in `prompt_external_review.md`.
