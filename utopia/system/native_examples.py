"""Convenience composition over an open native graph, not a rule catalog."""
from dataclasses import replace

from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, ScheduleSpec
from .native_kernel import add_context_receiver
from .validation import validate_system_spec


def connect_native_institution(spec, institution, *, observe="world.publication",
                               input_port="observations", phase=190,
                               researcher_output=None, delivery_latency=0):
    """Attach ANY registered/code/LLM implementation to real native records.

    New artifact kinds are inferred from the explicitly declared ports, not
    selected from evaluation/funding categories. Caller supplies algorithms.
    """
    artifacts = {a.artifact_type_id: a for a in spec.artifact_types}
    for port in (*institution.inputs, *institution.outputs):
        if port.artifact_type and port.artifact_type not in artifacts:
            artifacts[port.artifact_type] = ArtifactTypeSpec(port.artifact_type)
    result = replace(spec, artifact_types=tuple(artifacts.values()),
        mechanisms=(*spec.mechanisms, institution), schedules=(*spec.schedules, ScheduleSpec(institution.mechanism_id, phase)),
        connections=(*spec.connections, ConnectionSpec(observe, "world", institution.mechanism_id,
                                                      input_port, ChannelKind.ARTIFACT)))
    if researcher_output:
        result = add_context_receiver(result, source=institution.mechanism_id,
            source_port=researcher_output, latency=delivery_latency)
    validate_system_spec(result).require_valid()
    return result
