# Related Work Verification: Anthropic "Claude Plays Robotics"

## Bibliographic Metadata (Verified by Fetch)
- **Title**: Claude plays robotics
- **Authors**: Shmuel Berman, Michael Ilie, Jia Deng, Daniel Freeman
- **Venue**: Anthropic Research Blog (Frontier Red Team)
- **Publication Date**: July 9, 2026
- **Source URL**: https://www.anthropic.com/research/claude-plays-robotics

---

## Verification of Lead's Summary Points (i)–(ix)

### Point (i)
- **Lead Summary Statement**: LIBERO direct 7-D EEF control: Mythos Preview 5.5%, most frontier models 0%.
- **Original Heading(s)**:
  - `Summary of findings`
  - `Direct control is bad, but improving` > `Low-level manipulation`
- **Original Sentence(s)**:
  - Under `Summary of findings`: "With low-level manipulation methods, models are beginning to produce useful local physical behavior, even though full task success remains rare. Newer models are better at reaching objects, making contact, and grasping. However, they only complete the full task a small percentage of the time (from 0 to 5.5%)."
  - Under `Direct control is bad, but improving` > `Low-level manipulation`: "We evaluate this capability using a fixed-base, 7-DoF Franka Panda arm in kitchen-style environments adapted from the LIBERO benchmark." and "We test a simplified direct-control setting in which the model outputs standard seven-dimensional end-effector motion commands."
  - Figure Caption & Description (`LIBERO direct-manipulation success rates.`): "Two bar graphs (the second with performance intervals) showing various AI models' success on LIBERO with direct control. Mythos Preview has the highest success rate, at 5.5; many AI models have a success rate of 0."
- **Status**: CONFIRMED
- **Comparison**:
  - **Them**: Direct 7-D EEF control on a fixed-base 7-DoF Franka Panda arm across LIBERO benchmark tasks; Mythos Preview reaches a 5.5% success rate while many frontier models achieve 0%.
  - **Us (AionGenos)**: Evaluates single-arm Operational Space Control (OSC) targeting waypoint end-effector poses on a table push task; without demonstrations or marginal frame grants, initial direct VLM control yielded 0/50, reaching 11/50 under d1+d2 marginal grants on Pin-4b and 13/50 under lesson-only memory on Pin-4c.
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "Pin 3 — controller choice (Q1 companion rule)", § "2026-10-19 — rung-2′ pilot (full P1 feedback condition), memory ON, 50 ep (run 71134939, seeds 5000–5049)", § "2026-10-27 — rung-1′ on Pin-4c, and the (e) two-arm result (memory transmits paths)"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 1 "Is 0/50 real, or a tooling artifact?".

---

### Point (ii)
- **Lead Summary Statement**: "the model never receives object coordinates".
- **Original Heading(s)**: `Direct control is bad, but improving` > `Low-level manipulation`
- **Original Sentence(s)**:
  - "It is never given the objects’ coordinates directly, so it must first identify the relevant objects from vision and then use that information to decide how the hand should move next."
