# D11 Results — draft v1 (for narrative review)

*Claim discipline: every quantitative claim tagged [CONFIRMATORY] or
[EXPLORATORY]. All negative results carry recipe/task scope qualifiers.
Pre-registered α is stated; no "trending" language.*

---

## 4.1 A pre-registered null: memory does not bake into weights (T1)

Two timestamps matter and we keep them separate. The **hypothesis**
T1 was registered *before any training* (pre-registration §2, filed
2026-07-06; refined by Amendments 9–10 which sharpened the arm
semantics and reallocated α). The **analysis rules** — pairing gate,
test-selection fallback, two-sided form — were locked *after
collection but before any p-value was computed* (Amendment 14). The
raw success counts are visible in the collect logs; what A14 froze is
only how they would be tested, not what was hypothesised.

T1: a student distilled from memory-augmented-teacher trajectories
with retrieved-lesson gist in its target (`B_main`) would exceed a
student distilled from the same trajectories with action-only targets
(`A_action_only`), evaluated with zero inference-time retrieval. The
pre-registered rejection region was Δ SR ≥ +10 pp **and** statistically
significant (two-sided, α=0.020), with an explicit falsification clause.

The data reject the hypothesis. **[CONFIRMATORY]** `B_main` 26/100 vs
`A_action_only` 25/100 — a +1 pp difference (z=0.16, p=0.87; McNemar
sensitivity p=1.0, agreeing). Neither T1-strong (≥+10 pp) nor T1-weak
(>0 & significant at α=0.010) passes. **Per the pre-registered
falsification clause, we withdraw the memory-in-weights claim.**

Scope: this null concerns *this distillation recipe* — single-round
SFT + composable-KTO (LoRA rank-16), on the L0a-Left reach task. It
does **not** claim baking-in is impossible; stronger consolidation
(multi-round, replay, surprise-gated writing) is untested and named as
future work (§6).

## 4.2 The controlled reversal: external memory nearly doubles success (T4)

The comparison that inverts the framing is **T4**, `C_retrieval` vs
`B_main`. These two arms share the *same adapter weights* — `C_retrieval`
is `A_ctrl_rat`'s adapter run with an inference-time frozen-buffer
retrieval preamble; `B_main` is the weight-baked arm run with none. The
contrast is therefore a clean *protocol* comparison: same learned
parameters, memory supplied via context vs baked into weights.

**[CONFIRMATORY]** `C_retrieval` 49/100 vs `B_main` 26/100 — +23 pp
(z=3.36, p=7.8×10⁻⁴; McNemar p=1.0×10⁻³, agreeing), significant at the
pre-registered α=0.010. Relative effect ≈1.9×. Wilson 95% CI:
C_retrieval 49% [39.4, 58.7], B_main 26% [18.4, 35.4] — non-overlapping.

Read against §4.1: baking-in captured essentially none of retrieval's
benefit (+1 pp), while context retrieval captured +23 pp on identical
weights. The pre-registration §4 had anticipated a *small* gap
("bake-in replaces retrieval"); the **interpretation** inverts, not
the test.

*Registration note (immunisation against the "you saw the direction
first" objection):* the two-sided form of every pairwise test was
registered pre-collection — §4 of the original pre-registration (dated
2026-07-06) reads verbatim "all two-proportion z, α=0.05, **two-sided**".
The significance threshold for T4 (α=0.010) was set in Amendment 11,
also before collection. A14 restated the two-sided form; it did not
introduce it. T4 is thus a pre-registered, two-sided confirmatory
result whose rejection was reachable in either direction — the +23 pp
outcome was not privileged by the test design.

**The constructive corollary (the take-home for practitioners).**
`C_retrieval` reaches 49% — indistinguishable from the memory-augmented
teacher's own success rate (≈49.3%, post-fix pool)† — at student
inference cost (~200 ms/round) rather than teacher cost (10–15 s/round,
memory-augmented VLM). The competence transferred; only the *memory*
did not. The operational reading is therefore not "distillation
fails" but a design recipe: **distil the competence, externalise the
memory.** A high-Hz student carrying a frozen retrieval buffer
recovers full teacher-level task performance at ~50–75× lower
inference cost, without baking memory into weights at all.

†Footnote: the teacher 49.3% is an *indicative* comparison — pooled
post-fix teacher runs (n=221), not seed-matched to the D11 eval, so
this is a level-setting reference, not a controlled contrast.

## 4.3 Mechanism — distillation bakes the margin, retrieval supplies the condition (R1 ΔX probe)

The R1 ΔX behavioural probe (round-1 target X minus initial EE X;
reference fingerprints D6 memoryless teacher −23.5 cm, memory-teacher
last quartile −15.8 cm) localises *what* transferred. This probe was
**pre-registered with a per-arm prediction matrix** (Amendment 9 §9.4)
that named two branches: an H_language branch (bias correction carried
by rationale text — only gist/thought arms would shift) and an
H_behavior branch (correction carried by the action distribution — all
mem-teacher-distilled arms shift regardless of rationale).

**[CONFIRMATORY — pre-registered probe, registered branch selected]**
All four distilled arms cluster at the memory-teacher fingerprint, not
D6's, and the decisive control `A_action_only` (never trained on any
rationale) shifts identically — cleanly selecting the **H_behavior
branch**: the carrier of the bias correction is the action
distribution, not the memory content.

| Arm | R1 ΔX μ | σ | closer to |
|---|---|---|---|
| A_action_only | −16.62 | 8.61 | mem-teacher (−15.8) |
| A_ctrl_rat | −15.75 | 10.11 | mem-teacher |
| B_main | −16.67 | 8.53 | mem-teacher |
| D_gist | −18.15 | 7.89 | mem-teacher |
| **C_retrieval** | **−7.10** | **14.39** | (bias nearly erased) |

