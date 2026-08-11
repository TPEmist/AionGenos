"""WP1 (Paper 2) gym registrations — ISOLATED from tasks/__init__.py.

Rationale (2026-08-05, 4th shared-resource incident — file-level):
`tasks/__init__.py` is intermittently rewritten by the IDE's Python
language server / format-on-save (Antigravity jedi-lsp), which silently
clobbered a WP1 gym.register mid-bisection. Same lesson as GPU→lockfile,
session→worktree, working-tree→worktree: ISOLATE, don't share. WP1's
registrations live here, in a file the IDE is not actively editing, and
`__init__.py` merely imports this module. A clobber of __init__'s import
line is one obvious line to re-check; a clobber of an inline register block
was invisible.

Imported at the end of tasks/__init__.py via `from . import wp1_registry`.
"""

import gymnasium as gym

# WP1 contact test-bed (OSC controller). NEW task family; does NOT touch
# L0-L3 (which stay on DifferentialIK per PI decision Q1).
gym.register(
    id="Isaac-AionGenos-WP1-Contact-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_testbed_cfg:WP1ContactTestbedEnvCfg",
    },
)

# WP1-① OSC bisection stages (A1 diagnosis: build up from official OSC reach).
gym.register(
    id="Isaac-AionGenos-OSC-Bisect-S0-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_bisect_s0_cfg:OscBisectS0EnvCfg",
    },
)
gym.register(
    id="Isaac-AionGenos-OSC-Bisect-S1-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_bisect_s1_cfg:OscBisectS1EnvCfg",
    },
)
gym.register(
    id="Isaac-AionGenos-OSC-Bisect-S2-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_bisect_s2_cfg:OscBisectS2EnvCfg",
    },
)
gym.register(
    id="Isaac-AionGenos-OSC-Bisect-S3-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_bisect_s3_cfg:OscBisectS3EnvCfg",
    },
)

# Single-variable test on the REAL test-bed: gripper actuator gains zeroed.
gym.register(
    id="Isaac-AionGenos-WP1-GripZero-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.osc_gripzero_cfg:WP1GripZeroEnvCfg",
    },
)

# WP1-③a real push: OSC test-bed + dynamic pushable cube.
gym.register(
    id="Isaac-AionGenos-WP1-Push-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "aiongenos.tasks.WP1_contact_testbed.push_s3a_cfg:WP1PushS3aEnvCfg",
    },
)
