"""Original Simulation/physical journals with scripted HTTP/corpus; NOT research results."""
from copy import deepcopy

import pytest

from scripts import analyze_native_autonomous_search_v14 as audit
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_benchmark_controls import objective_specs
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import write_json_atomic


@pytest.mark.parametrize('missing_assigned_loss',[False,True])
def test_non42_controller_seed_new_loss_and_successful_native_physical_audit(
        tmp_path,monkeypatch,fixed_corpus,missing_assigned_loss):
    from tests.runtime import test_portable_checkpoint_integration as fixture
    from tests.optimization.test_native_search_v14 import BINDING,REVISION
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.optimization.native_factory import record_native_http
    from utopia.system.native_kernel import NativeScienceKernel
    losses={spec['id']:spec for spec in objective_specs().values()}
    assigned=deepcopy(objective_specs()['selective'])
    if missing_assigned_loss:
        assigned['id']='SCRIPTED-unavailable-assigned-loss'
        assigned['per_run']['terms'][0]['metric_id']='SCRIPTED-not-measured'
        losses[assigned['id']]=assigned
    initial=legacy_world_system()
    world={**BINDING,'source_commit':REVISION,'years':2}
    campaign=NativeAdaptiveDesignCampaign(tmp_path/'campaign',initial_system=initial,
        loss_spec=assigned,seeds=[42],world_binding=world,seed=1031,mode='blackbox',
        strategies={'scripted':{'kind':'SCRIPTED-not-an-LLM'}})
    monkeypatch.setattr('time.time',lambda:1234567890.)
    monkeypatch.setitem(fixture.BINDING,'model',BINDING['model'])
    monkeypatch.setitem(fixture.BINDING,'model_revision',BINDING['model_digest'])
    monkeypatch.setitem(fixture.BINDING,'corpus_sha256',BINDING['corpus_sha256'])
    def factory(candidate,seed,run_id):
        fixture.seed();cell=tmp_path/'worlds'/run_id
        monkeypatch.setitem(fixture.BINDING,'cell',candidate.fingerprint)
        monkeypatch.setitem(fixture.BINDING,'science_config',{'source_commit':REVISION,'years':2})
        model=fixture.FakeHTTPModel(cell,[])
        old=model.response_cache.path;model.response_cache.close();old.unlink()
        model.response_cache=CompletedResponseCache(cell/'replies/responses.sqlite',binding=fixture.BINDING)
        sim=fixture.SmallRealSimulation(cell,model);sim.num_years=2
        sim.native_system=NativeScienceKernel(candidate)
        sim.enable_portable_checkpoints(fixture.BINDING)
        record_native_http(model,sim,cell/'wire-requests.jsonl')
        write_json_atomic(cell/'system.json',candidate.to_dict(),sort_keys=True,allow_nan=False)
        return sim
    definition={'base_patch':None,'factors':[],'continuous':[],
        'provenance':{'mode':'SCRIPTED-software-QA-only'}}
    campaign.advance(simulation_factory=factory,generators={'scripted':lambda _:definition},count=1)
    kwargs=dict(method='blackbox',world=world,classification=audit.FIXTURE,loss=assigned,
        initial_system=initial.to_dict(),expected_budget=1,expected_controller_seed=1031,
        comparison_losses=losses)
    before=audit._inventory(tmp_path)
    result=audit.audit_native_campaign(tmp_path,**kwargs)
    assert result==audit.audit_native_campaign(tmp_path,**kwargs)
    assert before==audit._inventory(tmp_path)
    assert result['terminal'] and result['physical_native_worlds']==1
    assert result['physical_researcher_responses']>0 and result['technical_failures']==0
    row=result['observations'][0]
    assert row['status']==('loss-unavailable' if missing_assigned_loss else 'complete')
    assert row['cross_scores'][objective_specs()['throughput']['id']] is not None
    assert (row['own_loss'] is None)==missing_assigned_loss
    assert (row['observation']['status']=='failed')==missing_assigned_loss
    with pytest.raises(ValueError,match='seed binding'):
        audit.audit_native_campaign(tmp_path,**{**kwargs,'expected_controller_seed':42})


