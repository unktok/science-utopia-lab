"""SCRIPTED actual-name failure diagnostics; not generated scientific policies."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, IMAGE, request
from tests.optimization.test_native_staged_author_v15 import apply
from utopia.optimization.native_authoring_ir import AuthoringIRDiagnostic
from utopia.optimization.native_field_addressing_v28 import (
    MAX_FEEDBACK_NAME_BYTES, MAX_FEEDBACK_NAMES, field_failure_catalog,
    field_index, field_operations, resolve_field)
from utopia.optimization.native_staged_author_v15 import initial_draft


@pytest.mark.parametrize('names,failed_index,prior', [
    (['thresholds', 'memory_gain'], 1, ['thresholds']),
    (['program.thresholds', 'program.memory_gain'], 0, []),
    (['program.parameters.thresholds', 'program.parameters.memory_cost'], 0, [])])
def test_actual_v33_failed_field_operands_remain_atomic_with_observed_names(names, failed_index, prior):
    from utopia.system.native_open_examples import open_native_system
    body = request()
    body['parent_system'] = open_native_system(IMAGE).to_dict()
    state = initial_draft(body)
    original = deepcopy(state)
    # Actual V33 G0 failed operands, not a supplied/new native candidate.
    action = {'tool': 'edit_fields', 'mechanism_id': 'addressed-selection',
              'field_updates': [{'field_name': names[0], 'value': [[3.], [4.]]},
                                {'field_name': names[1], 'value': .002}]}
    same, receipt = apply(state, action, body)
    assert not receipt['ok'] and same == state == original
    diagnostic = receipt['errors'][0]['diagnostics'][0]
    assert diagnostic['field_name'] == names[failed_index] and diagnostic['match_count'] == 0
    assert diagnostic['matching_field_paths'] == []
    assert diagnostic['failed_field_update_index'] == failed_index
    assert diagnostic['field_updates_applied'] == 0
    assert diagnostic['resolved_prior_field_names'] == prior
    assert diagnostic['successfully_resolved_prior_update_count'] == len(prior)
    catalog = diagnostic['observed_field_name_catalog']
    assert catalog['complete'] and catalog['omitted_name_count'] == 0
    assert 'thresholds' in catalog['unique_field_names'] and 'memory_cost' in catalog['unique_field_names']
    assert not set(names) - {'thresholds'} & set(catalog['unique_field_names'])
    expected = field_index(body['parent_system']['mechanisms'][15])
    assert catalog['unique_field_names'] == expected['unique_field_names']
    assert catalog['ambiguous_field_names'] == expected['ambiguous_field_names']


def test_ambiguity_catalog_is_observed_data_not_a_guessed_field_or_replacement_value():
    from utopia.system.native_open_examples import open_native_system
    document = open_native_system(IMAGE).to_dict()
    original = deepcopy(document)
    with pytest.raises(AuthoringIRDiagnostic) as error:
        resolve_field(document, 'addressed-selection', 'parameters')
    d = error.value.diagnostics[0]
    assert d['match_count'] == 2 and len(d['matching_field_paths']) == 2
    catalog = d['observed_field_name_catalog']
    assert catalog['ambiguous_field_names']['parameters'] == 2
    assert 'parameters' not in catalog['unique_field_names']
    assert document == original and 'value' not in catalog


@pytest.mark.parametrize('count', [2, 90])
def test_complete_literal_names_survive_caps_and_omitted_names_remain_addressable(count):
    node = {'mechanism_id': ALPHA, 'implementation': 'arbitrary.test.abi',
            'parameters': {f'field-{i:03d}': i for i in range(count)}}
    node['parameters']['huge-' + '界' * 1000] = 'SCRIPTED secret value never included'
    original = deepcopy(node)
    catalog = field_failure_catalog(node)
    names = [*catalog['unique_field_names'], *catalog['ambiguous_field_names']]
    assert len(names) <= MAX_FEEDBACK_NAMES and not catalog['complete'] and catalog['omission']
    assert catalog['total_name_count'] == len(names) + catalog['omitted_name_count']
    assert sum(len(json.dumps(n, ensure_ascii=False).encode()) for n in names) <= MAX_FEEDBACK_NAME_BYTES
    actual_names = field_index(node)['unique_field_names']
    assert set(names) <= set(actual_names)
    assert 'SCRIPTED secret value never included' not in json.dumps(catalog)
    omitted = next(name for name in actual_names if name not in names)
    assert resolve_field({'mechanisms': [node]}, ALPHA, omitted)['field_name'] == omitted
    assert node == original


@pytest.mark.parametrize('name,escaped', [
    ('program.parameters.thresholds', 'program.parameters.thresholds'),
    ('a/b~c', 'a~1b~0c'), ('研究者\n"name"', '研究者\n"name"')])
def test_literal_path_like_and_unicode_names_are_not_split_fuzzy_matched_or_rewritten(name, escaped):
    node = {'mechanism_id': ALPHA, 'parameters': {name: 'SCRIPTED literal value'}}
    resolution = resolve_field({'mechanisms': [node]}, ALPHA, name)
    assert resolution['root_path'] == '/mechanisms/0/parameters/' + escaped
    assert name in field_failure_catalog(node)['unique_field_names']


def test_valid_transactions_never_invoke_failure_catalog_or_change_literal_operations(monkeypatch):
    import utopia.optimization.native_field_addressing_v28 as fields
    node = {'mechanism_id': ALPHA, 'parameters': {'first': 1, 'second': 2}}
    def forbidden(*args, **kwargs):
        raise AssertionError('error catalog must not gate or transform successful updates')
    monkeypatch.setattr(fields, 'field_failure_catalog', forbidden)
    updates = [{'field_name': 'first', 'value': 'literal'}, {'field_name': 'second', 'value': [False, None]}]
    operations, resolutions = field_operations({'mechanisms': [node]}, ALPHA, updates)
    assert operations == [
        {'op': 'replace', 'path': '/mechanisms/0/parameters/first', 'value': 'literal'},
        {'op': 'replace', 'path': '/mechanisms/0/parameters/second', 'value': [False, None]}]
    assert [r['field_name'] for r in resolutions] == ['first', 'second']
    assert node['parameters'] == {'first': 1, 'second': 2}


def test_unknown_owner_is_not_substituted_and_prior_summary_is_explicitly_bounded():
    node = {'mechanism_id': ALPHA, 'parameters': {str(i) + 'x' * 300: i for i in range(12)}}
    document = {'mechanisms': [node]}
    with pytest.raises(AuthoringIRDiagnostic) as absent:
        field_operations(document, 'not-this-owner', [{'field_name': 'mechanism_id', 'value': 'x'}])
    assert 'observed_field_name_catalog' not in absent.value.diagnostics[0]
    updates = [{'field_name': k, 'value': 99} for k in node['parameters']]
    updates.append({'field_name': 'missing-name', 'value': 100})
    with pytest.raises(AuthoringIRDiagnostic) as failure:
        field_operations(document, ALPHA, updates)
    d = failure.value.diagnostics[0]
    assert d['failed_field_update_index'] == 12 and d['successfully_resolved_prior_update_count'] == 12
    assert len(d['resolved_prior_field_names']) + d['omitted_prior_field_name_count'] == 12
    assert d['omitted_prior_field_name_count'] > 0 and d['field_updates_applied'] == 0
