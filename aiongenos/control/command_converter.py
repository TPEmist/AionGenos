"""command_converter — public re-export shim.

``convert_stage1_to_commands`` and ``convert_stage3_to_commands`` live in
``aiongenos.pipeline.stage2_attempt`` (next to the dataclasses they return).
This module re-exports them so that callers using the ``aiongenos.control``
namespace continue to work without modification.
"""

from aiongenos.pipeline.stage2_attempt import (  # noqa: F401
    convert_stage1_to_commands,
    convert_stage3_to_commands,
    BimanualCommand,
    MetricCommand,
)