@pytest.mark.parametrize('years',[2,4])
def test_evaluation_physical_audit_reads_real_native_checkpoints_at_declared_seed(
        tmp_path,monkeypatch,fixed_corpus,years):
    # Synthetic corpus and scientist HTTP, but actual Simulation, response
    # journal, native serialization, annual lineage and physical audit helpers.
    from scripts.native_benchmark_physical import physical_proof
    from tests.runtime import test_portable_checkpoint_integration as fixture
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.optimization.native_factory import record_native_http
    from utopia.optimization.native_world import evaluate_native_suggestion
    from utopia.optimization.blackbox import Suggestion
    from utopia.system.native_kernel import NativeScienceKernel
    system=legacy_world_system(seed=31001)
    world={'model':'SCRIPTED-model','model_digest':'SCRIPTED-digest','corpus_sha256':'SCRIPTED-corpus',
        'source_commit':'a'*40,'runtime_seed_binding':{'python_hash_seed_environment':'42'},
        'experiment':{'role':'SCRIPTED-common-world'}}
    config={'source_commit':world['source_commit'],'years':years,'corpus_years':4,
        'runtime_seed_binding':world['runtime_seed_binding'],'experiment':world['experiment'],
        'population':{'institutions':5,'per_institution':1,'strategy':'balanced'},
        'thinking_override':False,'max_tokens':768,'maximum_http_attempts':512 if years==2 else 1024,
        'lab_inference_serialized':True}
    for key,value in dict(seed=31001,cell=system.fingerprint,model=world['model'],
            model_revision=world['model_digest'],corpus_sha256=world['corpus_sha256'],science_config=config).items():
        monkeypatch.setitem(fixture.BINDING,key,value)
    def initialize(sim):
        fixture.SmallRealSimulation.initialize_agents(sim)
        sim.ecosystem.add_agent(fixture.UniversityResearcher('researcher-4','university-4',
            funding_level=1000,expertise=[fixture.DIRECTION],llm=sim.llm))
        sim._record_initial_university_count()
    class Five(fixture.SmallRealSimulation):
        initialize_agents=initialize
    def factory(candidate,seed,run_id):
        cell=tmp_path/'worlds'/run_id;model=fixture.FakeHTTPModel(cell,[])
        old=model.response_cache.path;model.response_cache.close();old.unlink()
        model.response_cache=CompletedResponseCache(cell/'replies/responses.sqlite',binding=fixture.BINDING)
        model.run_seed=seed;model.enable_thinking=False;model.max_tokens_override=768
        sim=Five(cell,model);sim.num_years=years;sim.args.seed=seed;sim.args.expected_founders=5
        sim.rag.document_identity=world['corpus_sha256']
        sim.native_system=NativeScienceKernel(candidate)
        sim.enable_portable_checkpoints(fixture.BINDING)
        record_native_http(model,sim,cell/'wire-requests.jsonl')
        write_json_atomic(cell/'system.json',candidate.to_dict(),sort_keys=True,allow_nan=False)
        return sim
    o=evaluate_native_suggestion(Suggestion('SCRIPTED-eval',system.to_dict(),0,'SCRIPTED-QA'),
        seeds=[31001],simulation_factory=factory,loss_spec=objective_specs()['throughput'])
    assert o.status=='complete',o.metadata
    before=audit._inventory(tmp_path)
    result=physical_proof(tmp_path/'worlds'/'SCRIPTED-eval-s31001',system,world=world,
        seed=31001,years=years,evidence=o.metadata['runs'][0])
    assert result['measurement']==o.metadata['measurements'][0]
    assert result['status']=='complete' and len(result['annual_checkpoints'])==years
    assert result['response_proof']['wire_requests']>0
    assert before==audit._inventory(tmp_path)
