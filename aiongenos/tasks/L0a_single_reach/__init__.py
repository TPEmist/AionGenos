"""L0a Single-arm reach — pre-L0 sub-stage attacking VLM mirror-bias.

Sensory-integration analogy: master *single-channel* (one EE + one target)
before the *dual-channel parallel* L0 task. See ``docs/plans/INDEX.md``
section V4 for design rationale.

Two registered environments:
- ``Isaac-AionGenos-L0a-Left-v0``: only the left arm acts; only one target
  cube is spawned in the left half-space.
- ``Isaac-AionGenos-L0a-Right-v0``: mirror image.
"""

from .single_reach_cfg import L0aSingleReachLeftEnvCfg, L0aSingleReachRightEnvCfg
