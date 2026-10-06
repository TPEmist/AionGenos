# A15 / P1 disclosure pack — numbers + labels for the paper session

**Produced by:** isaac session (master), 2026-10-05. CPU-only re-analysis of
on-disk replays/logs/recaps. No sim, no servers, no edits under `aiongenos/`.
**Base commit:** `ea58292` (A15.1). Pre-registration references:
`docs/d11_preregistration.md` — Amendment 14 (§14.1–14.6, anchor `73e712b`),
Amendment 15 (lock `989a753`) + operational pins 1–8 + A15.1.

**Discipline.** This pack gives numbers, their source, and a status label. It
does not write paper prose. Labels:

- **confirmatory**: a test/reading pre-registered before the number existed,
  computed exactly as registered.
- **pre-registered sensitivity**: a pre-registered companion number reported
  *beside* the primary. It never replaces the primary or changes a verdict
  (A15 pin 8; A14 §14.5b for McNemar).
- **exploratory**: a labelled analysis that was not a registered primary.
- **post-hoc exploratory**: computed after the result it depends on was seen,
  or under a rule set after seeing it. Never citable as confirmatory.
- **descriptive / disclosure**: a fact about the instrument. No test.

---

## 1. Inherited 24 s auto-reset: D11 sensitivity table (A15 pin 8)

### 1.1 Boundary rule (derived, not assumed)

1. **Env time-out.** `IsaacLab/source/isaaclab_tasks/.../reach/config/openarm/bimanual/reach_openarm_bi_env_cfg.py:330-335`
   sets `decimation=2`, `episode_length_s=24.0`, `sim.dt=1/60`, so
   `max_episode_length = ceil(24 / (1/60·2)) = 720` env steps
   (`isaaclab/envs/manager_based_rl_env.py:101-103`). Termination
   `time_out = episode_length_buf >= max_episode_length`
   (`isaaclab/envs/mdp/terminations.py:31-33`, wired at `reach_openarm_bi_env_cfg.py:283`).
   Inside `env.step` the code increments `episode_length_buf` and
   `common_step_counter` (`manager_based_rl_env.py:200-201`), then calls
   `_reset_idx` for timed-out envs in the same step (`:214-219`). The orchestrator
   discards `truncated` (`aiongenos/orchestrator/isaaclab_env_interface.py:368`).
2. **Step counter in the replays.** Replay `t = common_step_counter · sim.dt`
   (`isaaclab_env_interface.py:370`), so the counter is `c_i = round(60·t_i)`.
   The counter is never reset; it starts at 0 (`manager_based_rl_env.py:74`).
3. **Per-episode reset counter.** `c_reset` is the previous episode's last
   recorded counter in log order (0 for the first episode; +1 for each
   intervening parse-fail episode, which has no recorded steps but still runs
   one warm-up step). Recorded index *i* has `episode_length_buf = c_i − c_reset`.
   The first auto-reset is at the index where that equals 720.
   **Measured:** `c_0 − c_reset = 2` for every episode of all 14 runs. One
   unrecorded step is the warm-up `env.step(hold_action)` in `reset()`
   (`isaaclab_env_interface.py:136`). So the boundary is index **718** in every
   episode: index 718 is the first post-reset state, and the second boundary
   (1438) is past the 40 × 30 = 1200-step cap. Intra-episode counter steps are
   always 1. Steps per round are 30 in every run.
4. **Discontinuity cross-check.** The frozen right arm's integer EE position
   is static except at a reset re-sample. A boundary is **confirmed** when, at
   index 718, the right-EE jump is (a) ≥ 5 grid, (b) > 2 × the episode's largest
   right-EE step change elsewhere, and (c) the argmax of the right-EE step
   change. The left-EE jump and the |Δdist_red| jump are reported too.
   Across all 14 runs (D6 checked over its 100 logged episodes), the largest
   right-EE step change at any index other than 718 is 3.74 grid
   (`56ee684b/failure/3c49c89d-ac6.json`, idx 719). No reset-like
   discontinuity appears anywhere else.
