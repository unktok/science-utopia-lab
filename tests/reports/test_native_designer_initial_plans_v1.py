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
