# D11 Introduction — draft v1 (discussion in reverse)

*Claim discipline carried from Results/Discussion: contributions
point to specific results (T1/T4/R1); the criterion leads the
contribution list (transferable takeaway), the null supports it. Scope
qualifiers on every "cannot". Intermediate scope on the data-limitation
question (§4.4b), not the strongest reading.*

---

## 1. Introduction

### Opening problem

When an embodied agent accumulates experience, where should that
experience live — folded into the policy's parameters, or kept outside
and retrieved when needed? The question is old and unresolved. The
parametric view is seductive: a fluent agent, like a fluent human,
should not have to look things up mid-task; skill that has been
practised enough becomes automatic, and automaticity feels like
something written into the substrate. The contextual view is
pragmatic: retrieval systems that keep experience external and look it
up have repeatedly matched or beaten parametric memorisation in
language tasks, at a fraction of the training cost. For embodied agents
the stakes are concrete — a policy that must run at control rate cannot
carry a growing context window, so "bake it into the weights" is not
just philosophically appealing but architecturally convenient. Whether
it *works* is an empirical question that, for embodied skill, has — to
our knowledge — not been asked under controlled conditions.

### Why this test bed answers it

We ask it with a design that isolates the one variable that matters. A
memory-augmented teacher — a VLM that retrieves lessons from its own
past attempts — produces trajectories on a vision-conditioned
single-arm reach task (an Isaac Lab bimanual rig with the right arm
frozen). From those *same* trajectories we distil student policies
whose training targets differ only in whether retrieved-lesson content
is present, and we evaluate them under matched protocols — including
one that re-attaches inference-time retrieval to a fixed set of student
weights. The critical pair shares identical adapter weights and differs
only in protocol: memory supplied by baking it into those weights
during distillation, versus memory supplied through a retrieval context
at inference. This turns "parametric vs contextual memory" from a
slogan into a controlled contrast on one axis.

### Pre-registration as a stance

Because the headline outcome is a null — and nulls are the most easily
disbelieved result in machine learning — we pre-registered in two
locked layers. The hypotheses, comparison arms, primary tests, and
their directionality were registered *before any adapter trained*; the
final analysis rules (the pairing-integrity gate and its mechanical
test-selection fallback) were locked *after collection but before any
p-value was computed* — the raw success counts, visible in collect
logs, were frozen out of the test-selection decision by that locked
rule. The pre-registration is not decoration: it is what lets a reader
take the null as evidence rather than as a failure to find an effect we
wanted. Every result below is tagged confirmatory or exploratory
against that registered plan.

### Contributions

1. **A design criterion for where experience should live**: marginal
   knowledge — the correction that holds on average across situations —
   transfers into weights, while conditional knowledge — the correction
   that depends on the current situation — belongs in context, because
   weights can only approximate a conditional function with a constant
   whereas context conditions on it for free. We name and operationalise
   this marginal/conditional distinction and show it predicts the split
   we observe. *(This is the transferable takeaway; the results below
   are its evidence.)*
2. **A pre-registered null on parametric memory** (T1): distilling the
   memory-augmented teacher's behaviour into student weights beat an
   action-only control by +1 pp (n.s.), and we withdrew the
   memory-in-weights claim per the registered falsification clause —
   scoped to this recipe (single-round SFT + composable-KTO), this
   task, this data scale, and this adapter capacity (LoRA rank-16). A
   no-training diagnostic (§4.4b) finds no conditional trace that more
   data of the same kind could amplify.
3. **A controlled reversal** (T4): on identical weights, supplying the
   same memory through inference-time retrieval beat baking it in by
   +23 pp (z=3.36), recovering the teacher's own success rate at
   roughly 50–75× lower inference cost.
4. **A mechanism** (R1 ΔX probe, pre-registered per-arm prediction):
   distillation transfers the *marginal* distribution shift (a static
   prior all arms adopt regardless of situation) but not the
   *conditional* structure (the situation-specific correction that
   retrieval supplies), cleanly selecting the registered H_behavior
   branch — the correction's carrier is the action distribution, not
   the memory content.

### One-sentence preview

The two headline results are one finding: distillation moves the
average, retrieval supplies the situation — so the recipe is to distil
the competence and externalise the memory.
