# WP1-③a Pin-4b / Pin-4c — goal sampled RELATIVE to the cube (PI rulings 2026-10-05, 2026-10-26).
#
# With the cube spawned in a REGION (not a point), an absolute goal box would
# let push direction drift sideways whenever the cube lands at a region edge.
# Sampling the goal as cube + (dx, dy) keeps every push forward-dominant while
# direction AND distance still vary per episode (the situation variance r needs).
#
# Pin-4c (2026-10-26): polar command sampling theta ~ U(-theta_max, theta_max),
# dist ~ U(0.07, 0.10); goal = cube + dist * (cos theta, sin theta).
# Pure U(theta) x U(d) with NO clamping and NO rejection sampling (R1).
#
# Reset order makes this well-defined: ManagerBasedRLEnv._reset_idx applies the
# reset EVENTS (reset_object writes the cube pose) BEFORE command_manager.reset
# resamples this command, so the cube pose read here is this episode's pose.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import MISSING
import math
from typing import Any

import torch
try:
    from isaaclab.envs.mdp.commands.commands_cfg import UniformPoseCommandCfg
    from isaaclab.envs.mdp.commands.pose_command import UniformPoseCommand
    from isaaclab.utils import configclass
    from isaaclab.utils.math import subtract_frame_transforms
except (ImportError, ModuleNotFoundError):
    UniformPoseCommandCfg = object
    UniformPoseCommand = object

    def configclass(cls=None):
        return cls if cls is not None else lambda c: c

    subtract_frame_transforms = None


def compute_polar_goal(cube_xy: Sequence[float], theta: float, dist: float) -> tuple[float, float]:
    """Pure CPU function: takes (cube_xy, theta, dist) and returns goal_xy = cube_xy + dist*(cos theta, sin theta).
    No Isaac/torch required."""
    cx, cy = cube_xy[0], cube_xy[1]
    return (cx + dist * math.cos(theta), cy + dist * math.sin(theta))


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


class CubeRelativePolarCommand(UniformPoseCommand):
    """WP1-③a Pin-4c: goal sampled in polar coordinates relative to the cube:
    theta ~ U(theta_range), d ~ U(dist_range); goal = cube + d*(cos theta, sin theta).
    Pure U(theta) x U(d) with NO clamping and NO rejection sampling (R1).
    Logs (theta, d, cube_xy_at_sample) for geometry HARD checks (R3)."""

    cfg: "CubeRelativePolarCommandCfg"

    def __init__(self, cfg: "CubeRelativePolarCommandCfg", env: Any):
        super().__init__(cfg, env)
        self.last_sample: dict[str, Any] = {}

    def _resample_command(self, env_ids: Sequence[int]):
        super()._resample_command(env_ids)
        obj = self._env.scene[self.cfg.object_name]
        cube_b, _ = subtract_frame_transforms(
            self.robot.data.root_pos_w[env_ids],
            self.robot.data.root_quat_w[env_ids],
            obj.data.root_pos_w[env_ids],
        )
        r_th = torch.empty(len(env_ids), device=self.device)
        r_d = torch.empty(len(env_ids), device=self.device)
        theta = r_th.uniform_(*self.cfg.theta_range).clone()
        dist = r_d.uniform_(*self.cfg.dist_range).clone()
        # Pure U(theta) x U(d) — NO CLAMPING (R1)
        self.pose_command_b[env_ids, 0] = cube_b[:, 0] + dist * torch.cos(theta)
        self.pose_command_b[env_ids, 1] = cube_b[:, 1] + dist * torch.sin(theta)

        # R3: log (theta, d, cube_xy_at_sample) into last_sample
        self.last_sample = {
            "theta": float(theta[0].item()),
            "dist": float(dist[0].item()),
            "cube_xy": [float(cube_b[0, 0].item()), float(cube_b[0, 1].item())],
        }

    def get_last_sample(self, env_id: int = 0) -> dict[str, Any]:
        return dict(self.last_sample)


@configclass
class CubeRelativePolarCommandCfg(UniformPoseCommandCfg):
    class_type: type = CubeRelativePolarCommand

    object_name: str = "object"
    theta_range: tuple[float, float] = MISSING   # (-theta_max, theta_max) in radians
    dist_range: tuple[float, float] = MISSING    # (d_min, d_max) in meters
