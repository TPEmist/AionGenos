# L2 analysis-pipeline adaptation — dry-run findings + locked probe defs

*Debt #1 (analysis dry-run against real L2 replays). Written BEFORE any
L2 five-protocol result exists, so the L2 probe definitions below are
pre-specified, not post-hoc-picked. Dry-run used the 5 replays already
on disk from the fresh L2 collect (run a6e6c917 / current run).*

## Schema deltas L0a → L2 the D11 analysis scripts must handle

| aspect | L0a-Left (D11) | L2 dual-push | analysis impact |
|---|---|---|---|
| active arm | `left` (right frozen) | **both arms actuated**, `active_arm` field ABSENT | success gate + R1 probe both assume one arm — must generalise |
| success gate | `dist_red < 0.05` | **both**: `dist_red < thr AND dist_blue < thr` (already in collect.py:398-403, `active_arm=None` branch) | `outcome=='success'` extraction still valid; no change needed |
| R1 ΔX probe | left-arm X: `target_x − init_x` | two arms move (e.g. ΔX_L=−25, ΔX_R=+27 same ep) | **single scalar undefined — see locked redefinition below** |
| outcome taxonomy | success / failure | adds `timeout` (all 5 dry-run eps timed out — expected early, teacher not yet warmed) | McNemar/z only need binary success; fine |

Confirmed working unchanged on L2: the pairing gate (seed-based, uses
init EE + distances fingerprint — both arms present, richer fingerprint,
still a valid allclose), the z/McNemar success-count machinery, the
residual-correlation diagnostic (operates on whatever R1 metric we
define).

## LOCKED probe redefinition for L2 (pre-specified, audit-log timestamped)

The R1 ΔX probe measured, in L0a, the round-1 lateral (X) bias of the
single active arm against reference fingerprints. For L2 dual-push the
pre-registered L2 equivalent is defined **now, before L2 results**:

**L2 R1-bias probe = the per-arm round-1 signed displacement toward
each arm's own target, reported as a two-component vector
(ΔX_L, ΔX_R), plus a pooled magnitude ‖ΔR1‖ = mean over both arms of
|round-1 target − init EE| along the task-relevant push axis.**

- The *marginal-vs-conditional* test that R1 served in L0a carries over
  unchanged in FORM: does the distilled arm's per-arm R1 displacement
  collapse to a static per-arm prior (marginal) while retrieval's
  varies per episode (conditional)? The residual-correlation diagnostic
  (§4.4b analogue) runs per-arm and pooled.
- We do **not** import L0a's −23.5/−15.8 cm reference fingerprints:
  those are L0a-teacher-specific. L2 references are the L2
  memory-teacher's own R1 distribution (to be measured from the L2
  teacher buffer once the collect completes) — a task-matched
  fingerprint, not a transplanted one.
- Reason this is locked now: writing it after seeing L2 five-protocol
  numbers would make it a picked metric. Same discipline as Amendment
  9 §9.4. This file's commit timestamp is the pre-specification.

## Concrete code changes needed (when L2 five-protocol data lands)

1. `d11_mcnemar.py`: parameterise run_ids (currently hard-codes the 5
   L0a run_ids); success extraction unchanged.
2. `d11_exploratory.py`: R1 probe → emit (ΔX_L, ΔX_R) per episode +
   pooled; residual-correlation runs per-arm; drop the hard-coded
   −23.5/−15.8 references, read L2-teacher R1 distribution instead.
3. Neither script touches the frozen v1.0 paper; they are analysis
   tooling for the L2 extension.

## Not doing now (correctly deferred)

- No L2 training/eval yet — buffer still building.
- No edits to frozen paper v1.0.
- Rank sweep, L3: roadmap, not this window.
