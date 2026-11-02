"""Fabricated receipt-shape tests only; no source, world or model execution."""
from copy import deepcopy
from dataclasses import replace

import pytest

from scripts.native_activity_effect_audit_v12 import annual_activity_proof
from tests.system.test_native_activity_contracts import authored_system, unit_plan
from utopia.optimization.native_code_trace import validate_record
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest
from utopia.system.native_activity_contracts import AMENDMENT, EFFECT


def fixture():
    spec = authored_system('TEST-ONLY-image-no-execution')
    source = next(node for node in spec.mechanisms if node.mechanism_id == 'invented-project-director')
    _, _, base = unit_plan()
    assignment = deepcopy(base['assignments'][0])
    assignment['direction']['years'] = 2
    assignment['detailed_focus'] = 'TEST-ONLY-amended project'
    assignment['project_end_year'] = 2
    command = {'schema': AMENDMENT, 'target_year': 1, 'assignment': assignment, 'submit': False}
    base_event = {'event_id': 'TEST-base', 'sequence': 0, 'year': 1,
        'event_type': 'native.system.phase_executed', 'actor_ids': ['a', 'b'], 'payload': {'stage': 'research'},
        'provenance': {'mechanism_id': 'world.research', 'input_event_ids': []}}
    delivered = {'payload': base, 'source_mechanism': 'world.research', 'source_port': 'plans',
        'lineage_event_ids': ['TEST-base'], 'emitted_period': 1, 'available_period': 1}
    context = {'inputs': {'plans': [delivered]}, 'state': {}, 'random_seed': 1, 'period': 1}
    result = {'outputs': {'amendments': [{'payload': command}]}, 'state': {}}
    receipt = {'artifact_sha256': sha(source.parameters['code_artifact']), 'context_sha256': sha(context),
        'result_sha256': sha(result), 'image_id': source.parameters['runtime_image_id']}
    row = {'schema': 'scienceutopia.native-code-input.v1', 'binding': {'source_commit': 'TEST-only',
        'system_fingerprint': spec.fingerprint, 'run_id': 'TEST-no-native-execution'},
        'artifact': deepcopy(source.parameters['code_artifact']), 'context': context, 'result': result, 'receipt': receipt}
    row['bundle_sha256'] = sha(row)
    validate_record(row)
    code_event = {'event_id': 'TEST-code', 'sequence': 1, 'year': 1, 'event_type': 'generated.code_executed',
        'actor_ids': [], 'payload': deepcopy(receipt),
        'provenance': {'mechanism_id': source.mechanism_id, 'input_event_ids': ['TEST-base']}}
    applied = deepcopy(base)
    applied['assignments'][0] = deepcopy(assignment)
    applied['submit_actor_ids'] = ['b']
    origin = {'source_mechanism': source.mechanism_id, 'source_port': 'amendments', 'emitted_period': 1,
        'input_event_ids': ['TEST-code'], 'command_sha256': sha(command), 'command': deepcopy(command)}
    event = {'event_id': 'TEST-effect', 'sequence': 2, 'year': 1, 'event_type': EFFECT,
        'actor_ids': ['a', 'b'], 'payload': {'year': 1, 'plan_sha256': sha(applied),
            'submit_actor_ids': ['b'], 'amendments': [origin]},
        'provenance': {'mechanism_id': 'research-plan-effects', 'input_event_ids': ['TEST-base', 'TEST-code']}}
    actors = [{'id': item['actor_id'], 'project_start_year': item['project_start_year'],
        'project_end_year': item['project_end_year'], 'is_active': True,
        'newest_direction': {'direction': item['direction']['topic'], 'detailed_focus': item['detailed_focus'],
            'reason': item['reason']}} for item in applied['assignments']]
    saved = {'year': 1, 'native_system': {'events': [base_event, code_event, event]},
        'ecosystem_data': {'agents': actors}}
    return saved, spec, [row]


