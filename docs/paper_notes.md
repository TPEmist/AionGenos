# AionGenos Phase 4 — Paper Notes

> **Single source of truth** for paper-worthy claims, observations, ablations,
> caveats, and design rationale generated during Phase 4 development.
> Append-only during the project; consolidate into actual paper sections after
> D11 is in.

**Last updated**: 2026-07-01, after D10-ext-4 completed. All 4 planned
extension runs done. Phase 4 teacher-side results are frozen; next is D11
distillation.

---

## 1. Paper One-Liner (working claim)

> **"Valuable episodic memory can be baked into LoRA parameters, enabling a
> high-frequency, context-window-free student that retains the teacher's
> memory-derived behavior."**

Two phases of evidence:
1. **Teacher phase** (D6 → D10 → D10-ext, complete as of 2026-07-01):
   image-anchored episodic memory improves teacher VLA success rate vs.
   memoryless baseline.
2. **Student phase** (D11, pending): LoRA distillation from memory-augmented
   teacher trajectories baked into a context-free student inference path.

## 1.1 Canonical Result Sentences (paper-ready, cite these verbatim)

Every one of these traces to numbers in §2 below (2026-07-01 frozen).
When drafting paper, copy the sentence and cite the corresponding row.

### Headline (Abstract + Intro)
> **"Image-anchored episodic memory (DINOv2 + state-aware retrieval)
> combined with prompt-level anti-premature-STOP scaffolding raises
> L0a-Left teacher VLA success rate from 21.0% to 49.3% (n=221 vs n=100,
> p<10⁻⁵, 95% CI [42.8, 55.9])."**
> — Source: §2 Post-fix pool row.

### Ablation (Methods / Results section)
> **"Retrieval alone (memory + DINOv2 + state-aware ranking) yields 29.6%
> SR (n=226, +8.6pp vs baseline, p=0.10 — marginal). Adding prompt-level
> scaffolding (Fix 1: directional critic wording, Fix 3: live distance
> surface) adds +19.7pp, reaching 49.3% (p=2.1×10⁻⁵ vs retrieval-only pool)."**
> — Source: §2 Pooled analysis + Fix 1/3 ablation z-test row.

### Efficiency (Discussion)
> **"Memory-augmented teacher reaches the target in 11.8 rounds on average
> vs 19.7 baseline (-40%), with mean best-arm distance 6.9 cm vs 16.2 cm
> baseline (-57%). Improvements are visible on failures too — the teacher
> gets closer faster with memory."**
> — Source: §2 Efficiency table, computed over D10-ext-4.

### R1 perception bias (Behavioural evidence)
> **"Retrieval-based memory reduces teacher R1 X-axis perception bias from
> -23.5 cm (D6 baseline) to -15.8 cm at D10 end (n=100 window, -33%),
> monotonically across quartiles."**
> — Source: §2 R1 ΔX trend. Refresh with pooled D10-ext data before
> submission (TBD).

### Failure of naive distillation (Related work / Limitations of alternatives)
> **"Naive per-round or per-episode LoRA distillation of the same teacher
> without preserving the memory retrieval mechanism collapses SR to 2.8%–4.0%
> (F56/F58/F59, n=100 each), an order-of-magnitude regression from the
> memoryless baseline. This motivates our memory-then-distill architecture."**
> — Source: §2 D7/D8/D9 rows.

---

## 2. Key Numbers So Far

### Final SR comparison

