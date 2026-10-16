"""Birth certificate for DERIVED paper numbers (v1.1_notes RULE 2026-10-05).

Every number printed here is recomputed from a persisted source (audit
report, collect log, replay JSON, or config) — no operand is typed in by
hand. Prose that cites one of these numbers points at the output file
`derived_stats.txt` next to this script.

    python3 docs/paper/birth_certificates/derived_stats.py \
        --data-root <AionGenos data root> > docs/paper/birth_certificates/derived_stats.txt
"""
import argparse
import ast
import glob
import json
import math
import os
import re
from statistics import NormalDist

N = NormalDist()

ROUNDS_TXT = "r1_rounds_recompute.txt"   # sibling certificate (paper worktree)
SENS_JSON = "workspace/a15_p1/autoreset_sensitivity.json"  # isaac A15 P1 (pin 8), master 781fa96
L2_SENS_JSON = "docs/paper/data/l2_autoreset_sensitivity.json"  # isaac L2 auto-reset check, master 99dc108
A15_JSON = "docs/paper/data/a15_ab_stats.json"  # isaac A15 (a)/(b) paired stats, 4 arms, master e25011e
A15_SLOPE_JSON = "docs/paper/data/a15_slope_probe_gate15mm.json"  # isaac A15.1 15 mm gate, master e25011e
A15_ARM = {"a_base_ret": None, "b_action_only_ret": "A_action_only", "b_B_main_ret": "B_main", "b_D_gist_ret": "D_gist"}
COST_LOG = "logs/cost_remeasure_20261005_181930.md"   # A15 same-hardware cost re-measure
D11_CONF = "workspace/d11_audit/d11_confirmatory_report.txt"
L2_CONF = "workspace/l2_audit/l2_confirmatory_output.txt"
CONFIG = "aiongenos/config.py"
# D10 post-fix memory-teacher pool (paper_notes §9 changelog 2026-06-30/07-01):
# ext-3 is truncated at the teacher-server outage; ext-3b and ext-4 are whole.
TEACHER_POOL_LOGS = [
    ("logs/d10ext3_l0a_left_teacher_mem_20260630_111227.log", True),
    ("logs/d10ext3b_l0a_left_teacher_mem_20260630_125331.log", False),
    ("logs/d10ext4_l0a_left_teacher_mem_20260630_183612.log", False),
]
OUTAGE_MARK = "All connection attempts failed"
# D6b: memoryless teacher + the same Fix 1/3 scaffolding (clean relaunch).
D6B_LOG = "logs/d6b_l0a_left_no_memory_fix_20260702_125800.log"
# The three episodes shown in Fig. qual_end (scripts/figures/make_qualitative_figs.py GIF_ARMS).
SHOWN_EPISODES = [("56ee684b", "e6f690d6-775"), ("a7b11544", "16e50879-8d4"),
                  ("09817322", "e1837c00-399")]


