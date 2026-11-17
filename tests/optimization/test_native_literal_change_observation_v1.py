"""SCRIPTED JSON/AST diagnostics, not toy-world scientific experiments."""
from copy import deepcopy

import pytest

from utopia.optimization.native_literal_change_observation_v1 import observe, MAX_SOURCE_BYTES
from utopia.system.code_mechanisms import CODE_SCHEMA, validate_code_artifact


def document():
    return {'system_id': 'SCRIPTED', 'mechanisms': [{
        'mechanism_id': 'office', 'implementation': 'code.python.v1',
        'parameters': {'policy': 'one', 'code_artifact': {
            'schema': CODE_SCHEMA, 'label': 'SCRIPTED standard native artifact',
            'inputs': {}, 'outputs': {}, 'state_schema': {},
            'source': 'def step(context):\n    return {"outputs": {}, "state": {}}\n'}}}],
        'connections': [{'source': 'a', 'target': 'b'}, {'source': 'b', 'target': 'c'}],
        'schedules': [{'node': 'office', 'phase': 'open'}], 'metadata': {'known': True}}


def test_fixture_uses_the_actual_native_artifact_contract_not_an_invented_language_field():
    artifact = document()['mechanisms'][0]['parameters']['code_artifact']
    validate_code_artifact(artifact)
    assert 'language' not in artifact and artifact['schema'] == CODE_SCHEMA


def test_literal_retention_is_allowed_without_a_novelty_or_gain_verdict():
    d = document(); before = deepcopy(d); r = observe(d, d)
    assert not r['literal_document_changed'] and r['node_change_count'] == 0
    assert r['node_changes'] == [] and r['other_root_fields_changed'] == []
    assert r['connections']['added_occurrences'] == r['connections']['removed_occurrences'] == 0
    assert all(not r[k] for k in ('source_repair', 'veto_on_finish', 'changes_loss', 'grants_world_authority'))
    assert all(r[k] == 0 for k in ('new_model_calls', 'new_native_worlds', 'new_source_executions'))
    assert not any(k in r for k in ('valid', 'improves', 'novel', 'plan_fulfilled', 'loss'))
    assert d == before


def test_changed_source_text_can_have_the_same_AST_without_claiming_world_equivalence():
    a = document(); b = deepcopy(a)
    b['mechanisms'][0]['parameters']['code_artifact']['source'] = '# SCRIPTED comment\ndef step(context):\n  return {"outputs": {}, "state": {}}\n'
    r = observe(a, b); row, = r['node_changes']
    assert r['literal_document_changed'] and r['node_change_count'] == 1
    assert row['standard_python_AST_equal'] and row['non_code_parameter_fields_changed'] == []
    assert row['before_source']['source_sha256'] != row['after_source']['source_sha256']
    assert 'not whole-program/world equivalence' in r['scope']


def test_parameter_change_is_visible_even_when_the_source_AST_is_unchanged():
    a = document(); b = deepcopy(a); b['mechanisms'][0]['parameters']['policy'] = 'two'
    r = observe(a, b); row, = r['node_changes']
    assert row['standard_python_AST_equal'] and row['non_code_parameter_fields_changed'] == ['policy']
    assert not r['veto_on_finish'] and not r['changes_loss']


def test_actual_AST_change_is_not_an_improvement_or_validity_certificate():
    a = document(); b = deepcopy(a)
    b['mechanisms'][0]['parameters']['code_artifact']['source'] = 'raise RuntimeError("SCRIPTED never execute")\n'
    r = observe(a, b); row, = r['node_changes']
    assert row['standard_python_AST_equal'] is False
    assert row['after_source']['status'] == 'parsed-without-execution'
    assert r['new_source_executions'] == 0 and not r['veto_on_finish']


@pytest.mark.parametrize('change', ['bool-int', 'int-float', 'missing-null'])
def test_literal_JSON_type_and_presence_differences_are_not_collapsed(change):
    a = document(); b = deepcopy(a)
    if change == 'bool-int': b['metadata']['known'] = 1
    elif change == 'int-float': a['metadata']['known'] = 1; b['metadata']['known'] = 1.0
    else: b['metadata']['extra'] = None
    r = observe(a, b)
    assert r['literal_document_changed'] and r['other_root_fields_changed'] == ['metadata']


