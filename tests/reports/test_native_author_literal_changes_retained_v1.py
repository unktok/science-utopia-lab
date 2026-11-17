"""Compact saved evidence checks, not new models/worlds or full native replay."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def evidence():
    receipt = json.loads((ROOT / 'research/results/native-author-literal-changes-preparation-v1.json').read_text())
    report = checked(json.loads((ROOT / receipt['actual_exports']['report']).read_text()))
    return receipt, report


def test_exact_command_report_and_post_commit_junit_remain_bound():
    receipt, report = evidence(); exports = receipt['actual_exports']; tests = receipt['tests']
    assert file_sha256(ROOT / exports['report']) == exports['report_file_sha256']
    assert report['content_sha256'] == exports['report_content_sha256']
    assert report['analysis_source_commit'] == receipt['analysis_source_commit']
    assert report['scientific_source_commit'] == receipt['scientific_source_commit']
    assert exports['exit_codes'] == [0, 0] and exports['byte_equal']
    junit = ROOT / tests['junit']; assert file_sha256(junit) == tests['junit_file_sha256']
    suites = list(ET.parse(junit).getroot().iter('testsuite'))
    assert sum(int(s.attrib['tests']) for s in suites) == tests['passed'] == 70
    assert sum(int(s.attrib['failures']) + int(s.attrib['errors']) for s in suites) == 0


def test_all_explicit_edit_attempts_stay_visible_with_receipt_and_ast_interface_layers():
    receipt, report = evidence(); rows = report['sessions']
    assert len(rows) == receipt['actual_exports']['explicit_sessions'] == 2
    assert sum(s['completed_steps'] for s in rows) == 28
    edits = [e for s in rows for e in s['edits']]
    assert len(edits) == receipt['actual_exports']['original_edit_attempts'] == 8
    assert [len(s['edits']) for s in rows] == [5, 3]
    for session in rows:
        assert session['terminal_status'] == 'generated' and not session['full_native_cold_replay']
        assert session['original_file_sha256']
    for edit in edits:
        assert edit['status'] == 'observed-literal-before-and-next-view'
        diag = edit['diagnostic']; assert diag['literal_document_changed']
        assert diag['node_change_count'] == 1 and diag['omitted_node_rows'] == 0
        node, = diag['node_changes']
        assert node['standard_python_AST_equal'] is True
        assert node['before_source']['source_sha256'] != node['after_source']['source_sha256']
        assert node['non_code_parameter_fields_changed'] == node['code_artifact_fields_except_source_changed'] == []
        assert not diag['connections']['literal_changed'] and not diag['schedules']['literal_changed']
        assert diag['other_root_fields_changed'] == []
        assert all(diag[k] is False for k in ('source_repair', 'veto_on_finish', 'changes_loss'))


def test_no_author_exposure_or_scientific_gain_is_inferred_and_positive_control_is_retained():
    receipt, report = evidence()
    for value in (receipt, report):
        assert all(value[k] == 0 for k in ('new_model_calls', 'new_native_worlds', 'new_probe_attempts',
            'new_authored_source_executions', 'new_author_prompts_exposing_this_diagnostic'))
        assert all(value[k] is False for k in ('source_repair', 'veto_on_finish', 'changes_loss', 'publication_ready'))
    control = json.loads((ROOT / receipt['genuine_numeric_parameter_control']).read_text())
    assert control['analysis_module_file_sha256'] == file_sha256(
        ROOT / 'utopia/optimization/native_literal_change_observation_v1.py')
    diag = control['numeric_parameter_control']['diagnostic']
    node, = diag['node_changes']
    assert node['standard_python_AST_equal'] is True
    assert node['non_code_parameter_fields_changed'] == ['topic_priorities']
    assert not receipt['followup_condition_adopted_or_dispatched']
    prototype = json.loads((ROOT / receipt['original_schema_coverage_failure_preserved_in']).read_text())
    assert prototype['prototype_initial_native_replay']['result'].startswith('unassessed standard artifact')
    assert control['prototype_record_file_sha256'] == file_sha256(ROOT / control['prototype_record'])
