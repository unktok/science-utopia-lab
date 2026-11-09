"""Original-world connection QA only: scripted HTTP/corpus, real Docker.

Not live Qwen evidence, optimizer superiority, invented institutions or a new
scientific loss. This checks that existing tools act on the current native M1/M3
system instead of a separate numerical substitute world.
"""
from dataclasses import replace
import json
import math

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus,seed,BINDING
from tests.system.test_native_science_kernel import make_sim
from tests.system.test_native_migration import domain
from utopia.system import SystemSpec
from utopia.system.native_information_institution import information_system
from utopia.system.native_kernel import NativeScienceKernel,_hash
from utopia.system.native_migration import migrate_native_design
from utopia.system.design_patch import clone,make_patch,apply_design_patch
from utopia.optimization.native_benchmark_controls import objective_specs
from utopia.optimization.native_gradient import NativeScoreFunctionSearch
from utopia.optimization.native_discrete_policy import verify_native_observation
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.optimization.blackbox import Suggestion
from utopia.runtime.checkpointing import capture_rng

IMAGE='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_current_native_system_score_update_updated_forward_and_no_gradient_control(
        tmp_path,fixed_corpus,monkeypatch):
    loss=objective_specs()['throughput'];system=information_system(IMAGE)
    index=next(i for i,n in enumerate(system.mechanisms) if n.mechanism_id=='addressed-selection')
    path=f'/mechanisms/{index}/parameters/program/parameters/bias'
    optimizer=NativeScoreFunctionSearch(system,[{'path':path,'lower':-4.,'upper':4.}],
        loss_spec=loss,seed=42001,sampling='antithetic',sigma=1.2,learning_rate=.1)
    world={'source_commit':'pre-scale-scripted-native-connection',
        'model_digest':BINDING['model_revision'],'corpus_sha256':BINDING['corpus_sha256'],'years':6}
    runs=[]
    def factory(candidate,run_seed,run_id):
        seed();monkeypatch.setitem(BINDING,'cell',candidate.fingerprint)
        monkeypatch.setitem(BINDING,'science_config',{**BINDING['science_config'],'source_commit':world['source_commit']})
        sim,calls=make_sim(tmp_path/run_id,native=NativeScienceKernel(candidate))
        runs.append((candidate,sim,calls));return sim
    try:
        suggestions=optimizer.ask(2)
        observations=[evaluate_native_suggestion(s,seeds=[42],simulation_factory=factory,loss_spec=loss)
                      for s in suggestions]
        assert all(o.status=='complete' for o in observations)
        for o in observations:verify_native_observation(o,world,[42])
        report=optimizer.tell(observations)
        assert report['status']=='updated' and report['end_to_end_native_autograd'] is False
        value=-4.+8./(1.+math.exp(-report['mean_after'][0]))
        updated=apply_design_patch(system,make_patch(system,[{'op':'replace','path':path,'value':value}]))
        forward=evaluate_native_suggestion(Suggestion('updated-mean',updated.to_dict(),2,'QA-updated-forward'),
            seeds=[42],simulation_factory=factory,loss_spec=loss)
        control=evaluate_native_suggestion(Suggestion('no-gradient-control',system.to_dict(),3,'QA-fixed-control'),
            seeds=[42],simulation_factory=factory,loss_spec=loss)
        assert forward.status==control.status=='complete'
        verify_native_observation(forward,world,[42]);verify_native_observation(control,world,[42])
        assert runs[2][0].mechanisms[index].parameters['program']['parameters']['bias']==value
        assert runs[3][0].mechanisms[index].parameters['program']['parameters']['bias']==.5
        assert all('native-research-history-dossier-v1' in json.dumps(calls)
                   for _,_,calls in runs)
        # Equal paired costs/zero update are legitimate. No reroll or benefit assertion.
        assert len(runs)==4
    finally:
        for _,sim,_ in runs:sim.llm.response_cache.close()


def test_current_delayed_information_society_migrates_without_losing_native_state_or_pending_mail(
        tmp_path,fixed_corpus):
    kernel=NativeScienceKernel(information_system(IMAGE,condition='M3'))
    sim,calls=make_sim(tmp_path/'society',native=kernel)
    receipts=[];boundary=sim.args.checkpoint_callback
    def migrate(path):
        boundary(path)
        if kernel.last_year!=1:return
        before_domain=domain(sim);before_rng=capture_rng();saved=kernel.to_dict()
        previous=clone(kernel.graph_checkpoint['queued_deliveries'])
        assert previous
        candidate=replace(kernel.spec,mechanisms=tuple(replace(n,parameters={**n.parameters,'max_records':2})
            if n.mechanism_id=='information-office' else n for n in kernel.spec.mechanisms))
        receipt=migrate_native_design(kernel,candidate,expected_checkpoint_sha256=_hash(saved),
            state_actions={'information-office':'preserve'})
        assert domain(sim)==before_domain and capture_rng()==before_rng
        assert kernel.graph_checkpoint['queued_deliveries']==previous
        assert kernel.graph_checkpoint['mechanism_states']==saved['graph_checkpoint']['mechanism_states']
        assert NativeScienceKernel(candidate,checkpoint=kernel.to_dict()).to_dict()==kernel.to_dict()
        receipts.append(receipt)
    sim.checkpoint_callback=migrate
    try:
        sim.run()
        assert len(receipts)==1 and kernel.last_year==6
        years=[ctx[1] for (ctx,_,_),payload in calls if ctx[0]=='phase1_directions'
            and 'native-research-history-dossier-v1' in json.dumps(payload)]
        assert min(years)==3
        # Same society, all original researchers/artifacts/years retained.
        assert len(sim.yearly_results)==6 and sim.paper_tracker.papers_by_id
    finally:
        sim.llm.response_cache.close()
