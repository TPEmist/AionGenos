# Handoff: WP1-③a push — pipeline feasibility-clean, forward geometry locked, awaiting gen-0 decision

> **Executor**: isaac session (Claude, this session)
> **Time**: 2026-10-02 ~ 2026-10-05 14:44 (PDT) — multi-day session, this write-up 14:44 PDT
> **Operating Mode**: Project mode (AionGenos / isaac, master)
> **Branch**: master, uncommitted working-tree changes (see "Uncommitted" below)

## Where the project actually is (re-anchored this session — read first)

P2's confirmatory spine is **r-tracking** (prereg §2), NOT SR. The whole P2
pre-flight is blocked on **prereg §8b step 2**: a contact task + ONE gen-0
collect to estimate gen-0 r (the Δr prior). WP1-③a push exists ONLY to be that
contact task. It is a pre-flight unblocker, not r-tracking itself.

PI steer this session (critical, recorded in `rung1_smoke_criterion.md`
CORRECTION): the 10-ep smoke runs a FROZEN teacher with NO cross-episode
memory (`recap_buffer=None`). SR=0 there is EXPECTED and carries no rung-
language signal; the "10-ep SR=0 → rung-2" rule was MISAPPLIED. Correct pilot
criterion = MVC cold-start (§3a): can the frozen generator get ANY success →
can the task bootstrap gen-0.

### ✅ Completed Items
- [x] **cube-reset bug root-caused + fixed** (opus agent, file:line chain): IsaacLab
  `_reset_idx` never restores a RigidObject; only `EventTerm(reset_root_state_uniform)`
  does. push_s3a added `scene.object` with no reset event → cube drifted across
  episodes (void run bed0e663 polluted). Fix: `events.reset_object`, zero jitter,
  orthogonal to `reset_robot_joints`. Gate: shove → reset → drift 0.15cm ✓.
