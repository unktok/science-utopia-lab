"""Current original researcher world/Docker, scripted replies, not Qwen evidence."""
from copy import deepcopy
from dataclasses import replace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, BINDING
from tests.system.test_native_science_kernel import make_sim
from tests.system.test_native_review_routing_v13 import SOURCE
from tests.optimization.test_native_causal_design import IMAGE, routing_domain
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.system import ChannelKind, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CODE_SCHEMA
from utopia.system.native_information_institution import information_system, information_design_space
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.native_review_routing import BATCH, PLAN, EVENT, enable_review_routing, validate_routing_receipt
from utopia.system.runtime import GraphRuntimeError
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic
from utopia.optimization.native_benchmark_controls import selection_control
from utopia.optimization.native_world import measure_native_world


def source_system(reviews):
    system = information_system(IMAGE)
    source = MechanismSpec('review-coordinator', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('batch', ChannelKind.ARTIFACT, BATCH),),
        outputs=(PortSpec('routing', ChannelKind.ARTIFACT, PLAN),),
        parameters={'runtime_image_id': IMAGE, 'code_artifact': {'schema': CODE_SCHEMA,
            'label': 'Developer-authored native connection control, not a discovered rule',
            'source': 'REVIEWS = ' + repr(reviews) + '\n' + SOURCE,
            'inputs': {'batch': {'type': 'object'}}, 'outputs': {'routing': {'type': 'object'}},
            'state_schema': {'type': 'object'}}})
    system = replace(system, mechanisms=(*system.mechanisms, source),
        schedules=(*system.schedules, ScheduleSpec(source.mechanism_id, 87)))
    return system


def current_routed_system(reviews):
    return enable_review_routing(source_system(reviews), source='review-coordinator',
        source_port='routing', snapshot_phase=85)


def test_legacy_scope_rejects_but_explicit_new_scope_allows_real_routing():
    anchor = information_system(IMAGE); candidate = current_routed_system(1)
    with pytest.raises(ValueError, match='duplicate or replace'):
        require_candidate_in_space(anchor, candidate,
            information_design_space(anchor, 'code-and-graph', fixed_production=True))
    require_candidate_in_space(anchor, candidate, routing_domain(anchor))
    with pytest.raises(ValueError):
        require_candidate_in_space(anchor, candidate, routing_domain(anchor, 'code-fixed-graph'))


def test_actual_default_routing_phases_are_not_silently_rewritten():
    spec = current_routed_system(1)
    assert {s.mechanism_id:s.phase for s in spec.schedules}['world.review'] == 90
    # The builder was explicitly85/87. Original105 defaults cannot be silently
    # applied to this new graph to produce a fictitious valid candidate.
    with pytest.raises(GraphRuntimeError, match='ordered'):
        enable_review_routing(source_system(1), source='review-coordinator', source_port='routing')


def test_two_routing_rules_execute_in_current_world_with_equal_pre_review_inputs(tmp_path, fixed_corpus, monkeypatch):
    records = []
    for count, admission in ((1, 'reject-all'), (2, 'reject-all'), (2, 'accept-all')):
        seed(); system = selection_control(current_routed_system(count), rule=admission)
        monkeypatch.setitem(BINDING, 'cell', system.fingerprint)
        kernel = NativeScienceKernel(system)
        sim, calls = make_sim(tmp_path/(str(count)+'-'+admission), native=kernel); sim.num_years = 2
        try:
            sim.run()
            receipts = [e.payload for e in kernel.events if e.event_type == EVENT]
            assert receipts and kernel.last_year == 2
            for receipt in receipts:
                validate_routing_receipt(receipt)
                expected = sum(min(count, len(p['eligible_reviewer_ids'])) for p in receipt['batch']['papers'])
                assert receipt['actual_review_count'] == expected
            before = [deepcopy((ctx,payload)) for (ctx,_,_),payload in calls
                if ctx[1] == 1 and not ctx[0].startswith('phase3')]
            assert before
            # Only compare calls BEFORE the first actual review. Later calls
            # can legitimately depend on changed review work/decisions.
            first_review = next(i for i,((ctx,_,_),_) in enumerate(calls) if ctx[0].startswith('phase3'))
            before = deepcopy(calls[:first_review])
            records.append({'requested_reviews_per_paper':count, 'admission':admission,
                'system':system.to_dict(), 'pre_review_requests':before,
                'first_year_batch':receipts[0]['batch'],
                'first_year_actual_review_count':receipts[0]['actual_review_count'],
                'routing_receipts':receipts, 'measurement':measure_native_world(sim, run_id='SCRIPTED-connection')})
        finally:
            sim.llm.response_cache.close()
    assert records[0]['pre_review_requests'] and all(r['pre_review_requests']==records[0]['pre_review_requests'] for r in records[1:])
    assert all(r['first_year_batch']==records[0]['first_year_batch'] for r in records[1:])
    assert 0 < records[0]['first_year_actual_review_count'] < records[1]['first_year_actual_review_count']
    assert records[1]['first_year_actual_review_count'] == records[2]['first_year_actual_review_count']
    result = {'schema':'scienceutopia.current-native-routing-connection.v1', 'worlds':records,
        'scope':'Three developer-authored controls; original lifecycle/Docker, scripted researcher replies/corpus. Not local-LLM invention or method superiority.',
        'new_local_llm_calls':0, 'pre_review_payloads_equal':True,
        'late_admission_does_not_change_first_year_review_work':True}
    result['content_sha256'] = digest(result)
    write_json_atomic(tmp_path/'connection-receipt.json', result, sort_keys=True, allow_nan=False)