- **Status**: DIFFERENT
  - *Correct Version*: The original text states: "It is never given the objects’ coordinates directly, so it must first identify the relevant objects from vision and then use that information to decide how the hand should move next." (The Lead's quoted text `"the model never receives object coordinates"` is a non-verbatim paraphrase).
- **Comparison**:
  - **Them**: In direct-control manipulation, object coordinates are never supplied directly, requiring the model to infer object positions from visual camera frames and gripper force sensors.
  - **Us (AionGenos)**: In rung-1 and rung-2 push evaluations, absolute object coordinates are strictly withheld from prompt observations (only images in rung 1, and scalar distances in rung 2); in the (e) lesson-only configuration, coordinates are explicitly scrubbed from cross-episode preamble buffers (`--preamble_coords off`) to enforce visual-semantic grounding without coordinate leakage.
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "2026-10-05 (17:05) — observation interface returned to design (PI ruling)", § "2026-10-27 — rung-1′ on Pin-4c, and the (e) two-arm result (memory transmits paths)"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 3 "Macro reading".

---

### Point (iii)
- **Lead Summary Statement**: visual aids: gripper-camera cursor raises Mythos 10-task manipulation SR 6%→32%; compass improves all locomotion configs.
- **Original Heading(s)**: `What’s the bottleneck?` > `Is visual perception the bottleneck?` (and `Appendix` > `Vision tools`)
- **Original Sentence(s)**:
  - "The cursor tool, by contrast, gives every model a large uplift on manipulation—for Mythos Preview, success on the 10-task subset goes from 6% to 32%."
  - "The compass does the same for locomotion, lifting every configuration we tested. In both cases the results suggest that models mainly need better orientation, not a different view of the scene: it is still more helpful to tell the model which way it is facing than to show it a picture of itself."
  - Under `Appendix` > `Vision tools`: "For manipulation, we test a 2D crosshair projected onto the camera image at the gripper’s location..."
- **Status**: CONFIRMED
- **Comparison**:
  - **Them**: Visual orientation aids overlaid onto input frames (a 2D cursor crosshair at the gripper location for manipulation and a compass for locomotion) provide significant performance uplifts (Mythos Preview manipulation 6%→32%; compass lifts all locomotion configs), indicating models primarily bottleneck on orientation rather than scene perception.
  - **Us (AionGenos)**: Tested front camera, top-down camera (rung-1b), and multi-view setups; identified that spatial disorientation stemmed from unobservable vertical depth and missing axis conventions (prompt lacked ±X/±Y orientation and unit scale, leading 83% of rounds to confuse vertical floors with planar error), resolving this via d1 prompt axis conventions and d2 scalar feedback rather than image-space overlay crosshairs.
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "2026-10-07 — pilot step (c), rung-1b (top-down view), memory ON, 50 ep (run 30f15f0c, seeds 5000–5049)", § "2026-10-22 — PI ruling after the rung-2′ diagnosis: d1 + d2, the ladder re-run, rejected options"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 2 "The interface defects behind 0/50" (Defects 2 & 3) & § 4 "Gemini 4 Argon: what it does and what it means for us".

---

### Point (iv)
- **Lead Summary Statement**: "much of the improvement comes from a better ability to adapt after seeing prior outcomes".
- **Original Heading(s)**: `Simple settings`
- **Original Sentence(s)**:
  - "Our results suggest that much of the improvement comes from a better ability to adapt after seeing prior outcomes and to revise strategy accordingly. On tasks with a natural termination point (most notably TwinFlipper and Pendulum), average first-try performance is quite similar across models, and Claude Opus 4 and Opus 4.1 very slightly outperform later models on this measure. The larger gains appear in subsequent attempts, where newer models improve much more substantially."
- **Status**: CONFIRMED
- **Comparison**:
  - **Them**: In simple control environments, performance divergence between model generations is driven by iterative adaptation across attempts after observing outcomes rather than initial first-attempt capabilities.
  - **Us (AionGenos)**: In multi-round push episodes, within-episode critic feedback (`round_feedback` reporting target, actual movement, and progress verdict) is required for multi-round strategy revision; without history and feedback, rounds operate statelessly as random walks (51% sign flips on Δy, increasing distance).
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "2026-10-15: root cause missed so far — push rounds are STATELESS within an episode", § "2026-10-15: rung-2′ interface fix (PI B1/B2) and Rule 10 (PI B5)"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 2.4 "History locks the height".

---

### Point (v)
- **Lead Summary Statement**: context-truncation (keep first 10 turns + recent N): most models barely degrade → "models rely much more on the recent past than on a broad accumulated understanding".
- **Original Heading(s)**: `What’s the bottleneck?` > `Can they learn from experience?`
- **Original Sentence(s)**:
  - "In these truncation runs we always retain the first 10 turns plus the most recent N turns. Dropping the first turn caused models to forget basic conventions and loop, so we keep it in all conditions."
  - "If performance depended on a detailed memory of the full episode, this should have caused a large drop. In most cases, it did not. In some cases, performance even improved. This indicates that the models rely much more on the recent past than on a broad accumulated understanding of everything that happened earlier."
- **Status**: CONFIRMED
- **Comparison**:
  - **Them**: Evaluates within-episode context truncation retaining the first 10 turns plus the most recent N turns; finds minimal degradation across models (and improved performance for weaker models by mitigating context rot), demonstrating primary dependence on recent local context.
  - **Us (AionGenos)**: Implements conversation truncation in `EpisodeConversation` retaining turn 0 (system prompt and cross-episode preamble) plus the last 6 turn pairs, stripping past images from round 2 onward; observed that history retention introduces within-episode height-locking (e.g. round-2 Z=53 locked in 45/50 episodes).
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "2026-10-15: rung-2′ interface fix (PI B1/B2) and Rule 10 (PI B5)" (Table of P1 L0 vs push rung-2′); [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 1a "What the memory actually contains (answer to the PI)" & § 2.4 "History locks the height".

---

### Point (vi)
- **Lead Summary Statement**: "Without pausing, current API models would fail for a trivial reason" (simulator paused for inference).
- **Original Heading(s)**: `Latency`
- **Original Sentence(s)**:
  - "For direct-control and code-control simulations, we paused the simulator while the model produced its next action. Without pausing, current API models would fail for a trivial reason: they act far too slowly for a physics loop running at 10–125 Hz. Pausing lets us measure what the model could do if inference were faster, rather than only measuring today’s API latency."
- **Status**: CONFIRMED
- **Comparison**:
  - **Them**: Simulation steps are paused during API queries for direct and code control evaluations to decouple model reasoning capability from API network latency and physics update rate constraints (10–125 Hz).
  - **Us (AionGenos)**: The Isaac Gym/Lab collection pipeline executes in turn-based step-and-wait fashion: the simulation environment halts physics while querying the VLM teacher for waypoint coordinates, then unpauses to let the low-level OSC controller execute trajectories over discrete simulation timesteps.
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "Pin 3 — controller choice (Q1 companion rule)", § "Completion chain (order fixed)", § "2026-10-19 — rung-2′ pilot (full P1 feedback condition), memory ON, 50 ep (run 71134939, seeds 5000–5049)"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 1 "Is 0/50 real, or a tooling artifact?".

---

### Point (vii)
- **Lead Summary Statement**: no cross-episode memory / cumulative learning claims; oneshot_course few-shot practice "on harder courses, practice does not help".
- **Original Heading(s)**: `What’s the bottleneck?` > `Can they learn from experience?`
- **Original Sentence(s)**:
  - "On harder, longer courses, practice does not help. On those trials, neither Mythos Preview nor Opus 4.7 completes a single trial even with twenty practice runs. The models are learning a specific sequence and are not yet general planners."
  - (Context: Evaluations focus on within-trial interaction or in-context few-shot repeats on the identical course layout; no persistent cross-episode memory database or cumulative multi-episode learning is implemented or claimed).
- **Status**: DIFFERENT
  - *Correct Version*: The original text reads: "On harder, longer courses, practice does not help." (The Lead's quote omitted the word ", longer").
- **Comparison**:
  - **Them**: Tests short-horizon within-trial retries and in-context few-shot practice on identical course environments, finding that on harder, longer courses practice does not help (0 completions across 20 practice runs), with no external cross-episode memory or cumulative repository.
  - **Us (AionGenos)**: Implements persistent cross-episode episodic memory across 50 to 300 continuous episodes, storing episodic recaps in a memory buffer and retrieving top-k past experiences into turn 0 to evaluate whether memory accumulates over time across varying task seeds.
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "2026-10-27 — rung-1′ on Pin-4c, and the (e) two-arm result (memory transmits paths)", § "2026-10-28 — PRE-REGISTERED before data: memory time-axis pilot (long life)"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 1a "What the memory actually contains (answer to the PI)" & § 3 "Macro reading".

---

### Point (viii)
- **Lead Summary Statement**: supervised VLA (MolmoAct): on LIBERO-40 every frontier model worse than the VLA alone; wins only on 3 new tasks.
- **Original Heading(s)**: `Tools bridge some of the gap` > `High-level manipulation`
- **Original Sentence(s)**:
  - "We note that every tested model still performs substantially worse than MolmoAct does on its own. Counterintuitively, the penalty is not smallest for the strongest model: Claude Mythos Preview underperforms Opus 4.5 and Opus 4.6 here, because it overrides the VLA more often than is warranted, trusting its own judgment in cases where simply deferring would have succeeded."
  - "Across the standard LIBERO-40, no model beats MolmoAct alone—adding an LLM supervisor currently acts as a tax on a good policy."
  - "To evaluate this, we tested whether these systems can use, and potentially correct, an unreliable VLA. To do so, we created three new LIBERO-like tasks drawn from the original LIBERO-goal scenes but not included in the benchmark; in our baseline trials, MolmoAct is unable to complete any of the three tasks."
  - "Even so, Claude Opus 4.5 and Opus 4.6, along with Gemini 3.1, outperform MolmoAct alone."
  - (Takeaway): "Supervising the policy still costs some performance—the combined system does worse than the VLA running on its own—but the best supervisors now close most of the gap. That does not mean supervision is useless: earlier models destroy most of the policy's value, the best of current models recover most of it, and on tasks the VLA cannot do alone the strongest models already provide net uplift."
- **Status**: CONFIRMED
- **Comparison**:
  - **Them**: Explores pairing frontier LLMs as supervisors over a pretrained VLA policy (MolmoAct); on standard LIBERO-40 tasks, every LLM supervisor lowers performance compared to the standalone VLA, providing net uplift only on 3 novel tasks where baseline MolmoAct scored 0%.
  - **Us (AionGenos)**: Deploys a hierarchical structure without an external pretrained VLA, using a VLM teacher to output waypoint targets to deterministic OSC motion primitives, and distilling teacher trajectories into student policies.
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "Approach-behind ownership (pinned) — primitive-level, not teacher output", § "2026-10-22 — PI ruling after the rung-2′ diagnosis: d1 + d2, the ladder re-run, rejected options"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 4 "Gemini 4 Argon: what it does and what it means for us" & § 5 "Multi-view teacher → single-view student".

---

### Point (ix)
- **Lead Summary Statement**: limits: "cannot control humanoid robots without a pretrained policy", "fail at tasks that require stable spatial memory".
- **Original Heading(s)**:
  - Introductory section (before `Chapter 01`)
  - `Summary of findings`
- **Original Sentence(s)**:
  - In introductory section (paragraph 4): "Today’s frontier models cannot control humanoid robots without a pretrained policy, but newer models have made real gains in direct manipulation and high-level policy control across the humanoid and quadruped embodiments we tested."
  - Under `Summary of findings`: "However, models still fail at tasks that require stable spatial memory, self-localization, or long open-loop plans."
- **Status**: CONFIRMED
- **Comparison**:
  - **Them**: Cites explicit architectural limits of current frontier models: inability to control high-DoF humanoid dynamics directly without pretrained policies, and failure on tasks demanding stable spatial memory, self-localization, or open-loop planning.
  - **Us (AionGenos)**: Formulates manipulation on a fixed-base tabletop manipulator with low-level OSC to isolate dynamics from reasoning; addresses spatial estimation limits by structuring frame conventions (d1) and offloads temporal spatial memory across episodes to external episodic memory retrieval.
  - **Provenance Path**: [wp3a_push_provenance.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_push_provenance.md) § "Task identity", § "Pin 3 — controller choice (Q1 companion rule)", § "2026-10-27 — Pin-4c geometry fixed at ±75°, cube X [0.40, 0.46] × Y [−0.02, 0.10]; blind sweep 5/50 (qualifies)"; [wp3a_rung2p_diagnosis_2026-10-22.md](file:///home/control/AionGenos/docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md) § 2 "The interface defects behind 0/50" & § 3 "Macro reading".

---

## Summary Counts

- **CONFIRMED**: 7 (points i, iii, iv, v, vi, viii, ix)
- **DIFFERENT**: 2 (points ii, vii)
- **NOT FOUND**: 0

---
**Lead acceptance note (isaac, 2026-10-28):** five quotes spot-checked by the lead's own fetch (6%→32%; "rely much more on the recent past…"; "retain the first 10 turns…"; "practice does not help"; "Without pausing…"). All are verbatim.
- §0 corrections: (ii) reads "It is never given the objects' coordinates directly…"; (vii) reads "On harder, longer courses, practice does not help."
- The article's "practice" means repeats of the same course. It reports no memory that persists across different episodes or seeds.