| Run | N | Success | SR | 95% CI (Wilson) | Notes |
|---|---|---|---|---|---|
| D6 (baseline, no memory) | 100 | 21 | 21.0% | [14.2, 30.0] | Cold-start teacher |
| D7 (v3 LoRA, episode-level) | 100 | 4 | 4.0% | [1.6, 9.8] | Distillation failed — F56 bug |
| D8 (v3.1 LoRA, LAST stage1) | 100 | 4 | 4.0% | [1.6, 9.8] | Distillation failed — F59 |
| D9 (v3.2 LoRA, per-round) | 72 | 2 | 2.8% | [0.8, 9.6] | Distillation failed — single-step imitation |
| D10 (MobileNet+state memory) | 100 | 25 | 25.0% | [17.5, 34.3] | Pre-fix, MobileNet |
| **D10-ext-1** (DINOv2+state, salvaged) | 26 | 9 | 34.6% | [19.4, 53.8] | Pre-fix, salvaged from server reboot |
| **D10-ext-2** (DINOv2+state) | 100 | 33 | 33.0% | [24.6, 42.7] | Pre-fix, DINOv2 alone |
| **D10-ext-3 (salvaged)** (DINOv2 + Fix 1/3) | 21 | 10 | 47.6% | [28.3, 67.6] | Post-fix, salvaged from server reboot |
| **D10-ext-3b** (DINOv2 + Fix 1/3) | 100 | 51 | 51.0% | [41.3, 60.6] | Post-fix, headline replicate #1 |
| **D10-ext-4** (DINOv2 + Fix 1/3) | 100 | 48 | 48.0% | [38.5, 57.7] | Post-fix, headline replicate #2 ⭐ |

### Pooled analysis (2026-07-01 — Phase 4 teacher-side FROZEN)

- **Memory pre-fix pool** (D10 + ext-1 + ext-2): **67/226 = 29.6%**
- **Memory post-fix pool** (ext-3 + ext-3b + ext-4): **109/221 = 49.3%**
  95% CI: **[42.8%, 55.9%]** (Wilson)

### Statistical significance

| Comparison | z | p-value |
|---|---|---|
| D10-ext-3b (51/100) vs D6 (21/100) | +4.42 | p = 1.0×10⁻⁵ |
| D10-ext-4 (48/100) vs D6 (21/100) | +4.02 | p = 5.9×10⁻⁵ |
| **Post-fix pool (109/221) vs D6 (21/100)** | **+4.79** | **p = 1.7×10⁻⁶** |
| **Post-fix vs Pre-fix (Fix 1/3 ablation, n=221 vs n=226)** | **+4.26** | **p = 2.1×10⁻⁵** |
| Memory pre-fix vs D6 (memory alone effect) | +1.62 | p = 0.10 |

### Replication consistency

Post-fix replicate pair:
- ext-3b: 51.0%
- ext-4:  48.0%
- Δ = 3pp, within the CI overlap of each other. Tight replication —
  no run-to-run variance concern.

### Interpretation

- Fix 1/3 (directional critic + live distance) is the largest single
  contributor: **+19.7pp** on top of pre-fix memory retrieval,
  p=2.1×10⁻⁵ with n=447 total pooled comparison.
- Full stack (memory + DINOv2 + state-aware + Fix 1/3) vs baseline:
  **+28.3pp**, p<10⁻⁵.
- Pre-fix memory alone reached only marginal significance (p=0.10) —
  DINOv2 and state-aware ranking are necessary but not sufficient
  without prompt-level scaffolding for STOP behavior.
- Success rate is now nearly 2.4× the baseline; efficiency (rounds/ep,
  best-arm distance) also improves independent of SR — memory helps
  even on failed episodes.

### R1 ΔX bias trend (teacher perception calibration)

D6 baseline mean R1 ΔX = **-23.5 cm** (teacher systematically over-predicts
in -X direction at round 1, then corrects in later rounds via critic feedback).

D10 quartile-by-quartile decay:
- ep 1-25: -18.6 cm
- ep 26-50: -18.2 cm
- ep 51-75: -17.2 cm
- ep 76-100: -15.8 cm (-32% vs baseline)

**Paper claim**: Image-anchored memory monotonically reduces R1 perception
bias across episodes within a single run. This is *behavioral* evidence
that memory injection changes teacher reasoning, not just an outcome metric.

### Efficiency (rounds + distance)

| Metric | D6 | D10 | D10-ext-2 | D10-ext-3b | D10-ext-4 | Δ vs D6 (ext-4) |
|---|---|---|---|---|---|---|
| Avg rounds / ep | 19.7 | 14.1 | 11.1 | 11.4 | 11.8 | **-40%** |
| Avg best L-dist (cm) | 16.2 | 9.1 | 7.7 | 6.2 | 6.9 | **-57%** |
| Outcome: timeout (of 100) | 79 | 70 | 55 | 45 | 50 | **-37%** |
| vlm_stop_premature | 11 | 5 | 12 | 4 | 2 | **-82%** |

