# Distil the Competence, Externalise the Memory
## A pre-registered study of where an embodied agent's experience should live

*BAR @ NeurIPS 2026 — 4-page workshop draft (double-blind, non-archival).
Written against `bar_workshop_spec.md`; every claim traces to v1.1, labels
preserved. Author identity + repo link removed for double-blind review.*

---

### Abstract (workshop, ~120w)

Where should an embodied agent's accumulated experience live — folded into
its policy weights, or kept external and retrieved at inference? We study
this under pre-registration on a vision-conditioned reach task. Distilling
a memory-augmented teacher into student weights recovered essentially none
of the memory benefit (+1 pp over an action-only control, n.s.); attaching
the *same* memory as an inference-time retrieval context to a *fixed* set
of student weights recovered it in full (+34 pp, z=5.15), matching the
teacher's 49% success at ~50–75× lower inference cost. A pre-registered
probe localises the mechanism: distillation transfers the *marginal*
correction (a static prior) but not the *conditional*, situation-specific
one that retrieval supplies. On a second, harder task the effect points
the same direction but is not significant (+6 pp, sub-MDE). The recipe:
distil the competence, externalise the memory.

---

### 1. Consolidation: where should a skill's memory live?

Biological memory is not stored where it is used. Systems consolidation
moves memories from the hippocampus, a fast episodic store, into
neocortex, where they become slow, structured, and automatic — yet skilled
behaviour remains *conditional*, adapting note-by-note to the situation in
front of the agent. This is exactly the design tension for an embodied
learning agent: experience can be **consolidated into weights**
(cortical, parametric) or **kept external and retrieved** (episodic,
contextual). For an agent that must act at control rate, a growing
retrieval context is a cost the loop cannot afford, so the field's
instinct is to bake experience into weights. Whether that *works* — for
embodied skill, under controlled conditions — is the question we ask.

*(Analogy is framing only; the claims below are exactly those of the full
study.)*

### 2. Design that isolates the substrate

A memory-augmented teacher (a VLM retrieving lessons from its own past
attempts) produces trajectories on a vision-conditioned single-arm reach
task. From the *same* trajectories we distil LoRA student policies whose
targets differ only in whether retrieved-lesson content is present, and we
evaluate under matched protocols — including one that re-attaches the
teacher's frozen retrieval buffer to a *fixed* set of student weights. The
critical pair shares identical weights and differs only in protocol:
memory baked in during distillation vs memory supplied by retrieval at
inference. This turns "parametric vs contextual memory" into a controlled
contrast on one axis.

**Pre-registration.** Because the headline is a null, hypotheses, arms,
tests, and their directionality were registered before any adapter
trained; the analysis rules were locked after collection but before any
p-value. Every result is tagged confirmatory or exploratory against that
plan.

### 3. Result: the reversal, and its mechanism

**Distillation into weights did not carry the memory benefit.** The
memory-augmented behaviour distilled into student weights beat an
action-only control by +1 pp (n.s.); the registered test was underpowered
for its own minimum effect, so we *withdraw rather than refute* the
memory-in-weights claim.

**Retrieval on fixed weights did.** On the *same* adapter weights,
attaching inference-time retrieval added +34 pp (identical-weights
contrast, z=5.15, exploratory); the pre-registered protocol contrast
agrees at +23 pp (z=3.36, confirmatory). Retrieval matched the teacher's
own 49% success rate at ~50–75× lower inference cost.

**Mechanism (pre-registered R1 probe; main figure).** The five-arm
round-1 ΔX distribution shows distillation transfers the *marginal*
distribution shift — a static prior every distilled arm adopts regardless
of situation — but not the *conditional* structure, the situation-specific
correction that retrieval supplies. This selects the registered
H_behavior branch: the correction's carrier is the action distribution,
not the memory content.

> **[MAIN FIGURE]** R1 ΔX per-arm distribution (five arms): distilled arms
> collapse onto one static prior; the retrieval arm's correction varies
> per episode. *(Copy from v1.1 Results §4.3; figure to be exported at
> camera-ready.)*

### 4. The criterion, and how far it travels

**Marginal knowledge — the correction that holds on average across
situations — transfers into weights; conditional knowledge — the
correction that depends on the situation — belongs in context**, because
weights can only approximate a conditional function with a constant
whereas context conditions on it for free. This is the transferable
takeaway; the results above are its evidence, scoped to this recipe
(single-round SFT + composable-KTO, LoRA rank-16), task, and data scale.

**A second task.** On a harder, second reach task in the same family, the
identical-weights retrieval advantage points the same direction but does
not reach significance (+6 pp, 95% CI [−4.5, +16.4], sub-MDE); the round-1
correction mechanism replicates while the effect size does not, and
exploratory diagnostics tie the attenuation to memory coverage and a
distance-gated conversion threshold. *(Reported at its honest strength;
n.s. is not a positive replication of the effect size.)*

**A boundary.** A bounded feasibility probe porting the same interface to
contact-rich manipulation did not clear the task: it localises two
separable walls — a contact-precision ceiling on free-object contact and a
primitive-expressivity gap on articulated degrees of freedom — both
properties of *this interface paradigm* (integer-coordinate subgoals over
an open-loop position servo with a fixed macro-primitive set), not of the
prompted-VLM teacher, whose reasoning stayed sound. Closed-loop contact
control and an expanded primitive vocabulary are the two unlocks a richer
task suite would require.

### 5. Takeaway

Distillation moves the average; retrieval supplies the situation. For an
embodied agent, the consolidation question has a substrate-dependent
answer: **distil the competence, externalise the memory** — and the open
problem is consolidating a *conditional* function, not a marginal prior.

---

*Anonymised for double-blind review. Full methods, the amendment-tracked
pre-registration, and all diagnostics are in the archival version (under
review). Code available (link withheld for anonymity).*

---

## Draft notes (not part of submission)
- Length check: this is the content skeleton; at LaTeX pass, trim to fit
  4 pp + refs in the NeurIPS workshop template. Cut CONTENT (e.g. shorten
  §2), never the qualifiers (n.s., exploratory, sub-MDE, scope clauses).
- Every number verified against v1.1 sources per bar_workshop_spec.md
  provenance list: +1pp/+34pp(z=5.15)/+23pp(z=3.36)/49%/~50–75× from
  d11_results; +6pp CI[−4.5,+16.4] n.s. from l2_methods §5.1; two-boundary
  from d11_discussion §5.3.
- Double-blind: no author, no affiliation, repo link withheld. Confirm
  BAR's arXiv-during-review (dual-submission) clause before submitting.
- Anonymisation for the ANALOGY: systems-consolidation framing is generic
  neuroscience, carries no identity signal — safe.
