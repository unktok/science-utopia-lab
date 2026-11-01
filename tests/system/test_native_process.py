"""Original native science plus data-authored process control, not a toy world."""
from dataclasses import replace
import json

import pytest

from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
                           MechanismSpec, PortSpec, ScheduleSpec, SystemSpec)
from utopia.system.runtime import (DeterministicGraphRunner, GraphRuntimeError,
    MechanismEvent, MechanismRegistry, MechanismResult, MechanismValue)
from utopia.system.native_process import (CONTROL, DONE, compile_dependencies,
    controlled_activity, register_native_process)
from utopia.system.native_activity_contracts import PLAN, AMENDMENT, EFFECT, activity_world_system, add_activity_plan_authority
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.code_mechanisms import CODE_SCHEMA, DockerCodeExecutor
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim, original_science


def registry_extension(kernel, registry):
    register_native_process(kernel, registry)


def test_dependency_compiler_preserves_original_six_year_science_and_all_requests(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    old, old_calls = make_sim(tmp_path / 'original')
    old.run()
    seed()
    spec = activity_world_system()
    # Explicit contract; ordering within the DAG is derived from actual data
    # edges and declared dependencies, not a mandatory host serial stage list.
    deps = {n.mechanism_id: [] for n in spec.mechanisms}
    deps['world.resubmissions'] = ['world.open']
    deps['world.research'] = ['world.open']
    deps['world.costs'] = ['world.submission']
    deps['world.review'] = ['world.costs']
    deps['world.selection'] = ['world.review']
    deps['world.citation-potential'] = ['world.publication']
    deps['world.funding'] = ['world.citation-potential']
    deps['world.communication'] = ['world.funding']
    deps['world.close'] = ['world.communication']
    compiled = compile_dependencies(spec, deps, detach_serial=True)
    assert not any(e.target_port == 'after' for e in compiled.connections)
    native, calls = make_sim(tmp_path / 'compiled', native=NativeScienceKernel(compiled, registry_extension=registry_extension))
    try:
        native.run()
        assert original_science(native) == original_science(old)
        assert [p for _, p in calls] == [p for _, p in old_calls]
        assert native.native_system.last_year == 6
    finally:
        native.llm.response_cache.close(); old.llm.response_cache.close()


def counter_system(count=3, enabled=True, until=None):
    producer = MechanismSpec('control', MechanismFamily.CUSTOM, 'test.control',
        outputs=(PortSpec('control', ChannelKind.SIGNAL, CONTROL),))
    delegate = MechanismSpec('work', MechanismFamily.CUSTOM, 'test.work',
        outputs=(PortSpec('value', ChannelKind.ARTIFACT, 'measurement'),))
    worker = controlled_activity(delegate, count=count, limit=4, control=True,
        guard_path=['enabled'], count_path=['count'], until_path=until,
        initial_state={'n': 0, 'done': False})
    sink = MechanismSpec('sink', MechanismFamily.CUSTOM, 'test.sink',
        inputs=(PortSpec('values', ChannelKind.ARTIFACT, 'measurement', required=False),))
    spec = SystemSpec('flow-test', 1, artifact_types=(ArtifactTypeSpec(CONTROL), ArtifactTypeSpec('measurement')),
        mechanisms=(producer, worker, sink), schedules=tuple(ScheduleSpec(n.mechanism_id, i) for i, n in enumerate((producer,worker,sink))),
        connections=(ConnectionSpec('control','control','work','process-control',ChannelKind.SIGNAL),
                     ConnectionSpec('work','value','sink','values',ChannelKind.ARTIFACT)))
    registry, seen = MechanismRegistry(), []
    registry.register('test.control',1,lambda c: MechanismResult(outputs={'control':(MechanismValue({'count':count,'enabled':enabled}),)},events=(MechanismEvent('control.created'),)))
    def work(c):
        n = c.state['n']+1
        return MechanismResult(outputs={'value':(MechanismValue({'n':n}),)},next_state={'n':n,'done':n>=2},events=(MechanismEvent('work.called',payload={'n':n}),))
    registry.register('test.work',1,work)
    registry.register('test.sink',1,lambda c: (seen.extend(c.inputs['values']) or MechanismResult()))
    register_native_process(type('K',(),{'spec':spec})(), registry)
    return spec, registry, seen


def test_actual_iteration_memory_prefix_lineage_and_resume():
    spec, registry, seen = counter_system()
    result = DeterministicGraphRunner(spec,registry).run(periods=1,start_period=1)
    assert [v.payload['n'] for v in seen] == [1,2,3]
    events = {e.event_id:e for e in result.events}
    for value in seen:
        calls = [events[e].payload['n'] for e in value.lineage_event_ids if events[e].event_type=='work.called']
        assert calls == list(range(1,value.payload['n']+1))  # no future iteration ancestry
    seen.clear()
    continued = DeterministicGraphRunner(spec,registry).run(periods=1,checkpoint=result.checkpoint.to_dict())
    assert [v.payload['n'] for v in seen] == [4,5,6]
    assert continued.checkpoint.mechanism_states['work']['total_invocations']==6


@pytest.mark.parametrize('count,enabled,until,expected',[(3,False,None,0),(0,True,None,0),(4,True,['done'],2)])
def test_explicit_branch_skip_zero_and_data_state_termination(count,enabled,until,expected):
    spec, registry, seen = counter_system(count,enabled,until)
    result=DeterministicGraphRunner(spec,registry).run(periods=1,start_period=1)
    assert len(seen)==expected
    assert result.checkpoint.mechanism_states['work']['last_receipt']['executed']==expected
    assert sum(e.event_type=='work.called' for e in result.events)==expected


def test_budget_and_cycle_fail_without_activity_mutation():
    with pytest.raises(GraphRuntimeError,match='bound'):
        counter_system(count=5)
    spec=activity_world_system()
    dependencies={n.mechanism_id:[] for n in spec.mechanisms}
    dependencies['world.open']=['world.close']
    with pytest.raises(GraphRuntimeError,match='cycle'):
        compile_dependencies(spec,dependencies)


def test_explicit_delegate_event_prefix_survives_composition():
    spec, registry, seen = counter_system(count=2)
    def work(c):
        n = c.state['n'] + 1
        return MechanismResult(outputs={'value': (MechanismValue({'n': n}, event_prefix_length=1),)},
            next_state={'n': n}, events=(MechanismEvent('early', payload={'n': n}),
                                        MechanismEvent('late', payload={'n': n})))
    registry.register('test.work', 1, work, replace=True)
    result = DeterministicGraphRunner(spec, registry).run(periods=1, start_period=1)
    events = {e.event_id: e for e in result.events}
    for value in seen:
        attached = [events[e] for e in value.lineage_event_ids]
        assert any(e.event_type == 'early' and e.payload['n'] == value.payload['n'] for e in attached)
        assert not any(e.event_type == 'late' and e.payload['n'] == value.payload['n'] for e in attached)


def test_until_already_true_can_complete_without_unused_required_input():
    delegate = MechanismSpec('work', MechanismFamily.CUSTOM, 'test.must-not-call',
        inputs=(PortSpec('unavailable', ChannelKind.ARTIFACT, 'measurement'),))
    worker = controlled_activity(delegate, until_path=['done'], initial_state={'done': True})
    spec = SystemSpec('already-done', 1, artifact_types=(ArtifactTypeSpec(CONTROL), ArtifactTypeSpec('measurement')),
        mechanisms=(worker,), schedules=(ScheduleSpec('work', 0),))
    registry = MechanismRegistry()
    registry.register('test.must-not-call', 1, lambda _: pytest.fail('completed activity must not execute'))
    register_native_process(type('K', (), {'spec': spec})(), registry)
    result = DeterministicGraphRunner(spec, registry).run(periods=1, start_period=1)
    assert result.checkpoint.mechanism_states['work']['last_receipt']['executed'] == 0
    assert any(e.event_type == 'native.process.skipped' for e in result.events)


def test_delayed_control_waits_then_executes_actual_activity():
    spec, registry, seen = counter_system(count=2)
    worker = next(n for n in spec.mechanisms if n.mechanism_id == 'work')
    worker = replace(worker, parameters={**worker.parameters, 'missing_control': 'wait'},
        inputs=tuple(replace(p, required=False) if p.port_id == 'process-control' else p for p in worker.inputs))
    spec = replace(spec, mechanisms=tuple(worker if n.mechanism_id == 'work' else n for n in spec.mechanisms),
        connections=tuple(replace(e, latency=1) if e.source_mechanism == 'control' else e for e in spec.connections))
    result = DeterministicGraphRunner(spec, registry).run(periods=1, start_period=1)
    assert seen == []
    assert result.checkpoint.mechanism_states['work']['last_receipt']['waiting_for_control'] is True
    continued = DeterministicGraphRunner(spec, registry).run(periods=1, checkpoint=result.checkpoint.to_dict())
    assert [v.payload['n'] for v in seen] == [1, 2]
    assert continued.checkpoint.mechanism_states['work']['total_invocations'] == 2


CONTROLLER='''def step(context):
    plan=context['inputs']['plans'][0]['payload']
    return {'outputs':{'control':[{'payload':{'enabled':context['period'] % 2 == 1,'count':min(2,len(plan['assignments']))}}]},'state':{}}
'''
DIRECTOR='''def step(context):
    import copy
    plan=context['inputs']['plans'][0]['payload']
    n=context['state'].get('n',0)
    item=copy.deepcopy(plan['assignments'][n % len(plan['assignments'])])
    item['detailed_focus']='PROCESS_INVENTED_ACTIVITY ' + str(n)
    command={'schema':'native-research-amendment-v1','target_year':context['period'],
        'assignment':item,'submit':item['project_end_year']==context['period']}
    return {'outputs':{'amendments':[{'payload':command}]},'state':{'n':n+1}}
'''


def process_world(image,*,enabled=True):
    base=activity_world_system()
    def code(mid,source,inputs,outputs):
        return MechanismSpec(mid,MechanismFamily.CUSTOM,'code.python.v1',inputs=inputs,outputs=outputs,
            parameters={'runtime_image_id':image,'code_artifact':{'schema':CODE_SCHEMA,'label':'Authored process QA, not LLM discovery',
                'source':source,'inputs':{p.port_id:{'type':'object'} for p in inputs},'outputs':{p.port_id:{'type':'object'} for p in outputs},'state_schema':{'type':'object'}}})
    controller=code('plan-controller',CONTROLLER if enabled else CONTROLLER.replace("context['period'] % 2 == 1","False"),
        (PortSpec('plans',ChannelKind.ARTIFACT,PLAN),),(PortSpec('control',ChannelKind.SIGNAL,CONTROL),))
    director=controlled_activity(code('process-director',DIRECTOR,(PortSpec('plans',ChannelKind.ARTIFACT,PLAN),),
        (PortSpec('amendments',ChannelKind.ARTIFACT,AMENDMENT),)),control=True,guard_path=['enabled'],count_path=['count'],limit=2)
    result=replace(base,artifact_types=(*base.artifact_types,ArtifactTypeSpec(CONTROL)),
        mechanisms=(*base.mechanisms,controller,director),schedules=(*base.schedules,ScheduleSpec(controller.mechanism_id,42),ScheduleSpec(director.mechanism_id,45)),
        connections=(*base.connections,ConnectionSpec('world.research','plans','plan-controller','plans',ChannelKind.ARTIFACT),
            ConnectionSpec('world.research','plans','process-director','plans',ChannelKind.ARTIFACT),
            ConnectionSpec('plan-controller','control','process-director','process-control',ChannelKind.SIGNAL)))
    return add_activity_plan_authority(result,source='process-director',source_port='amendments')


def test_source_authored_branch_repeat_changes_actual_research_inputs_and_cold_resume(tmp_path,fixed_corpus):
    from utopia.runtime.checkpointing import PortableStop
    executor=DockerCodeExecutor()
    off, old_calls=make_sim(tmp_path/'off',native=NativeScienceKernel(process_world(executor.image_id,enabled=False),registry_extension=registry_extension,code_executor=executor))
    off.run(); seed()
    spec=process_world(executor.image_id)
    active,calls=make_sim(tmp_path/'active',native=NativeScienceKernel(spec,registry_extension=registry_extension,code_executor=executor))
    try:
        active.run()
        assert not any('PROCESS_INVENTED_ACTIVITY' in json.dumps(p) for _,p in old_calls)
        assert any('PROCESS_INVENTED_ACTIVITY' in json.dumps(p) for _,p in calls)
        assert any(e.event_type=='native.process.skipped' for e in active.native_system.events)
        assert active.native_system.graph_checkpoint['mechanism_states']['process-director']['total_invocations']==6
        effects=[e for e in active.native_system.events if e.event_type==EFFECT and e.payload['amendments']]
        assert [e.year for e in effects]==[1,3,5]
        seed()
        stopped,_=make_sim(tmp_path/'resume',native=NativeScienceKernel(spec,registry_extension=registry_extension,code_executor=executor),after_effects=True)
        with pytest.raises(PortableStop): stopped.run()
        stopped.llm.response_cache.close()
        resumed,_=make_sim(tmp_path/'resume',native=NativeScienceKernel(spec,registry_extension=registry_extension,code_executor=executor))
        try:
            resumed.run()
            assert science_snapshot(resumed)==science_snapshot(active)
            assert resumed.native_system.to_dict()==active.native_system.to_dict()
        finally: resumed.llm.response_cache.close()
    finally:
        off.llm.response_cache.close(); active.llm.response_cache.close()
