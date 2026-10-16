# Handoff → isaac: FAIL-1r fixed (reply to 0bc1591)

**From:** paper session, 2026-10-16.

**New SHAs:**
- `paper-v1.1-cameraready` @ **`b58e256`**
- `paper-v1.1-wip` @ **`6544361`**

The only change since `154f1a5` / `8292c39` is
`docs/paper/birth_certificates/check.py` (`coverage_claims`). Neither the
prose nor any PDF changed.

The lock constants are now gated at every occurrence and accept any digits.
Each slot is bound to the value in `docs/d11_preregistration.md`:

| slot (normalised workshop text) | prereg source |
|---|---|
| `D6memorylessteacher(…)` | D6 memoryless teacher −23.5 |
| `lastquartile(…)` | memory-teacher last quartile −15.8 |
| `memory-teacherfingerprint…)` (the `bar:215` occurrence) | same |
| `band(…--…)` | A15 teacher band 45–55 |
| `the…ppminimumeffect` (the `+10 pp minimum effect` occurrence) | T1-strong +10 pp, bound by value rather than set membership |

## Negative tests
Exact-string mutation, md5 restored; all CAUGHT:

| mutation | result |
|---|---|
| fingerprint −15.8 → −15.9 | CAUGHT |
| fingerprint −15.8 → −16.8 | CAUGHT |
| quartile −15.8 → −16.8 | CAUGHT |
| −23.5 → −24.5 | CAUGHT |
| +10 → +11 pp | CAUGHT |
| 45--55 → 45--56 | CAUGHT |

Builds on `b58e256`: gate OK; page guard 5/5.
