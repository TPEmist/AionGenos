"""Pin-4c geometry constants — Single source of truth (Spec §2, REVISION 1).
Pure Python module with no Isaac Sim / pxr dependencies, safe to import on CPU.
"""
from __future__ import annotations

import math
from typing import Optional

# PLACEHOLDER: provisional until wp3a_p4c_derive.py output; replace before any pin4c run
# Derived from reachability scan; None indicates constants are provisional placeholders.
PIN4C_DERIVED_FROM: Optional[str] = None

# PLACEHOLDER: provisional until wp3a_p4c_derive.py output; replace before any pin4c run
PIN4C_THETA_MAX = math.radians(60.0)             # provisional until wp3a_p4c_derive.py output; replace before any pin4c run
PIN4C_THETA_RANGE = (-PIN4C_THETA_MAX, PIN4C_THETA_MAX)
PIN4C_DIST_RANGE = (0.07, 0.10)                  # push distance d in [0.07, 0.10] m

# PLACEHOLDER: provisional until wp3a_p4c_derive.py output; replace before any pin4c run
PIN4C_CUBE_REGION_X = (0.38, 0.44)               # provisional until wp3a_p4c_derive.py output; replace before any pin4c run
PIN4C_CUBE_REGION_Y = (0.04, 0.16)               # provisional until wp3a_p4c_derive.py output; replace before any pin4c run
PIN4C_CUBE_START_X = sum(PIN4C_CUBE_REGION_X) / 2
PIN4C_CUBE_START_Y = sum(PIN4C_CUBE_REGION_Y) / 2
