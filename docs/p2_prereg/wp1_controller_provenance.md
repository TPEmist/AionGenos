# WP1 controller provenance — pinned BEFORE first data (Q1 companion rule)

**Rule (PI decision 2026-08-03, Q1):** any new task pins its controller
choice into provenance BEFORE collecting its first datum — no "run it and
see" suspension. This file is that pin for the WP1 contact test-bed.

## Test-bed identity
- **Task**: `wp1_contact_testbed` (NEW; L4+ contact-rich scope).
- **Controller**: `OperationalSpaceControllerActionCfg` (IsaacLab native),
  bimanual, one action term per arm. Explicitly NOT DiffIK.
- **Why OSC here**: closed-loop contact needs a force/compliance channel;
  DiffIK is open-loop position servo (the first wall). OSC ships
  `impedance_mode` + `contact_wrench_control_axes_task` /
  `contact_wrench_stiffness_task` (verified in
  `IsaacLab/.../controllers/operational_space_cfg.py`).

## Boundary guarantee (Q1)
- L0–L3 (`L0*`, `L1*`, `L2_dual_push`, `L3*`) remain on
  `DifferentialInverseKinematicsActionCfg`, byte-untouched. P1 provenance
  and all P1 numbers stay valid; no re-run, no comparability loss.
- The controller split is by task family, filed here so it is never a
  silent runtime choice.

## Initial controller config (smoke-stage, may be tuned before real data)
- `target_types = ["pose_abs"]` initially (motion-only), to first
  reproduce DiffIK-equivalent reaching under OSC before enabling contact.
- `motion_control_axes_task = (1,1,1,1,1,1)`,
  `contact_wrench_control_axes_task = (0,0,0,0,0,0)` at smoke stage
  (pure motion); wrench axes enabled only when the contact primitive
  (press/twist, WP1-③) is wired — that enabling is a SEPARATE provenance
  update, re-pinned before its first data.
- `impedance_mode = "fixed"`, `motion_stiffness_task` at the IsaacLab
  default (100) initially; per-task gain tuning is a tracked follow-up, not
  a silent change.

## Smoke acceptance (what WP1-① must show before any collect)
1. OSC bimanual env boots on the openarm URDF (no controller/asset error).
2. Under `pose_abs` motion-only, the EE tracks an absolute pose target to
   within the same ~5cm gate DiffIK achieves — i.e. OSC is at least
   motion-equivalent before we ask it to do contact.
3. Seed-determinism smoke passes (reuse the L2 check) so the test-bed is
   paired-eval-ready.
Contact (wrench) behaviour is NOT part of the ① smoke — it belongs to ③
and re-pins provenance when enabled.

## ① smoke STATUS (2026-08-03) — static swap PASSES, runtime step HANGS

Ran `scripts/diagnostics/wp1_osc_smoke.py` (IsaacLab, A4500, headless
--enable_cameras). Flush-bracketed markers localised progress:
- ✓ `cfg parsed OK` — `WP1ContactTestbedEnvCfg` parses.
- ✓ `env made` — **`gym.make` completes**: the OSC action terms build on
  the openarm bimanual URDF with NO controller/asset error. Sim starts,
  scene/robot/sensors initialise. **Acceptance #1 (boots, no OSC error)
  effectively PASSES** — the DiffIK→OSC swap is structurally sound.
- ✗ HANG at `env.reset()` / first `env.step()`: no `reset OK` marker; log
  frozen; python process ALIVE but GPU compute-app idle (waiting, not
  computing) → a solver/tick dead-wait, not a crash (first run's "silent
  death" was the same hang + a kit timeout-cleanup, misread as a crash).

**Diagnosis hypothesis (for the next work session, NOT yet fixed):** the
OSC controller's first solve hangs. Candidate causes, cheapest first:
1. zero-action ambiguity: feeding an all-zero `pose_abs` target may be
   ill-posed for OSC (unlike DiffIK it may need a *valid* absolute pose,
   not zeros) → try seeding the action with the current EE pose.
2. missing `nullspace`/`task_frame` wiring the OSC term expects but the
   reach base cfg does not provide.
3. camera-render + OSC tick interaction (accept #2/#3 need the render on).
Acceptance #2 (motion-equivalence) and #3 (seed determinism) are BLOCKED on
resolving this hang — not started. WP1-① is **partially green (static
swap), runtime open**; contact (③) stays gated behind a working ① step.
