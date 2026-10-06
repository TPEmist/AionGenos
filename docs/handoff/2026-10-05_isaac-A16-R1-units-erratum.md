# Handoff → isaac: Amendment 16 (documentation-only) — R1 ΔX units erratum

**From:** paper session · **Date:** 2026-10-05 · **PI ruling:** 2026-10-05

## What
File **Amendment 16** in `docs/d11_preregistration.md` (top of chain, after
A15) as a **documentation-only erratum**: the R1 ΔX quantities are in
**scalar-guard grid units, not cm**. No analysis, threshold, prediction,
branch rule or number changes. The pre-registration body stays as locked;
A16 only records the unit label correction.

## Evidence (all on disk)
- `scripts/analysis/d11_exploratory.py:55-64` — `r1_dx = parsed_left_pos[0] - trajectory[0].left_ee_pos[0]`.
- Both operands are integer grid coordinates in [−100, 100] (replay sample:
  `parsed_left_pos=[10, 15, -10]`, `left_ee_pos=[29, 21, -15]`).
- `aiongenos/vlm/scalar_guard.py` `metric_to_int`: normalise over bounds → [−100, 100].
- `aiongenos/config.py:43` `x_bounds=(-0.3, 0.6)` m → **1 grid unit = 0.45 cm along x**
  (no task overrides `workspace_bounds`).
- Machine-checked: `AionGenos-paper:docs/paper/birth_certificates/derived_stats.txt`
  line `[R1 dX unit]`.

## Scope of the erratum (list in A16)
Prereg lines labelling R1 values "cm": §5 l.79-83 (D6 −23.5, mem-teacher
−15.8, P2 prediction "−16 cm / −24 cm"), l.22. All comparisons are
within-unit (distances between arms/references), so **no prediction, branch
selection or conclusion changes**; only the label. Note the L2 R1 (DIAGNOSTIC_4b)
is already labelled grid units — consistent.

## Not in scope
- Do NOT edit the locked body text; A16 is additive.
- Do NOT re-run anything.

## Back to paper session
Send the A16 commit SHA. Paper (TMLR + workshop + Fig. 2, already relabelled
grid units) will cite "units erratum, Amendment 16 (`<sha>`)".
