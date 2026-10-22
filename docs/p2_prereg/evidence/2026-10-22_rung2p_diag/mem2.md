# Audit Report: Memory & Teacher Condition in Rung-2′ vs P1 L0a (mem2)

**Auditor:** mem2 (Independent auditor, Rule 10 compliance)  
**Date:** 2026-10-22  
**Target Run Under Study:** `71134939` (rung-2′, seeds 5000–5049, memory ON, feedback ON, history ON)  
**Reference Task:** P1 L0a (`L0a_single_reach_left` / `Isaac-AionGenos-L0a-Left-v0`, reach curriculum level -2)  
**Output Target:** `/home/control/audit/rung2p_diag/mem2.md`

---

## 1. Executive Summary

This audit performs a strict, field-by-field, code-level verification comparing the prompt inputs and sensory/memory conditions received by the Teacher VLM at round $r$ in **Rung-2′ Push** (`push_collect.py` under run `71134939`) against **P1 L0a Reach** (`collect.py` / `stage1_reasoning.py`).

While Rung-2′ was intended to reproduce the "full P1 condition" (Rule 10), code execution and data inspection reveal **four critical disparities** between the two pipelines:
1. **Critic Feedback Verdict Disparity:** In P1 L0a, the feedback verdict evaluates Euclidean distance from the arm end-effector to the target cube (`stage3_critic.py:166`). In Rung-2′ push, the verdict evaluates change in `cube_to_goal` distance (`push_feedback.py:43, 49-54`). Because the cube cannot move before physical contact, every pre-contact round in Rung-2′ receives a flat verdict (`CRITIC_FEEDBACK_FLAT`: *"Result: No significant progress (still 8.8 cm from target)..."*), even when the fingertip successfully approaches the cube from 15 cm down to 4.5 cm. This continuously informs the teacher that its moves did nothing.
2. **Preamble Image Stripping across Turns:** In both P1 and Rung-2′, `EpisodeConversation.append_user_turn` (`client.py:146-150`) strips all image URLs from previous user turns. Consequently, at Round 2 ($r=2$), the retrieved past-episode images in `messages[0]` are stripped. The teacher retains past lesson text in `messages[0]`, but loses all visual anchor images from past episodes for rounds 2 through 12.
3. **Cross-Episode Buffer Population at Runtime:** P1 L0a evaluation operated over an established, frozen external recap buffer of 547 episodes rich in successes (`workspace/l2_audit/DIAGNOSTIC_4a_PREDICTION.md:37`). In contrast, run `71134939` started with an empty recap buffer; 100% of the recaps retrieved by episodes 1–49 were failure/timeout episodes (`push_smoke_71134939.json`), completely inverting the intended 2/3 success floor.
4. **Multi-Camera History Asymmetry:** In Rung-2′, the current turn presents 2 images (front view + top-down view via `stage1_reasoning.py:253-260`), whereas past turns retain 0 images. However, the retrieval key embeds only the front image (`push_memory.py:645`), ignoring the top-down perspective entirely.

---

## 2. Field-by-Field Detailed Audit

### (a) Cross-Episode Memory

