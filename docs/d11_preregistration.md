# D11 Pre-Registration — Frozen Before Any Adapter Trains

**Purpose**: Freeze all hypotheses, primary/secondary metrics, and comparison
arms BEFORE any D11 adapter starts training. This closes the "we peeked at
the results then chose which comparisons to report" attack surface.

**Date frozen**: 2026-07-06
**Signed off by**: TPEmist (via chat approval of this document)
**Frozen artifact**: This file, plus its git commit SHA (referenced below).

## 1. Primary claim being tested

> **"Retrieved-memory content is baked into LoRA weights — the memory-augmented
> teacher's behavior transfers to a memoryless student LoRA at a level a
> memoryless-teacher-trained control student cannot reach."**

Falsifiable predictions:
- (P1) Student trained on memory-teacher trajectories with rationale-prefix
      target beats student trained on memoryless-teacher trajectories
      (both evaluated with zero retrieval at inference).
- (P2) Student(memory-taught) R1 ΔX bias resembles memory-teacher's terminal
      quartile (~-16 cm) more than D6's -23.5 cm.
- (P3) Student(memory-taught, no retrieval) achieves ≥ 0.7 × memory-teacher SR
      without inference-time retrieval or scaffolding.

## 2. Frozen comparison arms

All arms evaluated identically: L0a-Left, 100 ep, `--freeze_level`, current
prompt code (Fix 1/3 active), no `--use_memory`, no `--recap_buffer_root`.
Only the student adapter differs.

| Arm | Adapter | Training data | Retrieval at inference | Purpose |
|---|---|---|---|---|
| **A_ctrl** | v4-ctrl (SFT only) | D6 (n=158 progress rounds), **no rationale prefix** | none | Falsifies "any distillation works" — trained on memoryless teacher |
| **A_ctrl_rat** | v4-ctrl-rat (SFT only) | D6 (n=158) with **fresh-retrieval rationale** synthesized from current buffer | none | Falsifies "rationale text alone drives it" (controls for prompt-length effect) |
| **B_main** | v4-sft-A + v4-kto-B (composable C.3-B) | v4_sft_A (n=992) + v4_kto_B (n=2802), **historical retrieval rationale** | none | Headline D11 arm |
| **C_retrieval** | v4-sft-A + v4-kto-B (same as B) | same as B | **memory retrieval ACTIVE at inference** | Tests whether inference-time retrieval still helps or is redundant |

**A_ctrl** vs **B_main** is the direct "memory in weights" test — same
distillation recipe, same student architecture, only difference is whether
the source teacher had memory context. If B >> A_ctrl, memory content
transferred.

**A_ctrl_rat** is the tighter control: same rationale-token count, but the
rationale is post-hoc synthesized against a memoryless-teacher trajectory.
If B > A_ctrl_rat by a similar margin as A_ctrl, we can attribute the gain
to the *specific* retrieved-past-lesson content, not just the presence of
a THOUGHT block.

**C_retrieval** tests whether baked-in memory can *replace* retrieval or
merely *supplement* it.

## 3. Primary metric

**Cumulative success rate over 100 ep, L0a-Left, freeze_level, no memory
at inference (unless noted)**.

Wilson 95% CI reported for all arms.

## 4. Frozen pairwise tests (all two-proportion z, α=0.05, two-sided)

