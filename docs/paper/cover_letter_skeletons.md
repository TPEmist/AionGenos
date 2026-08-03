# Cover-letter first paragraphs — two venue framings (skeleton, ~150w each)

*Same paper, two emphases. TMLR audits correctness + methodology; ICRA
buys design recipe + robotics relevance. Draft the opening now so
submission week starts from a paragraph, not a blank page.*

---

## TMLR version (correctness + methodological stance) — v1.1 finalised

We submit a pre-registered study of a single, sharply-scoped question:
when an embodied agent's experience is supplied as retrievable memory,
can it be consolidated into policy weights by behavioural distillation,
or must it stay in context? The paper's central result is a
*pre-registered null* — distilling a memory-augmented teacher into
student weights gained +1 pp over an action-only control — and we treat
that null with the statistical honesty it demands: we show the
registered test was under-powered for its own minimum effect, and we
therefore *withdraw rather than refute* the memory-in-weights claim. A
mechanism probe (also pre-registered) and an identical-weights
retrieval contrast (+34 pp, z=5.15) turn the null into a positive,
mechanistic account. We extend the study to a second, harder task in the
same family (a 6-DoF pose-reach): the identical-weights retrieval
advantage points the same direction but does not reach significance
(+6 pp, 95% CI [−4.5, +16.4], sub-MDE), while the round-1 correction
*mechanism* replicates — a result we report at its honest strength, with
the same pre-registered discipline (a per-arm eval amendment locked
before the eval, analysis rules before any p-value) and with exploratory
diagnostics labelled as such. We believe the value to TMLR is precisely
the methodology: a full amendment-tracked pre-registration across both
experiments, analysis rules locked before any p-value, and negative /
sub-significance results reported as evidence rather than buried.

---

## ICRA version (design recipe + robotics relevance)

For embodied agents that must act at control rate, a growing memory
context is a luxury the inference loop cannot afford — so the field's
instinct is to bake accumulated experience into the policy's weights.
We test that instinct directly on a manipulation task and find it does
not hold: distilling a memory-augmented teacher into student weights
recovers essentially none of the memory benefit (+1 pp), whereas
attaching retrieval to the *same* fixed weights recovers it in full
(+34 pp), matching the teacher's success rate at ~50–75× lower
inference cost. The take-home is an actionable architecture recipe —
*distil the competence, externalise the memory* — grounded in a
controlled, pre-registered comparison and a mechanism that explains
why: distillation transfers the average correction but not the
situation-specific one that retrieval supplies. We are extending the
result to a second manipulation task (push) to establish it as a
cross-task regularity.

---

## Notes for submission week (not the letter itself)

- TMLR opener leads with "pre-registered null + statistical honesty";
  ICRA opener leads with "control-rate constraint + design recipe".
- Both name the +34 pp identical-weights number (the ② fix) — never
  the mislabeled +23 pp as the headline.
- ICRA version's last sentence is a promissory note on L2; only ship
  it if L2 is in the submission (else soften to "future work").
  UPDATE 2026-08-03: venue = TMLR (not ICRA/ICLR); L2 is IN the
  submission with a realised n.s. result (task = pose-reach, NOT "push").
  TMLR version above updated to carry the honest L2 result; the ICRA
  version's "extending to push (future work)" line is now stale — do not
  ship it.
- Neither claims "first controlled" (⑦ fix); both claim only the
  pre-registration is explicit + amendment-tracked.
