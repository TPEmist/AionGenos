"""Pin-4c geometry constants — Single source of truth (Spec §2, REVISION 1).
Pure Python module with no Isaac Sim / pxr dependencies, safe to import on CPU.
"""
from __future__ import annotations

import math

PIN4C_THETA_MAX = math.radians(60.0)             # PI ruling 2026-10-26 (>= 60 deg symmetric)
PIN4C_THETA_RANGE = (-PIN4C_THETA_MAX, PIN4C_THETA_MAX)
PIN4C_DIST_RANGE = (0.07, 0.10)                  # push distance d in [0.07, 0.10] m
PIN4C_CUBE_REGION_X = (0.38, 0.44)               # derived cube box X (hand keep-out floor 0.38)
PIN4C_CUBE_REGION_Y = (0.04, 0.16)               # derived cube box Y
PIN4C_CUBE_START_X = sum(PIN4C_CUBE_REGION_X) / 2
PIN4C_CUBE_START_Y = sum(PIN4C_CUBE_REGION_Y) / 2
