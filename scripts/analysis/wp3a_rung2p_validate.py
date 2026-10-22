"""Instrument validation for rung-2' run 71134939: does the pipeline report what happened?"""
import glob, hashlib, json, math, re, statistics as st, collections, sys
RUN = sys.argv[1] if len(sys.argv) > 1 else "71134939"
H = 0.0240; SUCC = 0.05
eps = [json.load(open(f)) for f in sorted(glob.glob(f"/home/control/AionGenos/data/collect_dumps/{RUN}/*/meta.json"))]
def box(p, c):  # axis-aligned approx (cube yaw ignored; flagged if mismatch)
    return math.sqrt(sum(max(abs(a - b) - H, 0) ** 2 for a, b in zip(p, c)))
R = collections.Counter(); reach = []; lowz = []; fb_bad = []; img_same = 0; img_pairs = 0
init_cg = []; min_cg = []; thoughts_z = 0; nrounds = 0; zt = collections.Counter(); outcomes = collections.Counter()
for e in eps:
    outcomes[e["outcome"]] += 1
    rs = e["rounds"]; init_cg.append(rs[0]["cube_goal_dist_m_pre"]); min_cg.append(min(r["cube_goal_dist_m"] for r in rs))
    d = f"/home/control/AionGenos/data/collect_dumps/{RUN}/{e['episode_id']}"
    prev_md5 = None
    for i, r in enumerate(rs):
        nrounds += 1; zt[r["eef_target_int"][2]] += 1
        if r.get("tcp_reach_err_cm") is not None: reach.append(r["tcp_reach_err_cm"])
        tg = r.get("table_guard") or {}
        if tg.get("target_clamp"): R["target_clamp"] += 1
        if r["eef_target_m"][2] < 0.52: lowz.append((r["eef_target_m"][2], r["tcp_final_b"][2]))
        t = (r.get("vlm_thought") or "").lower()
        if re.search(r"\bz\b|z=|lower|descend|height|down|above", t): thoughts_z += 1
        try:
            m = hashlib.md5(open(f"{d}/round_{i+1:02d}_pre.png", "rb").read()).hexdigest()
            if prev_md5 is not None:
                img_pairs += 1; img_same += (m == prev_md5)
            prev_md5 = m
        except FileNotFoundError: R["png_missing"] += 1
        if i == 0:
            if r.get("round_feedback"): R["fb_on_round1"] += 1
            continue
        fb = r.get("round_feedback") or ""
        if not fb: R["fb_missing"] += 1; continue
        p = rs[i - 1]
        nums = lambda pat: [int(x) for x in re.search(pat, fb).groups()]
        tgt = nums(r"predicted at: X=(-?\d+) Y=(-?\d+) Z=(-?\d+)")
        mv = nums(r"from X=(-?\d+) Y=(-?\d+) Z=(-?\d+) to X=(-?\d+) Y=(-?\d+) Z=(-?\d+)")
        ts, te = map(float, re.search(r"Fingertip-to-cube distance: started at ([\d.]+) cm, ended at ([\d.]+)", fb).groups())
        cs, ce = map(float, re.search(r"Cube-to-goal distance: started at ([\d.]+) cm, ended at ([\d.]+)", fb).groups())
        ok = {
            "target==prev_target": tgt == p["eef_target_int"],
            "move_from==prev_start": mv[:3] == p["ee_start_int"],
            "move_to==this_start": mv[3:] == r["ee_start_int"],
            "tip_start": abs(ts - 100 * box(p["ee_start_b"], p["cube_b_pre"])) <= 0.25,
            "tip_end": abs(te - 100 * box(r["ee_start_b"], r["cube_b_pre"])) <= 0.25,
            "cg_start": abs(cs - 100 * p["cube_goal_dist_m_pre"]) <= 0.15,
            "cg_end": abs(ce - 100 * r["cube_goal_dist_m_pre"]) <= 0.15,
            "verdict_matches_cg": (("progress" in fb.lower() and "no significant" not in fb.lower()) == (ce - cs < -1.0)) ,
        }
        for k, v in ok.items():
            R[f"fb_{k}_{'OK' if v else 'BAD'}"] += 1
            if not v and len(fb_bad) < 6: fb_bad.append((e["env_seed"], i + 1, k, fb.splitlines()[2:6]))
print(f"episodes={len(eps)} rounds={nrounds} outcomes={dict(outcomes)}")
print(f"[exec] tcp_reach_err_cm median={st.median(reach):.2f} p95={sorted(reach)[int(.95*len(reach))]:.2f} max={max(reach):.2f}; target_clamps={R['target_clamp']}")
print(f"[exec] rounds with target z<0.52m: {len(lowz)}; achieved z for those (target,achieved) sample: {lowz[:8]}")
print(f"[z] target z-int histogram top: {zt.most_common(6)}")
print(f"[thought] rounds whose thought mentions height/Z/descend: {thoughts_z}/{nrounds}")
print(f"[task] initial cube->goal cm: min={100*min(init_cg):.1f} median={100*st.median(init_cg):.1f} max={100*max(init_cg):.1f}; success needs <= {100*SUCC:.0f} cm")
print(f"[task] best cube->goal reached per episode: min={100*min(min_cg):.1f} cm")
print(f"[image] consecutive round_pre PNG identical: {img_same}/{img_pairs}; missing={R['png_missing']}")
print("[feedback]", {k: v for k, v in sorted(R.items()) if k.startswith('fb_')})
for b in fb_bad: print("  BAD", b)