5. **Ambiguous episodes.** 3 of 209 crossing episodes fail the strict rule.
   Their right-EE jump is 4.24, 2.24 and 4.58 grid, against a background of 1.41
   each (ratio 3.0 / 1.6 / 3.2). So all 3 fail check (a), and 6b9ef134 k=0 also
   fails (b). In all 3 the jump at 718 is still the argmax, and the left-EE jump
   is 23.3, 65.2 and 52.8 grid (background ≤ 6.8). The 3 are A_ctrl_rat k=70 (failure), D10 6b9ef134 k=0
   (failure) and D10 54bcc2d4 k=33 (success after the boundary). **0 are
   unresolved.** Only the 54bcc2d4 one affects a count, and both the counter
   derivation and the left-EE jump put it after the boundary.
6. **Sensitivity success** = outcome success AND success index < 718. Success
   is evaluated on a round's final step, and the episode ends there
   (`aiongenos/orchestrator/collect.py:406-419`), so success index = last index.
   Round 24 (indices 690–719) straddles the boundary. Its success check reads
   index 719, which is post-reset.

Cross-check against pin 8 (filed earlier): crossing/success-after counts
28/4, 33/3, 28/7, 30/2, 8/1 and |Δdist_red| > 4 cm counts 23/21/21/21/7 are
**reproduced exactly**.

### 1.2 Per-run table

Command: `python3 scripts/analysis/a15_p1_autoreset_sensitivity.py`. It writes
`workspace/a15_p1/autoreset_sensitivity.json` with per-episode rows (sha256
`1e01c0d3…e90e`; script sha256 `8da41c21…8dbd`). D11 episodes are loaded with
the A14 code (`d11_mcnemar.parse_log_order` / `load_replay` /
`outcome_success`). The other runs are loaded in log order from
`success/ failure/ parse_fail_quarantine/`.

| run | role | as-run SR | crossing 718 | successes after boundary | **sensitivity SR** | ambiguous | Δdist_red>4cm @718 |
|---|---|---|---|---|---|---|---|
| A_action_only `e4d81bb6` | D11 arm | 25/100 | 28 | 4 | **21/100** | 0 | 23 |
| A_ctrl_rat `56ee684b` | D11 arm | 15/100 | 33 | 3 | **12/100** | 1 | 21 |
| B_main `a7b11544` | D11 arm | 26/100 | 28 | 7 | **19/100** | 0 | 21 |
| D_gist `875c04fb` | D11 arm | 19/100 | 30 | 2 | **17/100** | 0 | 21 |
| C_retrieval `09817322` | D11 arm | 49/100 | 8 | 1 | **48/100** | 0 | 7 |
| `6b9ef134` | D10 teacher | 25/100 | 10 | 0 | 25/100 | 1 | 9 |
| `70028c23` | D10 teacher (74 parse-fail) | 9/100 | 3 | 1 | 8/100 | 0 | 3 |
| `18581c81` | D10 teacher | 33/100 | 4 | 0 | 33/100 | 0 | 4 |
| `b74d9f38` | D10 teacher (79 parse-fail) | 10/100 | 0 | 0 | 10/100 | 0 | 0 |
| `0eb35c80` | D10 teacher | 51/100 | 4 | 1 | 50/100 | 0 | 3 |
| `54bcc2d4` | D10 teacher | 48/100 | 9 | 3 | 45/100 | 1 | 9 |
| `aa08bb4c` | D10 teacher | 57/100 | 4 | 1 | 56/100 | 0 | 4 |
| D10 7-run total | — | 233/700 | 34 | 6 | 227/700 | 2 | — |
| `fa7f4571` | D6b memoryless teacher | 22/100 | 28 | 3 | **19/100** | 0 | 22 |
| `67685984` | D6 memoryless teacher | 21/100 | 20 | 4 | 17/100 | 0 | 14 |

The episodes that succeeded after the boundary (k, episode_id) are listed in
the JSON (`rows[].success_after_b`). For D11: A_action_only k=36,46,53,56;
A_ctrl_rat 51,56,60; B_main 35,36,47,54,61,66,99; D_gist 59,84;
C_retrieval 15.

Labels: as-run SR = **primary** (unchanged). Sensitivity SR = **pre-registered
sensitivity** (A15 pin 8). For the D10/D6 rows it is **descriptive**: those runs
are unseeded and in no test. The paper's teacher-pool constants (51.7% pinned
T3 floor; 49.3%, n=221 parity reference) are **not** re-derived here. 51.7% is
a pre-registered constant. This pack does not reconstruct the 49.3% pool's
membership.

