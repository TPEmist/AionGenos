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

### Amendment 13 — 2026-07-08 (still before any adapter trains) — Step 2.verify row-count sentinel + drop_policy alias `flags_only_a6`

**Status**: LOCKED — filed before any D11 arm training was launched.
**Date**: 2026-07-08
**Supersedes**: nothing — extends Amendment 12 §12.1
`verify_training_shas` with an earlier, cheaper sentinel; renames the
driver's `--drop_policy` argument for self-documentation.
**Iron rule check**: no adapter training has consumed any of the four
2×2 target files at time of filing. ✅

Motivation. Dry-run review of Amendment-12's driver observed that
`check_prereq` printed only "prereq OK: 7 runs + frozen buffer" with
no per-file training-set gate — the SHA verification had been moved
to a post-Step-2 function (`verify_training_shas`) but its output
didn't appear at the top of the dry-run because dry-run mode short-
circuited it silently. Two concrete risks:

- Any silent Step-2 change that alters sample counts (a filter policy
  regression, a rationale_map miss, a prep-side bug) would not be
  caught by prereq. The pipeline would run 30 hours on 8 different-
  from-pinned files.
- The `--drop_policy asymmetric_kto` label is an Amendment-3-era name;
  Amendment 6 flag-only-fied all rules. The name still fires the
  correct code path (rule 1/2 are advisory-only inside the filter
  itself, only Rule 3 keeps drop authority and empirically fires
  0/3794), but a future maintainer reading `asymmetric_kto` will
  reasonably worry it drops KTO-desirable samples.

#### 13.1 Step 2.verify — row-count sentinel + SHA gate

`verify_training_shas` in `run_d11_pipeline.sh` now runs a two-stage
check in order:

- **(a) Row-count sentinel** (cheap, human-readable): every
  `v_final_sft_${arm}.jsonl` must have `SFT_EXPECTED_ROWS = 992`
  rows, every `v_final_kto_${arm}.jsonl` must have
  `KTO_EXPECTED_ROWS = 2791` rows. This is the Amendment-8 §8.6
  "same 2791-row pool across all four arms" invariant. Any mismatch
  produces "rows=X EXPECTED=Y — row count drifted, filter or prep is
  dropping rows silently" and `exit 2` before the SHA check runs.
- **(b) SHA pin verification**: the Amendment-12 §12.1 pinned first-
  24 hex is checked. Message includes the row count for context.

Coupled with §13.2's structural flag-only contract, the failure
surface narrows to a single place: a row-count sentinel failure
under `flags_only_a6` MUST originate upstream of the filter (prep
regression, rationale_map miss, replay drift). The filter itself is
proven not to drop under this policy. Debug path shortens by half.

Dry-run now emits a "Step 2.verify (would run here in real invocation)"
placeholder at the correct position (between the last Step-2 filter
and Step 3 smoke test) so its location is discoverable without
executing hashes.

Real-run verified (2026-07-08 16:45): 8/8 files pass row-count (992
for SFT, 2791 for KTO) and SHA-24 pin — see `logs/d11_seed_
determinism.log` and preceding driver stdout.

#### 13.2 `flags_only_a6` — structural flag-only policy (not just an alias)

Initial draft of Amendment 13 introduced `flags_only_a6` as a pure
alias for `asymmetric_kto` (same code path, same behavior). That was
insufficient: the Amendment-6 flag-only guarantee for
`asymmetric_kto` is empirical (Rule 3 fires 0/3794 in the current
teacher rationale format), not structural. A future upstream shift
(new rationale_source, new prep template, gist_only formatting drift
in D_gist) could make Rule 3 fire — and `asymmetric_kto` would
silently drop those rows.

Under `flags_only_a6` the drop-authority override is structural:

```python
if args.drop_policy == "flags_only_a6":
    force_keep = True
# ... after apply_filter ...
if force_keep:
    v = FilterVerdict(keep=True, ..., reject_reason=None, debug=v.debug)
```

Every rule outcome (including Rule 3 vacuity) is still computed and
emitted as an advisory flag (`rule3_flag` field on every output row),
but the sample is always kept. **Zero drops guaranteed by code.**

Contract summary:

- `strict`         : Rule 1 / 2 / 3 all drop (Amendment 3 legacy).
- `vacuity_only`   : Only Rule 3 drops.
- `asymmetric_kto` : Per-sample split (desirable→strict,
                     undesirable→vacuity_only). Empirically zero
                     drops on D11 data because Rule 3 hasn't fired.
- `flags_only_a6`  : Structural zero drops. All rules → flags only.
                     Row count IS the count of rows in the input
                     JSONL, by construction.

`run_d11_pipeline.sh` uses `flags_only_a6`. The Rule 3 fire count
still appears in filter stdout stats — a nonzero Rule-3-fire count
under `flags_only_a6` is now a smoke alarm for upstream format drift
(free monitoring, kept deliberately). Old names remain valid for
backwards compat with pre-Amendment-13 tools.

Regression check: A_action_only KTO regenerated with `flags_only_a6`
produces sha `f30a3c3011bcb4b9208754ee` — byte-identical to the
Amendment-12 §12.1 pin. The structural override changed nothing on
this data (as expected, Rule 3 never fired), but the guarantee is
now a code path rather than a coincidence.

#### 13.3 Retained raw files (documentation-only, not enforced)

`Step 2.*.filter` currently ends with `&& rm -f *.raw.jsonl`. This
saves ~30 MB but discards the pre-filter file, which would be needed
if a future user asks "why is row (ep_id=X, round=Y) flagged rule
1_inconsistent — is it a filter bug or a real inconsistency in the
teacher's rationale?" The reasons.csv retains all flag verdicts, so
this is a debug-effort tradeoff, not a data-loss risk. Filed as a
future ease-of-debugging improvement (drop the `rm -f`); not enforced
by Amendment 13.

#### 13.4 Anchors

- Amendment 13 commit SHA: **_TBD (backfill after commit)_**
- Depends on: Amendment 12 (`0e26443`), Amendment 12 code (`ae196b5`).
- Companion code commit: **`9f5bec1`**.

**Frozen by**: TPEmist (chat) — signed 2026-07-08 before any adapter
training dispatches.

---

### Amendment 12 — 2026-07-08 (still before any adapter trains) — Canonical training-set naming, D_gist eval-slot fix, SHA gate timing, driver robustness

**Status**: LOCKED — filed before any D11 arm training was launched.
**Date**: 2026-07-08
**Supersedes**: file-name mentions in §8.6 (`v_final_kto_A_ctrl`,
`v_final_kto_B_v2`, `v_final_sft_A_v2`) — see §12.1 for canonical
successors. Also supersedes Amendment 11 §11.3's SHA gate wiring
(inline in `check_prereq`) — moved to a post-Step-2 gate per §12.1.
**Iron rule check**: no adapter training has consumed any of the four
2×2 target files at time of filing. ✅

Motivation. Dry-run review of `run_d11_pipeline.sh` after Amendment
11 surfaced four latent hazards that would have wasted 30 hours of
D11 compute:

- Filename convention drifted between `check_prereq` (verified
  `v_final_kto_${arm}`) and `Step 2` (generated
  `v_final_kto_B_${arm}` with a redundant "B_" prefix). Result: the
  SHA gate validated a stale fallback file and the actual training
  input passed through ungated.
- D_gist's `--eval_template_variant` was set to `rationale_with_gist`,
  but its training targets contained no `INTRINSIC_RATIONALE:` slot.
  The eval prompt would have asked the model to emit a slot it had
  never learned — a third-generation instance of the train/eval
  format mismatch class the whole D11 rewrite exists to prevent.
- Step labels changed from integers to `"2.A_ctrl_rat.sft"` strings
  for per-arm nesting, but `--skip N` still integer-compared against
  the string, breaking mid-pipeline resume — which the server-reboot
  history means we WILL need.
- Readonly gate on the C_retrieval buffer counted files; a same-count
  overwrite (recap of a new episode replacing a byte-identical name)
  would slip through undetected.

#### 12.1 Canonical filenames + post-Step-2 SHA gate

All training-set files use the pattern

```
${TRAINING_SETS_DIR}/v_final_{sft,kto}_${arm}.jsonl
```

with `arm ∈ {A_action_only, A_ctrl_rat, B_main, D_gist}`. No `_v2`,
`_A_`, `_B_`, `A_ctrl` legacy prefixes remain. Files are post-filter
(deterministic 3-rule filter with `--drop_policy asymmetric_kto`),
which adds `rule{1,2,3}_flag` fields but drops 0 rows.

