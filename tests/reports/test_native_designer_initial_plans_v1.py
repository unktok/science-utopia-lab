"""Literal action extraction; script-only checks do not establish discovery."""
import pytest

from scripts.reports.native_designer_initial_plans_v1 import first_plan
from utopia.system.design_patch import digest


def step():
    value = {'step': 0, 'status': 'applied', 'transition': {'tool': 'plan', 'ok': True,
        'result': {'source_execution': False, 'literal_document_changed': False,
            'stored_model_authored_plan': {'design_intent': 'SCRIPTED hypothesis, not implementation',
                'implementation_targets': ['new/arbitrary.json'], 'objective_reasoning': 'SCRIPTED unmeasured claim'}}}}
    return {**value, 'content_sha256': digest(value)}


def test_plan_is_retained_literally_without_execution_or_semantic_repair():
    value = step(); before = digest(value)
    observed = first_plan(value)
    assert observed == value['transition']['result']['stored_model_authored_plan']
    observed['design_intent'] = 'changed local copy'
    assert digest(value) == before


@pytest.mark.parametrize('kind', ['changed-file', 'not-first', 'rejected', 'write', 'executed', 'mutated'])
def test_wrong_stage_or_rehashed_claim_is_not_a_literal_first_plan(kind):
    value = step()
    if kind == 'changed-file': value['status'] = 'other'
    if kind == 'not-first': value['step'] = 1
    if kind == 'rejected': value['transition']['ok'] = False
    if kind == 'write': value['transition']['tool'] = 'write_file'
    if kind == 'executed': value['transition']['result']['source_execution'] = True
    if kind == 'mutated': value['transition']['result']['literal_document_changed'] = True
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    with pytest.raises(ValueError): first_plan(value)


def test_all_retained_actual_initial_plans_keep_final_outcomes_and_own_original_source():
    import json
    from pathlib import Path
    from utopia.optimization.native_numeric_designer import checked
    from utopia.utils.data_utils import file_sha256
    root = Path(__file__).resolve().parents[2]; base = root/'research/data/native-designer-initial-plans-v1'
    manifest = checked(json.loads((base/'manifest.json').read_text()))
    plans = checked(json.loads((base/'plans.json').read_text()))
    report = checked(json.loads((root/'research/data/native-objective-instrument-loop-v1/report.json').read_text()))
    assert file_sha256(base/'plans.json') == manifest['plans_file_sha256']
    assert plans['original_report_content_sha256'] == report['content_sha256']
    assert plans['scientific_source_commit'] == report['source_commit']
    assert plans['original_audit_content_sha256'] == report['audit_sha256']
    assert len(plans['slots']) == 8 and len({s['request_sha256'] for s in plans['slots']}) == 8
    for row, slot in zip(plans['slots'], report['slots']):
        assert (row['objective'], row['generation'], row['request_sha256']) == (slot['objective'], slot['generation'], slot['request_sha256'])
        assert row['actual_native_status'] == slot['status'] and row['actual_assigned_loss'] == slot['loss']
        assert row['actual_changed_paths_from_parent'] == slot['changed_paths_from_parent']
        assert row['untrusted_initial_plan']['implementation_targets']
    assert sum(s['actual_native_status'] == 'failed' for s in plans['slots']) == 2
    assert not plans['new_model_calls'] and not plans['candidate_reselection']
