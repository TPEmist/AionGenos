# WP1-③a rung-2′ (run 71134939): instrument diagnosis, macro reading, and Argon lessons

isaac, 2026-10-22. Requested by the PI. Evidence is in `evidence/2026-10-22_rung2p_diag/`: the spec plus 10 agy reports, which are agent-written. Every number below was re-run or spot-checked by isaac.

## 1. Is 0/50 real, or a tooling artifact?
**0/50 is real as a measurement.** No layer of the pipeline misreports what happened.

| Layer | Check | Result |
|---|---|---|
| Feedback text vs runtime | `scripts/analysis/wp3a_rung2p_validate.py`; negative test: a mutated copy is caught | 547/547 rounds match |
| Prompt actually sent | qa1 rebuilt the round-5 payload from code; it matches `meta.json` byte-for-byte; `tests/test_push_memory.py` 37 passed | OK |
| Memory / history vs P1 | mem1 and mem2 worked independently and agree | Same `EpisodeConversation` code as P1 (see §1a) |
| Controller | TCP→target error, median 0.05 cm; low-z targets are reached | OK |
| Images | No stale frames: 0/547 identical consecutive frames | OK |
| Parser | Strict regex with no Z default | Z=53 is the teacher's own output |
| Success detector | Best cube→goal reached = 7.3 cm = the initial minimum; the cube moved >1 cm in 0 episodes | Correct (cube was never pushed) |
| Feasibility | A scripted push through the same executor | Succeeds in 2 rounds (`logs/wp3a_reach_real.log`) |

**Isaac's own instrument error, caught by beh2 and prose_res:**
- `validate.py` reported that "thought mentions height" in 521/597 rounds. That is a regex artifact: it matched "top-down view" and "lower Y".
- Real vertical reasoning occurs in 25–46/597 rounds (4–8%).

### 1a. What the memory actually contains (answer to the PI)
It is not "all past text and images":
- **Cross-episode:**
  - top-3 recaps (text) plus each recap's start front image, round 1 only;
  - from round 2 on the images are stripped (`aiongenos/vlm/client.py:146–150`) and only the text stays in turn 0.
- **Within-episode:**
  - turn 0 plus the last 6 user/assistant pairs, as text;
  - images only for the current round (front and top).
- **Identical to the P1 code path.**
- **Differences from P1:** the feedback verdict metric (§2.1), the push template, the extra top view, and that the system prompt says "bimanual … both arms".

## 2. The interface defects behind 0/50
These are design gaps, not measurement bugs.
1. **The verdict line is actively misleading.**
   - It is computed on cube→goal (`push_feedback.py:43`), so all 547/547 rounds read "No significant progress … Try a different direction", even when the fingertip had closed in.
   - This is the known option (b).
2. **No axis convention or units (new).**
   - The prompt never says which way ±X/±Y point, or how many cm one grid unit is. The units also differ per axis: 0.45 / 0.40 / 0.35 cm per unit.
   - The needed push is +X (median 8.6 cm, against |ΔY| 1.7 cm). Yet 536/597 moves are Y-dominant.
   - In 62–64% of thoughts the teacher calls Y the forward or push axis (prose_res 370 and beh2 384 count this independently).
3. **Height is not observable.**
   - The top camera is at nadir, so height shows as at most ~2 px of parallax.
   - The front camera has a 12 mm focal length and 45 mm aperture (about 124° FOV) at 256 px. Fingertip and cube sit within ±2 px rows (qa2; front camera `aiongenos/tasks/base/reach_env_base_cfg.py:36–42` (inherited, same as P1 L0a), top camera `push_s3a_cfg.py:347–375`).
   - The 3D tip→cube scalar cannot be split into planar and vertical parts. The teacher reads the ~4.3 cm vertical floor as an xy error in 83% of rounds (beh2).
4. **History locks the height.** This is the rung-2 vs rung-2′ comparison on the same seeds (`scripts/analysis/wp3a_rung2_vs_2p_z.py`, re-run).

   | | rung-2 (stateless) | rung-2′ (history + feedback) |
   |---|---|---|
   | Rounds in contact band z∈[30,40] | 53% | 2% |
   | Round-2 Z=53 | 1/50 | 45/50 |

   - The anchor already exists at round 1 (the standby proprioception); history and feedback keep it.
   - Hypothesis, not yet tested: the cross-episode preamble shows past round-1 targets (`push_memory.py:587`), which were Z=53, so the anchor also propagates across episodes.

