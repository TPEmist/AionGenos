# L2 provenance: teacher and C_retrieval-L2 live in two different memory worlds

*Filed before L2 prep/eval (2026-07-15). A disclosed asymmetry, not a
flaw — but the first explanatory candidate if C_retrieval-L2 SR exceeds
the teacher's 28%.*

## The asymmetry

- **During collect**, the L2 buffer was JOINT-labelled and grew
  incrementally. Under the joint success-floor there was exactly **1
  [✓] episode** the whole run — so the teacher spent nearly the entire
  collect retrieving from a failure-dominated memory. Its 28% per-arm
  competence was achieved with essentially no retrievable success.
- **During C_retrieval-L2 eval**, the student uses the FROZEN,
  RE-TAGGED buffer (L2 Amendment 1a), in which **46 arm-aligned [✓]**
  episodes are now retrievable. The eval-time memory is strictly
  higher quality than the memory the teacher actually had.

This is a direct consequence of the re-tag (a correctness fix) plus the
frozen-snapshot design — both correct — but it means the comparison
"C_retrieval-L2 vs teacher-28%" is confounded with memory quality.

## Consequence, pinned now

**If C_retrieval-L2 SR > teacher 28%, this asymmetry is the first
explanatory candidate — before crediting the retrieval mechanism.**
The clean, un-confounded contrasts remain the within-eval ones that
share the same frozen re-tagged buffer (C_retrieval − A_ctrl_rat, the
identical-weights contrast; C_retrieval − B_main protocol contrast) —
those are unaffected because all eval arms see the same buffer. Only
the teacher-parity comparison carries this confound.

## Cross-reference: the memory-success-floor finding is alive here

This is the living instance of the finding recorded in v1.1_notes
("memory can only supply conditional knowledge if success experiences
exist to condition on"). The L2 teacher IS the below-floor case: at
collect time its buffer held 1 joint-success, so retrieval could only
tell it "others also failed here". The teacher's 28% was reached
essentially WITHOUT usable memory — which is itself evidence that the
28% is the raw distillation-source competence, and any C_retrieval-L2
lift above it is what retrieval adds once a usable (re-tagged) buffer
exists. The two notes cite each other: the finding predicts the
asymmetry, the asymmetry instantiates the finding.
