# Dual-Collect Equivalence Ledger

> **Purpose (PI ruling 2026-08-25):** AionGenos runs TWO first-class collect
> instruments. `collect.py` serves the P1 task family (reach / L2), frozen with
> the submission. `push_collect.py` serves the P2 task family (WP1-③a push),
> from smoke to gen-N — it is NEVER "integrated back" into collect.py. This
> document is the AUDIT that the two instruments provide EQUIVALENT guarantees.
> P2 paper methods cites it directly. Drift between the two = a defect this
> ledger exists to catch (same discipline as the train/eval format-contract
> gate).

## Architecture

| Instrument | Task family | Status |
|---|---|---|
| `aiongenos/orchestrator/collect.py` (`run_collect_loop`) | P1: reach / L2 | frozen with submission |
| `aiongenos/orchestrator/push_collect.py` (`run_push_collect_loop`) | P2: WP1-③a push | active (smoke → gen-N) |

**Shared substrate (SAME functions, imported — not copy-pasted):**
`replay/schema.py`, `replay/buffer.py`, `pipeline/stage4_recap.py`,
`memory/*`, `vlm/client.py`. Extract-to-shared candidates (currently
collect.py-private, pure, no loop state): `_make_vlm_interaction`,
`_write_episode`, `_active_arm_for_level` → lift to a shared module so both
instruments share ONE copy (prevents drift). Extraction is the ONLY legal edit
to collect.py: pure move, zero semantic diff, one L2 short-verify.

## Guarantee-by-guarantee equivalence checklist

| # | Guarantee | collect.py impl | class | push_collect plan | status |
|---|-----------|-----------------|-------|-------------------|--------|
| 1 | Raw VLM full text | `_make_vlm_interaction` (:542); `VLMInteraction` schema | INLINE + SHARED | import schema; share extracted helper | ☐ |
| 2 | Pre-action pose | loop :320-327,361-362; `env.get_state` | INLINE/GLUE | re-impl identically; **decide seed-paired init_* fields** | ☐ |
| 3 | Seed determinism | `env_seed_base + ep_idx` (:179) | GLUE | replicate exact expr; same `Optional[int]` param | ☐ |
| 4 | Per-round record | `round_meta` dict (:353-384) | INLINE/GLUE | re-impl dict; **push adds 3 primitive nums + τ_cmd**; keep recap-contract keys | ☐ |
| 5 | Replay schema/writer | `_write_episode` (:564); `ReplayBuffer` | SHARED + INLINE | import buffer/episode/timestep; share `_write_episode`; per-ep latency (not cumulative) | ☐ |
| 6 | Recap trigger | `_emit_recap_for_episode` (:609); `generate_recap` | SHARED core + INLINE | import `generate_recap`/`_RoundInfo`; prefer shared `rounds_from_meta_and_interactions`; keep readonly gate | ☐ |
| 7 | Round cap / termination | :187,251,405-468 (Pin-11 for push) | GLUE | re-impl; **push success = cube≤0.05m to goal; cap 12; plateau 3×<1cm** (Pin-11); keep break/tag structure | ☐ |
| 8 | Outcome + flags | `EpisodeOutcome` (schema); branches | SHARED enum + INLINE | import enum; **new push outcomes (object-not-moved / off-table) = EXTEND shared enum**; add pilot/confirmatory label (collect.py has none) | ☐ |
| 9 | Memory retrieval | :221-249,284; `MemoryRetriever` | SHARED + INLINE | reuse retriever + conversation preamble; smoke = pass None (defer) | ☐ |

## Gotchas (from the enumeration — must honor for true equivalence)

1. **`full_response` naming trap:** the field stores the parsed THOUGHT/diagnosis
   text, NOT the byte-raw HTTP body (the raw string never leaves `run_stage1`).
   Match this — or thread the raw string out of a push stage1 (collect.py does
   not). For smoke: match the gap (store thought), flag raw-body as a gen-0
   pre-req if the paper needs it.
2. **Schema init_* gap:** `init_cube_pose`, `init_left_ee_pose`,
   `init_right_ee_pose`, `env_seed` EXIST in `ReplayEpisode` for seed-paired
   verification but collect.py leaves them `None`. **Push DECISION:** push
   populates `init_cube_pose` + `env_seed` (it's cheap and push genuinely needs
   seed→cube determinism for r-tracking) — this is a push-side ADDITION that
   does NOT change collect.py, so it's not "divergence", it's push using a
   schema field collect.py left unused. Documented here so it's intentional.
3. **Per-round dict keys are a recap contract:** `rounds_from_meta_and_
   interactions` (stage4_recap.py:362) consumes the exact key set. Push keeps
   the same key names (`final_dist_l_cm` etc.) even where semantics differ, OR
   extends the shared adapter — not silently renames.
4. **No pilot/confirmatory labeling exists in collect.py.** Push ADDS an
   episode label field (pilot for smoke, confirmatory for gen-0) — a push-side
   addition, recorded here.
