# Founding-Intent Review: Prompt External Review Candidates (C1–C7)

**Reviewer Role:** Founding-Intent Reviewer (mem1)  
**Date:** 2026-10-28  
**Reference Documents:**
- `docs/aiongenos_founding_intent.md` (Precise statement of founding intent & auditability constraint)
- `docs/harness_grant_ledger.md` (Harness Grant Ledger & freeze clause)
- `docs/p2_prereg/prompt_external_review.md` (§4: Candidate prompt changes C1–C7)
- `docs/p2_prereg/wp3a_push_provenance.md` (§ "2026-10-15: rung-2′ interface fix (PI B1/B2) and Rule 10 (PI B5)")
- `docs/p2_prereg/evidence/2026-10-22_rung2p_diag/mem2.md` (Rule 10 field-by-field audit)

---

## 1. Executive Summary & Assessment Matrix

The 7 candidate prompt changes proposed in `docs/p2_prereg/prompt_external_review.md` §4 are evaluated against the core philosophical boundary of AionGenos:
1. **Marginal knowledge (situation-independent)** may be supplied by the harness as an auditable grant entered in the Ledger with an explicit reclamation experiment.
2. **Conditional knowledge (situation $\to$ action mappings)** must be earned through trial and experience; injecting it is strictly forbidden.
3. **Rule 10 (PI, 2026-10-15)**: Field-by-field, prompt-by-prompt equivalence against the P1 baseline must be preserved when replicating conditions.
4. **Ladder Comparability**: The observation ladder ($1 \to 1\text{b} \to 2 \to 3$) must isolate sensory scaffolding without unearned behavioral heuristics smuggled into lower rungs.

### Summary Table

| Candidate | Proposed Change | Founding-Intent Category | Rule 10 Invalidation? | Ladder Comparability Invalidation? | Verdict / Ledger Action |
|:---|:---|:---|:---|:---|:---|
| **C1** | Align identity framing to single-arm push (scope `STAGE1_SYSTEM` or clarify in `instruction`, drop `RIGHT_EE_POS`) | **(a) 介面修正/frame plumbing**（IN，可授予需 Ledger） | **Conditional**: Modifying `STAGE1_SYSTEM` breaks Rule 10 byte-identity; clarifying via `instruction` matches P1 `L0A` and preserves Rule 10. | No | **IN (Conditionally)**: Grant via `instruction` (matching P1), requires Ledger entry for single-arm scoping. |
| **C2** | Lock `preamble_coords="off"`, drop `(similarity=0.9xx)` badge, require conditional visual rules in recaps | **(a) 介面修正** (coords/badge) + **(c) 策略注入** (recap rule) | **Yes** (the recap rule clause breaks P1 reflection parity) | No | **SPLIT**: Coords-off & badge drop are **IN** (Ledger); requiring conditional visual rule in recap is **OUT (c)**. |
| **C3** | Fix Round 2+ stripped-image mismatch: (a) text header fix vs (b) retain $r-1$ image | Option (a): **(a) 介面修正** / **(d) 純工程**<br>Option (b): **(a) 介面修正** | **Option (b) directly INVALIDATES Rule 10** (P1 stripped all prior images); Option (a) preserves Rule 10. | No | **Option (a) ACCEPTED**; **Option (b) REJECTED** on Rule 10. |
| **C4** | Extend `d1` frame line to map base axes to camera image directions | **(a) 介面修正/frame plumbing**（IN，可授予需 Ledger） | No (extends push-specific `d1` grant) | No (preserves cumulative ladder) | **IN**: Marginal sensor frame plumbing, requires Ledger amendment for grant (e). |
| **C5** | Anti-anchoring feedback note at `obs_rung=1`: warn proprioception only + instruct to lower $Z$ below 53 or adjust $XY$ | **(c) 策略注入** + **(b) 揭露條件知識**（when to descend） | **INVALIDATES Rule 10** (P1 feedback had zero heuristic advice) | **INVALIDATES Ladder Comparability** (smuggles descent policy into Rung 1) | **OUT (REJECTED)**: Blatant violation of Founding Intent line 89. |
| **C6** | Structured 2-sentence `THOUGHT` slot: choose $(X,Y)$ behind cube and contact height $Z$ below hover | **(c) 策略注入** + **(b) 揭露條件知識**（approach-behind mapping） | **INVALIDATES Rule 10** (P1 used generic physics reasoning prompt) | **INVALIDATES Ladder Comparability** (hardcodes policy discovery across all rungs) | **OUT (REJECTED)**: Verbatim violation of Founding Intent line 29. |
| **C7** | Preserve Turn-0 assistant or separator when pruning history window in `EpisodeConversation` | **(d) 純工程** | No (fixes chat alternation bug while preserving window invariant) | No | **IN**: Pure engineering fix. |

