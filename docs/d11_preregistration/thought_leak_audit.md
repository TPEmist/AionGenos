# Amendment 9 §9.4 — Native-thought cross-episode memory leak audit

**Purpose.** Because all four Amendment 8 training arms drink from the
same 2791-row pool of memory-teacher (D10-ext) trajectories, the
`INTRINSIC_RATIONALE` block used by A_ctrl_rat / B_main is the
teacher's own thought text generated AFTER the teacher saw retrieved
PAST_LESSONS. That thought can echo the retrieval in language even
without an explicit gist header. Quantify the echo rate so the
A_action_only vs A_ctrl_rat and A_ctrl_rat vs B_main contrasts can be
interpreted correctly.

## Method

Parse each row's `target_response`, extract the substring between
`INTRINSIC_RATIONALE:` header and the first `LEFT_TARGET_POS:` line,
regex-match against two pattern families:

- **Cross-episode leak** — references outside the current episode:
  `past episodes/attempts/scenes/experience/data/examples`,
  `past` (excluding `past round/move/movement`), `lesson`,
  `similar past/episode/scene/situation`,
  `previous episode/attempt/scene`, `earlier episode/attempt/scene/round`,
  `historical / history / prior experience`,
  `from the near miss / past / prior / previous episode`,
  `as (shown|indicated|suggested) by (the) (past|prior|previous episode|lesson)`,
  `recall`.
- **Episode-internal** — references to prior rounds within the current
  episode (critic-feedback style, not memory leak):
  `previous move/movement/round/action/step`,
  `previous result/position/target/prediction`.

Both are case-insensitive.

## Result

Corpus: `data/training_sets/v_final_kto_A_ctrl_rat.jsonl`, 2791 native
thoughts.

| category | matches | % of thoughts |
|---|---|---|
| **any cross-episode reference** | **884** | **31.7%** |
| `past episodes/attempts/scenes` | 591 | 21.2% |
| `past` (excluding prev round)   | 670 | 24.0% |
| `lesson`                        | 384 | 13.8% |
| `previous episode`              |  86 | 3.1% |
| `similar past`                  |  37 | 1.3% |
| `history / prior experience`    |  26 | 0.9% |
| `recall`                        |  62 | 2.2% |
| `from past`                     |  16 | 0.6% |
| `as shown by past/lesson`       |   6 | 0.2% |
| `earlier episode`               |   1 | 0.0% |
| episode-internal only (not leak)| 759 | 27.2% |

## Cross-arm sanity

A_ctrl_rat and B_main use byte-identical thought text (same 2791
`(run, ep, round)` keys; 2791/2791 thoughts match char-for-char). The
two arms carry the same 31.7% implicit leak and differ only in whether
an explicit `PAST_LESSONS:` gist block precedes the thought. The
A_ctrl_rat vs B_main contrast is therefore symmetric on the implicit
leak channel.

## Representative examples (A_ctrl_rat)

- `[past]`: "…position. Looking at the past episodes, there is a
  recurring theme of visual misalignment regarding the X-axis (lateral
  offset) and Y-axis (depth). Episode 1 suggests the target may be
  further left…"
- `[previous, lesson]`: "The previous move resulted in a regression,
  meaning moving further left (to X=−25) and further forward (to
  Y=30) actually increased the distance to the target…"
- `[past]`: "The red cube is positioned slightly to the left and
  ahead of the current left end-effector position. Based on the past
  episodes, I must be cautious about overestimating the lateral (X)
  displacement…"

## Directional consequence (from Amendment 9 §9.4)

- **A_action_only vs A_ctrl_rat**: A_ctrl_rat carries +31.7% implicit
  memory language plus +121-token rationale format. Their difference
  therefore mixes format and implicit-leak effects; the
  "rationale-format-only" factor is **overstated** by this contrast.
- **A_ctrl_rat vs B_main**: B_main layers an explicit gist on top of
  the same 31.7%-leaked thought. Any residual gist effect is
  measured against a partially-informed baseline; the explicit
  retrieval factor is **understated** by this contrast (conservative
  direction).

No thought-cleaning intervention. Curation-freedom hazard exceeds
benefit; the direction is declared and the interpretation is written
against the biased contrast.

## Reproducibility

The exact grep script is stored inline in the Amendment 9 filing
transcript. Regex definitions used (Python `re.IGNORECASE`):

```python
CROSS_EP_PATTERNS = {
    'past_episodes': r'\bpast\s+(episodes?|attempts?|scenes?|experience|data|examples?)',
    'past_only':     r'\bpast\b(?!\s+(round|move|movement))',
    'lesson':        r'\blesson',
    'similar_past':  r'\bsimilar\s+(past|episode|scene|situation)',
    'previous_ep':   r'\bprevious\s+(episode|attempt|scene)',
    'earlier_ep':    r'\bearlier\s+(episode|attempt|scene|round)',
    'history':       r'\b(historical|history|prior\s+experience)\b',
    'from_past':     r'\bfrom\s+the\s+(near\s+miss|past|prior|previous\s+episode)\b',
    'as_shown_past': r'\bas\s+(shown|indicated|suggested)\s+by\s+(the\s+)?(past|prior|previous\s+episode|lesson)',
    'recall':        r'\brecall',
}
EPISODE_INTERNAL = {
    'prev_move':   r'\bprevious\s+(move|movement|round|action|step)',
    'prev_result': r'\bprevious\s+(result|position|target|prediction)',
}
```
