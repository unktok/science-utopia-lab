"""Original six-year scientific phases; HTTP/retrieval only are scripted QA."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim, original_science
from utopia.runtime.checkpointing import PortableStop
from utopia.system import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CODE_SCHEMA, DockerCodeExecutor, sha
from utopia.system.native_activity_contracts import (
    AMENDMENT, EFFECT, PLAN, activity_world_system, add_activity_plan_authority, apply_research_plans,
    reconstruct_applied_plan,
)
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.system.runtime import DeliveredValue, GraphRuntimeError


class NoPrivateActivityFrame(NativeScienceKernel):
    def _stage(self, stage, context):
        assert not {'directions', 'authors', 'resubmissions', 'submissions'} & self._frame.keys()
        result = super()._stage(stage, context)
        assert not {'directions', 'authors', 'resubmissions', 'submissions'} & self._frame.keys()
        return result


@pytest.mark.parametrize('project_years', [1, 2])
def test_typed_path_contains_exact_original_six_year_science(tmp_path, fixed_corpus, monkeypatch, project_years):
    from tests.runtime import test_portable_checkpoint_integration as fixture
    monkeypatch.setattr(fixture, 'DIRECTION', next(d for d in fixture.AVAILABLE_DIRECTIONS if d.years == project_years))
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    reference, old_calls = make_sim(tmp_path / 'old')
    reference.run()
    seed()
    native, calls = make_sim(tmp_path / 'typed', native=NoPrivateActivityFrame(activity_world_system()))
    native.run()
    assert original_science(native) == original_science(reference), first_difference(original_science(native), original_science(reference))
    assert [p for _, p in calls] == [p for _, p in old_calls]
    assert len([e for e in native.native_system.events if e.event_type == EFFECT]) == 6
    assert len([e for e in native.native_system.events if e.event_type == 'native.system.phase_executed']) == 78
    reference.llm.response_cache.close()
    native.llm.response_cache.close()


def first_difference(a, b, path=''):
    if type(a) is not type(b): return path, a, b
    if isinstance(a, dict):
        if a.keys() != b.keys(): return path, list(a), list(b)
        for key in a:
            diff = first_difference(a[key], b[key], path + '/' + str(key))
            if diff: return diff
    elif isinstance(a, list):
        if len(a) != len(b): return path, len(a), len(b)
        for index, (left, right) in enumerate(zip(a, b)):
            diff = first_difference(left, right, path + '/' + str(index))
            if diff: return diff
    elif a != b: return path, a, b


SOURCE = '''def step(context):
    plan = context['inputs']['plans'][0]['payload']
    assignment = dict(plan['assignments'][0])
    assignment['detailed_focus'] = 'NATIVE_FREE_ACTIVITY_PROTOCOL: independent replication commons'
    # Arbitrary new research direction, not a host institution/topic catalogue.
    assignment['direction'] = dict(assignment['direction'])
    assignment['direction']['topic'] = 'Open-ended institutional measurement'
    assignment['direction']['keywords'] = ['replication', 'institutional design']
    if LATENCY:
        assignment['project_start_year'] = context['period'] + LATENCY
        assignment['project_end_year'] = assignment['project_start_year'] + assignment['direction']['years'] - 1
    amendment = dict(schema='native-research-amendment-v1', target_year=context['period'] + LATENCY,
        assignment=assignment, submit=assignment['project_end_year'] == context['period'] + LATENCY)
    return {'outputs': {'amendments': [{'payload': amendment}]}, 'state': {'cycles': context['period']}}
'''


def authored_system(image, *, connected=True, latency=0, submit=True):
    base = activity_world_system()
    node = MechanismSpec('invented-project-director', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('plans', ChannelKind.ARTIFACT, PLAN),),
        outputs=(PortSpec('amendments', ChannelKind.ARTIFACT, AMENDMENT),),
        parameters={'runtime_image_id': image, 'code_artifact': {'schema': CODE_SCHEMA,
            'label': 'Scripted free activity algorithm, not model invention',
            'source': 'LATENCY = ' + str(latency) + '\n' + SOURCE.replace(
                "submit=assignment['project_end_year'] == context['period'] + LATENCY",
                "submit=" + repr(submit) + " and assignment['project_end_year'] == context['period'] + LATENCY"),
            'inputs': {'plans': {'type': 'object'}}, 'outputs': {'amendments': {'type': 'object'}},
            'state_schema': {'type': 'object'}}})
    base = replace(base, mechanisms=(*base.mechanisms, node),
        schedules=(*base.schedules, ScheduleSpec(node.mechanism_id, 45)),
        connections=(*base.connections, ConnectionSpec('world.research', 'plans', node.mechanism_id, 'plans', ChannelKind.ARTIFACT)))
    return add_activity_plan_authority(base, source=node.mechanism_id, source_port='amendments', latency=latency) if connected else base


@pytest.mark.parametrize('latency', [0, 1])
def test_free_code_changes_actual_native_research_inputs_and_source_receipts(tmp_path, fixed_corpus, monkeypatch, latency):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    reference, old_calls = make_sim(tmp_path / 'off', native=NativeScienceKernel(authored_system(executor.image_id, connected=False, latency=latency), code_executor=executor))
    reference.run()
    seed()
    native, calls = make_sim(tmp_path / 'on', native=NativeScienceKernel(authored_system(executor.image_id, latency=latency), code_executor=executor))
    native.run()
    effected = [ctx[1] for (ctx, _, _), p in calls if ctx[0] == 'phase2_intentions' and 'NATIVE_FREE_ACTIVITY_PROTOCOL' in json.dumps(p)]
    assert min(effected) == 1 + latency
    assert not any('NATIVE_FREE_ACTIVITY_PROTOCOL' in json.dumps(p) for _, p in old_calls)
    effects = [e for e in native.native_system.events if e.event_type == EFFECT and e.payload['amendments']]
    assert len(effects) == 6 - latency
    events = {e.event_id: e for e in native.native_system.events}
    for event in effects:
        reconstructed = reconstruct_applied_plan(event.payload)
        assert sha(reconstructed) == event.payload['plan_sha256']
        base = event.payload['base_plan']
        assert base['source_mechanism'] == 'world.research'
        assert base['source_port'] == 'plans'
        assert base['input_event_ids']
        assert all(events[i].event_type == 'native.system.phase_executed' for i in base['input_event_ids'])
        for receipt in event.payload['amendments']:
            assert receipt['command_sha256'] == sha(receipt['command'])
            assert receipt['emitted_period'] + latency == event.year
            assert all(events[i].event_type == 'generated.code_executed' for i in receipt['input_event_ids'])
    assert any(a.newest_direction['direction'].topic == 'Open-ended institutional measurement'
        for a in native.ecosystem.get_available_authors())
    reference.llm.response_cache.close()
    native.llm.response_cache.close()


def test_delayed_activity_cold_restart_preserves_actual_society_and_queue(tmp_path, fixed_corpus):
    executor = DockerCodeExecutor()
    spec = authored_system(executor.image_id, latency=1)
    reference, _ = make_sim(tmp_path / 'reference', native=NativeScienceKernel(spec, code_executor=executor))
    reference.run()
    seed()
    stopped, _ = make_sim(tmp_path / 'resume', native=NativeScienceKernel(spec, code_executor=executor), after_effects=True)
    with pytest.raises(PortableStop):
        stopped.run()
    stopped.llm.response_cache.close()
    resumed, _ = make_sim(tmp_path / 'resume', native=NativeScienceKernel(spec, code_executor=executor))
    resumed.run()
    assert science_snapshot(resumed) == science_snapshot(reference)
    assert resumed.native_system.to_dict() == reference.native_system.to_dict()
    resumed.llm.response_cache.close()
    reference.llm.response_cache.close()


def unit_plan():
    from utopia.agents.research_direction import ResearchDirection
    actors = {aid: SimpleNamespace(id=aid, is_active=True, project_start_year=1, project_end_year=1,
        newest_direction={'direction': ResearchDirection('original', [], 1, [], []), 'detailed_focus': 'original', 'reason': ''}) for aid in ('a', 'b')}
    assignments = [dict(actor_id=aid, direction=a.newest_direction['direction'].to_dict(), detailed_focus='original',
        reason='', project_start_year=1, project_end_year=1) for aid, a in actors.items()]
    plan = dict(schema=PLAN, year=1, assignments=assignments, submit_actor_ids=['a', 'b'])
    kernel = SimpleNamespace(_simulation=SimpleNamespace(ecosystem=SimpleNamespace(get_available_authors=lambda: list(actors.values()))))
    return kernel, actors, plan


def delivered(payload, *, period=1):
    return DeliveredValue(ChannelKind.ARTIFACT, PLAN, payload, (), (), ('actual-producer-event',), 'arbitrary-director', 'plans', period, 1)


@pytest.mark.parametrize('failure', ['unknown', 'duplicate', 'timeline', 'inactive', 'stale', 'nonfinite', 'null-keywords', 'two-writers'])
def test_whole_plan_and_amendments_fail_before_actual_mutation(failure):
    kernel, actors, plan = unit_plan()
    plan['assignments'][0]['detailed_focus'] = 'must not commit'
    amendments = []
    if failure == 'unknown': plan['assignments'][1]['actor_id'] = 'invented-actor'
    elif failure == 'duplicate': plan['assignments'][1]['actor_id'] = 'a'
    elif failure == 'timeline': plan['assignments'][1]['project_end_year'] = 4
    elif failure == 'inactive': actors['b'].is_active = False
    elif failure == 'stale': plan['year'] = 0
    elif failure == 'nonfinite': plan['assignments'][1]['direction']['years'] = float('nan')
    elif failure == 'null-keywords': plan['assignments'][1]['direction']['keywords'] = None
    else:
        command = dict(schema=AMENDMENT, target_year=1, assignment=plan['assignments'][1], submit=True)
        amendments = [delivered(command), delivered(command)]
    before = deepcopy({aid: vars(a) for aid, a in actors.items()})
    ctx = SimpleNamespace(inputs={'plans': (delivered(plan),), 'amendments': tuple(amendments)}, period=1)
    with pytest.raises((GraphRuntimeError, ValueError)):
        apply_research_plans(kernel, ctx)
    assert {aid: vars(a) for aid, a in actors.items()} == before


def test_primary_full_bundle_can_itself_be_freely_authored_without_catalog():
    kernel, actors, plan = unit_plan()
    plan['assignments'][0]['direction']['topic'] = 'Never enumerated in the host'
    plan['submit_actor_ids'] = ['b']
    ctx = SimpleNamespace(inputs={'plans': (delivered(plan),), 'amendments': ()}, period=1)
    result = apply_research_plans(kernel, ctx)
    assert actors['a'].newest_direction['direction'].topic == 'Never enumerated in the host'
    assert result.outputs['applied'][0].payload['submit_actor_ids'] == ['b']


def test_missing_typed_data_blocks_consumers_instead_of_private_frame_fallback(tmp_path, fixed_corpus):
    from utopia.system.validation import SystemSpecValidationError
    spec = activity_world_system()
    spec = replace(spec, connections=tuple(c for c in spec.connections
        if not (c.target_mechanism == 'world.submission' and c.target_port == 'plans')))
    with pytest.raises(SystemSpecValidationError, match='required input has no incoming'):
        NativeScienceKernel(spec)
    spec = activity_world_system()
    spec = replace(spec, connections=tuple(replace(c, latency=1) if
        c.target_mechanism == 'world.submission' and c.target_port == 'plans' else c for c in spec.connections))
    sim, _ = make_sim(tmp_path / 'delayed-current-plan', native=NativeScienceKernel(spec))
    with pytest.raises(GraphRuntimeError, match='blocked'):
        sim.run()
    assert not sim.submitted_paper_ids
    sim.llm.response_cache.close()


def test_free_code_submission_choice_changes_actual_native_papers(tmp_path, fixed_corpus):
    executor = DockerCodeExecutor()
    native, calls = make_sim(tmp_path / 'gated', native=NativeScienceKernel(
        authored_system(executor.image_id, submit=False), code_executor=executor))
    native.run()
    assert native.yearly_results[0]['paper_submission']['num_papers_submitted'] == 3
    assert len([1 for (ctx, _, _), _ in calls if ctx[:2] == ('phase2_intentions', 1)]) == 3
    first_actor = native.ecosystem.get_available_authors()[0].id
    assert not any(first_actor in p.all_author_ids and p.year == 1
        for p in native.paper_tracker.papers_by_id.values())
    native.llm.response_cache.close()


@pytest.mark.parametrize('failure', ['unknown', 'duplicate', 'content', 'stale'])
def test_paper_batch_references_are_checked_without_touching_real_archive(failure):
    from utopia.data.paper_tracker import ArchivedPaper
    from utopia.system.native_activity_contracts import PAPERS, _read_papers
    actual = ArchivedPaper('actual-paper', 'Title', 'Abstract', 'a', 'university', 1, 'venue', 'pending')
    papers = [{**actual.to_dict(), 'type': 'resubmission'}]
    payload = dict(schema=PAPERS, year=1, kind='resubmission', papers=papers)
    if failure == 'unknown': papers.append({**papers[0], 'id': 'invented-paper'})
    elif failure == 'duplicate': papers.append(deepcopy(papers[0]))
    elif failure == 'content': papers[0]['abstract'] = 'fabricated science'
    elif failure == 'stale': payload['year'] = 0
    kernel = SimpleNamespace(_simulation=SimpleNamespace(paper_tracker=SimpleNamespace(papers_by_id={actual.id: actual})))
    ctx = SimpleNamespace(inputs={'papers': (delivered(payload),)}, period=1)
    before = deepcopy(actual.to_dict())
    with pytest.raises(GraphRuntimeError):
        _read_papers(kernel, ctx, 'resubmission')
    assert actual.to_dict() == before


def test_effect_can_defer_real_project_without_premature_submission():
    kernel, actors, plan = unit_plan()
    plan['assignments'][0]['direction']['years'] = 3
    plan['assignments'][0]['project_end_year'] = 3
    plan['submit_actor_ids'] = ['b']
    ctx = SimpleNamespace(inputs={'plans': (delivered(plan),), 'amendments': ()}, period=1)
    apply_research_plans(kernel, ctx)
    assert actors['a'].project_end_year == 3
    plan['submit_actor_ids'].append('a')
    with pytest.raises(GraphRuntimeError, match='completing this year'):
        apply_research_plans(kernel, ctx)


def test_builder_does_not_silently_replace_already_custom_activity_algorithms():
    with pytest.raises(GraphRuntimeError, match='original native stage interfaces'):
        activity_world_system(activity_world_system())
