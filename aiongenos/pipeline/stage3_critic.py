"""Stage 3 — Critic (Self-Reflection via Observable State Only).

On failure: calls VLM with trajectory + before/after RGB to diagnose
and propose corrected sub-goals. STRICTLY observable-only inputs.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from aiongenos.config import ControlMode, LevelConfig
from aiongenos.replay.schema import TimeStep, validate_critic_input
from aiongenos.vlm.client import call_vlm_sync, encode_image_bytes_base64
from aiongenos.vlm.parser import parse_stage3, Stage3Response
from aiongenos.vlm.prompts import get_stage3_prompt, get_stage3_system_prompt

logger = logging.getLogger(__name__)


def format_trajectory_text(trajectory: list[TimeStep]) -> str:
    """Format trajectory timesteps into a text block for the critic prompt.

    Only uses observable data (EE position, gripper state, distances).
    """
    lines = []
    # Subsample to keep prompt within VLM context limits (e.g. max 10-12 steps)
    subsample_step = max(1, len(trajectory) // 10)
    subsampled = trajectory[::subsample_step]
    
    # Ensure the last timestep is always included to capture final state
    if len(trajectory) > 0 and trajectory[-1] not in subsampled:
        subsampled.append(trajectory[-1])

    for ts in subsampled:
        parts = [f"t={ts.t:.1f}:"]
        parts.append(f"LEFT_EE=({ts.left_ee_pos[0]},{ts.left_ee_pos[1]},{ts.left_ee_pos[2]})")
        parts.append(f"RIGHT_EE=({ts.right_ee_pos[0]},{ts.right_ee_pos[1]},{ts.right_ee_pos[2]})")
        if ts.left_gripper:
            parts.append(f"LG={ts.left_gripper}")
        if ts.right_gripper:
            parts.append(f"RG={ts.right_gripper}")
        if ts.distances:
            for k, v in ts.distances.items():
                if isinstance(v, float):
                    parts.append(f"{k}={v:.3f}")
                else:
                    parts.append(f"{k}={v}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def run_stage3(
    level_config: LevelConfig,
    teacher_url: str,
    instruction: str,
    failure_label: str,
    trajectory: list[TimeStep],
    rgb_start_bytes: bytes,
    rgb_end_bytes: bytes,
    temperature: float = 0.5,
) -> tuple[Optional[Stage3Response], float, Optional[str]]:
    """Execute Stage 3: Critic self-reflection.

    Args:
        level_config: Current curriculum level.
        teacher_url: Teacher VLM endpoint.
        instruction: Task instruction string.
        failure_label: Reason for failure.
        trajectory: Observed trajectory timesteps.
        rgb_start_bytes: RGB image at episode start (PNG bytes).
        rgb_end_bytes: RGB image at episode end (PNG bytes).
        temperature: VLM sampling temperature (lower for critic).

    Returns:
        Tuple of (parsed_response or None, latency_ms, error or None).
    """
    # Build critic input and validate observable-only
    trajectory_text = format_trajectory_text(trajectory)
    critic_input = {
        "instruction": instruction,
        "failure_label": failure_label,
        "trajectory_text": trajectory_text,
        "rgb_start": "base64_image",
        "rgb_end": "base64_image",
    }

    # MANDATORY: validate no hidden sensors
    validate_critic_input(critic_input)

    # Build prompt
    state = {
        "instruction": instruction,
        "failure_label": failure_label,
        "trajectory_text": trajectory_text,
    }
    system_prompt = get_stage3_system_prompt()
    user_prompt = get_stage3_prompt(level_config, state)

    # Encode images
    img_start_b64 = encode_image_bytes_base64(rgb_start_bytes)
    img_end_b64 = encode_image_bytes_base64(rgb_end_bytes)

    # Determine parser flags
    has_rpy = level_config.control_mode in (
        ControlMode.POSITION_RPY_2DOF,
        ControlMode.POSITION_RPY_GRIPPER,
    )
    rpy_2dof = level_config.control_mode == ControlMode.POSITION_RPY_2DOF
    has_gripper = level_config.control_mode == ControlMode.POSITION_RPY_GRIPPER

    t0 = time.time()
    try:
        raw_response = call_vlm_sync(
            url=teacher_url,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_base64_list=[img_start_b64, img_end_b64],
            temperature=temperature,
            max_tokens=1024,
            timeout=120.0,
        )
        latency_ms = (time.time() - t0) * 1000

        parsed = parse_stage3(
            raw_response,
            has_rpy=has_rpy,
            has_gripper=has_gripper,
            rpy_2dof=rpy_2dof,
        )
        logger.info(f"Stage 3 critic OK: diagnosis='{parsed.diagnosis[:80]}...' latency={latency_ms:.0f}ms")
        return parsed, latency_ms, None

    except ValueError as e:
        latency_ms = (time.time() - t0) * 1000
        logger.warning(f"Stage 3 parse fail: {e}")
        return None, latency_ms, f"critic_parse_fail: {e}"

    except Exception as e:
        latency_ms = (time.time() - t0) * 1000
        logger.error(f"Stage 3 VLM error: {e}")
        return None, latency_ms, f"critic_error: {e}"
