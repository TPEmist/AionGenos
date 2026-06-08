"""Per-level task instruction templates.

These are the ONLY prompt artifacts that legitimately differ across curriculum
levels — they describe **what task to do**. Everything else (system prompt,
output format, critic structure) lives in ``prompts.py`` and stays identical
across levels so a freshly-instantiated VLM treats every level the same way.

Adding a new level means:
1. add a key to ``LEVEL_TASK_INSTRUCTIONS`` here
2. point ``LevelConfig.task_instruction_template`` to that string in
   ``aiongenos.config``
"""

from __future__ import annotations

from typing import Final

L0A_SINGLE_REACH_LEFT: Final[str] = (
    "Move your LEFT end-effector to the {target_color} target. "
    "Your right arm is held still — you do not control it."
)

L0A_SINGLE_REACH_RIGHT: Final[str] = (
    "Move your RIGHT end-effector to the {target_color} target. "
    "Your left arm is held still — you do not control it."
)

L0_REACH_TWO_CUBES: Final[str] = (
    "Move both end-effectors to the target positions. "
    "Left arm should reach the {left_target_color} target, "
    "right arm should reach the {right_target_color} target."
)

L1_DUAL_TRACE: Final[str] = (
    "Follow the waypoint trajectory with both arms. "
    "Left arm traces {left_trace_shape}, right arm traces {right_trace_shape}."
)

L2_DUAL_PUSH: Final[str] = (
    "Push the {object_color} block to the {target_color} zone using both arms cooperatively."
)

L3_PICK_PLACE_CLOSE: Final[str] = (
    "Pick up the {object_color} object with one arm and place it at the {target_color} zone."
)

L4_BLOCK_HANDOVER: Final[str] = (
    "Pick up the {object_color} block with the left arm, "
    "hand it over to the right arm, and place it at the {target_color} zone."
)

# Convenience map for tooling that wants to enumerate all instructions.
# Sub-stage levels use negative ids (curriculum manager treats LEVEL_ORDER
# as the source of truth, not the integer values).
LEVEL_TASK_INSTRUCTIONS: Final[dict[int, str]] = {
    -2: L0A_SINGLE_REACH_LEFT,
    -1: L0A_SINGLE_REACH_RIGHT,
    0: L0_REACH_TWO_CUBES,
    1: L1_DUAL_TRACE,
    2: L2_DUAL_PUSH,
    3: L3_PICK_PLACE_CLOSE,
    4: L4_BLOCK_HANDOVER,
}