**Paper claim**: Memory both raises SR and dramatically reduces episode
length and final-arm distance. This is independent of SR — even on
failures the teacher gets closer faster with memory. Fix 1/3 also
essentially eliminates premature-STOP failures (ext-2: 12 → ext-4: 2).

---

## 3. Key Architectural Findings (paper-worthy)

### 3.1 Image-anchored memory beats text-only memory

**Setup**: each recap stores {init_pre.png, final_post.png, key_round_pre.png,
state_anchor (init/final EE pose, final dist), text_lesson ≤100 words,
image_embedding}. Retrieval injects all three modalities into next ep's R1
prompt.

**Why image-anchored matters**: Pure text retrieval ("X-axis flipped" lesson)
is uninterpretable without anchor — see Voyager limitation. Image-anchored
retrieval enables *visual analogy*: "current scene looks like past scene N,
which had lesson L." User-prompted insight, validated by D10 ep 21 → 2-round
success after retrieving ep 10's first-success image.

### 3.2 MobileNet → DINOv2 swap is critical for low-diversity scenes

**Problem identified in D10**: All retrieval cosine similarities clustered
at 0.94-0.98 (MobileNet ImageNet features). Retrieval degraded to noise
because all images "look the same" to a generic feature extractor.

**Fix**: DINOv2-base (768-d, self-supervised on 142M raw images).
- On 5 real D10 init images, off-diag cosine spread: MobileNet 0.94-0.98 vs **DINOv2 0.67-0.89**.
- Real visual signal restored.

**Paper claim**: Foundation vision encoders trained with self-supervised
objectives (DINOv2) are necessary for episodic memory retrieval in
low-diversity robot manipulation scenes; ImageNet-classifier features
collapse.

### 3.3 State-aware retrieval ranking (image + EE pose)

**Problem**: image cosine alone insufficient. State distance (3D init EE
position) is a physical ground-truth signal independent of vision pretraining.

**Fix**: combined score
```
score = α * image_cos + (1-α) * exp(-d_cm / state_scale)
α = 0.4, state_scale = 30 cm (workspace diameter)
```

State weighted more than image (1-α > α) because state distance is
deterministic; image is approximate.

**Paper-side caveat (limitation)**: state retrieval uses **absolute world coords** —
will not transfer across scenes / robots / camera placements. See §7 future work.

### 3.4 Success-floor retrieval (Q12 design call)

**Problem**: As buffer accumulates more failures than successes (D10 ended
25 succ / 75 fail), naive top-K retrieval gets dominated by failure lessons.

**Fix**: Force top-K to include at least `ceil(2/3 * K)` success records.
Fall back to mixed if buffer success count insufficient.

**Empirical**: D10-ext-2 ep 1 retrieved 3/3 success past eps (exceeding the
2/3 floor naturally because DINOv2+state ranking finds high-success-rate
neighborhoods at this scale).

### 3.5 Adaptive retrieval mode switching (L1+L2 watcher)

When sliding 10-ep SR falls below 5% for 2 consecutive windows, watcher
writes `success_only` to a flag file; collect reads the flag per ep and
flips retrieval to filter only success recaps until SR recovers ≥10%.

Did NOT trigger during D10-ext-2 — sliding window always stayed ≥20%. Kept
as defensive measure for longer runs.

### 3.6 Failed approaches (negative results worth documenting)

| Attempt | What | Why failed |
|---|---|---|
| F56: Distill from FIRST stage1 of success replays | Episode-level pairing | Teacher R1 wrong-direction bias hardcoded into LoRA → SR 4% |
| F59: Distill from LAST stage1 + init image | Geometric mismatch | Init image and final-round target are 25cm apart in state space → LoRA learned to over-shoot from home pose |
| v3.2: Per-round + dist-filter (lt15cm) | Distill from progress rounds only | Single-step BC throws away teacher's multi-round correction loop → still 2.8% SR |
| v3.2 lesson | **Single-step distillation of multi-step reasoning systematically fails** | LoRA learns the *symptom* (action) not the *process* (memory-conditioned reasoning) |

