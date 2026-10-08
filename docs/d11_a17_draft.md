# D11 Amendment 17 — text vs image in the retrieved context (DRAFT, NOT LOCKED)

**Drafted** 2026-10-08 by isaac, for the PI to lock. This is written after A15 and
before any A17 data. When the PI locks it, it moves into
`docs/d11_preregistration.md` as Amendment 17. The lock commit subject must
start with `docs(d11): A17 LOCK`; the night waiter keys on that string.

## Question
In C_retrieval, each retrieved episode reaches the prompt as two things: its
**lesson text** and its **`init_pre` image**. Which of the two carries the
+34 pp? A15 showed the effect does not depend on the weights loaded. It did
not separate text from image (paper §4.3: "not separable here").

## Protocols (each n = 100, seed base 4500, paired with D11 `C_retrieval` 49/100)

The anchor is C_retrieval itself: A_ctrl_rat SFT+KTO adapters, variant
`rationale_with_retrieval`, the frozen buffer `7d4f3f9e…`, readonly, top_k 3.

| Protocol | What reaches the prompt | Removed |
|---|---|---|
| `a17_text_only` | the lesson and all state/outcome lines | the 3 anchor images, the "Image i: …" lines, and the header clause announcing them |
| `a17_image_only` | the 3 anchor images and all state/outcome lines | the 3 lesson lines; the header clause "a one-paragraph lesson…" and the closing "past lessons" are reworded to "past episodes" |

- **Retrieval selection is unchanged.** The same records are chosen by the
  same score, including the 0.4 image-embedding weight. A17 ablates what the
  policy sees, not what is retrieved.
- Implementation:
  - `aiongenos/memory/a17_ablation.py` is a wrapper. The frozen
    `retriever.py` / `collect.py` / `client.py` are untouched.
  - Flag: `scripts/run_collect.py --a17_context`. When it is unset, the code
    path is unchanged.
  - Driver: `scripts/training/run_a17_night.sh`. It is a clone of the A15
    night driver: same flags, readonly tree-hash gate and manifest
    `logs/a17_manifest.jsonl`. It refuses to run while unlocked.
  - Tests: `tests/test_a17_ablation.py`. Each mode removes exactly its
    component, and every other line stays byte-identical.
- The state/outcome lines (init/final L_EE, final distance, outcome, rounds)
  stay in both arms. They are text, but they are not the lesson. **The PI
  must decide (D1)** whether they count as "text" for this question.

## Predictions — PI to fill (D2)
Proposed slots, with my prior marked as a prior and not as evidence:
- **text_only:** SR ≈ C_retrieval (within the paired MDE).
  - Prior: the retrieval score already uses the image. In P1 the
    lesson/state text was where calibration lived (L0a scalar condition).
- **image_only:** SR < C_retrieval.
  - Prior: without the lesson, the images give only "what the scene
    looked like".

## Analysis rules (carried from A15, unchanged)
- z is primary if the A14 §14.1 fingerprint gate fails (it has failed in
  every D11/A15 contrast); McNemar is the sensitivity check.
- α = 0.05, two-sided. MDE = 19.8 pp at the C_retrieval rate.
- "≈" means |Δ| inside the MDE and p ≥ α.
- Pin 8 (24 s) sensitivity on both contrasts.
- Also reported: text_only vs image_only; each arm vs the no-retrieval
  A_ctrl_rat (15/100); the A15.1 R1' slope reading at 15 mm.

## Pre-committed routing
| text_only | image_only | Paper wording |
|---|---|---|
| ≈ C_ret | < C_ret | "the lesson text carries the effect; the image anchors selection" |
| < C_ret | ≈ C_ret | "the anchor image carries the effect" |
| ≈ C_ret | ≈ C_ret | "either component suffices (redundant)" |
| < C_ret | < C_ret | "both are needed (complementary)" |

**Power caveat (disclosed).** With n = 100, only drops of ≥ ~20 pp are
detectable. Smaller partial contributions read as "≈", which is
under-powered and is not shown equivalent. The paper line must say "not
distinguishable at n = 100", not "equal".

## Schedule (PI 2026-10-08)
- Nights only. text_only runs on 10-08 and image_only on 10-09, each about
  8–12 h.
- Expected to land 10-10, before the 10-16 camera-ready cut-off: eligible for
  one line on page 5.
- If it slips past 10-16, it goes to TMLR. No rushing.

## Decisions needed from the PI before the lock
- **D1.** Do the state/outcome lines stay in both arms?
  - Proposed: yes, so that exactly one component is removed.
- **D2.** The predictions above: confirm or replace.
- **D3.** Should a third arm, `no_context` (retrieval runs but nothing is
  attached), be added?
  - Proposed: no. D11 `A_ctrl_rat` 15/100 already serves as that baseline,
    with the same weights and no retrieval. The only gap is the prompt
    variant, and that is disclosed.
