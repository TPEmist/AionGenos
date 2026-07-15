# L2 1% SR — diagnosis (48h timebox, resolved in ~1h)

## Verdict: compounding, NOT teacher incompetence or task bug

Decision-rule outcome (pinned before diagnosis): a config-level root
cause was found → L2 plan is revivable without changing the teacher.

## Evidence chain

**Step 1 (scaffolding):** L2 prompt feeds `LEFT_EE_TO_RED_CUBE` /
`RIGHT_EE_TO_BLUE_CUBE` = EE→goal-pose distance
(isaaclab_env_interface.py:434, ‖EE − target_pose‖). For THIS task that
is the correct error signal — because (Step 1b) the L2 "dual_push" cfg
tracks `left_ee_pose`/`right_ee_pose` commands with
end_effector_position_tracking rewards; the "goal cubes" are pose-target
VISUALIZERS, not pushable objects. **L2 as defined is a dual-arm
simultaneous 6-DoF pose-reach, not a push.** So scaffolding is not
mismatched — but the task is harder and different than its name implies.

**Step 2 (compounding — the actual cause):** per-arm vs joint success
on the 100-ep buffer (best-dist-over-episode, thr=0.05m):
- left arm reaches goal: 28/100 (28%)
- right arm reaches goal: 28/100 (28%)
- both (some timestep): 10/100
- both AT EPISODE END (collect's gate): 1/100
Teacher per-arm competence ≈28% is INSIDE the viable ≥25% band. The
1% is the success definition multiplying two ~28% events AND requiring
them simultaneously at episode end (0.28 × 0.28 ≈ 8% if independent;
timing coincidence drives it to 1%).

## Revival options (both legitimate, pick per paper goal)

A. **Per-arm scoring / single-arm L2.** Score each arm's push-reach
   independently, or run a single-arm L2 pose-reach. Teacher SR jumps
   to ~28% → viable desirable pool (~28 success eps/100) → D11
   replication runs. Cleanest cross-task point; the task stays
   "harder than L0a" (28% vs 49%) which is good for effect headroom.

B. **Keep dual, relax the joint gate to non-simultaneous** (both arms
   reached goal at ANY point in episode, not same timestep) → ~10% SR.
   Marginal; 10 success eps is a thin desirable pool. Weaker than A.

## Recommendation
Option A (per-arm scoring on the existing dual-push run, OR a fresh
single-arm L2 collect). Per-arm scoring is FREE — it re-scores the 100
episodes already collected, yielding ~28 desirable-arm trajectories
without re-running the 12h collect. A fresh single-arm collect is
cleaner but costs another ~12h. Decide per whether the paper wants
"two independent single-arm tasks" or "one re-scored dual task".

## Task-naming note (provenance)
The paper must NOT call L2 "push" — it is dual-arm pose-reach. Either
rename in all L2 references, or (better for a genuine push result)
build a real push task where a cube is the tracked object. The latter
is L3-scope, not this window.