| Dimension | P1 L0a (`collect.py`, `retriever.py`) | Rung-2′ Push (`push_collect.py`, `push_memory.py`) | Verification & Code Citations |
| :--- | :--- | :--- | :--- |
| **Retrieval Trigger & Round** | Round 0 ($r=1$) only. `collect.py:285-286` sets `r1_preamble_text` and `r1_preamble_imgs` only when `round_idx == 0`. | Round 0 ($r=1$) only. `push_collect.py:267-268` injects `memory_text` and `memory_imgs` only when `r1_conv is not None and round_idx == 0`. | Both inject exclusively on the first turn ($r=1$). Subsequent rounds pass `None`. |
| **Query State Key** | Initial left EE position grid `(left_x, left_y, left_z)` as integers. (`collect.py:227-231`). | Initial left TCP position grid `(tx, ty, tz)` as integers. (`push_collect.py:194, 218`, `push_memory.py:644`). | Both use normalized 3D base-frame integer grids of the active end-effector. |
| **Query Image Key** | Front camera initial RGB image bytes (`init_rgb_bytes`). (`collect.py:224, 237`, `retriever.py:124-126`). | Front camera initial RGB image bytes (`rgb_start`). (`push_collect.py:183, 218`, `push_memory.py:645`). | **Identical sensor**: Front camera only. Rung-2′ dumps a top-down start image (`push_collect.py:191`), but does **not** embed it for retrieval. |
| **Scoring Formula** | `score = 0.4 * img_cos + 0.6 * exp(-d_cm / 30.0)`. (`recap_buffer.py:219, 237`, `retriever.py:73-74`). | `score = 0.4 * img_cos + 0.6 * exp(-d_cm / 30.0)`. (`recap_buffer.py:219, 237`, `push_memory.py:626-627`). | **Byte-identical logic**: Both invoke the shared `RecapBuffer.retrieve` implementation. |
| **Candidate Filtering** | Filters `exclude_run_ids` and `success_only` if flagged. (`recap_buffer.py:203-207`). | Invokes shared retrieve, then enforces `is_push_record` (`metadata.task == 'WP1_3a_push'`). (`push_memory.py:650-653`). | Rung-2′ drops foreign reach/L2 records to prevent cross-task contamination. |
| **Number Retrieved ($K$)** | `top_k = 3`. (`retriever.py:70`, `run_collect.py:58`). | `top_k = 3`. (`push_memory.py:625`, `scripts/run_push_collect.py:44`). | Nominally up to 3 records. |
| **Runtime Retrieved Count in Run 71134939** | Full 3 records retrieved from pre-populated buffer of 547 recaps. | Ep 0: **0** recaps; Ep 1: **1** recap; Ep 2: **2** recaps; Ep 3–49: **3** recaps. | Verified from `logs/push_smoke_71134939.json` (`episodes[0]['memory_hits'] == []`). Buffer was empty at start. |
| **Success Floor** | $\lceil 2/3 \times 3 \rceil = 2$ successes required if available. (`recap_buffer.py:244`). | $\lceil 2/3 \times 3 \rceil = 2$ successes required if available. (`recap_buffer.py:244`). | In run `71134939`, **0/50** episodes succeeded. The buffer held 0 successes, so fallback (`recap_buffer.py:259-268`) returned 100% failure/timeout recaps. |
| **Retrieved Images (Which Images?)** | `_load_past_image_b64_list` loads `rec.image_anchors.get("init_pre")` **only**. (`retriever.py:210-224`). | `_load_past_image_b64_list` loads `rec.image_anchors.get("init_pre")` **only**. (`retriever.py:210-224`, `push_memory.py:639, 654`). | **Start front image only** (up to 3 PNGs). Even though push recaps save `init_pre_top`, `final_post`, etc., only `init_pre` is retrieved. |
| **Retrieved Text Format** | Formatted by `_format_preamble_text` (`retriever.py:173-207`). Fields: `init L_EE`, `final L_EE`, `final distance`, `outcome`, `rounds`, `lesson`. | Formatted by `format_push_preamble_text` (`push_memory.py:571-610`). Fields: `start TCP`, `round-1 target` + ORI + reached, `cube→goal` start/end, `outcome`, `rounds`, `lesson`. | Tail instruction: P1 says *"The LAST image below is the CURRENT scene"* (`retriever.py:204`); Rung-2′ says *"The LAST TWO images below are the CURRENT scene: front view, then top-down view"* (`push_memory.py:604`). |
| **Cross-Round Retention** | Preamble text stays in `messages[0]` across all rounds. Past images stripped at Round 2 (`client.py:146-150`). | Preamble text stays in `messages[0]` across all rounds. Past images stripped at Round 2 (`client.py:146-150`). | Identical behavior due to shared `EpisodeConversation` mechanics. |

---

### (b) Within-Episode History & Conversation Mechanics