# ── statistics ──────────────────────────────────────────────────────────
def two_prop_z(k1, n1, k2, n2):
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (k1 / n1 - k2 / n2) / se
    return z, 2 * (1 - N.cdf(abs(z)))


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def newcombe(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
            d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def mcnemar_exact(b, c):
    n, k = b + c, min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def mcnemar_rule(b, c):
    """The registered rule (scripts/analysis/d11_mcnemar.py mcnemar()): exact
    two-sided binomial if b+c < 25, else continuity-corrected chi2, 1 dof."""
    if b + c < 25:
        return mcnemar_exact(b, c)
    return math.erfc(math.sqrt((abs(b - c) - 1) ** 2 / (b + c) / 2.0))


def mde_and_power(p0, n, alpha, delta):
    """Critical difference at two-sided alpha, and power for a true +delta."""
    za = N.inv_cdf(1 - alpha / 2)
    se0 = math.sqrt(2 * p0 * (1 - p0) / n)
    p1 = p0 + delta
    se1 = math.sqrt((p0 * (1 - p0) + p1 * (1 - p1)) / n)
    return za * se0, 1 - N.cdf((za * se0 - delta) / se1)


# ── parsers ─────────────────────────────────────────────────────────────
def d11_counts(root):
    txt = open(os.path.join(root, D11_CONF)).read()
    return {a: (int(k), int(n)) for a, n, k in
            re.findall(r"^\s+(\w+)\s+run=\w+\s+episodes=(\d+)\s+successes=(\d+)", txt, re.M)}


def l2_discordant(root):
    txt = open(os.path.join(root, L2_CONF)).read()
    m = re.search(r"C_retrieval-only=(\d+)\s+A_ctrl_rat-only=(\d+)", txt)
    return int(m.group(1)), int(m.group(2))


def x_bounds(root):
    src = open(os.path.join(root, CONFIG)).read()
    return ast.literal_eval(re.search(r"x_bounds: Tuple\[float, float\] = (\([^)]*\))", src).group(1))


def run_id(log_text):
    return re.findall(r"run_id='(\w+)'", log_text)[-1]


def pooled_teacher(root):
    rows, K, M = [], 0, 0
    for rel, truncate in TEACHER_POOL_LOGS:
        lines = open(os.path.join(root, rel)).read().splitlines()
        rid = run_id("\n".join(lines))
        outcome = {}
        for f in glob.glob(os.path.join(root, "data/replays", rid, "*", "*.json")):
            r = json.load(open(f))
            outcome[r["episode_id"]] = r["outcome"]
        started = []
        for ln in lines:
            if truncate and OUTAGE_MARK in ln:
                break
            m = re.search(r"Episode (\d+)/\d+ \| [^|]+\| (\S+)", ln)
            if m:
                started.append(m.group(2))
        if truncate:
            started = started[:-1]  # episode in flight at the outage is excluded
        ids = [next(e for e in outcome if e.startswith(p)) for p in started]
        k = sum(outcome[i] == "success" for i in ids)
        rows.append((rel, rid, k, len(ids)))
        K, M = K + k, M + len(ids)
    return rows, K, M


# ── report ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=os.environ.get("AIONGENOS_DATA_ROOT"),
                    required="AIONGENOS_DATA_ROOT" not in os.environ,
                    help="AionGenos data root (or set $AIONGENOS_DATA_ROOT)")
    root = ap.parse_args().data_root
    c = d11_counts(root)
    pct = lambda lo_hi: f"[{100 * lo_hi[0]:+.1f}, {100 * lo_hi[1]:+.1f}] pp"

    print("# derived_stats.txt — generated by derived_stats.py; do not hand-edit")
    print(f"# sources: {D11_CONF}, {L2_CONF}, {CONFIG}, D10 collect logs + replays\n")

    print("[D11 counts]", {a: f"{k}/{n}" for a, (k, n) in c.items()})
    for name, a, b in [("identical-weights C_retrieval - A_ctrl_rat", "C_retrieval", "A_ctrl_rat"),
                       ("T1 B_main - A_action_only", "B_main", "A_action_only"),
                       ("T1a B_main - A_ctrl_rat", "B_main", "A_ctrl_rat"),
                       ("T4 C_retrieval - B_main", "C_retrieval", "B_main")]:
        z, p = two_prop_z(*c[a], *c[b])
        d = 100 * (c[a][0] / c[a][1] - c[b][0] / c[b][1])
        print(f"[{name}] delta={d:+.1f} pp  z={z:.3f}  p={p:.3g}  Newcombe95={pct(newcombe(*c[a], *c[b]))}")

    k, n = c["A_action_only"]
    mde, pw = mde_and_power(k / n, n, 0.020, 0.10)
    print(f"[T1 MDE] critical diff at alpha=0.020 two-sided, p0={k/n:.2f}, n={n}: {100*mde:.1f} pp;"
          f" power for true +10 pp: {100*pw:.1f}%")

    rows, K, M = pooled_teacher(root)
    for rel, rid, kk, nn in rows:
        print(f"[teacher pool] {os.path.basename(rel)} run={rid}: {kk}/{nn}")
    lo, hi = wilson(K, M)
    print(f"[teacher pool] post-fix memory teacher: {K}/{M} = {100*K/M:.1f}%  Wilson95=[{100*lo:.1f}, {100*hi:.1f}]")

    txt = open(os.path.join(root, D6B_LOG)).read()
    k6, n6 = map(int, re.search(r"Collect loop done: (\d+) episodes, (\d+) success", txt).groups()[::-1])
    rid6 = run_id(txt)
    reps = [json.load(open(f))["outcome"] for f in glob.glob(os.path.join(root, "data/replays", rid6, "*", "*.json"))]
    assert (sum(o == "success" for o in reps), len(reps)) == (k6, n6), "D6b log != replays"
    lo, hi = wilson(k6, n6)
    print(f"[D6b memoryless teacher] run={rid6}: {k6}/{n6} = {100*k6/n6:.1f}%  Wilson95=[{100*lo:.1f}, {100*hi:.1f}]"
          f"  (log == replays)")

    ka, na = c["A_ctrl_rat"]
    kc, nc = c["C_retrieval"]
    gap = K / M - ka / na
    print(f"[L0a parity gap] (C_retrieval - A_ctrl_rat)/(teacher - A_ctrl_rat) ="
          f" {100*(kc/nc - ka/na):.1f}/{100*gap:.1f} = {100*(kc/nc - ka/na)/gap:.1f}%")

    b, cc = l2_discordant(root)
    print(f"[L2 McNemar exact] discordant {b} vs {cc}: p={mcnemar_exact(b, cc):.3f}")

    # L2 auto-reset check (same 24 s time-out, pin 8 rule applied to the L2 pair).
    l2s = json.load(open(os.path.join(root, L2_SENS_JSON)))
    assert l2s["C_retrieval_minus_A_ctrl_rat_as_run"]["mcnemar_b_c"] == [b, cc], "L2 sensitivity file != L2_CONF"
    for arm in ("A_ctrl_rat", "C_retrieval"):
        r = l2s[arm]
        print(f"[L2 sens {arm}] crossings {r['n_cross']}/{r['n']}, successes after boundary {r['n_success_after_b']};"
              f" as-run {r['as_run_success']} -> sensitivity {r['sens_success']}")
    row = l2s["C_retrieval_minus_A_ctrl_rat_sensitivity_pin8"]
    print(f"[L2 sens contrast] {row['sa']} vs {row['sb']}: delta={row['diff_pp']:+.1f} pp  z={row['z']:.3f}  p={row['p_z']:.3f}")

    for rid, eid in SHOWN_EPISODES:
        f = glob.glob(os.path.join(root, "data/replays", rid, "*", eid + ".json"))[0]
        d0 = json.load(open(f))["trajectory"][0]["distances"]["dist_red"]
        print(f"[Fig qual_end start distance] run={rid} ep={eid}: {100*d0:.1f} cm")

    # Round-3 B_main vs A_action_only correlation difference (Fisher z,
    # independent-samples form) from the rounds certificate.
    rtxt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ROUNDS_TXT)).read()
    rr = {a: (int(n), float(r)) for a, n, r in
          re.findall(r"\[round 3\] (\w+)\s+n=\s*(\d+)\s+r=([+-][\d.]+)", rtxt)}
    (n1, r1), (n2, r2) = rr["B_main"], rr["A_action_only"]
    zf = (math.atanh(r1) - math.atanh(r2)) / math.sqrt(1 / (n1 - 3) + 1 / (n2 - 3))
    print(f"[round 3 Fisher z] B_main r={r1:+.3f} (n={n1}) vs A_action_only r={r2:+.3f} (n={n2}):"
          f" z={zf:.2f}  p={2 * (1 - N.cdf(abs(zf))):.2f}")

    # A15 pin 8 auto-reset sensitivity (pre-registered sensitivity; as-run stays primary).
    sens = json.load(open(os.path.join(root, SENS_JSON)))
    # Confirmatory-table McNemar column (audit #2 FAIL-10): main rows from the
    # confirmatory report's discordants, sensitivity rows from the pin-8 file.
    conf_txt = open(os.path.join(root, D11_CONF)).read()
    for t, (b_, c_) in zip(("T1", "T1a", "T4"), re.findall(r"discordant: \w+-only=(\d+)\s+\w+-only=(\d+)", conf_txt)):
        print(f"[McNemar {t}] discordant {b_}/{c_}: p={mcnemar_rule(int(b_), int(c_)):.2g}")
    for row in sens["contrasts"]["sensitivity"]["contrasts"]:
        pm = mcnemar_rule(row["disc_a_only"], row["disc_b_only"])
        assert abs(pm - row["p_mcnemar"]) < 1e-9 * max(1, pm), f"{row['name']}: McNemar {pm} != file {row['p_mcnemar']}"
        print(f"[McNemar sens {row['name']}] discordant {row['disc_a_only']}/{row['disc_b_only']}: p={pm:.2g}")
    t3 = sens["contrasts"]["sensitivity"]["T3"]
    print(f"[T3 sens] B_main {100 * t3['B_main_sr']:.0f}% vs floor {100 * t3['floor']:.1f}%: z={t3['z']:.2f}  p={t3['p']:.2f}")
    for arm in c:
        run = sens["runs"][arm]
        assert run["as_run_success"] == c[arm][0], f"{arm}: sensitivity file as-run != CONF"
        print(f"[sens {arm}] as-run {run['as_run_success']}/{run['n']} -> sensitivity {run['sens_success']}/{run['n']}")
    for row in sens["contrasts"]["sensitivity"]["contrasts"]:
        lo, hi = row["newcombe95_pp"]
        print(f"[sens contrast {row['name']}] {row['sa']} vs {row['sb']}: delta={row['diff_pp']:+.1f} pp"
              f"  z={row['z']:.3f}  p={row['p_z']:.3g}  Newcombe95=[{lo:+.1f}, {hi:+.1f}]")
    print(f"[sens D6b] {sens['runs']['D6b_fa7f4571']['sens_success']}/100")
    # Teacher pool under the same rule: the pooled episodes, each counted only if it
    # succeeded before the first auto-reset (row-level, matched by episode id).
    sens_rows = {}
    for key, run in sens["runs"].items():
        for r in run["rows"]:
            sens_rows[(key.split("_")[-1], r["id"])] = r["sens_success"]
    ks = 0
    for rel, truncate in TEACHER_POOL_LOGS:
        lines = open(os.path.join(root, rel)).read().splitlines()
        rid = run_id("\n".join(lines))
        started = []
        for ln in lines:
            if truncate and OUTAGE_MARK in ln:
                break
            m = re.search(r"Episode (\d+)/\d+ \| [^|]+\| (\S+)", ln)
            if m:
                started.append(m.group(2))
        if truncate:
            started = started[:-1]
        ids = [next(i for (r_, i) in sens_rows if r_ == rid and i.startswith(p)) for p in started]
        ks += sum(sens_rows[(rid, i)] for i in ids)
    print(f"[sens teacher pool] {ks}/{M} = {100*ks/M:.1f}%")

    # {target_color} disclosure: unformatted template in the frozen C_retrieval buffer.
    recs = [json.load(open(f)) for f in glob.glob(os.path.join(root, "workspace/recaps_d10_frozen_c_retrieval", "*", "*.json"))]
    n_inst = sum("{target_color}" in (r.get("metadata", {}).get("instruction") or "") for r in recs)
    n_less = sum("{target_color}" in (r.get("text_lesson") or "") for r in recs)
    n_red = sum(bool(re.search(r"\bred\b", r.get("text_lesson") or "", re.I)) for r in recs)
    print(f"[target_color] frozen buffer {len(recs)} recaps: literal in instruction {n_inst}/{len(recs)},"
          f" in lesson {n_less}/{len(recs)}; lesson names 'red' {n_red}/{len(recs)}")

    # Reproduction targets (REPRODUCE.md): 95% Wilson intervals for the two
    # identical-weights arms at n=100.
    for arm in ("C_retrieval", "A_ctrl_rat"):
        k, n = c[arm]
        lo, hi = wilson(k, n)
        print(f"[repro {arm}] {k}/{n}  Wilson95=[{100*lo:.1f}, {100*hi:.1f}]")

    # Same-hardware cost re-measure (descriptive, A15 add-on): per-step means.
    md = open(os.path.join(root, COST_LOG)).read()
    for row in json.loads(re.search(r"```json\n(.*?)\n```", md, re.S).group(1)):
        dec = row["server_predicted_ms_per_step"] / 1000
        print(f"[cost {row['protocol']}] completion_tok/step={row['completion_tok_per_step']:.0f}"
              f"  wall_s/step={row['wall_s_per_step']:.1f}"
              f"  decode_share={100 * dec / row['wall_s_per_step']:.0f}%"
              f"  decode_ms/token={row['server_predicted_ms_per_step'] / row['completion_tok_per_step']:.0f}")

    # A15 reviewer-requested controls: frozen buffer on no adapter / other adapters.
    # Counts re-tested here from the JSON's own counts; y-counts must equal D11.
    a15 = json.load(open(os.path.join(root, A15_JSON)))
    for proto, arm in A15_ARM.items():
        if proto not in a15:
            print(f"[A15 {proto}] not in {A15_JSON}")
            continue
        for key, ref in (("vs_C_retrieval", "C_retrieval"), ("vs_own_D11_no_retrieval", arm)):
            if key not in a15[proto]:
                continue
            row, sens_row = a15[proto][key], a15[proto][key + "_sensitivity_pin8"]
            kx, ky, n = row["sr_x"], row["sr_y"], row["n"]
            assert (ky, n) == c[ref], f"A15 {proto} {key}: sr_y {ky}/{n} != D11 {ref} {c[ref]}"
            z, p = two_prop_z(kx, n, ky, n)
            assert abs(z - row["z"]) < 1e-3, f"A15 {proto} {key}: z {z:.3f} != JSON {row['z']}"
            print(f"[A15 {proto} {key}] {kx} vs {ky}/{n}: delta={row['diff_pp']:+d} pp  z={z:.4f}  p={p:.3g}"
                  f"  Newcombe95={pct(newcombe(kx, n, ky, n))}  sensitivity {sens_row['sr_x']} vs {sens_row['sr_y']}")

    # A15.1 R1' slope reading (15 mm recovery gate): pre-registered status for the
    # A15 arms only; the five D11 arms are post hoc (A15.1).
    for arm, row in json.load(open(os.path.join(root, A15_SLOPE_JSON))).items():
        if not isinstance(row, dict):
            continue
        status = "prereg" if arm.startswith("A15_") else "post-hoc"
        print(f"[A15 slope {arm}] {status} r={row['r']:+.3f}  band=[{row['band'][0]:+.3f}, {row['band'][1]:+.3f}]"
              f"  above={row['above_band']}  n={row['n']}  excluded={row['excluded_recovery_gate']}"
              f"  residual_max={1000 * row['gate_residual_max_m']:.1f} mm")

    lo_x, hi_x = x_bounds(root)
    print(f"[R1 dX unit] scalar-guard grid [-100,100] over x_bounds={lo_x, hi_x} m:"
          f" 1 grid unit = {100*(hi_x - lo_x)/200:.3f} cm along x")


if __name__ == "__main__":
    main()
