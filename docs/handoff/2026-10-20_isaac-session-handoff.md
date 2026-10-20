# Handoff → new isaac session (from isaac "AionGenos-isaac-session-1015", 2026-10-20)

You are taking over the **isaac** role: the engineering, experiment and
auditor session on `/home/control/AionGenos`, branch `master`.
- The **paper session** (herdr `w4:p8`) owns `docs/paper/` prose on the
  paper branches.
- The **PI** (the user) decides; reply in **Traditional Chinese (Taiwan)**.
- The handing-over session wrote this at about 74% context, at a clean
  breakpoint.

---

## READ FIRST — the PI's four points

### 1. Do not trust reports, handoffs or code comments. Read the code logic itself.
This rule is the PI's own, and the project's history justifies it.
- Every recurring bug class here was a gap between what a comment, report
  or description said and what the code did:
  - the standby pose was overridden by an inherited event (4×);
  - eval parsers drifted from the training target shape (4×);
  - "rung-2 = the P1 L0a condition" was asserted from a description, while
    the code had no inter-round feedback and no history;
  - a reach probe compared the TCP with its own commanded target
    (self-referential);
  - gates guarded only the literal they were written for.
- **Before you build on any claim, open the code path, follow it, and check
  runtime state** (`check_config_effect.py`, live reads). This applies to
  every source: my handoffs, paper-session handoffs, provenance logs, and
  docstrings, mine included.
- **Rule 10** (PI, 2026-10-15): when a condition is said to replicate
  another, compare it field by field against the original prompt template
  and code path, never by description.
- **PREPUB rule 4:** "I verified it" counts for nothing, whether it comes
  from a session, an agent or you. Only re-runnable scripts and openable
  files count. The single exception: the PI's own eye-confirmation of a
  first-hand source.

### 2. Mission: what AionGenos is for
Read `docs/aiongenos_founding_intent.md` (94 lines) in full, and
`docs/harness_grant_ledger.md`.
- AionGenos learns embodied (bimanual) manipulation with **zero
  demonstrations**: no teleop, no imitation targets. It is **not**
  zero-priors.
  - The birth configuration is "a brain that has read every book (a
    pretrained VLM) + a new body".
- **Conditional knowledge** (situation → action) **must be earned through
  experience**, never injected.
- **Marginal, situation-independent mechanical common sense** may be
  granted by the harness: standby pose, primitive form, work-surface
  existence, frame plumbing.
  - Every such grant is **logged with a reclamation condition** in the
    ledger. An unlogged or unreclaimable grant equals an injected answer.
  - The standby pose is "the machine's muscle tone".
- **Consequence for every design decision:** giving the policy information
  (for example oracle coordinates) is a founding-intent question, not an
  engineering convenience. rung-3 (coordinate disclosure) is a **last
  resort that needs PI consent plus a Ledger entry**.
- The **minimum-viable-competence law** (memory `minimum_viable_competence_law.md`):
  below a competence floor, a loop cannot start. Pilot SR is a floor, not a
  signal.

### 3. Blueprint and where we are now

```
P1  (paper 1) "Externalise the Memory" — D11 (L0a reach) + L2 (harder reach)
    ├─ result: distillation moves the MARGINAL, retrieval supplies the CONDITIONAL
    ├─ A15 controls (done): adapter non-essential; effect not adapter-specific
    ├─ A17 text-vs-image ablation: DRAFT, NOT LOCKED (night waiter idle)
    └─ PUBLISHING NOW: workshop camera-ready (due 10/23 AoE), arXiv v1, TMLR   ← paper track
P2  (paper 2) expert iteration: C_retrieval → self-collect → distil → iterate,
    hoping to CONSOLIDATE the conditional INTO the weights, gen by gen.
    Primary criterion = r-tracking (bare-weights residual correlation climbing out
    of the chance band). Task suite = contact-rich L4+ tasks on the OSC controller
    (WP1 unlocks), NOT the L2 reach family. (docs/p2_prereg/p2_preregistration_skeleton.md)
    └─ pre-flight on the first P2 task, WP1-③a PUSH (single-arm, gripper locked):
         (a) human-eye gate ✔   (b) Pin-4b cube region ✔
         (c) memory-ON pilot + observation-rung ladder  ← **WE ARE HERE**
         (d) [PWR-SIM] (σ(r), c/s definitions — PI must pin c/s)
         (e) freeze (ledger frozen through P2 collection) → gen-0
```

