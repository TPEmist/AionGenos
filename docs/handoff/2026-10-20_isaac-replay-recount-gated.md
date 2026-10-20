# Handoff → isaac: replay recount is in the gate (reply to 11d94bf)

**From:** paper session, 2026-10-20.

## New SHAs
- `paper-v1.1-wip` @ **`d2976cf`**
- `paper-v1.1-cameraready` @ **`7bdb057`**

Only `docs/paper/birth_certificates/` changed; the prose and the PDFs did not.

## Spec, item by item
1. **Generator.** `birth_certificates/replay_recount.py` is copied from
   `889ea34` and changed as follows:
   - takes `--data-root`, or `$AIONGENOS_DATA_ROOT`; one of them is required;
   - no longer derives a path from `__file__`;
   - prints to stdout and writes no file.
2. **Deterministic and self-contained.**
   - The `# Date:` line is dropped, and the command line is generic.
   - The identical-weights report side is computed by the script from the
     `workspace/d11_audit/mcnemar_matrix.json` `success` vectors (44 / 10).
   - Your auditor notes are in `birth_certificates/README.md` (new file, the
     same README as release-step5-clean plus a section on recount
     provenance). They are no longer in the .txt.
   - Two runs give byte-identical output.
3. **REGENERATE.** `GENERATORS` now holds 3 scripts; the gate prints
   "3 generators".
4. **`recount_claims()`.** It fails when:
   - there is any MISMATCH row;
   - `# Mismatches detected` is not 0;
   - there are not 11 run rows, or a run does not have 100 files;
   - any of the 11 success counts differs from `derived_stats.txt`:
     `[sens <arm>] as-run K/100` (5 D11 runs), `[L2 sens <arm>] … as-run K`
     (2), and the first number of `[A15 <prot> vs_C_retrieval] K vs …` (4).

## My own negative tests (yours run on top of these)
| test | mutation | result |
|---|---|---|
| (a) | `replay_recount.txt` A_ctrl_rat 15→16 | CAUGHT (drift + RECOUNT ≠ derived) |
| (a2) | `# Mismatches detected: 0→1` | CAUGHT |
| (b) | `derived_stats.txt` `[sens A_ctrl_rat] as-run 15→16` | CAUGHT (drift + RECOUNT) |
| (c) | in an overlay copy of the data root, one `56ee684b` failure replay's `outcome` flipped to success (mtime preserved) | CAUGHT (`replay_recount.py` REGENERATE drift) |
| (d) | in the same copy, that replay file removed | CAUGHT (drift in `r1_rounds_recompute.py` and `replay_recount.py`) |

After each test the files were restored and md5-checked, or the gate came
back OK on the copy.

**For your (c)/(d) copy:** episodes are paired by **file mtime**. Copy with
`cp -a` / `rsync -a`. My overlay symlinked everything except
`data/replays/56ee684b`, which was a `cp -a` copy.
