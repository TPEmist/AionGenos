# L2 Amendment 1 — per-arm scoring (post-hoc, disclosed) + pool construction + task rename

**Status**: LOCKED before any L2 prep / training runs. Commit timestamp
is the pre-specification for the L2 desirable-pool construction and the
per-arm metric.
**Date**: 2026-07-15
**Governs**: the L2 extension only. The D11 (L0a) frozen paper v1.0 and
its pre-registration are untouched.

## 1. Per-arm scoring is a POST-HOC change — disclosed, not picked

The per-arm success numbers (left 28/100, right 28/100, joint-at-end
1/100) were **visible before this decision was made** — they are what
motivated it. We state this plainly, same immunisation standard as D11
Amendment 14:

> Promoting per-arm scoring to the primary L2 metric is a **post-hoc**
> change. Its motivation is a *structural* discovery about the success
> definition (joint simultaneous-both-arms-at-episode-end compounds two
> ~28% events down to 1%), **not** selection on a five-protocol result
> — no L2 arm has been trained or evaluated at the time of this filing.
> The joint-success SR remains reported alongside as the originally
> registered metric; per-arm is added, not substituted.

## 2. Task rename + provenance

L2 is renamed everywhere (cfg comment, docs, paper) from "dual_push" to
**dual-arm 6-DoF pose-reach (formerly misnamed dual_push)**. The
`left_ee_pose`/`right_ee_pose` command tracking with
`end_effector_position_tracking` rewards is a pose-reach; the goal cubes
are pose-target visualizers, not pushable objects (l2_diagnosis.md
Step 1). The paper's cross-task wording is fixed as **"a second, harder
task in the same primitive family"** — not "push", not "a different
skill". A genuine push (cube as tracked object) is L3-scope.

## 3. Desirable-pool construction rule (LOCKED before prep)

Under per-arm scoring, on the existing 100-ep dual run (run a6e6c917):

- **A per-arm episode is *desirable* for arm X** iff arm X's
  end-effector reached its pose goal (best-in-episode
  ‖EE−target‖ < 0.05 m, the registered threshold). This yields
  ~28 desirable-arm instances per arm.
- **SFT desirable target** = the progress-rounds of the desirable arm,
  with the canonical action lines emitted **single-arm** (only the
  scored arm's LEFT/RIGHT_TARGET_POS line + STOP), so the SFT target
  matches what a single-arm-scored student should emit. The
  non-scored arm's outcome is recorded as a **flag**
  (`other_arm_reached: bool`), not folded into the target.
- **KTO pairing**: for the scored arm, desirable = its progress-rounds
  in arm-reached episodes; undesirable = its progress-rounds in
  arm-failed episodes. Pairing is per-arm-instance, mirroring D11's
  desirable/undesirable split one arm at a time.
- **Both arms contribute instances** (left-scored and right-scored
  episodes both enter the pool), so n_desirable ≈ 56 (28+28) across the
  100-ep run — a real, if modest, pool. Row counts to be SHA-pinned by
  the Step-2.verify sentinel once prep runs.
- The 4-arm 2×2 factorial (A_action_only / A_ctrl_rat / B_main /
  D_gist) and the C_retrieval protocol carry over unchanged in FORM;
  only the pool source and the single-arm canonical target differ.

## 4. R1 probe

Uses the already-pre-specified L2 definition
(`l2_analysis_adaptation.md`): per-arm (ΔX_L, ΔX_R) + pooled, against
the **L2-teacher's own** R1 distribution (task-matched), not the
transplanted L0a −23.5/−15.8 cm fingerprints.

## 5. What is NOT changed

- D11 (L0a) frozen paper v1.0 / tag paper-v1.0: untouched.
- L2 arms, tests (T1/T1a/T4), seed-pairing, McNemar/z fallback,
  flags_only_a6 filter: all carry over from D11 unchanged.
- Joint-success SR: still reported (as originally registered), with
  per-arm added.

## 6. Decision rule for whether to re-collect native single-arm (pinned now)

After the L2 five-protocol eval completes, at a 48h checkpoint measured
from eval completion:
- **Keep the re-scored dual run** (no native re-collect) iff the
  marginal/conditional split replicates cleanly — judged on (a)
  C_retrieval − A_ctrl_rat direction + significance, and (b) whether
  the R1 per-arm fingerprint tracks the L2-teacher's own distribution.
- **Spend the extra ~12h on a native single-arm collect** iff the
  split-from-dual introduces a real confound OR the result is
  ambiguous on (a)/(b).
This criterion is written before any L2 five-protocol number exists.

---

## Amendment 1a — buffer re-tag (dual-label) + arm-aligned success-floor

**Status**: LOCKED before any C_retrieval-L2 eval. Filed 2026-07-15,
after the full per-arm re-score (56 desirable instances confirmed) but
before any five-protocol run.

### The mismatch (verified, not hypothesised)

The 100 L2 recaps were tagged `is_success` by JOINT outcome at collect
time (1 True / 99 False). Full-population re-score: 46/100 episodes have
≥1 arm reaching goal; **45 of those carry is_success=False despite
holding a goal-reaching arm trajectory.** Under per-arm scoring the
buffer's labels are wrong for ~45% of episodes — and the naive fix
(`is_success = left OR right`) reintroduces cross-arm contamination
(F65's cousin): a "right-reached, left-failed" episode whose
failure-driven `text_lesson` is about the LEFT arm would be served as a
[✓] success to a student operating the LEFT arm.

### Fix (two layers, minimal)

1. **Data layer — dual label on each recap** (does not touch retrieval
   similarity): add `left_reached` / `right_reached` bool fields from
   replay GT (the re-score in `workspace/l2_audit/per_arm_rescore.json`).
   Keep `is_success` (joint) for reference/comparison.
2. **Retriever logic — arm-aligned success-floor** (3–5 lines): the
   success-floor filter reads the label **corresponding to the arm the
   student is currently scored on** (`left_reached` when the current
   canonical action line is the left arm's, else `right_reached`), not
   the joint `is_success`. The arm being operated each round is already
   known to the pipeline (canonical lines are left/right explicit), so
   this is a lookup of an existing variable, NOT new retrieval logic.

### Explicitly unchanged (stated so future-me doesn't over-read it)

- **Retrieval similarity is untouched** — image + full-state anchor as
  before. Only the success-floor FILTER label is arm-aligned.
- No per-arm retrieval, no recap splitting.

### Residual limitation (disclosed)

`text_lesson` remains episode-level natural language and may reference
either or both arms; only the success-floor LABEL is arm-aligned, not
the lesson prose. One-line paper limitation: *"lesson text remains
episode-level; only the success-floor label is arm-aligned."* This
shrinks the original whole-buffer mislabel to an occasional
cross-arm phrasing in retrieved lesson text — an acceptable residual.

### Order of operations (locked)

Amendment (this) → buffer re-tag script → retriever 3–5 line change →
re-pin buffer SHA → THEN C_retrieval-L2 unlocked. No C_retrieval eval
before the re-pin.

### Pin targets (post re-tag)
- per-arm desirable instances: 56 (28 L + 28 R) — Step-2.verify target.
- re-tagged buffer tree-hash: to be recorded after re-tag runs.
