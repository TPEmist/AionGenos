"""WP1-③a rung-2' per-round feedback (PI ruling 2026-10-15, interface bug fix).

Push rounds were stateless: the teacher never saw its previous target or
whether the last move brought it closer. Round r >= 2 now carries a report of
round r-1 only. The format is P1's critic feedback (``DIAGNOSTIC REPORT FOR
PREVIOUS ROUND`` plus the LEFT-arm target and movement lines, wording taken
from ``vlm/prompts.py``, not copied). At rung >= 2 it also carries the two
push distances before and after the move. Below rung 2 those distances are
not observations, so the report carries proprioception only.

P1's progress / regression / flat verdict line (PI 2026-10-15: full P1
condition) is included whenever the distances are. It uses the same
templates and the same 1 cm dead band, applied to the push task's own
success distance (cube → goal), as P1 applies its to the reach success
distance. Without distances (rung < 2) there is no verdict.
"""
from __future__ import annotations

from typing import Optional, Sequence

from aiongenos.vlm.prompts import (CRITIC_FEEDBACK_ARM_BLOCK, CRITIC_FEEDBACK_FLAT, CRITIC_FEEDBACK_HEADER,
                                   CRITIC_FEEDBACK_PROGRESS, CRITIC_FEEDBACK_REGRESS, CRITIC_PROGRESS_DEAD_BAND_CM,
                                   PUSH_FEEDBACK_DIST_LINES)

# P1 arm block = arm header, target line, movement line, distance line; push keeps the first three
_P1_ARM_HEAD = "\n".join(CRITIC_FEEDBACK_ARM_BLOCK.split("\n")[:3])


def format_round_feedback(prev_target_int: Sequence[int], tcp_start_int: Sequence[int],
                          tcp_end_int: Sequence[int],
                          scalars_start_cm: Optional[Sequence[float]] = None,
                          scalars_end_cm: Optional[Sequence[float]] = None) -> str:
    """Report of the previous round. Scalars = (fingertip→cube, cube→goal) cm,
    passed only when the rung shows them; both or neither."""
    if (scalars_start_cm is None) != (scalars_end_cm is None):
        raise ValueError("round feedback: pass both scalar snapshots or neither")
    (px, py, pz), (sx, sy, sz), (ex, ey, ez) = prev_target_int, tcp_start_int, tcp_end_int
    parts = [CRITIC_FEEDBACK_HEADER,
             _P1_ARM_HEAD.format(arm="LEFT", px=px, py=py, pz=pz, sx=sx, sy=sy, sz=sz, ex=ex, ey=ey, ez=ez)]
    if scalars_start_cm is not None:
        parts.append(PUSH_FEEDBACK_DIST_LINES.format(tip_start=scalars_start_cm[0], tip_end=scalars_end_cm[0],
                                                     cg_start=scalars_start_cm[1], cg_end=scalars_end_cm[1]))
        parts.append(_p1_verdict(scalars_start_cm[1], scalars_end_cm[1]))
    return "\n".join(parts)


def _p1_verdict(d_start_cm: float, d_end_cm: float, arm: str = "LEFT") -> str:
    """P1's outcome line (stage3_critic._format_arm_block decision, same templates and dead band)."""
    delta = d_end_cm - d_start_cm
    if delta < -CRITIC_PROGRESS_DEAD_BAND_CM:
        return CRITIC_FEEDBACK_PROGRESS.format(Arm=arm.capitalize(), abs_delta=abs(delta))
    if delta > CRITIC_PROGRESS_DEAD_BAND_CM:
        return CRITIC_FEEDBACK_REGRESS.format(Arm=arm.capitalize(), delta=delta)
    return CRITIC_FEEDBACK_FLAT.format(d_end=d_end_cm)
