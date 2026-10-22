#!/usr/bin/env python3
"""Comparator script: Rung-2 (3e8c52d4) vs Rung-2' (71134939) on seeds 5000-5049.
Analyzes per-seed Z distributions, round-by-round dynamics, and tests the hypothesis:
'history/feedback caused height anchoring'.
"""
import glob
import json
from collections import Counter
import numpy as np

R2_DIR = "/home/control/AionGenos/data/collect_dumps/3e8c52d4"
R2P_DIR = "/home/control/AionGenos/data/collect_dumps/71134939"

def load_episodes(dump_dir):
    meta_files = sorted(glob.glob(f"{dump_dir}/*/meta.json"))
    eps = {}
    for f in meta_files:
        d = json.load(open(f))
        eps[d["env_seed"]] = d
    return eps

def main():
    r2_eps = load_episodes(R2_DIR)
    r2p_eps = load_episodes(R2P_DIR)
    seeds = sorted(list(set(r2_eps.keys()) & set(r2p_eps.keys())))
    assert len(seeds) == 50, f"Expected 50 paired seeds, got {len(seeds)}"

    print(f"Loaded {len(seeds)} paired seeds (seeds {min(seeds)}..{max(seeds)})")
    
    # 1. Per-seed Z statistics
    print("\n" + "="*120)
    print("PER-SEED Z DISTRIBUTION (Rung-2 vs Rung-2')")
    print("="*120)
    print(f"{'Seed':<5} | {'R2 Rds':<6} {'R2 R1':<6} {'R2 R2':<6} {'R2 Mean':<8} {'R2 Med':<6} {'R2 Uniq':<7} {'R2==53':<7} | "
          f"{'R2p Rds':<7} {'R2p R1':<7} {'R2p R2':<7} {'R2p Mean':<9} {'R2p Med':<7} {'R2p Uniq':<8} {'R2p==53':<8}")
    print("-"*120)

    r2_all_53_count = 0
    r2p_all_53_count = 0
    r2_zero_var_count = 0
    r2p_zero_var_count = 0

    for s in seeds:
        z2 = [r["eef_target_int"][2] for r in r2_eps[s]["rounds"]]
        z2p = [r["eef_target_int"][2] for r in r2p_eps[s]["rounds"]]
        
        r2_all_53 = all(z == 53 for z in z2)
        r2p_all_53 = all(z == 53 for z in z2p)
        if r2_all_53: r2_all_53_count += 1
        if r2p_all_53: r2p_all_53_count += 1
        if len(set(z2)) == 1: r2_zero_var_count += 1
        if len(set(z2p)) == 1: r2p_zero_var_count += 1

        print(f"{s:<5} | {len(z2):<6} {z2[0]:<6} {z2[1]:<6} {np.mean(z2):<8.2f} {np.median(z2):<6.1f} {len(set(z2)):<7} {str(r2_all_53):<7} | "
              f"{len(z2p):<7} {z2p[0]:<7} {z2p[1]:<7} {np.mean(z2p):<9.2f} {np.median(z2p):<7.1f} {len(set(z2p)):<8} {str(r2p_all_53):<8}")

    print("\n" + "="*120)
    print("GLOBAL SUMMARY METRICS")
    print("="*120)
    
    r2_rounds_all = [r["eef_target_int"][2] for s in seeds for r in r2_eps[s]["rounds"]]
    r2p_rounds_all = [r["eef_target_int"][2] for s in seeds for r in r2p_eps[s]["rounds"]]

    r2_r1 = [r2_eps[s]["rounds"][0]["eef_target_int"][2] for s in seeds]
    r2p_r1 = [r2p_eps[s]["rounds"][0]["eef_target_int"][2] for s in seeds]

    r2_r2 = [r2_eps[s]["rounds"][1]["eef_target_int"][2] for s in seeds]
    r2p_r2 = [r2p_eps[s]["rounds"][1]["eef_target_int"][2] for s in seeds]

    r2_r2plus = [r["eef_target_int"][2] for s in seeds for r in r2_eps[s]["rounds"][1:]]
    r2p_r2plus = [r["eef_target_int"][2] for s in seeds for r in r2p_eps[s]["rounds"][1:]]

    print(f"Total episodes: 50 | Total rounds: Rung-2={len(r2_rounds_all)}, Rung-2'={len(r2p_rounds_all)}")
    print(f"Rung-2 episodes with all rounds Z=53: {r2_all_53_count}/50 ({r2_all_53_count/50*100:.1f}%)")
    print(f"Rung-2' episodes with all rounds Z=53: {r2p_all_53_count}/50 ({r2p_all_53_count/50*100:.1f}%)")
    print(f"Rung-2 episodes with zero Z variation: {r2_zero_var_count}/50 ({r2_zero_var_count/50*100:.1f}%)")
    print(f"Rung-2' episodes with zero Z variation: {r2p_zero_var_count}/50 ({r2p_zero_var_count/50*100:.1f}%)")

    r2_uniq_per_ep = [len(set(r["eef_target_int"][2] for r in r2_eps[s]["rounds"])) for s in seeds]
    r2p_uniq_per_ep = [len(set(r["eef_target_int"][2] for r in r2p_eps[s]["rounds"])) for s in seeds]
    print(f"Rung-2 unique Z values per ep: mean={np.mean(r2_uniq_per_ep):.2f}, std={np.std(r2_uniq_per_ep):.2f}, min={min(r2_uniq_per_ep)}, max={max(r2_uniq_per_ep)}")
    print(f"Rung-2' unique Z values per ep: mean={np.mean(r2p_uniq_per_ep):.2f}, std={np.std(r2p_uniq_per_ep):.2f}, min={min(r2p_uniq_per_ep)}, max={max(r2p_uniq_per_ep)}")

    print("\n--- Round 1 ---")
    print(f"Rung-2  R1: mean={np.mean(r2_r1):.2f}, median={np.median(r2_r1):.1f}, Z=53 count={r2_r1.count(53)}/50 ({r2_r1.count(53)/50*100:.1f}%), Counter={dict(Counter(r2_r1))}")
    print(f"Rung-2' R1: mean={np.mean(r2p_r1):.2f}, median={np.median(r2p_r1):.1f}, Z=53 count={r2p_r1.count(53)}/50 ({r2p_r1.count(53)/50*100:.1f}%), Counter={dict(Counter(r2p_r1))}")

    print("\n--- Round 2 ---")
    print(f"Rung-2  R2: mean={np.mean(r2_r2):.2f}, median={np.median(r2_r2):.1f}, Z=53 count={r2_r2.count(53)}/50 ({r2_r2.count(53)/50*100:.1f}%), % in [30,40]={sum(1 for z in r2_r2 if 30<=z<=40)/50*100:.1f}%")
    print(f"Rung-2' R2: mean={np.mean(r2p_r2):.2f}, median={np.median(r2p_r2):.1f}, Z=53 count={r2p_r2.count(53)}/50 ({r2p_r2.count(53)/50*100:.1f}%), % in [30,40]={sum(1 for z in r2p_r2 if 30<=z<=40)/50*100:.1f}%")

    print("\n--- Rounds 2-12 (Combined) ---")
    print(f"Rung-2  R2+: n={len(r2_r2plus)}, mean={np.mean(r2_r2plus):.2f}, median={np.median(r2_r2plus):.1f}, Z=53 count={r2_r2plus.count(53)} ({r2_r2plus.count(53)/len(r2_r2plus)*100:.2f}%), % in [30,40]={sum(1 for z in r2_r2plus if 30<=z<=40)/len(r2_r2plus)*100:.1f}%")
    print(f"Rung-2' R2+: n={len(r2p_r2plus)}, mean={np.mean(r2p_r2plus):.2f}, median={np.median(r2p_r2plus):.1f}, Z=53 count={r2p_r2plus.count(53)} ({r2p_r2plus.count(53)/len(r2p_r2plus)*100:.2f}%), % in [30,40]={sum(1 for z in r2p_r2plus if 30<=z<=40)/len(r2p_r2plus)*100:.1f}%")

    print("\n--- Overall (All Rounds) ---")
    print(f"Rung-2  All: n={len(r2_rounds_all)}, mean={np.mean(r2_rounds_all):.2f}, median={np.median(r2_rounds_all):.1f}, Z=53 count={r2_rounds_all.count(53)} ({r2_rounds_all.count(53)/len(r2_rounds_all)*100:.2f}%), % in [30,40]={sum(1 for z in r2_rounds_all if 30<=z<=40)/len(r2_rounds_all)*100:.1f}%")
    print(f"Rung-2' All: n={len(r2p_rounds_all)}, mean={np.mean(r2p_rounds_all):.2f}, median={np.median(r2p_rounds_all):.1f}, Z=53 count={r2p_rounds_all.count(53)} ({r2p_rounds_all.count(53)/len(r2p_rounds_all)*100:.2f}%), % in [30,40]={sum(1 for z in r2p_rounds_all if 30<=z<=40)/len(r2p_rounds_all)*100:.1f}%")

if __name__ == "__main__":
    main()