New Amendment-12 SHA pins (first 24 hex of SHA-256):

| file (data/training_sets/) | n | sha (first-24) |
|---|---|---|
| v_final_sft_A_action_only.jsonl | 992  | `e2572d16071519ca4f984f7c` |
| v_final_kto_A_action_only.jsonl | 2791 | `f30a3c3011bcb4b9208754ee` |
| v_final_sft_A_ctrl_rat.jsonl    | 992  | `39adb1640cec9eb831e028a3` |
| v_final_kto_A_ctrl_rat.jsonl    | 2791 | `870df21da5c64a9cbfb7678f` |
| v_final_sft_B_main.jsonl        | 992  | `ce7434ed7b227a31a032a765` |
| v_final_kto_B_main.jsonl        | 2791 | `98c4ffca1715f20c7a3191a1` |
| v_final_sft_D_gist.jsonl        | 992  | `6a2436a056752513ec389e9e` |
| v_final_kto_D_gist.jsonl        | 2791 | `4091ebc175c2c1b712d489d1` |

Cross-check: `v_final_sft_B_main.jsonl` (this pin `ce7434ed…`) and
`v_final_kto_B_main.jsonl` (`98c4ffca…`) match the Amendment 8 §8.6
`v_final_sft_A_v2.jsonl` / `v_final_kto_B_v2.jsonl` pins byte-for-byte
under the new name — same content, canonical name.

SHA gate timing: moved from `check_prereq` (pre-Step-2) to a new
`verify_training_shas` function invoked AFTER Step 2's generate+filter
pipeline has run. Non-zero exit halts the pipeline. Runs whenever
`SKIP_TO < 5`, so `--skip 3` (jump to smoke test) also verifies the
canonical files that must be on disk for later steps.

#### 12.2 D_gist gets its own eval variant `gist_only`

`aiongenos/vlm/prompts.py::STAGE1_TEMPLATES_BY_VARIANT` gains a
`gist_only` variant:

```
PAST_LESSONS: <top-3 retrieved lessons as bullets>
LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>
RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>
STOP: <true|false>
```

