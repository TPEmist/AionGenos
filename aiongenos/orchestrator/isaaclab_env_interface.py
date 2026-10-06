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

        # WP1-③a PUSH observation interface (PI ruling 2026-10-05). Photos +
        # PROPRIOCEPTION only: the cube and the green zone are PERCEIVED from the
        # image, never oracle-fed. The P1 L0a teacher's actual condition is the
        # _S1_POS template (prompts.py:59): EE positions + scalar EE→target
        # distances, no object coordinates. Push rung-1 is stricter still (no
        # scalar either); the disclosed scaffold ladder adds them back only when
        # pre-registered (wp3a_pilot_plan.md): rung-2 = + scalar distances
        # (TCP→cube, cube→goal) = the P1 condition; rung-3 = + coordinates and
        # vectors. EEF reference point = the TCP (fingertip pad), matching the
        # TCP targets the executor converts to the hand (push_body).
        if level_config.control_mode == ControlMode.PUSH_WAYPOINT:
            state.update(self._push_state(bounds))

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

    # ─── WP1-③a push execution (OSC, teacher-only) ──────────────────────────
    _ARM_TORQUE_LIMITS = (40.0, 40.0, 27.0, 27.0, 7.0, 7.0, 7.0)  # real hw N·m

    # ── WP1-③a push: proprioception + disclosed scaffold rungs ──────────────
    push_obs_rung: int = 1   # set by run_push_collect (pre-registered ladder)

    def _push_state(self, bounds) -> dict:
        from aiongenos.orchestrator import push_body as _pb
        r = self.robot
        root = r.data.root_pos_w[0, :3]
        tcp_idx = r.find_bodies(_pb.TCP_BODY)[0][0]
        tcp_b = (r.data.body_pos_w[0, tcp_idx, :3] - root).cpu().numpy()
        (tx, ty, tz), _ = position_metric_to_int(
            float(tcp_b[0]), float(tcp_b[1]), float(tcp_b[2]),
            bounds.x_bounds, bounds.y_bounds, bounds.z_bounds)
        out = {"left_x": tx, "left_y": ty, "left_z": tz,
               "left_gripper": "closed (locked)", "oracle_block": ""}
        rung = int(self.push_obs_rung)
        if rung >= 2:
            import numpy as _np
            cube_b = _np.array(self.get_cube_pose_b())
            goal_b = _np.array(self.get_goal_pose_b())
            u = self.env.unwrapped
            cube_q = u.scene["object"].data.root_quat_w[0]
            from aiongenos.tasks.WP1_contact_testbed.push_s3a_cfg import _CUBE_HALF_H
            tip_cube = _pb.point_to_box_dist(
                r.data.body_pos_w[0, tcp_idx, :3],
                u.scene["object"].data.root_pos_w[0, :3], cube_q, _CUBE_HALF_H)
            cube_goal = float(_np.linalg.norm(cube_b[:2] - goal_b[:2]))
            lines = ["SCAFFOLD (oracle-measured, disclosed):",
                     f"  LEFT_TIP_TO_CUBE = {tip_cube * 100:.1f} cm",
                     f"  CUBE_TO_GOAL     = {cube_goal * 100:.1f} cm"]
            if rung >= 3:
                def _xy(m):
                    (xi, yi, _), _ = position_metric_to_int(
                        float(m[0]), float(m[1]), 0.0,
                        bounds.x_bounds, bounds.y_bounds, bounds.z_bounds)
                    return xi, yi
                c, g = _xy(cube_b), _xy(goal_b)
                # deltas = differences of grid positions (the x map has an offset)
                lines += [f"  CUBE_POS     = (X={c[0]}, Y={c[1]})",
                          f"  GOAL_POS     = (X={g[0]}, Y={g[1]})",
                          f"  TIP_TO_CUBE  = (dX={c[0] - tx}, dY={c[1] - ty})",
                          f"  CUBE_TO_GOAL = (dX={g[0] - c[0]}, dY={g[1] - c[1]})"]
            out["oracle_block"] = "\n".join(lines) + "\n"
        return out

    def get_left_hand_quat_b(self):
        """Left hand (OSC body) orientation, base frame (root identity rot)."""
        return self.robot.data.body_quat_w[0, self.left_body_idx, :4].clone()

    def get_left_tcp_pos_b(self):
        from aiongenos.orchestrator import push_body as _pb
        r = self.robot
        tcp_idx = r.find_bodies(_pb.TCP_BODY)[0][0]
        return (r.data.body_pos_w[0, tcp_idx, :3] - r.data.root_pos_w[0, :3]).cpu().numpy().tolist()

    _TRANSPORT_LEAD_M = 0.06   # carrot lead: 3cm stalled at ~13.5cm short (OSC
                               # force from a 3cm error too small to keep moving);
                               # 6cm doubles the position error → sustained push
                               # while still well below the one-step-slam span.

    def execute_push_segment(self, approach_b, contact_quat_b, steps: int,
                             right_hold: bool = True, frame_every: int = 0,
                             target_is_tcp: bool = False):
        """Drive the LEFT OSC arm to a base-frame approach target + orientation,
        monitoring PRE-CLIP commanded torque per step (Rule 9, innermost loop).

        contact_quat_b (w,x,y,z, base frame) is the primitive-computed contact
        orientation = f(push_dir); the executor NEVER hard-codes a quat (that
        identity-quat 'gripper faces sky' bug was the PI's 5th human-eye catch).
        Orientation stiffness is softened (~1/5 of position) so an imperfect
        orientation guides the wrist rather than dragging it.

        frame_every>0: capture an RGB frame every N steps into the returned
        dict's "frames" (PNG bytes list) for the human-eye-gate GIF.

        Pin-9 TRANSPORT phase: the setpoint is CARROTED — each step it advances
        at most _TRANSPORT_LEAD_M toward the approach point FROM THE CURRENT EE
        (not the absolute far target), so OSC never sees a large position error
        (that one-step-slam span was the pre-clip τ 3.0 saturation). Once the EE
        reaches the approach point the setpoint pins to it (CONTACT phase = pure
        OSC in its ±12cm comfortable envelope). Approach point + lead clamp came
        from push_segment_from_waypoint (the primitive); this drives servo + τ.

        target_is_tcp=True (push interface 2026-10-05): approach_b is a TCP
        (fingertip) target, converted ONCE to the hand target under the
        commanded orientation with the live-measured hand-local TCP offset.
        Every step also logs the orientation error (deg, hand vs command) and
        the contact report (push_body): TCP / left-link distances to the cube
        box and the anatomy of the nearest link when the cube starts moving.
        """
        import torch as _torch
        from aiongenos.orchestrator import push_body as _pb
        u = self.env.unwrapped
        r = self.robot
        left_ids, _ = r.find_joints("openarm_left_joint.*")
        lid = _torch.tensor(left_ids, device=u.device)
        lim = _torch.tensor(self._ARM_TORQUE_LIMITS, device=u.device)
        ee_idx = self.left_body_idx
        act_dim = self.env.action_space.shape[-1]
        term = u.action_manager._terms.get("left_arm_action")
        root = r.data.root_pos_w[0, :3]

        tb = _torch.as_tensor(approach_b, device=u.device, dtype=_torch.float32)
        qb = _torch.as_tensor(contact_quat_b, device=u.device, dtype=_torch.float32)
        tcp_idx = r.find_bodies(_pb.TCP_BODY)[0][0]
        tcp_target_b = None
        table_clamp = None
        if target_is_tcp:
            # Safety interlock: never command the TCP into the static scene.
            if getattr(self, "_static_scene_b", None) is None:
                self._static_scene_b = _pb.measure_static_scene_b(self.env, r)
            raw = tb.clone()
            tb, hits = _pb.scene_guard(tb, self._static_scene_b)
            if hits:
                table_clamp = {"raw_tcp_target_b": [round(float(v), 4) for v in raw],
                               "guarded_tcp_target_b": [round(float(v), 4) for v in tb],
                               "colliders": hits}
                logger.warning(f"  SCENE GUARD {hits}: TCP target {[round(float(v), 3) for v in raw]} → "
                               f"{[round(float(v), 3) for v in tb]}")
            tcp_target_b = tb.clone()
            tcp_off = _pb.tcp_offset_local(r, ee_idx, tcp_idx)
            tb = _pb.hand_target_from_tcp(tb, qb, tcp_off)
        setpoint_clamps = 0
        # contact report state
        obj = u.scene["object"]
        from aiongenos.tasks.WP1_contact_testbed.push_s3a_cfg import _CUBE_HALF_H
        bodies = _pb.left_contact_bodies(r)
        cube0_w = obj.data.root_pos_w[0, :3].clone()
        tip_min = 1e9
        link_min = {n: 1e9 for _, n in bodies}
        first_move = None
        ori_err = []
        action = _torch.zeros((u.num_envs, act_dim), device=u.device)
        action[:, 3:7] = qb   # primitive-computed contact orientation (NOT identity)
        if act_dim >= 13:
            # variable_kp: slots 7-9 = position stiffness (firm), 10-12 =
            # orientation stiffness (soft, ~1/5) so an imperfect orientation
            # guides the wrist rather than dragging it (Pin-9a).
            action[:, 7:10] = 300.0
            action[:, 10:13] = 60.0

        peak_pre = 0.0; peak_post = 0.0; warn = 0; flag = 0
        per_step_pre = []
        frames = []
        dmin = 1e9
        for _si in range(steps):
            # carrot setpoint: current EE (base frame) + ≤lead toward approach
            ee_b = r.data.body_pos_w[0, ee_idx, :3] - root
            d = tb - ee_b
            dist = float(_torch.norm(d))
            if dist <= self._TRANSPORT_LEAD_M:
                setpoint = tb
            else:
                setpoint = ee_b + d / dist * self._TRANSPORT_LEAD_M
            if target_is_tcp:
                # guard every carrot setpoint too (the straight path from a
                # below-table-edge pose into the table footprint would cut it)
                sp_tcp = setpoint + _pb.quat_rotate(qb, tcp_off)
                sp_g, c = _pb.scene_guard(sp_tcp, self._static_scene_b)
                if c:
                    setpoint = sp_g - _pb.quat_rotate(qb, tcp_off)
                    setpoint_clamps += 1
            action[:, 0:3] = setpoint

            self.env.step(action)
            # POST-clip (actuator applied)
            post = float((r.data.applied_torque[0, lid].abs() / lim).max())
            # PRE-clip (OSC commanded, before actuator clip) — Rule 9 monitor
            pre = post
            if term is not None and hasattr(term, "_joint_efforts"):
                try:
                    pre = float((term._joint_efforts[0].abs() / lim).max())
                except Exception:
                    pre = post
            peak_pre = max(peak_pre, pre); peak_post = max(peak_post, post)
            per_step_pre.append(round(pre, 3))
            if pre > 0.85:
                warn += 1
            if pre >= 1.0:
                flag += 1
            # servo_err in the SAME frame as tb (BASE): ee_world − root, not
            # ee_world − tb (that cross-frame compare was the 66cm phantom;
            # the true base-vs-base error is ~13.5cm).
            ee_b_now = r.data.body_pos_w[0, ee_idx, :3] - root
            dmin = min(dmin, float(_torch.norm(ee_b_now - tb) * 100))

            ori_err.append(round(_pb.quat_angle_deg(r.data.body_quat_w[0, ee_idx, :4], qb), 2))
            cpos, cq = obj.data.root_pos_w[0, :3], obj.data.root_quat_w[0, :4]
            tip_min = min(tip_min, _pb.point_to_box_dist(r.data.body_pos_w[0, tcp_idx, :3], cpos, cq, _CUBE_HALF_H))
            dists = {n: _pb.point_to_box_dist(r.data.body_pos_w[0, i, :3], cpos, cq, _CUBE_HALF_H)
                     for i, n in bodies}
            for n, dv in dists.items():
                link_min[n] = min(link_min[n], dv)
            if first_move is None and float(_torch.norm(cpos - cube0_w)) > _pb.CUBE_MOVE_EPS_M:
                near = min(dists, key=dists.get)
                first_move = {"step": _si, "nearest_link": near, "anatomy": _pb.anatomy_of(near),
                              "nearest_dist_cm": round(dists[near] * 100, 2)}

            if frame_every and (_si % frame_every == 0):
                png = self.get_rgb()
                if png:
                    frames.append(png)

        ee_final = r.data.body_pos_w[0, ee_idx, :3]
        root = r.data.root_pos_w[0, :3]
        ee_final_b = (ee_final - root).cpu().numpy().tolist()
        return {
            "min_err_cm": dmin,
            "ee_final_b": [round(v, 4) for v in ee_final_b],
            "tau_peak_preclip": round(peak_pre, 3),
            "tau_peak_postclip": round(peak_post, 3),
            "tau_warn_steps": warn,      # steps with pre-clip τ/limit > 0.85
            "tau_flag_steps": flag,      # steps with pre-clip τ/limit >= 1.0
            "tau_pre_per_step": per_step_pre,
            "n_steps": steps,
            "frames": frames,            # PNG bytes (if frame_every>0) for the GIF
            "ori_err_deg": ori_err,      # per step, hand orientation vs command
            "ori_err_deg_final": ori_err[-1] if ori_err else None,
            "tcp_target_b": None if tcp_target_b is None else [round(float(v), 4) for v in tcp_target_b],
            "hand_target_b": [round(float(v), 4) for v in tb],
            "tcp_final_b": [round(float(v), 4) for v in (r.data.body_pos_w[0, tcp_idx, :3] - root)],
            "table_guard": {"target_clamp": table_clamp, "setpoint_clamp_steps": setpoint_clamps,
                            "static_scene_b": getattr(self, "_static_scene_b", None)},
            "contact": {
                "tcp_to_cube_min_cm": round(tip_min * 100, 2),
                "link_to_cube_min_cm": {n: round(v * 100, 2) for n, v in link_min.items()},
                "first_cube_move": first_move,       # None = cube never moved > 2mm
                "cube_disp_vec_cm": [round(float(v) * 100, 2) for v in (obj.data.root_pos_w[0, :3] - cube0_w)],
                "note": "link points are body origins (not meshes); TCP = fingertip pad",
            },
        }

    def get_cube_pose_b(self):
        """Cube (scene['object']) position in the robot base frame (x,y,z)."""
        u = self.env.unwrapped
        root = self.robot.data.root_pos_w[0, :3].cpu().numpy()
        cube_w = u.scene["object"].data.root_pos_w[0, :3].cpu().numpy()
        return (cube_w - root).tolist()

    def get_goal_pose_b(self):
        """Push goal (re-purposed left_ee_pose command term) in base frame."""
        u = self.env.unwrapped
        return u.command_manager.get_term("left_ee_pose").command[0, :3].cpu().numpy().tolist()

    def get_left_ee_pose_b(self):
        """Left EE position in the robot base frame (x,y,z) — translation
        (base root is identity-rot, verified). Used for the EEF motion
        direction that sets the neutral contact orientation."""
        root = self.robot.data.root_pos_w[0, :3].cpu().numpy()
        ee_w = self.robot.data.body_pos_w[0, self.left_body_idx, :3].cpu().numpy()
        return (ee_w - root).tolist()

