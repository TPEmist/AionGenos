# D11 Discussion — draft v1 (for narrative review)

*Same claim discipline as Results: every outward-facing positioning
sentence points to a specific number (T1/T4/R1); every "cannot" carries
the recipe/task scope; the J-lens paragraph says "is the instrument to
test", never "will show".*

---

## 5. Discussion

### 5.1 What the results say to a system builder: distil the competence, externalise the memory

The two headline results are one finding seen from two sides. Baking
the memory-augmented teacher's behaviour into student weights bought
+1 pp over an action-only control (T1, null); supplying the same
memory to the *same weights* through an inference-time retrieval
context bought +23 pp (T4, z=3.36) and recovered the teacher's own
success rate (49% vs ≈49.3%) at roughly 50–75× lower inference cost.
The competence transferred under distillation; the memory did not.

We resist reading this as "distillation fails". The mechanism probe
(§4.3) shows *why* the split is principled rather than incidental, and
turns it into a design criterion. Memory's operational value here is a
*conditional* correction — a different adjustment for each episode's
situation (the C_retrieval R1 ΔX signature: mean near zero, σ=14.4,
per-episode variable). Baking a conditional function into a fixed
weight delta forces a single static approximation of it — the four
distilled arms all collapsed onto one −16.7 cm prior regardless of the
episode in front of them. A context channel, by contrast, is a natural
conditioning pathway: it can present a different retrieved lesson per
situation at inference with no parameter change.

So "where should this knowledge live" is not a matter of taste but a
function of the knowledge's own structure. **Marginal knowledge — the
average correction that holds across situations — transfers into
weights; conditional knowledge — the correction that depends on the
situation — belongs in context, because weights approximate it with a
constant and context conditions on it for free.** This is the criterion
D11 was ultimately built to test, and it is the transferable claim we
carry out of a single-task, single-recipe study: not "retrieval beats
baking-in" as a law, but a decomposition of *which* component of an
experience each substrate can hold.

### 5.2 Positioning against three frontiers

**ASPIRE (external memory as the substrate) — we supply supporting
evidence.** The retrieval-augmented pole, in which competence is
distilled and experience is kept external and looked up, is the world-
view our T4 supports: in a controlled comparison, on matched adapter
weights, context-supplied memory significantly outperformed weight-
baked memory (+23 pp, CI [+9.6, +35.3]). We claim this as, to our
knowledge, the first controlled *embodied* evidence for that pole —
with a scope guard:
ASPIRE's code-as-reusable-skill and our lesson-retrieval are two
instantiations of external memory, and our data support the pole, not
any single implementation of it.

**Titans (memory→weights at the architecture level) — we bound our
null and leave the door open.** Our T1 null is a statement about a
*behavioural distillation recipe* (single-round SFT + composable-KTO,
LoRA), not about parametric memory in general. Titans-style
architectural writing — surprise-gated updates that write only the
unexpected, with decay — is precisely a mechanism our recipe lacks: it
consolidates *conditionally* (what to write depends on the situation's
surprise), which is exactly the component §4.3 shows our recipe drops.
Whether such a mechanism can bake the conditional structure that flat
distillation could not is untested here and is the most direct
architectural follow-up our null points to.

**J-Space / J-lens (interpretability of the internal workspace) — we
have the behavioural half, this is the instrument for the mechanical
half.** Our R1 μ-branch result (§4.3) already establishes behaviourally
that the correction's carrier is the action distribution, not the
memory content: `B_main` still emits PAST_LESSONS text at inference,
yet that text bought +1 pp, suggesting it is epiphenomenal — produced
but not read by the downstream action tokens. J-lens is the instrument
to test that suggestion directly: ablating or swapping `B_main`'s
self-produced gist tokens (prediction: action distribution unchanged)
against ablating `C_retrieval`'s injected lessons (prediction: action
changes) would provide the mechanical account of the 23 pp gap —
"context content is read, self-produced content is ignored". We flag
this as the paper-2 target, not a claimed result.

### 5.3 The open problem: consolidating a conditional function, not a marginal prior

The deepest reading connects back to the study's motivating question —
whether the knowledge a system reads can be folded, through embodiment,
into its parameters. Human skill automation is the existence proof that
it can: a fluent pianist's playing is automatic yet still *conditional*,
responding note-by-note to what is in front of them. Automation
preserves the conditional structure; it does not collapse the skill to
its average. Our distillation product kept only the average.

That reframes the open problem. It is not "baked-in vs retrieved" —
that dichotomy is what T4 appears to settle, but it settles only the
question of substrate under one consolidation recipe. The real problem
underneath is **how to consolidate a conditional function rather than a
marginal prior**. That single question explains all three of our
results at once: T1 died because flat distillation consolidates the
marginal; T4 won because context still carries the conditional; and the
paths beyond — surprise-gated writing, per-round distillation targets
that supervise the situation-specific correction rather than its
average, and workspace-readout probes that check whether a consolidated
correction is actually used — are all attempts on that same problem.
A null on substrate is thus not a dead end; it is the reformulation
that turns "where should memory live" into "what would it take to
consolidate memory's conditional structure at all" — the question the
next decade of embodied continual learning has to answer.
