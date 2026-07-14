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

**[CONFIRMATORY]** `B_main` 26/100 vs `A_action_only` 25/100 — no
detectable effect: +1 pp (z=0.16, p=0.87, two-sided; Newcombe 95% CI
[−11.1, +13.1]; McNemar sensitivity p=1.0, agreeing).

We are deliberate about what this licenses. The registered minimum
effect (+10 pp) lies *inside* the confidence interval, and a post-hoc
minimum-detectable-effect calculation is unforgiving: at n=100 per arm
with SR≈0.25, significance at the registered two-sided α=0.020 requires
Δ ≥ 14.2 pp, so the design has only ~24% power for its own registered
+10 pp effect and *cannot* reach significance for a true +10 pp
difference at all — a flaw in our registered design that we disclose
rather than obscure. Accordingly, **per the registered clause we
withdraw the memory-in-weights claim (we stop asserting it), but we do
not assert the strong null at the success-rate level** — that would be
absence of evidence read as evidence of absence. The claim that the
*conditional* structure specifically fails to transfer does not rest on
this underpowered SR test; it is carried independently by the
mechanism-level diagnostic (§4.4b), whose conditional-trace null is not
subject to the SR power problem (with its own |r|<0.20 caveat).

Scope: this null concerns *this distillation recipe* — single-round
SFT + composable-KTO, on the L0a-Left reach task, at this data scale
and adapter capacity (LoRA rank-16); §4.4b and §4.5 sharpen the data-
and capacity-scope respectively. It does **not** claim baking-in is
impossible; stronger consolidation (multi-round, replay, surprise-gated
writing) is untested and named as future work (§6).

## 4.2 The reversal: retrieval on fixed weights nearly triples success

Two contrasts speak to bake-in vs retrieval, and we report both with
their exact adapter relationships — a distinction the earlier draft of
this section blurred.

**The identical-weights contrast (exploratory, decisive).** The genuine
same-weights comparison is `C_retrieval` vs `A_ctrl_rat`: `C_retrieval`
*is* `A_ctrl_rat`'s adapter, run with an inference-time frozen-buffer
retrieval preamble; `A_ctrl_rat` is the same adapter with none. On
*fixed* student weights, attaching retrieval moved 15/100 → 49/100 —
**+34 pp (z=5.15, p≈2.6×10⁻⁷; Newcombe 95% CI [+21, +45])**. This was
not pre-registered as a primary test, so we mark it exploratory — but
at p≈3×10⁻⁷ it survives any multiplicity correction; exploratory here
means "not registered", not "fragile".

**The registered protocol contrast (confirmatory).** The
pre-registered T4 is `C_retrieval` vs `B_main` — a *protocol* contrast
in which each arm carries its own adapter (C_retrieval = A_ctrl_rat's
weights + retrieval; B_main = the gist+thought-baked weights, no
retrieval). **[CONFIRMATORY]** 49/100 vs 26/100 — +23 pp (z=3.36,
p=7.8×10⁻⁴; McNemar p=1.0×10⁻³, agreeing), significant at the
pre-registered α=0.010. This contrast varies both adapter and protocol,
so it under-states the pure retrieval effect the identical-weights
contrast isolates.

The one-line pairing: *on fixed student weights, attaching retrieval
added +34 pp (exploratory, z=5.15); the registered
consolidation-vs-retrieval protocol contrast was +23 pp (confirmatory,
z=3.36).* Both point the same way — memory supplied through context at
inference vastly outperforms the same memory routed through
distillation into weights. The pre-registration §4 had anticipated a
*small* C_retrieval−B_main gap ("bake-in replaces retrieval"); the
**interpretation** inverts, not the test.

