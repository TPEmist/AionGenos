"""Rotation utilities — RPY ↔ Quaternion conversion.

Single source of truth for rotation representation conversions.
Convention: ZYX intrinsic (yaw → pitch → roll), aligned with Isaac Lab's
`math_utils.matrix_from_euler` convention.

Quaternion format: (w, x, y, z) — Isaac Lab convention.
"""

from __future__ import annotations

import math
from typing import Tuple

from aiongenos.vlm.scalar_guard import int_to_rpy_rad, rpy_rad_to_int


def rpy_rad_to_quat(roll: float, pitch: float, yaw: float) -> Tuple[float, float, float, float]:
    """Convert Euler RPY (radians, ZYX intrinsic) to quaternion (w, x, y, z).

    ZYX intrinsic = XYZ extrinsic: first rotate around Z by yaw, then Y by pitch,
    then X by roll.

    Args:
        roll: Roll angle in radians.
        pitch: Pitch angle in radians.
        yaw: Yaw angle in radians.

    Returns:
        Quaternion as (w, x, y, z).
    """
    cr = math.cos(roll / 2)
    sr = math.sin(roll / 2)
    cp = math.cos(pitch / 2)
    sp = math.sin(pitch / 2)
    cy = math.cos(yaw / 2)
    sy = math.sin(yaw / 2)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return (w, x, y, z)


def quat_to_rpy_rad(w: float, x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Convert quaternion (w, x, y, z) to Euler RPY (radians, ZYX intrinsic).

    Args:
        w, x, y, z: Quaternion components.

    Returns:
        Tuple of (roll, pitch, yaw) in radians.
    """
    # Roll (X-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (Y-axis rotation)
    sinp = 2 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))  # Clamp for numerical stability
    pitch = math.asin(sinp)

    # Yaw (Z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)


def int_rpy_to_quat(r_int: int, p_int: int, y_int: int) -> Tuple[float, float, float, float]:
    """Convert integer RPY to quaternion.

    Convenience function chaining int_to_rpy_rad → rpy_rad_to_quat.

    Args:
        r_int, p_int, y_int: Integer RPY values in [-100, 100].

    Returns:
        Quaternion as (w, x, y, z).
    """
    roll, pitch, yaw = int_to_rpy_rad(r_int, p_int, y_int)
    return rpy_rad_to_quat(roll, pitch, yaw)


def quat_to_int_rpy(
    w: float, x: float, y: float, z: float
) -> Tuple[int, int, int]:
    """Convert quaternion to integer RPY.

    Convenience function chaining quat_to_rpy_rad → rpy_rad_to_int.

    Args:
        w, x, y, z: Quaternion components.

    Returns:
        Tuple of (R_int, P_int, Y_int).
    """
    roll, pitch, yaw = quat_to_rpy_rad(w, x, y, z)
    (r_int, p_int, y_int), _flags = rpy_rad_to_int(roll, pitch, yaw)
    return (r_int, p_int, y_int)