---

## 2. Detailed Item-by-Item Review

### C1: Align Identity Framing to Single-Arm Push
- **Location:** `aiongenos/vlm/prompts.py` (`STAGE1_SYSTEM`, `_S1_EEF_PUSH`) & `scripts/run_push_collect.py` (`instruction`).
- **Core Proposal:** Eliminate contradictory bimanual framing by removing `RIGHT_EE_POS` from `_S1_EEF_PUSH` (or stating in `instruction` that the right arm is parked and held still), and scoping `STAGE1_SYSTEM` so it does not instruct to "plan the next sub-goal for both arms".
- **Category:** **(a) 介面修正/frame plumbing（IN，可授予需 Ledger）**.
  - *Founding-Intent Grounding:* Embodiment definition (which limbs are active vs. parked) is marginal, situation-independent mechanical common sense. It carries zero information about which action to execute for a specific cube/goal layout.
  - *Ledger Requirement:* Must be logged under the Harness Grant Ledger (analogous to Ledger entry d, which locks the `GRIP` degree of freedom to `CLOSE`). Reclamation condition: P3 multi-task / bi-manual coordination where the system autonomously determines limb assignment.
- **Rule 10 & Ladder Comparability Analysis:**
  - *Rule 10 (P1 Correspondence):* In P1 `L0a_single_reach_left` (`task_instructions.py:18-20`), the instruction explicitly stated:
    > `"Move your LEFT end-effector to the {target_color} target. Your right arm is held still — you do not control it."`
    Crucially, P1 achieved embodiment clarity through the **task instruction**, while keeping `STAGE1_SYSTEM` shared and bimanual across the codebase (`mem2.md` line 75).
    - If C1 modifies `STAGE1_SYSTEM` itself, it creates a field-by-field divergence against P1's `STAGE1_SYSTEM`.
    - If C1 adopts the **instruction-level clarification** (matching `task_instructions.py:18-20`), it **restores Rule 10 compliance** by replicating P1's exact mechanism.
  - *Ladder Comparability:* Preserved across all rungs.

---

### C2: Lock `preamble_coords="off"`, Drop Similarity Badge, and Require Conditional Visual Rules in Recaps
- **Location:** `aiongenos/orchestrator/push_memory.py` (`format_push_preamble_text`, `build_push_recap_system_prompt`).
- **Core Proposal:** 
  1. Default `preamble_coords="off"` (redact raw numerical coordinates from retrieved past episodes).
  2. Drop misleading `(similarity=0.9xx)` badge resulting from fixed standby pose.
  3. Add general anti-copying caveat: *"The cube and green zone are in DIFFERENT positions in every episode; do NOT copy a past direction blindly..."*.
  4. Instruct `build_push_recap_system_prompt` not to cite raw grid coordinates, but instead to write a *"conditional visual rule (how to adjust relative to where the yellow cube and green zone appear in the image)"*.
- **Category:** **Composite: (a) 介面修正/frame plumbing (Items 1–3) + (c) 策略注入 (Item 4)**.
  - *Items 1–3 (IN):* Redacting raw coordinates removes an unintended backdoor for memorized trajectory copying (`(e)` ablation in `wp3a_push_provenance.md`). Dropping the similarity badge eliminates an artifact of the constant standby pose. Adding the anti-copying warning merely states the task instance distribution (marginal). These are interface plumbing.
  - *Item 4 (OUT - 策略注入):* Requiring the recap prompt to enforce that lessons follow a specific semantic recipe (*"write a conditional visual rule: how to adjust relative to where the cube and green zone appear"*) dictates what form the model's reflection must take. Under Founding Intent § "The infant analogy", evolution supplied the reflexes, not the cognitive strategy template. Dictating how the brain structures its lessons is an injection of strategic scaffolding.
- **Rule 10 & Ladder Comparability Analysis:**
  - *Rule 10:* P1 recap prompts (`aiongenos/memory/recap.py`) did not prescribe conditional visual structures. Imposing Item 4 on push creates an asymmetric cognitive scaffold absent in P1, violating Rule 10 comparability.
  - *Ladder Comparability:* Preserved, but artificially enriches the cross-episode memory channel.
  - *Recommendation:* Approve Items 1–3 under (a); strike Item 4 as (c) 策略注入.

---

### C3: Fix Round 2+ Stripped-Image Preamble Mismatch
- **Location:** `aiongenos/orchestrator/push_memory.py` & `aiongenos/vlm/client.py` (`EpisodeConversation`).
- **Core Proposal:**
  - **Option (a):** Clean up the Turn-0 text header on Round 2+ (*"PAST EPISODE LESSONS (images shown on Round 1 only)"* and remove dangling `"Image i: ..."` pointers).
  - **Option (b):** Retain the previous round's scene image ($r-1$) in `EpisodeConversation` so Round $r$ can visually diff frame $r-1$ vs. frame $r$.
