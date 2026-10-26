# Spec — Pin-4c geometry, blind-sweep baseline, (e) preamble arm, validator metrics

Lead: isaac. Date: 2026-10-26. Authority: the PI ruling of 2026-10-26 (`docs/p2_prereg/wp3a_push_provenance.md`, last entry).
Repo: `/home/control/AionGenos`, master.
- The implementer works only in the worktree `/home/control/audit/wt_p4c`, branch `wp3a-p4c`.
- Isaac/GPU runs are launched by the lead or ops; agents never launch them.

## 0. Why
- rung-1′ (`611a3e2a`) made 11/50 by replaying one memorized path, ≈[40,20,50] → [60,20,50] → [80,20,50], that ignores the cube (ρ_X = +0.11, p = 0.22).
- The geometry lets that work: the goal is always the cube + (0.07–0.10, ±0.04) m and the cube region is 4 × 10 cm (`push_s3a_cfg.py:131–138`).
- Pin-4c must make a blind path fail (SR ≤ 10%) while keeping every episode solvable.

## 1. Reachability scan (new diagnostic, run on GPU by ops)
- **Script:** `scripts/diagnostics/wp3a_reach_scan_p4c.py`, adapted from `scripts/diagnostics/wp3a_reach_real.py`. Same executor (`execute_push_segment`, TCP target, rest orientation, 90-step rounds), **cube in place, outcome measured in the world** (never compare the TCP with its own target).
- **Grid:**
  - cube centre x ∈ {0.34, 0.37, …, 0.52}, y ∈ {−0.02, 0.01, …, 0.22} (base frame; each axis on a 3 cm step);
  - direction θ ∈ {−90°, −75°, …, +90°} relative to +X;
  - push distance d ∈ {0.07, 0.10} m.
  - Configurations where the goal disc would leave the table, or where the cube intersects the hand keep-out at reset, are skipped and logged.
- **Scripted push per configuration:** set the cube pose and the goal directly at reset, then:
  1. hover over the approach point at standby z;
  2. descend to the approach point, `cube − u·(half + 1 cm)` at cube-centre z;
  3. push to the push end, `goal − u·half`.

  Each stage gets ≤ 3 rounds. Success = cube→goal xy ≤ 5 cm, measured in the world.
- **Record per configuration:** success, final cube→goal, min finger→cube, joint-limit margin, τ saturation, table guard clamps, and whether the cube was disturbed during the approach.
- **Output:** `logs/wp3a_reach_scan_p4c.json`, plus a heat map per θ (`logs/wp3a_reach_scan_p4c_theta*.png`).
- **Derived (script `scripts/analysis/wp3a_p4c_derive.py`):**
  - the largest symmetric θ_max (≥ 60° required by the PI) and the largest cube region (an axis-aligned box) such that a scripted push succeeds for d ∈ {0.07, 0.10} at ALL θ ∈ [−θ_max, θ_max] for every cube grid point inside the box;
  - if no box supports θ_max ≥ 60°, report the best trade-off and STOP (PI decision).

## 2. Pin-4c sampler (code)
- New command `CubeRelativePolarCommand` (or a mode of the existing one): θ ~ U(−θ_max, θ_max), d ~ U(0.07, 0.10); goal = cube + d·(cos θ, sin θ).
  - **No clamping** (clamping distorts d and θ). If an implementation needs a guard, use rejection against the derived box only.
- The cube spawn region = the derived box.
- **Single source of truth:** θ_max, the d range and the cube box are constants in `push_s3a_cfg.py` (or a `pin4c` block), imported by the sampler, the gate and the scan-derivation report.
- **Selection:** a flag/env id. Pin-4b remains available, so old runs stay reproducible. Proposal: a new gym id `Isaac-AionGenos-WP1-Push-P4c-v0`, plus a TopCam variant, selected by `run_push_collect.py --geometry {pin4b,pin4c}` (default pin4b ⇒ the old behaviour, byte-identical).
- **Runtime config-effect gate:** `scripts/diagnostics/wp3a_pin4c_gate.py`, modelled on `wp3a_pin4b_gate.py`.
  - Over N resets (e.g. 200 seeds) it checks, at runtime: goal−cube distance ∈ [0.07, 0.10], angle ∈ [−θ_max, θ_max], the angle histogram roughly uniform, and the cube inside the box.
  - Memory `config-effect-gate`: read RUNTIME state after reset, not the cfg source.

