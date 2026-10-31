from copy import deepcopy

import pytest

from utopia.system.design_patch import apply_design_patch, make_patch, read_pointer
from utopia.system.native_kernel import legacy_world_system


def test_joint_graph_protocol_edit_is_atomic_not_a_fixed_menu():
    parent = legacy_world_system()
    document = parent.to_dict()
    new_type = {'artifact_type_id': 'novel-discussion', 'description': ''}
    node = {'mechanism_id': 'new-institution', 'family': 'custom', 'implementation': 'application.new.v1',
            'version': 1, 'inputs': [], 'outputs': [{'port_id': 'ideas', 'channel': 'artifact',
            'artifact_type': 'novel-discussion', 'required': True}], 'parameters': {'rules': {'any': [1, 2]}}}
    patch = make_patch(parent, [
        {'op': 'add', 'path': '/mechanisms/-', 'value': node},
        {'op': 'add', 'path': '/artifact_types/-', 'value': new_type},
        {'op': 'add', 'path': '/schedules/-', 'value': {'mechanism_id': 'new-institution', 'phase': 191, 'trigger': 'annual'}},
        {'op': 'replace', 'path': '/connections/0/latency', 'value': 1},
    ])
    child = apply_design_patch(parent, patch)
    assert child.mechanisms[-1].implementation == 'application.new.v1'
    assert child.connections[0].latency == 1
    assert parent.to_dict() == document
    # Implementation availability is an execution contract, not a finite family menu.


@pytest.mark.parametrize('operation', [
    {'op': 'replace', 'path': '/metadata/nonexistent', 'value': 1},
    {'op': 'remove', 'path': '/mechanisms/100'},
    {'op': 'add', 'path': '/unexpected-objective', 'value': 'wrong'},
    {'op': 'replace', 'path': '/schedules/00/phase', 'value': 1},
])
def test_invalid_edit_cannot_partially_mutate_parent(operation):
    parent = legacy_world_system()
    before = deepcopy(parent.to_dict())
    with pytest.raises((ValueError, KeyError)):
        apply_design_patch(parent, make_patch(parent, [operation]))
    assert parent.to_dict() == before


def test_parent_identity_and_noop_are_rejected():
    parent = legacy_world_system()
    patch = make_patch(parent, [{'op': 'replace', 'path': '/version', 'value': parent.version}])
    with pytest.raises(ValueError, match='no-op'):
        apply_design_patch(parent, patch)
    patch['parent_fingerprint'] = 'wrong'
    with pytest.raises(ValueError, match='parent'):
        apply_design_patch(parent, patch)
    assert read_pointer({'a/b': {'~': [42]}}, '/a~1b/~0/0') == 42
