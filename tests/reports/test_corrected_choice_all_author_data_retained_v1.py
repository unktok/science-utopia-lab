"""Dated original author/data records, not new scientific/cold proof."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((ROOT / 'research/results' / name).read_text())


def test_all8_journal_report_retains_every_edit_and_distinguishes_ast_from_effect():
    receipt = read('native-author-literal-changes-all8-v1.json')
    path = ROOT / receipt['retained_report']; report = checked(json.loads(path.read_text()))
    assert path.stat().st_size == receipt['report_bytes'] == 192849
    assert file_sha256(path) == receipt['report_file_sha256']
    assert report['content_sha256'] == receipt['report_content_sha256']
    assert report['analysis_source_commit'] == receipt['analysis_source_commit']
    assert report['scientific_source_commit'] == receipt['scientific_source_commit']
    assert receipt['public_export_exit_codes'] == [0, 0] and receipt['byte_equal']
    sessions = report['sessions']; assert len(sessions) == receipt['complete_original_sessions'] == 8
    assert len({s['request_sha256'] for s in sessions}) == 8
    assert all(s['terminal_status'] == 'generated' and s['completed_steps'] == 14 for s in sessions)
    assert sum(s['completed_steps'] for s in sessions) == receipt['completed_original_steps'] == 112
    edits = [e for s in sessions for e in s['edits']]
    assert len(edits) == receipt['edit_attempts'] == 25
    assert all(e['status'] == 'observed-literal-before-and-next-view' for e in edits)
    nodes = [n for e in edits for n in e['diagnostic']['node_changes']]
    assert len(nodes) == 25
    assert sum(n['standard_python_AST_equal'] is True for n in nodes) == receipt['changed_node_rows_with_equal_python_AST'] == 19
    assert sum(n['standard_python_AST_equal'] is False for n in nodes) == receipt['changed_node_rows_with_different_python_AST'] == 6
    assert all(n['before_source']['source_sha256'] != n['after_source']['source_sha256'] for n in nodes)
    assert all(not e['diagnostic']['connections']['literal_changed'] and not e['diagnostic']['schedules']['literal_changed'] for e in edits)
    assert all(not receipt[k] for k in ('source_repair', 'loss_changed', 'selection_changed',
        'novelty_or_merit_veto_added', 'whole_study_native_cold_audit_complete', 'publication_ready'))
    assert receipt['new_author_prompts_exposing_this_diagnostic'] == report['new_author_prompts_exposing_this_diagnostic'] == 0


def test_two_original_data_wait_headers_are_not_presented_as_completed_exports():
    receipt = read('native-corrected-choice-data-continuations-v1.json')
    assert receipt['status_at_recording'] == 'live-waiting-for-original-paired-readouts-not-exported'
    assert {r['kind'] for r in receipt['original_continuations']} == {'loss-paths', 'signed-content'}
    for row in receipt['original_continuations']:
        path = ROOT / row['retained_started']; header = checked(json.loads(path.read_text()))
        assert file_sha256(path) == row['started_file_sha256']
        assert header['analysis_source_commit'] == receipt['source_commit']
        assert header['scientific_source_commit'] == receipt['scientific_source_commit']
        assert header['preceding_readout_source_commit'] == receipt['preceding_readout_source_commit']
        assert header['kind'] == row['kind'] and header['pid'] == row['pid']
        assert header['maximum_wait_seconds'] == 86400
        assert not header['new_inference_allowed'] and not header['render_allowed'] and not header['retry_failed_stages']
    checks = receipt['checks']; junit = ROOT / checks['junit']
    assert file_sha256(junit) == checks['junit_file_sha256']
    suites = list(ET.parse(junit).getroot().iter('testsuite'))
    assert sum(int(s.attrib['tests']) for s in suites) == checks['passed'] == 91
    assert sum(int(s.attrib[k]) for s in suites for k in ('failures', 'errors', 'skipped')) == 0
    assert not receipt['actual_full_study_exports_complete'] and not receipt['publication_ready']


def test_both_free_four_step_cells_keep_nulls_losses_and_nonoperative_ast_change():
    value = read('native-corrected-choice-free-four-step-complete-v1.json'); rows = value['rows']
    assert len(rows) == 8 and {(r['objective'], r['generation']) for r in rows} == {
        (o,g) for o in ('content-utility', 'resource-aware-content') for g in range(4)}
    assert sum(r['status'] == 'complete' for r in rows) == value['complete'] == 7
    failed, = [r for r in rows if r['status'] == 'failed']
    assert failed['objective'] == 'content-utility' and failed['generation'] == 1
    assert all(failed[k] is None for k in ('loss', 'U', 'T', 'K_collected', 'uncollected'))
    complete = [r for r in rows if r['status'] == 'complete']
    for row in complete:
        assert row['loss'] == -row['U'] + (0.1 * row['K_collected'] if row['objective'] == 'resource-aware-content' else 0)
    assert value['tied'] + value['worse'] + value['better_than_assigned_reference'] == value['complete']
    assert value['better_than_assigned_reference'] == 0 and value['tied'] == 6
    last = value['latest_free_utility']
    assert last['final_source_AST_equal_to_parent'] is False
    assert last['all_scientist_inputs_and_choices_equal_to_actual_priority_zero_reference'] is True
    assert last['selection_receipts_joined_bijectively_to_native_events'] == 4
    assert last['actual_selection_years'] == [1,2,3,4]
    assert last['own_provider_body_sequence_sha256'] != last['reference_provider_body_sequence_sha256']
    assert all(value[k] is False for k in ('candidate_repaired_or_refilled', 'loss_changed_or_imputed',
        'final_selection_frozen', 'full_original_cold_closure_complete', 'publication_ready'))


def test_fixed_public_qa_runbook_is_prepared_not_completed_or_real_seed_dispatch():
    page = (ROOT / 'research/publication/native-corrected-choice-fixed-qa-runbook-v1.md').read_text()
    prepared = read('native-corrected-choice-data-continuations-v1.json')
    assert prepared['source_commit'] in page and prepared['source_worktree'] in page
    assert 'Prepared command — NOT RUN' in page and 'zero skips' in page
    assert 'SCIENCE_UTOPIA_CORRECTED_CHOICE_FIXED_PUBLIC_QA=1' in page
    assert '--basetemp=/Users/shiro/unktok/dev/science-utopia-lab-exports/' in page
    assert 'software seeds42/43003/43011' in page
    assert 'does not reserve hardware' in page and 'No scientific result or unusedness claim' in page