### 1.3 D11 headline contrasts: as-run vs sensitivity (same A14 code)

Statistics come from `scripts/analysis/d11_mcnemar.py` (unchanged since
`73e712b`; `git diff 73e712b HEAD -- scripts/analysis/d11_mcnemar.py` is
empty): `two_prop_z`, `mcnemar` (exact binomial when b+c < 25),
`one_prop_z_floor`, `MEMORY_TEACHER_SR = 0.517`. Newcombe CIs come from
`scripts/analysis/l2_confirmatory.newcombe_diff_ci`.

**Test choice is mechanical (A14 §14.2).** Re-running
`python3 scripts/analysis/d11_mcnemar.py` prints `✗ GATE FAILED — 377 mismatches`
and `§14.2 primary test = Z (mechanical fallback — pairing gate failed)`. So the
**two-proportion z is primary** and **McNemar is sensitivity only** (A14
§14.5b: the verdict follows z, never switched by McNemar). This inverts the
"McNemar primary if gate passes" branch, because the gate did not pass.

| contrast | α | version | counts | Δ pp | Newcombe 95% | z | p_z (PRIMARY) | discordant a/b | p_McNemar (sens.) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **T1** B_main − A_action_only | 0.020 | as-run | 26 vs 25 | +1.0 | [−11.0, +13.0] | 0.162 | 0.871 | 12/11 | 1.0 | T1-strong FAIL, T1-weak FAIL → **null** |
| | | sensitivity | 19 vs 21 | −2.0 | [−13.1, +9.1] | −0.354 | 0.724 | 7/9 | 0.804 | FAIL / FAIL → null |
| **T1a** B_main − A_ctrl_rat | 0.020 | as-run | 26 vs 15 | +11.0 | [−0.2, +22.0] | 1.927 | 0.0540 | 18/7 | 0.0455 | **n.s.** |
| | | sensitivity | 19 vs 12 | +7.0 | [−3.2, +17.1] | 1.368 | 0.171 | 12/5 | 0.144 | n.s. |
| **T4** C_retrieval − B_main | 0.010 | as-run | 49 vs 26 | +23.0 | [+9.6, +35.3] | 3.359 | 7.81e-4 | 34/11 | 1.04e-3 | **SIGNIFICANT** |
| | | sensitivity | 48 vs 19 | +29.0 | [+16.0, +40.7] | 4.345 | 1.40e-5 | 38/9 | 4.42e-5 | significant |
| **+34 pp identical weights** C_retrieval − A_ctrl_rat (exploratory, not registered) | (0.05 shown) | as-run | 49 vs 15 | +34.0 | [+21.3, +45.2] | 5.154 | 2.55e-7 | 44/10 | 7.10e-6 | significant |
| | | sensitivity | 48 vs 12 | +36.0 | [+23.7, +46.9] | 5.555 | 2.78e-8 | 43/7 | 7.43e-7 | significant |
| **T3** B_main vs 0.7×51.7% = 36.2% (one-sided) | 0.010 | as-run | 26% | — | — | −2.120 | 0.983 | — | — | **BELOW floor** |
| | | sensitivity | 19% | — | — | −3.577 | 0.9998 | — | — | below floor |

The as-run rows reproduce the commit-`73e712b` outputs and paper Table 1
exactly (z 0.162 / 1.927 / 3.359 / 5.15; McNemar 1.0 / 0.046 / 1.0e-3).

**Verdict change: NONE.** T1 stays a null (Δ changes sign, +1 → −2 pp, both
far from significance). T1a stays n.s. (Δ shrinks to +7 pp). T4 stays
significant (Δ grows to +29 pp). The +34 pp identical-weights effect stays
significant (+36 pp) and stays exploratory. T3 stays below the floor. McNemar
agrees with z on every contrast in both versions.

Not affected: the R1 ΔX probe (§4.3) and the A15 (c) R1' slope use round 1 only
(indices 0–29), which is far before index 718.

Side note (descriptive): results draft line 29 prints the T1 CI as
[−11.1, +13.1], but Table 1 (line 323) and `newcombe_diff_ci` give
[−11.0, +13.0] (−11.01, +12.97).

---

## 2. `{target_color}` placeholder in the recap prompt (disclosure)

