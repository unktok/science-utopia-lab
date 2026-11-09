from copy import deepcopy
import json

import pytest

from utopia.system.native_information_institution import information_system, information_design_space, SOURCE
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_kernel import NativeScienceKernel
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.system.test_native_science_kernel import make_sim

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_all_conditions_are_same_producer_and_do_not_amend_projects():
    specs = {k:information_system(IMAGE,condition=k) for k in ('M0','M1','M2','M3')}
    for spec in specs.values():
        old = next(n for n in spec.mechanisms if n.mechanism_id=='open-source')
        assert 'native.project' not in old.parameters['delegate']['parameters']['code_artifact']['source']
        office = next(n for n in spec.mechanisms if n.mechanism_id=='information-office')
        assert office.parameters['code_artifact']['source']==SOURCE
        domain=information_design_space(spec,'parameters')
        assert domain['numeric_coordinates'][-1]['mechanism_id']=='information-office'
        assert len(domain['numeric_coordinates'])==6
    assert not any(e.target_mechanism=='history-dossier-receiver' for e in specs['M0'].connections)
    assert any(e.latency==1 and e.target_mechanism=='history-dossier-receiver' for e in specs['M3'].connections)


@pytest.mark.parametrize('condition,first_year', [('M0',None),('M1',2),('M2',2),('M3',3)])
def test_real_original_world_requests_receive_only_declared_history(tmp_path,fixed_corpus,condition,first_year):
    # Original Simulation phases + scripted HTTP/corpus + actual Docker. Not a
    # live-Qwen scientific observation or evidence that the message helps.
    spec=information_system(IMAGE,condition=condition)
    kernel=NativeScienceKernel(spec, code_executor=DockerCodeExecutor(IMAGE))
    sim,calls=make_sim(tmp_path/condition,native=kernel)
    try:
        sim.run()
        observed=[ctx[1] for (ctx,_,_),payload in calls if ctx[0]=='phase1_directions'
                  and 'native-research-history-dossier-v1' in json.dumps(payload)]
        assert (min(observed) if observed else None)==first_year
        # The native activity bridge commits the original plan each year too.
        # Require no institutional amendments, not absence of native research.
        plans=[e for e in kernel.events if e.event_type=='native.system.research_plan_applied']
        assert plans and all(not e.payload['amendments'] for e in plans)
        events=[e for e in kernel.events if e.event_type=='native.system.context_delivered']
        assert bool(events)==(first_year is not None)
    finally:
        sim.llm.response_cache.close()


def test_all_actual_pre_delivery_payloads_match_across_information_edges_and_host_clocks(
        tmp_path,fixed_corpus,monkeypatch):
    from tests.runtime.test_portable_checkpoint_integration import seed,BINDING
    snapshots=[]
    for i,condition in enumerate(('M0','M1','M2','M3')):
        monkeypatch.setattr('time.time',lambda i=i:1234567890.+i*86400.)
        seed();spec=information_system(IMAGE,condition=condition)
        monkeypatch.setitem(BINDING,'cell',spec.fingerprint)
        kernel=NativeScienceKernel(spec,code_executor=DockerCodeExecutor(IMAGE))
        sim,calls=make_sim(tmp_path/condition,native=kernel);sim.num_years=2
        try:
            sim.run()
            snapshots.append({'first_year':[deepcopy((ctx,payload)) for ctx,payload in calls if ctx[0][1]==1],
                'raw_events':[e.to_dict() for e in kernel.events]})
        finally:sim.llm.response_cache.close()
    assert snapshots[0]['first_year']
    assert all(s['first_year']==snapshots[0]['first_year'] for s in snapshots[1:])
    assert all(s['raw_events']!=snapshots[0]['raw_events'] for s in snapshots[1:])
