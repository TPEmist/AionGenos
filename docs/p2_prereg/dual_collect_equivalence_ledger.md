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
(new), `push_collect.py`, `scripts/run_push_collect.py`,
`scripts/analysis/push_r_inputs.py` (new); tests `tests/test_push_memory.py`
(fake env / fake teacher, no sim). The frozen shared modules (collect.py,
recap_buffer.py, retriever.py, stage4_recap.py, vlm/client.py,
stage1_reasoning.py, collect_common.py) are **byte-untouched**; push imports
their pieces. Rows 6/9 stay ☐ until a sim run confirms them.

**Revision note:** a first draft of this section (same day, never run)
keyed retrieval and the recap/preamble on GT cube/goal. The PI ruling of
2026-10-05 (*the model observes IMAGE + PROPRIOCEPTION only; object positions
are perception, never oracle-fed; GT only in offline analysis and the success
predicate*) superseded it before any memory-ON episode ran (the draft is in commit
8c2a337; the only run on that code, eye-gate 098975dd, had memory OFF —
summary `memory_on: false` — and used the pre-ruling oracle stage-1
state). This section is the revised design.

Each push-side deviation from the L0/L2 path:

6. **Recap prompt is push-worded and rung-gated** (`build_push_recap_*`),
   replacing stage4_recap's reach prompt. SAME: `call_vlm_sync`, T=0.4,
   400 tok, 180 s; ≤100-word hard cap via the shared `_trim_to_word_limit`;
   DINOv2 embedding of `init_pre` as the image key; `RecapRecord` +
   `RecapBuffer.add`. Model-visible content by `obs_rung` (one source,
   `disclosed_values`): **rung 1** = task, predicate outcome
   (`success`/`failure` only), round count, per-round TCP target vs TCP
   reached (grid) + ORI, images; **rung 2** + the outcome string/class, the
   success rule, scalar cube→goal (start and per round) and per-round closest
   TCP→cube; **rung 3** + cube/goal grid coordinates and cube displacement.
   The reach invariant "GT coordinates never given to the recap" HOLDS at
   rungs 1–2. The lesson rules carry no strategy hints (the reflection
   names an adjustment *in its own words*); format rules + the `LESSON:`
   ending stay. Key image = the scene AFTER the key round
   (`round_{k+1}_pre.png`, anchor `key_round_post`), none when the key round
   is the last; at rung 1 the key round is the MIDDLE round (choosing it by
   GT distance would leak GT through the image choice). Reach: `round_k_pre`.
7. **Memory injection — Option A.** Round 1 ONLY gets a fresh single-turn
   `EpisodeConversation(get_stage1_system_prompt())` + preamble via
   `run_stage1_eef(conversation=…, memory_preamble_*=…)`; rounds 2+ keep
   `conversation=None` (stateless, as in the no-memory smoke). collect.py
   keeps ONE conversation for the whole episode. With no preamble round 1 is
   also stateless — payload layout is identical either way (system text
   folded into the first user turn, image, prompt; same T/max_tokens).
8. **Outcome class on GT cube→goal (cm)** (`classify_push_outcome`), not EE
   distance: success → `cube_not_moved` (every round disp < 1 cm, the Pin-11
   plateau threshold) → `near_miss` (best < 1.5×5 cm AND best < init−1 cm) →
   `wrong_direction` (final > init+1 cm) → raw outcome. It is an **OFFLINE**
   label (`metadata.offline_gt.outcome_class`); the model sees it only at
   rung ≥ 2. Reach's fixed 10 cm near-miss is meaningless here (init
   cube→goal is 7–10 cm).
9. **Recap record schema.** `state_anchor` = model-visible fields only (it
   feeds the preamble): `init_L_EE` = init **TCP** grid (the retrieval state
   key), `final_L_EE`, `ee_reference: "tcp"`, round count, `obs_rung`,
   `outcome_class` (predicate verdict at rung 1), round-1 target / ORI / TCP
   reached, `disclosed` (rung-allowed values). `final_L_dist_cm` (reach:
   EE→target) is not written. GT lives in `metadata["offline_gt"]`
   (cube/goal, situation, per-round cube→goal/displacement, best/final,
   class, round-1 contact report) and is never read by retrieval or the
   preamble. `left/right_reached` = None.
