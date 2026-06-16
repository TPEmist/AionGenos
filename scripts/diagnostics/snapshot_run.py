"""Render a one-page mid-run report (markdown + 4-panel PNG) for a collect run.

Used by the D5 watcher: every 10 episodes, snapshot to
``data/100ep-run-0616/snapshot_NN.md`` plus ``snapshot_NN.png``.

The PNG packs four panels:

  1. Per-episode best L_dist (cm) bar — color-coded outcome
  2. Cumulative success rate over episodes
  3. Outcome distribution pie
  4. Initial EE position scatter (X vs Y) — sample diversity

The markdown summarises the same data plus an axis-token usage
breakdown across all rounds in the run.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


_AXIS_TOKEN_PATTERNS = {
    "x_pos": re.compile(r"\bx\s*[+]|\+\s*x|x\s*=\s*positive|x\s*increases?", re.I),
    "x_neg": re.compile(r"\bx\s*[-]|\-\s*x|x\s*=\s*negative|x\s*decreases?", re.I),
    "y_pos": re.compile(r"\by\s*[+]|\+\s*y|y\s*=\s*positive|y\s*increases?", re.I),
    "y_neg": re.compile(r"\by\s*[-]|\-\s*y|y\s*=\s*negative|y\s*decreases?", re.I),
    "z_pos": re.compile(r"\bz\s*[+]|\+\s*z|z\s*=\s*positive|z\s*increases?|up", re.I),
    "z_neg": re.compile(r"\bz\s*[-]|\-\s*z|z\s*=\s*negative|z\s*decreases?|down", re.I),
}


_OUTCOME_COLORS = {
    "success": "#2e7d32",
    "timeout": "#1976d2",
    "vlm_stop_premature": "#f57c00",
    "vlm_parse_fail": "#c62828",
    "collision": "#7b1fa2",
}


def _gather_episodes(run_dir: Path, sim_steps: int = 30) -> list[dict]:
    """Read every replay JSON in run_dir/{success,failure}/, sorted by mtime."""
    files = sorted(
        list((run_dir / "success").glob("*.json")) + list((run_dir / "failure").glob("*.json")),
        key=lambda p: p.stat().st_mtime,
    )
    eps = []
    for f in files:
        d = json.loads(f.read_text())
        traj = d.get("trajectory", [])
        n = len(d.get("vlm_interactions", []))
        # per-round end-of-round dist
        L_per_round, R_per_round = [], []
        for i in range(n):
            end_step = min((i + 1) * sim_steps - 1, len(traj) - 1)
            if end_step < 0:
                continue
            dist = traj[end_step].get("distances", {})
            L_per_round.append(dist.get("dist_red", float("nan")) * 100)
            R_per_round.append(dist.get("dist_blue", float("nan")) * 100)

        L_min = min((v for v in L_per_round if v == v), default=float("nan"))
        R_min = min((v for v in R_per_round if v == v), default=float("nan"))
        last_dist = traj[-1]["distances"] if traj else {}

        # axis token counts across this episode's thoughts
        token_count: Counter[str] = Counter()
        for x in d.get("vlm_interactions", []):
            thought = x.get("full_response") or ""
            for k, pat in _AXIS_TOKEN_PATTERNS.items():
                token_count[k] += len(pat.findall(thought))

        # initial EE
        init_L = traj[0].get("left_ee_pos") if traj else None
        init_R = traj[0].get("right_ee_pos") if traj else None

        eps.append({
            "id": d["episode_id"][:12],
            "outcome": d.get("outcome", "?"),
            "rounds": n,
            "best_L_cm": L_min,
            "best_R_cm": R_min,
            "final_L_cm": last_dist.get("dist_red", 0) * 100,
            "final_R_cm": last_dist.get("dist_blue", 0) * 100,
            "axis_tokens": dict(token_count),
            "init_L": tuple(init_L) if init_L else None,
            "init_R": tuple(init_R) if init_R else None,
            "duration_s": d.get("episode_duration_s", 0.0),
            "flags": d.get("flags", []),
        })
    return eps


def _render_png(eps: list[dict], out_png: Path, run_id: str) -> None:
    """Four-panel matplotlib summary."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"Run {run_id} — {len(eps)} episodes", fontsize=13)

    # Panel 1: per-ep best_L bar with outcome color
    ax = axes[0, 0]
    xs = list(range(1, len(eps) + 1))
    ys = [e["best_L_cm"] for e in eps]
    colors = [_OUTCOME_COLORS.get(e["outcome"], "#666") for e in eps]
    ax.bar(xs, ys, color=colors)
    ax.axhline(5.0, color="red", linestyle="--", lw=1, label="success thr 5cm")
    ax.set_xlabel("episode #")
    ax.set_ylabel("best L_dist (cm)")
    ax.set_title("Per-episode active-arm best distance")
    ax.legend(fontsize=8)

    # Panel 2: cumulative SR
    ax = axes[0, 1]
    cum_succ = np.cumsum([1 if e["outcome"] == "success" else 0 for e in eps])
    sr = cum_succ / np.arange(1, len(eps) + 1)
    ax.plot(xs, sr, "o-", color="#2e7d32")
    ax.set_xlabel("episode #")
    ax.set_ylabel("cumulative SR")
    ax.set_ylim(0, max(0.5, max(sr) * 1.2 if len(sr) else 0.5))
    ax.set_title(f"Cumulative SR (final = {sr[-1]:.1%})" if len(sr) else "Cumulative SR")
    ax.grid(True, alpha=0.3)

    # Panel 3: outcome distribution pie
    ax = axes[1, 0]
    outcome_counts = Counter(e["outcome"] for e in eps)
    if outcome_counts:
        labels = list(outcome_counts.keys())
        sizes = [outcome_counts[k] for k in labels]
        pie_colors = [_OUTCOME_COLORS.get(k, "#aaa") for k in labels]
        ax.pie(sizes, labels=labels, colors=pie_colors,
               autopct="%1.0f%%", startangle=90)
    ax.set_title("Outcome distribution")

    # Panel 4: initial EE diversity (left arm only)
    ax = axes[1, 1]
    init_L = [e["init_L"] for e in eps if e["init_L"] is not None]
    if init_L:
        xs = [p[0] for p in init_L]
        ys_ = [p[1] for p in init_L]
        ax.scatter(xs, ys_, c=range(len(init_L)), cmap="viridis", s=50)
        ax.set_xlabel("init left X (grid)")
        ax.set_ylabel("init left Y (grid)")
        ax.set_title(f"Initial L-EE diversity  (n={len(init_L)})")
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def _render_md(eps: list[dict], out_md: Path, run_id: str, png_name: str) -> None:
    """Markdown summary."""
    n = len(eps)
    succ = sum(1 for e in eps if e["outcome"] == "success")
    sr = succ / n if n else 0.0
    avg_best_L = float(np.nanmean([e["best_L_cm"] for e in eps])) if eps else float("nan")
    avg_rounds = float(np.mean([e["rounds"] for e in eps])) if eps else 0.0
    outcome_counts = Counter(e["outcome"] for e in eps)
    flag_counts: Counter[str] = Counter()
    for e in eps:
        for f in e["flags"]:
            flag_counts[f] += 1

    # axis tokens aggregated across run
    axis_total: Counter[str] = Counter()
    for e in eps:
        for k, v in e["axis_tokens"].items():
            axis_total[k] += v

    # init-EE std
    init_L = np.array([e["init_L"] for e in eps if e["init_L"] is not None])
    if len(init_L) >= 2:
        std_L = init_L.std(axis=0)
        std_str = f"L-EE init std (X,Y,Z)=({std_L[0]:.1f},{std_L[1]:.1f},{std_L[2]:.1f})  n={len(init_L)}"
    else:
        std_str = f"L-EE init std: insufficient samples (n={len(init_L)})"

    lines = [
        f"# Snapshot — Run {run_id}  ({n} episodes)",
        "",
        f"![chart]({png_name})",
        "",
        "## Aggregate",
        "",
        f"- Episodes:                **{n}**",
        f"- Success rate:            **{sr:.1%}** ({succ}/{n})",
        f"- Avg active-arm best L:   {avg_best_L:.1f} cm",
        f"- Avg rounds / episode:    {avg_rounds:.1f}",
        f"- {std_str}",
        "",
        "## Outcome distribution",
        "",
    ]
    for k, v in outcome_counts.most_common():
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "## Flag distribution", ""])
    if flag_counts:
        for k, v in flag_counts.most_common():
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- (none)")

    lines.extend(["", "## Axis-token usage across all rounds", ""])
    for k in ("x_pos", "x_neg", "y_pos", "y_neg", "z_pos", "z_neg"):
        lines.append(f"- `{k}`: {axis_total.get(k, 0)}")

    lines.extend(["", "## Per-episode detail", "", "| # | id | outcome | rounds | best L (cm) | best R (cm) | final L | final R |",
                  "|---|---|---|---|---|---|---|---|"])
    for i, e in enumerate(eps, 1):
        lines.append(
            f"| {i} | `{e['id']}` | {e['outcome']} | {e['rounds']} | "
            f"{e['best_L_cm']:.1f} | {e['best_R_cm']:.1f} | "
            f"{e['final_L_cm']:.1f} | {e['final_R_cm']:.1f} |"
        )
    out_md.write_text("\n".join(lines) + "\n")


def main() -> None:
    """CLI entry."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=str, required=True)
    parser.add_argument("--replay_root", type=Path, default=Path("data/replays"))
    parser.add_argument("--out_dir", type=Path, required=True)
    parser.add_argument("--snapshot_idx", type=int, required=True,
                        help="Suffix index for snapshot files (e.g. 1 → snapshot_01.{md,png})")
    parser.add_argument("--steps_per_round", type=int, default=30)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    eps = _gather_episodes(args.replay_root / args.run, sim_steps=args.steps_per_round)
    out_png = args.out_dir / f"snapshot_{args.snapshot_idx:02d}.png"
    out_md = args.out_dir / f"snapshot_{args.snapshot_idx:02d}.md"

    _render_png(eps, out_png, args.run)
    _render_md(eps, out_md, args.run, out_png.name)

    succ = sum(1 for e in eps if e["outcome"] == "success")
    logger.info(
        f"snapshot_{args.snapshot_idx:02d}: n={len(eps)} success={succ} "
        f"→ {out_md} + {out_png.name}"
    )


if __name__ == "__main__":
    main()
