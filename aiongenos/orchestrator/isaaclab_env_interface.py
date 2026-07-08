# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""IsaacLab environment wrapper implementing the EnvInterface protocol."""

import io
import logging
from typing import Optional

import numpy as np
import torch
import gymnasium as gym
from PIL import Image

from aiongenos.config import LevelConfig, ControlMode, WorkspaceBounds
from aiongenos.pipeline.stage2_attempt import BimanualCommand, AttemptResult
from aiongenos.replay.schema import TimeStep
from aiongenos.vlm.scalar_guard import position_metric_to_int, rpy_rad_to_int
from aiongenos.control.rotation import quat_to_rpy_rad

logger = logging.getLogger(__name__)

class IsaacLabEnvInterface:
    """Concrete implementation of EnvInterface wrapping an IsaacLab gym environment."""

    def __init__(self, env: gym.Env):
        """Initialize the wrapper.

        Args:
            env: The gymnasium environment instantiated from IsaacLab.
        """
        self.env = env
        unwrapped = env.unwrapped
        
        # Access the robot asset from the interactive scene
        self.robot = getattr(unwrapped.scene, "robot", None)
        if self.robot is None:
            # Fallback to look up articulations dictionary
            self.robot = unwrapped.scene.articulations.get("robot")
            
        self.left_body_idx = 0
        self.right_body_idx = 0
        
        self.left_finger_joint_ids = []
        self.right_finger_joint_ids = []
        if self.robot is not None:
            # Resolve left end-effector body index
            for name in ["openarm_left_hand", "left_hand", "left_link7", "panda_hand", "panda_link7"]:
                try:
                    self.left_body_idx = self.robot.find_bodies(name)[0][0]
                    logger.info(f"Resolved left hand body to name: {name}, index: {self.left_body_idx}")
                    break
                except Exception:
                    pass
            # Resolve right end-effector body index
            for name in ["openarm_right_hand", "right_hand", "right_link7", "panda_hand_right", "panda_right_hand"]:
                try:
                    self.right_body_idx = self.robot.find_bodies(name)[0][0]
                    logger.info(f"Resolved right hand body to name: {name}, index: {self.right_body_idx}")
                    break
                except Exception:
                    pass
            # Resolve finger joint IDs
            try:
                self.left_finger_joint_ids = self.robot.find_joints("openarm_left_finger_joint.*")[0]
                logger.info(f"Resolved left finger joints: {self.left_finger_joint_ids}")
            except Exception:
                pass
            try:
                self.right_finger_joint_ids = self.robot.find_joints("openarm_right_finger_joint.*")[0]
                logger.info(f"Resolved right finger joints: {self.right_finger_joint_ids}")
            except Exception:
                pass
        else:
            logger.warning("Robot articulation not found in environment scene!")

    def reset(self, seed: Optional[int] = None) -> dict:
        """Reset environment, return initial state dict.

        Amendment 7 §7.7 / Amendment 10 §10.4 (item 7): when ``seed`` is
        provided, forward it to ``env.reset(seed=...)`` **and** also seed
        torch / numpy / Python-random. Gymnasium's ``reset(seed=)`` is
        supposed to be sufficient, but IsaacLab's randomization event
        terms sometimes draw from torch's global RNG rather than the
        env's private one — belt-and-braces here is cheap and closes the
        smoke-test hole preemptively. Determinism is verified by
        ``scripts/diagnostics/check_env_seed_determinism.py``.

        After ``env.reset()`` Isaac Lab's CommandManager has not yet resampled
        a new target — querying it returns the (0, 0, 0) sentinel. We need to
        step the env once so the manager regenerates targets.

        However we must NOT use a zero action: the L0/L1 action terms are
        ``DifferentialInverseKinematicsActionCfg(command_type='position',
        use_relative_mode=False)``. In absolute-IK mode a zero action is
        interpreted as "drive both EEs to base-frame origin (0, 0, 0)", which
        immediately undoes the ``reset_joints_by_offset`` randomization (this
        was bug V3 — Z-axis std collapsed to 1-2 grid units).

        Fix: feed the *current* EE pose as the action so the IK target equals
        the current state, leaving joints undisturbed.
        """
        if seed is not None:
            import random as _random
            _random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            obs, info = self.env.reset(seed=seed)
        else:
            obs, info = self.env.reset()

        try:
            action_shape = self.env.action_space.shape
            action_dim = action_shape[-1] if len(action_shape) > 0 else 6

            if self.robot is not None and action_dim in (6, 14, 16):
                # Build a "stay-in-place" action from the current EE poses.
                left_pos_b, right_pos_b, left_quat_w, right_quat_w = self._get_ee_poses()
                if action_dim == 6:
                    parts = [*left_pos_b, *right_pos_b]
                elif action_dim == 14:
                    parts = [*left_pos_b, *left_quat_w, *right_pos_b, *right_quat_w]
                else:  # 16: pose + 1-bit gripper per arm; gripper open = +1
                    parts = [*left_pos_b, *left_quat_w, 1.0, *right_pos_b, *right_quat_w, 1.0]
                hold_action = torch.tensor(
                    [parts], device=self.env.unwrapped.device, dtype=torch.float32
                )
            else:
                hold_action = torch.zeros(
                    (1, action_dim), device=self.env.unwrapped.device, dtype=torch.float32
                )
            self.env.step(hold_action)
        except Exception as e:
            logger.debug(f"warm-up step after reset skipped: {e}")

        return {"obs": obs, "info": info}

    def get_rgb(self) -> bytes:
        """Capture current scene as PNG bytes."""
        unwrapped = self.env.unwrapped
        camera = getattr(unwrapped.scene, "camera", None)
        if camera is None:
            camera = unwrapped.scene.sensors.get("camera")
            
        if camera is None:
            logger.warning("Camera sensor not found in environment scene! Cannot get RGB.")
            return b""
            
        if "rgb" not in camera.data.output:
            logger.warning("RGB data not yet populated in camera output sensor.")
            return b""
            
        # Extract RGB tensor (shape: num_envs, H, W, channels) for environment 0
        rgb_tensor = camera.data.output["rgb"]
        img_np = rgb_tensor[0].cpu().numpy()
        
        # If image has alpha channel, strip it to return pure RGB
        if img_np.shape[-1] == 4:
            img_np = img_np[:, :, :3]
            
        img = Image.fromarray(img_np.astype(np.uint8))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def get_state(self, level_config: LevelConfig) -> dict[str, str | int]:
        """Get current state dict for prompt template."""
        if self.robot is None:
            return {}

        left_pos_b, right_pos_b, left_quat_w, right_quat_w = self._get_ee_poses()
        bounds = level_config.workspace_bounds

        # Convert EE positions to normalized integer grid
        left_pos_int, _ = position_metric_to_int(
            left_pos_b[0], left_pos_b[1], left_pos_b[2],
            bounds.x_bounds, bounds.y_bounds, bounds.z_bounds
        )
        right_pos_int, _ = position_metric_to_int(
            right_pos_b[0], right_pos_b[1], right_pos_b[2],
            bounds.x_bounds, bounds.y_bounds, bounds.z_bounds
        )

        # V4: L0a sub-stage marker is red (configured in single_reach_cfg.py),
        # so target_color must match for the instruction template to align
        # with what the VLM sees. Other levels keep their existing fillers.
        is_l0a = level_config.name.startswith("L0a_")
        state = {
            "left_x": left_pos_int[0],
            "left_y": left_pos_int[1],
            "left_z": left_pos_int[2],
            "right_x": right_pos_int[0],
            "right_y": right_pos_int[1],
            "right_z": right_pos_int[2],
            "left_target_color": "red",
            "right_target_color": "blue",
            "left_trace_shape": "circle",
            "right_trace_shape": "square",
            "object_color": "yellow",
            "target_color": "red" if is_l0a else "green",
        }

        # Phase 4 Fix 3 — surface live distance-to-target into prompt template.
        # These are observable (RGB-derivable) so the observable-only invariant
        # is preserved. Used by Stage 1 prompt to disambiguate "stop because
        # plateau" from "stop because converged" — the teacher previously had
        # no way to know its absolute distance during a round.
        try:
            dists = self.get_current_distances()
            state["dist_red_cm"] = f"{dists.get('dist_red', 0.0) * 100:.1f}"
            state["dist_blue_cm"] = f"{dists.get('dist_blue', 0.0) * 100:.1f}"
        except Exception:
            state["dist_red_cm"] = "?"
            state["dist_blue_cm"] = "?"

        # For pose-level controls, include RPY
        if level_config.control_mode in (ControlMode.POSITION_RPY_2DOF, ControlMode.POSITION_RPY_GRIPPER):
            left_r, left_p, left_y = quat_to_rpy_rad(*left_quat_w)
            right_r, right_p, right_y = quat_to_rpy_rad(*right_quat_w)
            
            left_rpy_int, _ = rpy_rad_to_int(left_r, left_p, left_y)
            right_rpy_int, _ = rpy_rad_to_int(right_r, right_p, right_y)
            
            state.update({
                "left_r": left_rpy_int[0],
                "left_p": left_rpy_int[1],
                "left_yaw": left_rpy_int[2],
                "right_r": right_rpy_int[0],
                "right_p": right_rpy_int[1],
                "right_yaw": right_rpy_int[2],
            })

        # Gripper state (for L3+)
        if level_config.control_mode == ControlMode.POSITION_RPY_GRIPPER:
            left_gripper_state = "open"
            right_gripper_state = "open"
            
            if len(self.left_finger_joint_ids) > 0:
                # Average position of left fingers
                left_pos = self.robot.data.joint_pos[0, self.left_finger_joint_ids].mean().item()
                left_gripper_state = "closed" if left_pos < 0.015 else "open"
            if len(self.right_finger_joint_ids) > 0:
                # Average position of right fingers
                right_pos = self.robot.data.joint_pos[0, self.right_finger_joint_ids].mean().item()
                right_gripper_state = "closed" if right_pos < 0.015 else "open"
                
            state.update({
                "left_gripper": left_gripper_state,
                "right_gripper": right_gripper_state,
            })

        return state

    def execute_command(
        self,
        command: BimanualCommand,
        steps: int,
        active_arm: Optional[str] = None,
    ) -> AttemptResult:
        """Execute a bimanual command for N sim steps.

        Args:
            command: VLM-derived target for both arms.
            steps: number of sim steps to servo.
            active_arm: V4 — when set to ``"left"`` or ``"right"``, the inactive
                arm's command is overridden with its current EE pose (hold in
                place) regardless of what the VLM emitted. ``None`` (default)
                means both arms execute the VLM command.
        """
        left_pos = command.left.position
        right_pos = command.right.position

        # V4 single-arm masking: replace the inactive arm with hold-in-place.
        if active_arm in ("left", "right"):
            try:
                cur_left_b, cur_right_b, _, _ = self._get_ee_poses()
                if active_arm == "left":
                    right_pos = (float(cur_right_b[0]), float(cur_right_b[1]), float(cur_right_b[2]))
                else:
                    left_pos = (float(cur_left_b[0]), float(cur_left_b[1]), float(cur_left_b[2]))
            except Exception as e:
                logger.warning(f"single-arm mask skipped: {e}")

        # Build action list depending on action space dimension
        action_shape = self.env.action_space.shape
        action_dim = action_shape[-1] if len(action_shape) > 0 else 6

        if action_dim == 6:
            # Position-only action mode: [left_x, left_y, left_z, right_x, right_y, right_z]
            action_list = list(left_pos) + list(right_pos)
        elif action_dim == 14:
            # Absolute pose action mode: [left_pos, left_quat, right_pos, right_quat]
            left_quat = command.left.quaternion or (1.0, 0.0, 0.0, 0.0)
            right_quat = command.right.quaternion or (1.0, 0.0, 0.0, 0.0)
            action_list = list(left_pos) + list(left_quat) + list(right_pos) + list(right_quat)
        elif action_dim == 16:
            # Absolute pose + binary gripper action mode:
            # [left_pos(3), left_quat(4), left_gripper(1), right_pos(3), right_quat(4), right_gripper(1)]
            left_quat = command.left.quaternion or (1.0, 0.0, 0.0, 0.0)
            right_quat = command.right.quaternion or (1.0, 0.0, 0.0, 0.0)
            left_gripper_val = -1.0 if command.left.gripper_close else 1.0
            right_gripper_val = -1.0 if command.right.gripper_close else 1.0
            action_list = (
                list(left_pos) + list(left_quat) + [left_gripper_val] +
                list(right_pos) + list(right_quat) + [right_gripper_val]
            )
        else:
            # Fallback scaling/truncating to match action space dimension
            action_list = list(left_pos) + list(right_pos)
            while len(action_list) < action_dim:
                action_list.append(0.0)
            action_list = action_list[:action_dim]

        action_tensor = torch.tensor([action_list], device=self.env.unwrapped.device, dtype=torch.float32)
        
        trajectory = []
        outcome = "timeout"
        flags = []
        rgb_start_bytes = self.get_rgb()

        for step in range(steps):
            obs, reward, terminated, truncated, info = self.env.step(action_tensor)
            
            t = self.env.unwrapped.common_step_counter * self.env.unwrapped.cfg.sim.dt
            left_pos_b, right_pos_b, left_quat_w, right_quat_w = self._get_ee_poses()
            
            # Map back to integer coordinates for trajectory records
            unwrapped = self.env.unwrapped
            bounds = unwrapped.cfg.workspace_bounds if hasattr(unwrapped.cfg, "workspace_bounds") else WorkspaceBounds()
            
            left_pos_int, left_pos_flags = position_metric_to_int(
                left_pos_b[0], left_pos_b[1], left_pos_b[2],
                bounds.x_bounds, bounds.y_bounds, bounds.z_bounds
            )
            right_pos_int, right_pos_flags = position_metric_to_int(
                right_pos_b[0], right_pos_b[1], right_pos_b[2],
                bounds.x_bounds, bounds.y_bounds, bounds.z_bounds
            )
            
            # Record clamped/out-of-workspace flags
            if left_pos_flags.clamped or right_pos_flags.clamped:
                if "clamped" not in flags:
                    flags.append("clamped")
            if left_pos_flags.out_of_workspace or right_pos_flags.out_of_workspace:
                if "out_of_workspace" not in flags:
                    flags.append("out_of_workspace")

            left_r, left_p, left_y = quat_to_rpy_rad(*left_quat_w)
            right_r, right_p, right_y = quat_to_rpy_rad(*right_quat_w)
            
            left_rpy_int, left_rpy_flags = rpy_rad_to_int(left_r, left_p, left_y)
            right_rpy_int, right_rpy_flags = rpy_rad_to_int(right_r, right_p, right_y)
            
            if left_rpy_flags.near_singularity or right_rpy_flags.near_singularity:
                if "near_singularity" not in flags:
                    flags.append("near_singularity")

            # Calculate actual distance to targets for success checking
            left_target_pos, right_target_pos = self._get_target_poses()
            left_pos_w = self.robot.data.body_pos_w[0, self.left_body_idx].cpu().numpy()
            right_pos_w = self.robot.data.body_pos_w[0, self.right_body_idx].cpu().numpy()
            
            left_dist = float(np.linalg.norm(left_pos_w - left_target_pos))
            right_dist = float(np.linalg.norm(right_pos_w - right_target_pos))
            
            timestep = TimeStep(
                t=t,
                left_ee_pos=left_pos_int,
                right_ee_pos=right_pos_int,
                left_ee_rpy=left_rpy_int,
                right_ee_rpy=right_rpy_int,
                distances={"dist_red": left_dist, "dist_blue": right_dist}
            )
            trajectory.append(timestep)
            
            # Success check: both hands are within 5 cm of targets
            if left_dist < 0.05 and right_dist < 0.05:
                outcome = "success"
                break
                
            if terminated:
                outcome = "collision"
                break
                
        rgb_end_bytes = self.get_rgb()
        
        return AttemptResult(
            trajectory=trajectory,
            outcome=outcome,
            flags=flags,
            rgb_start_bytes=rgb_start_bytes,
            rgb_end_bytes=rgb_end_bytes
        )

    def _get_ee_poses(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Get end-effector position and orientation relative to base frame."""
        root_pos_w = self.robot.data.root_pos_w[0].cpu().numpy()
        
        left_pos_w = self.robot.data.body_pos_w[0, self.left_body_idx].cpu().numpy()
        right_pos_w = self.robot.data.body_pos_w[0, self.right_body_idx].cpu().numpy()
        
        # Compute relative to robot base coordinate system
        left_pos_b = left_pos_w - root_pos_w
        right_pos_b = right_pos_w - root_pos_w
        
        left_quat_w = self.robot.data.body_quat_w[0, self.left_body_idx].cpu().numpy()
        right_quat_w = self.robot.data.body_quat_w[0, self.right_body_idx].cpu().numpy()
        
        return left_pos_b, right_pos_b, left_quat_w, right_quat_w

    def _get_target_poses(self) -> tuple[np.ndarray, np.ndarray]:
        """Get current target goal poses in world frame."""
        unwrapped = self.env.unwrapped
        
        left_term = unwrapped.command_manager.get_term("left_ee_pose")
        right_term = unwrapped.command_manager.get_term("right_ee_pose")
        
        left_target = left_term.pose_command_w[0, :3].cpu().numpy()
        right_target = right_term.pose_command_w[0, :3].cpu().numpy()
        
        return left_target, right_target

    def get_current_distances(self) -> dict[str, float]:
        """Get current distances from left and right end effectors to targets."""
        if self.robot is None:
            return {"dist_red": 0.0, "dist_blue": 0.0}
        left_target_pos, right_target_pos = self._get_target_poses()
        left_pos_w = self.robot.data.body_pos_w[0, self.left_body_idx].cpu().numpy()
        right_pos_w = self.robot.data.body_pos_w[0, self.right_body_idx].cpu().numpy()
        left_dist = float(np.linalg.norm(left_pos_w - left_target_pos))
        right_dist = float(np.linalg.norm(right_pos_w - right_target_pos))
        return {"dist_red": left_dist, "dist_blue": right_dist}

