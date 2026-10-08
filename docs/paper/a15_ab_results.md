# D11 Amendment 15 — protocols (a) and (b), paired results (all 4 arms, COMPLETE)

**Filed** 2026-10-06 by isaac (2 arms); **completed 2026-10-08** (B_main, D_gist).
Every number in this file comes from `python3 scripts/analysis/a15_ab_stats.py`
(→ `docs/paper/data/a15_ab_stats.json`) and from
`A15C_GATE_TOL_M=0.015 python3 scripts/analysis/a15_slope_probe.py`
(→ `docs/paper/data/a15_slope_probe_gate15mm.json`).
- Lock: `989a753`. Operational pins and A15.1: see `docs/d11_preregistration.md`.
- Runs, from `logs/a15_manifest.jsonl`. Every arm passed the frozen-buffer
  readonly gate: tree hash `7d4f3f9e…` before and after.

| Protocol | Adapter | Template variant | Run | Finished |
|---|---|---|---|---|
| (a) | none (base) | rationale_with_retrieval | `995f496c` | 10-05 |
| (b) | A_action_only | action_only | `9be74fc2` | 10-06 |
| (b) | B_main | rationale_with_gist | `13c5c402` | 10-07 01:46 |
| (b) | D_gist | gist_only | `fdb2a9b0` | 10-08 01:06 |

- D_gist operations note: the 10-07 night start failed at the adapter reload
  (ssh). After the PI rebooted the host, both servers were restarted with the
  repo scripts, without config changes. GPU placement matched 10-05.
  - The A_ctrl_rat adapter SHAs re-verified identical.
  - D_gist adapter SHAs were recorded before the run:
    - SFT `dba178f3…ff85`
    - KTO `d5ebc32f…dfd6`
  - Full values: `docs/p2_prereg/wp3a_push_provenance.md`, 10-07 afternoon.
  - The arm started at 13:37 with `--ignore-window`, outside the night window.
    This changes the start time only. Flags, buffer and seeds are identical.

## Analysis rules (locked, plus disclosed operationalisations)
- **Pairing.** Seeds are 4500+k. 0/100 seed mismatches in every contrast.
  - The A14 §14.1 fingerprint gate (eps 1e-4 on trajectory[0]) **fails** in
    every contrast: 70–100 mismatches. This is the same instrument
    behaviour as D11: trajectory[0] is logged after the first execute step,
    which depends on the arm's first action.
  - Consequence, by the A14 §14.2 rule, applied mechanically: **two-proportion
    z is primary**. McNemar is reported as a sensitivity check.
- **α.** A15 fixes no α. I use the D11 §4 default, **α = 0.05 two-sided**
  (disclosed choice). No multiplicity correction is applied. Every (b) rise
  has p ≤ 1e-4, so the verdicts survive Bonferroni over the 3 arms.
- **"Within the paired MDE".** The lock gives no number. Disclosed
  operationalisation: MDE = 19.8 pp (two-sided α .05, power .8, n = 100, at
  the C_retrieval rate).
- **Sensitivity SR.** Pin 8 (24 s auto-reset) is applied to every contrast.

## Table

| Contrast | SR | Δ | z (primary) | p_z | McNemar b/c, p | Pin-8 sensitivity |
|---|---|---|---|---|---|---|
| (a) base+buffer vs C_retrieval | 48 vs 49 | −1 pp | −0.14 | 0.887 | 11/12, p=1.0 | 48 vs 48, Δ 0, p=1.0 |
| (b) action_only+buffer vs C_retrieval | 53 vs 49 | +4 pp | +0.57 | 0.572 | 19/15, p=0.607 | 53 vs 48, Δ +5, p=0.479 |
| (b) B_main+buffer vs C_retrieval | 53 vs 49 | +4 pp | +0.57 | 0.572 | 17/13, p=0.584 | 50 vs 48, Δ +2, p=0.777 |
| (b) D_gist+buffer vs C_retrieval | 55 vs 49 | +6 pp | +0.85 | 0.396 | 20/14, p=0.391 | 55 vs 48, Δ +7, p=0.322 |
| (b) action_only+buffer vs own D11 (A_action_only, no retrieval) | 53 vs 25 | **+28 pp** | +4.06 | 4.9e-5 | 38/10, p=9.7e-5 | 53 vs 21, Δ +32, p=2.8e-6 |
| (b) B_main+buffer vs own D11 (B_main) | 53 vs 26 | **+27 pp** | +3.90 | 9.4e-5 | 36/9, p=1.1e-4 | 50 vs 19, Δ +31, p=4.0e-6 |
| (b) D_gist+buffer vs own D11 (D_gist) | 55 vs 19 | **+36 pp** | +5.27 | 1.4e-7 | 39/3, p=6.6e-8 | 55 vs 17, Δ +38, p=2.2e-8 |

## Against the lock

**(a) Prediction:** "SR < `C_retrieval` (49/100). The gap = what the adapter
contributes …"
**Result: MISS.** 48 vs 49, Δ −1 pp, p = 0.887. There is no gap.
**Fallback triggered.** Lock text, verbatim: "if SR ≈ `C_retrieval` (within
the paired MDE), then **"distil the competence" is downgraded** — the adapter
is not necessary and retrieval is independently sufficient. We rewrite the
recipe accordingly and report it plainly; no spin."
Pre-committed route: "(a) no gap → recipe rewrite (adapter non-essential)."