## 3. Scripted blind-sweep mode (code)
- `run_push_collect.py --scripted_targets "40,20,50;60,20,50;80,20,50"`:
  - replaces the VLM with that fixed TCP-target sequence;
  - uses the same executor, success rule and plateau rule;
  - the episode ends at success or plateau, or after the last target, with outcome `scripted_end`;
  - no memory, no recap writing, `label=pilot`, flagged `scripted_policy` in every meta and replay.
- The path is exactly the rung-1′ stereotyped sequence. Verify it from `data/collect_dumps/611a3e2a` and cite it.
- The validator must accept `scripted_end` and the `scripted_policy` flag.

## 4. (e) preamble arm (code)
- Flag `--preamble_coords {on,off}`, default on ⇒ byte-identical.
- `off` removes from the push preamble ONLY the coordinate fields:
  - `start TCP`;
  - `round-1 target … → TCP reached …`;
  - the header phrase "your round-1 fingertip (TCP) target", replaced by a neutral phrase. The exact replacement text goes to the design review.
- It keeps the past images, the outcome, the rounds and the **lesson text verbatim**.
- Do NOT edit lessons. Lessons may themselves contain coordinates, so `validate` reports the **leak rate**: the fraction of injected lessons that match a coordinate pattern such as `X=\d`, `(\d+, *\d+, *\d+)` or `Y=\d`.
- **Interpretation recorded for the PI:** "lesson text only" = no structured coordinates; images are kept, because memory is image-anchored. Flag this in the report.

