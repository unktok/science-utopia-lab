"""SCRIPTED compact-publication tests; no model/native execution or audit."""
from copy import deepcopy
import json

import pytest

from scripts import summarize_native_warmstart_v45 as summary
from utopia.system.design_patch import digest
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import file_sha256, write_json_atomic

SOURCE = 'd49cf0b' + 'a' * 33


def hashed(value):
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    return value


def fixture():
    system = legacy_world_system()
    parent = system.to_dict()
    runs, comparisons = {}, {}
    for arm in summary.ARMS:
        status, loss = ('complete', -7.) if arm == 'throughput' else ('technical-failure', None)
        metadata = {'technical_failures': [] if loss is not None else [
            {'run_id': 'new-native-run', 'seed': 42, 'error_type': 'TestFailure', 'error': 'SCRIPTED failure', 'loss': None}]}
        row = {'status': status, 'loss': loss, 'generation': 0, 'slot': 0,
            'observation': {'status': 'complete' if loss is not None else 'failed', 'loss': loss, 'metadata': metadata},
            'request_sha256': 'request-' + arm, 'observation_id': 'new-' + arm,
            'system_fingerprint': system.fingerprint, 'generation_error': None,
            'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': 7}},
            'lineage': {'vs_parent': {'from_fingerprint': system.fingerprint, 'to_fingerprint': system.fingerprint,
                'counts': {'source_changes': 0}, 'source_changes': [], 'scope': 'literal changes only'}}}
        record = {'request': {'parent_system': parent, 'based_on_observation_id': 'historical-parent',
                             'initial_evidence': {'bank_sha256': 'common-bank'}}}
        designer = {'generations': 1, 'dispatch_intents': 2, 'known_designer_responses': 1,
            'cost_measurements': {'prompt_tokens': {'record_count': 1, 'recorded_sum': 2000,
                'missing_cost_not_imputed': True}},
            'proofs': [{'request_sha256': 'request-' + arm, 'definition_sha256': 'definition-' + arm,
                'counts': {'dispatch_intents': 2}, 'result': {'status': 'generated'},
                'authoring_change': {'exact_document_changed': False},
                'completed_records': [{'step': 0, 'status': 'rejected',
                    'transition': {'tool': 'write_file', 'errors': [{'type': 'TestError', 'message': 'SCRIPTED bad ABI'}]}}, None]}]}
        runs[arm] = {'terminal': True, 'consumed_native_slots': 1, 'pending': None,
            'observations': [row], 'records': [record], 'designer': designer,
            'loss_spec': {'id': arm}, 'physical_researcher_responses': 20,
            'physical_response_caches': [{'path': '/SCRIPTED/new-cache.sqlite', 'sha256': 'scripted-cache'}]}
        comparisons[arm] = {'historical_initial_selection': {'loss': -7.,
            'selected_observation_id': 'historical-parent', 'tied_observation_ids': ['historical-parent', 'tie-two']},
            'new_best_loss': loss, 'historical_best_updated': False,
            'source_equivalence_established': False, 'new_slot_statuses': [status]}
    return hashed({'schema': summary.FULL_SCHEMA, 'source_commit': SOURCE,
        'classification': 'SCRIPTED-not-scientific-evidence', 'status': 'budget-complete-with-failures',
        'budget_terminal': True, 'consumed_native_slots': 2, 'technical_failures': 1,
        'plan_sha256': 'plan', 'initial_evidence_sha256': 'common-bank',
        'historical_source_audit': {'source_commit': 'historical-source', 'content_sha256': 'historical-audit'},
        'runs': runs, 'comparisons': comparisons, 'designer_costs': {'dispatch_intents': 4},
        'terminal_writer_and_progress': {'started': {'started_utc': '2026-11-07T00:00:00+00:00', 'pid': 123,
            'argv': ['SCRIPTED', '--output', '/SCRIPTED/raw']},
            'ended': {'ended_utc': '2026-11-07T00:00:10+00:00', 'status': 'exited', 'exit_code': 0}},
        'calibration_cold_replay': {'controls': 28, 'certificate_sha256': 'certificate', 'age_seconds': 12.5},
        'role_loading': {'explicit_empty_prompt_load_POSTs': 4},
        'claims': {'historical_initialization_is_not_new_improvement': True, 'source_equivalence_established': False},
        'new_model_calls_during_audit': 0, 'new_code_executions_during_audit': 0,
        'audit': {'raw_files_verified_unchanged': True, 'exact_authoring_and_native_truth_reused': True,
            'input_file_count': 20, 'input_inventory_sha256': 'inventory', 'source_proofs': {'files': {
                'research/protocols/campaigns/native-warmstart-v45-a1.md': 'protocol-sha'}}}})


def save(tmp_path, report=None):
    path = tmp_path / 'full-audit.json'
    if report is None:
        report = fixture()
        report['terminal_writer_and_progress']['started']['argv'] = ['SCRIPTED', '--output', str(tmp_path / 'raw')]
        hashed(report)
    write_json_atomic(path, report, sort_keys=True, allow_nan=False)
    return path


