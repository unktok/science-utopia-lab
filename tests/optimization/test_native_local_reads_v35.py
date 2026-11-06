"""SCRIPTED syntactic hints; never execute/repair code or veto a candidate."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import code_node
from utopia.optimization.native_contract_notices import contract_notices, notice_summary


def document(source, *, parameters=None, inputs=None):
    node = code_node(); node['parameters'].update(parameters or {})
    node['parameters']['code_artifact']['source'] = source
    node['parameters']['code_artifact']['inputs'] = inputs or {}
    return {'mechanisms': [node]}


@pytest.mark.parametrize('namespace,key', [('parameters', 'arbitrary-local-value'), ('inputs', 'arbitrary-new-input')])
def test_missing_literal_local_reads_are_observed_not_filled_or_rebound(namespace, key):
    doc = document(f'def step(context):\n    return context[{namespace!r}][{key!r}]\n')
    # A neighbour having the key does NOT make it the current node's parameter/input.
    other = code_node('other-owner'); other['parameters'][key] = 'SCRIPTED neighbour value'
    doc['mechanisms'].append(other); before = deepcopy(doc)
    hints = [n for n in contract_notices(doc) if n['code'] == 'literal-local-context-key-not-present']
    assert len(hints) == 1
    h = hints[0]
    assert h['namespace'] == namespace and h['literal_key'] == key
    assert h['executed_mechanism_id'] == doc['mechanisms'][0]['mechanism_id']
    assert h['path'] == '/mechanisms/0/parameters/code_artifact/source'
    assert key not in h['observed_local_keys']
    assert h['changes_validity'] is False and h['native_execution_performed'] is False
    assert h['authored_value_changed_by_host'] is False and doc == before


def test_declared_keys_optional_get_dynamic_keys_and_other_implementations_are_not_assumed_missing():
    doc = document("def step(context):\n    a = context['parameters']['gain']\n    b = context['inputs']['known']\n"
        "    c = context['parameters'].get('optional')\n    d = context['inputs'][a]\n    return {}\n",
        inputs={'known': {'type': 'object'}})
    assert not contract_notices(doc)
    doc['mechanisms'][0]['implementation'] = 'arbitrary.other.implementation'
    doc['mechanisms'][0]['parameters']['code_artifact']['source'] = "context['inputs']['missing']"
    assert not contract_notices(doc)


@pytest.mark.parametrize('name', ['code_artifact', 'runtime_image_id'])
def test_reserved_editor_metadata_is_not_in_the_actual_code_handler_parameter_context(name):
    doc = document(f'def step(context):\n    return context["parameters"][{name!r}]\n')
    assert name in doc['mechanisms'][0]['parameters']
    hints = contract_notices(doc)
    assert len(hints) == 1 and hints[0]['literal_key'] == name
    assert name not in hints[0]['observed_local_keys']


def test_dead_or_caught_reads_remain_only_potential_syntactic_notices_not_a_validity_rule():
    doc = document("def step(context):\n    if False:\n        x = context['parameters']['not-reached']\n"
        "    try:\n        x = context['inputs']['caught']\n    except KeyError:\n        pass\n    return {}\n")
    hints = contract_notices(doc)
    assert len(hints) == 2 and all(not h['changes_validity'] for h in hints)
    assert all('reachability' in h['scope'] for h in hints)
    assert notice_summary(doc)['warning_is_not_a_veto']


def test_delegated_execution_owner_and_context_are_local_to_the_delegate():
    child = document("def step(context):\n    return context['parameters']['unknown']\n")['mechanisms'][0]
    wrapped = {'mechanism_id': 'outer-process', 'implementation': 'native.process.activity.v1',
        'parameters': {'delegate': child, 'unknown': 123}}
    hints = contract_notices({'mechanisms': [wrapped]})
    assert len(hints) == 1 and hints[0]['mechanism_id'] == 'outer-process'
    assert hints[0]['executed_mechanism_id'] == child['mechanism_id']
    assert hints[0]['path'] == '/mechanisms/0/parameters/delegate/parameters/code_artifact/source'


def test_notice_cap_is_explicit_and_syntax_errors_are_left_to_the_existing_validator():
    invalid = document('def step(:\n    THIS IS NOT EXECUTED')
    assert not contract_notices(invalid)
    source = 'def step(context):\n' + ''.join(f"    x = context['parameters']['key-{i}']\n" for i in range(12))
    doc = document(source); summary = notice_summary(doc, limit=3)
    assert summary['total_count'] == 12 and summary['included_count'] == 3
    assert summary['omitted_count'] == 9 and not summary['complete'] and summary['omission']


def test_observed_local_key_names_are_whole_literal_names_with_explicit_byte_count_omissions():
    values = {f'long-name-{i}-' + '界' * 60: i for i in range(90)}
    doc = document("def step(context):\n    return context['parameters']['absent']\n", parameters=values)
    h = contract_notices(doc)[0]; names = h['observed_local_keys']
    assert len(names) <= 64 and sum(len(json.dumps(n, ensure_ascii=False).encode()) for n in names) <= 2048
    assert set(names) <= set(doc['mechanisms'][0]['parameters'])
    assert h['observed_local_key_count'] == len(names) + h['observed_local_keys_omitted_count']
    assert h['observed_local_keys_omitted_count'] and not h['observed_local_keys_complete']
