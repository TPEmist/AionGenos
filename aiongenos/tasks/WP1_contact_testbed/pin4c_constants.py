"""Pin-4c geometry constants — Single source of truth (Spec §2, REVISION 1).
Pure Python module with no Isaac Sim / pxr dependencies, safe to import on CPU.
"""
from __future__ import annotations

import math
from typing import Optional

# Derived from reachability scan candidate ±75° (outcome-only; ±60° blind sweep 6ce58e20 = 10/50 > 10%).
PIN4C_DERIVED_FROM: Optional[str] = (
    "docs/p2_prereg/evidence/2026-10-26_p4c/derived_final.json "
    "(candidate ±75°, outcome-only; ±60° blind sweep 6ce58e20 = 10/50 > 10%)"
)

PIN4C_THETA_MAX = math.radians(75.0)
PIN4C_THETA_RANGE = (-PIN4C_THETA_MAX, PIN4C_THETA_MAX)
PIN4C_DIST_RANGE = (0.07, 0.10)

PIN4C_CUBE_REGION_X = (0.40, 0.46)
PIN4C_CUBE_REGION_Y = (-0.02, 0.10)
PIN4C_CUBE_START_X = sum(PIN4C_CUBE_REGION_X) / 2
PIN4C_CUBE_START_Y = sum(PIN4C_CUBE_REGION_Y) / 2
