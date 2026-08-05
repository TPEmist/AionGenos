"""Tasks — IsaacLab environment configs for each curriculum level."""

import gymnasium as gym

# Register the L0a single-arm reach environments (V4: pre-L0 sub-stage).
gym.register(
    id="Isaac-AionGenos-L0a-Left-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.L0a_single_reach.single_reach_cfg:L0aSingleReachLeftEnvCfg",
    },
)
gym.register(
    id="Isaac-AionGenos-L0a-Right-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.L0a_single_reach.single_reach_cfg:L0aSingleReachRightEnvCfg",
    },
)

# Register the L0 reach two cubes environment
gym.register(
    id="Isaac-AionGenos-L0-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.L0_reach_two_cubes.reach_two_cubes_cfg:L0ReachTwoCubesEnvCfg",
    },
)

# Register the L1 dual trace environment
gym.register(
    id="Isaac-AionGenos-L1-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.L1_dual_trace.dual_trace_cfg:L1DualTraceEnvCfg",
    },
)

# Register the L2 dual push environment
gym.register(
    id="Isaac-AionGenos-L2-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.L2_dual_push.dual_push_cfg:L2DualPushEnvCfg",
    },
)

# Register the L3 pick & place environment
gym.register(
    id="Isaac-AionGenos-L3-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.L3_pick_place_close.pick_place_cfg:L3PickPlaceEnvCfg",
    },
)

# Register the WP1 contact test-bed (Paper 2, OSC controller). NEW task
# family; does NOT touch L0-L3 (which stay on DifferentialIK per Q1).
gym.register(
    id="Isaac-AionGenos-WP1-Contact-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_testbed_cfg:WP1ContactTestbedEnvCfg",
    },
)

# WP1-① OSC bisection s0: official OSC reach env + openarm single arm.
gym.register(
    id="Isaac-AionGenos-OSC-Bisect-S0-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_bisect_s0_cfg:OscBisectS0EnvCfg",
    },
)

# WP1-① OSC bisection s1: s0 + second arm (dual articulation, two OSC terms).
gym.register(
    id="Isaac-AionGenos-OSC-Bisect-S1-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_bisect_s1_cfg:OscBisectS1EnvCfg",
    },
)

# WP1-① OSC bisection s2: s1 + camera (isolate camera×OSC-reset).
gym.register(
    id="Isaac-AionGenos-OSC-Bisect-S2-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_bisect_s2_cfg:OscBisectS2EnvCfg",
    },
)