5. **Success predicate genuinely differs** (§7): reach = EE-to-target distance;
   push = cube displacement to goal (Pin-11). This is the ONE place the two
   instruments legitimately diverge in logic — everything else is equivalent.
   The divergence is task-semantic, not a drift defect, and is exactly why
   push is a separate instrument.

## Step-1 relocation verification (2026-08-26) — collect.py surgery cleared

The three shared helpers (`_active_arm_for_level`, `_make_vlm_interaction`,
`_write_episode`) were extracted to `collect_common.py` by PURE RELOCATION.
Verified at BOTH layers spec-required:
- **Static:** per-function SHA(pre-move) == SHA(post-move), byte-identical for
  all three; collect.py diff = import block added + bodies deleted, ZERO logic
  lines added.
- **Dynamic (L2 regression, teacher gemma-4-31B on 148):** an L2 episode ran
  end-to-end through the relocated path and wrote replay
  `aa99ddd2/failure/209ac5a8-65b.json` with a fully intact schema —
  `_write_episode` produced all fields (level=2, outcome, rgb paths, trajectory
  300 steps, total_vlm_latency); `_make_vlm_interaction` produced 10 intact
  vlm_interactions (full_response=thought 679 chars, parsed_left_pos,
  latency_ms); `_active_arm_for_level` drove both arms (L2 non-single-arm)
  correctly. Products equivalent to pre-move. **collect.py relocation CLEARED.**

## Sign-off

Each ☐ becomes ☑ when push_collect.py implements it and a test/inspection
confirms parity (or documents an intentional push-side addition above). The
completed ledger is the equivalence proof cited in P2 methods.

## Push cross-episode memory — pilot step (c) (2026-10-05, pre-run)

Implements rows 6 (recap) and 9 (memory) for the memory-ON pilot
(`wp3a_pilot_plan.md` (c)). Code: `aiongenos/orchestrator/push_memory.py`
(new), `push_collect.py`, `scripts/run_push_collect.py`; tests
`tests/test_push_memory.py` (fake env / fake teacher, no sim). The frozen
shared modules (collect.py, recap_buffer.py, retriever.py, stage4_recap.py,
vlm/client.py, stage1_reasoning.py, prompts.py, collect_common.py) are
**byte-untouched**; push imports their pieces. Rows 6/9 stay ☐ until a sim
run confirms them. Each push-side deviation from the L0/L2 path:

6. **Recap prompt is push-worded** (`build_push_recap_*`), replacing
   stage4_recap's reach prompt. SAME: `call_vlm_sync`, T=0.4, 400 tok, 180 s;
   ≤100-word hard cap via the shared `_trim_to_word_limit`; DINOv2 embedding
   of `init_pre` as the retrieval key; `RecapRecord` + `RecapBuffer.add`.
   DIFFERENT: (a) per-round cube displacement and cube→goal (cm), and the
   round-1 EEF target vs what the cube did; (b) cube/goal **integer grid
   coordinates are shown** — the reach invariant "GT coords never given to
   the recap" is relaxed because push stage-1 already oracle-reveals
   CUBE_POS/GOAL_POS every round (no new information); (c) the lesson must
   end in a `LESSON:` sentence; (d) key image = the scene AFTER the key round
   (`round_{k+1}_pre.png`, anchor `key_round_post`); none when the key round
   is the last (episode_end already shown). Reach used `round_k_pre`.
7. **Memory injection — Option A.** Round 1 ONLY gets a fresh single-turn
   `EpisodeConversation(get_stage1_system_prompt())` + preamble via
   `run_stage1_eef(conversation=…, memory_preamble_*=…)`; rounds 2+ keep
   `conversation=None` (stateless, as in the no-memory smoke). collect.py
   instead keeps ONE conversation for the whole episode (history carries the
   preamble forward). When no preamble is retrieved, round 1 is also
   stateless — payload layout is identical either way (system text folded
   into the first user turn, image, prompt; same T/max_tokens).
8. **Outcome class on cube→goal (cm)** (`classify_push_outcome`), not EE
   distance: success → `cube_not_moved` (every round disp < 1 cm, the Pin-11
   plateau threshold) → `near_miss` (best < 1.5×5 cm AND best < init−1 cm)
   → `wrong_direction` (final > init+1 cm) → raw outcome. Reach's fixed
   10 cm near-miss is meaningless here (init cube→goal is 7–10 cm).
9. **state_anchor schema.** `init_L_EE` = the REAL init EE grid (honest;
   near-constant because the EE starts at standby) — the reach path left it
   (0,0,0) for push (empty trajectory). `final_L_dist_cm` (reach: EE→target)
   is NOT written; push writes `init/final/best_cube_goal_dist_cm`,
   `push_situation`, `init_cube_int`, `goal_int`, `r1_eef_target_int`,
   `r1_eef_disp_m`, `r1_cube_disp_cm`. `left/right_reached` = None.
