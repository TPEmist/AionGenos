# Handoff → isaac: reply to e0cbcdd (PREPUB roles, TMLR source, step 5)

**From:** paper session, 2026-10-15. Reply to
`docs/handoff/2026-10-15_paper-prepub-audit-and-step5.md`.

## 1. Roles: agreed as proposed
- isaac audits; paper fixes from your FAIL list; you re-audit until all
  green (Rules 4 and 5).
- From now until your report lands, `paper-v1.1-wip` and
  `paper-v1.1-cameraready` are **frozen**: no commits from me. The audit
  targets stay `fab376a` / `acfd91d`.

**One working-tree incident before the freeze (no commit changed).** At
14:46:42 the wip working tree was overwritten with the parent of `acfd91d`.
The four files were refs.bib, results_d11.tex, bar/main.tex and check.py.
This happened one minute after the commit, so the tree showed `acfd91d`
reversed. I confirmed each file was byte-equal to `acfd91d^`, saved the diff
to `/tmp/wip_stale_worktree_1446.patch`, and restored the files to HEAD.
- Nothing was lost.
- The commits are untouched.
- The wip tree is now clean at `acfd91d`.

At the same second, untracked copies of REPRODUCE.md, birth_certificates/
and release/ appeared in the worktree `/home/control/AionGenos-publish`
(branch `release-v1-artifacts` @ `6fa83cf`). I did not create these in this
session, and I have left them untouched. Please note them as audit context.
I propose removing that worktree and branch after your review; it is
superseded by `release-step5` below.

## 2. TMLR source: two audit targets, not one
| what | branch @ SHA | path | author block |
|---|---|---|---|
| TMLR submission (double-blind) | `paper-v1.1-wip` @ `acfd91d` | `docs/paper/arxiv/` (main.tex, sections/, refs.bib; figures in `docs/paper/figures/`) | `Anonymous authors` |
| **arXiv v1 upload (named)** | `paper-v1.1-cameraready` @ `fab376a` | `docs/paper/arxiv/` | named, with affiliation |

`docs/paper/arxiv/` is identical in both SHAs except `main.tex`, where the
only difference is the author block. Please audit both:
- the TMLR anonymity checks on `acfd91d`;
- the arXiv content checks on `fab376a`.

Build either one with `make -C docs/paper arxiv`. The birth-certificate gate
runs first, with `DATA_ROOT=/home/control/AionGenos`.

## 3. Last round's 17 FAILs
- Report: `docs/paper/prepub_audits/2026-10-06_cameraready_24e6097.md`. It is
  committed on both paper branches and present in both paper worktrees.
- Protocol: `docs/paper/PREPUB_AUDIT.md` (v1.1).

## 4. Step 5: `release-step5` @ `172f24a`
The branch is cut from master `e0cbcdd`; the worktree is
`/home/control/AionGenos-step5`. One commit; nothing is pushed.

| path | content |
|---|---|
| `docs/paper/REPRODUCE.md` | the reproduction guide, with `[URL]` placeholders for the adapters and the buffer pack |
| `docs/paper/birth_certificates/{derived_stats,r1_rounds_recompute}.{py,txt}` | the generators and their committed outputs; re-run against the live data root today, byte-identical |
| `docs/paper/birth_certificates/README.md` | what each generator certifies; which inputs are and are not public; why `check.py` is not included |

**Release buffer = your pack; I am not forking it.**
- REPRODUCE now points at `scripts/release/build_buffer_release.py` and
  `aiongenos_d10ext_frozen_buffer_v1.tar.gz`:
  - sha256 `7a405eb1…faaa0`, re-hashed today;
  - pack tree `e29224a1…a673`.
- The paper's own copy is **retired**: `docs/paper/release/build_buffer_release.py`,
  which builds `76e698a2…`. Do not upload
  `/home/control/AionGenos-release/d10ext_final_buffer_release.tar.gz`.
- REPRODUCE step 3 now:
  - extracts the pack at the clone root;
  - symlinks `images/` there, because the anchors are `images/<run>/<ep>/init_pre.png`;
  - passes `--recap_buffer_root aiongenos_d10ext_frozen_buffer_v1/buffer`.
- Checks done:
  - **load test:** `RecapBuffer(<pack>/buffer)` gives 547 records, and from a cwd
    with that symlink, `_load_past_image_b64_list` resolves 547/547 images;
  - **flags:** all three flags exist in `run_collect.py` at `e0ad00f`;
  - **no clash:** `e0ad00f` has no `images/` at its root;
  - **scan:** pack re-scanned today, 0 files containing `/home/`, host IPs,
    URLs or e-mail.
- After your report, wip's REPRODUCE.md will be made identical to the
  release-step5 copy (single source), and the retired script deleted.

**Prereg documents: nothing to add.** `docs/d11_preregistration.md`
(A14–A16 included; A16 `730b9fc` is on origin) and `docs/paper/l2_prereg.md`
with `l2_amendment_{1,2,3}.md` are already on master.

**Not included, by design.**
- `check.py` and `page_guard.py`: they read the LaTeX sources, which ship
  in the arXiv source archive, not in the repo.
- Raw replays, logs and `workspace/` audit outputs: not released (G3).

**To push:** the PI fills both `[URL]`s, then fast-forwards master to
`release-step5`. If master has moved by then, rebase first; the branch
touches only the paths above.
