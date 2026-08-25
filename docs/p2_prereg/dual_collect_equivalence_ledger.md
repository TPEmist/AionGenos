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

## Sign-off

Each ☐ becomes ☑ when push_collect.py implements it and a test/inspection
confirms parity (or documents an intentional push-side addition above). The
completed ledger is the equivalence proof cited in P2 methods.