- **T1 (primary)**: B_main vs A_ctrl.
  Rejection region: B_main SR − A_ctrl SR > +10pp AND z > 1.96.
  Effect size interpretation: SR pooled effect size (Cohen's h).
- **T2 (tighter control)**: B_main vs A_ctrl_rat. Same rejection rule.
- **T3 (transfer floor)**: B_main SR ≥ 0.7 × pooled memory-teacher SR
  (0.7 × 51.7% = 36.2%).
- **T4 (bake-in adequacy)**: C_retrieval vs B_main.
  If C_retrieval − B_main ≤ +5pp AND not statistically significant, we
  claim "baking-in replaces retrieval". If > +5pp, we honestly report
  "baking-in captures most but not all of retrieval's benefit".

## 5. Behavioural R1-ΔX probe (secondary, mandatory reporting)

For every arm run, compute the mean R1 target ΔX = R1_target_X − init_L_EE_X
across all 100 episodes. This is the "grounding vs prosthetic" probe.

**Reference values (already measured)**:
- D6 memoryless teacher: **−23.5 cm** (baseline behavioral fingerprint)
- Memory-teacher last quartile (D10 ep 76-100): **−15.8 cm** (memory-shifted)

**Frozen prediction (P2)**: Student(B_main) R1 ΔX will be closer to −16 cm
than to −24 cm (i.e., |ΔX_student − ΔX_mem_teacher| < |ΔX_student − ΔX_D6|).

**Reporting rule**: This probe MUST be reported for A_ctrl, A_ctrl_rat,
B_main, C_retrieval — no cherry-picking a subset. Table format:

| Arm | R1 ΔX μ | R1 ΔX σ | Δ from D6 (−23.5) | Δ from mem-teacher (−15.8) |

## 6. Rationale-quality filter (raised from checklist to hard gate)

**Concern**: KTO desirable/undesirable is labeled by episode outcome, not
by rationale-content quality. A trajectory that succeeded despite wrong
reasoning ("correct result, wrong reason") still lands in desirable, and
its rationale prefix gets baked in.

**Mitigation applied BEFORE step 5 (SFT training)**:
Run a teacher self-audit over `data/training_sets/v4_sft_A.jsonl` and
`v4_kto_B.jsonl`. For each sample, ask the teacher to grade its rationale
prefix on 4 dimensions (1-5 scale):
  - **Groundedness**: Does the rationale reference specific, checkable
    facts (init pose, image regions, past outcomes)?
  - **Direction consistency**: Does the rationale describe a direction that
    ends up matching the action's ΔEE vector?
  - **Non-boilerplate**: Does it say something specific to this scene, or
    is it generic filler?
  - **No leakage**: Does it avoid mentioning ground-truth cube coordinates?

Reject samples scoring ≤2 on any dimension. Report:
  - # dropped per dimension
  - Pre-filter and post-filter dataset sizes
  - Optional: histogram of per-sample composite score

Filter cost: 992 + 2802 = 3794 teacher calls at ~15s each = ~16 hr of
teacher time. Worth it because otherwise "rationale-quality drift" is a
reviewer weapon.

**Fallback if filter reveals <60% of samples pass**: pause D11, discuss
whether to lower the threshold or invest in better recap-generation
prompts, rather than train on noise.

## 7. Additional secondary metrics (reported but not primary)

- Avg rounds per episode
- Avg best active-arm distance (cm)
- Premature-STOP count
- Latency per round (student inference)
- Token count generated at inference (rationale-suppression check —
  should be low if action-only decoding works)

## 8. Anti-cherry-picking commitments

- All 4 arms **must** be reported with n=100 each. No dropping arms if
  results are unfavorable.
- If any arm produces <70 valid episodes (teacher/student crash mid-run),
  we relaunch to fill, we do not truncate.
- Wilson CIs, not standard error bars.
- Bonferroni correction is applied for the 4 primary tests (T1-T4):
  effective α = 0.0125 per test.

## 9. What we do NOT get to change post-hoc

- The Fix 1/3 code as of commit `40ac761`. If we discover a bug in
  scaffolding after D11 begins, we do not retroactively "fix" and rerun.
- The Wilson CI + z-test method.
- The 0.7× transfer floor threshold in P3.
- The R1 ΔX probe formula.
- The rationale-quality filter thresholds (≤2 = drop).

## 10. Execution order (revised)

1. **NOW** — commit this pre-registration to git.
2. Rationale-quality filter over v4_sft_A + v4_kto_B (~16h teacher time,
   run in background).
3. Prepare arm-A_ctrl training data (D6 progress rounds, no rationale).
4. Prepare arm-A_ctrl_rat training data (D6 progress rounds + fresh
   retrieval-lookalike rationale from current buffer).
5. Server-side: train A_ctrl, A_ctrl_rat, B_main sequentially.
   Skip retraining if filter drops <40% of samples.
6. Export all three adapters to GGUF.
7. **D11 collect** (100 ep each × 4 arms = ~20 hr):
   - D11-Actrl: base + v4-ctrl adapter
   - D11-Actrl-rat: base + v4-ctrl-rat adapter
   - D11-Bmain: base + v4-sft-A + v4-kto-B (both, composable)
   - D11-Cretrieval: same adapters as B_main + `--use_memory`
8. Analysis: T1-T4 + R1 ΔX probe table + secondary metrics.

## 11. Git anchor

Pre-registration frozen at:
- File: `docs/d11_preregistration.md`
- Commit SHA: **`069586b`**
- Any subsequent modification requires a signed amendment section
  appended below (never overwrite section 1-10).

## 12. Amendment log

### Amendment 2 — 2026-07-06 (still before any adapter trains)

**Rationale-quality filter downgraded from 12h LLM audit to deterministic
3-rule filter + blinded human audit for validation.**

Reasons for change:
- LLM self-audit has known **self-preference bias** — same model grading
  its own output systematically over-rates.
- External LLM judge introduces its own validity defense as a paper
  liability, not just cost.
- Deterministic rules are pre-registerable in a way LLM prompts aren't
  (grading-prompt wording sensitivity + threshold arbitrariness both
  vanish under deterministic rules).

**Three deterministic filter rules** (applied symmetrically to every arm
with rationale — B_main gist, A_ctrl_rat's D6 native thought, and B_matched):

**Rule 1 — Direction consistency**
For each of X, Y, Z axes:
  1. Parse spatial claim from rationale text: extract phrases like
     "move in negative X", "increase Y", "shift left", "closer forward",
     etc. Map to sign of intended ΔEE on that axis.
  2. Compute observed ΔEE on that axis (predicted target − init pose).
  3. Apply **dead-band** = `CRITIC_PROGRESS_DEAD_BAND_CM = 1.0 cm`
     (reused from stage3_critic — no new hyperparam). Axes with
     |ΔEE| < dead-band produce no direction judgment (noise floor).
  4. If any axis has a stated direction AND |ΔEE| ≥ dead-band on that
     axis AND signs disagree → sample rejected as "direction inconsistent".

**Rule 2 — GT geometric consistency**
The replay schema stores ground-truth cube positions (available in
trajectory[t].distances plus the goal_pose extractable from the scene).
Using GT for offline curation is legal — the observable-only invariant
governs model inputs, not data-curation oracles. Student never sees GT.
  1. For every parseable directional claim about the cube ("cube is to
     the left of EE", "cube is further forward"), compute the same
     claim from GT.
  2. If the rationale's claimed sign disagrees with the GT-derived sign
     on any axis where the claim was parseable → sample rejected as
     "spatial claim contradicts geometry".

**Rule 3 — Vacuity check**
The rationale MUST contain at least one parseable spatial token from
one of these categories:
  - An axis name mentioned with sign or direction: `X`, `Y`, `Z`,
    `left`, `right`, `forward`, `back`, `up`, `down`
  - A distance value with a unit: e.g. `5 cm`, `10cm`, `20 grid units`
  - A named landmark with a directional preposition: `left of the
    cube`, `above the target`

If a rationale contains none of these, it's boilerplate ("be careful
and precise", "trust the visual cues") → rejected as "vacuous".

**Reporting requirements** (mandatory in paper):
  - Drop rate per rule per arm, side-by-side.
  - If B_main and A_ctrl_rat differ substantially in drop rate, that
    itself is an observation worth reporting (memory-derived rationale
    might be higher-quality on average — informative regardless of
    which direction).

**Scope narrowing**: Rule filter applied to the ~992 desirable (SFT)
samples first. KTO undesirable samples (~1810) are directionally
harmless if noisy — they teach the model what "bad" looks like, and
noise in that pool degrades gracefully. Filter them second if time
permits, but they are not blocking.

**Blinded human audit (50-100 samples, stratified)**:
Purpose: **validate the deterministic filter itself** — not audit rationale
directly. Produces a paper-defensible number ("deterministic filter and
human agreement rate = X%") which either:
  - ≥85% agreement → skip LLM judge, filter is validated as method
  - <85% → run LLM judge only on the human-vs-filter disagreement
    subset (a few hundred samples, not 3794)

Stratification: sampled evenly across
  - success ep vs failure ep (2 strata)
  - early ep vs late ep in each collect run (2 strata)
So 4 buckets × 12-25 samples each = 50-100 total.

Sample presentation:
  - Shuffled order, arm labels stripped
  - Human sees: (image_path, state, rationale text, chosen action)
  - Human labels: {clearly good, clearly bad, borderline}
  - Compare against filter's {pass, drop} decision
  - Agreement rate = fraction where human "clearly good" ↔ filter "pass"
    (borderline is excluded from denominator; also reported separately)

**Deliverables**:
1. `scripts/training/filter_rationale_deterministic.py` — the 3 rules,
   parses each sample, emits `{keep: bool, reject_reason: str|None}`.
2. `scripts/training/audit_gui.py` — a minimal CLI GUI (or Streamlit)
   for the 50-100-sample blinded audit. Prints image + rationale + action,
   accepts 1/2/3 keypress for good/bad/borderline, saves to CSV.
3. Post-audit report emitted from raw CSV: filter-vs-human confusion matrix
   + agreement rate + per-stratum breakdown.

**α allocation unchanged** — filter is a data-curation step, not a
statistical test.

**Frozen by**: TPEmist (chat), 2026-07-06.
- Amendment 2 commit SHA: **[filled after commit]**

---

### Amendment 1 — 2026-07-06 (before any adapter trains, still pre-hoc)

Two changes forced by adversarial review, both tighten the claim:

**Change 1: A_ctrl_rat rationale source**

Original v1 §2 specified A_ctrl_rat as "D6 trajectory + fresh-retrieval
rationale synthesized from current buffer". That design has a fatal
counterfactual problem:

- The D6 actions were produced by a teacher that had NEVER seen the
  retrieved lessons.
- Pairing those actions with post-hoc-generated rationales trains the
  student on a `(rationale R, action A)` pairing where A was not caused
  by R.
- The comparison then measures neither "rationale presence" nor
  "rationale content" — it measures noise from an impossible causal
  configuration.

Amended source: **use D6's own native Stage-1 THOUGHT block**, which
the replay schema already stores per interaction. That THOUGHT was
what the D6 teacher actually reasoned to produce that action — the
causal chain is intact. Truncate to ≤100 words to match the length
distribution of B_main's recap-gist prefix, so token-budget cannot
become the confounder.

New arm definitions (replacing §2 table for these two rows):

| Arm | Adapter | Training data | Purpose |
|---|---|---|---|
| A_ctrl     | v4-ctrl     | D6 success progress rounds, **action-only target** (no THOUGHT block) | Baseline distillation on memoryless teacher, no rationale slot |
| A_ctrl_rat | v4-ctrl-rat | D6 success progress rounds, **THOUGHT = D6's own native Stage-1 reasoning, ≤100 words** | Pure "Distilling Step-by-Step" effect — rationale exists, but it's memory-free rationale from memory-free teacher |

Interpretation ladder now clean:
- `A_ctrl_rat − A_ctrl` = pure rationale-as-auxiliary-supervision effect
  (isolates the arXiv:2305.02301 mechanism from memory content)
- `B_main − A_ctrl_rat` = memory-derived content + memory-shaped trajectory
  quality effect

This closes the reviewer objection: "your gain is just rationale-augmented
distillation, not memory." Without A_ctrl_rat in this form, T1 passing
does not defend that objection.

**Change 2: Sample-count confounder — add B_matched arm**

Original v1 had A_ctrl (n=158) vs B_main (n=992). If T1 passes, the
predictable second objection is "you trained on 6× more data, of course
the student is better."

New secondary arm: **B_matched** — random-sampled 158 rounds from
B_main's success-progress pool, same target format (rationale prefix +
action). Trained with same recipe as A_ctrl / A_ctrl_rat. Evaluated
at 50 ep (compressed budget to stay under wall-clock cap) as a
secondary comparison against A_ctrl_rat.

Claim upgrade path:
- If B_matched > A_ctrl_rat at similar n: "memory-augmented trajectories
  give more effective supervision per sample, independent of sample count"
  — a stronger claim than "more data helps."
- If B_matched ≈ A_ctrl_rat but B_main > A_ctrl_rat: "the gain is in the
  volume of memory-derived samples; per-sample effect is modest" —
  weaker but honest.

**α reallocation** (non-uniform Bonferroni):
Instead of 4 tests at α=0.0125 each, reallocate to preserve power on T1:
- T1 (B_main vs A_ctrl):          α = 0.020
- T1a (B_main vs A_ctrl_rat):     α = 0.010
- T3 (B_main ≥ 0.7 × mem-teacher): α = 0.010
- T4 (C_retrieval vs B_main):      α = 0.010
- Secondary (B_matched vs A_ctrl_rat, 50 ep): α = 0.010

Family-wise α = 0.06 (was 0.05); we accept the slight over-spend for
extra secondary evidence rather than power-loss on T1.

**R1 ΔX probe prediction updated (three-way fingerprint)**:

- A_ctrl:      predicted R1 ΔX ≈ −24 cm (D6-like, no memory content)
- A_ctrl_rat:  predicted R1 ΔX ≈ −24 cm (D6-like — rationale format
                without memory content should not shift bias)
- B_main:      predicted R1 ΔX ≈ −16 cm (memory-shifted, matches D10-ext
                terminal quartile)
- B_matched:   predicted R1 ΔX ≈ −18 to −20 cm (partial shift, small n)

If A_ctrl_rat's R1 ΔX also moves toward −16, the interpretation flips:
"the bias correction comes from the rationale format itself, not from
memory content." That would be a legitimate scientific outcome, not a
failure — a well-designed control gives interpretable results in both
directions.

**Cost delta**: −16h (removed fresh-retrieval generation for old
A_ctrl_rat) + 6.5h (B_matched training + 50 ep collect) = net −9.5 hr,
plus one extra 50-ep collect for B_matched. Total D11 budget still
~45h.

**Frozen by**: TPEmist (chat) — signed 2026-07-06 before any adapter
training dispatches.
- Amendment commit SHA: **`fe935e0`**
