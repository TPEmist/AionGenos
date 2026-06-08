# Sensory-Integration Curriculum (V4 design note)

## Why this document

The original 5-level curriculum (L0 reach → L1 trace → L2 push → L3 pick &
place → L4 handover) treats *bimanual coordination* as an entry point. Empirically,
both 31B and E4B Gemma-4 teachers regress to a **left-right mirror policy**
on L0 (predicted right-arm target = ‑predicted left-arm target axis-by-axis,
even when the GT cubes are independently sampled). That is, they cannot yet
do single-arm reach reliably, but we are forcing them to do two simultaneously.

This document defines a pre-L0 sub-stage (L0a) and explains why it does not
violate either the project's task-agnostic principle or the cumulative-data
invariant of plan §2.2.

## Borrowed concepts (Ayres' sensory-integration theory)

We're not implementing SI therapy literally; we're borrowing four design
principles that map cleanly onto AionGenos:

1. **Single-channel before multi-channel.** SI therapy isolates one
   modality (vestibular OR proprioceptive OR visual) before integrating
   them, because integration with an unstable single channel learns hacks.
   → AionGenos: master single-arm reach (one EE + one target) before
     dual-arm reach.

2. **Body-quiet baseline during isolation training.** When training a
   single-arm task, the opposite arm must be physically still — otherwise
   attention diffuses and the system learns mirrored / coupled output.
   → AionGenos: `IsaacLabEnvInterface.execute_command(active_arm=...)`
     replaces the inactive arm's command with hold-in-place at the
     hardware level.

3. **Failure-mode diagnosis from observable trajectory deltas.** SI uses
   the `dyspraxia` measurement protocol (target vs actual movement
   trajectory deltas) as the primary diagnostic, not muscle force / EMG.
   → AionGenos: this is exactly the same observable-only constraint that
     plan §10 already requires for Stage 3 critic. Our existing
     `generate_critic_feedback` (P8 in the prompt inventory) is therefore
     a sound design, not an ad-hoc invention.

4. **Repetition until automation = parametric memory.** SI therapy's end
   goal is to push intentional control into reflex.
   → AionGenos: this is the existing Stage 4-A (BC with CoT) → Stage 4-B
     (CoT-strip) progression. SI gives 4-B a clearer raison d'être beyond
     "lower latency".

## Anti-patterns we explicitly avoid

- ❌ Naming sim signals after anatomical channels (vestibular,
  proprioceptive). The sim doesn't have these and the analogy doesn't
  add information.
- ❌ Modeling SI clinical concepts like sensory-defensiveness,
  hyporesponsiveness. Those have no zero-demo POC counterpart.
- ❌ Sub-staging *inside* every level. L1 / L2 / L3 / L4 are NOT being
  refactored. L0a only exists because empirical evidence (mirror bias)
  showed L0 was being entered above the VLM's competence ceiling.

## Why L0a is task-agnostic, not task-specific

User constraint: *we cannot design a custom difficulty ramp per task*.

L0a is structurally simpler than L0 (one EE, one target) but uses the
exact same:
- camera + RGB processing
- prompt template family (P2 `_S1_POS`)
- critic feedback format (P8)
- IK + scalar-guard pipeline
- replay schema

The only "knowledge" injected is *which arm is active* — and that is
delivered through the **task instruction** (`L0A_SINGLE_REACH_LEFT`:
"Move your LEFT end-effector ... your right arm is held still — you do
not control it."), which is exactly the legitimate per-level field
isolated in `vlm/task_instructions.py`. Architecture / prompt / control
are unchanged.

L0a's implementation (`aiongenos/tasks/L0a_single_reach/`) reuses
`AionGenosReachEnvBaseCfg`. No new physics, no new sensors, no new
control modes.

## Curriculum integration

```
LEVEL_ORDER = (-2, -1, 0, 1, 2, 3, 4)
               ^^^ ^^^
               L0a-L  L0a-R   (V4 sub-stages)
```

`AionGenosCurriculumManager` traverses `LEVEL_ORDER`; integer arithmetic
on `level` is replaced by `order.index(level)` so the negative ids are
safe.

Cumulative training data invariant (plan §2.2) holds: when L0 trains, it
sees L0a-L's success replays + L0a-R's success replays + its own —
exactly as if L0a were the literal "first level". This pulls the
single-arm direction grounding into L0's QLoRA fine-tune so dual-arm
inference inherits it.

## Open question (deferred)

**Cross-midline practice**: SI therapy includes deliberate cross-body
reaches (left hand → right side of body) to consolidate spatial mapping.
Whether to bake this into L0a (e.g. `L0a_left_ipsilateral` /
`L0a_left_contralateral`) depends on what we observe after V4. If the
mirror bias resolves and L0a→L0 transfer works, we don't need it. If
single-arm reach succeeds only when target is ipsilateral, we add this.

## What V4 does NOT change

- No prompt schema differences between L0a and L0/L1/L2/L3/L4.
- No new ControlMode (still `POSITION_ONLY`).
- No new replay schema fields.
- No changes to plan §2.2 advance rules (≥60% SR, cumulative data,
  12-hour blocked timeout).

This makes V4 a strict **prepend** to the existing pipeline.
