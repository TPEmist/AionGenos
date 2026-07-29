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

## 5. Results (L2) — PLACEHOLDER

*Pending isaac Stage-1 eval (A_ctrl_rat + C_retrieval, n=100) and its
audit-log verdict. To be translated mechanically from isaac's analysis
package per the session split — paper does not self-interpret the numbers.
Fill: (i) per-arm baseline SR (→ pins the MDE from §4.4's formula);
(ii) C_retrieval − A_ctrl_rat contrast (McNemar/z, direction + significance
vs the pinned α=0.010); (iii) R1 (ΔX_L, ΔX_R) per-arm signature vs the L2
teacher fingerprint; (iv) conditional-expansion criterion outcome
(Amendment 2) — headline-secured vs diagnosis branch.*

## 6. Discussion (L2 additions) — PLACEHOLDER

*Slots already drafted elsewhere, to fold in once Results land:*
- *Cross-task replication (or not) of the marginal/conditional split —
  connects to D11 §5.1.*
- *Success-floor boundary condition (v1.1_notes.md): the marginal/
  conditional criterion presupposes the teacher clears a task-competence
  floor; L2 at 1% joint SR sits near it. "You cannot externalise a
  competence the teacher does not have."*
- *Contact-rich extension boundary is already written as §5.3
  (two-boundary anatomy: contact-precision ceiling + primitive-expressivity
  gap), independent of the L2 numbers.*

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
