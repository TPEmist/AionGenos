import logging
import time
from typing import Optional

from aiongenos.config import AionGenosConfig, LevelConfig
from aiongenos.pipeline.stage1_reasoning import run_stage1
from aiongenos.control.command_converter import convert_stage1_to_commands

logger = logging.getLogger(__name__)


def run_eval(
    config: AionGenosConfig,
    env,
    level_config: LevelConfig,
    vlm_url: str,
    num_episodes: int = 10,
) -> dict[str, float]:
    """Evaluate a VLM endpoint (teacher or student) on a specific level.

    Args:
        config: Global config.
        env: Isaac Lab environment interface.
        level_config: Current curriculum level config.
        vlm_url: VLM endpoint URL to query.
        num_episodes: Number of episodes to run for evaluation.

    Returns:
        Dict with metrics (success_rate, avg_latency_ms, avg_duration_s).
    """
    logger.info(f"Starting evaluation: URL={vlm_url}, level={level_config.level}, episodes={num_episodes}")
    
    success_episodes = 0
    total_latency_ms = 0.0
    total_duration_s = 0.0
    vlm_calls = 0

    for ep_idx in range(num_episodes):
        ep_start = time.time()
        logger.info(f"Eval Episode {ep_idx + 1}/{num_episodes} | L{level_config.level}")
        
        # Reset environment
        env.reset()
        
        # Stage 1: Reasoning
        rgb_start = env.get_rgb()
        state = env.get_state(level_config)
        try:
            state["instruction"] = level_config.task_instruction_template.format(**state)
        except Exception:
            state["instruction"] = level_config.task_instruction_template

        stage1_result, stage1_latency, stage1_error = run_stage1(
            level_config=level_config,
            teacher_url=vlm_url,
            rgb_bytes=rgb_start,
            state=state,
            max_retries=level_config.max_retry_on_parse_fail,
        )

        total_latency_ms += stage1_latency
        vlm_calls += 1

        if stage1_result is None:
            logger.warning(f"VLM parse fail on episode {ep_idx + 1}. Marking as failure.")
            total_duration_s += time.time() - ep_start
            continue

        # Stage 2: Attempt
        command = convert_stage1_to_commands(stage1_result, level_config.workspace_bounds)
        attempt = env.execute_command(command, level_config.sim_steps_per_subgoal)

        if attempt.outcome == "success":
            success_episodes += 1
            logger.info(f"Episode {ep_idx + 1} SUCCESS")
        else:
            logger.info(f"Episode {ep_idx + 1} FAILED with: {attempt.outcome}")

        total_duration_s += time.time() - ep_start

    sr = success_episodes / num_episodes if num_episodes > 0 else 0.0
    avg_latency = total_latency_ms / vlm_calls if vlm_calls > 0 else 0.0
    avg_duration = total_duration_s / num_episodes if num_episodes > 0 else 0.0

    metrics = {
        "success_rate": sr,
        "avg_latency_ms": avg_latency,
        "avg_duration_s": avg_duration,
        "total_episodes": float(num_episodes),
        "success_episodes": float(success_episodes),
    }

    logger.info(
        f"Evaluation finished: SR={sr:.1%}, "
        f"avg_latency={avg_latency:.0f}ms, "
        f"avg_duration={avg_duration:.1f}s"
    )
    return metrics
