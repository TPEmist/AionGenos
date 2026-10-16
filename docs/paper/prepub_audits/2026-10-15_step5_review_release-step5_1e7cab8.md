# Step-5 release review — `release-step5` @ `1e7cab8` (PI 2026-10-15: auditor reviews before the PI pushes)

**Auditor:** isaac.
**Date:** 2026-10-15.
**Reviewed:** `release-step5` @ `1e7cab8`, and everything a push of it would
publish.
- The branch descends from `origin/master` (`6fa83cf`), so pushing it
  publishes **8 commits**:
  - 3 release commits: `172f24a`, `4132e1f`, `1e7cab8`;
  - 5 master commits already in its ancestry: `e66f8eb`, `b848667`,
    `752a831`, `56b387c`, `e0cbcdd`.

**Verdict: NOT YET — 1 FAIL (S-1), 1 PI decision (S-2).** Push only after S-1
is fixed and S-2 is decided.

## Checks requested by the PI
| check | result | evidence |
|---|---|---|
| content list, file by file: no company documents | PASS | 7 files differ from origin: README.md, docs/paper/REPRODUCE.md, docs/paper/birth_certificates/{README.md, derived_stats.{py,txt}, r1_rounds_recompute.{py,txt}}; plus the 5 ancestry commits' files (push_* code, diagnostics, provenance, one handoff). No .docx/.pdf, no packet, no permission document. "company" appears only as the generic data-policy sentence ("generated on company hardware; the permission covers publication, not data release") |
| no local paths | **FAIL (S-1)** | `derived_stats.py:9` (usage example) and `:137`, and `r1_rounds_recompute.py:83`: `--data-root` default `/home/control/AionGenos`. README / REPRODUCE: 0 hits (`/home/`, host IPs, `exx@`) |
| no `.env` | PASS | the tree has `.env.example` only: a template, no keys, tokens or passwords; public on origin since `a201c10` (2026-06-02). Advisory: it still holds the internal host IP (`10.80.9.148`), which the README rewrite removed elsewhere |
| `git log -- docs/paper/company_*` empty in the commit's history | PASS | `git log release-step5 -- 'docs/paper/company_*' '*company_disclosure*' '*company_clearance*'` → 0 commits. (`--all` gives 9, all on the local paper branches `paper-v1.1-wip` / `-cameraready`, which must never be pushed as-is) |

## Additional checks (PREPUB applies to a public README)
- **README numbers** (+1 pp, +34 pp / z 5.15, +23 pp / z 3.36, 49.3%,
  48 vs 49, 53/53/55 from 25/26/19, +6 pp, 48–55, rank 16): all equal the
  gated certificate values (`derived_stats.txt`).
  - Advisory: the README states SRs without the auto-reset sensitivity count.
    Align it with whatever resolves audit #2 FAIL-2.
- **Links:** every relative link in README.md and REPRODUCE.md resolves in
  the `release-step5` tree, including `docs/d11_preregistration.md` §12
  (amendment log, l.176), `docs/paper/l2_*.md` and `birth_certificates/`.
- **REPRODUCE:**
  - adapter and pack sha256 equal the local release files re-hashed today
    (`4807767d…`, `7f7f7363…`, `7a405eb1…`);
  - its download URLs point to the `paper-v1-artifacts` release, which does
    not exist until the PI creates it.

## S-1 (FAIL) — paper session
Replace the `/home/control/AionGenos` default in both generators with a
required `--data-root` (or `$AIONGENOS_DATA_ROOT`), and make the usage line
generic. Then re-run both generators and confirm the committed `.txt` stays
byte-identical, i.e. the gate's REGENERATE check still passes.

## S-2 (PI decision) — what else goes public
- **(a)** `e0cbcdd` (in the push set) adds
  `docs/handoff/2026-10-15_paper-prepub-audit-and-step5.md`, which states
  that the PI confirmed the company permission covers arXiv, workshop and
  GitHub (source: PI mailbox). It is not a company document, but it does
  disclose the permission's scope.
  - Option: keep it, or drop or redact it before the push (rebase
    `release-step5` without that file).
- **(b)** master has **5 more commits after `e0cbcdd`** (`11d00cf`,
  `36e105c`, `7424bf1`, `79e60e6`, `85ea8f4`). They are **not** in this push
  set and must stay local until scrubbed. They include:
  - audit #2, which quotes the arXiv source comment "company publication
    permission granted 2026-08-27; affiliation = NRCA";
  - handoffs naming the GPU host paths.
- After pushing `release-step5`, rebase local master onto it. Do **not**
  rebase `release-step5` onto current master, because that would pull those
  5 commits into the public push.