- [x] **Visible goal + triads removed** (PI a-1/a-2): goal = flat GREEN DISC
  (`_GREEN_GOAL_MARKER_CFG`, r=5cm h=4mm) rendering INTO the sensor RGB; left
  current-pose triad hidden; right-arm visualizers off. Prompt + instruction say
  "green zone" consistently. Verified: command markers DO render to the tiled
  camera (my earlier grep-guess that they don't was WRONG).
- [x] **Reachability math (PI question)**: validated L2 DiffIK sweep, table plane
  z_B=0.468 × both arms. LEFT owns +y + center; RIGHT owns −y + center; neither
  reaches x>0.46 at center. Old Pin-4a goal region (y∈±0.15, x→0.54) was ~half
  LEFT-unreachable. `logs/reach_table_both.log`.
- [x] **3 spawn bugs found by gates, fixed**: (1) cube spawn z penetrated table 4mm
  (half-h 0.024 > 0.02) → now rest+1mm; (2) cube collided with standby LEFT hand
  (measured hand at x≈0.21–0.27, y≈0.06–0.13; settle map: x≥0.38 STAYS for all y);
  (3) left-unreachable goal box.
- [x] **Clean 10-ep smoke run 3ca3b769**: SR 0/10, ALL plateau, start cube→goal
  9–17cm (env honest), cube moved 18cm/ep but min cube→goal never <9cm. PI eyes on
  GIF: geometry was a REACH-AROUND side-push (mean push angle 71°, 9/10 sideways)
  → cube squirts off the side. Pathological-hard, not conditional-rich hard.
- [x] **FORWARD-dominant geometry LOCKED + gated (ALL PASS)**: cube (0.38, 0.10);
  goal x(0.44,0.50) y(0.05,0.15) spanning around cube y → push angle 2–29° (mean
  17°), cube→goal 6.5–11.3cm, approach left-reachable + hand-clear, cube drift
  0.20cm / nondeterm 0.10cm. Layout `logs/fwd_layout.png`. Gates:
  `/home/control/.claude/jobs/fbbce146/tmp/{fwd_gate,final_gate,hand_map,
  reach_table_both,slide_diag}.py` (job tmp — copy to scripts/diagnostics if kept).
- [x] All of the above appended to `docs/p2_prereg/wp3a_push_provenance.md`
  (2026-10-02 / 10-05 entries) + `rung1_smoke_criterion.md` CORRECTION.

### ⏳ In Progress / Decision pending (PI)
- [ ] **gen-0 start decision** — pipeline is feasibility-clean; geometry locked. Next
  real step is prereg §8b step 2: wire recap/memory buffer into `push_collect`
  (`recap_buffer` currently None; `_emit_push_recap` is a stub returning text
  rounds — full `generate_recap` wiring NOT done) and run a gen-0 collect to
  estimate gen-0 r. BLOCKED on PI because of **§2c FREEZE clause**: once gen-0
  starts, body+geometry must not change until P2 collection completes. PI must
  confirm the forward geometry is final before gen-0 is pressed. Do NOT start
  gen-0 unilaterally.
- [ ] **Uncommitted working tree** (nothing committed since 9c0403d + paper's a88c4de):
  `push_s3a_cfg.py` (reset event, green disc, triads off, geometry), `prompts.py`
  (green-zone wording), `run_push_collect.py` (instruction string),
  `rung1_smoke_criterion.md`, `wp3a_push_provenance.md`, untracked `localProps/`
  (Table_sor_1.usd — needed by the env!) and `scripts/diagnostics/wp3a_reach_watch.py`.
  Commit as fix/feat/docs with NO Claude attribution (memory rule). `localProps/`
  must be committed or the env won't boot elsewhere.
- [ ] **Incoming handoff from paper session** `docs/handoff/2026-10-05_isaac-cost-remeasure.md`:
  standalone same-hardware cost-measure harness (teacher / student-bare /
  student+retrieval, ~20 steps each, record server `usage` tokens + wall-clock +
  retrieval overhead, store student full_response). Fold into the A15 night batch.
  Not started. Not urgent for 10/10 camera-ready; needed before TMLR.
- [ ] **A15 night batch** (`docs/p2_prereg/a15_eval_configs.md` prepared): 4 eval
  invocations still to fill once the A15 lock commit lands on master. Not started.

### ❌ Issues / Blockers
- **Reach-around + agent-picks-arm ("iii")** — PI's eventual target (cube random,
  agent emits ARM + can drive `left:cmd right:cmd`). Pipeline is LEFT-hardcoded in
  4 places (prompt, parser, `execute_push_segment`, neutral orientation). Deferred
  to a harder rung AFTER the memory→climb mechanism is shown on this bootstrappable
  task. Medium.
- **L3 `pick_place_cfg.py` latent twin bug**: `scene.object` with no reset event
  (same omission). Fix when L3 is next touched. Low.
- **Teacher server** gemma-4-31B on 148:18888 was UP at session end (I did not stop
  it). Check before assuming.
- **Transient Isaac boot crashes** (Vulkan DEVICE_LOST / std::system_error) still
  occur; retry. inotify limit was raised to 1024 by PI (transient; reboot reverts).

### 👉 Suggestions for Next Agent
1. **First**: ask PI to ratify the forward geometry as FINAL (FREEZE §2c), then commit
   the working tree (incl. `localProps/`). Until ratified, do not touch geometry.
2. Then wire the memory buffer into `push_collect` (`recap_buffer` + real
   `generate_recap`), mirroring collect.py's pattern; keep collect.py frozen
   (dual-instrument ledger). Re-run with PI-ratified criterion = MVC cold-start
   (>0 success), NOT rung-SR.
3. Run gates from `scripts/diagnostics/check_config_effect.py` after ANY cfg change
   (standby-pose bug recurred 4×; this session's cube bugs were all caught only by
   runtime gates, never by reading cfg).
4. Pick up the paper session's cost-remeasure handoff alongside the A15 batch.
5. Human-eye rule stands (3492b96): present GIFs, say what to look for, never judge
   them. PI's eyes caught 6+ things this session that numbers could not.

### Memory Sync Checklist
- [x] Provenance log updated (`wp3a_push_provenance.md`, two 10-05 entries)
- [x] Criterion doc corrected (`rung1_smoke_criterion.md`)
- [ ] No INDEX.md in this repo's convention; `docs/handoff/` is the journal.
- [x] Gotchas worth remembering: (a) command visualizer markers DO render into the
  sensor camera; (b) RigidObject needs an explicit reset EventTerm; (c) cube spawn
  must clear the standby hand (x≥0.38) and not penetrate the table; (d) SR under a
  frozen no-memory teacher is a floor, not a learning signal.
