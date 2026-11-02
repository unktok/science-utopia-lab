"""Original six-year worlds, with scripted HTTP only; never actual Qwen."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim, original_science
from utopia.runtime.checkpointing import PortableStop
from utopia.system import ChannelKind, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CODE_SCHEMA, DockerCodeExecutor, sha
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.system.native_review_routing import (BATCH, PLAN, REVIEW, EVENT,
    enable_review_routing, review_input_batch, validate_routing_plan, validate_routing_receipt)
from utopia.system.runtime import GraphRuntimeError


SOURCE = '''import hashlib, json
def step(context):
    batch = context['inputs']['batch'][0]['payload']
    tasks = []
    for paper in batch['papers']:
        for reviewer in paper['eligible_reviewer_ids'][:REVIEWS]:
            tasks.append(dict(conference_id=paper['conference_id'], paper_id=paper['paper_id'], reviewer_id=reviewer))
    plan = dict(schema='native-review-routing-plan-v13', year=context['period'],
        batch_sha256=hashlib.sha256(json.dumps(batch,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest(), tasks=tasks)
    return dict(outputs={'routing':[{'payload':plan}]}, state={})
'''


def routed_system(image, *, reviews=1):
    base = legacy_world_system()
    source = MechanismSpec('invented-review-coordinator', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('batch', ChannelKind.ARTIFACT, BATCH),),
        outputs=(PortSpec('routing', ChannelKind.ARTIFACT, PLAN),),
        parameters={'runtime_image_id': image, 'code_artifact': {'schema': CODE_SCHEMA,
            'label': 'Scripted QA routing algorithm; not model invention',
            'source': 'REVIEWS = ' + repr(reviews) + '\n' + SOURCE,
            'inputs': {'batch': {'type': 'object'}}, 'outputs': {'routing': {'type': 'object'}},
            'state_schema': {'type': 'object'}}})
    base = replace(base, mechanisms=(*base.mechanisms, source),
        schedules=(*base.schedules, ScheduleSpec(source.mechanism_id, 110)))
    base = enable_review_routing(base, source=source.mechanism_id, source_port='routing')
    if reviews == 0:
        # Deliberate TEST-AUTHORED admission rule. Native legacy selection raises
        # on unreviewed papers; the routing host must not silently replace it.
        from utopia.system.native_selection_slot import selection_source_slot
        base = selection_source_slot(base, image_id=image)
        nodes = []
        for node in base.mechanisms:
            if node.mechanism_id == 'world.selection':
                parameters = deepcopy(node.parameters)
                parameters['code_artifact']['source'] = '''def step(context):
    world = context['inputs']['observations'][0]['payload']
    decisions = [{'payload':dict(paper_id=p['id'],conference_id=c['conference_id'],decision='accept',final_score=0)}
        for c in world['conferences']['conferences'] for p in c['submitted_papers']]
    return dict(outputs={'next':[{'payload':{'year':context['period']}}], 'world':[{'payload':world}],
        'decisions':decisions or [{'payload':{'empty_cycle':True}}]}, state={})
'''
                node = replace(node, parameters=parameters)
            nodes.append(node)
        base = replace(base, mechanisms=tuple(nodes))
    return base


def unit_batch():
    actors = {aid: SimpleNamespace(id=aid, can_review=True, conflict_of_interest=[]) for aid in ('a', 'b', 'c')}
    paper = dict(id='p', year=1, conference='venue', author_id='a', title='Actual paper')
    conference = SimpleNamespace(conference_id='venue', submitted_papers=[paper], status='unchanged', reviews={})
    sim = SimpleNamespace(conference_system=SimpleNamespace(conferences=[conference]),
        ecosystem=SimpleNamespace(agent_population=actors, get_agent_by_id=actors.__getitem__,
            get_available_reviewers=lambda exclude_agent_ids: [a for a in actors.values() if a.id not in exclude_agent_ids]),
        _get_all_author_ids=lambda p: [p['author_id']])
    batch = review_input_batch(sim, 1)
    plan = dict(schema=PLAN, year=1, batch_sha256=sha(batch),
        tasks=[dict(conference_id='venue', paper_id='p', reviewer_id='b')])
    return sim, batch, plan


@pytest.mark.parametrize('failure', ['paper', 'reviewer', 'conference', 'self', 'duplicate', 'year',
    'hash', 'unknown-field', 'batch-content', 'batch-eligibility', 'nonfinite', 'null-task', 'bool-year'])
def test_invalid_whole_command_fails_before_any_review_mutation(failure):
    sim, batch, plan = unit_batch()
    if failure in {'paper', 'reviewer', 'conference'}:
        plan['tasks'].append({**plan['tasks'][0], failure + '_id': 'unknown'})
    elif failure == 'self': plan['tasks'].append({**plan['tasks'][0], 'reviewer_id': 'a'})
    elif failure == 'duplicate': plan['tasks'].append(deepcopy(plan['tasks'][0]))
    elif failure == 'year': plan['year'] = 2
    elif failure == 'hash': plan['batch_sha256'] = '0' * 64
    elif failure == 'unknown-field': plan['accept_everything'] = True
    elif failure == 'batch-content': batch['papers'][0]['paper']['title'] = 'fabrication'
    elif failure == 'batch-eligibility': batch['papers'][0]['eligible_reviewer_ids'].append('a')
    elif failure == 'nonfinite': plan['tasks'][0]['reviewer_id'] = float('nan')
    elif failure == 'null-task': plan['tasks'].append(None)
    else: plan['year'] = True
    before = deepcopy(vars(sim.conference_system.conferences[0]))
    with pytest.raises((GraphRuntimeError, ValueError, TypeError)):
        validate_routing_plan(sim, 1, batch, plan)
    assert vars(sim.conference_system.conferences[0]) == before


def test_zero_plan_has_no_minimum_reviews_or_selection_policy():
    sim, batch, plan = unit_batch()
    plan['tasks'] = []
    assert validate_routing_plan(sim, 1, batch, plan) == {'p': []}


def test_native_coi_eligibility_is_explicit_not_a_metric_constraint():
    sim, _, _ = unit_batch()
    sim.ecosystem.agent_population['a'].conflict_of_interest = ['b']
    batch = review_input_batch(sim, 1)
    assert batch['papers'][0]['eligible_reviewer_ids'] == ['c']


@pytest.mark.parametrize('failure', ['batch-hash', 'command-hash', 'task-hash', 'count',
    'command-lineage', 'batch-lineage', 'task-identity'])
def test_saved_receipt_hash_and_work_identity_tampering_is_rejected(failure):
    _, batch, plan = unit_batch()
    tasks = deepcopy(plan['tasks'])
    receipt = dict(batch=batch, batch_sha256=sha(batch), command=plan, command_sha256=sha(plan),
        native_tasks=tasks, native_tasks_sha256=sha(tasks), actual_review_count=1,
        batch_origin={'input_event_ids': ['actual-batch-event']},
        command_origin={'input_event_ids': ['actual-code-event']})
    validate_routing_receipt(receipt)
    if failure == 'batch-hash': receipt['batch_sha256'] = '0' * 64
    elif failure == 'command-hash': receipt['command_sha256'] = '0' * 64
    elif failure == 'task-hash': receipt['native_tasks_sha256'] = '0' * 64
    elif failure == 'count': receipt['actual_review_count'] = 0
    elif failure == 'command-lineage': receipt['command_origin']['input_event_ids'] = []
    elif failure == 'batch-lineage': receipt['batch_origin']['input_event_ids'] = []
    else:
        receipt['native_tasks'][0]['reviewer_id'] = 'c'
        receipt['native_tasks_sha256'] = sha(receipt['native_tasks'])
    with pytest.raises(GraphRuntimeError): validate_routing_receipt(receipt)


@pytest.mark.parametrize('reviews', [0, 1])
def test_free_code_selects_exact_actual_native_work_and_original_records(tmp_path, fixed_corpus, monkeypatch, reviews):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    sim, calls = make_sim(tmp_path / 'routed', native=NativeScienceKernel(
        routed_system(executor.image_id, reviews=reviews), code_executor=executor))
    sim.run()
    receipts = [e for e in sim.native_system.events if e.event_type == EVENT]
    assert len(receipts) == 6
    tasks = [t for e in receipts for t in e.payload['native_tasks']]
    actual_calls = [p for (ctx, _, _), p in calls if ctx[0] == 'phase3_reviews']
    assert len(actual_calls) == len(tasks)
    assert len(tasks) == sum(len(e.payload['batch']['papers']) * reviews for e in receipts)
    assert bool(tasks) == bool(reviews)
    for event in receipts:
        receipt = event.payload
        validate_routing_receipt(receipt)
        assert receipt['actual_review_count'] == len(receipt['native_tasks'])
        assert receipt['command_origin']['source_mechanism'] == 'invented-review-coordinator'
        assert receipt['batch_origin']['source_mechanism'] == 'review-task-inputs'
        assert receipt['command_origin']['input_event_ids']
        for task in receipt['native_tasks']:
            assert type(task['native_score']) is int
            paper = sim.paper_tracker.papers_by_id[task['paper_id']]
            rows = [r for round_ in paper.review_history for r in round_['reviews']
                if r['reviewer_id'] == task['reviewer_id'] and r['year'] == event.year]
            assert len(rows) == 1
            assert sha(rows[0]) == task['native_review_sha256']
    checkpoint = sim.native_system.to_dict()
    assert NativeScienceKernel(sim.native_system.spec, checkpoint=checkpoint).to_dict() == checkpoint
    tampered = deepcopy(checkpoint)
    tampered['graph_checkpoint']['mechanism_states']['world.review']['receipt_sha256'] = '0' * 64
    with pytest.raises(GraphRuntimeError, match='persistent state'):
        NativeScienceKernel(sim.native_system.spec, checkpoint=tampered)
    assert not hasattr(sim, 'native_assignment')
    sim.llm.response_cache.close()


def test_routing_cold_restart_does_not_repeat_native_work(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    spec = routed_system(executor.image_id)
    reference, _ = make_sim(tmp_path / 'reference', native=NativeScienceKernel(spec, code_executor=executor))
    reference.run()
    seed()
    stopped, _ = make_sim(tmp_path / 'resume', native=NativeScienceKernel(spec, code_executor=executor), after_effects=True)
    with pytest.raises(PortableStop): stopped.run()
    stopped.llm.response_cache.close()
    resumed, _ = make_sim(tmp_path / 'resume', native=NativeScienceKernel(spec, code_executor=executor))
    resumed.run()
    assert science_snapshot(resumed) == science_snapshot(reference)
    assert resumed.native_system.to_dict() == reference.native_system.to_dict()
    reference.llm.response_cache.close()
    resumed.llm.response_cache.close()


def test_unused_capability_retains_exact_original_six_year_world(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    original, calls = make_sim(tmp_path / 'old')
    original.run()
    seed()
    native, new_calls = make_sim(tmp_path / 'new', native=NativeScienceKernel(legacy_world_system()))
    native.run()
    assert original_science(original) == original_science(native)
    assert [p for _, p in calls] == [p for _, p in new_calls]
    assert not any(e.event_type == EVENT for e in native.native_system.events)
    original.llm.response_cache.close()
    native.llm.response_cache.close()
