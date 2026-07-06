"""Phase 4 D11 blinded rationale audit — Streamlit GUI.

Loads a manifest (from audit_sample.py) and presents one sample at a
time: init-scene image + init pose + rationale text + parsed action.
Labels saved incrementally to a CSV — safe to close the browser and
resume.

Blinded: no arm identifier or run_id shown. Filter verdict is HIDDEN
during audit so the human's decision cannot be biased.

Launch:
    streamlit run scripts/training/audit_gui.py -- \\
        --manifest workspace/d11_audit/manifest.json \\
        --out      workspace/d11_audit/human_labels.csv

Then open http://localhost:8501/
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import streamlit as st

# ─────────────────────────── CLI ───────────────────────────

# Streamlit passes CLI args as `sys.argv` after "--"
_parser = argparse.ArgumentParser()
_parser.add_argument("--manifest", type=Path, required=True)
_parser.add_argument("--out", type=Path, required=True)
_args, _ = _parser.parse_known_args()

MANIFEST_PATH: Path = _args.manifest
OUT_PATH: Path = _args.out


# ─────────────────────────── Persistence ───────────────────────────


def _load_labels() -> dict[int, dict]:
    """Load prior labels keyed by sample_id."""
    if not OUT_PATH.exists():
        return {}
    labels = {}
    with OUT_PATH.open() as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            try:
                sid = int(row["sample_id"])
                labels[sid] = row
            except (ValueError, KeyError):
                continue
    return labels


def _save_label(sample_id: int, ep_id: str, round_idx: int,
                human_label: str, human_notes: str) -> None:
    """Append or replace a label row. Naive: read-all-rewrite-all so
    replacing an existing sample_id works cleanly."""
    labels = _load_labels()
    labels[sample_id] = {
        "sample_id": sample_id,
        "ep_id": ep_id,
        "round_idx": round_idx,
        "human_label": human_label,
        "human_notes": human_notes or "",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=[
            "sample_id", "ep_id", "round_idx", "human_label", "human_notes",
        ])
        writer.writeheader()
        for sid in sorted(labels):
            writer.writerow(labels[sid])


# ─────────────────────────── Text formatting ───────────────────────────


def _split_target(text: str) -> tuple[str, str]:
    """Split target_response into past_lessons block vs teacher's own thought."""
    marker = "PAST_LESSONS (from similar past attempts):"
    if not text.startswith(marker):
        return "", text
    lines = text.split("\n")
    boundary = None
    for i, ln in enumerate(lines):
        if ln.startswith("  (") and "] " in ln:
            boundary = i
    if boundary is None:
        return text, ""
    return "\n".join(lines[: boundary + 1]), "\n".join(lines[boundary + 1:]).lstrip()


# ─────────────────────────── Main app ───────────────────────────