*Registration note (immunisation against the "you saw the direction
first" objection):* the two-sided form of every pairwise test was
registered pre-collection — §4 of the original pre-registration (dated
2026-07-06) reads verbatim "all two-proportion z, α=0.05, **two-sided**".
The significance threshold for T4 (α=0.010) was set in Amendment 11,
also before collection. A14 restated the two-sided form; it did not
introduce it. T4 is thus a pre-registered, two-sided confirmatory
result whose rejection was reachable in either direction — the +23 pp
outcome was not privileged by the test design.

One further disclosure about the A14 lock, since a skeptic is entitled
to it. The pairing-integrity gate's *literal* failure was foreseeable
at lock time — that replays do not persist pre-action cube pose is a
fixed schema property, not a post-hoc surprise — so the gate→z fallback
was a mechanical rule, not a branch chosen after seeing which test
favoured which conclusion. We therefore lean on the fact that the two
tests *agree on every contrast* (McNemar and z, §4.5b), not on a claim
that the fallback was executed blind. On the one contrast where the
branch could matter (T1a: McNemar p=0.046 vs z p=0.054), both remain
n.s. at the pre-registered α=0.020, so the choice changes no verdict.

**The registered transfer floor (T3), and the like-for-like reading
it forces.** [CONFIRMATORY] T3 asks whether `B_main` (distilled,
no-retrieval) clears 0.7 × the *memory-augmented* teacher's 51.7% pool
= 36.2%. It does not: 26% < 36.2% (one-sided z=−2.12). Reported
honestly, T3 **fails**. But the floor is a cross-rung comparison — it
measures a *no-memory* student against a *with-memory* teacher's bar,
a level mismatch baked into the registration. Aligning rungs
like-for-like (exploratory):

| rung | student | teacher (same rung) |
|---|---|---|
| no-memory | B_main / A_action_only ≈ 25–26% | memoryless teacher ≈ 30%† |
| with-memory | C_retrieval 49% | memory-teacher 49.3%‡ |

At *matched* memory conditions the student tracks the teacher on both
rungs; what fails is specifically the middle step — **consolidating the
memory advantage into weights**. So the practitioner take-home is not
"competence didn't transfer" (it did, at each rung) but the sharper
recipe: **distil the competence, externalise the memory** — a high-Hz
student carrying a frozen retrieval buffer reaches the memory-teacher's
own rung (49% vs 49.3%) at ~50–75× lower inference cost, whereas
routing that same memory through distillation into weights lands it
back on the no-memory rung.

†Memoryless-teacher ≈30% is derived, not directly seed-matched: D6b
memory main-effect (+19.2 pp) subtracted from the memory-teacher pool.
‡The two teacher figures use different pools and we keep them distinct
on purpose: T3's floor uses the pre-registration's pinned 51.7%
(pre-reg §4, the memory-teacher pool at registration time); the parity
reference uses the post-fix pool's 49.3% (n=221). Neither is
seed-matched to the D11 eval, so both are level-setting references, not
controlled contrasts — disclosed rather than picked.

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
*behavioural* distillation of a *prompt-retrieved* memory teacher bakes
in the marginal distribution shift (a static prior) but not the
conditional structure (situation-specific correction) that the
retrieved-lesson text carried — the conditional component does not
survive this recipe and is the source of retrieval's edge. We scope the
claim to prompt-retrieved memory and behavioural distillation
deliberately: a teacher whose memory is architecturally trained-in
(§5.2) presents a different distillation surface we do not test. This
variance-based account is
exploratory — it interprets σ, which the pre-registration did not
predict, whereas the μ-based branch selection above is confirmatory.

*Figure 2 (money figure): five-arm R1 ΔX distribution (violin/strip),
with two horizontal reference lines — D6 memoryless teacher (−23.5 cm)
and memory-teacher last quartile (−15.8 cm). Four distilled arms sit
tight on the −15.8 line at −16.7±9; C_retrieval sits at −7.1±14.4. μ
and σ together show static prior vs conditional correction in one
panel; the reference lines show all four distilled arms adopting the
memory-teacher fingerprint, not D6's.*

## 4.4 Which episodes need memory — and what "conditional" is not

**[EXPLORATORY]** Exploiting the shared-seed paired design, 29/100
episodes are solved *only* by `C_retrieval` (all four no-retrieval arms
fail) — a "memory-dependent" episode set.

Two exploratory mechanistic hypotheses for *what makes them
memory-dependent*, each stated in the audit log before its test,
returned null:
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

## 4.4b Is the null just too little data? A no-training diagnostic

The first reviewer question about a null this size is whether `B_main`
underperformed for lack of training data — 992 desirable rounds spread
over a continuous cube-position space may leave each situation-cell
sparse, and a conditional situation→correction map is far more
sample-hungry than a constant marginal shift. The concern is
well-founded: the marginal/conditional asymmetry has a sample-complexity
asymmetry built in, and this is arguably the *cause* of our headline
split, not a threat to it.

We can bound it without any retraining, using the paired seeds.
**[EXPLORATORY]** Treat `C_retrieval`'s per-episode R1 residual (its
round-1 correction minus its own mean) as a proxy for the
situation-specific correction each episode calls for, and correlate it
with each distilled arm's R1 residual on the same episode. If weight
distillation captured any conditional structure, the correlation should
be positive; a null correlation means the arm learned nothing beyond
the static prior.

| distilled arm | corr with C_retrieval residual | p |
|---|---|---|
| A_action_only | −0.12 | 0.24 |
| B_main | −0.12 | 0.23 |
| A_ctrl_rat | +0.03 | 0.78 |
| D_gist | −0.12 | 0.24 |

We ran this at rounds 1–3 (later rounds give the student fresh visual
observations and are where a conditional component could most plausibly
surface) with a 2000-draw permutation null:

| arm | r (round 1) | r (round 2) | r (round 3) |
|---|---|---|---|
| A_action_only | −0.12 | +0.15 | +0.02 |
| B_main | −0.12 | +0.19 | −0.10 |
| A_ctrl_rat | +0.03 | +0.20 | +0.00 |
| D_gist | −0.12 | +0.05 | −0.16 |

