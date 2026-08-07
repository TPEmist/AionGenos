"""P2 [PWR-SIM] step 1 — the r-tracker (per-generation residual-correlation).

Upgrades the D11 residual-correlation diagnostic into P2's confirmatory
spine: r_g = the degree to which the BARE-WEIGHTS student's per-episode
round-1 correction is CONDITIONAL on the situation (init configuration),
tracked across expert-iteration generations. H-main predicts r_g climbs
monotonically OUT of the chance band as the conditional structure
consolidates into weights.

This module locks the ESTIMATOR + chance-band + monotonicity test (P2 §8
step 1) — the parts that need no contact-task data. It is deliberately
pure-function + stdlib so it runs anywhere and is unit-testable on
synthetic data before any real gen-0 collect exists.

Definitions (locked here, pre-data):
- correction c_i  : per-episode round-1 signed displacement (e.g. ΔX_L),
  the same quantity d11_exploratory.r1_dx measures, per bare-weights student.
- situation  s_i  : a scalar situation feature (e.g. init dist-to-target, or
  a projection of the init-config vector). Multivariate handled by taking
  the max |partial corr| or a fixed linear projection pinned per task.
- r_g = Spearman(c, s) over the generation's n episodes. Spearman (rank)
  not Pearson: robust to the nonlinear, bounded correction range.
- chance band = the null distribution of r under H0 "correction is
  situation-independent", obtained by permuting s against c (n_perm shuffles)
  → 2.5/97.5 percentile CI_g. r_g ABOVE the band's upper edge = the weights'
  correction is significantly situation-conditional at gen g.
- monotonic climb test across G gens = Spearman(gen_index, r_g) with its own
  permutation p (does r rise with generation?). This is the confirmatory
  trend; α locked before gen 0.
"""
from __future__ import annotations

import math
from typing import Sequence


def _rank(xs: Sequence[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j < len(xs) and xs[order[j]] == xs[order[i]]:
            j += 1
        avg = (i + 1 + j) / 2.0  # 1-based average rank for ties
        for k in range(i, j):
            ranks[order[k]] = avg
        i = j
    return ranks


def _pearson(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def spearman(c: Sequence[float], s: Sequence[float]) -> float:
    """Rank correlation between correction c and situation s."""
    return _pearson(_rank(c), _rank(s))


def _seeded_shuffle(xs: list[float], seed: int) -> list[float]:
    """Deterministic LCG shuffle (no Math.random dependency; reproducible)."""
    a = xs[:]
    state = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    for i in range(len(a) - 1, 0, -1):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        j = state % (i + 1)
        a[i], a[j] = a[j], a[i]
    return a


def chance_band(c: Sequence[float], s: Sequence[float], n_perm: int = 2000,
                lo_pct: float = 2.5, hi_pct: float = 97.5, seed0: int = 1):
    """Null distribution of r under H0 (situation-independent correction):
    permute s vs c, recompute Spearman. Returns (lo, hi) percentile band."""
    s_list = list(s)
    null = []
    for k in range(n_perm):
        null.append(spearman(c, _seeded_shuffle(s_list, seed0 + k)))
    null.sort()
    def pct(p):
        idx = min(len(null) - 1, max(0, int(round(p / 100.0 * (len(null) - 1)))))
        return null[idx]
    return pct(lo_pct), pct(hi_pct)


def r_for_generation(c: Sequence[float], s: Sequence[float], n_perm: int = 2000):
    """r_g + chance band + 'above band' flag for one generation."""
    r = spearman(c, s)
    lo, hi = chance_band(c, s, n_perm=n_perm)
    return {"r": r, "band_lo": lo, "band_hi": hi, "above_band": r > hi, "n": len(c)}


def monotonic_climb(r_by_gen: Sequence[float], n_perm: int = 5000, seed0: int = 7):
    """Confirmatory trend: does r rise with generation index? Spearman(gen, r)
    with a permutation p-value. Returns (rho, p_one_sided_increase)."""
    gens = list(range(len(r_by_gen)))
    rho = spearman(gens, r_by_gen)
    r_list = list(r_by_gen)
    ge = 0
    for k in range(n_perm):
        if spearman(gens, _seeded_shuffle(r_list, seed0 + k)) >= rho:
            ge += 1
    return rho, (ge + 1) / (n_perm + 1)


if __name__ == "__main__":
    # Self-test on synthetic data: a conditional signal should clear the band;
    # pure noise should sit inside it; a rising-across-gen r should trend up.
    import sys
    # gen with real situation-dependence
    N = 100
    s = [((i * 37) % N) / N for i in range(N)]
    c_cond = [0.8 * s[i] + 0.1 * (((i * 13) % 7) / 7 - 0.5) for i in range(N)]
    c_noise = [(((i * 29) % 11) / 11 - 0.5) for i in range(N)]
    rc = r_for_generation(c_cond, s, n_perm=500)
    rn = r_for_generation(c_noise, s, n_perm=500)
    print(f"[r-tracker self-test] conditional: r={rc['r']:.3f} band=({rc['band_lo']:.3f},{rc['band_hi']:.3f}) above={rc['above_band']}")
    print(f"[r-tracker self-test] noise:       r={rn['r']:.3f} band=({rn['band_lo']:.3f},{rn['band_hi']:.3f}) above={rn['above_band']}")
    # NOTE (locked finding): the permutation monotonicity test cannot reach
    # α=0.05 with G<5 — even a PERFECT climb gives min p=0.084 at G=4 (only
    # 1 of 4! orderings, and the test counts ">=rho" inclusive). So G>=5 is a
    # hard floor for the confirmatory trend; the self-test uses G=5.
    rho, p = monotonic_climb([0.05, 0.18, 0.32, 0.48, 0.61])  # G=5
    print(f"[r-tracker self-test] climb (G=5) rho={rho:.3f} p={p:.4f}")
    ok = rc["above_band"] and (not rn["above_band"]) and p < 0.05
    print(f"[r-tracker self-test] VERDICT {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
