"""Whole-system specifications and adapters for executable science systems.

The public abstraction in this package is :class:`SystemSpec`.  Individual
mechanism APIs (including evaluation) are implementations referenced by a
specification; none of them is the root design object.
"""

from .legacy import (
    LegacyCompilationError,
    LegacyExecutionPlan,
    compile_legacy_system,
    legacy_candidate_to_system_spec,
)
from .model import (
    AgentTypeSpec,
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from .validation import (
    SystemSpecValidationError,
    ValidationIssue,
    ValidationReport,
    validate_system_spec,
)

__all__ = [
    "AgentTypeSpec",
    "ArtifactTypeSpec",
    "ChannelKind",
    "ConnectionSpec",
    "LegacyCompilationError",
    "LegacyExecutionPlan",
    "MechanismFamily",
    "MechanismSpec",
    "PortSpec",
    "ScheduleSpec",
    "SystemSpec",
    "SystemSpecValidationError",
    "ValidationIssue",
    "ValidationReport",
    "compile_legacy_system",
    "legacy_candidate_to_system_spec",
    "validate_system_spec",
]
