# Handoff → paper session: PREPUB audit kickoff, PI rulings, step-5 master commit

**From** isaac, 2026-10-15. I am not running inside a Herdr pane (HERDR_ENV
unset), so per the Herdr rules I cannot type into w4:p4. This file is the
channel. Reply with a handoff file the same way.

## PI rulings (2026-10-15, forwarded verbatim in substance)
- **F3 PASS.** PI confirmed the permission covers arXiv, workshop and GitHub.
  Source: PI mailbox. Recorded as "PI confirmed 2026-10-15".
- **E5d PASS.** Deadline 10/23 AoE, PI eye-confirmed.
- **Bib:** cite the formal published versions; keep the arXiv ID as a note.
- **The 14.6 pp upper-bound sentence stays.**
- **R1 slope:** not in the caption; it stays in TMLR. One limitations
  sentence on the A15.1 gate setting.
  - I see acfd91d already applies the bib and R1 rulings. The audit will
    verify them, not trust them (Rule 4).

## Roles (Rule 5)
- **isaac = auditor.** From today: the full PREPUB_AUDIT v1.1 table on
  - `paper-v1.1-cameraready` @ **fab376a**, and
  - the TMLR full-length version on `paper-v1.1-wip` @ **acfd91d**
    (`docs/paper/arxiv/`; tell me if the TMLR source lives elsewhere).
- Output: a table plus a FAIL list, committed with the audited SHAs in the
  commit message. **Due before noon 10/16.**
- If you push new commits before then, I audit the SHAs above and note any
  drift. Please hold non-urgent edits until the report lands, so the audit
  target stays fixed.
- **Re-checked with priority (last round's 17 FAILs):**
  - G4/B5 sensitivity side by side;
  - E5 template;
  - D3, all five places;
  - R1 labels;
  - A-6 gate coverage;
  - E1 bib now citing published versions;
  - birth certificates for the three page-5 items;
  - the "same memory" qualifier sentence;
  - the 2610.01787 sentence.
- Negative tests follow Rule 3: sed break → sed restore → md5 check.
- **paper = fixer.** Fix from my FAIL list. I re-audit until all green.

## Step 5 (PI): clean master commit, pushed only after the PI fills HF/Zenodo URLs
The PI asked you to prepare it. Proposal, to avoid two writers on master:
- You prepare it on branch **`release-step5`** cut from current master, with:
  - the prereg documents;
  - `REPRODUCE.md` with URL placeholders;
  - the birth-certificate script;
  - the buffer packing script.
    - That script already exists on master:
      `scripts/release/build_buffer_release.py`, tar `7a405eb1…`.
    - Reference it; do not fork it.
- I review it as auditor (PREPUB applies to a public README).
- The PI pushes after the URLs are in.
- During that time I will not touch those paths on master.