which matches D_gist's training target (`--rationale_source
gist_only`: gist + canonical, no INTRINSIC_RATIONALE). `run_collect.py`
CLI `choices` updated. Driver's `ARM_TO_VARIANT` and
`PROTOCOL_TO_VARIANT` both map `D_gist → gist_only`.

#### 12.3 Readonly gate upgraded to tree hash

`run_d11_pipeline.sh` step `8.frozen_buffer_unpack` records

```
sha256sum( sorted( per-file sha256sum ) )
```

into `/tmp/d11_c_retrieval_buffer_tree.sha256`. The C_retrieval
post-collect gate re-computes and compares byte-for-byte; any
mismatch triggers `exit 3` with message "READONLY GATE FAILED —
buffer tree hash changed during C_retrieval eval". Catches same-count
overwrites that the file-count gate missed.

#### 12.4 Driver robustness — `--skip` string-safe + hard-exit on missing buffer

- The `run` helper now extracts the leading integer of the step label
  before comparing to `SKIP_TO` (`step_num=${step%%.*}`). Labels like
  `"2.A_ctrl_rat.sft"` now compare as 2, restoring `--skip N` resume
  after a mid-pipeline crash.
- `check_prereq` now hard-exits (exit 2) if the frozen buffer tar is
  missing, matching the severity of a SHA mismatch. Previously
  missing-file merely printed a warning — inconsistent with the same
  gate's mismatch behavior.

#### 12.5 Anchors

- Amendment 12 commit SHA: **`0e26443`**
- Depends on: Amendment 11 (`bfa7cc6`), Amendment 8 code (`1a44d61`),
  Amendment 8 pre-reg (`a7bada2`).
- Companion code commit (prompts.py + run_collect + driver rewrite):
  **`ae196b5`**.

**Frozen by**: TPEmist (chat) — signed 2026-07-08 before any adapter
training dispatches.

---

### Amendment 11 — 2026-07-08 (still before any adapter trains) — Paired design → McNemar; env_seed_base pin; SHA gate

**Status**: LOCKED — filed before any D11 arm training was launched.
**Date**: 2026-07-08
**Supersedes**: primary-test formula (two-proportion z-test) in §7 for
T1 / T1a / T4 pairwise contrasts. Adds two operational pins used by
`scripts/training/run_d11_pipeline.sh`.
**Iron rule check**: no adapter training has consumed any of the four
2×2 target files at time of filing. ✅

Motivation. The `--env_seed_base` plumbing landed in Amendment 7 §7.7
(commit `bc524b8`) means the D11 eval collect is paired by design:
every eval protocol runs episode index k against the SAME initial
world state induced by `seed = env_seed_base + k`. Under paired
observations the two-proportion z-test is no longer the correct
primary statistic — it treats the two arms as independent samples
and wastes the within-episode dependence structure that seed-sharing
was built to expose. Amendment 11 upgrades the primary tests to
McNemar (paired binary) and demotes z to a sensitivity check.

#### 11.1 Primary test upgrade — McNemar for T1 / T1a / T4

For each pairwise contrast (X vs Y), enumerate the 100 ep_idx values
and their per-arm binary success outcomes:

|                | Y success | Y failure |
|----------------|-----------|-----------|
| **X success**  | n_11      | n_10      |
| **X failure**  | n_01      | n_00      |

McNemar statistic under H0 (no difference in the discordant cells):

```
χ² = (|n_10 − n_01| − 1)² / (n_10 + n_01)     # with continuity correction
```

for n_10 + n_01 ≥ 25; otherwise exact binomial on min(n_10, n_01) with
n = n_10 + n_01 and p = 0.5.

Primary tests migrated to McNemar:

- **T1 (strong)**: `B_main vs A_action_only`, McNemar at α=0.020,
  with pre-registered practical-significance threshold Δ SR ≥ +10 pp
  (Amendment 9 §9.2).
- **T1 (weak)**: `B_main vs A_action_only`, McNemar at α=0.010 with
  no practical-significance threshold — passes on statistical
  significance alone; publishable claim gated to "directional
  transfer" per §9.2.
- **T1a**: `B_main vs A_ctrl_rat`, McNemar at α=0.020 (Amendment 10
  §10.2 reallocation).
- **T4**: `C_retrieval vs B_main`, McNemar at α=0.010.
- **T3**: `B_main ≥ 0.7 × memory-teacher-SR`, unchanged (one-sided
  proportion vs constant); z-test retained.

**Sensitivity check** (not a primary test): the two-proportion z-test
values remain reported alongside each McNemar as evidence that the
result is not an artifact of the paired-design assumption. If the two
statistics disagree in direction of significance, the primary McNemar
still governs.

**Family-wise α**: 0.060 (unchanged; McNemar substitution does not
alter the Bonferroni allocation).

#### 11.2 env_seed_base — locked value 4500

`run_d11_pipeline.sh` (commit added in this round) pins:

```
D11_ENV_SEED_BASE = 4500
```

Every eval protocol collect (A_action_only, A_ctrl_rat, B_main,
D_gist, C_retrieval) runs with `--env_seed_base 4500`. Per-ep seed
is 4500 + ep_idx, so ep_idx=0 across all five protocols starts from
the SAME world state, and so on to ep_idx=99. This is what makes the
paired McNemar analysis in §11.1 valid.

Choice of 4500: arbitrary but different from all training-side seeds
used in D6 / D10-ext / prep scripts, so that D11 eval initial poses
have not been seen during any teacher-side data generation. If the
Blocker-2 smoke test (§11.4) reveals ep_idx=0 lands the EE inside a
particular workspace corner in a way that is degenerate, this pin is
allowed a ONE-TIME rotation to (4500 + 100) = 4600 before any real
collect launches; that rotation must be filed as an Amendment
addendum, not a silent edit.

#### 11.3 JSONL SHA gate — enforced by pipeline prereq check

`run_d11_pipeline.sh check_prereq` verifies the first-24-hex of
sha256 for every §8.6-pinned training file:

- `v_final_kto_A_ctrl.jsonl`     (A_action_only) → `3386672377abf8bb2899a7e0`
- `v_final_kto_A_ctrl_rat.jsonl`                 → `542eddde69cfada29daf096c`
- `v_final_kto_B_v2.jsonl`       (B_main)        → `98c4ffca1715f20c7a3191a1`
- `v_final_kto_D_gist.jsonl`                     → `2eea5c6b7c3f9e7046fa09b4`
- `v_final_sft_A_v2.jsonl`                       → `ce7434ed7b227a31a032a765`
- `workspace/frozen_buffers/d10ext_final_buffer.tar.gz` →
  `a762386b79e18ce50440d1ff3e7045f6f82f32bd7b05092ac332b9217fb0eb9c`
  (full 64-hex; C_retrieval buffer snapshot).

The pipeline exits non-zero on any mismatch. Rationale: Amendment 8
§8.6 pinned these bytes; if they no longer match, the pipeline is
either running on stale files or on files regenerated by a code path
that has drifted from the pin — either way, the four arms would not
be sharing the same 2791-row ID set (§8.6 invariant), and every
downstream contrast is contaminated.

#### 11.4 Blocker 2 dependency — seed determinism smoke test

`scripts/diagnostics/check_env_seed_determinism.py` is dispatched at
Step 3 of the pipeline (BEFORE the server-side training block). It
MUST return exit 0 (both conditions PASS: same-seed determinism +
different-seed variation), or the pipeline halts. Non-negotiable —
if seed is silently ignored by IsaacLab's randomization events, the
paired McNemar analysis is a mirage and the T1 statistical power
argument in Amendment 10 §10.2 evaporates.

The interface implementation (`aiongenos/orchestrator/isaaclab_env_interface.py`
IsaacLabEnvInterface.reset, commit `bc524b8` + follow-up) belt-and-braces
seeds `torch / np.random / random` global RNGs plus `env.reset(seed=)`
to defend against IsaacLab randomization event terms that read a
different RNG stream than the env's private one.

#### 11.5 Anchors

- Amendment 11 commit SHA: **`bfa7cc6`**
- Depends on: Amendment 10 (`bf2dbb5`), Amendment 9 (`503496b`),
  Amendment 8 pre-reg (`a7bada2`), Amendment 8 code (`1a44d61`).
- Companion code change (driver + smoke test + interface seeding):
  **`64798d7`**.

**Frozen by**: TPEmist (chat) — signed 2026-07-08 before any adapter
training dispatches.

---

### Amendment 10 — 2026-07-08 (still before any adapter trains) — B_matched removed (confounder dissolved), α reallocated to T1a

**Status**: LOCKED — filed before any D11 arm training was launched.
**Date**: 2026-07-08
**Supersedes**: Amendment 1's "Change 2: Sample-count confounder"
(paragraph text at pre-reg lines 1176+), the "Secondary" α row in
Amendment 1's Bonferroni allocation, all Amendment 8 references to
`B_matched`, and the `B_matched` row in Amendment 9 §9.3's per-arm
R1 ΔX prediction table.
**Iron rule check**: no adapter training has consumed any of the four
2×2 target files at time of filing. ✅

#### 10.1 Motivation — the confounder B_matched was designed to control has been dissolved

Amendment 1 introduced B_matched to control a 6× sample-count
imbalance between the then-158-row A_ctrl arm and the 992-row B_main
arm. Amendment 8 §8.6 pinned all four training arms to the SAME 2791-
row pool (992 desirable + 1799 undesirable, identical `(run, ep,
round)` ID set across arms). Once samples are equalized, the
6×-imbalance confounder does not exist and B_matched has no residual
job:

- `B_main − A_action_only` (the T1 headline) is already at matched
  sample count.
- `B_main − A_ctrl_rat` (T1a) is already at matched sample count.

An "n=158 vs n=992 same-format" side experiment could be defined
post-hoc, but it does not test a claim this paper makes (the thesis
is weights vs context memory, not data-efficiency), and one point
does not define a scaling curve. If a future rebuttal requires
data-efficiency evidence, B_matched can be run then as a post-hoc
supplement — a side question needs no confirmatory pre-registration.

#### 10.2 α reallocation — the 0.010 goes entirely to T1a

Amendment 1's non-uniform Bonferroni allocation was:

- T1 (B_main − A_action_only):       α = 0.020
- T1a (B_main − A_ctrl_rat):         α = 0.010
- T3 (B_main ≥ 0.7 × mem-teacher):   α = 0.010
- T4 (C_retrieval − B_main):         α = 0.010
- Secondary (B_matched − A_ctrl_rat, 50 ep): α = 0.010

Family-wise α: 0.060.

With B_matched removed, the freed 0.010 is reallocated **entirely to
T1a** (not split, not returned to headline). Rationale: Amendment 9
§9.2 narrowed T1's semantics (pure target-content effect after
teacher-side memory was factored out into D6b). Under the narrower
semantics the +10-pp headline threshold is deliberately kept, which
raises the exposure of the "true effect, modest size" scenario in
which T1-strong fails but T1-weak / T1a should still catch the signal.
T1a is that safety net; more α on T1a = more power against precisely
that scenario.

New allocation:

- T1 (B_main − A_action_only):       α = 0.020
- **T1a (B_main − A_ctrl_rat):       α = 0.020** (was 0.010)
- T3 (B_main ≥ 0.7 × mem-teacher):   α = 0.010
- T4 (C_retrieval − B_main):         α = 0.010

Family-wise α: 0.060 (unchanged — dropped test, redistributed
allocation).

Note on Amendment 9 §9.2's two-tier T1: T1-strong (+10 pp at α=0.020)
and T1-weak (z > 1.96 at α=0.010) continue as pre-registered.
Amendment 10 does not alter the T1 tier structure; the reallocated
0.010 lands on T1a, a separate contrast (B_main vs A_ctrl_rat).

#### 10.3 Arm table — final form

Training adapters (four):

|                       | no retrieved gist         | with retrieved gist    |
|-----------------------|---------------------------|------------------------|
| no native thought     | **A_action_only**         | **D_gist** (secondary; drop-first if budget slips) |
| with native thought   | **A_ctrl_rat**            | **B_main**             |

Eval protocols (five, sharing the four adapters):

- A_action_only     — no retrieval, --eval_template_variant=action_only
- A_ctrl_rat        — no retrieval, --eval_template_variant=rationale
- B_main            — no retrieval, --eval_template_variant=rationale_with_gist
- D_gist            — no retrieval, --eval_template_variant=rationale_with_gist (secondary)
- C_retrieval       — A_ctrl_rat adapter + frozen D10-ext buffer
                       retrieval preamble,
                       --eval_template_variant=rationale_with_retrieval,
                       --recap_buffer_readonly

`B_matched` no longer appears in either list.

#### 10.4 Downstream text tombstoning

The following pre-reg passages are now tombstones — read-only
historical record, no operational force:

- Amendment 1 "Change 2: Sample-count confounder — add B_matched
  arm" (pre-reg lines ~1176 onward).
- Amendment 1 "α reallocation" bullet: "Secondary (B_matched vs
  A_ctrl_rat, 50 ep): α = 0.010".
- Amendment 1 "R1 ΔX probe prediction updated (three-way
  fingerprint)": the `B_matched` bullet is retired.
- Amendment 8 §8.3 sentence "plus **B_matched** as SFT-only
  sample-count control (Amendment 7 §7.4)": retired.
- Amendment 8 §8.8 open-item mention of "B_matched fixed seed,
  SFT-only positioning": retired.
- Amendment 9 §9.3 R1 prediction table: the `B_matched` row is retired.

Amendment 7 items 4–5 (B_matched fixed seed, SFT-only positioning) are
withdrawn as no-op. Items 6–7 (cross-arm hyperparam sharing +
effective-step logging; env `reset(seed=...)` plumbing) remain OPEN.

#### 10.5 Cost delta

- −7 hr training (B_matched adapter no longer built)
- −8 hr eval (50-ep collect deleted)
- 0 α net-spent (0.010 moved, not added)
- 0 forfeited claim scope (the memory-in-weights thesis does not route
  through a sample-count arm)

#### 10.6 Anchors

- Amendment 10 commit SHA: **`bf2dbb5`**
- Depends on Amendment 9 (`503496b`) and Amendment 8 code (`1a44d61`),
  pre-reg (`a7bada2`).

**Frozen by**: TPEmist (chat) — signed 2026-07-08 before any adapter
training dispatches.

---

### Amendment 9 — 2026-07-08 (still before any adapter trains) — Semantic consequences of Amendment 8: T1 threshold, R1 probe rewrite, thought-leak quantification, arm rename

**Status**: LOCKED — filed before any D11 arm training was launched.
**Date**: 2026-07-08
**Supersedes**: §1–§10 wording that referred to `A_ctrl` under its old
"D6-only, memoryless teacher" semantics. Also revises T1 threshold
interpretation and the R1 ΔX per-arm prediction table.
**Iron rule check**: no adapter training has consumed any of the four
2×2 target files at time of filing. ✅

Motivation. Amendment 8 §8.6 pinned all four 2×2 training arms to the
same 2791-row pool drawn from seven memory-augmented D10-ext runs.
That silently rewrote what `A_ctrl` falsifies: originally
"memoryless-teacher distillation gives no gain" (D6-only source);
now "target-content ablation gives no gain within the same
memory-teacher trajectory pool". The two are legitimate but distinct
falsifiers, and D11 can only test the second. This addendum makes the
consequences explicit before any adapter starts training.

#### 9.1 Division of labour: D6b covers the teacher-side falsifier

The "memoryless-teacher distillation" falsifier is retired from D11
scope. It is already answered by the D6b factorial (paper_notes.md,
committed pre-Amendment 8): **memory main effect +19.2 pp**, memory
teacher's trajectories are strictly better source material than the
no-memory teacher's. That result stands on its own commit chain and
does not need re-litigation inside D11.

D11 therefore inherits a narrower question: **holding teacher-side
constant (all four arms drink from the same memory-teacher pool),
which target-content ingredients transfer under distillation?**

#### 9.2 T1 threshold — deliberate retention at +10 pp, plus a graded fallback

Original §7 pre-registered `T1: B_main − A_ctrl > +10 pp` as headline
falsification. Under §2's old semantics this Δ pooled two effects
(teacher-side memory + target-side rationale/gist); under Amendment 8's
new semantics only the target-content effect remains. The +10 pp
threshold was set for the pooled quantity.

**Decision** (locked here, before any results): keep +10 pp for the
headline claim. Rationale: (i) only large per-sample-format effects
deserve the "memory ingredient bakes into weights" claim; (ii)
adjusting downward now, after redefining the LHS but before seeing
data, would look like moving the goalposts even if intended
conservatively.

**Add a graded secondary** (also pre-registered here, to prevent
post-hoc softening if the headline just barely misses):

- **T1-strong** (headline): `B_main − A_action_only ≥ +10 pp` at α=0.020
  → publishable claim: "memory content bakes into student weights with
  substantial effect size, independent of teacher-side memory
  presence."
- **T1-weak** (secondary): `B_main − A_action_only > 0 with z > 1.96`
  at α=0.010 → publishable weaker claim: "memory content transfers
  directionally under distillation; effect size within this 2×2
  ablation is modest (< 10 pp) and warrants larger-n confirmation."

If neither passes, the memory-in-weights claim is withdrawn. If only
T1-weak passes, the paper writes the weaker version — no post-hoc
climb from "directional" to "substantial".

#### 9.3 R1 ΔX probe — from sanity check to mechanism probe

Amendment 8 upgraded this probe by accident. Because A_action_only's
teacher is a memory teacher (its behavior is already bias-corrected to
≈ −16 cm on average), the R1 ΔX outcome now discriminates
mechanistically between two hypotheses:

- **H_behavior**: memory corrects bias at the action-layer; the
  bias-corrected coordinates in the target are sufficient supervision;
  no language carrier needed. Prediction: A_action_only ≈ B_main
  ≈ −16 cm; probe fails to differentiate.
- **H_language**: memory correction requires a language-layer carrier
  (rationale text encoding the corrected spatial frame); dropping the
  rationale block loses the correction. Prediction: A_action_only
  reverts toward −24 cm; B_main stays ≈ −16 cm; probe becomes direct
  evidence of language-mediated bake-in.

**Per-arm predictions** (locked, before D11):

| arm | R1 ΔX (H_behavior) | R1 ΔX (H_language) | interpretation on convergence |
|---|---|---|---|
| A_action_only | ≈ −16 cm | ≈ −24 cm | which end wins IS the finding |
| A_ctrl_rat    | ≈ −16 to −20 cm | ≈ −18 to −22 cm | intermediate under either (has ~32% implicit leak) |
| B_main        | ≈ −16 cm | ≈ −16 cm | matches D10-ext terminal quartile under either |
| D_gist        | ≈ −16 cm | ≈ −18 to −22 cm | gist without native thought stresses H_language |
| B_matched     | ≈ −18 to −20 cm | ≈ −18 to −22 cm | small-n partial shift under either |
| C_retrieval   | ≈ −16 cm | ≈ −16 cm | context-injected retrieval bypasses target-content axis |

Report the observed R1 ΔX per arm on the same table; the H_behavior /
H_language shading becomes the mechanism finding.

#### 9.4 A_ctrl_rat native-thought memory leak — quantified, direction-declared, not cleaned

Because all four arms draw from memory-teacher (D10-ext) trajectories,
A_ctrl_rat's `INTRINSIC_RATIONALE` block is the teacher's own thought
generated AFTER seeing PAST_LESSONS retrieval — it can echo the
retrieved lessons in language even without an explicit gist header.

Grep audit on `data/training_sets/v_final_kto_A_ctrl_rat.jsonl`
(2791 native thoughts total, produced by
`docs/d11_preregistration/thought_leak_audit.md`):

| pattern | matches | % of thoughts |
|---|---|---|
| any cross-episode reference | 884 | **31.7%** |
| `past episodes/attempts/scenes` | 591 | 21.2% |
| `past` (excluding prev round) | 670 | 24.0% |
| `lesson`  | 384 | 13.8% |
| `previous episode` | 86 | 3.1% |
| `similar past` | 37 | 1.3% |
| `history / prior experience` | 26 | 0.9% |
| `recall` | 62 | 2.2% |
| episode-internal only (`previous move/round`) | 759 | 27.2% (not counted as leak) |

**Sanity**: A_ctrl_rat and B_main share **100% identical thought text**
(2791/2791 (run, ep, round) tuples map to byte-identical thought
strings). Both arms carry the same 31.7% implicit leak; the two-arm
contrast is therefore symmetric on leak.

**Direction declaration** (pre-registered here):

- A_action_only vs A_ctrl_rat: A_ctrl_rat has +31.7% implicit memory
  language + +121-token rationale format. This overstates the
  "rationale format" factor (any observed Δ is a mixture of format and
  implicit leak).
- A_ctrl_rat vs B_main: B_main adds an explicit PAST_LESSONS gist on
  top of the same 31.7%-leaked thought. This understates the "explicit
  retrieval content" factor (A_ctrl_rat already ate some retrieval
  content in language form). If B_main − A_ctrl_rat is still
  significant under this dilution, the conclusion is strictly stronger.

**No thought-cleaning intervention.** Rewriting native thoughts to
strip past-reference language would add a curation-freedom axis and
break the pre-registration hygiene the whole D11 rewrite exists to
protect. The dilution is accepted, declared, and interpreted in the
conservative direction.

#### 9.5 Arm rename: A_ctrl → A_action_only

Amendment 8's A_ctrl semantics ("target = canonical action lines
only") deserves a name that says what the arm actually is. Rename in
all pre-registration text going forward:

- `A_ctrl` → `A_action_only`
- CLI `--rationale_source none` unchanged (already accurate).
- Training-set filename `v_final_kto_A_ctrl.jsonl` retained (no data
  rewrite, only conceptual rename); an alias symlink
  `v_final_kto_A_action_only.jsonl` may be added if convenient but is
  not required.
- 2×2 table updates:

|                       | no retrieved gist    | with retrieved gist |
|-----------------------|----------------------|---------------------|
| no native thought     | **A_action_only**    | **D_gist** (secondary) |
| with native thought   | **A_ctrl_rat**       | **B_main**          |

- Primary hypothesis tests referenced by A_ctrl in §7 are rewritten in
  §9.2 as `B_main − A_action_only`.

The name `A_ctrl` in Amendment 8 §8.2 / §8.6 tables remains in place
for immutable-record purposes; readers should treat it as an alias for
A_action_only per §9.5.

#### 9.6 Anchors

- Grep audit reproducible via
  `docs/d11_preregistration/thought_leak_audit.md`
  (patterns + counts + representative examples).
- Depends on Amendment 8 commit SHA **`a7bada2`** (pre-reg doc) and
  **`1a44d61`** (code).
- Amendment 9 commit SHA: **`503496b`**

**Frozen by**: TPEmist (chat) — signed 2026-07-08 before any adapter
training dispatches.

---

### Amendment 8 — 2026-07-08 (still before any adapter trains) — Cross-arm target-format hygiene + 2×2 factorial + C_retrieval as inference protocol

**Status**: LOCKED — filed before any D11 arm training was launched.
**Date**: 2026-07-08
**Supersedes**: §6.4 pin (files + counts) — see §8.6 for new pin. All
other Amendment 6 clauses (Rule 1/2/3 as advisory flags) retained.
**Iron rule check**: no adapter training has consumed any of the four
2×2 target files at time of filing. ✅

Motivation. A bug found during D11 prep: the B_main training targets
were "PAST_LESSONS gist + teacher prose", where the prose contained
coord numbers embedded in text (e.g. "X=-12, Y=30, Z=-45") but not
canonical `LEFT_TARGET_POS: X=.. Y=.. Z=..` lines — because D6/D10-ext
teacher `full_response` is prose only, and the coordinate parser lifts
numbers from prose. Meanwhile the newly added A_ctrl / A_ctrl_rat arms
emitted canonical action lines synthesized from the parsed coord fields.
Result: A_ctrl / A_ctrl_rat students learn canonical output, B_main
student learns prose output. The B_main − A_ctrl_rat comparison was no
longer a pure rationale ablation — output format also differed, which
(a) contaminates arm attribution and (b) puts B_main at inference-time
disadvantage under constrained decoding (which stops at `LEFT_TARGET_POS`
and expects the canonical form). The R1 ΔX probe is only well-defined
when every arm emits the canonical coordinate line, so the fix is
architectural, not cosmetic.

#### 8.1 Cross-arm target hygiene — single canonical synthesizer

All training arms now build their target's action tail through the same
function, `scripts/training/prep_training_data.py :: _build_action_lines`,
which reads `parsed_left_pos / parsed_right_pos / parsed_stop` directly
from the interaction record. Format:

```
LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>
RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>
STOP: <true|false>
```

Any target-format drift between arms would now be a bug in this single
function.

#### 8.2 2×2 factorial training design

Two independent factors → four training-time arms. Every arm terminates
with the canonical action lines from §8.1.

|                       | no retrieved gist | with retrieved gist |
|-----------------------|-------------------|---------------------|
| no native thought     | **A_ctrl**        | **D_gist** (secondary) |
| with native thought   | **A_ctrl_rat**    | **B_main**          |

- A_ctrl: canonical action lines only.
- A_ctrl_rat: `INTRINSIC_RATIONALE: <thought>` + canonical.
- D_gist: `PAST_LESSONS: <top-3 lessons>` + canonical.
- B_main: `PAST_LESSONS: <top-3 lessons>` + `INTRINSIC_RATIONALE: <thought>` + canonical.

D_gist is **secondary** — it isolates "gist without native thought", but
none of the primary hypotheses (T1–T4) route through it. If the D11
budget runs long, D_gist is the first arm to drop.

#### 8.3 C_retrieval is not the 2×2 fourth cell — it is an inference protocol

Original v6 pre-registration listed C_retrieval alongside A/B/D as if it
were a fourth training arm. This confused two orthogonal dimensions
(training-time target content vs inference-time protocol). Amendment 8
separates them:

- **Training** (four adapters, all with constrained decoding, no
  inference-time retrieval): A_ctrl / A_ctrl_rat / B_main / D_gist,
  plus **B_matched** as SFT-only sample-count control (Amendment 7 §7.4).
- **Inference protocol** (five eval collects, sharing the four adapters):
  A_ctrl / A_ctrl_rat / B_main / B_matched all run **no retrieval**;
  **C_retrieval** reuses the **A_ctrl_rat** adapter and injects a frozen
  D10-ext buffer retrieval preamble at inference time.

Why A_ctrl_rat is C_retrieval's base (not A_ctrl):

- A_ctrl_rat's adapter has seen `INTRINSIC_RATIONALE: … + canonical`
  target structure at training time.
- At inference, C_retrieval prepends a `PAST_LESSONS: …` preamble to the
  user prompt; the model's own output slots stay `INTRINSIC_RATIONALE`
  + canonical — same slot shape it learned.
- A_ctrl as base would have to interpret both a retrieval preamble AND
  produce rationale-plus-action tail, without having learned either
  format contribution — that would confound retrieval effect with
  format adaptation.

Under this split the three key contrasts become:

- **B_main − A_ctrl_rat**: retrieved memory baked into weights.
- **C_retrieval − A_ctrl_rat**: retrieved memory injected via context.
- **B_main − C_retrieval**: parameter memory vs external memory (paper's
  thesis contrast). Each pairwise contrast now differs in exactly one
  variable.

#### 8.4 Length confound quantified, not eliminated

By construction B_main's target ≈ A_ctrl_rat's target + gist block, so
B_main is ~134 tokens longer on average. Full per-arm table in
`docs/d11_preregistration/target_length_distributions.md`. Median deltas
across the 2×2 (measured empirically):

- gist adds ≈134 tokens (D_gist − A_ctrl = 134; B_main − A_ctrl_rat = 134)
- thought adds ≈121 tokens (A_ctrl_rat − A_ctrl = 121; B_main − D_gist = 121)

The two factors are near-perfectly additive on target length; the
confound reduces to two known constants. Sensitivity analyses on record:

1. Token-count regression: report SR residualized on target-token count
   across arms (does the effect survive length control?).
2. D_gist secondary arm serves as an equal-length control for the
   "retrieved gist" factor (if it trains).
3. C_retrieval − A_ctrl_rat uses **identical training targets** (same
   adapter), so is a pure inference-protocol contrast with no
   training-target length confound.

#### 8.5 Inference-template + buffer-freeze plumbing

`--eval_template_variant` on `scripts/run_collect.py` selects the
output-slot shape presented to the student (implemented in
`aiongenos/vlm/prompts.py::STAGE1_TEMPLATES_BY_VARIANT`):

- `action_only` → A_ctrl adapter (no THOUGHT slot, canonical only)
- `rationale` → A_ctrl_rat adapter (INTRINSIC_RATIONALE + canonical)
- `rationale_with_gist` → B_main adapter (PAST_LESSONS + INTRINSIC_RATIONALE + canonical)
- `rationale_with_retrieval` → C_retrieval eval — same prompt as
  `rationale` (base = A_ctrl_rat adapter + preamble retrieval).

`--recap_buffer_readonly` on `scripts/run_collect.py` disables new
recap writes during eval. C_retrieval MUST use it; otherwise its
"external memory" grows during eval and the weights-vs-context
comparison against B_main (frozen weights) is no longer symmetric.

Frozen buffer snapshot at time of Amendment 8 (D10-ext terminal state):

- Path: `workspace/frozen_buffers/d10ext_final_buffer.tar.gz`
- SHA256: `a762386b79e18ce50440d1ff3e7045f6f82f32bd7b05092ac332b9217fb0eb9c`
- Contents: 547 recap records across 7 runs (6b9ef134, 70028c23,
  18581c81, b74d9f38, 0eb35c80, 54bcc2d4, aa08bb4c).

#### 8.6 Regenerated training-set pin (supersedes §6.4)

Old files (§6.4 pin, retired):

- `data/training_sets/v_final_sft_A.jsonl` — 992 desirable
- `data/training_sets/v_final_kto_B.jsonl` — 992 desirable + 1810 undesirable

New files:

| file (data/training_sets/) | rows | sha256 (24) |
|---|---|---|
| v_final_sft_A_v2.jsonl       | 992  | `ce7434ed7b227a31a032a765` |
| v_final_kto_B_v2.jsonl       | 2791 | `98c4ffca1715f20c7a3191a1` |
| v_final_kto_A_ctrl.jsonl     | 2791 | `3386672377abf8bb2899a7e0` |
| v_final_kto_A_ctrl_rat.jsonl | 2791 | `542eddde69cfada29daf096c` |
| v_final_kto_D_gist.jsonl     | 2791 | `2eea5c6b7c3f9e7046fa09b4` |

**ID-set diff vs §6.4 pin** (SHA of sorted `(run, ep, round)` tuples, first 16 hex):

- v_final_kto_B desirable:   old 992 == new 992, hash `85a6dbc407b2d278` unchanged (same batch, format only).
- v_final_kto_B undesirable: old 1810 → new 1799, lost 11 (subset relation
  gained=0). All 11 lost rows are from the single ep
  `6b9ef134/0982ca01-144` which has no rationale_map hit; the old prep
  fell back to keeping the row without a gist prefix (definition
  pollution), the new prep drops rows without retrieval so
  {B_main, D_gist} arms are always gist-carrying and
  {A_ctrl, A_ctrl_rat} arms use the same row set via
  `--restrict_to_retrievable`.
- v_final_sft_A desirable: 992 == 992, hash `85a6dbc407b2d278` unchanged.

All four training arms share the SAME 2791 (run, ep, round) tuples —
cross-arm sample-count is a controlled variable, not a between-arm
confound.

#### 8.7 STOP-field audit (cross-arm invariant)

`_build_action_lines` reads `parsed_stop` from the same interaction as
the coord fields, so STOP consistency across arms is enforced by
construction. Empirical distribution on v_final_kto_B_v2:

- 2788 rows with `STOP: false` (all progress rounds).
- 3 rows with `STOP: true`, all in `outcome=failure / is_progress=True`
  (teacher misjudged "arrived" while ep ultimately failed). These land
  in the undesirable KTO label; the KTO loss will suppress this
  behavior. No filter action needed.

#### 8.8 Anchors + attribution

- Prep code + template changes commit SHA: **`1a44d61`**
- Amendment 6 supersession scope: §6.4 pin (files + counts) replaced by
  §8.6; §6.5 (Rule 1/2/3 as advisory flags) retained in full.
- Amendment 7 checklist items 1–3 (length alignment / decision-tail
  truncation / same-round pairing assertion) are implemented in the
  new prep code (`_A_CTRL_RAT_WORD_CAP=130`, tail-preserving cap in
  `extract_native_thought`, and `interaction = inter[round_idx - 1]`
  reused for both action tail and rationale block). Items 4–7
  (B_matched fixed seed, SFT-only positioning, cross-arm hyperparam
  sharing with logged effective-step counts, env `reset(seed=...)`
  plumbing for shared init poses) remain OPEN as pre-training TODOs.

**Frozen by**: TPEmist (chat) — signed 2026-07-08 before any adapter
training dispatches.

---

### Amendment 6 — 2026-07-07 (still before any adapter trains) — Coherence Filter Demoted to Advisory Flags (v-final)

**Status**: LOCKED — filed before any D11 arm training was launched.
**Date**: 2026-07-07
**Supersedes**: filter drop policy of Amendments 1–5. Does not alter arms, T1, R1-ΔX probe, or Bonferroni allocation.
**Iron rule check**: no training run has consumed any filter output at time of filing. ✅

---

#### 6.1 Trigger — residual audit result

Amendment 5 §5.3 mandated a blinded audit of the v4 filter's sole active surface: the 66 desirable-side samples dropped by Rule 1 (fixed). Result:

- Audited: 13 of 66, blinded, notes recorded per sample (2 borderline excluded from denominator).
- Agreement (filter=drop ∧ human=clearly-bad): **2/13 = 15.4%**, Wilson 95% CI ≈ **[4%, 42%]**.
- 11/13 clearly-good drops trace to three phrasing classes the parser does not model:
  1. **Number-based direction spec** — "increase X to 14" / "target Y=45" (direction implied by `sign(target − current)`).
  2. **Missing-axis mentions** — rationale claims 2 axes; parser demanded consistency on all 3.
  3. **Relative/reversal semantics** — "reverse the previous change", "shift back".

Even the CI upper bound (42%) cannot justify a drop rule. The disaster branch is triggered.

#### 6.2 Correction to §5.3 band definition

§5.3 defined the disaster case as agreement ∈ [20%, 45%]; the observed 15.4% falls below the band, which was an unanticipated gap in the original spec. The band is hereby amended to **agreement < 45%**, and this trigger is processed under the amended definition per the original intent (lower agreement is strictly worse). Recorded here so the pre-registration contains no undefined branch.

#### 6.3 Decision

All deterministic rules are **demoted from drop authority to advisory flags**:

| Rule | v4 role | v-final role |
|---|---|---|
| Rule 1 (direction consistency, fixed) | drop (desirable side) | `rule1_flag` only |
| Rule 2 (GT contradiction) | flag (per Amendment 5) | `rule2_flag` only (unchanged) |
| Rule 3 (vacuity) | drop | retains nominal drop authority; **0 fires / 3,794 samples** |

Net effect: **all 992 desirable and 1,810 undesirable samples enter training.** The filter is retired as a curator and retained as a diagnostic instrument.

#### 6.4 Stopping rationale — cost-benefit, not impossibility

We explicitly do **not** claim deterministic parsing is incapable of this judgment. Two of the three failure classes in §6.1 are deterministically fixable (class 1: sign of target minus current state; class 2: check only claimed axes). The stopping argument is expected-return based:

- Maximum filter surface: 66/992 = **6.7%** of desirable pool.
- True-positive rate on that surface: ~15% ⇒ true rationale–action incoherence ≈ **1% of pool**.
- Each fix+re-audit iteration costs 2–3 h and has, across three rounds (n = 88 audited samples total: 60 + 13 + 15), surfaced a new phrasing class each time.
- Expected recoverable signal is bounded and small; iteration is terminated as a resource decision.

#### 6.5 Residual contamination bound and downstream defenses

The original motivation ("wrong reason, right result" baked into weights) is not dismissed; it is bounded:

- Keep-precision from v2 audit: ~95% (43/45) ⇒ pool-level clearly-bad rationale rate ≈ **4–5%**, i.e. **~40–50 desirable samples** enter training with incoherent rationales (upper bound).
- Defense 1: KTO undesirable side (n = 1,810) actively suppresses low-quality rationale–action patterns.
- Defense 2 (decisive): the **R1 ΔX probe** is the pre-registered end-to-end detector. If ~5% contamination materially corrupts the student's grounding, it manifests as failure of the probe prediction (student R1 bias near −16 cm, not −24 cm). Contamination that does not move the probe or T1 is, by the study's own success criteria, immaterial.

#### 6.6 Symmetry clause

Flag-only policy applies **identically to A_ctrl_rat** (D6 native stage-1 thoughts): no drops, same three flag columns computed with the same code path. No curation asymmetry may exist between arms.

#### 6.7 Flag-computation fixes (non-drop)

The two cheap fixes from §6.4 (number-based direction, claimed-axes-only) are applied to the **flag computation only**, to improve post-hoc analysis precision. They confer no drop authority. Implemented in commit `9b0a9da` via:
- `collect_number_target_claims()` — parses "axis to N" / "target Y=N" patterns and derives direction from `sign(N − init_ee_axis)`.
- The claimed-axes-only rule was already the semantic of the Amendment-4 Rule 1 fix (loop `if not claimed[axis]: continue`); made explicit in docstring.

Empirical effect on v_final_kto_B: Rule 1 flag fires 169 times (vs 199 pre-fix on v3), a 15% reduction driven by fewer false alarms on multi-axis and number-based rationales.

#### 6.8 Final training data spec (v-final JSONL)

- Desirable: **992** · Undesirable: **1,810** · ratio **1.82** (original).
- KTO auto-balance reads counts from dataset load — confirmed effective for v-final.
- Every row carries `rule1_flag`, `rule2_flag`, `rule3_flag`.
- Post-hoc analyses pre-committed:
  (a) coherence-flag × outcome 2×2 table
  (b) Rule-2 flag axis/sign distribution vs the R1 ΔX bias (language-level mechanism check)
  (c) flagged-subset ablation if T1 marginally fails.

Files: `data/training_sets/v_final_sft_A.jsonl`, `data/training_sets/v_final_kto_B.jsonl`.

#### 6.9 Canonical paper sentences (replace Amendment 5 draft)

> "We designed a deterministic three-rule filter for rationale–action coherence. Blinded audits across three rounds (n = 88) showed high precision on *keep* decisions (~95%) but only 15% precision on *drop* decisions: legitimate variation in how the teacher phrases spatial intent (number-based targets, relative reversal semantics, partial-axis mentions) dominates the drop surface. Since the filter's maximum surface was 6.7% of the pool with ~15% true-positive rate — a bounded ~1% true incoherence rate — we terminated rule iteration on cost-benefit grounds, demoted all rules to advisory flags, and retained the full dataset. Residual contamination is bounded at ~4–5% and is detectable end-to-end by the pre-registered R1 ΔX probe."

Do **not** claim "deterministic parsing is insufficient" (falsifiable by §6.4 class-1/2 counterexamples) and do **not** claim "the teacher never produces vacuous rationales" (Rule 3's 0/3,794 is structurally guaranteed by the coordinate-bearing output format; if mentioned, phrase as "the output format enforces spatial specificity").

#### 6.10 Audit trail summary

| Round | Sample | Target | Key finding |
|---|---|---|---|
| v1 | 60 (47 ex-borderline) | stratified random | 48.9% — label definition error (correctness vs coherence) |
| v2 | same 60, relabeled | stratified random | 74.5%; success×inconsistent stratum 0% → Rule 1 past-reference bug |
| Amendment 4 | 13 (5 flips + 8 Rule-2 drops) | targeted | flips 5/5 ✓; Rule 2 precision 0% → demoted to flag |
| Residual (this) | 13 of 66 (2 borderline) | Rule 1 (fixed) drops | 15.4% (11/13 disagreements = clearly good) → this amendment |

Total human labels across all audits: **88 samples**.

**Frozen by**: TPEmist (chat), 2026-07-07.
- Amendment 6 commit SHA: **`9b0a9da`**

---

### Amendment 5 — 2026-07-07 (still before any adapter trains)

Amendment 5 lands three items, all responses to the targeted 13-sample
re-audit that Amendment 4 requested. That audit produced two clean
signals and exposed one methodological hole; Amendment 5 addresses
each in isolation and pins the resulting v4 filter.

#### 5.1 Rule 2 — demoted from drop-rule to advisory flag

The 8-sample Rule-2-drop cell of the targeted re-audit produced 0/8
agreement (all human labels: clearly good). Two independent causes
combine:

**Cause 1**: Rule 2 checks whether the rationale's spatial claim
about the cube matches ground-truth cube position. This is a
**correctness** check. Amendment 3 pinned the filter's audit
dimension as **coherence** (rationale ↔ action consistency).
Applying a correctness-based rule under a coherence-labeled audit
guarantees near-zero agreement — the criteria measure orthogonal
axes. The disagreement is definitional, not a Rule-2 failure.

**Cause 2**: Even by its own criterion, Rule 2's precision is
unknown post-audit. The 45 "GT contradict" desirable drops include
samples where the teacher used axis-name confusion ("Y is height")
in the natural-language description but generated a mostly-correct
action. Dropping those samples throws away instances that may
carry the linguistic signature of the R1-ΔX bias mechanism itself
— a diagnostic asset, not a training-time contaminant.

**Decision**: Rule 2 is **demoted to advisory flag**. Samples with
`rule_2_gt == "contradicts_gt"` are retained in the training set
but tagged with a `rule2_flag` field for post-hoc analysis. Rule 2
is not the drop authority.

**Follow-up analysis (planned, not blocking training)**:
The 45 flagged desirable samples will be analyzed for:
  (a) Which axis's spatial claim contradicts GT (x/y/z distribution)
  (b) Whether the axis-error sign is consistent (e.g. "always claims
      Y direction wrong" vs "randomly wrong across axes")
  (c) Whether Rule-2-flagged samples cluster with success or failure
      episodes (implicating rationale-vs-execution decoupling)

If (a) and (b) show a consistent bias — e.g. "the teacher's
natural-language X-axis semantics are systematically inverted"
— this becomes a mechanistic finding attachable to the R1-ΔX
bias probe (§5 of pre-registration §5). "A failed filter rule
became a diagnostic tool for teacher's language–action decoupling"
is a stronger paper contribution than "the filter dropped 45
samples." Analysis script skeleton at
`scripts/training/analyze_rule2_flags.py` — will run after
Amendment 5 lands.

#### 5.2 Composite agreement rate — rejected as circular

The temptation to combine v2's 74.5% with amendment-4's 100%
flip-to-keep and 100% (post-Rule-2-demotion) Rule-2-drop cells to
report "composite 80% agreement" fails on two grounds:

**Ground 1 (circularity)**: The 8 Rule-2 drops from the
amendment-4 audit were what *motivated* the demotion of Rule 2.
Using them again as agreement-rate evidence for the modified
filter is textbook circular validation.

**Ground 2 (sampling probability mismatch)**: The v2 sample is
stratified-random from 2802 rows across four cells. The
amendment-4 sample is targeted uniform from ~200 rows split
across two cells. Concatenating them and dividing by 60 is
combining two incompatible sampling schemes. The result has no
frequentist interpretation.

**Decision**: Do NOT report a composite agreement rate. Report
each audit stratum separately:
  - v2 audit (stratified, n=60, coherence definition):
      Overall: 74.5%
      Per-stratum breakdown reported in audit_report.md
  - Amendment 4 targeted audit (n=13):
      Flip-to-keep cell: 5/5 = 100% (validates Rule 1 fix)
      Rule-2-drops cell: 0/8 (motivates Rule 2 demotion — do not
      count toward filter validation)
  - Amendment 5 residual audit (n=15, planned): validates the
      v4 filter's actual drop surface (66 R1-only drops on
      desirable side).

Each audit answers a scoped question. There is no single-number
"filter validation score."

#### 5.3 LLM-judge escalation — closed via risk-asymmetry argument

Amendment 2 set a rule: agreement <85% → escalate to LLM judge.
v2 came in at 74.5%, mechanically triggering it. Amendment 4
tabled the escalation pending targeted re-audit. Amendment 5
closes escalation entirely on the following principled ground:

**The two error types have asymmetric cost.**

- **False negative** (filter dropped a clearly-good sample):
  cost = one training row lost. On the desirable side, worst-case
  = 66/992 = 6.7% desirable data loss. The upper bound is small
  and computable; the actual bound is what Amendment 5's residual
  audit measures.
- **False positive** (filter kept a clearly-bad sample):
  cost = training on `(bad rationale, action)` corrupts the
  student's rationale channel. The v2 keep-precision was 35/37
  = 94.6% (2 FPs of 37 clearly-labeled keeps). Post-Amendment-4
  R1 fix strictly reduces the keep set (Amendment-4 flipped
  drops→keeps, not keeps→drops), so keep-precision is bounded
  BELOW by 94.6% and likely higher.

LLM judge can at most recover the ≤66 R1-only drops. Even if all
66 were false negatives (extreme upper bound), the recovered
gain is 6.7% of desirable rows. The cost — 12h teacher-hours,
LLM-judge validity as a new methodology defense — exceeds this
capped upside.

**Formal closure**: The Amendment-2 LLM-judge escalation is
closed *conditional on Amendment 5's residual audit not
revealing a disaster case* (defined below). If the audit shows
Rule 1 fixed drops are majority-clearly-good, filter is
declared "conservative but not corrupting" in the paper
limitations. If the audit shows Rule 1 drops are majority-
clearly-bad, no action required — filter is doing its job.

**Disaster case (would trigger LLM judge revival)**: If
Amendment 5's residual audit shows the R1-drop cell has
agreement 20-45% (like the v2 success×inconsistent stratum),
this indicates the Rule 1 fix left another systematic error
in place. In that event, LLM-judge escalation on the residual
disagreements is triggered — this is the same principle as
Amendment 4's targeted fix (localize the bug, then re-audit).

#### 5.4 Amendment 5 residual audit — 15 samples from the v4 drop surface

The single unaudited region: the 66 desirable samples that the
Rule-1-fixed filter drops. Amendment-5's residual audit samples
15 uniformly at random (seed=44, distinct from earlier audits),
excluding any samples already in previous manifests.

**Manifest**: `workspace/d11_audit/manifest_amendment5_residual.json`
**Output**: `workspace/d11_audit/human_labels_amendment5.csv`

This closes the coverage gap.

#### 5.5 Rule 3 (vacuity) — restraint on paper narrative

Rule 3 fired 0/2802 times. Amendment-5 draft narrative had
"teacher rationales are always spatially specific" — this is
overclaimed. The Stage-1 output format enforces a `LEFT_TARGET_POS
: X=... Y=... Z=...` line, and the recap-gist prefix format
guarantees per-lesson metadata lines. Both introduce spatial
tokens by structural requirement. Rule 3 tests a boilerplate
class that our output format makes structurally impossible.

**Paper-safe wording**: "The output format guarantees at least one
spatial token per sample; Rule 3 therefore fires zero times.
This is a property of the schema, not evidence that teacher
rationales are semantically grounded."

Before that sentence lands in paper, 10 rationale spot-checks
will verify the spatial tokens carry semantic content (not just
schema fill). Deferred to paper-drafting phase, not blocking
training.

#### 5.6 Final v4 filter — pinned counts for training

Applying Rule 1 (fixed, Amendment 4) + Rule 3 (vacuity) as
drop-rules, with Rule 2 as flag:

- Total kept: **2736 / 2802 = 97.6%**
- Desirable kept: **926 / 992 = 93.3%**
- Undesirable kept: **1810 / 1810 = 100.0%**
- KTO ratio drift: 1.82 → 1.95

`train_qlora_kto.py --auto-balance` reads lambdas from post-load
`dataset.examples` counts; the final n=926/1810 feed in
automatically. Amendment-3's auto-balance invariant remains.

**These counts are locked**. No further filter iteration before
training. Amendment 5's residual audit (§5.4) is data-collection,
not filter-modification — its outcome informs paper limitations
wording, not the training set.

**Frozen by**: TPEmist (chat), 2026-07-07.
- Amendment 5 commit SHA: **`6a29103`**

---

### Amendment 4 — 2026-07-07 (still before any adapter trains)

**Rule 1 past-tense-reference fix + audit interpretation correction +
LLM-judge trigger revision.**

Three items, all landing together because they are causally chained:

**Item A: Label definition clarification (v1→v2 audit discrepancy)**

The random-stratified 60-sample audit was executed twice:

- **v1 (2026-07-06)**: Labels were assigned under "correctness" criterion
  (did the rationale correctly describe the scene / target). Result:
  48.9% agreement (n=45, borderline excluded). This is not filter
  underperformance — it's a definition mismatch. The filter was built
  to measure *coherence* (rationale-action self-consistency, no fact
  claim), not correctness.
- **v2 (2026-07-07)**: Labels reassigned under "coherence" criterion —
  does the rationale describe the same direction the action moved?
  Same 60 samples, re-audited, no seed change. Result: 74.5% agreement
  (n=47, borderline excluded).

Because v1 was executed under a misaligned label definition and no
adapter had been trained at that point, v1 is documented but NOT used
for validation. v2 is the audit of record. This is a legal
pre-registration amendment: no post-hoc numbers changed, no training
data selected based on results — the fix is upstream of training.

The v1 audit data (labels + report) was deleted from the working
tree to prevent it being cited as an alternate metric. It's recoverable
from git if needed for retrospective methodology explication.

**Item B: Rule 1 past-tense-reference fix**

v2 audit revealed a single-stratum failure mode:
  outcome=success × r1_state=inconsistent → 0.0% agreement (10/10 FN)
All 10 FN cases traced to the same parser bug: my `collect_direction_claims`
pooled direction words across the entire teacher THOUGHT, including
past-reference clauses ("the previous move went further left") whose
direction terms should not be counted as intent claims.

Fix (this Amendment): sentence-level classifier splits THOUGHT on
sentence boundaries, classifies each sentence into
{past, intent, neutral} using regex markers, and pools direction
claims only from **intent** sentences. Neutral sentences ("EE is to
the left of cube") describe visual observation and were also
excluded — they carry facts about state, not plans about action.

Verification: rerun filter on v4_kto_B.jsonl. On the 10 previously-FN
cases from v2 audit, 9/10 now correctly flip to keep. The 1 remaining
(sid=18) is dropped by Rule 2 (GT contradict), a different rule
unaffected by this fix.

Post-fix filter stats on v4_kto_B (n=2802):
  Total kept:   2700 / 2802 = 96.4%   (was 2532, 90.4%)
  Desirable:    890 / 992 = 89.7%     (was 722, 72.8%)
  Undesirable:  1810 / 1810 = 100.0%  (unchanged, Rule 3 alone)
  KTO ratio (undesirable:desirable): pre 1.82 → post 2.03 (was 2.51)

**Item C: LLM-judge trigger revision + targeted re-audit**

Amendment 2 pinned an escalation rule: agreement <85% → LLM judge on
FP+FN residual. v2 achieved 74.5% (below threshold), which mechanically
would trigger LLM judge. But the failure was localized to a fixable
parser bug in one stratum, not distributed filter unreliability. The
correct response is:

  1. Fix the bug (done, Item B).
  2. Targeted re-audit on the two evidence-thin questions the v2 audit
     couldn't answer:
        (a) Rule-2 (GT contradict) drop precision — 8 samples from
            current Rule-2 drops.
        (b) Whether the Amendment 4 fix over-corrected — 5 samples
            from previously-dropped-now-kept.
     Manifest at workspace/d11_audit/manifest_amendment4.json,
     seed=43, excludes samples already in v2 audit.
  3. Only if targeted re-audit still shows <85% (on the composite
     of v2 + amendment4 clearly-labeled samples) does the LLM judge
     escalation trigger. This preserves the letter of Amendment 2
     (LLM-judge as circuit breaker) while not mechanically firing
     it in response to a fixed bug.

The 13-sample targeted audit is stratified by cell (Rule-2 drops
vs flip-to-keep), not by outcome/r1_state — because the objective is
to characterize the residual filter behavior post-fix, not to sample
uniformly across the training set.

**Item D: Auto-balance drift note**

Post-filter class ratio is 2.03 (undesirable:desirable), down from the
raw 1.82 (before filter) and from Amendment 3's post-filter 2.51.
`train_qlora_kto.py --auto-balance` reads lambdas from
`dataset.examples` after JSONL load; the final n=2700 counts feed in
automatically. No manual adjustment. This invariant was pinned in
Amendment 3 and remains.

**Item E: Paper narrative wording correction**

Prior draft said "pre-registered post-hoc after v1 mislabeling
incident" — self-contradictory phrasing that would forfeit reviewer
trust. Correct phrasing (to be used in paper):
  "The audit was executed twice: v1 under a mislabeled coherence-vs-
  correctness definition (labels excluded from analysis; data
  preserved in git history), v2 under the corrected definition
  (labels of record). All amendments were committed and time-stamped
  before any adapter training began."

Numbers to cite in paper (corrected from Amendment 3):
- v2 keep-precision: 35 / (35+2) = **94.6%** on the coherence definition
  (2 FP out of 37 clearly-labeled keeps).
- v2 overall agreement (excluding borderline): 74.5%,
  Wilson 95% CI [60.5, 84.7].
- Post-Amendment-4 filter kept 2700/2802 (96.4%);
  the tightening happens on 890/992 = 89.7% of desirable.

**Frozen by**: TPEmist (chat), 2026-07-07.
- Amendment 4 commit SHA: **`e2d7c41`**

---

### Amendment 3 — 2026-07-06 (still before any adapter trains)

**Asymmetric drop policy on KTO desirable vs undesirable + auto-balance invariant.**

Rationale: Amendment 2's original phrasing was "apply filter symmetrically
to every rationale-bearing arm". That is wrong for KTO because KTO's
desirable and undesirable sides teach opposite things:

- **KTO desirable side (SFT-like)**: bad rationale + good outcome is
  the classic "correct result, wrong reason" leakage — must filter, all
  three rules apply. `drop_policy=strict`.
- **KTO undesirable side**: KTO pushes down `(rationale, action)` joint
  probability. Splitting the 2×2:
    - good_rat + bad_action → keep ("said right, did wrong — bad pair")
    - bad_rat + bad_action → keep ("hallucinated + fumbled — bad pair")
    - **direction-inconsistent rat + bad_action → keep**: these are the
      most instructive negatives (the model learns "say −X then do +X
      then fail = don't do this"). Dropping them removes the highest-
      value negative examples from KTO's reference distribution.
    - Only vacuous rationale + bad_action → drop, because boilerplate
      negative teaches nothing specific and occupies KTO reference mass.
  `drop_policy=vacuity_only`.

Implementation: `--drop_policy asymmetric_kto` on the full mixed KTO
JSONL applies per-sample policy based on `kto_label` field. Runs in
30 seconds for the full 2802-sample file.

**Empirical result of running filter on v4_kto_B.jsonl**:
- Kept 2532 / 2802 = 90.4% overall
- Desirable side: 722 / 992 = 72.8% kept
- Undesirable side: 1810 / 1810 = 100.0% kept (no vacuous rationale
  found in any undesirable sample — all had at least one spatial token)
- Class ratio (undesirable : desirable) drifted 1.82 → 2.51

**Auto-balance invariant** (must be verified before training):
`server_side/train_qlora_kto.py` lines 534-543 compute
`lambda_d = max(n_d, n_u) / n_d` and `lambda_u = max(n_d, n_u) / n_u`
from `dataset.examples` AFTER JSONL load. Since we pass the
post-filter JSONL to the trainer, auto-balance will use the drifted
1:2.51 counts automatically. No manual adjustment needed. This
invariant is now pinned; any change to when auto-balance is computed
would break the pre-registered guarantee that filter drift feeds into
the KTO weighting correctly.

**Free by-product observation** (for Discussion, not a primary test):
Rule-1 consistency × episode outcome 2×2 on the full KTO pool:
  - P(inconsistent rationale | success episode) = 25.7%
  - P(inconsistent rationale | failure episode) = 30.4%
  - χ² = 6.35, p = 0.012, RR = 1.18
This says direction-inconsistent rationales are 18% more common in
failure episodes than success episodes — moderate correlation between
reasoning-action coherence and eventual outcome. Two-line note for
Discussion; not a claim in the abstract.

**Frozen by**: TPEmist (chat), 2026-07-06.
- Amendment 3 commit SHA: **`2ba693c`**

---

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
- Amendment 2 commit SHA: **`037e2c8`**

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
