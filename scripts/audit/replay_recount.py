#!/usr/bin/env python3
"""Independent re-counter for pre-publication audit (replay-recount).

Hard rules:
- Python standard library only (json, glob, os, collections, re, sys).
- Independent count: no imports from aiongenos/ or scripts/analysis/.
- Replays: data/replays/<run_id>/<success|failure>/<episode_id>.json.
- Assigns ep_idx 0..99 by sorting replay files by modification time (os.path.getmtime).
- Cross-checks mtime order against log order from logs/*.log.
- Compares against reported figures from audit reports and stats JSONs.
- Outputs table to docs/paper/birth_certificates/replay_recount.txt.
"""

import collections
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

RUNS = collections.OrderedDict([
    ("e4d81bb6", ("D11", "A_action_only")),
    ("56ee684b", ("D11", "A_ctrl_rat")),
    ("a7b11544", ("D11", "B_main")),
    ("875c04fb", ("D11", "D_gist")),
    ("09817322", ("D11", "C_retrieval")),
    ("8384a740", ("L2", "A_ctrl_rat")),
    ("2154e57e", ("L2", "C_retrieval")),
    ("995f496c", ("A15", "a_base_ret")),
    ("9be74fc2", ("A15", "b_action_only_ret")),
    ("13c5c402", ("A15", "b_B_main_ret")),
    ("fdb2a9b0", ("A15", "b_D_gist_ret")),
])

CONTRASTS = [
    ("T1", "a7b11544", "e4d81bb6"),
    ("T1a", "a7b11544", "56ee684b"),
    ("T4", "09817322", "a7b11544"),
    ("identical-weights", "09817322", "56ee684b"),
    ("L2", "2154e57e", "8384a740"),
    ("A15 995f496c vs 09817322", "995f496c", "09817322"),
    ("A15 9be74fc2 vs 09817322", "9be74fc2", "09817322"),
    ("A15 13c5c402 vs 09817322", "13c5c402", "09817322"),
    ("A15 fdb2a9b0 vs 09817322", "fdb2a9b0", "09817322"),
    ("A15 own 9be74fc2 vs e4d81bb6", "9be74fc2", "e4d81bb6"),
    ("A15 own 13c5c402 vs a7b11544", "13c5c402", "a7b11544"),
    ("A15 own fdb2a9b0 vs 875c04fb", "fdb2a9b0", "875c04fb"),
]


def find_collect_log(repo_root, run_id, arm_name):
    """Find the specific collect log in logs/ for a given run_id."""
    log_dir = os.path.join(repo_root, "logs")
    candidates = []
    for fname in sorted(os.listdir(log_dir)):
        if not fname.endswith(".log"):
            continue
        fpath = os.path.join(log_dir, fname)
        if os.path.getsize(fpath) > 10 * 1024 * 1024:
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                for line in fp:
                    if f"run_id={run_id}" in line:
                        candidates.append(fpath)
                        break
        except Exception:
            pass

    if not candidates:
        return None
    for c in candidates:
        if arm_name.lower() in os.path.basename(c).lower():
            return c
    return candidates[0]


def extract_log_episodes(log_path):
    """Extract episode IDs in order from collect log lines."""
    episodes = []
    pattern = re.compile(r"Episode\s+(\d+)/100\s+\|\s+L-?2\s+\|\s+([0-9a-f\-]+)")
    with open(log_path, "r", encoding="utf-8", errors="ignore") as fp:
        for line in fp:
            m = pattern.search(line)
            if m:
                episodes.append(m.group(2))
    return episodes