**On disk (HEAD `ea58292`; all four files are unmodified in the working tree):**

- `aiongenos/vlm/task_instructions.py:19`: the L0a-Left template is
  `"Move your LEFT end-effector to the {target_color} target. "…`
- `aiongenos/orchestrator/collect.py:258`: per-round prompts **are**
  formatted (`task_instruction_template.format(**state)`). Every replay
  `instruction` field of the 7 D10 runs + C_retrieval reads
  `"Move your LEFT end-effector to the red target…"` (800/800 checked).
- `aiongenos/orchestrator/collect.py:622`: the recap call passes the
  **unformatted** template (`instruction=level_config.task_instruction_template`).
- `aiongenos/pipeline/stage4_recap.py:312`: `parts.append(f"TASK: {instruction}")`
  in `_build_recap_user_prompt`. The recap VLM saw the literal `{target_color}`.
- `aiongenos/pipeline/stage4_recap.py:159`: the same string is stored as
  `metadata.instruction` in every recap record.
- `git blame` puts both collect.py:622 and stage4_recap.py:312 in commit
  `2ce1700c` (2026-06-25 12:20). That is before the first D10 teacher run
  `6b9ef134`, whose log starts 2026-06-25 13:23.
- The retrieval preamble shown at inference (`aiongenos/memory/retriever.py:172-206`)
  injects `text_lesson` plus state anchors, **not** `metadata.instruction`. The
  placeholder never reaches a student or teacher action prompt directly.

**Counts over the frozen buffer** `workspace/recaps_d10_frozen_c_retrieval/`
(547 JSON records; per run 0eb35c80 100, 18581c81 100, 54bcc2d4 100,
6b9ef134 100, aa08bb4c 100, 70028c23 26, b74d9f38 21):

| field | contains literal `{target_color}` |
|---|---|
| `metadata.instruction` (= the TASK line the recap VLM saw) | **547/547** |
| `text_lesson` (the text injected at retrieval) | **0/547** (and 0/547 contain any `{`) |
| `text_lesson` mentions "red" (`\bred\b`, case-insens.) | 517/547 |

The full recap prompt text is not persisted (`data/collect_dumps/<run>/<ep>/meta.json`
has no recap prompt; `grep -rl target_color data/collect_dumps/0eb35c80` returns
nothing). The TASK line is reconstructed from the code path above plus the stored
`metadata.instruction`. Example record:
`workspace/recaps_d10_frozen_c_retrieval/70028c23/7cce77bb-361.json` →
`metadata.instruction = "Move your LEFT end-effector to the {target_color} target. Your right arm is held still — you do not control it."`.
Its lesson begins "The red cube appeared closer to the center line…".

**Exposure (descriptive):**

- *Direct* (recap author saw the literal): every recap generated in the 7 D10
  memory-teacher runs, i.e. all 547 frozen records.
- *Indirect* (consumes lessons written under that prompt; the lessons
  themselves contain no literal): the D10 memory teacher's own in-run retrieval;
  C_retrieval (D11); A15 (a) and (b) arms (same frozen buffer, pins 1–2); any
  arm whose training target carries retrieved-lesson gist (B_main, D_gist, per
  Amendment 8 arm design).
- *Not exposed*: D6/D6b (memoryless, no retrieval), A_action_only and
  A_ctrl_rat at inference (no retrieval preamble).
- No fix: the instrument stays frozen for pairing. Label: **disclosure**.

---

## 3. D6 memoryless-teacher measured SR (A15 protocol (d), pin 6)

| run | log | log `Stats summary` | replays | sensitivity SR (§1) | conditions |
|---|---|---|---|---|---|
| **D6b `fa7f4571`** | `logs/d6b_l0a_left_no_memory_fix_20260702_125800.log:24697` | `success_episodes=22, vlm_parse_fails=0` of 100 | success 22 (all `run_id=fa7f4571`, outcome success); failure 78 (70 timeout + 8 vlm_stop_premature) = 100 | 19/100 | `--freeze_level`, no `--use_memory` (launcher `scripts/training/launch_d6b_after_ext5b.sh:50-56`, LOG pattern `:39`); unseeded (0 `env.reset(seed=` lines in log) |
| D6 `67685984` | `logs/d6_l0a_left_20260617_111817.log:23460` | `success_episodes=21` of 100 | 101 files: 22 success + 79 failure (75 timeout + 4 vlm_stop_premature) | 17/100 | no freeze_level (pin 6); unseeded |