Every correlation, at every round, falls inside its permutation chance
band (±≈0.20 at these n); none is significant, and `B_main` never
exceeds the no-rationale control `A_action_only`. Two caveats bound the
reading. (i) `C_retrieval`'s correction is one noisy sample of a good
policy, not ground truth, so the correlation is attenuated toward zero.
(ii) With n≈100 the correlation's 95% CI is roughly ±0.20, so this
rules out a *moderate* conditional structure, not a vanishingly weak
trace. The uniform −0.12 at round 1 is itself a shared-residual
artifact of the common seed/trajectory source, confirmed in the
chance band by permutation.

Accordingly we take the *intermediate* scope, not the strongest one:
**we find no detectable trace of a conditional component that more data
of the same kind could amplify** (round 1–3 residual correlations ≈ 0,
|r| < 0.20). This is stronger than "insufficient at n=992" — a scaling
curve has to grow from a detectable trace, and the trace is absent —
but weaker than "unlearnable at any scale", which would over-extrapolate
from one data point. The data-scaling probe's omission is therefore an
evidenced decision, not an untested assumption; we did not run it.
`B_main` ≈ `A_action_only` also mirrors T1a at finer grain: the
gist-in-target contributes no detectable conditionality.

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
- **Adapter capacity is a sibling explanation to data quantity.** A
  rank-16 LoRA may lack the capacity to represent a conditional
  situation→correction function even with unlimited data — a limitation
  parallel to, not subsumed by, the data-scaling diagnostic in §4.4b
  (that probe holds capacity fixed and varies data; this holds data
  fixed and varies capacity). We do not run a rank sweep here. Together
  these sharpen the scope of the T1 null to: *this recipe, at this data
  scale and this adapter capacity*.
- **Single task, single recipe.** L0a-Left only; one distillation
  configuration. Generalisation across tasks and stronger consolidation
  recipes is untested.

## Table 1 — Confirmatory contrasts (n=100/arm, two-sided z primary)

| Test | Contrast | Δ SR | Δ 95% CI (Newcombe) | z | p_z | McNemar p | agree | verdict @ pre-reg α |
|---|---|---|---|---|---|---|---|---|
| T1 | B_main − A_action_only | +1 pp | [−11.0, +13.0] | 0.16 | 0.87 | 1.0 | ✓ | FAIL @ α=0.020 → **null** |
| T1a | B_main − A_ctrl_rat | +11 pp | [−0.2, +22.0] | 1.93 | 0.054 | 0.046 | ✓ | **n.s.** @ α=0.020 |
| T4 | C_retrieval − B_main | +23 pp | [+9.6, +35.3] | 3.36 | 7.8e-4 | 1.0e-3 | ✓ | **PASS** @ α=0.010 |
| T3 | B_main SR vs 0.7×teacher floor | 26% vs 36.2% | — | −2.12 | 0.98¹ | — | — | **BELOW floor** |

¹ T3 is a one-sided proportion-vs-constant test (H₁: SR > floor); floor
= 0.7 × 51.7% pooled memory-teacher SR = 36.2% (pre-reg §4). Reported
one-sided p is the upper-tail probability; B_main is below the floor.

**Two-tier T1**: T1-strong (Δ ≥ +10 pp & sig) and T1-weak (Δ > 0 & sig
at α=0.010) are graded readings *within* T1's single α=0.020 budget
line (Amendment 9 §9.2), not separate family members. Both fail here.

**α budget (Amendment 10 §10.2, family-wise 0.060)**: T1 0.020, T1a
0.020, T3 0.010, T4 0.010. (The original 0.05 five-test plan was
revised when B_matched was dropped and its 0.010 reallocated to T1a;
the documented over-spend to 0.060 buys power on the T1a safety-net
contrast and is itself pre-registered.)

**Reading the CIs**: T1a's [−0.2, +22.0] is the honest statement that
a real effect may exist but this study is underpowered to resolve it
(the interval barely includes zero); we therefore report n.s. at the
pre-registered α and make no directional claim. T4's [+9.6, +35.3]
excludes zero comfortably.

## Table 2 — Arm / protocol definitions (from pre-reg §10.3)

| Protocol | Adapter | Training target | Inference retrieval |
|---|---|---|---|
| A_action_only | own | canonical action only | none |
| A_ctrl_rat | own | native thought + action | none |
| B_main | own | gist + native thought + action | none |
| D_gist | own | gist + action | none |
| C_retrieval | A_ctrl_rat's | (reuses A_ctrl_rat) | frozen D10-ext buffer |

---

## Title (LOCKED)

> **Distil the Competence, Externalise the Memory:
> A Pre-Registered Study of Parametric vs. Contextual Memory in
> Embodied Agents**

Imperative-recipe form (cf. "Attention Is All You Need", "Textbooks
Are All You Need") — the main clause is the operational design
criterion a system builder can cite directly ("following [cite], one
should distil the competence and externalise the memory"). Grew from
the §5.1 thesis sentence. The mechanism slogan (*Distillation Moves the
Average, Retrieval Supplies the Situation*) demotes to abstract
sentence 2 and the §4.3 heading — not wasted. Risk of an
imperative title: reading as single-task overclaim; the "Pre-Registered"
subtitle is the armour, and the L2/L3 cross-task replication (in
progress) converts the recipe from observation to regularity.
