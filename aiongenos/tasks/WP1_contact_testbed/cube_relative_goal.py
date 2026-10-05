# WP1-③a Pin-4b — goal sampled RELATIVE to the cube (PI ruling 2026-10-05).
#
# With the cube spawned in a REGION (not a point), an absolute goal box would
# let push direction drift sideways whenever the cube lands at a region edge.
# Sampling the goal as cube + (dx, dy) keeps every push forward-dominant while
# direction AND distance still vary per episode (the situation variance r needs).
#
# Reset order makes this well-defined: ManagerBasedRLEnv._reset_idx applies the
# reset EVENTS (reset_object writes the cube pose) BEFORE command_manager.reset
# resamples this command, so the cube pose read here is this episode's pose.
# The wp3a_pin4b_gate checks goal − cube ∈ ranges at runtime (config-effect gate).

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import MISSING

import torch
from isaaclab.envs.mdp.commands.commands_cfg import UniformPoseCommandCfg
from isaaclab.envs.mdp.commands.pose_command import UniformPoseCommand
from isaaclab.utils import configclass
from isaaclab.utils.math import subtract_frame_transforms


class CubeRelativePoseCommand(UniformPoseCommand):
    """UniformPoseCommand whose x/y are cube_b + U(offset ranges), clipped to a
    reachable box. z and orientation are sampled exactly as the parent."""

    cfg: "CubeRelativePoseCommandCfg"

    def _resample_command(self, env_ids: Sequence[int]):
        super()._resample_command(env_ids)
        obj = self._env.scene[self.cfg.object_name]
        cube_b, _ = subtract_frame_transforms(
            self.robot.data.root_pos_w[env_ids],
            self.robot.data.root_quat_w[env_ids],
            obj.data.root_pos_w[env_ids],
        )
        r = torch.empty(len(env_ids), device=self.device)
        dx = r.uniform_(*self.cfg.offset_x).clone()
        dy = r.uniform_(*self.cfg.offset_y).clone()
        self.pose_command_b[env_ids, 0] = (cube_b[:, 0] + dx).clamp(*self.cfg.clip_x)
        self.pose_command_b[env_ids, 1] = (cube_b[:, 1] + dy).clamp(*self.cfg.clip_y)


@configclass
class CubeRelativePoseCommandCfg(UniformPoseCommandCfg):
    class_type: type = CubeRelativePoseCommand

    object_name: str = "object"
    offset_x: tuple[float, float] = MISSING   # goal − cube, base frame (m)
    offset_y: tuple[float, float] = MISSING
    clip_x: tuple[float, float] = MISSING     # reachable-box clip (base frame)
    clip_y: tuple[float, float] = MISSING