| Dimension | P1 L0a (`collect.py`, `client.py`) | Rung-2′ Push (`push_collect.py`, `client.py`) | Same / Different & Evidence |
| :--- | :--- | :--- | :--- |
| **Conversation Class** | `EpisodeConversation(get_stage1_system_prompt())` (`collect.py:194`). | `EpisodeConversation(get_stage1_system_prompt())` (`push_collect.py:259`). | **Same**: Shared class in `aiongenos/vlm/client.py:92-182`. |
| **History Flag** | Always enabled by default in `collect.py`. | Enabled conditionally via `--round_history` (`push_collect.py:151, 254-260`). In run `71134939`, `round_history: True` was set. | **Same condition at runtime** in run 71134939 (`01b82183-43e.json:metadata.round_history == True`). |
| **Turn Window Retention** | `DEFAULT_RECENT_WINDOW = 6` (`client.py:109`). Keeps `messages[0]` + last 6 user/assistant pairs (`client.py:120-130`). | `DEFAULT_RECENT_WINDOW = 6` (`client.py:109`). Keeps `messages[0]` + last 6 user/assistant pairs (`client.py:120-130`). | **Same**: Window pruning formula `keep_tail = 2 * recent_window = 12` messages. |
| **Image Stripping on Prior Turns** | Strips all `image_url` parts from all existing user turns upon appending a new turn (`client.py:146-150`). | Strips all `image_url` parts from all existing user turns upon appending a new turn (`client.py:146-150`). | **Same**: Confirmed by scratch execution. Older turns in `messages` become purely text. |
| **Top-Down Camera Handling** | No top-down camera exists in P1 L0a (monocular front view only). | `run_stage1_eef` (`stage1_reasoning.py:253-260`) splices `extra_b64` (top view) into `messages[-1]["content"]` for the current round only. | **Different**: In Rung-2′, the latest user turn carries 2 images (front + top). However, on subsequent rounds, the top view of older turns is stripped alongside the front view. |
| **Prompt State View Block** | Empty / omitted. | State dictionary includes `view_block = "The last image is a top-down view of the current scene.\n"` (`push_memory.py:60, 95`). | Rung-2′ explicitly instructs the model about the top-down image in the text prompt at every round. |

---

### (c) Critic Feedback

| Field / Element | P1 L0a (`stage3_critic.py`, `collect.py`) | Rung-2′ Push (`push_feedback.py`, `push_collect.py`) | Same / Different & Evidence |
| :--- | :--- | :--- | :--- |
| **Injection Header** | `### CRITIC FEEDBACK FROM PREVIOUS ROUND:` (`prompts.py:381`, `stage1_reasoning.py:75`). | `### CRITIC FEEDBACK FROM PREVIOUS ROUND:` (`prompts.py:381`, `stage1_reasoning.py:243`). | **Same**: Imported string constant. |
| **Diagnostic Report Header** | `DIAGNOSTIC REPORT FOR PREVIOUS ROUND:` (`prompts.py:355`, `stage3_critic.py:200`). | `DIAGNOSTIC REPORT FOR PREVIOUS ROUND:` (`prompts.py:355`, `push_feedback.py:38`). | **Same**: Imported string constant. |
| **Active Arms Reported** | Both `LEFT ARM:` and `RIGHT ARM:` blocks. (`stage3_critic.py:201-208`). | `LEFT ARM:` block only. (`push_feedback.py:39`). | **Different**: Push is single-arm; right arm block is omitted. |
| **Target & Movement Lines** | `Target coordinate was predicted at: X={px} Y={py} Z={pz}`<br>`Actual movement: from X={sx} Y={sy} Z={sz} to X={ex} Y={ey} Z={ez}` (`prompts.py:359-360`). | `Target coordinate was predicted at: X={px} Y={py} Z={pz}`<br>`Actual movement: from X={sx} Y={sy} Z={sz} to X={ex} Y={ey} Z={ez}` (`push_feedback.py:26, 39`). | **Same**: Reuses `_P1_ARM_HEAD` verbatim. |
| **Distance Reporting** | **Single line:**<br>`Euclidean distance to target: started at {d_start:.1f} cm, ended at {d_end:.1f} cm` (`prompts.py:361`). | **Two lines:**<br>`Fingertip-to-cube distance: started at {tip_start:.1f} cm, ended at {tip_end:.1f} cm`<br>`Cube-to-goal distance: started at {cg_start:.1f} cm, ended at {cg_end:.1f} cm` (`prompts.py:389-390`, `push_feedback.py:40-42`). | **Different**: P1 reports single reach distance. Rung-2′ reports approach distance and goal distance. |
| **Verdict Dead Band** | 1.0 cm (`CRITIC_PROGRESS_DEAD_BAND_CM = 1.0`, `prompts.py:378`). | 1.0 cm (`CRITIC_PROGRESS_DEAD_BAND_CM = 1.0`, `prompts.py:378`, `push_feedback.py:50, 52`). | **Same**: 1.0 cm threshold. |
| **Verdict Distance Metric** | Evaluates end-effector to cube target distance (`stage3_critic.py:166`). | Evaluates **`cube_to_goal`** distance (`push_feedback.py:43, 49`). | **CRITICAL DIFFERENCE**: In Rung-2′, until the cube moves, `cube_to_goal` does not change ($|\Delta| < 1.0\text{ cm}$). Thus, all pre-contact rounds receive the flat verdict: *"Result: No significant progress..."*. |

