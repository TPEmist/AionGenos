# L2 Amendment 3 — per-arm EVAL (single-arm inference matches single-arm training)

**Status**: LOCKED before any L2 eval number existed. The Step-8 eval
crashed at episode 1 (a `NotImplementedError` — the eval prompt template
for `POSITION_RPY_2DOF` was never built), so **no L2 eval result had
been observed** when the per-arm decision was made.

**Provenance (honest disclosure of the filing path).** The five-point
per-arm-eval specification below was **decided in conversation on
2026-07-22, before the eval was restarted** — the decision predates any
L2 success number. It was first committed the same day as `6cf31b7` on
the `paper-v1.1-wip` branch, but that commit was **not carried onto
master** during the 2026-07-28 paper/isaac worktree untangle (a stray on
the paper branch — same class of miss as `server_side/gguf_tools/`, later
re-filed as `d527952`). This file is the **formal re-filing onto master
on 2026-07-28**; its body is restored verbatim from `6cf31b7` except this
Provenance block. The pre-result timestamp integrity rests on the
2026-07-22 conversation record and the `6cf31b7` commit time — both
precede the eval restart and its 14/20-of-100 numbers; the 2026-07-28
date on this file is a re-filing, not the decision date.
**Date decided**: 2026-07-22.  **Date re-filed to master**: 2026-07-28.
**Original stray commit**: `6cf31b7` (paper-v1.1-wip, 2026-07-22).
**Anchor**: the L2 GGUF export fix is on master as `154e974`
(cherry-picked from the same stray line `ae75ada`); adapters load,
seed-determinism PASS — the eval was launchable, only the prompt contract
was missing.
**Governs**: the L2 eval action shape only. D11 (L0a) frozen paper v1.0,
its pre-registration, and L2 Amendments 1/1a/2 are untouched; this
amendment *completes* the eval side of Amendment 1's per-arm design.

## 1. What broke, and why it is a spec gap not a code bug

Amendment 1 §3 defined the per-arm **training** target: the SFT/KTO
target emits the **scored arm only** (`LEFT_TARGET_POS` *or*
`RIGHT_TARGET_POS` + `STOP`), position-only, with the non-scored arm's
outcome recorded as a flag (`other_arm_reached`), never folded into the
target. A_ctrl_rat-L2 was trained exactly this way.

The **eval** side was never wired to match. The L2 collect path resolves
`_active_arm_for_level("L2_dual_push") → None` (only names ending
`_left`/`_right` get a single arm), so eval (a) parses **both** arms
(`parse_stage1` raises on a missing `RIGHT_TARGET_POS`), (b) steps both
arms, and (c) gates success on **both** arms `< 0.05 m` — the joint
definition that produced SR = 1/100 and motivated the per-arm re-score
in the first place.

Asking a single-arm-trained model to emit both arms at eval measures
**format-adaptation, not task competence** — an out-of-distribution
probe of a capability the student was never trained for. The governing
principle is the one this project has applied throughout: *the student
is evaluated in the shape it was trained to emit.*

## 2. Decision: per-arm eval, non-scored arm frozen at initial pose

**Per-arm eval is the only correct resolution.** The eval prompt asks
for the scored arm's slot only (matching the training target
byte-for-byte in structure); the parser tolerates the absent non-scored
arm; the non-scored arm is **frozen at its initial pose** via the
existing V4 `active_arm` hold-in-place mask (`execute_command`
overrides the inactive arm with its current EE pose); success gates on
the **scored arm only** (`‖EE_scored − target_scored‖ < 0.05 m`).

### 2.1 Freezing the non-scored arm is a structural advantage, not a workaround

A left-scored L2 episode (left arm moves, right arm frozen) is
**isomorphic to the L0a-Left layout** (active arm moves, other arm held
by the env). This makes the L2↔L0a cross-task comparison *cleaner*, not
noisier: the same single-active-arm control structure is evaluated on a
harder task.

**Disclosed delta (honest):** at *training* time the non-scored arm was
in motion (both arms pursued their own goals in the collected
trajectories); at *eval* time it is frozen. This is defensible for
pose-reach specifically because the task is two arms driving to two
**separate** goals with minimal inter-arm coupling — freezing one arm
does not change the physics the scored arm must solve. It would NOT be
defensible on a contact-coupled task (e.g. a genuine cooperative push
where the arms share a load); the L2 task is not that (see §4 naming).