def test_failure_null_ties_source_ids_unknown_costs_and_no_new_audit_claim(tmp_path):
    path = save(tmp_path)
    before = path.read_bytes()
    first = summary.summarize_saved_audit(path, expected_source=SOURCE)
    assert first == summary.summarize_saved_audit(path, expected_source=SOURCE)
    assert path.read_bytes() == before
    assert first['full_audit']['file_sha256'] == file_sha256(path)
    assert first['full_audit']['content_sha256'] == json.loads(path.read_text())['content_sha256']
    assert first['status'] == 'budget-complete-with-failures'
    failed, good = first['arms']['efficiency'], first['arms']['throughput']
    assert failed['new_slot']['loss'] is None and failed['new_slot']['status'] == 'technical-failure'
    assert good['new_slot']['loss'] == -7.
    assert len(good['comparison']['historical_initial_selection']['tied_observation_ids']) == 2
    assert good['new_slot']['parent_system_fingerprint'] == good['new_slot']['system_fingerprint']
    assert good['authoring_generations'][0]['steps'][1]['status'] == 'interrupted-response-unknown'
    assert failed['new_slot']['technical_errors'][0]['message'] == 'SCRIPTED failure'
    assert first['writer']['elapsed_seconds'] == 10.
    assert first['calibration_times']['completed_utc'] is None
    assert first['calibration_times']['age_seconds_at_writer_start'] == 12.5
    assert not first['projection']['fresh_raw_or_scientific_audit']
    assert first['content_sha256'] == digest({k: v for k, v in first.items() if k != 'content_sha256'})
    encoded = json.dumps(first)
    assert 'parent_system"' not in encoded and 'literal_document' not in encoded


@pytest.mark.parametrize('mutation', ['hash', 'source', 'unfinished', 'extra-arm', 'loss-on-failure', 'unknown-status'])
def test_invalid_saved_audit_never_becomes_compact_success(tmp_path, mutation):
    report = fixture()
    if mutation == 'hash': report['claims']['source_equivalence_established'] = True
    elif mutation == 'source': report['source_commit'] = 'b' * 40
    elif mutation == 'unfinished': report['budget_terminal'] = False
    elif mutation == 'extra-arm': report['runs']['rogue'] = deepcopy(report['runs']['efficiency'])
    elif mutation == 'loss-on-failure': report['runs']['efficiency']['observations'][0]['loss'] = 0.
    else: report['runs']['efficiency']['observations'][0]['status'] = 'almost-complete'
    if mutation != 'hash': hashed(report)
    path = save(tmp_path, report)
    with pytest.raises(ValueError):
        summary.summarize_saved_audit(path, expected_source=SOURCE)


def test_generation_failure_has_no_candidate_and_is_not_historical_retention(tmp_path):
    report = fixture()
    row = report['runs']['efficiency']['observations'][0]
    row.update(status='generation-failure', observation=None, system_fingerprint=None,
        generation_error={'type': 'TestGenerationFailure', 'message': 'SCRIPTED no candidate', 'loss': None})
    result = summary.summarize_saved_audit(save(tmp_path, hashed(report)), expected_source=SOURCE)
    failed = result['arms']['efficiency']['new_slot']
    assert failed['status'] == 'generation-failure' and failed['system_fingerprint'] is None
    assert failed['loss'] is None and not failed['new_source_measurement']
    assert failed['generation_error']['type'] == 'TestGenerationFailure'


def test_parse_transport_error_lists_are_not_silently_dropped(tmp_path):
    report = fixture()
    step = report['runs']['efficiency']['designer']['proofs'][0]['completed_records'][0]
    step.update(status='invalid-response', transition=None,
        errors=[{'type': 'ValueError', 'message': 'SCRIPTED JSON function arguments malformed',
                 'diagnostics': {'raw_body_preserved_in_full_audit': True}}])
    result = summary.summarize_saved_audit(save(tmp_path, hashed(report)), expected_source=SOURCE)
    recorded = result['arms']['efficiency']['authoring_generations'][0]['steps'][0]
    assert recorded['status'] == 'invalid-response' and recorded['error'] is None
    assert recorded['errors'][0]['message'] == 'SCRIPTED JSON function arguments malformed'
    assert recorded['errors'][0]['error_sha256'] == digest(step['errors'][0])


def test_safe_fresh_output_outside_raw_and_full_audit(tmp_path):
    path = save(tmp_path)
    raw = tmp_path / 'raw'
    raw.mkdir()
    output = tmp_path / 'compact.json'
    result = summary.write_summary(path, output, expected_source=SOURCE, raw_run=raw)
    assert json.loads(output.read_text()) == result
    with pytest.raises(ValueError, match='fresh'):
        summary.write_summary(path, output, expected_source=SOURCE, raw_run=raw)
    with pytest.raises(ValueError, match='outside'):
        summary.write_summary(path, raw / 'not-allowed.json', expected_source=SOURCE, raw_run=raw)
    with pytest.raises(ValueError, match='fresh'):
        summary.write_summary(path, path, expected_source=SOURCE, raw_run=raw)
    link = tmp_path / 'link.json'
    link.symlink_to(tmp_path / 'missing.json')
    with pytest.raises(ValueError, match='fresh'):
        summary.write_summary(path, link, expected_source=SOURCE, raw_run=raw)


def test_input_symlink_and_duplicate_json_keys_rejected(tmp_path):
    path = save(tmp_path)
    link = tmp_path / 'input-link.json'
    link.symlink_to(path)
    with pytest.raises(ValueError, match='regular'):
        summary.summarize_saved_audit(link, expected_source=SOURCE)
    # A deliberately ambiguous incoming JSON frame is not parsed lossily.
    ambiguous = tmp_path / 'ambiguous.json'
    ambiguous.write_text('{"schema":"one","schema":"two"}')
    with pytest.raises(ValueError, match='Duplicate JSON key'):
        summary.summarize_saved_audit(ambiguous, expected_source=SOURCE)


def test_claimed_raw_directory_cannot_bypass_original_writer_identity(tmp_path):
    path = save(tmp_path)
    with pytest.raises(ValueError, match='original writer'):
        summary.write_summary(path, tmp_path / 'raw' / 'inside-original-raw.json',
            expected_source=SOURCE, raw_run=tmp_path / 'unrelated')
    assert not (tmp_path / 'raw' / 'inside-original-raw.json').exists()
