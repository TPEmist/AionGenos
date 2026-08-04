# Handoff: scrub Claude + Antigravity attribution from master history

**From:** paper session
**To:** isaac session (owns master + its history rewrites)
**Date:** 2026-08-04
**Trigger:** user found "Claude" listed in the public GitHub repo's contributors.

## Diagnosis (verified, read-only)

- **Source = a `Co-Authored-By:` trailer in commit bodies**, not the
  author/committer field. Exact line, on **23 master commits**:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
  The `noreply@anthropic.com` address is what GitHub attributes to
  "Claude" in the contributor list.
- All 23 are on **master and already pushed to `origin/master`** — none
  on `paper-v1.1-wip` (the paper branch is clean; paper-session commits
  carry no such trailer).
- **Second attribution to scrub (user ruling 1+2):** the commit
  **author/committer identity is `Antigravity <antigravity@gemini.google>`**
  on the multi-round-phase commits — an agent identity, not TPEmist.
  User wants author shown as themselves.

## The 23 commits carrying the Claude trailer
```
1f57aa4 425d8bf 6eb9420 7a6f19d 5629bd1 6b1594d db8413f 125e270 fe17349
b6df6b8 01884b7 28f7c9c b1bb934 d3705e6 f270425 7c06923 5447112 bd5d735
65d70c1 cb8b454 d527952 154e974
```
(plus the older `Antigravity`-authored commits — check `git log --all
--format="%an" | sort -u`; scrub author→TPEmist on those too.)

## Ruling (user, 2026-08-04)
1. **Scrub the `Co-Authored-By: Claude` trailer** from all commit bodies.
2. **Rewrite the `Antigravity <antigravity@gemini.google>` author/committer**
   → TPEmist's git identity.
3. Then **force-push** the rewritten master to `origin/master`.
4. Global config already updated (paper session): `~/.claude/settings.json`
   now has `attribution: {commit:"", pr:""}` → future commits carry no
   trailer. **This does NOT touch existing history** — that is this job.

## ⚠️ CRITICAL side effect — provenance re-pin (do NOT skip)

Rewriting these commits **changes their SHAs**. The project pins commit
SHAs throughout provenance docs. Every reference below must be updated
with an old→new SHA map AFTER the rewrite (build the map from
`git filter-repo`'s commit-map output, or `git log` before/after):

**On master:**
- `docs/handoff/2026-07-29_isaac-L2-final-master-selfcontained.md` — refs
  6b1594d, db8413f, 125e270, fe17349, b6df6b8
- `docs/paper/l2_confirmatory_report.md` — refs 01884b7, 28f7c9c, b1bb934,
  d3705e6, f270425, 7c06923, 65d70c1
- `workspace/l2_audit/DIAGNOSTIC_4a_RESULT.md` — 7c06923
- `workspace/l2_audit/DIAGNOSTIC_4b_RESULT.md` — d3705e6
- `workspace/l2_audit/DIAGNOSTIC_4c_RESULT.md` — 28f7c9c
- `docs/handoff/2026-07-28_isaac-ack-gap-closed.md` — d527952, 154e974
- `docs/handoff/2026-07-28_paper-isaac-worktree-split.md` — 154e974
- `docs/paper/l2_amendment_3.md` — d527952, 154e974

**On paper-v1.1-wip (paper session will re-pin its OWN side after your
rewrite lands + you send the SHA map):** refs to fe17349, 5447112,
65d70c1, 154e974 in `docs/paper/l2_methods_draft.md`,
`docs/paper/arxiv/sections/methods_l2.tex`, `docs/paper/v1.1_notes.md`.
**→ send paper session the old→new SHA map when done; do not edit the
paper branch yourself (territory).**

## Coordination
- **paper-v1.1-wip is NOT yet pushed** (still local, awaiting the
  submission-ready state). So your master force-push does not collide with
  the paper branch on origin. Good — do the master rewrite first.
- Recommended tool: `git filter-repo --commit-callback` (strip the
  trailer line) + `--mailmap` (Antigravity→TPEmist). `filter-branch` works
  too but is slower/error-prone.
- **After rewrite:** verify `git log --all --format='%an <%ae>' | sort -u`
  shows only TPEmist, and `git log --all --format='%b' | grep -c
  anthropic` == 0. THEN force-push. Then send paper session the SHA map.
- Push cred note: this env has no push creds (HTTPS, no gh, no
  credential-helper). The force-push is run by the user via
  `! git push --force-with-lease origin master`.