## 5. Validator additions
- Use `scripts/analysis/wp3a_rho_segments.py` logic (import, don't copy) for:
  - ρ_X and ρ_Y over all episodes, before the first success, and from the first success on, with one-sided permutation p and band95;
  - unique round-1 targets per segment.
- **(c) pass verdict line:** `count≥5: yes/no; ρ_X significant: yes/no → PASS/NOT PASSED`.
- **Geometry telemetry:**
  - distributions of the goal−cube distance and angle, and of the cube position, from meta;
  - HARD fail if a pin4c run has a goal−cube distance outside [0.07, 0.10] ± 2 mm, or an angle outside ±θ_max ± 1°.
- **(e):** report preamble_coords on/off and the lesson coordinate-leak rate.

## 6. Tests (CPU; `CUDA_VISIBLE_DEVICES=`; only the push test files plus new ones; timeout 600)
- `--geometry` default and `--preamble_coords on` ⇒ byte-identical prompts, preamble and feedback (reuse `tests/golden`).
- Unit-test the polar sampler math on CPU: pure functions take (cube_xy, θ, d) and give the goal; no Isaac.
- Scripted mode: the fake env runs the 3 targets; `scripted_end` and the flag are recorded; no VLM call.
- Preamble off: no coordinate fields; lessons byte-identical; the leak counter catches a planted coordinate.
- Validator: negative tests for each new HARD check.

## 7. May / may not (implementer)
- **May:** edit inside the worktree; CPU tests; commit on `wp3a-p4c` (no AI attribution).
- **May NOT:** run Isaac/GPU; touch the main checkout, docs, `collect.py` or `stage3_critic.py`; push; kill.

## 8. Acceptance criteria
- AC1: defaults ⇒ byte-identical to master (pin4b, coords on, VLM policy).
- AC2: the scan script exists and a 2-config dry run is executed by ops (GPU); the derive script turns the scan JSON into θ_max and the box, with a test on a synthetic JSON.
- AC3: the polar sampler has no clamping; constants are single-sourced; the gate script exists, and a negative test (narrowing a constant) makes it FAIL.
- AC4: the scripted mode is correct (path cited from data); no VLM call.
- AC5: the preamble-off arm is correct, and the leak rate is reported.
- AC6: the validator has the new metrics and HARD checks with negative tests.
- AC7: all relevant CPU tests pass; the diff does not touch forbidden files.

## 9. Run order after acceptance (lead/ops, for reference)
1. Full reach scan, then derive θ_max and the box. **PI sign-off on the box only if θ_max < 60°.**
2. Pin-4c gate (runtime), 200 resets.
3. Blind sweep on **pin4b** (positive control: should reproduce roughly the rung-1′ success geometry), then on **pin4c** (must be ≤ 10%; otherwise widen θ toward θ_max and repeat).
4. rung-1′ on pin4c, seeds 5000–5049, memory ON, coords on. This doubles as the (e) "coords" arm.
5. The (e) lesson-only arm: rung-1′ on pin4c, coords off, same seeds, fresh buffer.

---
## REVISION 1 — design gate (critic1 3B/9M; mem2 1B/3M). OVERRIDES §1–§9 where they conflict.
- **R1 (c1-B1) — no rejection sampling of the goal against the cube box.** The box is derived (§1) so that every θ ∈ [−θ_max, θ_max] and d ∈ [0.07, 0.10] is solvable from every cube position inside it. So the sampler is pure U(θ) × U(d), with no guard. The scan-derive step enforces solvability, not the sampler.
- **R2 (c1-B2, mem2-M) — lesson leak.** In the coords-off arm, the preamble formatter replaces coordinate patterns inside the lesson text with `[coordinates omitted]`. It does this at render time; the stored recaps are unchanged. Patterns: `X=\d`, `Y=\d`, `Z=\d`, `\(\s*-?\d+\s*,\s*-?\d+\s*(,\s*-?\d+\s*)?\)`. Every replacement is counted and logged per episode as `preamble_coord_redactions`. The coords-on arm is unchanged; validate reports its leak rate as telemetry. *(Lead flags this to the PI as the operationalisation of "lesson text only".)*
- **R3 (c1-B3) — geometry HARD checks use the values the sampler commanded,** not the settled poses. The command term logs `(θ, d, cube_xy_at_sample)` into meta (`goal_sample`). HARD: d ∈ [0.07, 0.10] and |θ| ≤ θ_max, exactly (float tolerance 1e-6). The settled-pose distance and angle are TELEMETRY only.
- **R4 (c1-M) — the scan transit flies at standby z + 0.05 m** to the point above the approach point, then descends to cube-centre z. Record whether the cube was disturbed before the push stage. A disturbed approach = failure of that configuration, reported separately.
- **R5 (c1-M, asymmetric reach) — derive θ⁺_max and θ⁻_max separately.** The sampled range is symmetric ±min(θ⁺, θ⁻), as the PI's "±60° 以上" requires. If min < 60°, STOP and go to the PI with both values.
- **R6 (c1-M) — scan success = outcome only** (cube→goal ≤ 5 cm). Table-guard clamps, τ saturation and joint margins are telemetry.
- **R7 (c1-M) — config plumbing.** Add a `CubeRelativePolarCommandCfg(theta_range, dist_range, object_name)`, a `WP1PushP4cEnvCfg` (and a TopCam variant) in `push_s3a_cfg.py` with gym ids `Isaac-AionGenos-WP1-Push-P4c-v0` and `…-P4c-TopCam-v0`, and `--geometry {pin4b,pin4c}` in `run_push_collect.py`. Default pin4b ⇒ byte-identical. `meta.json` records `geometry`.
- **R8 (c1-M) — the scripted sweep is the geometric upper bound of that path:** no hesitation repeats. It is therefore a conservative (strict) baseline. State this in the report.
- **R9 (c1-M) — header text when coords are off:** "PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see the scene at its start, the outcome, and a short lesson you wrote afterwards. Use these to choose a better target for the current scene."
- **R10 (c1-M) — arms.** Steps 9.4 and 9.5 are both on pin4c, with fresh, separate buffers and the same seeds. `611a3e2a` (pin4b) is never used as an arm.
- **R11 (c1-M) — the validator applies the pin4c checks only when `geometry == "pin4c"`;** pin4b runs keep the old checks.
- **R12 (c1-M) — the (c) verdict is TELEMETRY (exit 0).** Significance = the one-sided permutation p < 0.05 on the `all` segment (10,000 permutations, seed 20261026), as in the amendment.
- **R13 (mem2-B) — PI's criterion kept; extra diagnostic.** The PI's ρ_X criterion stays as ruled. In addition, as TELEMETRY: the direction of the round-1 target relative to the cube vs the goal direction θ (circular correlation, permutation p), and ρ_Y. *(Lead escalates to the PI: under random θ, ρ_X alone can pass for a cube-tracking but direction-blind policy.)*
- **R14 (mem2-M) — if the blind sweep exceeds 10% at θ_max: STOP and go to the PI.** No automatic widening beyond θ_max.
- **R15 (mem2-M) — the blind-sweep SR is recorded in the P2 prereg as a gen-0 control** (lead docs). Its comparison rule is left to the PI / [PWR-SIM].
