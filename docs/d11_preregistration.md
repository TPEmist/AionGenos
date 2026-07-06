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
- Commit SHA: **[filled after commit]**
- Any subsequent modification requires a signed amendment section
  appended below (never overwrite section 1-10).

## 12. Amendment log

*(none yet)*
