# L2 Methods — draft skeleton (v1.1)

*Mechanical translation of the L2 pre-registration chain (l2_prereg.md +
Amendments 1/1a/2/3, all frozen before any L2 eval number). Same
discipline as D11 Methods: every design choice traces to a pre-reg
section or a numbered, dated, SHA-anchored amendment. This is the
**skeleton**: the Methods that are a pure translation of the plan are
written now; Results/Discussion are left as placeholders pending isaac's
Stage-1 two-protocol eval and its audit-log verdict. Per the session
split, paper translates isaac's audit documents and does not
self-interpret numbers — including numbers mentioned only in passing in
an amendment's provenance block (those await the formal analysis package).*

*Scope note: L2 reuses the entire D11 apparatus (teacher/memory pipeline,
LoRA recipe, seed-paired design, McNemar/z machinery, `flags_only_a6`
filter) unchanged. §§ below pin only what is NEW or task-specific for L2.
Cross-references "D11 §3.x" point to the frozen v1.0 Methods.*

---

## 4. Methods (L2 extension)

### 4.1 Task: dual-arm 6-DoF pose-reach (Amendment 1 §2)

L2 is a **dual-arm position-goal reaching task in a 6-DoF control space**
(renamed from the working title "dual_push"; Amendment 1 §2). Both
end-effectors are actuated toward per-arm goals — `left_ee_pose` /
`right_ee_pose` command tracking under `end_effector_position_tracking`
rewards; the goal cubes are target visualizers, not pushable objects
(l2_diagnosis.md Step 1). **Naming discipline (Amendment 3 §4):** although
the control space is 6-DoF and the state carries RPY, the trained output
slot and the success gate are **position-only** (‖EE−target‖ < 0.05 m; no
RPY term is scored). The paper must not let "6-DoF / pose" imply a
rotational success dimension that is not measured — hence "position-goal
reaching in a 6-DoF control space", not "6-DoF pose-reach". The paper
wording is otherwise fixed as **"a second, harder task in the same
primitive family"** — not "push", not "a different skill"; a genuine push
(cube as a tracked, displaceable object) is L3 scope. This is the harder
second task on which the D11 headline is tested for cross-task replication.

### 4.2 Per-arm scoring (Amendment 1 §1) — disclosed post-hoc

Joint success (both arms within tolerance simultaneously at episode end)
was **1/100** on the L2 collect; per-arm success was **28/100 left,
28/100 right**. The joint metric compounds two ~28% events down to ~1%,
so the primary L2 metric is **per-arm** success. Promotion of per-arm
scoring to primary is stated plainly as a **post-hoc** change (Amendment
1 §1, same immunisation standard as D11 Amendment 14): its motivation is
a *structural* discovery about the success definition, not selection on a
protocol result — no L2 arm was trained or evaluated at filing time. The
joint-success SR is still reported as the originally-registered metric;
per-arm is *added, not substituted*.

- **A per-arm episode is desirable for arm X** iff arm X's end-effector
  reached its pose goal (best-in-episode ‖EE−target‖ < 0.05 m, the
  registered threshold) → ~28 desirable-arm instances per arm.
- **SFT target** = the progress-rounds of the desirable arm, canonical
  action lines emitted **single-arm** (only the scored arm's target line +
  STOP), so the SFT target matches what a single-arm-scored student should
  emit; the non-scored arm's outcome is recorded as a flag
  (`other_arm_reached`), not folded into the target.
- **KTO pairing** is per-arm-instance: desirable = the scored arm's
  progress-rounds in arm-reached episodes, undesirable = its rounds in
  arm-failed episodes — mirroring D11's desirable/undesirable split, one
  arm at a time. Both arms contribute instances (left-scored and
  right-scored episodes both enter the pool).

### 4.3 Buffer re-tag: arm-aligned success-floor (Amendment 1a)

The 100 L2 recaps were tagged `is_success` by JOINT outcome at collect
time (1 True / 99 False). Full-population re-score: 46/100 episodes have
≥1 arm reaching goal, of which **45 carry `is_success=False` despite
holding a goal-reaching arm trajectory** — so under per-arm scoring the
buffer's labels are wrong for ~45% of episodes, and the naive fix
(`is_success = left OR right`) reintroduces cross-arm contamination (a
"right-reached, left-failed" episode whose failure lesson is about the
LEFT arm would be served as a success to a LEFT-arm student). Fix, two
minimal layers:

