"""Plan-B fallback: task-space initial-EE-pose randomization via IK.

Used only if Plan A (``mdp.reset_joints_by_offset``, ±0.2 rad joint-space
offset) fails to produce diverse initial EE poses. Plan A is structurally
sound (additive bias, all 7 joints perturbed) so this should rarely be
needed; we keep it as an opt-in EventTerm.

Design:
1. Sample a random EE target in a configurable workspace box (per arm).
2. Use IsaacLab's DifferentialIKController one-shot solve to find joint
   positions that realize the EE target from the default home pose.
3. Set those joint positions on reset (no scale/offset on top).

Trade-offs vs Plan A:
- Pros: precise control over EE distribution; no risk of weird arm angles
  that confuse the VLM's visual interpretation.
- Cons: IK is iterative, costs ~5-10 ms per env per reset (vs Plan A's
  near-zero); can fail / fall back to default if target is unreachable.

Status: scaffolded but **not wired**. Enable by replacing the EventTerm in
``aiongenos/tasks/base/reach_env_base_cfg.py`` with this module's factory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskSpaceResetConfig:
    """Per-arm task-space EE-randomization box."""

    x_range_m: tuple[float, float] = (-0.05, 0.30)
    y_range_m: tuple[float, float] = (0.10, 0.45)  # left arm; right arm flips sign
    z_range_m: tuple[float, float] = (0.20, 0.55)


def reset_ee_pose_uniform_ik(*args, **kwargs):  # pragma: no cover - placeholder
    """Sample uniform EE pose, solve IK, set joint positions.

    Not yet implemented. To activate, fill in:
    - sample target ``ee_target_b`` per arm from ``TaskSpaceResetConfig``
    - call ``DifferentialIKController(...).compute(...)`` from default home
    - assign solution to ``asset.write_joint_state_to_sim``

    See ``IsaacLab.controllers.differential_ik.DifferentialIKController``.
    """
    raise NotImplementedError(
        "Plan-B IK-based reset is scaffolded only. "
        "Implement when Plan A (reset_joints_by_offset) proves insufficient."
    )