- **Category:**
  - Option (a): **(a) 介面修正/frame plumbing** / **(d) 純工程** (removes false dangling references).
  - Option (b): **(a) 介面修正/frame plumbing** (modifies sensory history interface).
- **Rule 10 & Ladder Comparability Analysis:**
  - **CRITICAL: Option (b) directly INVALIDATES Rule 10 (P1 條件逐欄可比)!**
    - In P1 L0a, `client.py:146-150` stripped all `image_url` parts from all prior user turns upon appending a new turn (`mem2.md` line 50: *"Older turns in messages become purely text"*).
    - If push retains the $r-1$ image in-context, push receives an inter-round visual differential that was strictly absent in P1 L0a. This introduces a major sensory disparity, invalidating P1-vs-push field-by-field comparability.
    - Conversely, **Option (a) preserves Rule 10** by aligning the text prompt with the actual stripping behavior without altering sensory inputs.
  - *Ladder Comparability:* Neither option alters observation ladder definitions.
  - *Recommendation:* Select Option (a); reject Option (b).

---

### C4: Extend `d1` Frame Line to Map Base Axes to Camera Image Directions
- **Location:** `aiongenos/vlm/prompts.py` (`format_frame_convention_line`, `TOP_VIEW_SENTENCE`).
- **Core Proposal:** Extend the runtime `d1` frame line to specify camera projection geometry (e.g., front camera view axis mapping, and top camera view: `UP in image = +X (forward), LEFT in image = +Y (robot's left)`).
- **Category:** **(a) 介面修正/frame plumbing（IN，可授予需 Ledger）**.
  - *Founding-Intent Grounding:* Extrinsic camera mounting angles and optical projections are situation-independent marginal coordinate conventions. Founding Intent § "What this rules in and out" explicitly states: `"IN: frame conventions and coordinate plumbing"`.
  - *Ledger Requirement:* Harness Grant Ledger entry (e) granted base-frame directions with the explicit restriction: *"No object, goal or table position, no image→axis mapping, no strategy"*. Expanding `d1` to include camera image projection requires an **amendment to Ledger entry (e)** (or a new entry (f)).
  - *Reclamation Condition:* In P3, remove the image-to-axis mapping prompt line and require the policy to infer camera-to-base projection autonomously from closed-loop motion feedback.
- **Rule 10 & Ladder Comparability Analysis:**
  - *Rule 10:* P1 did not have `d1`. `d1` is an accepted marginal grant added in push. Extending it does not violate Rule 10 beyond the existing Ledger grant.
  - *Ladder Comparability:* Preserved. Camera coordinate mapping is gated with the sensor (top-view axis mapping only appears at `obs_rung >= 1b` when `scene.camera_top` is present). It discloses zero object coordinates or distance scalars.

---

### C5: Anti-Anchoring Feedback Note at `obs_rung=1`
- **Location:** `aiongenos/orchestrator/push_feedback.py` (`format_round_feedback`) & `aiongenos/vlm/prompts.py` (`_S1_EEF_PUSH`).
- **Core Proposal:** Add a note to Round $\ge 2$ critic feedback at `obs_rung < 2` clarifying that `Actual movement` is TCP proprioception only, and adding:
  > *"and if the cube did not move, it must adjust height (Z, lowering below the Z=53 standby hover) or (X, Y) alignment rather than repeating the same Z."*
- **Category:** **(c) 策略注入（OUT）** and **(b) 揭露條件知識（OUT）**.
  - *Founding-Intent Grounding:*
    Founding Intent § "What this rules in and out" explicitly states:
    > `"- OUT (must be earned, conditional): which object to act on; when to descend / approach / push; contact-force targets; the parameters that tune a primitive to a specific situation; any situation→action mapping."`
    Telling the agent *"if the cube did not move, adjust height (Z, lowering below Z=53)"* is an overt injection of:
    1. **When to descend** (explicitly OUT);
    2. A conditional **situation $\to$ action mapping** (stationary cube $\to$ lower $Z$ or adjust $XY$).
- **Rule 10 & Ladder Comparability Analysis:**
  - **INVALIDATES Rule 10:** In P1 L0a, the diagnostic feedback block consisted solely of target, actual movement, distance, and the dead-band progress verdict (`mem2.md` lines 58–68). P1 never included heuristic advisory sentences instructing the agent how to adjust its degrees of freedom.
  - **INVALIDATES Ladder Comparability:** `obs_rung=1` is pre-registered as **IMAGE + PROPRIOCEPTION ONLY** with zero scalar distance oracles and zero verdict lines (`push_feedback.py:15`). Injecting an action-correction rule into Rung-1 feedback converts Rung 1 into an oracle-guided heuristic mode, destroying the ladder's ability to measure whether unassisted vision is sufficient.
  - *Verdict:* **REJECTED (OUT)**.

