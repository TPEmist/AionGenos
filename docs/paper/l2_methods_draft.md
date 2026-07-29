# L2 Methods — draft skeleton (v1.1)

*Mechanical translation of the L2 pre-registration chain (l2_prereg.md +
Amendments 1/1a/2, and — pending — isaac's Amendment 3). Same discipline
as D11 Methods: every design choice traces to a pre-reg section or a
numbered, dated, SHA-anchored amendment. This is the **skeleton**: the
Methods that are a pure translation of the (already-frozen) plan are
written now; Results/Discussion are left as placeholders pending isaac's
five-protocol → (Stage-1: two-protocol) eval and its audit-log verdict.
Per the session split, paper translates isaac's audit documents and does
not self-interpret numbers.*

*Scope note: L2 reuses the entire D11 apparatus (teacher/memory pipeline,
LoRA recipe, seed-paired design, McNemar/z machinery, `flags_only_a6`
filter) unchanged. §§ below pin only what is NEW or task-specific for L2.
Cross-references "D11 §3.x" point to the frozen v1.0 Methods.*

---

## 4. Methods (L2 extension)

### 4.1 Task: dual-arm 6-DoF pose-reach (Amendment 1 §2)

L2 is a **dual-arm 6-DoF pose-reach** (renamed from the working title
"dual_push"; Amendment 1 §2). Both end-effectors are actuated toward
per-arm pose targets — `left_ee_pose` / `right_ee_pose` command tracking
under `end_effector_position_tracking` rewards; the goal cubes are
pose-target visualizers, not pushable objects (l2_diagnosis.md Step 1).
The paper wording is fixed as **"a second, harder task in the same
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

### 4.5 Per-arm evaluation specification (Amendment 3 — PENDING isaac)

> **STUB — do not treat as authoritative.** The five-point per-arm eval
> specification is L2 pre-registration content (master = isaac territory).
> It will be filed by isaac as **L2 Amendment 3**; this section is the
> mechanical translation slot, to be filled *from that filed document*
> once it lands, per the session split (paper translates isaac's audit
> docs, does not self-author pre-reg). Expected content to calibrate
> against Amendment 3 when filed (recorded here so it is not lost, NOT as
> the authority):
> 1. non-scored arm frozen at its initial pose during eval;
> 2. primary eval = left-scored only, ×2 protocols (A_ctrl_rat +
>    C_retrieval), n=100;
> 3. eval seed base = **4600** (shared across the two protocols → paired
>    design, distinct from collect's 4500);
> 4. success = scored arm ‖EE−target‖ < 0.05 m;
> 5. task naming corrected to **position-goal reaching**.
>
> On Amendment 3 landing: verify these five against the filed text, adjust
> to match, cite `l2_amendment_3.md` + its SHA, and fold the seed-paired
> design into the Analysis-rules subsection (below) the same way D11 §3.4
> cites the 4500 base.

### 4.6 Analysis rules (carried from D11 §3.6, per-arm generalisation)

Unchanged in form from D11 (two-timestamp discipline; pairing-integrity
gate → McNemar primary on pass, two-proportion z on fail; all tests
two-sided). L2 generalisations, pre-specified in l2_analysis_adaptation.md
(Debt #1 dry-run, timestamped before any L2 five-protocol result):

- **Success gate** generalises to per-arm: `outcome=='success'` extraction
  reads the scored arm's `dist_red < thr` (already in collect.py
  `active_arm=None` branch); binary success-count machinery unchanged.
- **Pairing gate**: seed-based init fingerprint now includes both arms
  (richer `allclose`, still valid).
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
| **L2-3** | **pending** | **Per-arm eval spec (5-point) — to be filed by isaac; §4.5 translates on landing** | `l2_amendment_3.md` (pending) |