def parse_report_values(repo_root):
    """Parse reference values from audited reports and summary JSONs."""
    reports_runs = {}
    reports_contrasts = {}

    # D11 report
    d11_rep = os.path.join(repo_root, "workspace", "d11_audit", "d11_confirmatory_report.txt")
    if os.path.exists(d11_rep):
        with open(d11_rep, "r", encoding="utf-8") as fp:
            d11_text = fp.read()
        for line in d11_text.splitlines()[:15]:
            m = re.search(r"run=([0-9a-f]{8})\s+episodes=\d+\s+successes=(\d+)", line)
            if m:
                reports_runs[m.group(1)] = int(m.group(2))

        m_t1 = re.search(r"\[T1\].*?discordant:\s*B_main-only=(\d+)\s+A_action_only-only=(\d+)", d11_text, re.DOTALL)
        if m_t1:
            reports_contrasts["T1"] = (int(m_t1.group(1)), int(m_t1.group(2)))
        m_t1a = re.search(r"\[T1a\].*?discordant:\s*B_main-only=(\d+)\s+A_ctrl_rat-only=(\d+)", d11_text, re.DOTALL)
        if m_t1a:
            reports_contrasts["T1a"] = (int(m_t1a.group(1)), int(m_t1a.group(2)))
        m_t4 = re.search(r"\[T4\].*?discordant:\s*C_retrieval-only=(\d+)\s+B_main-only=(\d+)", d11_text, re.DOTALL)
        if m_t4:
            reports_contrasts["T4"] = (int(m_t4.group(1)), int(m_t4.group(2)))

    # L2 report
    l2_rep = os.path.join(repo_root, "workspace", "l2_audit", "l2_confirmatory_output.txt")
    if os.path.exists(l2_rep):
        with open(l2_rep, "r", encoding="utf-8") as fp:
            l2_text = fp.read()
        for m in re.finditer(r"run=([0-9a-f]{8}).*?successes=(\d+)", l2_text, re.DOTALL):
            reports_runs[m.group(1)] = int(m.group(2))
        m_l2 = re.search(r"discordant cells:\s*C_retrieval-only=(\d+)\s+A_ctrl_rat-only=(\d+)", l2_text)
        if m_l2:
            reports_contrasts["L2"] = (int(m_l2.group(1)), int(m_l2.group(2)))

    # A15 JSON
    a15_path = os.path.join(repo_root, "docs", "paper", "data", "a15_ab_stats.json")
    if os.path.exists(a15_path):
        with open(a15_path, "r", encoding="utf-8") as fp:
            a15_data = json.load(fp)
        arm_to_run = {
            "a_base_ret": "995f496c",
            "b_action_only_ret": "9be74fc2",
            "b_B_main_ret": "13c5c402",
            "b_D_gist_ret": "fdb2a9b0",
        }
        for arm, rid in arm_to_run.items():
            sub = a15_data.get(arm, {})
            vc = sub.get("vs_C_retrieval", {})
            reports_runs[rid] = vc.get("sr_x")
            reports_contrasts[f"A15 {rid} vs 09817322"] = (
                vc.get("discordant_b_x_only"),
                vc.get("discordant_c_y_only"),
            )
            if "vs_own_D11_no_retrieval" in sub:
                vo = sub["vs_own_D11_no_retrieval"]
                own_map = {
                    "9be74fc2": "e4d81bb6",
                    "13c5c402": "a7b11544",
                    "fdb2a9b0": "875c04fb",
                }
                reports_contrasts[f"A15 own {rid} vs {own_map[rid]}"] = (
                    vo.get("discordant_b_x_only"),
                    vo.get("discordant_c_y_only"),
                )

    # Identical-weights search in derived_stats.txt and workspace/d11_audit/
    # Confirmatory discordant pair for 09817322 vs 56ee684b is not reported
    reports_contrasts["identical-weights"] = ("NOT FOUND", "NOT FOUND")

    return reports_runs, reports_contrasts


