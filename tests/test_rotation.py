"""Tests for rotation.py — RPY ↔ quaternion, ZYX convention verification."""

import math

import pytest

from aiongenos.control.rotation import (
    int_rpy_to_quat,
    quat_to_int_rpy,
    quat_to_rpy_rad,
    rpy_rad_to_quat,
)


class TestRPYToQuat:
    """Test RPY → quaternion conversion."""

    def test_identity(self):
        """Zero rotation → identity quaternion (1, 0, 0, 0)."""
        w, x, y, z = rpy_rad_to_quat(0.0, 0.0, 0.0)
        assert abs(w - 1.0) < 1e-10
        assert abs(x) < 1e-10
        assert abs(y) < 1e-10
        assert abs(z) < 1e-10

    def test_unit_quaternion(self):
        """Any RPY should produce a unit quaternion."""
        for roll, pitch, yaw in [
            (0.5, 0.3, -0.7),
            (math.pi, 0.0, 0.0),
            (0.0, math.pi / 4, math.pi / 2),
        ]:
            w, x, y, z = rpy_rad_to_quat(roll, pitch, yaw)
            norm = math.sqrt(w**2 + x**2 + y**2 + z**2)
            assert abs(norm - 1.0) < 1e-10, f"Non-unit quat: norm={norm}"

    def test_pure_roll(self):
        """Pure 90° roll about X axis."""
        w, x, y, z = rpy_rad_to_quat(math.pi / 2, 0.0, 0.0)
        expected_w = math.cos(math.pi / 4)
        expected_x = math.sin(math.pi / 4)
        assert abs(w - expected_w) < 1e-10
        assert abs(x - expected_x) < 1e-10
        assert abs(y) < 1e-10
        assert abs(z) < 1e-10

    def test_pure_yaw(self):
        """Pure 90° yaw about Z axis."""
        w, x, y, z = rpy_rad_to_quat(0.0, 0.0, math.pi / 2)
        expected_w = math.cos(math.pi / 4)
        expected_z = math.sin(math.pi / 4)
        assert abs(w - expected_w) < 1e-10
        assert abs(x) < 1e-10
        assert abs(y) < 1e-10
        assert abs(z - expected_z) < 1e-10


class TestQuatToRPY:
    """Test quaternion → RPY conversion."""

    def test_identity(self):
        roll, pitch, yaw = quat_to_rpy_rad(1.0, 0.0, 0.0, 0.0)
        assert abs(roll) < 1e-10
        assert abs(pitch) < 1e-10
        assert abs(yaw) < 1e-10


class TestRoundTrip:
    """RPY → quat → RPY round-trip tests."""

    def test_round_trip_various_angles(self):
        test_cases = [
            (0.0, 0.0, 0.0),
            (0.5, 0.3, -0.7),
            (-1.0, 0.2, 2.0),
            (math.pi / 4, -math.pi / 6, math.pi / 3),
            (0.0, 0.0, math.pi),
        ]
        for roll, pitch, yaw in test_cases:
            w, x, y, z = rpy_rad_to_quat(roll, pitch, yaw)
            r2, p2, y2 = quat_to_rpy_rad(w, x, y, z)
            assert abs(r2 - roll) < 1e-8, f"Roll: {roll} → {r2}"
            assert abs(p2 - pitch) < 1e-8, f"Pitch: {pitch} → {p2}"
            assert abs(y2 - yaw) < 1e-8, f"Yaw: {yaw} → {y2}"

    def test_integer_round_trip(self):
        """int RPY → quat → int RPY should be stable."""
        test_cases = [
            (0, 0, 0),
            (50, 30, -50),
            (-75, 60, 42),
            (100, 0, -100),
        ]
        for r, p, y in test_cases:
            quat = int_rpy_to_quat(r, p, y)
            r2, p2, y2 = quat_to_int_rpy(*quat)
            assert abs(r2 - r) <= 1, f"Roll int: {r} → {r2}"
            assert abs(p2 - p) <= 1, f"Pitch int: {p} → {p2}"
            assert abs(y2 - y) <= 1, f"Yaw int: {y} → {y2}"