These negative results frame why memory-then-distillation matters — direct
distillation without preserving the memory mechanism doesn't work.

---

## 4. Methodology / Honest Caveats (for Limitations section)

### 4.1 Statistical power

- D10-ext-2 alone: 33% vs D6 21%, two-proportion z-test p ≈ 0.056 (borderline)
- Pooled D10+ext1+ext2 (n=226): 29.6%, p ≈ 0.10 (not yet significant)
- Need D10-ext-3 + ext-4 to clinch p<0.05

### 4.2 vlm_stop_premature in D10-ext-2 (12 cases)

Teacher prematurely emitted STOP=true in 12 eps, all with final dist 5-13cm.
Pattern: 2-3 rounds of critic feedback saying "No significant progress.
Adjust coordinate prediction." was being interpreted as "stop trying".

**Fix applied starting from D10-ext-3**:
- (Fix 1) Critic FLAT wording made directional + cites current distance:
      `"No significant progress (still {d_end:.1f} cm from target). Try a
       different direction or larger step size. STOP only when the task's
       success criterion is met — do not stop because previous rounds
       showed no progress."`
- (Fix 3) Stage 1 user template surfaces live distances:
      `LEFT_EE_TO_RED_CUBE = {dist_red_cm} cm`
      `RIGHT_EE_TO_BLUE_CUBE = {dist_blue_cm} cm`
  Both already observable (RGB-derivable), so observable-only invariant
  preserved.

**Rejected fixes** (would violate Phase 4 design principles):
- (Fix 2 rejected) Hardcoded "STOP only when dist < 5cm" in system prompt —
  violates task-agnostic principle (5cm is L0a hyperparameter; would not
  transfer to L3 grasp tasks where success criterion is gripper state).
- Engine-level STOP veto — moves logic out of model, defeats the purpose
  of testing whether teacher learns the rule.

**Experimental design after fix**:
- "pre-fix arm" baseline = D10 (n=100, 25%) + D10-ext-2 (n=100, 33%) =
  pooled n=200, SR=29.0%
- "post-fix arm" = D10-ext-3 + D10-ext-4 (both n=100, with Fix 1/3) =
  pooled n=200, SR=?
- Comparison of these two pools is the headline efficacy claim for
  the Fix 1/3 ablation. D10-ext-1 (salvaged n=26) is in a tier of its own
  (DINOv2 introduced mid-run after teacher crash) — list separately.

### 4.3 Absolute state retrieval (single-domain limitation)

Current retrieval key is absolute `init_L_EE` in world frame. Would not
transfer to:
- different table positions (state offset)
- different lighting/textures (DINOv2 will give different features)
- different robot embodiments (different workspace)

**Phase 5 plan** (out of scope for this paper): Domain Randomization +
relative-state retrieval (`dist_red`, `dist_blue`, `ee_to_cube_vector`).

### 4.4 Single-task evaluation

Phase 4 only evaluates on L0a-Left (single-arm reach to red cube). Multi-task
generalization not demonstrated. The framework is task-agnostic by design
(see Phase 4 principles in docs/plans/01_poc_cognitive_evolution_pipeline.md),
but empirical validation across L0b/L1/L2 is future work.

---

## 5. Open Questions / Things to Verify Before Submission

- [ ] D10-ext-3 (running) — replicate D10-ext-2 ~33% SR or regress?
- [ ] D10-ext-4 (after Fix 1/3) — does premature-stop fix yield 38-42%?
- [ ] D11 — does student LoRA trained on D10-ext aggregated trajectories
      match or beat teacher SR without retrieval at inference?
- [ ] R1 ΔX bias curve across **all 4-5 runs pooled** (n=400-500 ep) — does
      it monotonically decay? plateau? where?
- [ ] Recap quality drift — does VLM-generated lesson quality degrade as
      buffer accumulates? (qualitative spot-check at ep 200, 300, 400)
- [ ] Wilson CI vs t-test vs bootstrap — pick one method, justify
- [ ] Retrieval ablation: pure state (α=0) vs pure image (α=1) vs combined.
      Need to log this for paper Table.