---

### (d) System Prompt

| Component | P1 L0a (`prompts.py`, `stage1_reasoning.py`) | Rung-2′ Push (`prompts.py`, `stage1_reasoning.py`) | Same / Different & Evidence |
| :--- | :--- | :--- | :--- |
| **Function Call** | `get_stage1_system_prompt()` (`stage1_reasoning.py:68`). | `get_stage1_system_prompt()` (`stage1_reasoning.py:240`). | **Same**: Returns `STAGE1_SYSTEM` (`prompts.py:42-49`). |
| **Prompt Text** | `"You are a bimanual robot controller. You receive a camera image of the scene and must plan the next sub-goal for both arms.\nRules:\n- All coordinates are integers in [-100, 100].\n- Never output floating point numbers for coordinates.\n- Reason step-by-step about the physics before giving targets.\n- Output your response in the EXACT format specified below."` | Byte-identical text. | **Byte-identical**: Even though push is single-arm left-hand execution, the system prompt explicitly says *"bimanual robot controller"* and *"plan the next sub-goal for both arms"*. |
| **Folding into User Turn** | Folded into `messages[0]` as leading text: `self.system_prompt + "\n\n"`. (`client.py:63, 155`). | Folded into `messages[0]` as leading text: `self.system_prompt + "\n\n"`. (`client.py:63, 155`). | **Same**: Required for Gemma 4 / llama-server compatibility (`client.py:53-56`). |

---

## 3. Master Synthesis Table: Teacher Reception at Round $r$

| Item | P1 L0a Code Path | Rung-2′ Code Path | Same / Different | Code Evidence & Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **System Prompt** | `aiongenos/vlm/prompts.py:42-49, 452` | `aiongenos/vlm/prompts.py:42-49, 452` | **Same** | `STAGE1_SYSTEM` is imported and folded into `messages[0]` on turn 1 (`client.py:155`). |
| **User Prompt Template** | `_S1_POS` (`prompts.py:67-71`) | `_S1_EEF_PUSH` (`prompts.py:147-172`) | **Different** | P1 asks for 2 arms pos only; Rung-2′ asks for left TCP pos + optional ORI + affordance contract. |
| **Disclosed Scaffold State** | `get_state` (`isaaclab_env_interface.py:192-218`) | `_push_state` (`isaaclab_env_interface.py:457-494`) | **Different** | P1 provides scalar EE-to-target distances. Rung-2′ provides `LEFT_TIP_TO_CUBE` and `CUBE_TO_GOAL` cm. |
| **Top-Down Camera Image** | None (`run_stage1` takes single `rgb_bytes`) | `stage1_reasoning.py:253-260` (`extra_image_bytes`) | **Different** | Rung-2′ feeds top-down image in addition to front image on current round. |
| **Older Turn Image Stripping** | `aiongenos/vlm/client.py:146-150` | `aiongenos/vlm/client.py:146-150` | **Same** | `for msg in self.messages: msg["content"] = [p for p in msg["content"] if p["type"] == "text"]`. Older turns stripped of all images. |
| **Top View Kept in History?** | N/A | `aiongenos/vlm/client.py:147-149` | **Different from intent (Stripped)** | Top view is stripped from all prior user turns alongside the front image. Only current turn has images. |
| **Cross-Episode Preamble Timing** | `collect.py:285-286` (Round 0 only) | `push_collect.py:267-268` (Round 0 only) | **Same** | Injected on Round 0. In Round $\ge 2$, preamble text persists in `messages[0]`, but preamble images are stripped. |
| **Cross-Episode Retrieved Images** | `retriever.py:210-224` | `retriever.py:210-224`, `push_memory.py:654` | **Same** | Loads `rec.image_anchors["init_pre"]` only (start front view). No top-down past images loaded. |
| **Cross-Episode Retrieved Text** | `retriever.py:173-207` | `push_memory.py:571-610` | **Different** | Push preamble includes `start TCP`, `round-1 target`, and `cube→goal` displacement. |
| **Cross-Episode Buffer Quality (Run)** | Pre-populated 547 recaps (mostly success) | `logs/push_smoke_71134939.json` | **Major Runtime Disparity** | Run `71134939` started with empty buffer; retrieved 100% timeout episodes from its own run. |
| **Critic Feedback Timing** | `collect.py:263` (Round $\ge 2$) | `push_collect.py:243` (Round $\ge 2$) | **Same** | Injected at round $r \ge 2$, reporting on round $r-1$. |
| **Critic Feedback Arms** | `stage3_critic.py:201-208` (Both arms) | `push_feedback.py:39` (Left arm only) | **Different** | Push reports left arm only. |
| **Critic Feedback Distances** | `prompts.py:361` (EE to target) | `prompts.py:389-390` (Tip-cube & cube-goal) | **Different** | Push reports two scalar lines. |
| **Critic Feedback Verdict Target** | `stage3_critic.py:166` (EE to target) | `push_feedback.py:43, 49` (`cube_to_goal`) | **Major Semantic Bug** | Pre-contact moves receive 100% flat verdicts in Rung-2′, blinding the teacher to approach progress. |