All four arms were pinned
(Amendment 8) to the same memory-teacher trajectories, whose coordinates
were already memory-corrected; distillation moved the corrected
behavioural *average* into weights, and all four arms inherited it
equally — which is exactly why T1 is +1 pp.

**[EXPLORATORY — σ interpretation beyond the registered branch]** What
distillation does **not** transfer is visible in the variance.
`C_retrieval`'s μ=−7.10 with σ=14.4 (the largest) is the signature of a
*conditional* correction: retrieval applies a different, situation-
specific adjustment per episode, averaging near zero bias with wide
spread. The four distilled arms apply the *same* static −16.7 shift to
every episode regardless of need. This motivates the mechanism reading:
distillation bakes in the marginal distribution shift (a static prior);
the value of memory lives in the conditional structure (situation-
specific correction), which does not survive distillation and is the
source of retrieval's +23 pp. This variance-based account is
exploratory — it interprets σ, which the pre-registration did not
predict, whereas the μ-based branch selection above is confirmatory.

*Figure 2 (money figure): five-arm R1 ΔX distribution (violin/strip) —
four arms tight at −16.7±9, C_retrieval at −7.1±14.4. μ and σ together
show static prior vs conditional correction in one panel.*

## 4.4 Which episodes need memory — and what "conditional" is not

**[EXPLORATORY]** Exploiting the shared-seed paired design, 29/100
episodes are solved *only* by `C_retrieval` (all four no-retrieval arms
fail) — a "memory-dependent" episode set.

Two pre-registered-style mechanistic hypotheses for *what makes them
memory-dependent* were tested and both returned null:
- **Not starting difficulty**: rescue-only episodes are not init-pose
  outliers (init-pose deviation ratio 0.96; initial red-cube distance
  identical, 19.9 cm vs 19.9 cm). [null]
- **Not mid-trajectory recovery**: `C_retrieval` shows a non-monotonic
  diverge-then-converge signature in only 10% of rescue episodes (other
  arms show it *more*, 22%, on the same episodes). Its rescues are
  monotonic convergence from the first round. [null]

Both nulls narrow the mechanism rather than weaken it: retrieval's edge
is not any single timepoint (hard start, or a mid-course save) but
**per-round sustained supply of the correct direction** — it emits a
good target every round, whereas the baked-in static prior gives one
round-1 correction and no per-round situational update. Failing arms
stall for lack of continued correct supply, not for lack of recovery.
A round-resolved test of this is future work (§6).

*Figure 3: rescue matrix / UpSet plot over the five arms.*

## 4.5 Limitations

- **Rationale-fabrication is a measurement gap, not a null.** The D11
  collect did not persist raw VLM text (the constrained-decode path
  stored only parsed coordinates), so per-arm rationale-fabrication rate
  and self-produced-gist content are *not computable* from these runs.
  We report this honestly and do not substitute a proxy. The replay
  schema now stores reset-time pose + seed; paper 2's re-run adds
  raw-response logging.
- **Pairing gate literal failure.** The confirmatory analysis used the
  pre-registered mechanical fallback (two-proportion z) because the
  pairing-integrity gate failed its literal check — replay does not
  persist pre-action cube pose and trajectory[0] is already one
  servo-step in. A frozen-arm diagnostic (seed identical 100/100,
  frozen right-arm identical 100/100, active left-arm 1/100) shows the
  pairing is physically real; the reported McNemar sensitivity
  (agreeing with z on all contrasts) recovers the design's power. Per
  the pre-registration, the z verdict governs.
- **Single task, single recipe.** L0a-Left only; one distillation
  configuration. Generalisation across tasks and stronger consolidation
  recipes is untested.

## Table 1 — Confirmatory contrasts (n=100/arm, two-sided)

| Test | Contrast | Δ SR | z (primary) | p_z | McNemar p | agree | verdict @ pre-reg α |
|---|---|---|---|---|---|---|---|
| T1-strong | B_main − A_action_only | +1 pp | 0.16 | 0.87 | 1.0 | ✓ | FAIL (α=0.020) → null |
| T1-weak | B_main − A_action_only | +1 pp | 0.16 | 0.87 | 1.0 | ✓ | FAIL (α=0.010) |
| T1a | B_main − A_ctrl_rat | +11 pp | 1.93 | 0.054 | 0.046 | ✓ | n.s. (α=0.020) |
| T4 | C_retrieval − B_main | +23 pp | 3.36 | 7.8e-4 | 1.0e-3 | ✓ | PASS (α=0.010) |
| T3 | B_main ≥ 0.7×mem-teacher | 26% vs 36.2% | −2.12 | — | — | — | BELOW floor |

## Table 2 — Arm / protocol definitions (from pre-reg §10.3)

| Protocol | Adapter | Training target | Inference retrieval |
|---|---|---|---|
| A_action_only | own | canonical action only | none |
| A_ctrl_rat | own | native thought + action | none |
| B_main | own | gist + native thought + action | none |
| D_gist | own | gist + action | none |
| C_retrieval | A_ctrl_rat's | (reuses A_ctrl_rat) | frozen D10-ext buffer |

---

## Open: title

Needs to hold BOTH "pre-registered null (weights)" and "retrieval wins"
without reading as two papers. Candidates to workshop:
- "Memory Does Not Bake In: A Pre-Registered Null and the Marginal-vs-
  Conditional Account of Experience Transfer"
- "The Margin Transfers, the Condition Does Not: Why Distilled Memory
  Underperforms Retrieval in an Embodied Agent"
- "Baked-In vs Looked-Up: A Controlled, Pre-Registered Comparison of
  Parametric and Contextual Memory for Embodied Skill"