def test_exact_activity_command_native_timeline_submitter_and_generated_output_provenance():
    saved, spec, rows = fixture()
    original = deepcopy((saved, spec.to_dict(), rows))
    report = annual_activity_proof(saved, spec, rows)
    assert (saved, spec.to_dict(), rows) == original
    assert report['generated_amendment_output_matches'] == 1
    effect = report['effects'][0]
    assert effect['event_id'] == 'TEST-effect' and effect['event_sha256'] == digest(saved['native_system']['events'][-1])
    assert effect['submit_actor_ids'] == ['b']
    amendment = effect['amendments'][0]
    assert amendment['annual_actor_state']['id'] == 'a'
    assert amendment['annual_actor_state']['project_end_year'] == 2
    assert amendment['annual_actor_state_matches_assignment']
    assert amendment['origin']['input_event_ids'] == ['TEST-code']
    assert amendment['code_output_proofs'][0]['generated_event_ids'] == ['TEST-code']
    assert amendment['code_output_proofs'][0]['bundle_sha256'] == rows[0]['bundle_sha256']
    plan = effect['applied_plan_proof']
    assert plan['status'] == 'verified-hash-consistent-recorded-upstream-plan'
    assert sha(plan['plan']) == effect['event']['payload']['plan_sha256']
    assert plan['plan']['submit_actor_ids'] == ['b']
    assert plan['matching_base_contexts'][0]['upstream_value']['lineage_event_ids'] == ['TEST-base']


@pytest.mark.parametrize('tamper', ['commandhash', 'submitauthor', 'future', 'missinglineage', 'wrongwire',
    'codeoutput', 'codesource', 'actor', 'two-writers'])
def test_wrong_command_wire_lineage_or_recorded_output_is_rejected(tamper):
    saved, spec, rows = fixture()
    effect = saved['native_system']['events'][-1]
    origin = effect['payload']['amendments'][0]
    if tamper == 'commandhash': origin['command_sha256'] = 'forged'
    if tamper == 'submitauthor': effect['payload']['submit_actor_ids'].append('a')
    if tamper == 'future': saved['native_system']['events'][1]['sequence'] = 3
    if tamper == 'missinglineage': origin['input_event_ids'] = ['missing-event']
    if tamper == 'wrongwire': origin['source_port'] = 'undeclared-port'
    if tamper == 'codeoutput': rows[0]['result']['outputs']['amendments'] = []
    if tamper == 'codesource': rows[0]['artifact']['source'] += '# changed\n'
    if tamper == 'actor': effect['actor_ids'].append('not-an-actual-native-author')
    if tamper == 'two-writers': effect['payload']['amendments'].append(deepcopy(origin))
    with pytest.raises(ValueError):
        annual_activity_proof(saved, spec, rows)


def test_later_annual_snapshot_mismatch_is_reported_not_hidden_or_mistaken_for_invalidity():
    saved, spec, rows = fixture()
    saved['ecosystem_data']['agents'][0]['project_end_year'] = 3
    saved['native_system']['events'].append({'event_id': 'TEST-later-project', 'sequence': 3,
        'year': 1, 'event_type': 'native.domain.project_applied', 'actor_ids': ['a'],
        'payload': {'assignment': {'actor_id': 'a'}}, 'provenance': {}})
    item = annual_activity_proof(saved, spec, rows)['effects'][0]['amendments'][0]
    assert not item['annual_actor_state_matches_assignment']
    assert item['later_same_year_activity_or_project_effect_ids'] == ['TEST-later-project']


def test_base_plan_not_recorded_is_unavailable_not_fabricated():
    saved, spec, rows = fixture()
    rows[0]['context']['inputs']['plans'] = []
    proof = annual_activity_proof(saved, spec, rows)['effects'][0]
    assert proof['applied_plan_proof']['status'] == 'unavailable-recorded-upstream-plan'
    assert proof['applied_plan_proof']['plan'] is None
    assert proof['amendments'][0]['code_output_proofs']


def test_noncode_producer_keeps_explicit_receipt_without_fake_python_execution():
    saved, spec, rows = fixture()
    source = next(node for node in spec.mechanisms if node.mechanism_id == 'invented-project-director')
    noncode = replace(source, implementation='fixture.non-python', parameters={})
    spec = replace(spec, mechanisms=tuple(noncode if node.mechanism_id == source.mechanism_id else node for node in spec.mechanisms))
    item = annual_activity_proof(saved, spec, [])['effects'][0]['amendments'][0]
    assert item['code_output_attribution'] == 'not-a-python-source'
    assert item['code_output_proofs'] == []


def test_no_activity_effect_is_truthful_zero_count_not_native_project_surrogate():
    saved, spec, rows = fixture()
    saved['native_system']['events'] = saved['native_system']['events'][:2]
    report = annual_activity_proof(saved, spec, rows)
    assert report['effects'] == [] and report['generated_amendment_output_matches'] == 0
