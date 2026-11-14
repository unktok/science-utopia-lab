import pytest

from scripts.native_workflow_submission_feedback_v1 import diagnose
from tests.optimization.test_native_workflow_submission_v1 import request
from utopia.optimization.native_workflow_submission_v1 import control_submission
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.system import SystemSpec
from utopia.system.design_patch import clone


def test_legal_control_is_not_changed_or_given_a_new_merit_filter(tmp_path):
    req = request(tmp_path / 'c'); s = control_submission(req); before = clone([req, s])
    result = diagnose(req, s)
    assert result['valid_under_original_compiler'] and result['original_compiler_error'] is None
    assert not result['causal_order_witnesses'] and not result['new_admission_rule']
    assert [req, s] == before and not result['graph_repaired']


def test_received_selection_phase_error_has_all_four_literal_causal_witnesses(tmp_path):
    req = request(tmp_path / 'c')
    # The actual retained free frame's selected parent is the stronger hand
    # control, not the fixture's R7 initial graph. Their edge5 producers differ.
    req['parent_system'] = post_funding_cost_control(SystemSpec.from_dict(req['parent_system'])).to_dict()
    s = {'phase_updates': {'developer-catalog-agenda': 1, 'developer-catalog-effects': 2,
        'open-source': 10, 'world.resubmissions': 30, 'world.selection': 40, 'world.submission': 70},
        'remove_connections': [], 'add_connections': [], 'rationale': 'SCRIPTED retained actual phase shape'}
    before = clone(s); result = diagnose(req, s)
    assert not result['valid_under_original_compiler'] and s == before
    assert result['original_compiler_error']['message'] == 'zero-latency data must precede its consumer; declare delayed memory explicitly'
    assert [r['candidate_connection_index'] for r in result['causal_order_witnesses']] == [5, 19, 20, 24]
    assert [r['source_phase'] for r in result['causal_order_witnesses']] == [70, 100, 110, 120]
    assert {r['target_phase'] for r in result['causal_order_witnesses']} == {40}


@pytest.mark.parametrize('bad', [{'rationality': 'wrong key'}, {'phase_updates': []}, None])
def test_malformed_model_json_remains_failed_feedback_not_a_host_exception(tmp_path, bad):
    result = diagnose(request(tmp_path / 'c'), bad)
    assert not result['valid_under_original_compiler'] and result['schema_errors']
    assert not result['causal_order_witnesses'] and not result['graph_repaired']
