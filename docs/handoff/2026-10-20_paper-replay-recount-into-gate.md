# Handoff → paper session: replay recount into the birth-certificate gate (PI 2026-10-20)

**From:** isaac, 2026-10-20.

**PI ruling.** `replay_recount` goes into the gate. It is not a one-off
record.
- **Reason:** when the analysis is re-run or the replay schema changes, this
  is the only check that raises an alarm at the replay → report layer. A
  one-off check protects only today's version.

## Spec (you implement; isaac audits with negative tests — rule 5)
1. **Generator.** Move `scripts/audit/replay_recount.py` (master `889ea34`) to
   `docs/paper/birth_certificates/replay_recount.py` on the paper branches.
   - Take `--data-root` or `$AIONGENOS_DATA_ROOT` (required), like the two
     existing generators. Today it derives the repo root from `__file__`,
     which breaks outside master.
   - Output: `docs/paper/birth_certificates/replay_recount.txt`.
2. **Deterministic, self-contained output.**
   - Keep or drop the hard-coded `# Date:` line, but do not compute it.
   - Make the script emit the identical-weights report-side cells itself
     (from `workspace/d11_audit/mcnemar_matrix.json` `success` vectors).
   - Move my hand-appended auditor note into
     `birth_certificates/README.md`. As it stands, a regenerate would drop
     the note and fail the byte comparison.
3. **REGENERATE.** Add `replay_recount.py` to `GENERATORS`, so every build
   re-counts from the replays and compares byte for byte with the committed
   `.txt`. This is what makes a replay change alarm. The PI's 11-value
   check alone only compares two committed files.
4. **New CLAIMS check (the PI's "five lines").** The 11 success counts in
   `replay_recount.txt` must equal `derived_stats.txt`:

   | source in `derived_stats.txt` | counts |
   |---|---|
   | `[sens <arm>] as-run K/100`, D11 | 5 |
   | `[L2 sens <arm>] … as-run K`, L2 | 2 |
   | first number of `[A15 <prot> vs_C_retrieval] K vs 49/100`, A15 | 4 |

   Also fail if `replay_recount.txt` reports any MISMATCH.

## isaac's negative tests on your SHA
- (a) Edit one success count in `replay_recount.txt` → caught.
- (b) Edit one `as-run` count in `derived_stats.txt` → caught.
- (c) Run the gate against a temporary copy of the data root with one
  replay `outcome` flipped → REGENERATE drift caught.
- (d) Delete one replay file in that copy → caught (file count ≠ 100).
