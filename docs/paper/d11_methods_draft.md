# D11 Methods — draft v1

*Mechanical translation of the frozen pre-registration. Every design
choice traceable to a pre-reg section or numbered amendment; the full
amendment chain is Appendix Table A1.*

---

## 3. Methods

### 3.1 Task and environment

We use a vision-conditioned single-arm reach task (L0a-Left) in an
Isaac Lab bimanual manipulation rig with the right arm held frozen
throughout — a controlled setting in which only the left end-effector
is actuated toward a target cube. An episode succeeds when the active
end-effector comes within 0.05 m of the target; each episode runs up
to a fixed round budget, where a *round* is one VLM reasoning step
followed by an inverse-kinematics servo to the emitted target. All
evaluation runs use `--freeze_level` (no curriculum auto-advance) so
every arm sees the identical task distribution.

### 3.2 Teacher and memory pipeline

The teacher is Gemma-4-31B-it (multimodal, 4-bit) served via llama.cpp,
augmented with an image-anchored episodic memory: after each episode it
writes a self-recap; at round 1 of a new episode it retrieves the
top-K visually-and-state-similar past recaps (DINOv2 image embedding,
state-aware ranking) and injects them as a PAST_LESSONS preamble. The
memory-augmented teacher's trajectories are the distillation source;
its retrieval buffer, frozen at a fixed snapshot (SHA-pinned), is what
the C_retrieval protocol later reuses at student inference.

### 3.3 Students, arms, and the 2×2 factorial

Students are LoRA adapters (rank-16, α=32, dropout 0.05) on the same
Gemma-4-31B-it base, targeting the language-model attention and MLP
projections only (`self_attn.{q,k,v,o}_proj`, `mlp.{gate,up,down}_proj`);
the vision tower is untouched. Each arm is trained in two stages on the
*same* pinned trajectory pool: SFT (stage 4-A, 992 desirable
progress-rounds, 1 epoch, lr 2e-4) followed by composable-KTO refinement
(stage 4-B, 992 desirable + 1799 undesirable rounds, 1 epoch, lr 5e-5,
β=0.1, auto-balanced class weights) with the frozen SFT adapter as the
KTO reference (the C.3-B composable dual-adapter scheme). All arms share
this recipe and hyperparameter set; per-arm effective step counts are
logged to `training_meta.json` for audit.

The four training arms form a 2×2 factorial over two binary factors —
retrieved-lesson gist in the target, and the teacher's native thought
in the target — all four terminating in the same canonical action lines
synthesised from parsed coordinates (a single synthesiser across arms,
so output format is not a between-arm confound):

| | no gist | with gist |
|---|---|---|
| **no native thought** | A_action_only | D_gist |
| **with native thought** | A_ctrl_rat | B_main |

All four arms are pinned to the identical 2791-round pool (992
desirable + 1799 undesirable), verified by SHA-256 before training
(Appendix A1, Amendments 12–13); this makes training-sample count a
controlled variable, not a confound.

### 3.4 Evaluation protocols

Five inference protocols are evaluated, 100 episodes each, all at the
same task with `--freeze_level`:

| Protocol | Adapter | Inference-time retrieval |
|---|---|---|
| A_action_only | own | none |
| A_ctrl_rat | own | none |
| B_main | own | none |
| D_gist | own | none |
| C_retrieval | A_ctrl_rat's | frozen teacher buffer snapshot |

C_retrieval is *not* a fifth trained arm: it reuses A_ctrl_rat's
adapter weights and re-attaches the frozen retrieval buffer as an
inference-time PAST_LESSONS preamble. Two contrasts therefore follow,
and we keep them distinct (a distinction the results section makes
central):
- **Identical-weights** (C_retrieval vs A_ctrl_rat): same adapter,
  retrieval toggled — the clean parametric-vs-contextual contrast.
  Not pre-registered as primary (reported exploratory).
- **Registered protocol** (C_retrieval vs B_main = T4): each arm its
  own adapter, so this varies both adapter and protocol; pre-registered
  and confirmatory (Amendment 8).

The C_retrieval buffer is read-only during evaluation; a tree-hash gate
confirms it was not written during the run (Amendment 12–13).

All five protocols share a fixed environment seed base (4500; per-
episode seed = 4500 + episode index), so episode *k* starts from the
same initial world configuration across protocols — a paired design
(Amendment 11).

### 3.5 Pre-registered hypotheses and tests

Registered before any adapter trained (pre-reg §2–§4, refined by
Amendments 9–10):

- **T1 (primary)**: B_main − A_action_only. Rejection: Δ SR ≥ +10 pp
  AND significant, two-sided, α=0.020. A graded reading within this
  budget line: T1-strong (≥+10 pp) and T1-weak (>0, significant at
  α=0.010). Explicit falsification clause on the memory-in-weights
  claim.
- **T1a**: B_main − A_ctrl_rat, two-sided, α=0.020.
- **T4**: C_retrieval − B_main, two-sided, α=0.010.
- **T3**: B_main SR ≥ 0.7 × pooled memory-teacher SR (=36.2%),
  one-sided.
