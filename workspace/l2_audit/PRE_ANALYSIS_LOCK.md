# L2 Confirmatory — PRE-ANALYSIS LOCK

**Timestamp intent: this file is written and committed BEFORE any p-value,
McNemar, z, or CI is computed.** Its git commit time is the proof that the
verdict framework was fixed before seeing any inferential result. Only the
raw success counts (already visible in the eval logs' Stats summary) are
known at lock time.

**Filed:** 2026-07-28 (isaac session, master).
**Governs:** the L2 Stage-1 confirmatory analysis (Step 3) and the
diagnostic pack (Step 4). Anchored to Amendment 2 (scope) + Amendment 3
(per-arm eval).

## Known at lock time (raw SR only — no inferential test run yet)

| protocol | run_id | successes / n | SR |
|---|---|---|---|
| A_ctrl_rat (bare, left-scored) | `8384a740` | 14 / 100 | 14% |
| C_retrieval (left-scored)      | `2154e57e` | 20 / 100 | 20% |

Point estimate: **C_retrieval − A_ctrl_rat = +6 pp** (20% − 14%).
`parse_fails = 0` both protocols (per-arm format contract held).

## (a) Verdict framework — LOCKED regardless of the McNemar outcome

Amendment 2's MDE analysis (T4-class, baseline ~15%, n=100, α=0.010):
power is **76% for +20pp, 99% for +30pp, 100% for +34pp**. The observed
A_ctrl_rat SR (14%) sits essentially on the assumed baseline (~15%), so
the MDE frame applies as filed — no recomputation of the design
assumption is warranted.

The observed **+6 pp is well below the +20 pp minimum detectable effect.**
Therefore:

1. **Prediction (pre-registered here): the McNemar / z test will be n.s.**
2. **The verdict follows Amendment 2's "not significant → DIAGNOSE"
   branch, NOT more arms.** The response to a sub-MDE point estimate is
   the three-item diagnostic pack (Step 4), whose job is to explain *why*
   the retrieval effect attenuates on the harder task — not to chase
   significance with additional protocols.
3. **If the test comes back UNEXPECTEDLY SIGNIFICANT**, the verdict frame
   does **not** change: report the inconsistency-with-prediction itself as
   the finding (a +6pp effect reaching significance at n=100 would be
   surprising and worth flagging), and still run the diagnostic pack. The
   framework is fixed here so a significant result cannot be
   retrospectively reframed as "the headline we were hoping for."

This is the third application of the event-driven power discipline
(cf. Amendment 2 §"paper wording"): the power analysis, filed before the
number, decides how the number is read.

## (b) Headroom-normalization framing — POST-HOC, disclosure-timed

A cross-task comparison in raw pp is misleading because the two tasks have
different achievable headroom. A normalized framing:

- **L0a:** retrieval closed the parity gap 34.3 / 34.3 ≈ **100%** of the
  gap to the teacher.
- **L2:** retrieval closes 6 / 14 ≈ **43%** of the per-arm gap
  (L2 teacher per-arm SR ≈ 28%; A_ctrl_rat bare 14% → headroom to teacher
  = 14 pp; +6 pp recovered = ~43% of it).

**This framing is introduced AFTER the raw SR is known and is therefore
POST-HOC. It carries the `exploratory` label; the label is not optional
and may not be dropped in any downstream text.** Cross-task statements use
the *gap-closed proportion*, not the raw pp difference — but always tagged
exploratory, and always with the raw pp reported alongside. (Exact
per-arm teacher SR and headroom denominators to be pinned from data in
Step 4b; the ~28% / 43% figures here are the lock-time estimates to be
confirmed, not asserted.)

## (c) Wording red-line — until the diagnostic pack completes

Before Step 4 completes, NO attribution sentence may be written. The only
permitted characterization of the confirmatory result is the three-clause
statement:

> "The point estimate is below the pre-registered MDE; the direction
> agrees with L0a; the confidence interval simultaneously admits zero and
> a moderate effect."

No sentence of the form "retrieval fails to transfer because …",
"distillation captured …", "the conditional structure is smaller …", or
any other mechanism claim, until Step 4's diagnostics license it. The
diagnostics' own predictions are pre-registered in Step 4 (each written
before its script runs).

## Verdict authority

The verdict phrasing in `l2_confirmatory_report` is bound to this lock
file. The paper session (v1.1 writing) translates the report into prose
but does **not** re-interpret the verdict — this audit log is the source
of truth for what the L2 numbers are allowed to say.
