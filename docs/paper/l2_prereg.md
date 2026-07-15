# L2 mini pre-registration (one page, timestamped before L2 five-protocol results)

*The heavy 14-amendment machinery is not repeated; the D11 pre-reg's
arms, tests, seed-pairing, analysis-rule lock, and flags_only_a6
filter all carry over unchanged to L2. This page pins only what is
NEW or task-specific for L2, before any L2 five-protocol number exists.*

## Hypotheses carried over from D11 (same form, L2 task)

- **T1 (L2)**: B_main − A_action_only on L2 dual-push, two-sided.
- **T1a (L2)**: B_main − A_ctrl_rat.
- **T4 (L2)**: C_retrieval − B_main (protocol contrast); plus the
  identical-weights C_retrieval − A_ctrl_rat as the clean comparison
  (the ② lesson baked in from the start this time).
- **R1-bias probe (L2)**: per-arm (ΔX_L, ΔX_R) + pooled, per
  `l2_analysis_adaptation.md` (locked there).

## The prediction (pinned before results)

**Primary prediction — does the marginal/conditional split replicate?**
We predict the *same qualitative pattern* as L0a:
- distillation transfers a marginal (static, per-arm) prior → T1 near
  zero;
- retrieval on fixed weights recovers a conditional component → the
  identical-weights contrast (C_retrieval − A_ctrl_rat) positive and
  large.

**Direction/magnitude bets (falsifiable):**
- T1 (L2): |Δ| < 5 pp (null replicates), predicted.
- identical-weights retrieval effect (L2): positive, and we bet ≥ +15
  pp — but with lower confidence than L0a, because push may carry MORE
  conditional structure than reach (a push's required force direction
  depends on contact geometry, not just target position), so the
  retrieval advantage could be *larger*; or push may be so hard that
  all arms floor near zero and effects compress. Both are interesting;
  the bet is direction (positive), not a tight magnitude.
- A plausible *dis*-confirmation: if push's conditional structure is
  richer, even retrieval may not fully supply it in-context, and
  C_retrieval could fall well short of the L2 teacher — which would
  refine the thesis to "context supplies conditional structure only
  up to the task's in-context describability".

## MDE — computed as a function of the (not-yet-measured) L2 baseline

The ① lesson: state detectable effect BEFORE results. L2 baseline SR
is unknown (early episodes all timeout; teacher not yet warmed on
push). The MDE rule, pinned as a formula:

- At n=100/arm, two-sided α (per the D11 allocation: T1/T1a α=0.020,
  T4 α=0.010), the minimum detectable Δ is
  **MDE = z_α · √(2·p̄·(1−p̄)/100)** where p̄ is the pooled baseline.
- Worked points (fill p̄ once L2 baseline SR is measured):
  - if L2 baseline p̄ ≈ 0.15 → SE ≈ 0.0505 → MDE(α=0.020) ≈ 11.7 pp
  - if p̄ ≈ 0.25 → SE ≈ 0.0612 → MDE(α=0.020) ≈ 14.2 pp (= L0a's)
  - if p̄ ≈ 0.10 → SE ≈ 0.0424 → MDE(α=0.020) ≈ 9.9 pp
- **Decision rule pinned now:** as in D11, T1's registered "≥10pp AND
  significant" is only *jointly* satisfiable if MDE ≤ 10 pp, i.e. if
  L2 baseline SR ≤ ~0.10. If measured L2 baseline is higher, we
  acknowledge up front (as we did post-hoc for L0a, now pre-hoc for
  L2) that a true +10 pp effect is under-powered, and we report T1 as
  "withdraw not refute" by the same standard — NOT as a strong null.
  This time the underpowering is disclosed before the test, not after.

## Filter / curation

Unchanged: `flags_only_a6` structural zero-drop; L2 training pool
counts to be pinned by SHA once the L2 collect + prep complete (the
D11 Step-2.verify row-count sentinel carries over).

## Addendum (2026-07-15) — superseded/refined by Amendments 1 & 2

This page pinned the L2 plan before the 100-ep collect result was
known. After collect (teacher per-arm 28%, joint 1%) two amendments
refined it; this addendum records the delta so the pre-registration
reads as one coherent chain:

- **Scope narrowed (Amendment 2).** The symmetric 4-arm 2×2 above is
  NOT run. T1-class (bake-in) is dropped as un-measurable: measured L2
  baseline ~15–25% gives MDE 12–13 pp at α=0.020, n=100, against an
  L0a bake-in effect of +1 pp — the "decision rule pinned now" clause
  above resolves to *do not run T1 on L2*. L2 tests only the
  answerable question: does the identical-weights retrieval effect
  (C_retrieval − A_ctrl_rat) replicate? T4-class power at n=100,
  α=0.010, baseline 15%: 76% (+20pp) / 99% (+30pp) / 100% (+34pp).
- **Per-arm scoring (Amendment 1).** Joint SR (1%) is compounding, not
  incompetence (per-arm 28%/28%). Primary L2 metric is per-arm;
  desirable pool = 56 episode-instances = 511/1119 desirable/undesirable
  ROUNDS (training adequacy, distinct from the episode-level n=100 eval
  power). Task renamed dual-arm pose-reach (not push).
- **Buffer re-tag (Amendment 1a).** Success-floor arm-aligned; the
  memory-world asymmetry (teacher joint-labelled growing buffer vs
  eval's re-tagged frozen buffer) is disclosed in
  l2_memory_world_asymmetry.md.
- **R1 probe** per l2_analysis_adaptation.md (per-arm, L2-teacher
  fingerprint).

The prediction bets above (marginal/conditional split; retrieval
positive) stand, restricted to the retrieval half that Amendment 2
retains.

## What this page is NOT

Not a rewrite of the D11 pre-reg; a task-specific delta sheet. Its
commit timestamp is the pre-specification for L2's confirmatory tests
and the R1-equivalent probe.