1. **Data layer** — each recap gains `left_reached` / `right_reached`
   bool fields from replay GT (re-score in
   `workspace/l2_audit/per_arm_rescore.json`); joint `is_success` kept for
   reference. Retrieval *similarity is untouched* (image + full-state
   anchor as before).
2. **Retriever logic** — the success-floor FILTER reads the label
   corresponding to the arm the student is currently scored on
   (`left_reached` when the canonical action line is the left arm's, else
   `right_reached`), a lookup of an existing per-round variable, not new
   retrieval logic.

Disclosed residual (one-line paper limitation): *lesson text remains
episode-level natural language and may reference either arm; only the
success-floor label is arm-aligned, not the lesson prose.* Order of
operations was locked (Amendment 1a): re-tag → 3–5-line retriever change →
re-pin buffer SHA → **then** C_retrieval-L2 unlocked. Pins recorded:
pre-retag tree-hash `83337879…`, post-retag `a79581cd…`, 100/100 recaps
dual-labelled. The teacher's joint-labelled *growing* buffer vs eval's
re-tagged *frozen* buffer asymmetry is disclosed in
l2_memory_world_asymmetry.md.

### 4.4 Scope: L2 tests the answerable question (Amendment 2)

L2's desirable pool is 56 per-arm episode-instances (vs L0a's 992). The
two D11 headlines have opposite detectability at this n; L2 therefore
tests **one** question, not a symmetric 2×2 (Amendment 2):

- **T4-class (identical-weights retrieval, C_retrieval − A_ctrl_rat)** —
  D11's strongest result (+34 pp, z=5.15). At L2 baseline ~15%, power at
  n=100, α=0.010 is **76% (+20 pp) / 99% (+30 pp) / 100% (+34 pp)**.
  Detectable — this is the question L2 can answer.
- **T1-class (bake-in)** — L0a effect +1 pp; L2 MDE at α=0.020, n=100 is
  **12–13 pp**. A ~1 pp effect on a 12 pp-MDE instrument with 1/17 the
  training data is a guaranteed uninformative null. **Not run on L2** —
  stated as an MDE-driven *design choice* (the ① lesson used
  prospectively to decide what not to run), not an omission.

