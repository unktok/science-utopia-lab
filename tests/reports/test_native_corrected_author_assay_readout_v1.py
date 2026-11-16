"""SCRIPTED readout guards, not actual author/backend/native proof."""
from copy import deepcopy
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_corrected_author_assay_readout_v1 as reader
from utopia.system import SystemSpec
from utopia.system.design_patch import digest, make_patch

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/native_author_context_boundary_v1'


@pytest.fixture(autouse=True)
def no_model_or_generated_source(monkeypatch):
    def forbidden(*a, **kw): pytest.fail('readout must not call models or execute generated code')
    monkeypatch.setattr('requests.Session.post', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


def example():
    cases, rows = [], []
    for label in reader.LABELS:
        parent = json.loads((FIXTURES / (label + '.json')).read_text())
        request = {'parent_system': parent, 'SCRIPTED': label}
        cases.append({'label': label, 'request': request, 'request_sha256': digest(request)})
        rows.append({'label': label, 'request_sha256': digest(request), 'new_native_worlds': 0,
            'new_scientific_loss': None, 'free_submission_available': True,
            'implementation_phase_calls': 2, 'actual_calibration_records': 28,
            'actual_proposal_started_calls': 4,
            'public_proposal_result': {'definition': {'base_patch': None, 'factors': [], 'continuous': []}},
            'visibility': {'any_phase_interpretation_mismatch_calls': 0, 'uncommitted_responses': 0,
                'missing_or_different_loss_views': 0, 'phase_counts': {'implementation': 2, 'general': 2}},
            'generation_transport': [{'prompt_tokens': 100, 'completion_tokens': 5, 'done': True,
                'done_reason': 'stop'}, {'prompt_tokens': None, 'completion_tokens': None, 'done': None}]})
    plan = {'schema': reader.ASSAY + '.plan', 'source_commit': 'SCRIPTED-source',
        'content_sha256': 'SCRIPTED-plan', 'cases': cases}
    terminal = {'schema': reader.ASSAY + '.terminal', 'status': 'closed', 'completed_cases': 3}
    cold = {'schema': reader.ASSAY + '.cold', 'source_commit': plan['source_commit'],
        'plan_content_sha256': plan['content_sha256'], 'cases': [{k: deepcopy(row[k]) for k in (
            'label', 'free_submission_available', 'implementation_phase_calls',
            'actual_calibration_records', 'actual_proposal_started_calls')} for row in rows]}
    return plan, terminal, rows, cold


def test_all_three_known_cases_and_unknown_tokens_not_invention_or_zero_cost():
    inputs = example(); before = deepcopy(inputs); report = reader.project(*inputs)
    assert inputs == before
    assert [r['label'] for r in report['cases']] == list(reader.LABELS)
    assert all(not r['literal_base_change']['literal_base_changed'] for r in report['cases'])
    assert all(r['new_native_loss'] is None for r in report['cases'])
    usage = report['cases'][0]['free_transport_usage']
    assert usage['prompt_tokens'] == {'known_sum': 100, 'unknown_responses': 1}
    assert usage['output_tokens'] == {'known_sum': 5, 'unknown_responses': 1}
    assert usage['nonfinal_responses'] == 0 and usage['completion_signal_unknown'] == 1
    assert report['new_model_calls'] == report['new_generated_code_executions'] == report['new_native_worlds'] == 0
    assert not report['publication_ready'] and not report['selection_changed']


def test_calibration_completion_comes_from_original_provider_envelope_not_missing_flat_field():
    counts = reader.usage([{'prompt_tokens': 9, 'completion_tokens': 3,
        'response_payload': {'done': True, 'done_reason': 'stop'}}])
    assert counts['nonfinal_responses'] == counts['completion_signal_unknown'] == 0
    assert counts['prompt_tokens']['known_sum'] == 9


def test_known_no_submission_is_retained_without_a_parent_program():
    p, t, rows, cold = example()
    rows[1]['public_proposal_result']['definition'] = {'generation_failure': {'SCRIPTED': 'known finite null'}}
    rows[1]['free_submission_available'] = cold['cases'][1]['free_submission_available'] = False
    result = reader.project(p, t, rows, cold)['cases'][1]
    assert not result['free_submission_available'] and result['literal_base_change'] is None
    assert result['new_native_loss'] is None


def test_authored_source_change_is_literal_not_a_behavior_or_loss_claim():
    p, t, rows, cold = example(); parent = SystemSpec.from_dict(p['cases'][0]['request']['parent_system'])
    nodes = parent.to_dict()['mechanisms']; index = next(i for i, n in enumerate(nodes)
        if n['mechanism_id'] == 'developer-catalog-agenda')
    source = nodes[index]['parameters']['code_artifact']['source'] + '\n# SCRIPTED new literal version\n'
    rows[0]['public_proposal_result']['definition']['base_patch'] = make_patch(parent, [
        {'op': 'replace', 'path': f'/mechanisms/{index}/parameters/code_artifact/source', 'value': source}])
    change = reader.project(p, t, rows, cold)['cases'][0]['literal_base_change']
    assert change['literal_base_changed'] and change['changed_top_level_fields'] == ['mechanisms']
    assert [r['node_id'] for r in change['changed_source_nodes']] == ['developer-catalog-agenda']
    assert not change['added_node_ids'] and not change['removed_node_ids']
    assert change['new_native_loss'] is None and not change['mixed_distribution_instantiated']


def test_generated_factors_and_coordinates_are_counted_but_not_instantiated():
    p, t, rows, cold = example(); definition = rows[0]['public_proposal_result']['definition']
    definition['factors'] = [{'SCRIPTED': 'uninstantiated factor'}]
    definition['continuous'] = [{'SCRIPTED': 'uninstantiated coordinate'}]
    change = reader.project(p, t, rows, cold)['cases'][0]['literal_base_change']
    assert change['authored_factor_count'] == change['authored_continuous_coordinate_count'] == 1
    assert not change['mixed_distribution_instantiated'] and not change['literal_base_changed']


@pytest.mark.parametrize('problem', ['stopped', 'missing', 'reorder', 'cold', 'request', 'loss', 'world', 'phase', 'pending', 'fallback'])
def test_incomplete_or_mismatched_original_evidence_is_not_promoted(problem):
    p, t, rows, cold = example()
    if problem == 'stopped': t['status'] = 'stopped'
    elif problem == 'missing': rows.pop()
    elif problem == 'reorder': rows.reverse()
    elif problem == 'cold': cold['cases'][0]['actual_calibration_records'] = 99
    elif problem == 'request': p['cases'][0]['request']['SCRIPTED'] = 'changed'
    elif problem == 'loss': rows[0]['new_scientific_loss'] = -99.
    elif problem == 'world': rows[0]['new_native_worlds'] = 1
    elif problem == 'phase': rows[0]['visibility']['any_phase_interpretation_mismatch_calls'] = 1
    elif problem == 'pending': rows[0]['visibility']['uncommitted_responses'] = 1
    else: rows[0]['public_proposal_result']['definition'] = {'generation_failure': {'SCRIPTED': True}}
    with pytest.raises(ValueError): reader.project(p, t, rows, cold)


def test_wrong_patch_parent_is_not_repaired():
    p, t, rows, cold = example()
    patch = make_patch(SystemSpec.from_dict(p['cases'][1]['request']['parent_system']), [
        {'op': 'add', 'path': '/metadata/SCRIPTED', 'value': True}])
    rows[0]['public_proposal_result']['definition']['base_patch'] = patch
    with pytest.raises(ValueError): reader.project(p, t, rows, cold)


@pytest.mark.parametrize('inside', ['reader', 'raw', 'source'])
def test_output_preflight_precedes_source_or_writer_access(tmp_path, monkeypatch, inside):
    root = tmp_path / 'raw'; source = tmp_path / 'source'; output = {'reader': reader.ROOT / 'outputs/SCRIPTED',
        'raw': root / 'out', 'source': source / 'out'}[inside]
    def forbidden(*a): pytest.fail('unsafe output must reject before original source or writer access')
    monkeypatch.setattr(reader, 'pinned_revision', forbidden)
    with pytest.raises(ValueError, match='outside'):
        reader.export(SimpleNamespace(run=root, assay_source=source, output=output))


def test_live_original_writer_lock_is_not_bypassed(tmp_path, monkeypatch):
    root = tmp_path / 'raw'; root.mkdir(); source = tmp_path / 'source'
    monkeypatch.setattr(reader, 'pinned_revision', lambda p: 'SCRIPTED')
    with (root / 'writer.lock').open('w') as original:
        fcntl.flock(original, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            reader.export(SimpleNamespace(run=root, assay_source=source, output=tmp_path / 'out'))
    assert not (tmp_path / 'out').exists()