def main():
    repo_root = REPO_ROOT
    rep_runs, rep_contrasts = parse_report_values(repo_root)

    run_data = {}
    mismatches = 0

    run_rows = []
    for run_id, (proto, arm) in RUNS.items():
        pattern = os.path.join(repo_root, "data", "replays", run_id, "*", "*.json")
        files = glob.glob(pattern)
        file_count = len(files)
        if file_count != 100:
            mismatches += 1

        # Sort by mtime (os.path.getmtime)
        files.sort(key=lambda p: (os.path.getmtime(p), p))

        episodes = []
        success_count = 0
        for ep_idx, fpath in enumerate(files):
            with open(fpath, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            is_succ = (d.get("outcome") == "success")
            if is_succ:
                success_count += 1
            episodes.append({
                "ep_idx": ep_idx,
                "episode_id": d.get("episode_id"),
                "success": is_succ,
                "mtime": os.path.getmtime(fpath),
            })

        run_data[run_id] = {
            "proto": proto,
            "arm": arm,
            "files": file_count,
            "successes": success_count,
            "episodes": episodes,
        }

        # Cross-check mtime order vs log order
        log_file = find_collect_log(repo_root, run_id, arm)
        if log_file and os.path.exists(log_file):
            log_ep_ids = extract_log_episodes(log_file)
            mtime_ep_ids = [e["episode_id"] for e in episodes]
            agreement = sum(
                1 for m, l in zip(mtime_ep_ids, log_ep_ids)
                if m.startswith(l) or l.startswith(m)
            )
            agreement_str = f"{agreement}/100"
        else:
            agreement_str = "LOG NOT FOUND"

        report_val = rep_runs.get(run_id, "NOT FOUND")
        if report_val != "NOT FOUND":
            status = "MATCH" if success_count == report_val else "MISMATCH"
            if status == "MISMATCH":
                mismatches += 1
        else:
            status = "NOT FOUND"

        run_rows.append({
            "run_id": run_id,
            "label": f"{proto} {arm}",
            "files": file_count,
            "successes": success_count,
            "report_val": report_val,
            "status": status,
            "agreement": agreement_str,
        })

    contrast_rows = []
    for contrast_name, rx, ry in CONTRASTS:
        ox = [e["success"] for e in run_data[rx]["episodes"]]
        oy = [e["success"] for e in run_data[ry]["episodes"]]

        b = sum(1 for x, y in zip(ox, oy) if x and not y)
        c = sum(1 for x, y in zip(ox, oy) if y and not x)

        rep_pair = rep_contrasts.get(contrast_name, ("NOT FOUND", "NOT FOUND"))
        rep_b, rep_c = rep_pair

        if rep_b != "NOT FOUND" and rep_c != "NOT FOUND":
            status = "MATCH" if (b == rep_b and c == rep_c) else "MISMATCH"
            if status == "MISMATCH":
                mismatches += 1
        else:
            status = "NOT FOUND"

        contrast_rows.append({
            "contrast": contrast_name,
            "pair": f"{rx} vs {ry}",
            "b": b,
            "c": c,
            "rep_b": rep_b,
            "rep_c": rep_c,
            "status": status,
        })

    # Prepare plain-text table
    lines = []
    if mismatches > 0:
        lines.append("MISMATCH - STOP")

    lines.append("# Replay Recount Birth Certificate — Independent Pre-Publication Audit")
    lines.append("# Date: 2026-10-20")
    lines.append("# Command: python3 scripts/audit/replay_recount.py")
    lines.append(f"# Mismatches detected: {mismatches}")
    lines.append("")
    lines.append("=" * 105)
    lines.append("RUN-LEVEL AUDIT TABLE")
    lines.append("=" * 105)
    lines.append(f"{'Run ID':8s}  {'Protocol / Arm':25s}  {'Files':5s}  {'Successes':9s}  {'Report Val':10s}  {'Status':8s}  {'Mtime-Log Agr':13s}")
    lines.append(f"{'-'*8}  {'-'*25}  {'-'*5}  {'-'*9}  {'-'*10}  {'-'*8}  {'-'*13}")

    for r in run_rows:
        lines.append(
            f"{r['run_id']:8s}  {r['label']:25s}  {r['files']:5d}  {r['successes']:9d}  {str(r['report_val']):10s}  {r['status']:8s}  {r['agreement']:13s}"
        )

    lines.append("")
    lines.append("=" * 105)
    lines.append("PAIRED CONTRAST AUDIT TABLE")
    lines.append("=" * 105)
    lines.append(f"{'Contrast':28s}  {'Pair (x vs y)':21s}  {'b':3s}  {'c':3s}  {'Report b':9s}  {'Report c':9s}  {'Status':8s}")
    lines.append(f"{'-'*28}  {'-'*21}  {'-'*3}  {'-'*3}  {'-'*9}  {'-'*9}  {'-'*8}")

    for c in contrast_rows:
        lines.append(
            f"{c['contrast']:28s}  {c['pair']:21s}  {c['b']:3d}  {c['c']:3d}  {str(c['rep_b']):9s}  {str(c['rep_c']):9s}  {c['status']:8s}"
        )

    output_text = "\n".join(lines) + "\n"

    out_file = os.path.join(repo_root, "docs", "paper", "birth_certificates", "replay_recount.txt")
    with open(out_file, "w", encoding="utf-8") as fp:
        fp.write(output_text)

    sys.stdout.write(output_text)
    return mismatches


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