- Family-wise α=0.060 (Amendment 10, non-uniform allocation).
- **R1 ΔX probe** (mechanism, pre-registered per-arm prediction matrix,
  Amendment 9 §9.4): round-1 target X minus initial EE X, per arm,
  against two reference fingerprints (memoryless-teacher −23.5 cm,
  memory-teacher last-quartile −15.8 cm), with a registered branch
  choice (H_language vs H_behavior).

### 3.6 Analysis rules (locked post-collection, pre-p-value)

The two-timestamp discipline (§4.1): the analysis rules below were
locked (Amendment 14) after collection but before any p-value, with the
raw counts frozen out of the test-selection decision.

1. **Pairing-integrity gate**: for each episode index, a 5-way
   `allclose` (ε=1e-4 m) on the initial configuration; on failure, a
   mechanical fallback (below) — no per-contrast discretion.
2. **Test selection**: gate pass → McNemar (paired) primary; gate fail
   → two-proportion z primary. Binary, all-or-nothing.
3. All pairwise tests two-sided (pre-reg §4, never altered).

In the event, the gate failed its literal check because replays do not
persist pre-action cube pose and the first trajectory sample is already
one servo-step in; a frozen-arm diagnostic (seed identical 100/100,
frozen right-arm identical 100/100, active left-arm 1/100) confirms the
pairing is physically real. Per the locked rule, the two-proportion z
governs; McNemar is reported as a sensitivity analysis and agrees on
all contrasts (§4.5b).

### 3.7 Data curation and its honest history

The training targets passed a deterministic three-rule rationale
filter (direction-consistency, ground-truth geometry, vacuity). Over
three blinded-audit rounds the first two rules were found to measure
*coherence*, not *correctness*, and were demoted to advisory flags;
only the vacuity rule retains (structurally guaranteed, Amendment 13)
zero drop authority under the `flags_only_a6` policy actually used, so
the filter drops no rows and the four arms' 992/2791 counts are
filter-invariant. We report this curation history rather than hiding
it: the demotion is part of the data's provenance, and the full audit
trail is in Appendix A2.

---

## Appendix A1 — Pre-registration amendment chain

Every change to the frozen plan was filed as a signed, dated,
SHA-anchored amendment before the step it governed. Amendments 1–13
were filed before any adapter trained; Amendment 14 was filed after
collection but before any p-value.

| # | Date | Change | Anchor |
|---|---|---|---|
| 1 | 07-06 | Sample-count control arm (B_matched) added | pre-reg §12 |
| 2 | 07-06 | Filter escalation rule (agreement <85% → LLM judge) | — |
| 3 | 07-06 | Filter audit stratum pinned | — |
| 4 | 07-07 | Rule-1 sentence classifier (past/intent) fix | — |
| 5 | 07-07 | Rule-2 demoted to flag; composite-agreement rejected | 6a29103 |
| 6 | 07-07 | Coherence filter → advisory flags (v-final 992+1810) | 9b0a9da |
| 7 | 07-08 | Pre-flight checklist (length align, seed, env reset) | bc524b8 |
| 8 | 07-08 | Cross-arm target hygiene + 2×2 + C_retrieval protocol | 1a44d61 / a7bada2 |
| 9 | 07-08 | T1 threshold, R1 probe branches, thought-leak, rename | 503496b |
| 10 | 07-08 | B_matched removed (confounder dissolved), α→T1a | bf2dbb5 |
| 11 | 07-08 | Paired design → McNemar; env_seed_base=4500; SHA gate | bfa7cc6 |
| 12 | 07-08 | Canonical filenames, D_gist eval slot, SHA-gate timing | ae196b5 / 0e26443 |
| 13 | 07-08 | Step-2 row-count sentinel; structural `flags_only_a6` | 9f5bec1 / cd1eb94 |
| 14 | 07-13 | Analysis-time decision lock (gate, fallback, two-sided) | 00be6d5 / 73e712b |

*(Amendments 5–13 filed 07-07/07-08 in the pre-flight window; SHAs are
the frozen commits. Full text of each is in the pre-registration
document.)*

*Counts shown are as pinned at each amendment's date; the final
training counts are 992 + 1799 (Amendment 8 re-pinned from A6's
992 + 1810 after a trajectory-set ID diff removed 11 no-retrieval-hit
rounds from a single episode). The methods body uses the final 1799.*

## Appendix A2 — Filter audit trail

Three blinded audit rounds on the deterministic filter's drop surface;
Rules 1–2 precision on the correctness axis was low (they measure
coherence), motivating their demotion to flags (Amendments 4–6). The
`flags_only_a6` policy used in the final pipeline is a structural
zero-drop guarantee (Amendment 13): all three rules compute and emit
advisory flags, none drops a row, so the 992/2791 pool is
filter-invariant and the cross-arm SHA pins hold.
