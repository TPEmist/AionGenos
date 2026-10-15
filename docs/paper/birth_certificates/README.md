# Birth certificates for the paper's derived numbers

Every number in the paper that the registered analysis scripts do not
print directly is regenerated here from a file on disk. Examples are
Newcombe intervals, the identical-weights z, the pooled teacher reference,
the auto-reset sensitivity counts, the Amendment 15 controls and the cost
re-measure. The script names its sources at the top.

| generator | output (committed) | what it certifies |
|---|---|---|
| `derived_stats.py` | `derived_stats.txt` | D11 contrasts and intervals; pooled memory-teacher and D6b references; auto-reset sensitivity (Amendment 15 pin 8, D11 and L2); Amendment 15 (a)/(b) controls and R1′ slopes; cost re-measure; reproduction intervals; R1 grid unit |
| `r1_rounds_recompute.py` | `r1_rounds_recompute.txt` | R1 residual correlations per round (paper §4.4b, Table `residual_rounds`) |

```bash
python3 docs/paper/birth_certificates/derived_stats.py --data-root <AionGenos data root> > derived_stats.txt
python3 docs/paper/birth_certificates/r1_rounds_recompute.py --data-root <AionGenos data root> > r1_rounds_recompute.txt
```

**What can be re-run publicly.** Some inputs are in this repository:
`docs/paper/data/*.json`, `aiongenos/config.py`, `scripts/analysis/`. Others
are not released:
- the raw replays (`data/replays/`);
- the collect logs (`logs/`);
- the audit outputs (`workspace/d11_audit/`, `workspace/l2_audit/`, `workspace/a15_p1/`);
- the buffer working copy.

They were generated on company hardware, and the permission covers
publication, not data release (see `REPRODUCE.md`). The committed `.txt`
outputs are therefore the published record. Re-running them requires the
private data root.

**Not included.** The paper's build gate (`check.py`) compares these outputs
against the LaTeX prose. It runs inside the paper sources (the arXiv source
archive), not in this repository.