**Stage 1** (the window's scope): train ONE adapter, **A_ctrl_rat**, on
all 56 desirable episode-instances. Training adequacy (distinct from eval
power — not conflated): the 56 desirable episode-instances expand to
**511 desirable / 1119 undesirable per-arm ROUNDS** (KTO trains on
rounds; SFT = 511 behavior-cloning rounds, KTO = 511 + 1119). Two eval
protocols: A_ctrl_rat bare + C_retrieval (A_ctrl_rat's weights + frozen
re-tagged buffer, `success_label_arm='left'`). Primary L2 contrast =
**C_retrieval − A_ctrl_rat** (identical-weights), two-sided, McNemar/z per
the D11 machinery.

Conditional-expansion criterion (pinned pre-data, Amendment 2): if
C_ret − A_ctrl_rat is significant and same direction as L0a → cross-task
headline secured, then optionally add A_action_only (Stage 2) for the L2
"rationale tax"; D_gist not run in either stage. If not significant or
reversed → that is itself a finding (the effect does not cross tasks), and
the response is DIAGNOSIS, not more arms.

Paper claim locked a half-grade down: **"the identical-weights retrieval
effect replicates on a second, harder task in the same primitive
family"** — not "the full 2×2 replicates".

### 4.5 Per-arm evaluation: single-arm inference matches single-arm training (Amendment 3)

*Mechanical translation of `l2_amendment_3.md` (decided 2026-07-22 before
any L2 eval number existed; re-filed to master 2026-07-28). Amendment 1 §3
defined the per-arm **training** target (scored arm only); Amendment 3
completes the **eval** side to match, under the principle applied
throughout the program: **the student is evaluated in the shape it was
trained to emit.***

The eval was initially wired to parse, step, and gate on **both** arms
(`_active_arm_for_level("L2_dual_push") → None`), i.e. the joint
definition that produced SR = 1/100 and motivated the per-arm re-score.
Asking a single-arm-trained model to emit both arms measures
*format-adaptation, not task competence* — an out-of-distribution probe.
The per-arm eval resolves this:

1. **Prompt** asks for the scored arm's slot only, matching the training
   target in structure (position-only, no RPY line, no non-scored-arm
   line).
2. **Non-scored arm frozen at its initial pose** via the existing V4
   `active_arm` hold-in-place mask.
3. **Success gates on the scored arm only** (‖EE_scored − target_scored‖
   < 0.05 m), reusing the L0a single-arm success branch.

**Freezing the non-scored arm is a structural advantage, not a
workaround (§2.1).** A left-scored L2 episode (left moves, right frozen)
is *isomorphic to the L0a-Left layout*, making the L2↔L0a cross-task
comparison cleaner — the same single-active-arm control structure on a
harder task. **Disclosed delta (honest):** at training time the
non-scored arm was in motion; at eval it is frozen. This is defensible
for pose-reach *specifically* because the two arms drive to two
**separate** goals with minimal inter-arm coupling, so freezing one does
not change the physics the scored arm must solve; it would **not** be
defensible on a contact-coupled cooperative task — which L2 is not (§4.1
naming).

**Scope: main eval = LEFT-scored only, 2 protocols × n=100, seed_base
4600 shared** (paired McNemar design preserved). Left-only is a *scope
decision, not a compute shortcut*: Amendment 1a already anchored the
retrieval side to the left arm (`success_label_arm='left'`, retrieval
query keyed on the initial left-EE state), so a right-scored C_retrieval
would need a *different retrieval anchor* — a new degree of freedom and a
new amendment, which L2 does not open. The left-scored contrast is a
complete, valid test of the identical-weights retrieval question
(Amendment 2). Right-scored eval, if ever run, is restricted to an
**exploratory bare-arm re-check** (A_ctrl_rat only, no anchor change),
after the main numbers and only in idle windows — explicitly not part of
the confirmatory contrast.

### 4.6 Analysis rules (carried from D11 §3.6, per-arm generalisation)

Unchanged in form from D11 (two-timestamp discipline; pairing-integrity
gate → McNemar primary on pass, two-proportion z on fail; all tests
two-sided). L2 generalisations, pre-specified in l2_analysis_adaptation.md
(Debt #1 dry-run, timestamped before any L2 five-protocol result):

- **Success gate** generalises to per-arm: `outcome=='success'` extraction
  reads the scored arm's `dist_red < thr` (already in collect.py
  `active_arm=None` branch); binary success-count machinery unchanged.
- **Pairing gate**: seed-based init fingerprint now includes both arms
  (richer `allclose`, still valid). L2 eval seed base = **4600** (shared
  across both protocols → episode *k* starts from the same world config
  in A_ctrl_rat and C_retrieval; paired design, Amendment 3 §3), distinct
  from the collect base 4500.
- **R1-bias probe (L2)** — pre-specified redefinition (§4.7).

### 4.7 R1-bias probe, L2 redefinition (l2_analysis_adaptation.md, locked pre-data)

The L0a R1 probe measured the round-1 lateral (X) bias of the single
active arm. For L2 the pre-registered equivalent is the **per-arm round-1
signed displacement toward each arm's own target, reported as a
two-component vector (ΔX_L, ΔX_R), plus a pooled magnitude ‖ΔR1‖** (mean
over both arms of |round-1 target − init EE| along the task-relevant
axis). The marginal-vs-conditional test R1 served in L0a carries over
unchanged in form (does the distilled arm's per-arm R1 collapse to a
static prior while retrieval's varies per episode?). References are the
**L2 memory-teacher's own** R1 distribution (task-matched, measured from
the L2 teacher buffer), **not** the transplanted L0a −23.5/−15.8 cm
fingerprints. Locked now so it is not a picked metric post-results.

### 4.8 Pipeline integrity (verify-layer interceptions, carried from D11)

The D11 Step-2 row-count sentinel and SHA gates carry over. Recorded for
the Methods "pipeline integrity" note: the L2 run exercised the verify
layer twice more (interception rate 3/3 across the program) —
(i) the per-arm SFT pool lives almost entirely in the `failure/` replay
dir (joint-success 1/100), so pool selection is by per-arm *label*
(`--sft_desirable_only`, kto_label=='desirable') reading BOTH dirs, not by
directory; the sentinel caught a would-be training-semantics error (1119
failed-arm rounds nearly behavior-cloned as desirable), not a miscount
(Amendment 2 addendum 2026-07-16); and (ii) a version-drift in the GGUF
conversion toolchain transposed the LoRA storage layout, caught at the
GGUF-load verify gate and fixed by version rollback + a structural arch
byte-patch — not by hand-transposing tensors, whose danger is a load that
succeeds but silently mis-maps (Amendment 2 addendum 2026-07-21). Methods
sentence for each is in l2_amendment_2.md.

A fourth interception (Amendment 3 §7) closes a recurring family: the L2
eval initially parsed both arms for a single-arm-trained model — the
fourth train/eval output-format mismatch caught in the program, but the
fourth caught *reactively* (crashing at episode 1). The permanent fix is
a **format-contract assert** resident in the driver *before* any eval
collect: verbatim training-target rows from the SFT JSONL are fed through
the eval parser configured exactly as eval will configure it (control
mode + variant + `scored_arm`), and every row must parse clean. A
single-arm target fed to a both-arms parser fails this at dry-run — the
whole bug family dies before the simulator boots. This makes the
train/eval-contract interception rate 4/4 and, from here, prospective
rather than reactive.

---

## 5. Results (L2)

*Mechanical translation of `l2_confirmatory_report.md` (isaac, verdict
authority bound to `PRE_ANALYSIS_LOCK.md`, committed `65d70c1` before any
p-value). Every claim below is on that report's §4 "may say" list; the
verdict is translated, not re-interpreted. Confirmatory analysis:
`scripts/analysis/l2_confirmatory.py`; run_ids A_ctrl_rat=`8384a740`,
C_retrieval=`2154e57e`, L2-teacher=`a6e6c917`.*

### 5.1 Confirmatory contrast — the identical-weights retrieval effect

Per-arm eval (Amendment 3: left-scored, n=100 paired, seed_base 4600):

| protocol | successes / n | SR |
|---|---|---|
| A_ctrl_rat (bare) | 14 / 100 | 14% |
| C_retrieval (same weights + frozen re-tagged buffer) | 20 / 100 | 20% |

The identical-weights contrast is **C_retrieval − A_ctrl_rat = +6.0 pp**
(Newcombe 95% CI **[−4.5, +16.4] pp**). Primary test: two-proportion
z = 1.129, **p = 0.259, n.s.** at the pre-registered α=0.010 (T4-class).
The paired McNemar was the intended primary; the pairing-integrity gate
fell back to z per Amendment 14 §14.2 (§5.2), and McNemar's discordant
cells (9 vs 3) give the same n.s. conclusion.

**Locked verdict (verbatim from the pre-analysis lock):** *the point
estimate is below the pre-registered MDE (+20 pp for 76% power, Amendment
2); the direction agrees with L0a; the confidence interval simultaneously
admits zero and a moderate effect.* Per Amendment 2's pinned rule, a
sub-MDE point estimate triggers the **diagnosis branch** (§5.3), not more
arms — and the +6 pp result was predicted n.s. in advance and is. We do
**not** call +6 pp a positive replication of the effect *size*; it is n.s.
and sub-MDE. What replicates is examined mechanistically below.

### 5.2 Pairing integrity (why z, not McNemar)

The environment seed was identical across the two protocols on 100/100
episodes, and the frozen right arm (Amendment 3 hold-in-place) matched at
integer + RPY resolution on 94/100. The float fingerprint gate (ε=1e-4)
failed on 17 episodes at ~1e-4 drift because `trajectory[0]` is already
one servo-step in and the scored (left) arm's differing first action
perturbs the shared-sim float state. Pairing is *physically real but not
machine-verifiable from the persisted replay*, so the mechanical rule
(Amendment 14 §14.2) selected the two-proportion z — the same fallback
D11 disclosed, and n.s. either way. No discretion was exercised.

### 5.3 Diagnostic appendix — why the effect is small, not absent

Three pre-registered diagnostics, each prediction committed before its
result; all three findings are **exploratory** and none is a sole-cause
claim (report §3, §4).

**(a) Retrieval quality — a cross-task correlate (n=2 tasks, not a
within-task predictor).** L2 retrieves systematically less-similar
neighbours than L0a under an identical retriever (top-1 median 0.900 →
0.870, MW p=4.7e-17; top-3 0.883 → 0.827, p=1.3e-26), consistent with a
5.5× thinner buffer (547 vs 100 recaps, ~28 usable left-aligned). Stated
at the level it holds: *the L2 attenuation is consistent with reduced
buffer coverage* — a correlation across two tasks, not a causal "∝", and
explicitly **not** the claim that match quality predicts which L2 episodes
succeed (see (c), where it does not).

**(b) Retrieval restores the teacher's round-1 bias.** Round-1 left-arm
lateral bias ΔX_L (against the L2-teacher's *own* R1, not L0a's
transplant): teacher −17.1, A_ctrl_rat (distilled) **−4.8**, C_retrieval
**−17.2**. The pre-registered σ test did not fire (σ 15.5 vs 17.3,
F=1.25 — reported plainly); the informative signal is the **mean**:
distillation collapses to a magnitude-deficient prior (~28% of teacher
displacement), and the retrieval preamble on identical weights restores
the teacher's magnitude almost exactly (−4.8 → −17.2 ≈ −17.1). This is the
L2 analogue of the L0a static-prior collapse (D11 §4.3), on the mean axis
(mean finding post-hoc/exploratory; σ test was the registered one).

*Exploratory cross-task note — even the marginal transfer appears
dose-dependent.* On L0a the distilled arm's R1 sat on the teacher's
(−16.7 ≈ −15.8); on L2 the distilled prior reaches only −4.8 against
−17.1 (~72% short). The ready candidate is training dose (L2's per-arm
distillation saw 56 episodes / 511 rounds vs L0a's 992), suggesting
**marginal transfer is cheap but not free** — below some data floor even
the static prior is under-learned. Labelled exploratory (n=2 tasks, a
single before/after point, no dose-response curve).

**(c) Rescue is gated by start distance, not memory match (surprise).**
The +6 pp = 9 rescues (C✓A✗) − 3 regressions (A✓C✗). Rescues share a
sharp init-pose signature: rescue init `dist_red` mean 13.9 cm vs
both-fail 21.6 cm (MW z=−3.88, p=1e-4) — retrieval rescues almost only
episodes that start close. Rescue retrieval-similarity is *not* higher
(0.847 vs 0.868, p=0.03), so start distance, not match quality, is the
decisive within-L2 variable.

**Synthesis (licensed for the combined picture).** The identical-weights
retrieval effect replicates on L2 in **mechanism** (the R1 correction, (b))
and in **direction** (+6 pp), but its conversion to end-task success is
**competence-gated**: the retrieved correction is injected **once per
episode** (anchored on `init_L_EE`, round-0 only — verified literal, not
metaphor), biasing the initial direction with nothing re-aiming it
mid-trajectory, so it converts only where the start is already within
reach of the 0.05 m gate (c). Far-start episodes fire the correction yet
miss the goal. The effect is therefore **small (+6 pp, n.s.), not
absent.** Two levels, kept separate to pre-empt the "similarity explains
attenuation but not rescue" objection: *between tasks* (a, n=2) thinner
buffer co-occurs with a smaller effect (its **size**); *within L2* (c)
conversion is gated by start distance (its **incidence**).

### 5.4 Headroom-normalized cross-task framing (post-hoc, exploratory)

Raw pp understates the effect across tasks of different achievable
headroom. On a gap-to-teacher basis, L0a retrieval closed ≈100% of the
parity gap; **L2 retrieval closes 42.9%** of the per-arm gap (A_ctrl_rat
14% → L2 per-arm teacher **28.0%**, pinned from `per_arm_rescore.json`;
headroom 14 pp, +6 pp recovered = 6/14). This framing is **post-hoc /
exploratory** (introduced after the raw SR was known); pinning the 28.0%
denominator removes the "≈", not the exploratory label, and the raw
+6 pp n.s. is always reported alongside.

## 6. Discussion (L2 additions)

*To fold into §5 (Discussion) alongside the D11 material; every claim
bound to the report's §4 list. Connects three ways:*

- **Cross-task replication of the marginal/conditional split (D11 §5.1).**
  L2 corroborates the *mechanism* — distillation transfers a
  magnitude-deficient marginal prior (R1 −4.8), retrieval on identical
  weights restores the teacher's conditional correction (−17.2 ≈ −17.1) —
  while the end-task effect stays sub-MDE (+6 pp, n.s.). The substrate
  story replicates in mechanism and direction; the effect *size* does not
  reach significance on this harder, thinner-buffer task, and we say so.
- **Marginal transfer is dose-dependent (exploratory extension of §5.1).**
  L2's ~72%-short marginal (§5.3b) adds a dimension to the marginal/
  conditional frame: even the static prior has a data floor below which it
  is under-learned — cheap but not free.
- **The memory success-floor / minimum-viable-competence law
  (v1.1_notes.md).** L2 at 1% joint SR sits near the floor: memory
  conditions the correction but does not manufacture the multi-step
  competence to execute it from far configurations (§5.3c). *You cannot
  externalise a competence the teacher does not have* — here sharpened to
  *retrieval sets the initial direction; whether that cashes out depends on
  how far the corrected trajectory still has to travel.*
- **Two-paper thread (one sentence).** This dovetails with D11's
  recovery-timing null: both datasets say retrieval's value is
  **front-loaded** — it sets the initial direction (L2's start-distance
  gate is its range limit; D11's monotonic-from-R1 convergence is its
  timing signature).
- **Contact-rich extension boundary** is already written as §5.3
  (two-boundary anatomy: contact-precision ceiling + primitive-expressivity
  gap), independent of the L2 numbers.

*Pending isaac's revised report (two items flagged for sync): (i) the
two-levels separation (coverage=between-task size correlate vs
start-distance=within-task conversion gate) may gain a sharper statement;
(ii) the "marginal transfer is dose-dependent" sentence may be refined.
Both are already reflected above at the current report's wording; re-sync
on the revision.*

---

## Appendix — L2 amendment chain (extends D11 Appendix A1)

| # | Date | Change | Anchor |
|---|---|---|---|
| L2-1 | 07-15 | Per-arm scoring (post-hoc, disclosed); SFT single-arm target; task rename | l2_amendment_1.md |
| L2-1a | 07-15 | Buffer re-tag (dual label) + arm-aligned success-floor; pins 83337879→a79581cd | l2_amendment_1.md §1a |
| L2-2 | 07-15 | Scope to answerable question (T4-class only); Stage-1 A_ctrl_rat; T1 not run (MDE design choice) | l2_amendment_2.md |
| L2-2 add | 07-16 | Per-arm SFT pool selected by label not directory (verify-layer 2/2) | l2_amendment_2.md |
| L2-2 add | 07-21 | GGUF conversion version-drift caught at load gate; rollback + arch byte-patch (verify-layer 3/3) | l2_amendment_2.md |
| L2-3 | 07-22 (decided) / 07-28 (re-filed to master) | Per-arm EVAL: single-arm inference matches single-arm training; non-scored arm frozen; left-scored ×2 protocols n=100, seed 4600; position-only success; format-contract gate (verify-layer 4/4) | l2_amendment_3.md (`5447112`; orig `6cf31b7`) |

*L2-3 note: decided 2026-07-22 before any L2 eval number existed
(Step-8 crashed at episode 1 on a missing `POSITION_RPY_2DOF` template);
first committed as a stray `6cf31b7` on `paper-v1.1-wip`, re-filed to
master as `5447112` in the 2026-07-28 worktree untangle. Pre-result
timestamp integrity rests on the 2026-07-22 conversation record + the
`6cf31b7` commit time, both preceding the eval restart.*
