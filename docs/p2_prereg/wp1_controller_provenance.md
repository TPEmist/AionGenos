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

> **⚠️ SUPERSEDED — dated correction 2026-08-05 (later same day).**
> **This install-layer verdict is WRONG. Kept verbatim below for honesty;
> do not act on it.** Two compounding errors produced it, both surfaced
> when the user hand-ran the official example without `--headless`:
>
> 1. **Misread control.** The official `run_osc.py` did NOT hang. It prints
>    `"Setup complete..."` then enters a SILENT `while
>    simulation_app.is_running()` loop (`sim.step(render=True)`, no
>    per-step print). "log frozen after Setup complete" was a normal
>    no-output sim loop, not a hang. The user's headed run stayed alive 3+
>    min; a fresh headless run also just runs silently. **Official OSC works
>    on this install.**
> 2. **Self-broken instrument.** Our own smoke had a DUPLICATE
>    `AppLauncher(args_cli)` (accidentally inserted during an earlier
>    shell-edit that added flush markers). The 2nd AppLauncher deadlocks
>    (app already started) → the real cause of the `_start_app` hang the
>    faulthandler dump kept pointing at. Removing the dup → smoke now
>    reaches `env made` (OSC env builds fine).
>
> **Corrected root state:** Isaac Sim 5.1 / OSC install is FINE (not #6220).
> The remaining real issue is our OSC test-bed hanging at **reset /
> first-step** — the original problem, now cleanly isolated (see the
> 2026-08-05b section below). The "4 hypotheses refuted → install-layer"
> chain was disciplined but built on a self-broken instrument + a misread
> control, so its conclusion is void. Lesson → the three process rules
> added at the end of this file.

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

### 2026-08-05b — CORRECTED state after the dup-AppLauncher fix

With the duplicate `AppLauncher` removed, the smoke now prints
`[smoke] cfg parsed OK` → `[smoke] env made: Isaac-AionGenos-WP1-Contact-v0`
(the OSC bimanual env BUILDS — this was unreachable before). It then stalls
at **reset / first step** (no `reset OK` marker). This is the original,
real WP1-① issue, now cleanly isolated from the two red-herrings above.

- Install is fine (official OSC runs; headed run stayed alive 3+ min).
- OSC env construction is fine (`env made`).
- Open: reset/first-step stall. faulthandler in-process dump is unreliable
  here (Isaac Sim app takes over signal handlers → the timer never fired);
  need EXTERNAL attach (`py-spy dump --native`, no in-proc signal dep) if a
  stack is required.

**Diagnosis plan (PI-approved):** B first (cheapest single variable) —
run the OSC test-bed WITHOUT `--enable_cameras` (official run_osc has no
camera and runs; ours has a camera and stalls → camera×OSC-reset
interaction is the sole differing variable). If B runs → root cause locked;
assess whether WP1 needs the camera (teacher needs vision → likely yes) and
fix the interaction. If B still stalls → switch to A: headed mode (leverage
"headed works") to step closer, and `py-spy dump --native` from outside.

## Process rules (from the 2026-08-05 mis-diagnosis — two root causes, three gates)

These are standing rules, not one-offs. Each grows from a root cause of the
mis-diagnosis above.

**Rule 1 — Instrument re-calibration (from: self-broken instrument).**
After ANY change to a diagnostic tool/script, the NEXT step must re-run a
KNOWN-GOOD baseline (e.g. the L2 DiffIK config) through the *changed* tool
before trusting any new observation from it. If the baseline breaks, you
broke the instrument — you did NOT find evidence. This would have caught
the duplicate `AppLauncher` within one run (L2 through the edited harness
would have hung too, flagging the harness not the task).

**Rule 2 — Operational definition of "hang" (from: misread control).**
Before declaring a hang, check ≥2 liveness signals over a defined window:
GPU utilisation, process CPU state, log-file size growth, sim-step counter.
"No stdout output" ALONE is not a hang — a silent sim loop looks identical.
This would have caught the official-example misread (it was running silently
with live GPU/CPU, growing nothing in the log because the loop simply does
not print).

**Rule 3 — Evidence-attached reporting (from: expensive-to-audit verdicts).**
Any empirical claim that changes a decision branch ("X also hangs", "Y
PASS") is reported WITH raw evidence: exact command, last ~20 log lines,
exit status / liveness readings — not just the verdict. The user's spot-check
cost should be one glance, not a re-run.

### A1 bisection 2026-08-05 — s-table (build-up from official OSC reach env)

| stage | added variable | verdict | evidence |
|---|---|---|---|
| s0 | official OSC + openarm SINGLE arm | **PASS** | env made → reset OK → 5/5 steps → STAGE PASS, action_dim=13; body `openarm_hand` confirmed |
| s1 | + 2nd arm (dual articulation, 2 OSC terms) | **PASS** | STAGE PASS, action_dim=26 — REFUTES highest-suspicion bimanual×OSC |
| s2 | + AionGenos RGB camera (verbatim) | **PASS** | STAGE PASS w/ --enable_cameras — refutes camera×OSC-reset |
| s3 | + AionGenosReachEnvBaseCfg extras (reset event, cmd lock, …) | pending | next |

**Interim conclusion:** OSC, bimanual, and camera are all EXONERATED. The
root cause of the original test-bed's reset stall is in what
`AionGenosReachEnvBaseCfg` adds over the official reach base. Prime suspect:
the custom `reset_robot_joints` EventTerm (`reset_joints_to_target_with_offset`,
reach_env_base_cfg.py:90). s3 adds the base's extras one at a time; the
first red stage is the root cause, then A2 native-stack on that config.

Incidental (crashes not hangs, fixed): s1 stale franka `arm_action`
(panda_joint.* regex); s1 gym-register clobbered by a linter edit on
`tasks/__init__.py` — re-added. Note: `tasks/__init__.py` is being edited by
a linter/other hand between my writes; re-verify my gym.register survives
before each run.

### 2026-08-05 — the "other hand" located + isolated (4th shared-resource incident)

The intermittent clobber of a WP1 `gym.register` in `tasks/__init__.py` was
traced to the **IDE (Antigravity) Python language server / format-on-save**
(jedi-lsp + Pylance processes live; git shows no non-mine commit; paper
worktree did not touch master's tasks/; file mtime = my edit time, so the
rewrite is intermittent-on-save, not a daemon loop). Cannot disable the
user's IDE → **isolate**: WP1 registrations moved to a dedicated
`aiongenos/tasks/wp1_registry.py`; `__init__.py` now only
`from . import wp1_registry`. A clobber of one import line is trivially
re-verified; an inline-block clobber was invisible.

**4th shared-resource incident, same lesson each time — isolate, don't
share:** GPU→lockfile; session-territory→worktree; working-tree→worktree;
now **file-level contention→dedicated module**. Also scripted the
cleanup+GPU-assert+launch path into `run_osc_bisect_stage.sh` (explicit
per-step exit checks, no &&-chains) to buy out the repeated pkill/&&
footguns — one entry point for every stage from here.

### A1 bisection 2026-08-05 (cont.) — s3 PASS; last unisolated variable found

| stage | added variable | verdict |
|---|---|---|
| s3 | + custom reset event (reset_joints_to_target_with_offset) | **PASS** (action_dim=26) |

s0–s3 ALL GREEN. OSC, bimanual, camera, and the custom reset event are all
exonerated. Comparing the original `WP1ContactTestbedEnvCfg` against the
(green) s-stages, the ONE remaining unisolated variable is the **robot cfg
flavour**: the original uses `OPENARM_BI_HIGH_PD_CFG`, the s-stages use
plain `OPENARM_BI_CFG`. The original already zeroes the ARM actuator
stiffness/damping (so HIGH_PD's arm-gain override is neutralised), leaving
HIGH_PD's **gripper actuator gains (stiffness=2e3, damping=1e2)** as the
only remaining difference (s-stages have plain gripper gains). Candidate
s4: s3 + swap robot to HIGH_PD (or raise gripper gains) — the last thing to
test before the original testbed's config is fully accounted for.

**Timebox reached (s0–s3 done, all green, original still stalls).** Per PI
rule: STOP and report the complete s-table. Emerging root-cause candidate:
HIGH_PD gripper gains × OSC (a high-stiffness gripper PD loop under an
effort controller — plausibly the same "PD fights effort" mechanism that
zeroing the ARM gains fixed, but left in place on the gripper). This is a
lead, not a verdict — s4 + the 2×2 confirm would settle it, pending PI go.

### 2026-08-06 — WP1-① RESOLVED: the config was fine all along (both "hangs" were script bugs)

Direct single-variable test on the REAL test-bed, via the clean bisect
smoke (single AppLauncher, all prints flushed): **the original
`WP1ContactTestbedEnvCfg` PASSES** — env made → reset OK → 5/5 steps →
STAGE PASS (action_dim=26), reproduced twice. The gripper-gain fix
(gripzero) was not even needed to reach this; the original config runs.

**Root-cause post-mortem — TWO separate script bugs, zero config faults:**
1. The original "reset hang" (2026-08-03) = the DUPLICATE `AppLauncher` in
   wp1_osc_smoke.py deadlocking at `_start_app` (fixed 2026-08-05).
2. After that fix, wp1_osc_smoke still "stalled at env made" (2026-08-05b)
   = its `reset OK` print had NO `flush=True`, so a successful reset+step
   sat in the stdout buffer and the log looked frozen — the SAME
   no-flush→false-hang misread, 3rd instance. The bisect smoke flushes
   every marker, so running the identical cfg through it → PASS.

**Verdict: WP1-① OSC bimanual test-bed WORKS.** OSC × openarm × dual-arm ×
camera × custom-reset all run; s0–s3 green were real, and the original is
green too. The whole "install-layer / reset-hang / gripper-gain" chase was
chasing diagnostic-instrument artefacts. The arm-gain zeroing (2026-08-04)
IS a correct OSC prerequisite and stays; the gripper-gain hypothesis is
moot (never needed). 

**Cost honestly logged:** ~4 diagnosis sessions burned on two flush/dup
script bugs. The three process rules (instrument re-calibration, hang
operational-definition, evidence-attached reporting) were written FROM
these; the 3rd no-flush recurrence shows Rule 2 ("≥2 liveness signals, not
'no output'") must be applied every time, not just written down — had I
checked CPU state (0.0%, but the proc was mid-close after a completed run,
not blocked) against log-size I'd have caught it a session earlier.

**WP1-① acceptance status:** #1 boots ✓, reset+step ✓. Remaining for a
true green: #2 motion-equivalence (does OSC actually track a pose target to
the ~5cm gate, not just step without error) + #3 seed determinism. These
are behavioural checks on a WORKING env, not blockers. WP1-① unblocked.
