# Teacher per-arm SR — PINNED (fulfils PRE_ANALYSIS_LOCK.md §b's deferral)

**Filed:** 2026-07-29 (isaac session, master).

The pre-analysis lock (§b) recorded the headroom denominator as a lock-time
estimate "≈28%" and deferred pinning it from data. Now pinned.

## Source (already-committed re-score, not a new computation)

`workspace/l2_audit/per_arm_rescore.json` (run `a6e6c917`, the L2-teacher
collect; threshold = 0.05 m, n = 100, per Amendment 1 §3):

- **left_reached  = 28 / 100 → teacher LEFT per-arm SR = 28.0%**
- right_reached = 28 / 100 (28.0%)
- both          = 10 / 100
- per_arm_any   = 46 / 100
- per_arm_desirable_instances = 56 (= 28 L + 28 R)

## Headroom recomputation (exact, "≈" removed)

Left-scored eval (Amendment 3):
- A_ctrl_rat bare SR = 14.0%
- teacher LEFT per-arm SR = 28.0%  → headroom = 14.0 pp
- C_retrieval recovered +6.0 pp → gap-closed = 6 / 14 = **42.9%**

## Label unchanged

The gap-closed framing is still POST-HOC / EXPLORATORY (introduced after
raw SR; PRE_ANALYSIS_LOCK.md §b). Pinning the denominator removes only the
"≈", not the exploratory label. Lock-time estimate (≈28% / ≈43%) vs pinned
(28.0% / 42.9%) agree — the lock's estimate was accurate; this file is the
provenance for the exact figures that go into the paper.
