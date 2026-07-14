# D11 Abstract + Related Work — draft v1

---

## Abstract

Should an embodied agent's accumulated experience be baked into its
policy weights, or kept external and retrieved at inference? We test
this directly. A memory-augmented teacher (a VLM that retrieves lessons
from its own past attempts) produces trajectories on a
vision-conditioned single-arm reach task; from the *same* trajectories
we distil LoRA student policies and evaluate them under matched
protocols, including one that re-attaches the teacher's frozen
retrieval buffer to a fixed set of student weights — a clean parametric-
vs-contextual-memory contrast on identical weights. Because the
headline result is a null, we pre-registered the hypotheses, arms,
tests, and analysis rules before training and before any p-value.
Distilling the memory-augmented behaviour into weights beat an
action-only control by only +1 pp (n.s.); the registered test proves
underpowered for its own minimum effect, so we withdraw — rather than
refute — the memory-in-weights claim. By contrast, attaching retrieval
to a *fixed* set of student weights added +34 pp (z=5.15), matching the
memory-augmented teacher's own 49% success rate at ~50–75× lower
inference cost; the pre-registered protocol contrast agrees
(+23 pp, z=3.36). A pre-registered behavioural
probe localises the mechanism: behavioural distillation transfers the
*marginal* correction (a static prior every arm adopts) but not the
*conditional*, situation-specific correction that prompt-retrieved
memory supplies. The recipe that follows: distil the competence,
externalise the memory.

*(~200 words. Sentence 2 of a shorter version can carry the mechanism
slogan "distillation moves the average, retrieval supplies the
situation" if length permits.)*

---

## 2. Related Work

*(Coverage map — distinct from the Discussion's three-frontier
positioning, which states where we stand. Here: what the landscape is.)*

**Parametric vs. retrieved knowledge in language models.** A large line
compares injecting knowledge into weights (fine-tuning) against keeping
it external and retrieving it (RAG), repeatedly finding retrieval
competitive or superior at lower cost [RAG-vs-FT studies]; recent work
on self-editing / self-adapting weights (e.g. SEAL) pushes the
parametric pole. Our contribution is the embodied, controlled analogue
of this comparison — same weights, memory supplied two ways.

**Agent memory and experiential learning.** Voyager, ExpeL, and
Agent-Workflow-Memory accumulate and reuse experience as external,
retrievable artifacts (skills, lessons, workflows); this is the
external-memory pole our T4 result supports. We differ in isolating,
under pre-registration, whether that experience can instead be
consolidated into weights.

**VLA post-training and RL.** Recent vision-language-action work
refines pretrained policies with RL and preference signals (e.g.
SimpleVLA-RL and related); our students are distilled+KTO-refined VLAs,
and our null speaks to what such post-training does and does not move
into parameters.

**Lifelong / continual LoRA.** CORAL, TAIL, and related study adapter-
based continual adaptation; our marginal/conditional distinction
offers a lens on *what* such adapters can absorb — a static prior
readily, a conditional map not (at this recipe and capacity).

**Reasoning distillation.** Distilling Step-by-Step, Embodied-CoT, and
fast/slow thinking-action work distil chain-of-thought into cheaper
students; our rationale-in-target arms (A_ctrl_rat, B_main) are
instances of this, and our finding — that self-produced rationale at
inference did not help (+1 pp) while retrieved content did (+23 pp) —
qualifies when rationale externalisation pays.

**Pre-registration in ML.** We adopt pre-registration [pre-reg
advocacy refs] as a methodological stance: registering hypotheses,
tests, and analysis rules before seeing outcomes is what converts a
null from a non-result into evidence. We do not claim primacy; we claim
only that the study is explicitly pre-registered with a full,
amendment-tracked chain, which is uncommon in embodied learning and is
what licenses the null's interpretation.

*(TODO: fill bracketed citations — the named systems above are all
discussed in the project log; convert to bibkeys at bib pass.)*