def main() -> None:
    st.set_page_config(page_title="AionGenos D11 Rationale Audit", layout="wide")

    # Load manifest and labels
    if not MANIFEST_PATH.exists():
        st.error(f"Manifest not found: {MANIFEST_PATH}")
        st.stop()

    manifest = json.loads(MANIFEST_PATH.read_text())
    labels = _load_labels()
    total = len(manifest)

    # Session-state cursor — start at the first unlabeled sample
    if "cursor" not in st.session_state:
        first_unlabeled = next(
            (i for i, m in enumerate(manifest) if m["sample_id"] not in labels),
            0,
        )
        st.session_state.cursor = first_unlabeled

    cursor = st.session_state.cursor
    cursor = max(0, min(cursor, total - 1))

    sample = manifest[cursor]
    sid = sample["sample_id"]

    # ─────────── Header ───────────
    st.title("AionGenos — Rationale Audit (blinded)")
    n_labeled = len(labels)
    st.markdown(
        f"**Sample {cursor + 1} / {total}** &nbsp;·&nbsp; "
        f"labeled so far: **{n_labeled} / {total}** "
        f"({100*n_labeled/total:.0f}%)"
    )
    st.progress(n_labeled / total)

    # ─────────── Two-column layout ───────────
    col_img, col_text = st.columns([1, 1])

    with col_img:
        st.subheader("Scene (init frame)")
        img_path = sample.get("image_path")
        if img_path and Path(img_path).exists():
            st.image(img_path, use_container_width=True)
        else:
            st.warning(f"Image missing: {img_path}")

        st.markdown("**Init pose (state)**")
        state = sample.get("state", {})
        st.code(json.dumps({
            "left_ee": state.get("left_ee"),
            "right_ee": state.get("right_ee"),
        }, indent=2), language="json")

        st.markdown("**Action target (parsed)**")
        parsed_left = sample.get("parsed_left_pos") or []
        if parsed_left and len(parsed_left) >= 3 and state.get("left_ee"):
            left_ee = state["left_ee"]
            delta = [parsed_left[i] - left_ee[i] for i in range(3)]
            st.code(
                f"target left_pos = {parsed_left}\n"
                f"           ΔEE = {delta}   ← observed motion",
                language=None,
            )
        else:
            st.code(str(parsed_left), language=None)

    with col_text:
        st.subheader("Rationale (blinded)")
        past, own = _split_target(sample.get("target_response", ""))
        if past:
            with st.expander("PAST_LESSONS prefix (retrieval context — not the sample being audited)", expanded=False):
                st.text(past)
        st.markdown("**Teacher's own THOUGHT — audit this**")
        st.markdown(
            f"<div style='font-family: monospace; font-size: 0.9em; "
            f"white-space: pre-wrap; background: #f5f5f5; padding: 10px; "
            f"border-radius: 5px;'>{own}</div>",
            unsafe_allow_html=True,
        )

        # metadata (non-blinded — outcome is real ground truth, safe to show)
        with st.expander("Metadata", expanded=False):
            st.write({
                "outcome": sample.get("outcome"),
                "kto_label": sample.get("kto_label"),
                # Filter verdict / arm INTENTIONALLY hidden during audit
                # to preserve blinding. Available after label submission
                # only in the post-hoc report.
            })

    # ─────────── Labeling UI ───────────
    st.markdown("---")
    st.subheader("Your judgment")

    st.markdown(
        "Rate whether **the teacher's own THOUGHT** (not the PAST_LESSONS prefix) "
        "is a coherent, grounded rationale for the action shown. Ignore whether "
        "the action itself was successful; you're grading the rationale-action fit."
    )
    st.markdown(
        "- **Clearly good**: the rationale describes a plausible reason for the "
        "specific action taken, references spatial/geometric facts, and the "
        "claimed direction matches ΔEE.\n"
        "- **Clearly bad**: the rationale is either boilerplate/fluff, "
        "contradicts the action's direction, or claims something visibly "
        "wrong about the scene.\n"
        "- **Borderline**: partially grounded but ambiguous; you could argue "
        "either way."
    )

    # Load existing label if any
    prior = labels.get(sid)
    prior_label = prior["human_label"] if prior else ""
    prior_notes = prior["human_notes"] if prior else ""

    label_choice = st.radio(
        "Label",
        options=["clearly good", "clearly bad", "borderline"],
        index=(
            ["clearly good", "clearly bad", "borderline"].index(prior_label)
            if prior_label in ("clearly good", "clearly bad", "borderline")
            else 0
        ),
        horizontal=True,
        key=f"label_{sid}",
    )
    notes = st.text_input(
        "Notes (optional)",
        value=prior_notes,
        key=f"notes_{sid}",
    )

    col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 1])
    with col_a:
        if st.button("◀ Prev", use_container_width=True):
            st.session_state.cursor = max(0, cursor - 1)
            st.rerun()
    with col_b:
        if st.button("💾 Save", use_container_width=True, type="primary"):
            _save_label(sid, sample["ep_id"], sample["round_idx"],
                        label_choice, notes)
            st.session_state.cursor = min(total - 1, cursor + 1)
            st.rerun()
    with col_c:
        if st.button("Save & Next ▶", use_container_width=True):
            _save_label(sid, sample["ep_id"], sample["round_idx"],
                        label_choice, notes)
            st.session_state.cursor = min(total - 1, cursor + 1)
            st.rerun()
    with col_d:
        if st.button("Skip ▶", use_container_width=True):
            st.session_state.cursor = min(total - 1, cursor + 1)
            st.rerun()

    if prior_label:
        st.caption(f"You previously labeled this as: **{prior_label}**")


if __name__ == "__main__":
    main()
