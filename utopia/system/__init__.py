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
from .runtime import (
    CHECKPOINT_SCHEMA_VERSION,
    DeliveredValue,
    DeterministicGraphRunner,
    ExecutionRecord,
    GraphRunResult,
    GraphCheckpoint,
    GraphRuntimeError,
    MechanismContext,
    MechanismEvent,
    MechanismImplementation,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
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
    "CHECKPOINT_SCHEMA_VERSION",
    "ConnectionSpec",
    "DeliveredValue",
    "DeterministicGraphRunner",
    "ExecutionRecord",
    "GraphRunResult",
    "GraphCheckpoint",
    "GraphRuntimeError",
    "LegacyCompilationError",
    "LegacyExecutionPlan",
    "MechanismFamily",
    "MechanismContext",
    "MechanismEvent",
    "MechanismImplementation",
    "MechanismRegistry",
    "MechanismResult",
    "MechanismSpec",
    "MechanismValue",
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
