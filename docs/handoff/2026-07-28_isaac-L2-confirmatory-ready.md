# Handoff: L2 confirmatory report + diagnostic appendix ready for v1.1

**From:** isaac session (L2 pipeline & analysis)
**To:** paper session (v1.1 writing)
**Date:** 2026-07-28

## Deliverable

`docs/paper/l2_confirmatory_report.md` — the L2 Stage-1 confirmatory
result + diagnostic appendix, ready to translate into the v1.1 L2 chapter.

## One-line result

C_retrieval − A_ctrl_rat = **+6.0 pp (20% vs 14%), n.s.** (z=1.13, p=0.26;
Newcombe 95% CI [−4.5, +16.4]); below the pre-registered +20pp MDE. The
diagnostics explain why it is **small, not absent**: retrieval restores the
round-1 correction on ~all episodes (mechanism intact) but conversion to
success is competence-gated — it rescues only episodes that start near the
goal (init dist_red 13.9cm vs 21.6cm, p=1e-4).

## Verdict authority (please respect the boundary)

The report's §4 lists exactly what the paper **may** and **may not** say.
The verdict wording is bound to `workspace/l2_audit/PRE_ANALYSIS_LOCK.md`
(committed before any p-value) and the six pre-registered diagnostic
prediction/result commits. **Translate the prose; do not re-interpret the
verdict, do not drop the exploratory labels on §2/§3, do not upgrade +6pp
into a positive replication or the n=9 rescue clustering into a
confirmatory claim.**

## For the v1.1 L2 chapter, this slots as

- the honest cross-task result (replicates in direction/mechanism, n.s. in
  magnitude, sub-MDE — the disciplined "withdraw not refute" register the
  v1.0 abstract already uses for T1);
- the memory-success-floor / minimum-viable-competence law seen from the
  memory face (ties to v1.1_notes.md's existing finding and §5.3's
  competence-floor framing);
- a clean methods note: pairing gate mechanically fell back to z on ~1e-4
  float drift (A14 §14.2), no discretion.

## Open item paper may want isaac to pin
The headroom-normalized ≈43% gap-closed uses a lock-time teacher-per-arm
SR estimate ≈28%. If the chapter wants it exact, isaac can compute the
per-arm teacher SR from a6e6c917 on request. Currently reported as ≈.

## UPDATE 2026-07-29 — report revised (4 surgical edits, all landed)

The report was sharpened per PI direction; re-read
`docs/paper/l2_confirmatory_report.md` before drafting:

1. **Two-level separation (§3a/§synthesis):** pre-empts the reviewer's
   "similarity explains attenuation but not rescue" objection. Coverage
   (3a) = between-task correlate of effect SIZE, n=2, consistent-with (no
   causal ∝). Start-distance (3c) = within-task conversion gate; match
   quality does NOT predict within-L2 success. Two levels, no contradiction.
   Plus the D11 recovery-timing-null two-paper thread (front-loaded
   correction; range set by how far the corrected trajectory travels).
2. **§3b dose-dependent marginal (EXPLORATORY):** L0a distilled R1 hit the
   teacher (−16.7≈−15.8); L2 only −4.8 vs −17.1 (~72% short) — even the
   marginal didn't transfer fully; candidate = training dose (56 ep/511
   rounds vs 992). "marginal transfer is cheap but not free."
3. **Teacher per-arm SR PINNED:** left_reached 28/100 → **28.0%**;
   gap-closed **42.9%** (was "≈"). Provenance
   `workspace/l2_audit/TEACHER_PERARM_SR_PINNED.md`. Exploratory label
   unchanged, only the "≈" removed.
4. **Minimum-viable-competence law (§4b, paper-2 seed):** ONE Discussion
   sentence, three faces (teacher/buffer/student-4c). Not a paper-1 claim.

Verified fact underpinning "single/front-loaded correction" wording:
C_retrieval retrieves ONCE per episode (init_L_EE anchor, round-0-only
injection) — confirmed in code 2026-07-29, not per-round.

The §4 may/may-not list was updated to match all four.
