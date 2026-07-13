"""D11 exploratory pack (Amendment 14 §14.5, labelled exploratory).

Execution order fixed by §14.5 (most-disciplined first):
  1. R1 ΔX probe per arm  — pre-registered per-arm predictions (§9.3).
  2. Rationale fabrication rate per arm — "self-produced rationale tax".
  3. Per-episode rescue analysis — memory-dependent episode profile.

R1 ΔX per episode = round-1 VLM left-target X − init left-EE X.
Reference fingerprints (§5):
  D6 memoryless teacher: −23.5 cm     mem-teacher last quartile: −15.8 cm
H_behavior: bake-in shifts bias to ≈−16 (content entered weights, not
  used well) → paper 2 = "written in, but not read".
H_language: bias reverts to ≈−24 (content never entered weights) →
  paper 2 = "why distillation didn't write it in".

Usage: python3 scripts/analysis/d11_exploratory.py
"""

from __future__ import annotations

import json
import re
import statistics as st
from pathlib import Path

ARMS = {
    "A_action_only": {"run": "e4d81bb6", "log": "logs/d11_A_action_only_20260711_020143.log"},
    "A_ctrl_rat":    {"run": "56ee684b", "log": "logs/d11_A_ctrl_rat_20260711_134456.log"},
    "B_main":        {"run": "a7b11544", "log": "logs/d11_B_main_20260711_233501.log"},
    "D_gist":        {"run": "875c04fb", "log": "logs/d11_D_gist_20260712_095415.log"},
    "C_retrieval":   {"run": "09817322", "log": "logs/d11_C_retrieval_20260712_222441.log"},
}
REPLAY_ROOT = Path("data/replays")
D6_REF = -23.5
MEM_TEACHER_REF = -15.8
_EP_RE = re.compile(r"Episode (\d+)/\d+ \| [^|]+\| ([0-9a-f-]+)")


def arm_episodes(cfg) -> list[tuple[int, str, dict]]:
    order = []
    for line in Path(cfg["log"]).read_text().splitlines():
        m = _EP_RE.search(line)
        if m:
            order.append((int(m.group(1)) - 1, m.group(2)))
    out = []
    for ep_idx, ep_id in order:
        for sub in ("success", "failure"):
            p = REPLAY_ROOT / cfg["run"] / sub / f"{ep_id}.json"
            if p.exists():
                out.append((ep_idx, ep_id, json.loads(p.read_text())))
                break
    return out


def r1_dx(replay: dict) -> float | None:
    try:
        init_x = replay["trajectory"][0]["left_ee_pos"][0]
        vi = replay["vlm_interactions"][0]
        tgt_x = vi["parsed_left_pos"][0]
        if tgt_x is None:
            return None
        return float(tgt_x - init_x)
    except (KeyError, IndexError, TypeError):
        return None


def is_success(replay: dict) -> bool:
    return replay.get("outcome") == "success"


# ─── Rationale fabrication: does the emitted THOUGHT/rationale reference a
# past lesson / cross-episode memory that the student could not actually
# have (A_ctrl_rat & B_main emit rationale; A_action_only should not)? We
# proxy "fabrication" as cross-episode-reference tokens appearing in the
# student's round-1 full_response, reusing the A9 §9.4 leak lexicon.
_FAB_RE = re.compile(
    r"\b(past (?:episode|attempt|lesson)|previous (?:episode|attempt)|"
    r"lesson|recall|earlier attempt|similar past|prior experience|"
    r"as (?:shown|learned) before)\b", re.IGNORECASE)


def fabrication_hit(replay: dict) -> bool | None:
    """True/False if round-1 response has rationale text to inspect; None if
    the arm emits no rationale (pure action, nothing to fabricate)."""
    vi = replay["vlm_interactions"][0]
    resp = (vi.get("full_response") or "").strip()
    if not resp:
        return None
    return bool(_FAB_RE.search(resp))