Critic's gaps in `validate.py`:
- It has no checks for ORI error (up to 38.75°), τ saturation (60 rounds), `env_auto_reset` flags, setpoint clamps, or cube quaternion (not logged).
- None of these explains 0/50 here, but they should be added before contact runs.

## 3. Macro reading
- **"0/50 = the teacher cannot push" does not follow.** The teacher was below the competence floor for an interface reason.
  - The founding intent explicitly lists **frame conventions and coordinate plumbing** and **primitive forms** as grantable marginal knowledge (IN). We withheld them anyway.
  - The rung ladder jumps from scalars (rung-2) straight to object coordinates (rung-3, conditional disclosure). It never offers the marginal grants first.
- Minimum-viable-competence law: with 0 successes, memory has nothing positive to retrieve. Pushing more rounds or episodes through this interface cannot start the loop.
- **Contact height is marginal knowledge for this task:** the cube always rests on the same table, so the height does not depend on the situation. Per P1, distillation moves the marginal. If the teacher gets height right, the student can inherit it without seeing depth.
- x/y (where the cube is, which way to push) is the conditional part that must be earned.
- The P1 history mechanism itself has a side effect, self-anchoring on its own earlier turns. That does not change any P1 claim, but it is worth one line of discussion.

## 4. Gemini 4 Argon: what it does and what it means for us
Sources: Google's own pages only; no paper. Facts confirmed by two independent agents plus isaac's fetch of developers.googleblog.com/gemini-4-argon-for-robotics.
- **What it is:** a reasoner and coder over **action primitives**, not a VLA.
- **What the harness supplies:**
  - an explicit **axis convention in the prompt**: "+X (UP in image): away from robot base; +Y (LEFT): world left; +Z: height above table";
  - **projected world coordinates** drawn on the image (a 2 cm grid);
  - **contact-terminated primitives** (`move_until_contact`, `place_until_contact`).
- **Practice and training:**
  - contact skills are practised in MuJoCo twins under "no sim cheating" rules;
  - a VLA fine-tuned on 4,500+ sim episodes went from 56% to 75% real success.
- **Demonstrations:** teleop episodes and human video serve as Real2Sim inputs. Argon makes **no zero-demonstration claim**.

Lessons:
1. Argon's harness supplies exactly the three things our teacher lacks: axes, units, and contact sense. The first two are **frame plumbing**; contact-terminated motion is a **primitive form**. Both are IN under our founding intent, so each needs a ledger entry with a reclamation condition.
   - The image coordinate grid is different: it makes object positions readable, which amounts to rung-3. That needs PI consent plus a ledger entry.
2. Their sim-episode → VLA fine-tune loop has the same structure as our P2 expert iteration. Their "no sim cheating" rule plays the role of our auditability guard.
3. Our distinctive claim (zero demonstrations; conditional knowledge earned) is untouched. Argon reaches competence partly through human video and teleop twins.

## 5. Multi-view teacher → single-view student
- It is known to work. Acar et al., RA-L, arXiv 2303.07026 (abstract checked): a single-view student distilled from a multi-camera teacher "can successfully learn to grasp and lift … which was not possible with a single-view policy alone". Learning-by-Cheating and asymmetric actor-critic are related.
- lit1's overall verdict, "No for contact-rich", is **rejected**: its own paper 8 says the opposite. lit1's specific percentage drops are unverified and not used here.
- For us, height is marginal (§3), which favours distillation.
- Human analogy: final height is set by **touch**, not vision. A contact-terminated descent is closer to an infant reflex than an extra camera is.

## 6. For PI decision (not acted on)
New option (d), a marginal-grant bundle, each item ledgered:
- d1: an axis and unit convention line in the prompt;
- d2: the pre-contact verdict on tip→cube (= option b);
- d3: either a contact-terminated descent primitive or a side camera.

Comparability rule: the ladder must be re-run under one interface (rung-1′ and up). The isaac recommendation is d1+d2 first: they are the cheapest and are plumbing only. Then judge d3.