## 3. Scope: main eval = LEFT-scored only, 2 protocols × n=100

The main L2 numbers are **left-scored only**, both protocols
(A_ctrl_rat bare + C_retrieval), n = 100 each, seed_base 4600 shared
(paired McNemar design preserved).

**Why left-only is a scope decision, not a compute shortcut.** Amendment
1a already anchored the retrieval side to the **left** arm:
`success_label_arm='left'`, and the retrieval query anchor is the
initial left-EE state. A right-scored C_retrieval would need a
**different retrieval anchor** (right-EE query + right success-label
floor) — a new degree of freedom and therefore a new amendment. We do
not open it. The left-scored contrast is a complete, valid test of the
identical-weights retrieval question on a harder task; that is what L2
was scoped to answer (Amendment 2).

**Right-scored** eval, if ever run, is restricted to an **exploratory
bare-arm re-check** (A_ctrl_rat only, no retrieval, so no anchor
change), scheduled *after* the main numbers and only in idle A4500
windows (LIBERO priority). It is explicitly not part of the
confirmatory contrast.

## 4. Naming hygiene (paper wording)

The L2 task is described as "6-DoF pose-reach", but the **target and
success criterion are position-only** — there is no RPY term in either
the trained output slot or the `< 0.05 m` success gate. The paper must
describe the task as **"position-goal reaching in a 6-DoF control
space"** (or equivalent), and must not let the "6-DoF / pose" name imply
a rotational success dimension that is not measured. RPY exists in the
control space and the state readout; it is not a scored objective.

## 5. What is NOT changed

- D11 (L0a) frozen paper v1.0 / tag `paper-v1.0`: untouched.
- L2 Amendments 1/1a/2: pool construction, per-arm re-score, re-tagged
  buffer, retrieval floor (`success_label_arm='left'`), power/MDE
  scoping — all carry over unchanged.
- Seed pairing (base 4600, shared across protocols), McNemar/z fallback,
  `flags_only_a6` filter, R1 per-arm probe: unchanged.
- The identical-weights primary contrast (C_retrieval − A_ctrl_rat) and
  the Amendment-2 conditional-expansion criterion: unchanged in
  substance; now measured per (left-)arm.

## 6. Implementation contract (mechanical, so eval matches training)

1. **Prompt** (`prompts.py`): `rationale` and `rationale_with_retrieval`
   variants gain `POSITION_RPY_2DOF` entries that emit the scored arm's
   `*_TARGET_POS` + `STOP` only, headed by
   `INTRINSIC_RATIONALE (this attempt's own reasoning):` — the exact
   training-target structure. No RPY line, no non-scored-arm line.
2. **Parser** (`parse_stage1`): a `scored_arm` mode extracts only the
   scored arm's POS (and no RPY, matching the single-arm target); the
   non-scored arm is filled with a hold sentinel that
   `execute_command(active_arm=...)` overrides anyway. `scored_arm=None`
   → byte-identical to the legacy bimanual path (L0a/L3/L4 untouched).
3. **Collect**: L2 eval passes `scored_arm` as `active_arm` → non-scored
   arm frozen + success gated on the scored arm (reusing the L0a F33
   single-arm success branch).
4. **Driver**: left-scored 2-protocol run; and a permanent pre-eval
   **format-contract assert** (§7).

## 7. Structural fix — the format-contract gate (this is the 4th such incident)

Train/eval output-format mismatch has now been caught **four** times,
every time by crashing into it at runtime rather than before:

1. B_main prose target vs parsed target shape,
2. D_gist variant mis-selection,
3. driver Step-9 missing `--eval_template_variant`,
4. **this** — L2 eval parsing both arms for a single-arm-trained model.

Each was intercepted, but reactively (at episode 1 / mid-run). The
permanent fix is a **format-contract assert** that runs in the driver
*before* any eval collect: take a few **verbatim training-target rows**
from the SFT JSONL, feed each through the **eval parser** configured
exactly as the eval will configure it (control mode + variant +
scored_arm), and assert every row parses clean. A single-arm target fed
to a both-arms parser fails this assert at dry-run — the entire bug
family dies before the simulator boots. Installed as a resident driver
step for L2 and every future task.

Sentinel note: interception rate on train/eval-contract defects becomes
**4/4**, and with the §7 gate, prospective rather than reactive from
here on.