---

## 4. Key Structural Pathologies Identified

1. **Approach Blindness via Critic Verdict:**
   In `push_feedback.py:43`:
   ```python
   parts.append(_p1_verdict(scalars_start_cm[1], scalars_end_cm[1]))
   ```
   `scalars_*_cm[1]` is the `cube_to_goal` distance. Because the cube is stationary before contact, $\Delta = 0$. In run `71134939`, across 597 rounds, **100% of verdict lines before contact were `CRITIC_FEEDBACK_FLAT`**:
   `"Result: No significant progress (still 8.8 cm from target). Try a different direction or larger step size..."`
   Even when the teacher reduced fingertip-to-cube distance (e.g. from 4.9 cm to 4.7 cm), the feedback explicitly instructed it that no progress was made.
2. **Preamble Image Loss on Multi-Turn:**
   In `client.py:146-150`:
   ```python
   for msg in self.messages:
       if msg["role"] == "user" and isinstance(msg["content"], list):
           msg["content"] = [part for part in msg["content"] if part["type"] == "text"]
   ```
   On Round 2, `messages[0]` is stripped of all images. This purges the retrieved past-episode images (`P1`, `P2`, `P3`). The teacher can no longer perform visual feature comparison against past episodes in rounds 2–12.
3. **Empty Initial Buffer and Failure Reinforcement:**
   Because run `71134939` did not mount an existing push recap buffer, episode 5000 had 0 memory hits, episode 5001 had 1 hit (5000 timeout), episode 5002 had 2 hits, and episodes 5003–5049 had 3 hits consisting entirely of failed attempts. The model was continuously prompted with lessons from timeout episodes.

---

## 5. Re-runnable Verification Commands

The assertions in this audit can be independently re-verified using the following commands:

```bash
# 1. Verify that run 71134939 metadata had memory ON, feedback ON, and history ON
python3 -c "import json; d=json.load(open('data/replays/71134939/failure/01b82183-43e.json')); print('history:', d['metadata']['round_history'], 'feedback:', d['metadata']['round_feedback'], 'memory:', d['metadata']['memory_on'])"

# 2. Verify that run 71134939 started with an empty buffer and retrieved 100% failure episodes
python3 -c "import json; d=json.load(open('logs/push_smoke_71134939.json')); print([(ep['env_seed'], len(ep['memory_hits']), [h['outcome'] for h in ep['memory_hits']]) for ep in d['episodes'][:5]])"

# 3. Verify that EpisodeConversation strips all images from prior turns (including preamble) on round 2
python3 -c "from aiongenos.vlm.client import EpisodeConversation; c=EpisodeConversation('SYS'); c.append_user_turn('U1', 'IMG1', preamble_text='P_TXT', preamble_image_base64_list=['P_IMG']); c.append_assistant_turn('A1'); c.append_user_turn('U2', 'IMG2'); print('m0 images:', sum(1 for p in c.messages[0]['content'] if p.get('type')=='image_url'), 'm2 images:', sum(1 for p in c.messages[2]['content'] if p.get('type')=='image_url'))"

# 4. Verify that push feedback verdict evaluates cube_to_goal, giving flat verdict despite fingertip approach
python3 -c "from aiongenos.orchestrator.push_feedback import format_round_feedback; print(format_round_feedback((44,20,53),(44,35,53),(44,20,53),(4.9,8.8),(4.7,8.8)))"
```
