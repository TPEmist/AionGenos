"""Stage 1 — Reasoning (Zero-Shot Planning).

Takes current RGB + state → calls Teacher VLM → returns parsed sub-goal action.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Optional

from aiongenos.config import ControlMode, LevelConfig
from aiongenos.vlm.client import (
    call_vlm_sync,
    call_vlm_history_sync,
    encode_image_bytes_base64,
    EpisodeConversation,
)
from aiongenos.vlm.parser import parse_stage1, Stage1Response
from aiongenos.vlm.prompts import (
    CRITIC_FEEDBACK_INJECTION_HEADER,
    get_stage1_prompt,
    get_stage1_system_prompt,
)

logger = logging.getLogger(__name__)


def run_stage1(
    level_config: LevelConfig,
    teacher_url: str,
    rgb_bytes: bytes,
    state: dict[str, str | int],
    conversation: Optional[EpisodeConversation] = None,
    critic_feedback: Optional[str] = None,
    temperature: float = 0.7,
    max_retries: int = 2,
) -> tuple[Optional[Stage1Response], float, Optional[str]]:
    """Execute Stage 1: VLM Reasoning.

    Args:
        level_config: Current curriculum level config.
        teacher_url: Teacher VLM endpoint URL.
        rgb_bytes: Current scene RGB image as PNG bytes.
        state: Dict with template placeholders (instruction, left_x, etc.).
        conversation: Optional stateful conversation history for the episode.
        critic_feedback: Optional diagnostic text from the critic.
        temperature: VLM sampling temperature.
        max_retries: Max parse failure retries.

    Returns:
        Tuple of (parsed_response or None, latency_ms, error_message or None).
    """
    system_prompt = get_stage1_system_prompt()
    user_prompt = get_stage1_prompt(level_config, state)
    
    if critic_feedback:
        user_prompt += f"\n\n{CRITIC_FEEDBACK_INJECTION_HEADER}\n{critic_feedback}"
        
    img_b64 = encode_image_bytes_base64(rgb_bytes)

    # Determine parser flags from control mode
    has_rpy = level_config.control_mode in (
        ControlMode.POSITION_RPY_2DOF,
        ControlMode.POSITION_RPY_GRIPPER,
    )
    rpy_2dof = level_config.control_mode == ControlMode.POSITION_RPY_2DOF
    has_gripper = level_config.control_mode == ControlMode.POSITION_RPY_GRIPPER

    if conversation is not None:
        conversation.append_user_turn(user_prompt, img_b64)

    for attempt in range(max_retries + 1):
        t0 = time.time()
        try:
            if conversation is not None:
                raw_response = call_vlm_history_sync(
                    url=teacher_url,
                    conversation=conversation,
                    temperature=temperature,
                    max_tokens=2048,
                    timeout=300.0,
                )
            else:
                raw_response = call_vlm_sync(
                    url=teacher_url,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    image_base64=img_b64,
                    temperature=temperature,
                    max_tokens=2048,
                    timeout=300.0,
                )
            latency_ms = (time.time() - t0) * 1000

            parsed = parse_stage1(
                raw_response,
                has_rpy=has_rpy,
                has_gripper=has_gripper,
                rpy_2dof=rpy_2dof,
            )
            logger.info(
                f"Stage 1 OK (attempt {attempt + 1}): "
                f"L=({parsed.left.position.x},{parsed.left.position.y},{parsed.left.position.z}) "
                f"R=({parsed.right.position.x},{parsed.right.position.y},{parsed.right.position.z}) "
                f"latency={latency_ms:.0f}ms"
            )
            if conversation is not None:
                conversation.append_assistant_turn(raw_response)
            return parsed, latency_ms, None

        except ValueError as e:
            latency_ms = (time.time() - t0) * 1000
            logger.warning(f"Stage 1 parse fail (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt == max_retries:
                return None, latency_ms, f"vlm_parse_fail: {e}"

        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            logger.error(f"Stage 1 VLM error: {e}")
            return None, latency_ms, f"vlm_error: {e}"

    return None, 0.0, "max_retries_exceeded"