**The 101st D6 file is explained.** `data/replays/67685984/success/0fb0b1ac-148.json`
has embedded `run_id = "e227aeaa"`. It is the D4 episode logged at
`logs/d4_l0a_left_20260615_142508.log:516` ("Episode 3/5 | L-2 | 0fb0b1ac-148")
and written to `data/replays/e227aeaa/success/` (`:533`; the original still
exists there). It is not in the D6 log's 100 episode IDs. Its mtime in the D6
dir (2026-06-22 11:41) matches the `a_train` sync of run 67685984
(`logs/a_train_20260622_114144.log:1`, 11:41:44), while the other 21 D6
successes date 06-17/06-18. The 21/100 count is correct. How the file got copied
is not established beyond that timing.

(Also on disk, not the pinned value: `logs/d6b_l0a_left_no_memory_fix_20260701_181246.log`,
run `d5416947`, 9/100 with 40 parse fails. This is the earlier D6b attempt
before the fix re-run.)

**Comparison:** paper `docs/paper/d11_results_draft.md:121` (table cell
"memoryless teacher ≈ 30%†") and `:134` († "derived, not directly seed-matched:
D6b memory main-effect (+19.2 pp) subtracted from the memory-teacher pool").
Measured D6b = **22/100 (22%), measured, not seed-paired**, which is 8 pp below
the derived ≈30%. Pre-registered sensitivity per pin 8: 19/100.
Label: **descriptive (A15 (d) measured value)**. There is no test. D6b is
unseeded, so it cannot pair with the seed-4500 D11 arms.

---

## 4. A15 (c) R1' slope status

- The **pinned (c) reading for the five D11 arms is UNAVAILABLE as
  pre-registered** (A15.1). Under the 1 mm recovery gate (pin 5)
  `logs/a15_slope_probe_gate1mm.json` keeps n = 14 / 20 / 11 / 12 / 1
  (A_action_only / A_ctrl_rat / B_main / D_gist / C_retrieval) and excludes
  86 / 80 / 89 / 88 / 99. C_retrieval's n=1 gives `r = 0.0, band [0.0, 0.0]`.
- The 15 mm-gate D11 numbers are **post-hoc exploratory** (A15.1: the gate was
  set after the 1 mm result was seen, and the 15 mm result was seen before
  A15.1 was filed). Quoted from `logs/a15_slope_probe_gate15mm.json`
  (n=100 each, 0 excluded by gate, 0 excluded no-R1):

| arm | Spearman r | permutation band | above_band | gate residual median / max (m) |
|---|---|---|---|---|
| A_action_only | −0.29757804398478066 | [−0.17737651824931594, 0.20088185973642858] | false | 0.004008352756500244 / 0.009656459093093872 |
| A_ctrl_rat | −0.2447017352344807 | [−0.1916038636196572, 0.19665722500699334] | false | 0.004194244742393494 / 0.010624736547470093 |
| B_main | −0.15631653936852655 | [−0.18606362402317853, 0.19736462929331422] | false | 0.004296496510505676 / 0.009528666734695435 |
| D_gist | −0.20728191386313025 | [−0.18407974748003597, 0.1990463634299142] | false | 0.003965839743614197 / 0.010371342301368713 |
| C_retrieval | 0.3058177336123941 | [−0.19152094267933964, 0.19418829834275328] | **true** | 0.006886139512062073 / 0.012099996209144592 |

  Arithmetic fact, not a reading: A_action_only, A_ctrl_rat and D_gist have r
  below their band's lower edge. B_main is inside its band.
- **Teacher slope: not computable.** The JSON field `D10_teacher_pool` reads
  "not computable: D10 collects were unseeded, target not on disk (A15 op pin 5)".
  The "teacher > 0, wide σ" prediction is **untested**.
- **Pre-registered status remains only** for the R1 slopes of the A15 (a)/(b)
  arms under the 15 mm gate (A15.1). Those arms have not run.

---

## 5. Routing table

| item | paper location affected | label | pre-committed route |
|---|---|---|---|
| 1 auto-reset | `d11_results_draft.md` §4.1 T1 numbers (:26-29), §4.2 +34 pp (:65), T4 (:73-75), T1a branch remark (:100-102), T3 (:105-109), rung table (:121-122), Table 1 (:319-327); `d11_methods_draft.md` §3.1 (:17-18, "runs up to a fixed round budget": the 24 s time-out / 718-step boundary is not stated) | as-run = primary; sensitivity = pre-registered sensitivity | **A15 pin 8**: sensitivity SR is "reported beside every A15 and D11 SR, never replacing it". No A15 routing branch applies. Verdicts unchanged (§1.3). |
| 2 `{target_color}` | `d11_methods_draft.md` §3.2 (:25-31, recap/memory pipeline description) | disclosure | No A15 route (not a registered item). Instrument frozen, no fix. |
| 3 D6 measured SR | `d11_results_draft.md` :121 ("≈ 30%†") and footnote † :134-135 | descriptive, "measured, not seed-paired" | **A15 (d) + pin 6**: "Report the D6 memoryless-teacher's actual SR if a log exists". A log exists, so D6b `fa7f4571` 22/100 is the reported value and "derived, not measured" no longer applies. Pin-8 sensitivity beside it: 19/100. |
| 4 A15 (c) | `d11_results_draft.md` §4.3 σ argument (:161-199, incl. Figure 2 caption :194-199) | D11-arm slopes: post-hoc exploratory; teacher: not computable / untested | A15 (c) routes ("slope > band → mechanism strengthened, Fig. 2 gains teacher σ + R1' figure" / "in band → mechanism downgraded, σ argument withdrawn") **cannot be selected with confirmatory status for the D11 arms**: the pinned reading is UNAVAILABLE (A15.1). The teacher-σ part of the "strengthened" route is not available (teacher slope not computable). The only pre-registered (c) reading left is the A15 (a)/(b) arm slopes under the 15 mm gate. They are pending. |

---

## Commands run (all from `/home/control/AionGenos`)

```bash
python3 scripts/analysis/a15_p1_autoreset_sensitivity.py     # §1 tables + JSON
python3 scripts/analysis/d11_mcnemar.py                      # gate FAILED (377), primary=Z; as-run reproduction
git diff 73e712b HEAD --stat -- scripts/analysis/d11_mcnemar.py   # empty
# ambiguous-boundary listing / after-boundary success ids: read rows[] of
#   workspace/a15_p1/autoreset_sensitivity.json (cross && !confirmed; success_after_b)
# background right-EE scan (max step jump at idx != 718 over 13 runs = 3.74; D6 67685984
#   re-checked over its 100 log-order episodes, also 3.74):
python3 - <<'EOF'
import json,math,glob
mx=0
for run in 'e4d81bb6 56ee684b a7b11544 875c04fb 09817322 6b9ef134 70028c23 18581c81 b74d9f38 0eb35c80 54bcc2d4 aa08bb4c fa7f4571'.split():
    for p in glob.glob(f'data/replays/{run}/*/*.json'):
        tr=json.load(open(p))['trajectory']
        mx=max([mx]+[math.dist(tr[i]['right_ee_pos'],tr[i-1]['right_ee_pos']) for i in range(1,len(tr)) if i!=718])
print(mx)
EOF
# §2 counts: iterate workspace/recaps_d10_frozen_c_retrieval/*/*.json, test
#   '{target_color}' in metadata['instruction'] / text_lesson, re r'\bred\b' in text_lesson
git blame -L 622,622 aiongenos/orchestrator/collect.py
git blame -L 312,312 aiongenos/pipeline/stage4_recap.py
grep -rl target_color data/collect_dumps/0eb35c80          # no output
# §3: grep "Stats summary" logs/d6b_l0a_left_no_memory_fix_20260702_125800.log logs/d6_l0a_left_20260617_111817.log
#     grep -c "env.reset(seed=" <same logs>                 # 0, 0
#     per-file (subdir, run_id, outcome) counts over data/replays/{fa7f4571,67685984}/*/*.json
#     grep -n 0fb0b1ac logs/*.log ; ls -la data/replays/{67685984,e227aeaa}/success/0fb0b1ac-148*
# §4: cat logs/a15_slope_probe_gate15mm.json logs/a15_slope_probe_gate1mm.json
```
