"""Render a training-run snapshot (markdown + loss curve PNG).

Parses the stdout log of ``server_side/train_qlora_gemma4.py`` and produces:

  data/training_snapshots/<run_id>/loss_curve.png   – loss / grad_norm / lr per step
  data/training_snapshots/<run_id>/report.md        – human readable summary

The trainer prints lines like::

    {'loss': '2.14', 'grad_norm': '199.5', 'learning_rate': '0', 'epoch': '0.3636'}
    {'train_runtime': '46.46', 'train_samples_per_second': '0.473', ...}

We grep those and turn them into structured data without re-running the trainer.

Usage:
    python3 scripts/diagnostics/training_snapshot.py \\
        --run RUN_ID --log_path LOCAL_OR_REMOTE_LOG --base_model NAME [--n_samples N]
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


_STEP_LINE = re.compile(r"\{('loss'|\"loss\")[^}]+\}")
_FINAL_LINE = re.compile(r"\{('train_runtime'|\"train_runtime\")[^}]+\}")


def _parse_dict_line(line: str) -> dict:
    """Trainer prints python-repr dicts (single quotes). ast.literal_eval handles them."""
    # Crop to the {...} block
    start = line.find("{")
    end = line.rfind("}")
    if start < 0 or end < 0:
        return {}
    try:
        d = ast.literal_eval(line[start : end + 1])
    except (SyntaxError, ValueError):
        return {}
    # Trainer logs numbers as strings sometimes — coerce
    coerced: dict = {}
    for k, v in d.items():
        if isinstance(v, str):
            try:
                v = float(v) if "." in v or "e" in v.lower() else int(v)
            except ValueError:
                pass
        coerced[k] = v
    return coerced


def _read_log(log_path: str) -> list[str]:
    """Read log lines from local file or remote (`user@host:/path`)."""
    if ":" in log_path and not Path(log_path).exists():
        # Treat as remote — fetch via scp into /tmp
        tmp = f"/tmp/train_log_fetch_{datetime.now().strftime('%H%M%S')}.log"
        subprocess.run(["scp", log_path, tmp], check=True, capture_output=True)
        text = Path(tmp).read_text()
    else:
        text = Path(log_path).read_text()
    return text.splitlines()


def parse_log(log_path: str) -> tuple[list[dict], dict]:
    """Return (per-step records, final-stats dict)."""
    lines = _read_log(log_path)
    steps: list[dict] = []
    final: dict = {}
    for ln in lines:
        if _FINAL_LINE.search(ln):
            final = _parse_dict_line(ln)
        elif _STEP_LINE.search(ln):
            d = _parse_dict_line(ln)
            if "loss" in d:
                steps.append(d)
    return steps, final


def render_png(steps: list[dict], out_png: Path, run_id: str) -> None:
    """Three-panel curve: loss / grad_norm / lr."""
    if not steps:
        logger.info("No step data — skip PNG.")
        return
    xs = [s.get("epoch", i + 1) for i, s in enumerate(steps)]
    loss = [s.get("loss") for s in steps]
    grad = [s.get("grad_norm") for s in steps]
    lr = [s.get("learning_rate") for s in steps]

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    fig.suptitle(f"Training run {run_id}  —  {len(steps)} step(s)")

    axes[0].plot(xs, loss, "o-", color="#1976d2")
    axes[0].set_xlabel("epoch"); axes[0].set_ylabel("loss")
    axes[0].set_title("loss"); axes[0].grid(True, alpha=0.3)

    axes[1].plot(xs, grad, "o-", color="#f57c00")
    axes[1].set_xlabel("epoch"); axes[1].set_ylabel("grad_norm")
    axes[1].set_title("grad_norm"); axes[1].set_yscale("log")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(xs, lr, "o-", color="#2e7d32")
    axes[2].set_xlabel("epoch"); axes[2].set_ylabel("learning rate")
    axes[2].set_title("lr"); axes[2].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def render_md(
    steps: list[dict],
    final: dict,
    run_id: str,
    base_model: str,
    n_samples: int | None,
    out_md: Path,
    png_name: str,
) -> None:
    lines = [
        f"# Training snapshot — {run_id}",
        "",
        f"![curves]({png_name})",
        "",
        "## Configuration",
        "",
        f"- Base model       : `{base_model}`",
        f"- Training samples : {n_samples if n_samples is not None else '?'}",
        f"- Stage            : 4-A (BC with CoT preserved)",
        f"- LoRA rank        : 16 (alpha 32)",
        f"- Optimizer        : AdamW (default Trainer)",
        f"- Trainable params : 122M / 31.4B (≈ 0.39 %)",
        "",
        "## Step-by-step",
        "",
        "| epoch | loss | grad_norm | learning_rate |",
        "|---|---|---|---|",
    ]
    for s in steps:
        lines.append(
            f"| {s.get('epoch', '?'):>4} | {s.get('loss', '?'):>5} | "
            f"{s.get('grad_norm', '?'):>5} | {s.get('learning_rate', '?'):>5} |"
        )
    lines.extend([
        "",
        "## Final stats",
        "",
    ])
    if final:
        for k, v in final.items():
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- (no train_runtime line found)")

    if steps:
        first = steps[0].get("loss")
        last = steps[-1].get("loss")
        if first and last:
            try:
                delta = float(last) - float(first)
                lines.extend([
                    "",
                    "## Loss delta",
                    "",
                    f"- first → last: {first} → {last}  ({delta:+.3f})",
                    f"- relative    : {(delta / float(first)) * 100:+.1f}%",
                ])
            except (TypeError, ValueError):
                pass
    out_md.write_text("\n".join(lines) + "\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="run_id label for output dir")
    parser.add_argument("--log_path", required=True,
                        help="Local path or scp-style remote (user@host:/path) to trainer log")
    parser.add_argument("--base_model", default="(unknown)")
    parser.add_argument("--n_samples", type=int, default=None)
    parser.add_argument("--out_root", type=Path, default=Path("data/training_snapshots"))
    args = parser.parse_args()

    out_dir = args.out_root / args.run
    out_dir.mkdir(parents=True, exist_ok=True)

    steps, final = parse_log(args.log_path)
    logger.info(f"Parsed {len(steps)} steps; final stats keys: {list(final.keys())}")

    png = out_dir / "loss_curve.png"
    md = out_dir / "report.md"
    render_png(steps, png, args.run)
    render_md(steps, final, args.run, args.base_model, args.n_samples, md, png.name)
    logger.info(f"Wrote {md} + {png.name}")


if __name__ == "__main__":
    main()
