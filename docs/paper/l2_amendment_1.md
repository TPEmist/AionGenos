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
