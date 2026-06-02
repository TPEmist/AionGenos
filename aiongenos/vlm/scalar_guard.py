"""Scalar Guard — Normalized integer grid conversion.

All VLM I/O uses integer coordinates in [-100, 100]. This module is the single
source of truth for metric ↔ integer conversions (position and RPY).

Rules (from plan §4):
- LLM never sees any decimal point.
- Position axes map task workspace metric bounds → [-100, 100].
- RPY axes: Roll/Yaw map [-π, π] → [-100, 100]; Pitch maps [-π/2, π/2] → [-100, 100].
- Out-of-range values are clamped and flagged.
- |Pitch| > 80 triggers near_singularity flag.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

# ──────────────────────────── Constants ────────────────────────────

INT_MIN = -100
INT_MAX = 100

RPY_RANGES = {
    "roll": (-math.pi, math.pi),
    "pitch": (-math.pi / 2, math.pi / 2),
    "yaw": (-math.pi, math.pi),
}

NEAR_SINGULARITY_PITCH_THRESHOLD = 80  # integer units


# ──────────────────────────── Flags ────────────────────────────────

@dataclass
class ConversionFlags:
    """Flags produced during conversion."""

    clamped: bool = False
    out_of_workspace: bool = False
    near_singularity: bool = False


# ──────────────────────── Position helpers ─────────────────────────

def metric_to_int(
    value: float,
    bounds: Tuple[float, float],
) -> Tuple[int, ConversionFlags]:
    """Convert a metric-space coordinate to normalized integer [-100, 100].

    Args:
        value: Metric-space coordinate (meters).
        bounds: (min, max) metric bounds for this axis from task config.

    Returns:
        Tuple of (integer value, conversion flags).
    """
    lo, hi = bounds
    flags = ConversionFlags()

    if hi <= lo:
        raise ValueError(f"Invalid bounds: {bounds}")

    # Normalize to [0, 1]
    normalized = (value - lo) / (hi - lo)

    # Map to [-100, 100]
    raw = normalized * (INT_MAX - INT_MIN) + INT_MIN

    # Clamp
    if raw < INT_MIN or raw > INT_MAX:
        flags.clamped = True
        flags.out_of_workspace = True

    clamped_val = max(INT_MIN, min(INT_MAX, raw))
    return round(clamped_val), flags


def int_to_metric(
    value: int,
    bounds: Tuple[float, float],
) -> float:
    """Convert a normalized integer [-100, 100] back to metric-space coordinate.

    Args:
        value: Integer coordinate in [-100, 100].
        bounds: (min, max) metric bounds for this axis.

    Returns:
        Metric-space value (meters).
    """
    lo, hi = bounds

    if hi <= lo:
        raise ValueError(f"Invalid bounds: {bounds}")

    # Clamp input
    clamped_val = max(INT_MIN, min(INT_MAX, value))

    # Map from [-100, 100] → [0, 1] → [lo, hi]
    normalized = (clamped_val - INT_MIN) / (INT_MAX - INT_MIN)
    return lo + normalized * (hi - lo)


# ──────────────────────── RPY helpers ──────────────────────────────

def rpy_rad_to_int(
    roll: float,
    pitch: float,
    yaw: float,
) -> Tuple[Tuple[int, int, int], ConversionFlags]:
    """Convert RPY in radians to normalized integers [-100, 100].

    Roll/Yaw: [-π, π] → [-100, 100]
    Pitch: [-π/2, π/2] → [-100, 100]

    Args:
        roll: Roll angle in radians.
        pitch: Pitch angle in radians.
        yaw: Yaw angle in radians.

    Returns:
        Tuple of ((R_int, P_int, Y_int), flags).
    """
    flags = ConversionFlags()

    r_int, r_flags = _angle_to_int(roll, RPY_RANGES["roll"])
    p_int, p_flags = _angle_to_int(pitch, RPY_RANGES["pitch"])
    y_int, y_flags = _angle_to_int(yaw, RPY_RANGES["yaw"])

    # Merge flags
    flags.clamped = r_flags.clamped or p_flags.clamped or y_flags.clamped
    flags.out_of_workspace = r_flags.out_of_workspace or p_flags.out_of_workspace or y_flags.out_of_workspace

    # Near-singularity check
    if abs(p_int) > NEAR_SINGULARITY_PITCH_THRESHOLD:
        flags.near_singularity = True

    return (r_int, p_int, y_int), flags


def int_to_rpy_rad(
    r_int: int,
    p_int: int,
    y_int: int,
) -> Tuple[float, float, float]:
    """Convert normalized integers back to RPY in radians.

    Args:
        r_int: Roll integer [-100, 100].
        p_int: Pitch integer [-100, 100].
        y_int: Yaw integer [-100, 100].

    Returns:
        Tuple of (roll_rad, pitch_rad, yaw_rad).
    """
    roll = _int_to_angle(r_int, RPY_RANGES["roll"])
    pitch = _int_to_angle(p_int, RPY_RANGES["pitch"])
    yaw = _int_to_angle(y_int, RPY_RANGES["yaw"])
    return roll, pitch, yaw


# ──────────────────────── Internal helpers ─────────────────────────

def _angle_to_int(
    angle_rad: float,
    angle_range: Tuple[float, float],
) -> Tuple[int, ConversionFlags]:
    """Convert a single angle in radians to normalized integer."""
    lo, hi = angle_range
    flags = ConversionFlags()

    normalized = (angle_rad - lo) / (hi - lo)
    raw = normalized * (INT_MAX - INT_MIN) + INT_MIN

    if raw < INT_MIN or raw > INT_MAX:
        flags.clamped = True
        flags.out_of_workspace = True

    clamped_val = max(INT_MIN, min(INT_MAX, raw))
    return round(clamped_val), flags


def _int_to_angle(
    value: int,
    angle_range: Tuple[float, float],
) -> float:
    """Convert a normalized integer back to angle in radians."""
    lo, hi = angle_range
    clamped_val = max(INT_MIN, min(INT_MAX, value))
    normalized = (clamped_val - INT_MIN) / (INT_MAX - INT_MIN)
    return lo + normalized * (hi - lo)


# ──────────────────────── Batch helpers ────────────────────────────

def position_metric_to_int(
    x: float,
    y: float,
    z: float,
    x_bounds: Tuple[float, float],
    y_bounds: Tuple[float, float],
    z_bounds: Tuple[float, float],
) -> Tuple[Tuple[int, int, int], ConversionFlags]:
    """Convert 3D position from metric to integer grid.

    Returns:
        ((X_int, Y_int, Z_int), flags) with merged flags.
    """
    flags = ConversionFlags()

    x_int, x_flags = metric_to_int(x, x_bounds)
    y_int, y_flags = metric_to_int(y, y_bounds)
    z_int, z_flags = metric_to_int(z, z_bounds)

    flags.clamped = x_flags.clamped or y_flags.clamped or z_flags.clamped
    flags.out_of_workspace = (
        x_flags.out_of_workspace or y_flags.out_of_workspace or z_flags.out_of_workspace
    )

    return (x_int, y_int, z_int), flags


def position_int_to_metric(
    x_int: int,
    y_int: int,
    z_int: int,
    x_bounds: Tuple[float, float],
    y_bounds: Tuple[float, float],
    z_bounds: Tuple[float, float],
) -> Tuple[float, float, float]:
    """Convert 3D position from integer grid to metric."""
    return (
        int_to_metric(x_int, x_bounds),
        int_to_metric(y_int, y_bounds),
        int_to_metric(z_int, z_bounds),
    )
