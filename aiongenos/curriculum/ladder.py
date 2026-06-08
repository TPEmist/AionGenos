# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Curriculum ladder for AionGenos.

Defines the 5-level progression (L0 to L4), control modes, and the maps to IsaacLab task IDs.
"""

from typing import Dict
from aiongenos.config import LEVEL_CONFIGS, LevelConfig, ControlMode

# Maps curriculum level integer to the registered Gym environment ID.
# Negative ids are V4 sub-stages (pre-L0).
LEVEL_TO_GYM_ID: Dict[int, str] = {
    -2: "Isaac-AionGenos-L0a-Left-v0",
    -1: "Isaac-AionGenos-L0a-Right-v0",
    0: "Isaac-AionGenos-L0-v0",
    1: "Isaac-AionGenos-L1-v0",  # Custom task for L1 dual trace
    2: "Isaac-AionGenos-L2-v0",  # Custom task for L2 dual push (RPY control)
    3: "Isaac-AionGenos-L3-v0",  # Custom task for L3 pick place
    4: "Isaac-Reach-OpenArm-Bi-v0",  # Candidate/fallback for L4 handover
}

class CurriculumLadder:
    """Helper class to query curriculum level configs and environment mapping."""

    @staticmethod
    def get_level_config(level: int) -> LevelConfig:
        """Get the configuration details for a specific curriculum level."""
        if level not in LEVEL_CONFIGS:
            raise ValueError(f"Curriculum level {level} is not defined in LEVEL_CONFIGS.")
        return LEVEL_CONFIGS[level]

    @staticmethod
    def get_gym_id(level: int) -> str:
        """Get the Gymnasium environment ID registered with Gym for this level."""
        if level not in LEVEL_TO_GYM_ID:
            raise ValueError(f"No Gym ID mapped for curriculum level {level}.")
        return LEVEL_TO_GYM_ID[level]

    @staticmethod
    def format_instruction(level: int, **kwargs) -> str:
        """Format the task instruction template for the VLM prompt."""
        config = CurriculumLadder.get_level_config(level)
        try:
            return config.task_instruction_template.format(**kwargs)
        except KeyError as e:
            # Fallback if specific formatting variables are missing or incorrect
            return config.task_instruction_template
