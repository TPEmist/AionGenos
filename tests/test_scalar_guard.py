"""Tests for scalar_guard — position and RPY round-trip, clamping, gimbal-lock zone."""

import math

import pytest

from aiongenos.vlm.scalar_guard import (
    ConversionFlags,
    INT_MAX,
    INT_MIN,
    NEAR_SINGULARITY_PITCH_THRESHOLD,
    int_to_metric,
    int_to_rpy_rad,
    metric_to_int,
    position_int_to_metric,
    position_metric_to_int,
    rpy_rad_to_int,
)


class TestMetricToInt:
    """Position metric ↔ int conversion."""

    def test_center(self):
        val, flags = metric_to_int(0.15, (0.0, 0.3))
        assert val == 0  # midpoint → 0
        assert not flags.clamped

    def test_lower_bound(self):
        val, flags = metric_to_int(0.0, (0.0, 0.3))
        assert val == -100
        assert not flags.clamped

    def test_upper_bound(self):
        val, flags = metric_to_int(0.3, (0.0, 0.3))
        assert val == 100
        assert not flags.clamped

    def test_out_of_range_high(self):
        val, flags = metric_to_int(0.5, (0.0, 0.3))
        assert val == 100  # clamped
        assert flags.clamped
        assert flags.out_of_workspace

    def test_out_of_range_low(self):
        val, flags = metric_to_int(-0.1, (0.0, 0.3))
        assert val == -100  # clamped
        assert flags.clamped
        assert flags.out_of_workspace

    def test_invalid_bounds(self):
        with pytest.raises(ValueError):
            metric_to_int(0.5, (0.3, 0.0))

    def test_round_trip(self):
        """Verify metric → int → metric round-trip within quantization error."""
        bounds = (-0.3, 0.6)
        for original in [-0.3, -0.1, 0.0, 0.15, 0.3, 0.6]:
            int_val, _ = metric_to_int(original, bounds)
            reconstructed = int_to_metric(int_val, bounds)
            resolution = (bounds[1] - bounds[0]) / 200
            assert abs(reconstructed - original) <= resolution + 1e-9, (
                f"Round-trip failed: {original} → {int_val} → {reconstructed}"
            )


class TestRPYConversion:
    """RPY radian ↔ int conversion."""

    def test_zero(self):
        (r, p, y), flags = rpy_rad_to_int(0.0, 0.0, 0.0)
        assert r == 0
        assert p == 0
        assert y == 0
        assert not flags.near_singularity

    def test_full_range_roll(self):
        (r, _, _), flags = rpy_rad_to_int(math.pi, 0.0, 0.0)
        assert r == 100

        (r, _, _), flags = rpy_rad_to_int(-math.pi, 0.0, 0.0)
        assert r == -100

    def test_full_range_pitch(self):
        (_, p, _), flags = rpy_rad_to_int(0.0, math.pi / 2, 0.0)
        assert p == 100

        (_, p, _), flags = rpy_rad_to_int(0.0, -math.pi / 2, 0.0)
        assert p == -100

    def test_near_singularity(self):
        """Pitch near ±90° should trigger near_singularity flag."""
        # |P| > 80 → near_singularity
        (_, p, _), flags = rpy_rad_to_int(0.0, math.pi / 2 * 0.85, 0.0)
        assert abs(p) > NEAR_SINGULARITY_PITCH_THRESHOLD
        assert flags.near_singularity

    def test_not_near_singularity(self):
        """Moderate pitch should NOT trigger near_singularity."""
        (_, p, _), flags = rpy_rad_to_int(0.0, math.pi / 4, 0.0)
        assert abs(p) <= NEAR_SINGULARITY_PITCH_THRESHOLD
        assert not flags.near_singularity

    def test_round_trip(self):
        """RPY int → rad → int round-trip."""
        test_cases = [
            (0, 0, 0),
            (50, 30, -50),
            (-100, 100, 0),
            (75, -60, 42),
        ]
        for r, p, y in test_cases:
            roll, pitch, yaw = int_to_rpy_rad(r, p, y)
            (r2, p2, y2), _ = rpy_rad_to_int(roll, pitch, yaw)
            assert abs(r2 - r) <= 1, f"Roll round-trip: {r} → {r2}"
            assert abs(p2 - p) <= 1, f"Pitch round-trip: {p} → {p2}"
            assert abs(y2 - y) <= 1, f"Yaw round-trip: {y} → {y2}"


class TestPositionBatch:
    """Batch position conversion."""

    def test_3d_round_trip(self):
        x_bounds = (-0.3, 0.6)
        y_bounds = (-0.4, 0.4)
        z_bounds = (0.0, 0.7)

        x, y, z = 0.15, 0.0, 0.35
        (xi, yi, zi), flags = position_metric_to_int(x, y, z, x_bounds, y_bounds, z_bounds)
        x2, y2, z2 = position_int_to_metric(xi, yi, zi, x_bounds, y_bounds, z_bounds)

        for original, reconstructed, bounds in [
            (x, x2, x_bounds), (y, y2, y_bounds), (z, z2, z_bounds)
        ]:
            resolution = (bounds[1] - bounds[0]) / 200
            assert abs(original - reconstructed) <= resolution + 1e-9
