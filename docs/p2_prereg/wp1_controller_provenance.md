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

### Step-0 stack dump (2026-08-04) — RELOCATES the hang, refutes earlier guess

Per PI direction, before H1-H3 guessing, dumped the hung process's Python
stacks (faulthandler `dump_traceback_later`, since py-spy is unavailable
here). Two runs (with and without the faulthandler timer as a control):

**The main thread hangs at `simulation_app._start_app`**
(`.../simulation_app/simulation_app.py:534` ← `_create_app`
`app_launcher.py:823` ← `wp1_osc_smoke.py:43` AppLauncher). Other threads
are idle `concurrent.futures` workers. So the hang is at **Isaac Sim app
init**, NOT at OSC reset/step (this refutes the earlier "hangs at reset /
first solve" reading — that was a misattribution; the process never got
past app launch on these runs).

**Environment control (decisive): L2 seed-smoke PASSES.** The known-good
L2 task (DiffIK, same `--enable_cameras`, same base cfg — differs ONLY in
action term) boots, resets, runs both seed trials, VERDICT PASS. So the
machine / kit / GPU is healthy; the hang is **WP1-OSC-task-specific**,
surfacing during the app-init⇄env-cfg-parse window (IsaacLab interleaves
`gym.make` cfg parsing with app startup). The OSC action term's build has
a side-effect that stalls app init on this task, though the same
`_start_app` completes fine for the DiffIK L2 task.

**Revised diagnosis plan (timebox: one working day):**
- Cheapest-first candidates now re-scoped to "what in the OSC cfg stalls
  app-init build" (NOT reset/solve): H1 the OSC controller cfg triggers a
  synchronous asset/extension load that never returns; H2 a required OSC
  wiring the base cfg lacks (nullspace / task_frame_rel_path) makes the
  action-term build block; H3 render-tick⇄OSC-build interaction.
- If unresolved by timebox → **minimal reproduction by bisection**:
  single-arm, NO camera, one OSC target — strip variables until it either
  boots or pins the offending cfg field. + search IsaacLab GitHub issues
  for known OSC action-term / app-init hangs.

Acceptance #1 (boots) is therefore NOT actually passing (earlier
"gym.make completes / env made" on prior runs is now suspect — those may
have been different flaky outcomes; the reproducible result is the
app-init hang). #2/#3 remain BLOCKED. WP1-① is **runtime-blocked at
app-init; OSC swap is written but unproven at runtime**; contact (③)
stays gated behind a booting ① step.

### Diagnosis session 2026-08-04 — 4 hypotheses tested, ALL refuted

Reproducible hang at `_start_app` every run. Tested and REFUTED:
1. **actuator gain** — zeroed the `openarm_arm` stiffness/damping +
   disable_gravity (matching the official OSC reach env, which is the
   *correct* OSC prerequisite regardless) → still hangs. So while zeroing
   gains is a needed OSC fix, it is NOT the hang cause.
2. **multithread freeze (`PXR_WORK_THREAD_LIMIT=1`, cf. issue #6464)** →
   still hangs. Refuted.
3. **faulthandler timer interfering with app init** — a fully
   faulthandler-free smoke variant → still hangs. Refuted (also confirms
   the `_start_app` stack dump is the real block, not a timer-thread
   artefact).
4. **leftover-GPU-process accumulation** — cleared all stray isaac PIDs,
   ran on a fully idle GPU → still hangs. Refuted. (NB: this session DID
   leave 2 stray hung PIDs on the A4500 because `pkill -f 'wp1_osc_smoke.py'`
   missed the job-tmp path variant and single-PID `kill` only got one —
   cleanup lesson: kill by `env_isaaclab/bin/python` match, verify GPU
   empty after every hung run.)

**Control that stands: L2 (DiffIK, same base cfg, same --enable_cameras)
boots + runs + PASSES.** So the hang is OSC-task-specific, not the
machine.

**Investigation agent (IsaacLab issue search) key finding:** no known OSC
app-init-hang issue exists; and the `_start_app` frame is architecturally
INCONSISTENT with "OSC term inits after scene build" — the real block may
be elsewhere (all-threads dump needed, not just main frame). Agent's
first-priority next step (NOT yet done, the decisive fork):

**NEXT (do first, before any more cfg guessing):** run the OFFICIAL OSC
example to isolate install-vs-our-cfg —
`isaaclab.sh -p scripts/tutorials/05_controllers/run_osc.py --headless`
and/or the `Isaac-Reach-Franka-OSC-v0` task. If the official OSC example
ALSO hangs → Isaac Sim / PhysX install problem (unrelated to our cfg,
cf. #6220). If it runs → the problem is in our bimanual OSC cfg, then
bisect (single-arm, no camera, one OSC target). Timebox for this session
spent; WP1-① stays in_progress, runtime-blocked, next step pinned.

### Isolation test 2026-08-05 — VERDICT: INSTALL-LAYER (official OSC also hangs)

Per the pinned fork + PI spec (mechanical GPU gate before launch;
`assert_gpu_clear.sh` = "cleanup must have an assertion"). Ran the
**official, unmodified** IsaacLab tutorial
`scripts/tutorials/05_controllers/run_osc.py --headless --num_envs 1`
(no camera, no AionGenos cfg — pure install-layer probe).

**Result: it HANGS too** — reaches deeper than our smoke (into
`simulation_context` PhysX init, GPU 2549 MiB = scene actually building)
then freezes; log frozen, process alive, no sim loop. A stock IsaacLab OSC
example, zero of our code, hangs on this machine.

**Verdict (spec branch 1): this is an INSTALL-LAYER problem, NOT our
bimanual OSC cfg.** Evidence chain:
- official run_osc.py (our code = none) hangs → not our cfg;
- L2 (DiffIK, our cfg) runs → not the machine in general, and not our
  task scaffolding;
- ⇒ the fault is on the **OSC execution path × this Isaac Sim install**.

**Isaac Sim version: `5.1.0-rc.19+release.26219.9c81211b.gl`** — matches
the version family in issue **#6220** (Isaac Sim 5.1 kit-startup hang) that
the investigation agent flagged. Strong corroboration that the OSC path is
broken in this 5.1-rc build.

**Minimal reproduction (for the upstream/version decision):**
`./isaaclab.sh -p scripts/tutorials/05_controllers/run_osc.py --headless --num_envs 1`
hangs at `simulation_context` init; any non-OSC task (e.g. L2 reach) runs
fine on the same install. gdb/py-spy native backtrace was attempted but
ptrace was not permitted in this env (native stack not captured).

**Per PI spec: NOT entering a fix spiral.** An install operation
(IsaacLab / Isaac Sim version up/down-grade) is a NEW engineering decision
outside this timebox. WP1-① is marked **BLOCKED-ON-UPSTREAM**; the cfg is
written and correct, unprovable until the OSC-on-5.1 install issue is
resolved. Recommended next (for PI ruling): assess cost of moving off
Isaac Sim 5.1-rc.19 to a build where the official OSC example runs. Pivot
work to WP1-② (Edge-Grasp bridge recon — no ① dependency, pure CPU).