def test_list_order_and_duplicate_wire_occurrences_remain_distinct():
    a = document(); b = deepcopy(a); b['connections'].reverse()
    r = observe(a, b)
    assert r['connections']['literal_changed'] and r['connections']['order_only_change']
    assert r['connections']['multiset_changed'] is False
    b['connections'].append(deepcopy(b['connections'][0])); r = observe(a, b)
    assert r['connections']['added_occurrences'] == 1 and r['connections']['removed_occurrences'] == 0
    assert r['connections']['order_only_change'] is False


def test_node_order_schedule_new_nodes_and_removed_nodes_are_reported_without_repair():
    a = document(); a['mechanisms'].append({'mechanism_id': 'other', 'parameters': {}})
    b = deepcopy(a); b['mechanisms'].reverse(); r = observe(a, b)
    assert r['mechanisms']['order_only_change'] and r['node_change_count'] == 0
    b = deepcopy(a); b['mechanisms'].pop(); b['mechanisms'].append({'mechanism_id': 'new', 'parameters': {}})
    b['schedules'][0]['phase'] = 'close'; r = observe(a, b)
    assert {(x['mechanism_id'], x['change']) for x in r['node_changes']} == {('new', 'added'), ('other', 'removed')}
    assert r['schedules']['added_occurrences'] == r['schedules']['removed_occurrences'] == 1


@pytest.mark.parametrize('kind', ['syntax', 'large', 'other-runtime', 'other-schema', 'nested'])
def test_unassessed_source_or_runtime_is_not_a_rejection_or_false_AST_equality(kind):
    a = document(); b = deepcopy(a); node = b['mechanisms'][0]
    if kind == 'syntax': node['parameters']['code_artifact']['source'] = 'def broken('
    elif kind == 'large': node['parameters']['code_artifact']['source'] = '#' * (MAX_SOURCE_BYTES + 1)
    elif kind == 'other-runtime': node['implementation'] = 'SCRIPTED.unrestricted.new-runtime'
    elif kind == 'other-schema': node['parameters']['code_artifact']['schema'] = 'SCRIPTED.new-artifact'
    else: node['parameters']['delegate'] = node['parameters'].pop('code_artifact')
    r = observe(a, b); row, = r['node_changes']
    assert row['standard_python_AST_equal'] is None
    assert not row['after_source']['status'].startswith('parsed') and not r['veto_on_finish']
    if kind == 'nested': assert row['non_code_parameter_fields_changed'] == ['delegate']


@pytest.mark.parametrize('kind', ['duplicate', 'missing-list', 'bad-node', 'non-object'])
def test_invalid_drafts_are_explicitly_unassessed_not_zero_changes(kind):
    a = document(); b = deepcopy(a)
    if kind == 'duplicate': b['mechanisms'].append(deepcopy(b['mechanisms'][0]))
    elif kind == 'missing-list': b['mechanisms'] = None
    elif kind == 'bad-node': b['mechanisms'].append(5)
    else: b = []
    r = observe(a, b)
    assert r['node_changes'] is r['node_change_count'] is None
    assert not r['veto_on_finish'] and not r['source_repair']


def test_row_budget_does_not_discard_total_change_count_or_restrict_new_nodes():
    a = document(); b = deepcopy(a)
    b['mechanisms'] += [{'mechanism_id': 'new-' + str(i), 'parameters': {}} for i in range(9)]
    r = observe(a, b, maximum_node_rows=2)
    assert r['node_change_count'] == 9 and len(r['node_changes']) == 2 and r['omitted_node_rows'] == 7
    assert len(b['mechanisms']) == 10 and not r['veto_on_finish']
    for bad in (True, 0, 129):
        with pytest.raises(ValueError): observe(a, b, maximum_node_rows=bad)
