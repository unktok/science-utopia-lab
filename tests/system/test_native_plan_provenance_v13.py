"""Prospective full-plan provenance; historical receipts are never rewritten."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from tests.system.test_native_activity_contracts import unit_plan, delivered
from utopia.system.code_mechanisms import sha
from utopia.system.native_activity_contracts import (
    AMENDMENT, apply_research_plans, reconstruct_applied_plan,
)
from utopia.system.runtime import GraphRuntimeError


@pytest.mark.parametrize('amend', [False, True])
def test_full_original_plan_snapshot_and_exact_reconstruction(amend):
    kernel, _, plan = unit_plan()
    original = deepcopy(plan)
    amendments = []
    if amend:
        assignment = deepcopy(plan['assignments'][0])
        assignment['detailed_focus'] = 'Arbitrary generated direction not present in base plan'
        command = dict(schema=AMENDMENT, target_year=1, assignment=assignment, submit=False)
        amendments.append(delivered(command))
    context = SimpleNamespace(inputs={'plans': (delivered(plan),), 'amendments': tuple(amendments)}, period=1)
    result = apply_research_plans(kernel, context)
    receipt = result.events[0].payload
    assert receipt['base_plan']['plan'] == original
    assert receipt['base_plan']['plan_sha256'] == sha(original)
    assert receipt['base_plan']['source_mechanism'] == 'arbitrary-director'
    assert receipt['base_plan']['source_port'] == 'plans'
    assert receipt['base_plan']['input_event_ids'] == ['actual-producer-event']
    assert reconstruct_applied_plan(receipt) == result.outputs['applied'][0].payload
    assert plan == original  # no accidental mutation of input provenance


@pytest.mark.parametrize('failure', ['base-content', 'base-hash', 'base-lineage', 'base-year',
    'amendment-content', 'final-hash', 'submitters', 'historical-missing-context'])
def test_missing_or_tampered_complete_context_is_not_claimed_reconstructable(failure):
    kernel, _, plan = unit_plan()
    command = dict(schema=AMENDMENT, target_year=1, assignment=deepcopy(plan['assignments'][0]), submit=False)
    context = SimpleNamespace(inputs={'plans': (delivered(plan),), 'amendments': (delivered(command),)}, period=1)
    receipt = deepcopy(apply_research_plans(kernel, context).events[0].payload)
    if failure == 'base-content': receipt['base_plan']['plan']['assignments'][0]['reason'] = 'tampered'
    elif failure == 'base-hash': receipt['base_plan']['plan_sha256'] = '0' * 64
    elif failure == 'base-lineage': receipt['base_plan']['input_event_ids'] = []
    elif failure == 'base-year': receipt['base_plan']['emitted_period'] = 2
    elif failure == 'amendment-content': receipt['amendments'][0]['command']['submit'] = True
    elif failure == 'final-hash': receipt['plan_sha256'] = '0' * 64
    elif failure == 'submitters': receipt['submit_actor_ids'] = []
    else: receipt.pop('base_plan')
    with pytest.raises(GraphRuntimeError): reconstruct_applied_plan(receipt)