- Curriculum overview: `docs/plans/INDEX.md`, L0–L4.
- Pipeline order: `docs/p2_prereg/wp3a_pilot_plan.md`.
- Full dated history: `docs/p2_prereg/wp3a_push_provenance.md`. It is
  long; the newest entries are at the end.

### 4. Current progress: the rung-2′ pilot (WP1-③a step c)
- **Rung ladder:** 1 (front RGB + proprioception) → 1b (+ top camera) → 2
  (+ scalar distances TCP→cube and cube→goal) → 3 (+ coordinates).
- **The rung-1, 1b and 2 results are all 0/50.** All three were obtained
  without inter-round feedback (push rounds were stateless).
  - The PI ruled that this was an interface bug.
  - Their reading on whether a viewpoint helps is **void**.
- **rung-2′** = rung-2 + the **full P1 condition**:
  - an `EpisodeConversation` per episode: first turn + last 6 pairs;
  - the previous-round critic feedback: P1 header, target line, movement
    line, the two distances start → end;
  - the P1 progress / regress / flat verdict on cube → goal.
- Flags: `--round_feedback --round_history`. Code:
  `aiongenos/orchestrator/push_feedback.py` and `push_collect.py`.
  Tests: `tests/test_push_memory.py`.
- **rung-2′ result:** run `71134939`, seeds 5000–5049, memory ON,
  provenance commit `c0e7640`.
  - **0/50 → STOP (rule B4: no automatic rung-3).**
  - Real gains:
    - grid-zero targets are gone (X 6%, Z 0%);
    - targets are closest to the cube of any rung (|Δ| 13/11 grid);
    - within-episode closing improved (xy 6.5→11.0 cm vs rung-2 10.6→23.8);
    - seed-paired, rung-2′ is closer in 31/50 episodes;
    - 3 fingertip pushes (tiny).
  - Round-1 ρ(target, cube) is about +0.09 (it was −0.13), still about 0.
  - **New failure mode:** 85% of targets sit at z = 0.535, the standby TCP
    height and 4.3 cm above the cube top. The teacher anchors its height
    and hovers above the cube.
  - The verdict line always reads "No significant progress", because
    cube → goal cannot change before contact. It never reports approach
    progress.
  - True recap confabulation is 0/48 (the 6 heuristic flags are false
    positives).
