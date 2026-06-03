"""Tasks — IsaacLab environment configs for each curriculum level."""

import gymnasium as gym

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
