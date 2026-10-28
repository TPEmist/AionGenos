"""Unit tests for WP1-3a life window analysis (scripts/analysis/wp3a_life_windows.py).

Spec: docs/p2_prereg/wp3a_push_provenance.md (§ "PRE-REGISTERED before data:
memory time-axis pilot" + "Clarifications").
Authority: PI 2026-10-28.
CPU only.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analysis.wp3a_life_windows import (
    analyze_life_windows,
    calc_slope,
    compute_joint_verdict,
    format_window_table,
    perm_test_slope,
)


def make_synthetic_episode(
    seed: int,
    alpha: float,
    theta: float,
    outcome: str = "push_plateau",
    tcp_cube: Sequence[float] = (0.0, 0.0, 0.0),
    has_contact: bool = False,
    memory_hits: List[Dict[str, Any]] = None,
    empty_rounds: bool = False,
) -> Dict[str, Any]:
    """Helper to create a synthetic episode dict."""
    if empty_rounds:
        return {
            "ep_id": f"ep_{seed}",
            "env_seed": seed,
            "outcome": outcome,
            "rounds": [],
            "round_meta": [],
            "memory_hits": memory_hits or [],
        }

    tx = math.cos(alpha)
    ty = math.sin(alpha)
    gx = math.cos(theta)
    gy = math.sin(theta)

    round_dict = {
        "round": 1,
        "cube_b_pre": list(tcp_cube),
        "goal_b_pre": [gx, gy, 0.0],
        "tcp_target_b": [tx, ty, 0.0],
        "eef_target_int": [int(tx * 100), int(ty * 100), 0],
        "contact": {"first_cube_move": {"anatomy": "finger"} if has_contact else None},
    }

    return {
        "ep_id": f"ep_{seed}",
        "env_seed": seed,
        "outcome": outcome,
        "goal_sample": {"theta": theta},
        "rounds": [round_dict],
        "round_meta": [round_dict],
        "memory_hits": memory_hits or [],
    }


def make_synthetic_window(
    win_idx: int,
    target_circ_corr: float,
    n_episodes: int = 50,
    sr: float = 0.20,
    zero_variance: bool = False,
    empty_rounds: bool = False,
) -> List[Dict[str, Any]]:
    """Create n_episodes with controlled circular correlation and success rate."""
    eps = []
    base_seed = 5000 + (win_idx - 1) * n_episodes
    n_succ = int(round(sr * n_episodes))

    for i in range(n_episodes):
        seed = base_seed + i
        outcome = "success" if i < n_succ else "push_plateau"

        if empty_rounds:
            eps.append(make_synthetic_episode(seed, 0.0, 0.0, outcome=outcome, empty_rounds=True))
            continue

        th = -1.2 + (i / max(n_episodes - 1, 1)) * 2.4

        if zero_variance:
            al = 0.5  # Constant angle -> zero variance
        else:
            # target_circ_corr in [-1, 1]
            # Blend between theta and independent/orthogonal/inverted angle
            al = target_circ_corr * th + (1.0 - abs(target_circ_corr)) * (math.sin(i * 3.7) * 1.2)

        eps.append(make_synthetic_episode(seed, al, th, outcome=outcome))

    return eps


class TestSlopeExactEnumeration:
    """Test 720-enumeration exactness and slope calculations."""

    def test_calc_slope_linear(self):
        x = [1, 2, 3, 4, 5, 6]
        y = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        slope = calc_slope(x, y)
        assert pytest.approx(slope, rel=1e-6) == 0.1

    def test_exact_720_monotone_increasing(self):
        """Spec line 6: 720-enumeration exactness (p for perfectly monotone 6 windows = 2/720)."""
        x = [1, 2, 3, 4, 5, 6]
        y = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60]
        slope, p = perm_test_slope(x, y)
        assert slope > 0
        assert pytest.approx(p, abs=1e-12) == 2.0 / 720.0
        assert p < 0.05

    def test_exact_720_monotone_decreasing(self):
        """Degrade: slope < 0, perfectly monotone yields p = 2/720."""
        x = [1, 2, 3, 4, 5, 6]
        y = [0.60, 0.50, 0.40, 0.30, 0.20, 0.10]
        slope, p = perm_test_slope(x, y)
        assert slope < 0
        assert pytest.approx(p, abs=1e-12) == 2.0 / 720.0
        assert p < 0.05

    def test_exact_720_flat(self):
        x = [1, 2, 3, 4, 5, 6]
        y = [0.30, 0.30, 0.30, 0.30, 0.30, 0.30]
        slope, p = perm_test_slope(x, y)
        assert pytest.approx(slope, abs=1e-12) == 0.0
        assert pytest.approx(p, abs=1e-12) == 1.0

    def test_exact_5_windows(self):
        """When k=5 symmetric, 5! = 120 perms, monotone yields p = 2/120."""
        x = [1, 2, 3, 4, 5]
        y = [0.10, 0.20, 0.30, 0.40, 0.50]
        slope, p = perm_test_slope(x, y)
        assert slope > 0
        assert pytest.approx(p, abs=1e-12) == 2.0 / 120.0

    def test_asymmetric_windows_slope(self):
        """When 1 window is excluded (e.g. x=[1, 2, 4, 5, 6]), test runs exact k! enumeration."""
        x = [1, 2, 4, 5, 6]
        y = [0.10, 0.20, 0.40, 0.50, 0.60]
        slope, p = perm_test_slope(x, y)
        assert slope > 0
        assert pytest.approx(p, abs=1e-12) == 1.0 / 120.0


class TestSyntheticLifeRuns:
    """Synthetic runs with known slopes: climb, plateau, degrade."""

    def test_climb_verdict(self):
        """Climb: slope > 0 with p < 0.05 and window 6 p < 0.05."""
        eps = []
        # Target circular correlations: strictly increasing from 0.05 to 0.95
        corrs = [0.05, 0.20, 0.40, 0.60, 0.80, 0.95]
        for w_idx, corr in enumerate(corrs, 1):
            eps.extend(make_synthetic_window(w_idx, target_circ_corr=corr, sr=0.20))

        res = analyze_life_windows(eps, window_size=50, perm=500, seed=20261026)
        assert res["n_windows"] == 6
        assert res["n_excluded"] == 0
        assert res["trend"]["slope_primary"] > 0
        assert res["trend"]["p_slope_primary"] < 0.05
        # Window 6 within-window p is significant
        assert res["trend"]["win6_p_circ"] is not None
        assert res["trend"]["win6_p_circ"] < 0.05
        assert res["verdict"] == "climb"

    def test_plateau_verdict(self):
        """Plateau: no significant slope."""
        eps = []
        # Target correlations oscillate around 0.20 without trend
        corrs = [0.20, 0.22, 0.19, 0.21, 0.20, 0.21]
        for w_idx, corr in enumerate(corrs, 1):
            eps.extend(make_synthetic_window(w_idx, target_circ_corr=corr, sr=0.20))

        res = analyze_life_windows(eps, window_size=50, perm=500, seed=20261026)
        assert res["n_windows"] == 6
        assert res["verdict"] == "plateau"

    def test_degrade_verdict(self):
        """Degrade: slope < 0 with p < 0.05 (wrong-lesson accumulation)."""
        eps = []
        corrs = [0.95, 0.70, 0.45, 0.20, -0.20, -0.80]
        for w_idx, corr in enumerate(corrs, 1):
            eps.extend(make_synthetic_window(w_idx, target_circ_corr=corr, sr=0.20))

        res = analyze_life_windows(eps, window_size=50, perm=500, seed=20261026)
        assert res["n_windows"] == 6
        assert res["trend"]["slope_primary"] < 0
        assert res["trend"]["p_slope_primary"] < 0.05
        assert res["verdict"] == "degrade"


class TestShortcutVerdict:
    """Shortcut: SR rises significantly (p < 0.05), but primary indicator does not."""

    def test_shortcut_case(self):
        eps = []
        # SR strictly increases: 0.10, 0.20, 0.30, 0.40, 0.50, 0.60
        srs = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60]
        # Primary correlation remains flat / noisy around 0.20
        corrs = [0.20, 0.19, 0.21, 0.20, 0.21, 0.19]
        for w_idx, (sr_val, corr) in enumerate(zip(srs, corrs), 1):
            eps.extend(make_synthetic_window(w_idx, target_circ_corr=corr, sr=sr_val))

        res = analyze_life_windows(eps, window_size=50, perm=500, seed=20261026)
        assert res["n_windows"] == 6
        assert res["trend"]["slope_sr"] > 0
        assert res["trend"]["p_slope_sr"] < 0.05
        # Primary slope is not significant
        assert res["trend"]["p_slope_primary"] >= 0.05 or res["trend"]["slope_primary"] <= 0
        assert res["verdict"] == "shortcut"


class TestNaNWindows:
    """Pre-registered NaN window rule:
    - Window with < 5 valid episodes or zero variance is excluded.
    - Slope computed on remaining windows.
    - If >= 2 windows excluded -> 'uninformative'.
    """

    def test_one_nan_window_excluded(self):
        eps = []
        corrs = [0.10, 0.30, 0.0, 0.50, 0.70, 0.90]
        for w_idx, corr in enumerate(corrs, 1):
            if w_idx == 3:
                # Window 3 has 0 valid episodes (< 5)
                eps.extend(make_synthetic_window(w_idx, target_circ_corr=0.0, empty_rounds=True))
            else:
                eps.extend(make_synthetic_window(w_idx, target_circ_corr=corr, sr=0.20))

        res = analyze_life_windows(eps, window_size=50, perm=500, seed=20261026)
        assert res["n_windows"] == 6
        assert res["n_excluded"] == 1
        assert res["excluded_windows"] == [3]
        assert res["trend"]["n_valid_windows"] == 5
        # Slope is successfully computed on the 5 valid windows
        assert res["trend"]["slope_primary"] is not None
        assert res["trend"]["slope_primary"] > 0
        assert res["verdict"] == "climb"

    def test_two_nan_windows_uninformative(self):
        eps = []
        corrs = [0.10, 0.0, 0.50, 0.0, 0.70, 0.90]
        for w_idx, corr in enumerate(corrs, 1):
            if w_idx in (2, 4):
                # Window 2 and 4 have zero variance
                eps.extend(make_synthetic_window(w_idx, target_circ_corr=0.0, zero_variance=True))
            else:
                eps.extend(make_synthetic_window(w_idx, target_circ_corr=corr, sr=0.20))

        res = analyze_life_windows(eps, window_size=50, perm=500, seed=20261026)
        assert res["n_windows"] == 6
        assert res["n_excluded"] == 2
        assert res["excluded_windows"] == [2, 4]
        assert res["verdict"] == "uninformative"
        assert "≥ 2 windows excluded" in res["verdict_reason"]


class TestJointVerdictRule:
    """Pre-registered two-life joint verdict rule."""

    def test_both_climb(self):
        v, reason = compute_joint_verdict("climb", "climb")
        assert v == "climb"

    def test_both_degrade(self):
        v, reason = compute_joint_verdict("degrade", "degrade")
        assert v == "degrade"

    def test_climb_not_reproduced(self):
        v, reason = compute_joint_verdict("climb", "plateau")
        assert v == "not reproduced"
        v, reason = compute_joint_verdict("plateau", "climb")
        assert v == "not reproduced"

    def test_degrade_not_reproduced(self):
        v, reason = compute_joint_verdict("degrade", "plateau")
        assert v == "not reproduced"
        v, reason = compute_joint_verdict("plateau", "degrade")
        assert v == "not reproduced"

    def test_both_plateau(self):
        v, reason = compute_joint_verdict("plateau", "plateau")
        assert v == "plateau"

    def test_both_shortcut(self):
        v, reason = compute_joint_verdict("shortcut", "shortcut")
        assert v == "shortcut"

    def test_uninformative_in_joint(self):
        v, reason = compute_joint_verdict("uninformative", "climb")
        assert v == "uninformative"
        v, reason = compute_joint_verdict("climb", "uninformative")
        assert v == "uninformative"


class TestExistingRun3786f4e5:
    """Spec line 6: run on existing run 3786f4e5 (50 eps -> 1 window -> expect uninformative)."""

    def test_run_3786f4e5_analysis(self):
        smoke_file = ROOT / "logs/push_smoke_3786f4e5.json"
        if not smoke_file.exists():
            smoke_file = Path("/home/control/AionGenos/logs/push_smoke_3786f4e5.json")
        assert smoke_file.exists(), f"Could not find {smoke_file}"

        data = json.load(smoke_file.open())
        eps = data["episodes"]

        recap_root = Path("/home/control/AionGenos/workspace/recaps_push_rung1p_p4c_lesson")
        lessons = {}
        ep_ids = set()
        if (recap_root / "3786f4e5").is_dir():
            for p in (recap_root / "3786f4e5").glob("*.json"):
                d = json.loads(p.read_text())
                eid = d.get("ep_id") or p.stem
                ep_ids.add(eid)
                lesson = d.get("text_lesson") or d.get("lesson") or ""
                if lesson:
                    lessons[eid] = lesson

        res = analyze_life_windows(
            eps,
            window_size=50,
            perm=1000,
            seed=20261026,
            lessons=lessons,
            recap_ep_ids=ep_ids,
            run_id="3786f4e5",
        )

        assert res["n_episodes"] == 50
        assert res["n_windows"] == 1
        assert res["verdict"] == "uninformative"
        assert "insufficient valid windows" in res["verdict_reason"]

        w1 = res["windows"][0]
        assert w1["window"] == 1
        assert w1["n_episodes"] == 50
        assert w1["n_success"] == 13
        assert pytest.approx(w1["sr"], abs=1e-3) == 0.260
        assert pytest.approx(w1["circ_corr"], abs=1e-3) == 0.172
        assert w1["unique_r1_targets"] == 42
        assert w1["buffer_size_start"] == 0
        assert pytest.approx(w1["retrieval_hit_rate"], abs=1e-3) == 0.667
        assert w1["confab_count"] == 5
        assert pytest.approx(w1["confab_rate"], abs=1e-3) == 0.333

        # Test table formatting
        tbl = format_window_table(res)
        assert "3786f4e5" in tbl
        assert "uninformative" in tbl

    def test_cli_execution_3786f4e5(self):
        script_path = ROOT / "scripts/analysis/wp3a_life_windows.py"
        cmd = [sys.executable, str(script_path), "3786f4e5", "--perm", "100"]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env={"CUDA_VISIBLE_DEVICES": ""})
        assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
        assert "Verdict: uninformative" in proc.stdout
        out_json = ROOT / "logs/life_windows_3786f4e5.json"
        assert out_json.exists()
        d = json.loads(out_json.read_text())
        assert d["run_id"] == "3786f4e5"
        assert d["verdict"] == "uninformative"