---

### C6: Structured 2-Sentence `THOUGHT` Slot (Observation $\to$ 3D Adjustment)
- **Location:** `aiongenos/vlm/prompts.py` (`_S1_EEF_PUSH`).
- **Core Proposal:** Replace generic `THOUGHT: <one paragraph physics reasoning>` with:
  > `THOUGHT: <1 sentence stating where the yellow cube and green zone are relative to the fingertip in the image, then 1 sentence choosing (X, Y) behind the cube and a contact height Z below the standby hover>`
- **Category:** **(c) 策略注入（OUT）** and **(b) 揭露條件知識（OUT）**.
  - *Founding-Intent Grounding:*
    Founding Intent lines 29–34 define the inviolable core commitment:
    > `Conditional knowledge — every mapping of the form situation → action ("this cube here → push from behind along that vector", "this contact state → this force") — must be acquired through experience. It may not be injected.`
    The founding intent document literally cites **`"push from behind along that vector"`** as the exact definition of forbidden conditional knowledge!
    Furthermore, Ledger entry (b) records that approach-behind was explicitly **WITHDRAWN** by the PI because approach geometry belongs to the brain to learn. C6 smuggles approach-behind back into the prompt.
- **Rule 10 & Ladder Comparability Analysis:**
  - **INVALIDATES Rule 10:** P1 used the unguided prompt `- Reason step-by-step about the physics before giving targets` (`prompts.py:47`). Mandating an operational push recipe destroys field-by-field comparability.
  - **INVALIDATES Ladder Comparability:** By hardcoding the kinematic solution directly into the reasoning schema, C6 masks whether different observation rungs actually enable autonomous discovery.
  - *Verdict:* **REJECTED (OUT)**.

---

### C7: Preserve Turn-0 Assistant or Separator When Pruning History Window
- **Location:** `aiongenos/vlm/client.py` (`EpisodeConversation._prune_to_window`).
- **Core Proposal:** When `len(self.messages) > 2 * recent_window + 1`, retain `self.messages[:2]` (Turn-0 user + assistant) before `tail` or re-inject headers cleanly, preventing two consecutive `"role": "user"` turns (`messages[0]` followed by `tail[0]`) from appearing at Round 8+.
- **Category:** **(d) 純工程**.
  - *Founding-Intent Grounding:* Modifies neither prompt semantics, sensory observations, nor action choices. It fixes an off-by-one window concatenation flaw in multi-turn conversation data structures to satisfy LLM API schema invariants (`user` $\leftrightarrow$ `assistant` alternation).
- **Rule 10 & Ladder Comparability Analysis:**
  - *Rule 10:* P1 shared `EpisodeConversation` in `client.py`. Correcting this malformed chat alternation preserves the intended First Turn + Last 6 Pairs contract without modifying prompt content.
  - *Ladder Comparability:* Completely unaffected.
  - *Verdict:* **APPROVED (IN)** as pure engineering maintenance.

---

## 3. Reviewer Synthesis & Recommendation to the PI

1. **Permissible for Immediate Adoption (Pre-Gen-0):**
   - **C7** (Pure engineering fix for conversation pruning).
   - **C1 via Instruction Option** (Align embodiment framing by stating right arm is parked in task instruction, matching P1 `L0A` and preserving Rule 10; requires Ledger entry).
   - **C3 Option (a)** (Fix dangling text pointer on stripped Round 2+ preamble).
   - **C2 Items 1–3 only** (Lock `coords="off"`, drop deceptive `0.98x` similarity badge, add distribution warning; requires Ledger entry).

2. **Permissible via New Harness Grant Ledger Entry:**
   - **C4** (Camera image-to-base projection mapping). Valid marginal coordinate plumbing, but requires amending Ledger entry (e) with an explicit P3 reclamation experiment.

3. **Strictly Prohibited by Founding Intent & Comparability Rules:**
   - **C5** (Injects descent timing and heuristic action rules into feedback; invalidates Rule 10 and Rung-1 ladder comparability).
   - **C6** (Injects approach-behind and descent strategy into `THOUGHT`; verbatim violation of Founding Intent line 29; invalidates Rule 10 and ladder comparability).
   - **C3 Option (b)** (Retaining $r-1$ image invalidates Rule 10 against P1 L0a).
   - **C2 Item 4** (Prescribing conditional visual rules in recap prompt constitutes strategy injection into memory reflection).
