"""Reset events that need to override the asset default joint pose.

Why this exists
---------------
``mdp.reset_joints_by_offset`` biases the asset's *default* ``joint_pos``
which, for OpenArm Bimanual, is all zeros (see openarm.py:47-54). With
``±0.2 rad`` offset the arms end up vertical / hanging down — the wrist
EEs land in the lower third of the camera image and frequently occlude
the cube target (F22). For reach tasks we want the arms parked *above*
the workspace by default, then jittered around that.

This file provides ``reset_joints_to_target_with_offset`` which
1. Resolves a per-joint-name target position dict to a tensor aligned
   with ``asset.data.joint_names``,
2. Adds a uniform random offset in ``position_range``,
3. Clamps to soft joint limits and writes to sim.

The rest of the reset pipeline (CommandManager target resampling, EE
warm-up step in IsaacLabEnvInterface) is unchanged.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedEnv

from isaaclab.assets import Articulation
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils import math as math_utils


def _build_target_tensor(
    joint_names: list[str],
    target_dict: dict[str, float],
    fallback: torch.Tensor,
) -> torch.Tensor:
    """Map a {regex: value} dict into a per-joint target tensor.

    Joints not matched by any pattern keep their value from ``fallback``
    (typically the asset's default joint pose). Match order follows the
    dict insertion order; later patterns override earlier ones for the
    same joint.
    """
    target = fallback.clone()
    for pattern, value in target_dict.items():
        rx = re.compile(pattern)
        for i, jn in enumerate(joint_names):
            if rx.fullmatch(jn) or rx.search(jn):
                target[..., i] = float(value)
    return target


def reset_joints_to_target_with_offset(
    env: "ManagerBasedEnv",
    env_ids: torch.Tensor,
    target_joint_pos: dict[str, float],
    position_range: tuple[float, float] = (0.0, 0.0),
    velocity_range: tuple[float, float] = (0.0, 0.0),
    asset_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
) -> None:
    """Reset robot joints to a configured target pose plus a uniform offset.

    Args:
        env: the environment.
        env_ids: ids of envs to reset.
        target_joint_pos: per-joint-name (regex-matched) target in radians;
            unmatched joints keep their asset default value.
        position_range: ``(low, high)`` uniform offset added to the target.
        velocity_range: ``(low, high)`` uniform offset for joint velocities.
        asset_cfg: the asset to reset; defaults to ``robot``.
    """
    asset: Articulation = env.scene[asset_cfg.name]

    if asset_cfg.joint_ids != slice(None):
        iter_env_ids = env_ids[:, None]
    else:
        iter_env_ids = env_ids

    default_pos = asset.data.default_joint_pos[iter_env_ids, asset_cfg.joint_ids].clone()
    default_vel = asset.data.default_joint_vel[iter_env_ids, asset_cfg.joint_ids].clone()

    joint_names = list(asset.data.joint_names)
    target_pos = _build_target_tensor(joint_names, target_joint_pos, default_pos)

    target_pos = target_pos + math_utils.sample_uniform(
        *position_range, target_pos.shape, target_pos.device
    )
    target_vel = default_vel + math_utils.sample_uniform(
        *velocity_range, default_vel.shape, default_vel.device
    )

    pos_limits = asset.data.soft_joint_pos_limits[iter_env_ids, asset_cfg.joint_ids]
    target_pos = target_pos.clamp_(pos_limits[..., 0], pos_limits[..., 1])
    vel_limits = asset.data.soft_joint_vel_limits[iter_env_ids, asset_cfg.joint_ids]
    target_vel = target_vel.clamp_(-vel_limits, vel_limits)

    asset.write_joint_state_to_sim(
        target_pos, target_vel, joint_ids=asset_cfg.joint_ids, env_ids=env_ids
    )