**(b) Prediction:** "all three rise into the teacher band (≈45–55% SR),
showing the retrieval effect is not specific to `A_ctrl_rat`'s weights."
**Result: HIT, all three arms.**

| Arm | Without retrieval | With retrieval | Δ | p |
|---|---|---|---|---|
| A_action_only | 25 | 53 | +28 | 4.9e-5 |
| B_main | 26 | 53 | +27 | 9.4e-5 |
| D_gist | 19 | 55 | +36 | 1.4e-7 |

- All three land at 53–55, inside 45–55. D_gist sits at the upper edge.
- None differs from C_retrieval (|Δ| ≤ 6 pp, all p ≥ 0.39), and none differs
  from the base model with the buffer (48).
- The locked fallback ("adapter-dependent") is **not** triggered.
- Pre-committed route: **"(b) all rise → +34 pp generalised beyond
  `A_ctrl_rat`."**

## R1' slope for the new arms
These readings have pre-registered status under A15.1: the 15 mm gate, with
slope > 0 iff r is above the band.
- The lock states no directional prediction for these arms. This is a
  reading, not a hit/miss.
- All four arms had 100/100 episodes pass the gate.

| Arm | Spearman r | Permutation band | Above band |
|---|---|---|---|
| (a) base+buffer | +0.291 | [−0.209, +0.187] | yes |
| (b) action_only+buffer | +0.487 | [−0.203, +0.186] | yes |
| (b) B_main+buffer | +0.359 | [−0.202, +0.185] | yes |
| (b) D_gist+buffer | +0.442 | [−0.199, +0.194] | yes |

For context only, labelled post-hoc per A15.1:
- C_retrieval r = +0.306 (above its band).
- The same four adapters *without* retrieval have r from −0.16 to −0.30
  (action_only −0.298, A_ctrl_rat −0.245, B_main −0.156, D_gist −0.207).
  All are at or below their bands.
- In every arm, attaching the buffer flips the round-1 slope from ≤ 0 to
  above the band.

## Routing for the paper session (both routes now selected)
1. **(a) MISS → recipe rewrite: the adapter is non-essential.** Retrieval
   alone is sufficient on the base model (48 vs 49).
2. **(b) HIT → +34 pp generalises beyond `A_ctrl_rat`.** All five weight
   configurations land at 48–55 with the buffer. The no-retrieval runs are
   at 19–26 (A_ctrl_rat 15 in D11).
   - Five configurations: base, A_ctrl_rat (= C_retrieval), A_action_only,
     B_main, D_gist.
   - Read together with (a): with the frozen buffer, SR does not depend on
     which adapter, or no adapter, is loaded.
- This supports the title amendment lock: "Externalise the Memory", with the
  competence not distilled into the weights.
- Not tested here: whether the effect comes from the lesson text or from the
  attached `init_pre` images. They are confounded by design (proposed A17).

---

# L2 auto-reset check (pin-8 rule applied to L2), 2026-10-06

**Command:** `python3 scripts/analysis/l2_autoreset_sensitivity.py`. Results are
in `docs/paper/data/l2_autoreset_sensitivity.json`.

**The limit exists in L2.** `L2DualPushEnvCfg` inherits from the IsaacLab
openarm ReachEnvCfg, which sets `episode_length_s = 24` (720 env steps). No
AionGenos class overrides it. L2 eval allows up to 40 rounds × 30 steps = 1200
steps.
- **Boundary:** index 718 in every episode. It is derived from the step counter,
  and every crossing is confirmed by the frozen-arm jump (0 ambiguous).
- **Trajectory length** (q1 / median / q3 / max):
  - A_ctrl_rat: 300 / 420 / 570 / 1200
  - C_retrieval: 300 / 390 / 510 / 1200

| Arm (run) | As-run SR | Episodes crossing | Successes after boundary | Sensitivity SR |
|---|---|---|---|---|
| A_ctrl_rat (`8384a740`) | 14/100 | 10 | 0 | 14/100 |
| C_retrieval (`2154e57e`) | 20/100 | 9 | 0 | 20/100 |

**Contrast:**

| | Δ | Newcombe 95% CI | z | p | McNemar 9/3 | Verdict |
|---|---|---|---|---|---|---|
| C_retrieval − A_ctrl_rat, as-run | +6.0 pp | [−4.5, +16.4] | +1.13 | 0.259 | p = 0.146 | n.s. at α = 0.010 |
| C_retrieval − A_ctrl_rat, sensitivity | +6.0 pp | [−4.5, +16.4] | +1.13 | 0.259 | p = 0.146 | n.s. at α = 0.010 |

The two rows are identical because no L2 success happened after the reset. The
**verdict is unchanged**: below the +20 pp MDE, n.s., DIAGNOSE branch. For the
paper: the L2 methods should state the 24 s time-out and that 9–10 episodes per
arm crossed it, with no success after the crossing.
