"""Phase 4 D11 pre-registered rationale-quality filter.

Three deterministic rules applied to the teacher's own THOUGHT block
(NOT the PAST_LESSONS prefix — that's retrieval context, not this sample's
first-person reasoning):

  Rule 1: Direction consistency
    For each of X, Y, Z axes:
      - Parse spatial claim from THOUGHT text (which axis + which direction)
      - Compute observed ΔEE on that axis (parsed_left_pos − init pose)
      - Apply DEAD_BAND_CM = 1.0 cm (reused from stage3_critic)
      - If any axis has a stated direction AND |ΔEE| ≥ dead-band AND signs
        disagree → REJECT ("direction inconsistent")

  Rule 2: GT geometric consistency
    Using ground-truth cube position from replay schema, check whether the
    rationale's claim about the cube's position relative to the EE matches
    reality. Applied for parseable claims only.

  Rule 3: Vacuity check
    THOUGHT must contain at least one parseable spatial token from:
      - axis name with sign or direction
      - distance value with unit (cm or grid units)
      - named landmark with directional preposition

    Otherwise REJECT ("vacuous").

Usage:
    python3 filter_rationale_deterministic.py \
        --in  data/training_sets/v4_sft_A.jsonl \
        --out data/training_sets/v4_sft_A.filtered.jsonl \
        --replay_root data/replays

Output JSONL keeps only samples that PASS all three rules. A companion
CSV `<out>.reasons.csv` records per-sample rule outcomes for the human
audit step.

DESIGN CONSTRAINTS (pre-registered — do not modify without amendment):
  - The dead-band constant equals CRITIC_PROGRESS_DEAD_BAND_CM = 1.0 cm.
  - Only the teacher's own THOUGHT is audited (the PAST_LESSONS prefix
    is retrieval context, not this sample's causal reasoning).
  - Applied symmetrically to every rationale-bearing arm's training set.
  - GT cube position is used only offline for curation; the student
    never sees it (observable-only invariant preserved).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────── Constants ───────────────────────────

DEAD_BAND_CM = 1.0  # matches aiongenos/vlm/prompts.py CRITIC_PROGRESS_DEAD_BAND_CM

# Directional term → (axis, sign) mapping, in the AionGenos coordinate
# convention (see aiongenos/config.py workspace_bounds and F60/F62/F65
# analysis notes):
#   X: horizontal, right-positive from robot POV
#   Y: forward (depth), forward-positive
#   Z: vertical, up-positive
#
# NOTE: "left/right" from robot POV maps to X's sign; adjust convention here
# if the env changes. We derived this from D6 baseline analysis where
# "cube to the left" corresponded to smaller X in success episodes.
_DIRECTION_TERMS: dict[str, tuple[str, int]] = {
    # explicit axis+sign
    "positive x": ("x", +1), "+x direction": ("x", +1), "increase x": ("x", +1),
    "negative x": ("x", -1), "-x direction": ("x", -1), "decrease x": ("x", -1),
    "positive y": ("y", +1), "+y direction": ("y", +1), "increase y": ("y", +1),
    "negative y": ("y", -1), "-y direction": ("y", -1), "decrease y": ("y", -1),
    "positive z": ("z", +1), "+z direction": ("z", +1), "increase z": ("z", +1),
    "negative z": ("z", -1), "-z direction": ("z", -1), "decrease z": ("z", -1),
    # colloquial spatial words → axis mapping
    "to the left": ("x", -1),   "further left": ("x", -1),
    "to the right": ("x", +1),  "further right": ("x", +1),
    "forward": ("y", +1),       "further forward": ("y", +1),
    "backward": ("y", -1),      "further back": ("y", -1),
    "closer to the robot": ("y", -1), "further from the robot": ("y", +1),
    "higher": ("z", +1),        "up": ("z", +1),          "above": ("z", +1),
    "lower": ("z", -1),         "down": ("z", -1),        "below": ("z", -1),
}

# Vacuity: at least ONE of these patterns must appear anywhere in THOUGHT.
_VACUITY_PATTERNS = [
    re.compile(r"\b[XYZxyz]\s*=\s*[-+]?\d+"),          # X=15 style
    re.compile(r"\b[XYZxyz]\s*-?\s*axis", re.IGNORECASE),   # X-axis, y axis
    re.compile(r"\b\d+(?:\.\d+)?\s*cm", re.IGNORECASE),    # 5cm, 12.3 cm
    re.compile(r"\bgrid\b", re.IGNORECASE),               # "grid units"
]
# Directional term keys are also vacuity-satisfying.
_VACUITY_TERM_HITS = re.compile(
    r"\b(left|right|forward|backward|closer|further|higher|lower|above|below|up|down|ahead|behind|nearer)\b",
    re.IGNORECASE,
)


# ─────────────────────────── Parsers ───────────────────────────


def split_target_response(text: str) -> tuple[str, str]:
    """Split full target_response into (past_lessons_block, own_thought).

    Structure (produced by prep_training_data.wrap_target_with_rationale):
        PAST_LESSONS (from similar past attempts):
          (1) [...] <lesson_1>
          (2) [...] <lesson_2>
          (3) [...] <lesson_3>
        <blank line>
        <teacher's raw full_response — starts with the actual THOUGHT>

    If no PAST_LESSONS prefix, the entire target is treated as own thought.
    """
    marker = "PAST_LESSONS (from similar past attempts):"
    if not text.startswith(marker):
        return "", text
    # Find first blank-line separator after the (3) lesson.
    # The gist ends with `(N) [...] ...` followed by "\n\n"
    lines = text.split("\n")
    # Find last line that begins with "  (N) [" and after that we split
    boundary = None
    for i, ln in enumerate(lines):
        if ln.startswith("  (") and "] " in ln:
            boundary = i
    if boundary is None:
        return text, ""
    past = "\n".join(lines[: boundary + 1])
    own = "\n".join(lines[boundary + 1 :]).lstrip()
    return past, own


def parse_action_target(own_thought: str) -> Optional[dict]:
    """Extract LEFT_TARGET_POS X Y Z + RIGHT_TARGET_POS X Y Z from thought."""
    def _grab(prefix: str) -> Optional[tuple[int, int, int]]:
        pat = re.compile(
            re.escape(prefix) + r"[^X]*X\s*=\s*(-?\d+)\s+Y\s*=\s*(-?\d+)\s+Z\s*=\s*(-?\d+)",
            re.IGNORECASE,
        )
        m = pat.search(own_thought)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2)), int(m.group(3))

    left = _grab("LEFT_TARGET_POS")
    right = _grab("RIGHT_TARGET_POS")
    if left is None:
        return None
    return {"left": left, "right": right}


# Sentence classifier — past reference vs current intent vs neutral.
#
# Rationale: Rule 1 v1 pooled all direction words across the whole thought,
# causing false positives when the teacher references past actions
# ("The previous move went further left — I need to shift right"). The
# audit v2 exposed this: success × inconsistent stratum agreement = 0%,
# all 10 FN cases traced to past-reference direction words polluting the
# claimed-signs set. Amendment 4 (2026-07-07): only extract direction
# claims from sentences classified as current-intent OR neutral. Past-
# reference sentences are excluded from the sign pool.
_PAST_REF_MARKERS = re.compile(
    r"\b("
    r"previous(?:ly)?|last (?:round|move|step)|"
    r"regression|resulted (?:in|from)|caused a regression|"
    r"moved too|overshot|landed at|had moved|had been|"
    r"went (?:too|further)|used to be|was (?:too )?(?:far|close)|"
    r"trend(?:s|ed)? (?:show|toward)|indicate[ds]?|suggest(?:ed|s)? (?:that )?"
    r")\b",
    re.IGNORECASE,
)

_INTENT_MARKERS = re.compile(
    r"\b("
    r"I (?:will|need to|should|must|plan to|intend to|would|am going to)|"
    r"(?:will|to) (?:target|move|adjust|shift|pull|nudge|push|lift|lower|raise|"
    r"decrease|increase|reduce|maintain|keep|correct|close|reach|align|"
    r"try|attempt|reposition|approach|continue|reverse|change|apply|make|"
    r"place|drive|command|set|update|hold|steer|guide)|"
    r"(?:in order|so as) to|to (?:correct|close|reach|fix|address|avoid)|"
    r"the (?:next|proposed|new) (?:target|move|position|action)|"
    r"my (?:new|next|proposed) (?:target|action|move|plan)"
    r")\b",
    re.IGNORECASE,
)


def classify_sentence(sent: str) -> str:
    """Return 'past', 'intent', or 'neutral'.

    A sentence is 'past' if it matches _PAST_REF_MARKERS AND does NOT
    match _INTENT_MARKERS. This handles compound sentences like
    "the previous move regressed, so I will shift right" — those get
    classified as intent (they carry current plan info even if they
    also reference the past).
    """
    has_intent = bool(_INTENT_MARKERS.search(sent))
    if has_intent:
        return "intent"
    if _PAST_REF_MARKERS.search(sent):
        return "past"
    return "neutral"


def _split_sentences(text: str) -> list[str]:
    """Split thought text into sentences. Naive but adequate — the model's
    output is bounded, structured English."""
    # Split on sentence-ending punctuation followed by space/newline.
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def collect_direction_claims(own_thought: str) -> list[tuple[str, int, str]]:
    """Return list of (axis, sign, matched_phrase) from current-intent
    sentences only. Past-reference and neutral sentences are excluded.

    Amendment 4 v2 (2026-07-07): neutral sentences also excluded.
    Rationale: neutral sentences typically describe visual observation
    ("EE is to the left of cube") which is a fact about the current
    state, not a claim about which direction the action will move.
    Pooling those direction words with intent-declared directions
    caused Rule 1 to see "both signs claimed" and mis-flag as
    inconsistent. Intent-only extraction fixes 4 of 10 audit FN cases
    directly and further audit will show whether it's enough.
    """
    hits: list[tuple[str, int, str]] = []
    for sent in _split_sentences(own_thought):
        cls = classify_sentence(sent)
        if cls != "intent":
            continue
        text_lower = sent.lower()
        for phrase, (axis, sign) in _DIRECTION_TERMS.items():
            # naive substring but word-boundary at the ends
            # (e.g. "left" shouldn't fire inside "leftmost")
            # Only apply word-boundary to alphabetic terms.
            if phrase.replace(" ", "").isalpha() and len(phrase) < 15:
                pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
                if pat.search(text_lower):
                    hits.append((axis, sign, phrase))
            else:
                if phrase in text_lower:
                    hits.append((axis, sign, phrase))
    return hits


# ─────────────────────────── Rules ───────────────────────────


@dataclass
class FilterVerdict:
    keep: bool
    rule_1_direction: str  # "pass", "no_claim_parseable", "inconsistent", "consistent"
    rule_2_gt: str         # "pass", "no_claim_parseable", "gt_missing", "contradicts_gt", "consistent_with_gt"
    rule_3_vacuity: str    # "pass_has_spatial_token", "vacuous_no_spatial_token"
    reject_reason: Optional[str]
    debug: dict


def rule_1_direction(
    own_thought: str,
    parsed_left: Optional[tuple[int, int, int]],
    init_left: tuple[int, int, int],
) -> tuple[str, dict]:
    """Rule 1 — direction consistency with dead-band.

    Relaxed formulation to handle the common pattern where the teacher's
    thought discusses both past mistakes ("moving further left was wrong")
    and current intent ("I will shift back to the right"). Both signs will
    appear in the text.

    Decision:
      - For each axis where |ΔEE| ≥ dead-band, we require that AT LEAST
        ONE claimed direction on that axis matches the observed sign.
      - If any claims exist for that axis AND none of them match the
        observed sign → reject as "direction inconsistent" (this is the
        strong case: teacher never acknowledged the direction they're
        actually moving).
      - If claims exist AND at least one matches → pass (the rationale
        does describe the action, even if it also references past
        counter-examples).
    """
    if parsed_left is None:
        return "no_claim_parseable", {"reason": "no action available"}

    delta = tuple(parsed_left[i] - init_left[i] for i in range(3))
    axes = ("x", "y", "z")
    delta_dict = dict(zip(axes, delta))

    claims = collect_direction_claims(own_thought)
    if not claims:
        return "no_claim_parseable", {"delta": delta_dict}

    # Aggregate per-axis claimed signs (as a set — order doesn't matter).
    claimed: dict[str, set[int]] = {"x": set(), "y": set(), "z": set()}
    for axis, sign, _ in claims:
        claimed[axis].add(sign)

    inconsistent_axes: list[str] = []
    for axis in axes:
        if not claimed[axis]:
            continue
        observed = delta_dict[axis]
        # Dead-band gate — small ΔEE is noise, no direction judgment.
        if abs(observed) < DEAD_BAND_CM:
            continue
        observed_sign = 1 if observed > 0 else -1
        # PASS if observed_sign appears among claimed signs.
        if observed_sign not in claimed[axis]:
            inconsistent_axes.append(axis)

    if inconsistent_axes:
        return "inconsistent", {
            "axes": inconsistent_axes,
            "claims_by_axis": {a: sorted(claimed[a]) for a in axes if claimed[a]},
            "delta": delta_dict,
        }
    return "consistent", {
        "delta": delta_dict,
        "claims_by_axis": {a: sorted(claimed[a]) for a in axes if claimed[a]},
    }


def rule_2_gt_geometry(
    own_thought: str,
    init_left: tuple[int, int, int],
    gt_cube_pos: Optional[tuple[float, float, float]],
) -> tuple[str, dict]:
    """Rule 2 — GT geometric consistency.

    Checks statements about the CUBE's position relative to the EE.
    We only parse claims of the form:
      - "cube is to the left/right of ..."
      - "cube is further forward/back ..."
      - "cube is higher/lower ..."
    against the actual sign of (gt_cube − init_ee) on the relevant axis.
    """
    if gt_cube_pos is None:
        return "gt_missing", {}

    # gt_cube_pos in world/base coords. init_left is integer grid.
    # For sign comparison we only need direction (cube_axis − ee_axis) sign.
    # Both live in the same normalized grid convention per config.py, so
    # sign comparison is direct.
    ee = init_left
    cube = gt_cube_pos

    # Simple claim patterns about the cube:
    text_lower = own_thought.lower()

    cube_claim_patterns: list[tuple[re.Pattern, str, int]] = [
        # (pattern, axis, sign_relative_to_ee)
        # "cube is to the left of" → cube_x < ee_x → cube - ee sign is -1
        (re.compile(r"cube\s+(?:is\s+)?(?:located\s+)?(?:to\s+the\s+)?left\s+of", re.IGNORECASE), "x", -1),
        (re.compile(r"cube\s+(?:is\s+)?(?:located\s+)?(?:to\s+the\s+)?right\s+of", re.IGNORECASE), "x", +1),
        (re.compile(r"cube\s+(?:is\s+)?(?:further\s+)?forward", re.IGNORECASE), "y", +1),
        (re.compile(r"cube\s+(?:is\s+)?(?:further\s+)?back", re.IGNORECASE), "y", -1),
        (re.compile(r"cube\s+(?:is\s+)?higher", re.IGNORECASE), "z", +1),
        (re.compile(r"cube\s+(?:is\s+)?lower", re.IGNORECASE), "z", -1),
    ]

    axis_idx = {"x": 0, "y": 1, "z": 2}
    claim_count = 0
    for pat, axis, claimed_sign in cube_claim_patterns:
        if pat.search(text_lower):
            claim_count += 1
            gt_delta = cube[axis_idx[axis]] - ee[axis_idx[axis]]
            if abs(gt_delta) < DEAD_BAND_CM:
                continue  # near-equal; can't judge
            gt_sign = 1 if gt_delta > 0 else -1
            if gt_sign != claimed_sign:
                return "contradicts_gt", {
                    "axis": axis,
                    "claim_sign": claimed_sign,
                    "gt_delta": gt_delta,
                    "cube": list(cube),
                    "ee_init": list(ee),
                }

    if claim_count == 0:
        return "no_claim_parseable", {}
    return "consistent_with_gt", {"n_claims": claim_count}


def rule_3_vacuity(own_thought: str) -> tuple[str, dict]:
    """Rule 3 — vacuity check."""
    for pat in _VACUITY_PATTERNS:
        if pat.search(own_thought):
            return "pass_has_spatial_token", {"matched": pat.pattern}
    if _VACUITY_TERM_HITS.search(own_thought):
        return "pass_has_spatial_token", {"matched": "colloquial_direction_term"}
    return "vacuous_no_spatial_token", {}


def apply_filter(
    sample: dict,
    gt_lookup: dict[str, tuple[float, float, float]],
    drop_policy: str = "strict",
) -> FilterVerdict:
    """Run all three rules on one sample.

    drop_policy:
      - "strict"        : any rule violation drops the sample. Used for SFT
                          and KTO desirable (bad rationale + good result is
                          exactly the "correct outcome, wrong reason" case
                          that KTO would bake in as "this reasoning is good"
                          — must be filtered).
      - "vacuity_only"  : only Rule 3 (vacuous rationale) drops the sample.
                          Used for KTO undesirable: direction-inconsistent
                          and GT-contradicting rationales paired with bad
                          actions are the highest-value negative examples
                          ("wrong reasoning + wrong action → don't do this")
                          — dropping them would remove the most instructive
                          negative pattern from the KTO reference.
                          Pure vacuous rationales are still dropped because
                          a boilerplate-negative teaches nothing specific.
    """
    if drop_policy not in ("strict", "vacuity_only"):
        raise ValueError(f"unknown drop_policy: {drop_policy}")
    past, own = split_target_response(sample.get("target_response", ""))

    # Action target lives in sample.parsed_left_pos (structured), not in
    # the free-text response — teacher's raw response is pure prose here.
    parsed_left_raw = sample.get("parsed_left_pos")
    parsed_left: Optional[tuple[int, int, int]] = None
    if parsed_left_raw is not None and len(parsed_left_raw) >= 3:
        parsed_left = tuple(int(v) for v in parsed_left_raw[:3])

    state = sample.get("state") or {}
    left_ee = state.get("left_ee") or [0, 0, 0]
    init_left = tuple(int(v) for v in left_ee[:3])

    ep_id = sample.get("ep_id", "")
    gt_cube = gt_lookup.get(ep_id)

    r1_out, r1_debug = rule_1_direction(own, parsed_left, init_left)
    r2_out, r2_debug = rule_2_gt_geometry(own, init_left, gt_cube)
    r3_out, r3_debug = rule_3_vacuity(own)

    reject_reason = None
    if r3_out == "vacuous_no_spatial_token":
        reject_reason = "vacuous"
    elif drop_policy == "strict":
        if r2_out == "contradicts_gt":
            reject_reason = f"gt_contradiction:{r2_debug.get('axis','?')}"
        elif r1_out == "inconsistent":
            axes = r1_debug.get("axes") or [r1_debug.get("axis", "?")]
            reject_reason = f"direction_inconsistent:{','.join(axes)}"

    return FilterVerdict(
        keep=(reject_reason is None),
        rule_1_direction=r1_out,
        rule_2_gt=r2_out,
        rule_3_vacuity=r3_out,
        reject_reason=reject_reason,
        debug={"r1": r1_debug, "r2": r2_debug, "r3": r3_debug,
               "past_len": len(past), "own_len": len(own)},
    )


# ─────────────────────────── GT lookup ───────────────────────────


def build_gt_cube_lookup(replay_root: Path, run_ids: list[str]) -> dict[str, tuple[float, float, float]]:
    """Load per-episode ground-truth cube position from replay JSONs.

    For L0a-Left the red-cube is the target. We look at trajectory[0]
    which stores the initial state's distances and derive cube position
    from that. If the replay stores a scene / goal_pose field, prefer that.

    Returns dict: ep_id (full) → (x, y, z) in the same integer-grid coord
    system as init_L_EE.
    """
    lookup: dict[str, tuple[float, float, float]] = {}
    for run_id in run_ids:
        run_dir = replay_root / run_id
        if not run_dir.exists():
            continue
        for sub in ("success", "failure"):
            subdir = run_dir / sub
            if not subdir.exists():
                continue
            for f in subdir.glob("*.json"):
                try:
                    d = json.loads(f.read_text())
                except json.JSONDecodeError:
                    continue
                ep_id = d.get("episode_id")
                if not ep_id:
                    continue
                # First try metadata.gt_cube_pos or similar; fall back to
                # deriving from the final ep pose (where EE landed = ~cube
                # for success eps only). For robustness use metadata field
                # if present; else use the position of the EE at the round
                # where distance was minimum.
                cube = _extract_cube_from_replay(d)
                if cube is not None:
                    lookup[ep_id] = cube
    return lookup


def _extract_cube_from_replay(replay: dict) -> Optional[tuple[float, float, float]]:
    """Best-effort GT cube position extraction.

    Priority:
      1. replay['metadata']['gt_cube_pos'] if present.
      2. Position where active arm was closest to target (min dist), plus
         3D correction using distance-to-target: not trivially recoverable
         without geometry. Fall back to EE pose at min-distance-timestamp
         (accurate within success threshold ≈ 5cm for successful eps).

    Anything better would require access to the IsaacLab scene metadata.
    """
    meta = replay.get("metadata") or {}
    if isinstance(meta, dict):
        gt = meta.get("gt_cube_pos") or meta.get("red_cube_pos")
        if gt and len(gt) >= 3:
            return (float(gt[0]), float(gt[1]), float(gt[2]))

    # Fallback: find timestep with min dist_red, take EE at that timestep
    # as a cube-position proxy (accurate to within success threshold).
    traj = replay.get("trajectory") or []
    if not traj:
        return None
    best_i = None
    best_d = float("inf")
    for i, ts in enumerate(traj):
        d = (ts.get("distances") or {}).get("dist_red")
        if d is None:
            continue
        if d < best_d:
            best_d = d
            best_i = i
    if best_i is None:
        return None
    left = traj[best_i].get("left_ee_pos")
    if not left:
        return None
    # This is only an approximation — accuracy = success threshold ≈ 5cm.
    # Rule 2 uses sign comparison + dead-band, so approx is acceptable
    # for the tail of parseable claims. Flag this in the reject_reason
    # by tagging it "gt_approx" via a wrapper.
    return (float(left[0]), float(left[1]), float(left[2]))


# ─────────────────────────── Main ───────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", type=Path, required=True,
                        help="Input JSONL to filter.")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output filtered JSONL.")
    parser.add_argument("--replay_root", type=Path, default=Path("data/replays"),
                        help="Replay root for GT cube position lookup.")
    parser.add_argument(
        "--drop_policy",
        default="strict",
        choices=("strict", "vacuity_only", "asymmetric_kto"),
        help="How to decide drop. "
             "strict = any rule violation drops (use for SFT + KTO desirable-only files); "
             "vacuity_only = only Rule 3 drops (use for KTO undesirable-only files); "
             "asymmetric_kto = per-sample: kto_label=desirable → strict, "
             "kto_label=undesirable → vacuity_only. Used when passing the "
             "full mixed KTO JSONL in one call.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load all samples and collect run_ids for GT lookup.
    samples: list[dict] = []
    run_ids: set[str] = set()
    with args.in_path.open() as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            s = json.loads(line)
            samples.append(s)
            if "run_id" in s:
                run_ids.add(s["run_id"])
    logger.info(f"Loaded {len(samples)} samples spanning {len(run_ids)} runs")
    logger.info(f"Drop policy: {args.drop_policy}")

    gt_lookup = build_gt_cube_lookup(args.replay_root, list(run_ids))
    logger.info(f"GT cube lookup built for {len(gt_lookup)} episodes")

    # Apply filter.
    from collections import Counter
    n_pass = 0
    n_pass_desirable = 0
    n_pass_undesirable = 0
    n_input_desirable = 0
    n_input_undesirable = 0
    reason_counter: Counter = Counter()
    rule_stats = {"r1": Counter(), "r2": Counter(), "r3": Counter()}
    # 2×2 free by-product: rule-1-consistency × outcome
    consist_outcome_2x2: Counter = Counter()  # (r1_verdict, outcome) → count

    args.out.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.out.with_suffix(args.out.suffix + ".reasons.csv")

    with args.out.open("w") as out_fp, csv_path.open("w", newline="") as csv_fp:
        writer = csv.writer(csv_fp)
        writer.writerow([
            "ep_id", "run_id", "round_idx", "kto_label", "outcome", "keep",
            "rule_1_direction", "rule_2_gt", "rule_3_vacuity",
            "reject_reason", "r1_debug", "r2_debug", "r3_debug",
        ])
        for s in samples:
            kto_label = s.get("kto_label")
            outcome = s.get("outcome", "?")
            # Decide per-sample policy under asymmetric_kto.
            if args.drop_policy == "asymmetric_kto":
                if kto_label == "desirable":
                    policy = "strict"
                elif kto_label == "undesirable":
                    policy = "vacuity_only"
                else:
                    # Rows without kto_label (shouldn't happen after Option C+
                    # prep, but be safe) — default to strict.
                    policy = "strict"
            else:
                policy = args.drop_policy

            v = apply_filter(s, gt_lookup, drop_policy=policy)
            rule_stats["r1"][v.rule_1_direction] += 1
            rule_stats["r2"][v.rule_2_gt] += 1
            rule_stats["r3"][v.rule_3_vacuity] += 1
            consist_outcome_2x2[(v.rule_1_direction, outcome)] += 1

            if kto_label == "desirable":
                n_input_desirable += 1
                if v.keep:
                    n_pass_desirable += 1
            elif kto_label == "undesirable":
                n_input_undesirable += 1
                if v.keep:
                    n_pass_undesirable += 1

            if v.keep:
                n_pass += 1
                out_fp.write(json.dumps(s) + "\n")
            else:
                reason_counter[v.reject_reason or "unknown"] += 1
            writer.writerow([
                s.get("ep_id", ""), s.get("run_id", ""), s.get("round_idx", 0),
                kto_label or "", outcome,
                v.keep,
                v.rule_1_direction, v.rule_2_gt, v.rule_3_vacuity,
                v.reject_reason or "",
                json.dumps(v.debug["r1"], default=str),
                json.dumps(v.debug["r2"], default=str),
                json.dumps(v.debug["r3"], default=str),
            ])

    logger.info("")
    logger.info(f"Kept: {n_pass}/{len(samples)} ({100 * n_pass / max(1, len(samples)):.1f}%)")
    if n_input_desirable or n_input_undesirable:
        d_rate = 100 * n_pass_desirable / max(1, n_input_desirable)
        u_rate = 100 * n_pass_undesirable / max(1, n_input_undesirable)
        logger.info(
            f"  desirable:   kept {n_pass_desirable}/{n_input_desirable} ({d_rate:.1f}%)"
        )
        logger.info(
            f"  undesirable: kept {n_pass_undesirable}/{n_input_undesirable} ({u_rate:.1f}%)"
        )
        # Class-imbalance drift into --auto-balance
        if n_pass_desirable and n_pass_undesirable:
            pre_ratio = n_input_undesirable / max(1, n_input_desirable)
            post_ratio = n_pass_undesirable / max(1, n_pass_desirable)
            logger.info(
                f"  KTO class ratio (undesirable:desirable): "
                f"pre-filter {pre_ratio:.2f} → post-filter {post_ratio:.2f}"
            )
            logger.info(
                "  NOTE: train_qlora_kto.py --auto-balance recomputes lambdas "
                "from dataset.examples after load, so the post-filter ratio "
                "will be used automatically. No manual adjustment needed."
            )

    logger.info(f"Dropped by reason:")
    for reason, count in reason_counter.most_common():
        logger.info(f"  {reason}: {count}")
    logger.info("")
    logger.info(f"Rule 1 (direction) outcomes:  {dict(rule_stats['r1'])}")
    logger.info(f"Rule 2 (GT geometry) outcomes: {dict(rule_stats['r2'])}")
    logger.info(f"Rule 3 (vacuity) outcomes:    {dict(rule_stats['r3'])}")

    # Free by-product: rule-1-consistency × outcome 2×2
    logger.info("")
    logger.info("Rule-1 consistency × episode outcome (for Discussion):")
    consistency_states = ("consistent", "inconsistent", "no_claim_parseable")
    outcomes = sorted({k[1] for k in consist_outcome_2x2})
    header = "  " + " ".join(f"{o:>14s}" for o in ["r1_state"] + outcomes)
    logger.info(header)
    for st in consistency_states:
        row = [f"{st:>14s}"]
        for o in outcomes:
            row.append(f"{consist_outcome_2x2[(st, o)]:>14d}")
        logger.info("  " + " ".join(row))

    logger.info(f"")
    logger.info(f"Wrote filtered JSONL → {args.out}")
    logger.info(f"Wrote per-sample reasons → {csv_path}")


if __name__ == "__main__":
    main()