10. **Retrieval — `PushMemoryRetriever`** (shared `RecapBuffer.retrieve` /
    `MemoryRetriever` not used for ranking). SAME formula shape: score =
    α·img_cos + (1−α)·exp(−‖Δ‖_cm/scale), α = 0.4, same ceil(2/3·k)
    success floor, same image-dim-mismatch fallback, same drop of hits whose
    `init_pre` image is missing, top_k = 3, within-run retrieval allowed.
    DIFFERENT: (a) Δ is on `push_situation` = (cube_x, cube_y, goal_x,
    goal_y) base frame, not `init_L_EE`; (b) **scale = 5 cm** (reach 30 cm):
    the Pin-4b situation space has median pairwise ‖Δ‖ ≈ 5.4 cm (p10 2.5,
    p90 9.9; MC over push_s3a_cfg ranges) — at 30 cm the state term spans only
    0.92→0.72 (flat, the D10 image-collapse failure mode), at 5 cm 0.61→0.14;
    5 cm also equals the Pin-11 success radius; (c) records without
    `push_situation` are skipped and the run script REFUSES a root holding
    any (no task filter in the shared buffer → never share with reach);
    (d) no success_only / mode-flag / per-arm-label options (unused in the
    pilot); (e) stable argsort (tie order may differ from the original).
11. **Preamble text is push-worded** (`format_push_preamble_text`): cube
    start / goal grid, start cube→goal, round-1 EEF target and cube motion,
    final/best cube→goal, outcome class, lesson; closes with "choose your
    push target" (reach: "predicting the current target", L_EE bounds). The
    printed `similarity` is the combined score (reach prints it as "visual
    similarity", also combined).
12. **Per-episode dumps** under `--dump_images_root` (default
    `data/collect_dumps`, ON — collect.py defaults OFF) with collect.py's
    layout `{root}/{run_id}/{ep_id}/`: `episode_start.png`,
    `round_NN_pre.png`, `episode_end.png`, `meta.json`. No
    `round_NN_post.png`: post of round k == pre of round k+1 (no sim step in
    between), so it is not duplicated.
13. **Replay init_* + metadata** (resolves Gotcha 2): `init_cube_pose`
    {"yellow": xyz}, `init_left_ee_pose`, `env_seed` are populated (captured
    after reset, before any servo); `init_right_ee_pose` stays None.
    `metadata` carries label, task, goal_pose_b, init_cube_pose_b,
    push_situation, workspace_bounds, rounds_state (per-round pre-action
    ee/cube/goal + EEF target), memory_on/memory_hits, dump_dir. Written via
    `push_memory.write_push_episode`, a proxy around the SHARED
    `_write_episode` (signature/body unchanged). (c, s) for `p2_r_tracker`
    are computable from the replay alone: `scripts/analysis/push_r_inputs.py`
    (raw components + exploratory candidate grid; the scalar projection is a
    PI-pinned TODO).
14. **round_meta additions** (summary JSON): `ee/cube/goal_b_pre`,
    `ee/cube/goal_int_pre`, `cube_goal_dist_m_pre`, `memory_preamble`;
    episode entries add label, env_seed, init_cube_b, goal_b, init_ee_b,
    memory_hits. Existing keys unchanged.
15. **Env time-limit guard + auto-reset detection** (push-only; collect.py
    has neither). (a) Hard check at loop start: `env.env.unwrapped.
    max_episode_length` must exceed PUSH_ROUND_CAP × steps_per_segment × 1.5,
    else RuntimeError — the inherited env (24 s = 720 steps) auto-reset
    inside env.step at round 8 in the smoke (visible in run 3ca3b769 as a
    round-8 cube "jump" of 9–14 cm). (b) If `episode_length_buf[0]` drops
    across a segment the episode is flagged `env_auto_reset` and ended; the
    contaminated round is NOT recorded, outcome stays as-is, no recap is
    written (its end scene is a fresh reset), `final_cube_pose_b` = None.
16. **Pilot label everywhere:** replay `flags` (existing `label:pilot`) +
    `metadata.label`; summary top-level + per-episode `label`; recap
    `metadata.label` (+ `task`, `recap_prompt_version`).
17. **run_push_collect.py logging:** stdout handler on `aiongenos.*` (same
    fix as run_collect.py) so loop/memory INFO lines are visible. Output-only.
18. **Push state deltas (2026-10-05):** `get_state` PUSH_WAYPOINT branch now
    reports EE_TO_CUBE / CUBE_TO_GOAL as differences of grid positions (was a
    metric delta through the offset position map — x biased by −33). Branch
    is PUSH_WAYPOINT-only; the L0/L2 state path is byte-identical.
19. **Push output-line unit label:** `_S1_EEF_PUSH` "integer cm" → "same grid
    as CURRENT STATE — not cm". Push template only.
20. **Push episode_length_s = 300** (inherited 24 s auto-reset). L0/L2 keep 24 s
    (D11 A15 pin 8 sensitivity covers it there).