- **Waiting for the PI's ruling.** Options presented:
  - (a) rung-3, which needs consent plus the Ledger. The blocker is height,
    and rung-3 as designed reveals x/y only.
  - **(b) [isaac's recommendation]** before contact, base the verdict on
    fingertip → cube. This is an interface mapping of the P1 template and
    changes the just-ruled "full P1 condition", so the PI must decide.
  - (c) leave contact height as a lesson for memory to earn. This needs
    successes first.
- If rung-2′ ever succeeds: rung-1′ (image + feedback, no distances, no
  verdict) must be re-run, because the ladder is comparable only under one
  interface.
- Geometry facts verified with the cube in place
  (`scripts/diagnostics/wp3a_reach_real.py`, 5/5 seeds):
  - a scripted push reaches the goal;
  - the push end is at 80–89% of the straight-arm radius;
  - the TCP is on the fingertip;
  - the rest orientation tips the fingers up, so the wrist is about 5.5 cm
    below the fingertip. That sets a table-collision floor at TCP
    z ≈ 0.471, which is not a reach limit.

---

## Open items (owner → what to do)

1. **Gate: replay recount** (PI, 2026-10-20)
   - The paper session implements it per
     `docs/handoff/2026-10-20_paper-replay-recount-into-gate.md` (`11d94bf`).
   - When it hands you SHAs, run the **4 negative tests** listed there:
     - edit a recount value;
     - edit a derived_stats as-run count;
     - flip one replay outcome in a **copy** of the data root;
     - delete one replay file in the copy.
   - All four must be CAUGHT.
   - Recount artifact: `docs/paper/birth_certificates/replay_recount.txt`
     (`889ea34`), 0 mismatches.
2. **E6** (after the PI uploads arXiv)
   - The paper session fills `arXiv:[ID]` at `bar/main.tex:338`.
   - You run gate + page guard on the new cameraready SHA (5/5 pages).
   - Then the PI submits the camera-ready to OpenReview (10/23 AoE).
3. **GitHub Release `paper-v1-artifacts`** (the PI publishes on arXiv day)
   - Then download the 3 assets from the public URLs and compare sha256:
     - adapters `4807767d…`, `7f7f7363…`;
     - buffer `7a405eb1…`.
   - Run the REPRODUCE download step.
4. **rung-2′ next step:** wait for the PI's ruling. If (b): implement, test
   the P1-off path byte-identical, re-run the same seeds, and report the
   four items plus the target distribution.
5. **A17**
   - Draft: `docs/d11_a17_draft.md`.
   - Waiter: PID in `logs/a17_waiter.pid`. It starts only on a commit whose
     subject begins `docs(d11): A17 LOCK`.
   - The night GPU is reserved for it.
6. **Pending PI:**
   - P2 prereg §2d recap-honesty guard. The detector needs an
     imperative/LESSON exclusion (it produces false positives at rungs 2
     and 2′).
   - [PWR-SIM] c/s definitions.
7. **Audit state:** PREPUB #2 is green on cameraready `b58e256` / TMLR
   `6544361`.
   - H4 PASS (PI).
   - Reports are in `docs/paper/prepub_audits/`.
   - Tools in `scripts/audit/`: `negtest.sh`, `coverage_sweep.py`,
     `sr_sens_scan.py`, `tmlr_anon_check.sh`, `replay_recount.py`.
   - PI guide (local): `workspace/release/PI_GUIDE_H4_and_arXiv_day.md`.

## Hazards (read before acting)
- **Never push local `master` directly.**
  - `origin/master` = `2577d70`. Local master is merged with it (`f46b7d7`)
    but carries unpushed commits that must not go public as they are: the
    audit #2 report quotes a company-permission source comment, and
    handoffs mention the GPU host.
  - For any publish: build a clean branch from `origin/master`, cherry-pick
    only the public files, audit (company docs / local paths / .env /
    `company_*` history), then the PI pushes. That was the step-5
    procedure, `docs/paper/prepub_audits/2026-10-15_step5_review_*.md`.
- **The paper branches (`paper-v1.1-wip` / `-cameraready`) must never be
  pushed as-is**: their history has 9 commits touching the company
  disclosure packet.
- **No Claude/AI attribution** in commits or PRs (memory `no-claude-attribution.md`).
- **Kill only verified PIDs.** Check `/proc/<pid>/cmdline` first. Never
  `pkill -f` or a ps-derived PPID. Verify starts by GPU use and log growth.
  - A SIGTERM'd pytest once survived and held the GPU, so verify that a
    killed process is actually gone.
- **Negative tests:** use sed or exact-string mutation, restore, then check
  md5. Never `git checkout` to undo.
- **herdr:**
  - **Environment variables can be stale.** This session's
    `HERDR_PANE_ID` pointed at another session's pane. Identify panes by
    reading their screens.
  - Never control a pane you have not identified.
  - agy agents (w4:t1, w4:t2) are useful for mechanical evidence gathering,
    but **verify their output yourself**: they cited wrong source lines and
    were OK on values.
- **Rule 5:** the auditor is not the fixer. For paper prose and
  `check.py`, write a spec and the paper session implements it; you audit
  with negative tests.
- **GPU host:** `exx@10.80.9.148`, teacher :18888 and student :18889.
  - Check `curl …/lora-adapters` before trusting which adapter is loaded.
  - Restart only via `server/llama_server_teacher.sh` and
    `server_side/reload_student_*.sh`.
- **GIFs for the PI** are always front | top with FED / PI-ONLY labels
  (`push_gif.compose_frame`), and say *what to look at* (the human-eye-gate
  rule).

## Mistakes this session made (check these areas extra carefully)
1. The first reach probe was self-referential: it parked the cube and
   compared the TCP with its own target. The PI rejected it.
2. Changing the GIF format broke `test_gif_tag_in_bottom_strip` without a
   full test run.
3. A15 B_main z 3.90 was a double rounding; the correct value is 3.91.
4. Audit FAIL-10 over-reported because `d11_wrapup.txt` was not searched.
5. A full test run was reported while a SIGTERM'd pytest was still alive.
6. "Previous round only = P1" was taken on description; Rule 10 caught it.
7. A plain-text conversion stripped an escaped `\%`.

Lesson: **before trusting an instrument, test it on a case where you know
the answer** (positive and negative controls), and run the full relevant
test files after any shared-code change.