10. **Retrieval = the SHARED `RecapBuffer.retrieve`** (the L0a combined
    score α·DINOv2 cos + (1−α)·exp(−‖Δ init_L_EE‖/scale), success floor
    ceil(2/3·k), image-dim fallback), α = 0.4, **scale = 30 (L0a default)**,
    top_k = 3, within-run retrieval allowed. Key = observables only: start
    image + init TCP grid. **Stated plainly:** the TCP starts at the fixed
    Pin-7a standby every episode, so Δ init_L_EE ≈ 0 and state_sim ≈ 1 for
    every candidate at ANY scale — the state term is a constant offset and
    the IMAGE term decides the ranking. That is the L0a design (L0a's EE
    also starts at a fixed pose). `PushMemoryRetriever` only wraps it: drops
    non-push hits (defensive), drops hits whose `init_pre` image is missing
    (as MemoryRetriever), formats the push preamble. The run script REFUSES
    a recap root holding non-push recaps or recaps of another `obs_rung`
    (no task filter in the shared buffer; lessons written under another
    disclosure level would leak it). No success_only / mode-flag / per-arm
    options (unused in the pilot).
11. **Preamble text is push-worded and rung-gated**
    (`format_push_preamble_text`): start TCP, round-1 target + ORI → TCP
    reached, outcome (predicate verdict at rung 1), rounds, lesson; rung 2
    adds disclosed cube→goal start/end + outcome class, rung 3 adds disclosed
    cube/goal grid. Gating uses the CURRENT run's rung. Closes with "choose
    your target" (reach: "predicting the current target", L_EE bounds). The
    printed `similarity` is the combined score (reach prints it as "visual
    similarity", also combined).
12. **Per-episode dumps** under `--dump_images_root` (default
    `data/collect_dumps`, ON — collect.py defaults OFF) with collect.py's
    layout `{root}/{run_id}/{ep_id}/`: `episode_start.png`,
    `round_NN_pre.png`, `episode_end.png`, `meta.json`. No
    `round_NN_post.png`: post of round k == pre of round k+1 (no sim step in
    between).
13. **Replay init_* + metadata** (resolves Gotcha 2): `init_cube_pose`
    {"yellow": xyz}, `init_left_ee_pose` (= init **TCP**, `metadata.
    ee_reference = "tcp"`), `env_seed` populated after reset, before any
    servo; `init_right_ee_pose` stays None. `metadata`: label, task,
    obs_rung, init TCP grid, rest hand quat, GT (init_cube_pose_b,
    goal_pose_b, offline_gt_situation, final_cube_pose_b), workspace_bounds,
    rounds_state, memory_on/memory_hits, dump_dir. Written via
    `push_memory.write_push_episode`, a proxy around the SHARED
    `_write_episode` (signature/body unchanged). (c, s) for `p2_r_tracker`
    are computable from the replay alone (`push_r_inputs.py`: c_raw = round-1
    TCP target − init TCP; s from offline GT; exploratory candidate grid; the
    scalar projection is a PI-pinned TODO; r is per-rung, mixed rungs
    refused).
14. **round_meta additions** (summary JSON, offline): `ee_start_b/int`
    (TCP), GT `cube_b_pre`/`goal_b_pre`/`cube_goal_dist_m_pre`,
    `memory_preamble`; episode entries add label, obs_rung, env_seed,
    init_cube_b, goal_b, init_tcp_b, memory_hits.
15. **Env time-limit guard + auto-reset detection** (push-only). (a) Hard
    check at loop start: `env.env.unwrapped.max_episode_length` must exceed
    PUSH_ROUND_CAP × steps_per_segment × 1.5, else RuntimeError — the
    inherited env (24 s = 720 steps) auto-reset inside env.step at round 8
    in the smoke (run 3ca3b769: a round-8 cube "jump" of 9–14 cm). (b) If
    `episode_length_buf[0]` drops across a segment the episode is flagged
    `env_auto_reset` and ended; that round is NOT recorded, outcome stays
    as-is, no recap is written, `final_cube_pose_b` = None.
16. **Pilot label everywhere:** replay `flags` (`label:pilot`) +
    `metadata.label`; summary top-level + per-episode `label`; recap
    `metadata.label` (+ `task`, `recap_prompt_version`).
17. **run_push_collect.py logging:** stdout handler on `aiongenos.*` (same
    fix as run_collect.py). Output-only.
18. **Orientation: motion-dependent neutral RETIRED.**
    `neutral_contact_orientation_b` / `_euler_zyx_to_quat` / `_quat_mul` (and
    the `prev_x_n` hysteresis, `neutral_x_n` record) are gone from the push
    path. After each reset `q_rest = env.get_left_hand_quat_b()` (the live
    Pin-7a standby orientation); each round
    `q_cmd = push_body.command_quat(q_rest, ORI)` = Rz(Y)·Ry(P)·Rx(R)·R_rest
    about BASE axes; no ORI → exactly q_rest. Every pose decision is the
    brain's (the old neutral was a primitive-side opinion).
19. **Targets are TCP.** `execute_push_segment(target, q_cmd, steps,
    frame_every, target_is_tcp=True)`; the executor converts TCP → hand with
    the live-measured offset. round_meta records the TCP target (int +
    metric), `tcp_target_b`, `hand_target_b`, `tcp_final_b`,
    `tcp_reach_err_cm` (‖tcp_final − target‖), `servo_min_err_cm` (hand
    servo), `ori_err_deg_final`, `ori_err_deg_max_last20`, the full `contact`
    report (GT, offline), τ fields. EE start = TCP.
20. **`obs_rung` (disclosed scaffold rung).** `--obs_rung {1,2,3}` (default
    1) sets `iface.push_obs_rung` (which shapes the stage-1 state's
    `oracle_block`); the loop reads it once from the env (single source) and
    records it in every replay (`metadata.obs_rung`), summary (top-level +
    per episode, dump meta.json) and recap (`metadata.obs_rung`,
    `state_anchor.obs_rung`). A retriever built for another rung is refused.
    The P2 paper must state the rung of every dataset.
21. **Observables-only model inputs** (the PI ruling, restated as the push
    invariant): stage-1 prompt (prompts.py `_S1_EEF_PUSH` + `_push_state`),
    recap prompt, retrieval key and preamble carry no GT at rung 1. GT is read
    by push_collect only for the success predicate and offline records.
    Tests assert the absence of GT markers in rung-1 recap prompts,
    preambles and stage-1 states.
22. **L0a comparison, corrected.** Earlier push docs called the two-leg
    oracle reveal "the L0a Fix-3 convention". L0a's actual teacher condition
    is `prompts.py _S1_POS_HEAD`: EE positions + a scalar EE→target distance,
    no object coordinates. Push rung 2 = that condition; rung 1 is
    stricter; rung 3 (coordinates) has no L0a counterpart.
23. **GIF overlay** (human-eye gate, PI only, never a model input): the tag
    (round, GT cube→goal, contact anatomy of the round's first cube motion)
    is drawn in a 14-px BOTTOM margin strip below the scene (the canvas
    grows); the old top bar that covered scene pixels is gone.
24. **Proprio self-calibration.** The hand→TCP offset is MEASURED LIVE from
    the sim bodies at every segment (`push_body.tcp_offset_local`), never a
    hardcoded constant; state and target share the TCP reference.
    **Deferred P3 item:** self-calibration of that offset from contact events
    (the body learning its own fingertip from where the cube starts moving),
    instead of reading it from the simulator.
25. **Recap prompt version** `push_recap_v2_obs_rung` stamped in every
    recap's metadata (v1 = the superseded GT draft, never run).
26. **Table-collision interlock (SAFETY, not knowledge; 2026-10-05):** push
    executor lifts any TCP target / carrot setpoint over the table footprint
    below top+1cm to top+1cm; events logged per round. Any real arm has it.
    Run 3577d85e's 45cm wrist knock happened without it. L0/L2 untouched.
27. **Known body limit:** Y+30 yaw from rest untrackable (22.6°); recorded as
    a body fact, visible to the model via proprioception; not a fix.
28. **Interlock scope (PI 2026-10-05):** static scene only = table top slab +
    robot body link box (nearest-face projection) + ground, all measured live
    from USD; supersedes item 26's table-only scope. Not extended to awkward
    free poses (those are learnable). No stand prim exists in the scene.
