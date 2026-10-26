"""ρ_X / ρ_Y between round-1 target and cube position, split by first success.
Usage: python3 wp3a_rho_segments.py <run_id> [--perm 10000] [--seed 20261026]
Segments: all episodes; before the first success (seed order, exclusive); from the first success on (inclusive).
One-sided permutation test (H1: ρ > 0): p = (1 + #{ρ_perm ≥ ρ_obs}) / (1 + N); band95 = 95th percentile of ρ_perm."""
import argparse, glob, json, random, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def rho(a, b):
    ma, mb = st.mean(a), st.mean(b)
    sa = sum((x - ma) ** 2 for x in a) ** .5
    sb = sum((y - mb) ** 2 for y in b) ** .5
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else float("nan")


def perm_test(t, c, n, rng):
    obs = rho(t, c)
    if obs != obs:
        return obs, float("nan"), float("nan")
    cc = list(c); null = []
    for _ in range(n):
        rng.shuffle(cc); null.append(rho(t, cc))
    null.sort()
    p = (1 + sum(v >= obs for v in null)) / (1 + n)
    return obs, p, null[int(0.95 * n) - 1]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("--perm", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20261026); a = ap.parse_args()
    eps = sorted((json.load(open(f)) for f in glob.glob(str(ROOT / f"data/collect_dumps/{a.run}/*/meta.json"))),
                 key=lambda e: e["env_seed"])
    first = next((i for i, e in enumerate(eps) if e["outcome"] == "success"), None)
    segs = {"all": eps, "before_first_success": eps[:first] if first is not None else eps,
            "from_first_success": eps[first:] if first is not None else []}
    print(f"run={a.run} episodes={len(eps)} first_success_seed={eps[first]['env_seed'] if first is not None else None} perm={a.perm} seed={a.seed}")
    for name, s in segs.items():
        if len(s) < 3:
            print(f"[{name}] n={len(s)} (too few)"); continue
        t1 = [e["rounds"][0]["eef_target_int"] for e in s]; c1 = [e["rounds"][0]["cube_b_pre"] for e in s]
        out = []
        for ax, k in (("X", 0), ("Y", 1)):
            r, p, band = perm_test([t[k] for t in t1], [c[k] for c in c1], a.perm, random.Random(a.seed))
            out.append(f"rho_{ax}={r:+.3f} p_one_sided={p:.4f} band95={band:+.3f}")
        uniq = len({tuple(t) for t in t1})
        print(f"[{name}] n={len(s)} seeds {s[0]['env_seed']}-{s[-1]['env_seed']} | " + " | ".join(out) + f" | unique_R1_targets={uniq}")


if __name__ == "__main__":
    main()
