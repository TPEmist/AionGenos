"""AionGenos MDP extensions (custom reset functions etc.).

Anything in here is meant to slot in alongside ``isaaclab.envs.mdp`` —
import-compatible signatures, config-class friendly. Add to this module
rather than monkey-patching upstream.
"""

from .reset import reset_joints_to_target_with_offset

__all__ = [
    "reset_joints_to_target_with_offset",
]