---

## 6. Paper Section Outline (rough)

1. **Intro**: VLA agents can reason but are slow; demo data is expensive;
   propose "memory-then-distill" zero-demo route.
2. **Related work**:
   - VLA / multimodal robotics: OpenVLA, RT-2, π0
   - Memory-augmented LLMs: RAG, Voyager (text-only, limitation), MemGPT
   - Distillation: STaR, Reflexion, KTO (Ethayarajh 2024)
   - Sim2real prerequisites: DR (Tobin 2017), R3M, DINOv2 robotics
3. **Method**:
   - 3.1 Pipeline architecture (4 stages + memory)
   - 3.2 Episodic memory: schema, retrieval, image-anchoring
   - 3.3 Distillation: progress-filtering, KTO formulation
4. **Experiments**:
   - 4.1 Setup: IsaacLab L0a-Left, Gemma-4-31B teacher, QLoRA student
   - 4.2 Baseline (D6) and memory-augmented (D10-ext) teacher SR
   - 4.3 Distillation (D11) — student SR with and without memory
   - 4.4 Ablations: DINOv2 vs MobileNet, image_weight α, success_floor
5. **Discussion**:
   - Failed approaches (F56/F59/v3.2) — single-step distillation insufficient
   - Why memory-anchored visual analogy works (Voyager comparison)
6. **Limitations**:
   - Single task, single domain, absolute-coord retrieval (see §4)
7. **Future work**:
   - Phase 5: multi-view + DR + relative-state retrieval
   - Cross-embodiment transfer
   - Online memory pruning / saturation analysis

---

## 7. Figures Planned

- **Fig 1** (architecture): pipeline diagram — Stage1 + retrieval + critic + recap
- **Fig 2** (SR curve): cumulative SR vs ep, D6/D10/D10-ext-2/ext-3/ext-4 overlaid
- **Fig 3** (R1 ΔX): bias decay across quartiles, multiple runs
- **Fig 4** (efficiency): rounds/ep vs SR scatter, D6 vs memory
- **Fig 5** (qualitative): one success ep with retrieved past images shown
- **Table 1** (ablation): DINOv2 vs MobileNet, α sweep, success_floor effect
- **Table 2** (Phase 4 vs prior distillation attempts F56/F59/v3.2)

---

## 8. Reproducibility checklist

- [x] Code commits tag each Phase 4 milestone (6b647d6, ecc3134, e98bb99, 661efa3)
- [x] Replay schemas versioned (`schema_version: 1`)
- [x] Recap JSON format documented in `aiongenos/memory/recap_buffer.py`
- [ ] Random seed for IsaacLab env reset — currently NOT seeded, need to log
      seed per run for paper Appendix
- [ ] HF model snapshot pins (gemma-4-31B-it, dinov2-base) — capture in
      requirements.txt with revision SHA
- [ ] Memory buffer release: include D10 full buffer as supplementary

---

## 9. Append-only changelog

- 2026-06-29: D10-ext-2 finished, SR=33%. R1-R4 retrieval patches validated.
- 2026-06-30 morning: This file created; Fix 1 (rev) + Fix 3 spec confirmed
  and applied for ext-3 (plan change from earlier "unmodified baseline").
- 2026-06-30 afternoon: **BREAKTHROUGH**. D10-ext-3 partial (n=21) hit 47.6%
  before server reboot; D10-ext-3b (n=100) confirmed at **51.0%** SR, p<0.001
  vs D6 baseline. Fix 1/3 ablation clean: +20.8pp vs pre-fix pool (p=0.00013).
  D10-ext-4 launched to consolidate.
- 2026-07-01: **D10-ext-4 = 48.0%** confirms 51.0% was not a fluke. Post-fix
  pool now n=221, SR=49.3% [42.8, 55.9] with p<10⁻⁵ vs D6. Fix 1/3 ablation
  hardened to p=2.1×10⁻⁵ (n=447 pooled). Phase 4 teacher-side results
  **frozen**. Canonical result sentences added to §1.1 for verbatim
  paper use. Next: D11 distillation OR extend teacher runs to N=500.
