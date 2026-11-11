"""Developer allocation controls; original phases with scripted HTTP/corpus."""
from dataclasses import replace
import json

import pytest

from tests.runtime.test_portable_checkpoint_integration import FakeHTTPModel,SmallRealSimulation,fixed_corpus,seed
from tests.optimization.test_native_search_generator_v14 import IMAGE
from utopia.system.native_kernel import legacy_world_system,NativeScienceKernel
from utopia.system.native_liquidity_controls import liquidity_control
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_resource_transfers import EVENT


def test_same_algorithm_nodes_and_schedule_only_connection_differs():
    base=legacy_world_system();on=liquidity_control(base,IMAGE);off=liquidity_control(base,IMAGE,connected=False)
    assert on.mechanisms==off.mechanisms and on.schedules==off.schedules
    assert on.initial_state==base.initial_state
    assert on.connections[:-1]==off.connections
    assert on.connections[-1].target_mechanism=='developer-liquidity-effects'
    phases={s.mechanism_id:s.phase for s in on.schedules}
    assert phases['world.submission']<phases['developer-liquidity-director']<phases['developer-liquidity-effects']<phases['world.costs']
    assert all(n in on.mechanisms for n in base.mechanisms)


def test_no_available_native_execution_slot_is_not_silently_rescheduled():
    base=legacy_world_system();base=replace(base,schedules=tuple(replace(s,phase=81) if s.mechanism_id=='world.costs' else s for s in base.schedules))
    with pytest.raises(ValueError,match='execution opportunity'):liquidity_control(base,IMAGE)


def test_actual_docker_control_changes_conserving_balances_and_subsequent_native_inputs(tmp_path,fixed_corpus,monkeypatch):
    monkeypatch.setattr('time.time',lambda:1234567890.)
    class UnequalSimulation(SmallRealSimulation):
        def initialize_agents(self):
            super().initialize_agents()
            authors=sorted((a for a in self.ecosystem.agent_population.values() if a.can_author),key=lambda a:a.id)
            for actor,amount in zip(authors,[100.,300.,500.,700.]):actor.resources=amount
    executor=DockerCodeExecutor();worlds=[];requests=[]
    for label,connected in [('off',False),('on',True)]:
        seed();root=tmp_path/label;calls=[];model=FakeHTTPModel(root,calls)
        sim=UnequalSimulation(root,model,ledger=True)
        sim.native_system=NativeScienceKernel(liquidity_control(legacy_world_system(),executor.image_id,connected=connected),code_executor=executor)
        sim.run();worlds.append(sim);requests.append(calls)
    try:
        off,on=worlds;events=[e for e in on.native_system.events if e.event_type==EVENT]
        assert events and not any(e.event_type==EVENT for e in off.native_system.events)
        for event in events:
            before=event.payload['balances_before'];after=event.payload['balances_after']
            assert sum(before.values())==sum(after.values())
            assert event.payload['actual_debit']==event.payload['actual_credit']>0
        for sim in worlds:
            sim.resource_ledger.reconcile(6,sim.ecosystem.agent_population,require_closed=True)
        # Full original researcher request payloads, not an allocation log alone.
        before0=[payload for (context,_,_),payload in requests[0] if context[:2]==('phase1_directions',1)]
        before1=[payload for (context,_,_),payload in requests[1] if context[:2]==('phase1_directions',1)]
        assert before0==before1 and before0
        assert [payload for _,payload in requests[0]]!=[payload for _,payload in requests[1]]
        assert on.native_system.last_year==off.native_system.last_year==6
    finally:
        for sim in worlds:sim.llm.response_cache.close()
