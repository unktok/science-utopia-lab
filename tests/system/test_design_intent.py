from copy import deepcopy

import pytest

from utopia.system.design_intent import compile_design_intent, SCHEMA
from utopia.system.design_patch import apply_design_patch
from utopia.system.native_kernel import legacy_world_system


def intent():
    parent = legacy_world_system()
    return parent, {'schema': SCHEMA, 'parent_fingerprint': parent.fingerprint,
        'rationale': 'Free institution algorithms with stable graph references', 'changes': [
            {'op': 'artifact_type', 'artifact_type': {'artifact_type_id': 'new-policy-protocol'}},
            {'op': 'put_node', 'node': {'mechanism_id': 'invented-council', 'family': 'custom',
                'implementation': 'invented-institution.v7', 'inputs': [{'port_id': 'observations', 'channel': 'artifact', 'artifact_type': 'native-world-observation'}],
                'outputs': [{'port_id': 'policies', 'channel': 'artifact', 'artifact_type': 'new-policy-protocol', 'required': False}],
                'parameters': {'arbitrary_rule': {'not-a-fixed-menu': [1, 2, 3]}}}},
            {'op': 'schedule', 'schedule': {'mechanism_id': 'invented-council', 'phase': 191}},
            {'op': 'connect', 'connection': {'source_mechanism': 'world.publication', 'source_port': 'world',
                'target_mechanism': 'invented-council', 'target_port': 'observations', 'channel': 'artifact'}},
            {'op': 'deliver_to_researchers', 'source': 'invented-council', 'source_port': 'policies'}]}


def test_id_addressed_atomic_graph_edits_preserve_free_rules_and_install_native_delivery():
    parent, proposal = intent()
    before = parent.to_dict()
    child = apply_design_patch(parent, compile_design_intent(parent, proposal))
    assert parent.to_dict() == before
    assert child.mechanisms[-2].parameters['arbitrary_rule'] == {'not-a-fixed-menu': [1, 2, 3]}
    assert child.mechanisms[-1].implementation == 'native.world.researcher-context.v1'
    assert child.mechanisms[-1].inputs[0].artifact_type == 'new-policy-protocol'


def test_named_removal_cleans_incident_edges_and_schedules_without_index_shift():
    parent, proposal = intent()
    proposal['changes'] = [{'op': 'remove_node', 'id': 'world.communication'},
        {'op': 'connect', 'connection': {'source_mechanism': 'world.funding', 'source_port': 'next',
            'target_mechanism': 'world.close', 'target_port': 'after', 'channel': 'signal'}}]
    child = apply_design_patch(parent, compile_design_intent(parent, proposal))
    assert not any(n.mechanism_id == 'world.communication' for n in child.mechanisms)
    assert not any(c.source_mechanism == 'world.communication' or c.target_mechanism == 'world.communication' for c in child.connections)


@pytest.mark.parametrize('fault', ['parent', 'unknown', 'port', 'dangling'])
def test_intent_errors_are_not_silently_repaired_by_changing_algorithms(fault):
    parent, proposal = intent()
    if fault == 'parent': proposal['parent_fingerprint'] = 'stale'
    if fault == 'unknown': proposal['changes'][1]['node']['secret_field'] = True
    if fault == 'port': proposal['changes'][1]['node']['inputs'][0]['secret_field'] = True
    if fault == 'dangling': proposal['changes'][3]['connection']['target_port'] = 'not-defined'
    with pytest.raises(ValueError): compile_design_intent(parent, proposal)