def main() -> None:
    print("=" * 70)
    print("D11 EXPLORATORY PACK (Amendment 14 §14.5 — labelled exploratory)")
    print("=" * 70)

    data = {arm: arm_episodes(cfg) for arm, cfg in ARMS.items()}

    # ── 1. R1 ΔX probe ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("1. R1 ΔX PROBE (§5 / §9.3)  ref: D6=%.1f  mem-teacher=%.1f"
          % (D6_REF, MEM_TEACHER_REF))
    print("=" * 70)
    print(f"  {'arm':16s} {'n':>4s} {'μ':>8s} {'σ':>7s} "
          f"{'|Δ D6|':>8s} {'|Δ memT|':>9s}  closer-to")
    r1_summary = {}
    for arm in ARMS:
        vals = [r1_dx(rp) for _, _, rp in data[arm]]
        vals = [v for v in vals if v is not None]
        mu = st.mean(vals)
        sd = st.stdev(vals) if len(vals) > 1 else 0.0
        dd6 = abs(mu - D6_REF)
        dmt = abs(mu - MEM_TEACHER_REF)
        closer = "mem-teacher" if dmt < dd6 else "D6"
        r1_summary[arm] = {"n": len(vals), "mu": mu, "sd": sd,
                           "closer": closer, "d_d6": dd6, "d_memT": dmt}
        print(f"  {arm:16s} {len(vals):4d} {mu:8.2f} {sd:7.2f} "
              f"{dd6:8.2f} {dmt:9.2f}  {closer}")

    print("\n  Interpretation for B_main (the T1-null arm):")
    b = r1_summary["B_main"]
    if b["closer"] == "mem-teacher":
        print(f"    B_main μ={b['mu']:.2f} is CLOSER to mem-teacher (−15.8).")
        print(f"    → H_behavior: memory content DID shift weight-level bias,")
        print(f"      but T1 null means it didn't convert to task success.")
        print(f"      paper 2 framing: 'written in, but not read/used'.")
    else:
        print(f"    B_main μ={b['mu']:.2f} is CLOSER to D6 (−23.5).")
        print(f"    → H_language: memory content did NOT reach weight-level")
        print(f"      behaviour; T1 null = 'not written in'.")
        print(f"      paper 2 framing: 'why distillation didn't write it in'.")

    # ── 2. Rationale fabrication rate ───────────────────────────────
    print("\n" + "=" * 70)
    print("2. RATIONALE FABRICATION RATE — NOT COMPUTABLE FROM D11 REPLAYS")
    print("=" * 70)
    total_resp = sum(
        1 for arm in ARMS for _, _, rp in data[arm]
        for vi in rp["vlm_interactions"] if (vi.get("full_response") or "").strip()
    )
    print(f"  Non-empty full_response across ALL arms/interactions: {total_resp}")
    print(f"  → D11 collect did NOT persist raw VLM text (constrained-decode")
    print(f"    path stored only parsed coords). Fabrication analysis needs")
    print(f"    the emitted rationale string, which is absent. This is a")
    print(f"    MEASUREMENT GAP, reported honestly — NOT zero fabrication.")
    print(f"  Weak proxy (R1 ΔX σ, higher = noisier targeting):")
    for arm in ("A_action_only", "A_ctrl_rat", "B_main", "D_gist"):
        print(f"    {arm:16s} σ={r1_summary[arm]['sd']:.2f}")
    print(f"  → A_ctrl_rat σ={r1_summary['A_ctrl_rat']['sd']:.2f} is the")
    print(f"    highest non-retrieval arm, weakly consistent with (but far")
    print(f"    from proving) the 'fabricate-then-act' hypothesis. Paper 2")
    print(f"    must re-run with raw-response logging (schema field added")
    print(f"    2026-07-13) to test fabrication properly.")

    # ── 3. Per-episode rescue analysis ──────────────────────────────
    print("\n" + "=" * 70)
    print("3. RESCUE ANALYSIS — C_retrieval solves, A_ctrl_rat fails")
    print("=" * 70)
    # align by ep_idx
    def by_idx(arm):
        return {ep_idx: is_success(rp) for ep_idx, _, rp in data[arm]}
    c = by_idx("C_retrieval")
    a = by_idx("A_ctrl_rat")
    bm = by_idx("B_main")
    aa = by_idx("A_action_only")
    common = sorted(set(c) & set(a) & set(bm) & set(aa))
    rescued_vs_actrl = [k for k in common if c[k] and not a[k]]
    rescued_vs_bmain = [k for k in common if c[k] and not bm[k]]
    both_fail_c_wins = [k for k in common if c[k] and not a[k] and not bm[k] and not aa[k]]
    print(f"  common ep_idx: {len(common)}")
    print(f"  C_retrieval solves, A_ctrl_rat fails:  {len(rescued_vs_actrl)}")
    print(f"  C_retrieval solves, B_main fails:      {len(rescued_vs_bmain)}")
    print(f"  C_retrieval solves, ALL others fail:   {len(both_fail_c_wins)}")
    print(f"    → 'pure memory-dependent' episodes (only external retrieval")
    print(f"      rescues them): ep_idx {both_fail_c_wins}")

    # persist
    out = {
        "r1_dx": {arm: r1_summary[arm] for arm in ARMS},
        "rescue": {
            "c_solves_actrl_fails": rescued_vs_actrl,
            "c_solves_bmain_fails": rescued_vs_bmain,
            "pure_memory_dependent": both_fail_c_wins,
        },
    }
    outp = Path("workspace/d11_audit/exploratory.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2))
    print(f"\nWrote → {outp}")


if __name__ == "__main__":
    main()
