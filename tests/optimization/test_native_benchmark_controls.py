"""Developer baseline software QA; scripted scholars are not research results."""
from copy import deepcopy
import pytest

from utopia.optimization.native_benchmark_controls import control_systems, objective_specs, selection_control
from utopia.optimization.loss import evaluate_loss, validate_loss_spec
from utopia.system import validate_system_spec
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus

IMAGE='sha256:'+'a'*64


def test_eight_explicit_controls_keep_seed_intact_and_one_true_legacy():
    systems=control_systems(IMAGE)
    assert len(systems)==8 and systems['legacy'].to_dict()==legacy_world_system().to_dict()
    original=deepcopy(systems['open-seed'].to_dict())
    for name,s in systems.items():
        validate_system_spec(s).require_valid()
        if name.startswith('open-') and name!='open-no-review-accept-all':
            assert s.connections==systems['open-seed'].connections
            assert s.schedules==systems['open-seed'].schedules
    no_review=systems['open-no-review-accept-all']
    assert all(n.mechanism_id!='world.review' for n in no_review.mechanisms)
    assert all(e.source_mechanism!='world.review' and e.target_mechanism!='world.review' for e in no_review.connections)
    assert any(e.source_mechanism=='world.costs' and e.target_mechanism=='native-feature-extractor' for e in no_review.connections)
    assert systems['open-seed'].to_dict()==original


def test_objectives_are_literal_tradeoffs_not_hidden_admission_rules():
    losses=objective_specs()
    assert set(losses)=={'throughput','efficiency','selective'}
    for loss in losses.values():validate_loss_spec(loss)
    metrics={k:{'status':'measured','value':v} for k,v in [
        ('native.accepted_decisions',7),('native.accepted_peer_score_sum',22.),('native.review_records',21)]}
    assert evaluate_loss(losses['selective'],[{'run_id':'SCRIPTED','metrics':metrics}])['loss']==pytest.approx(8.1)


@pytest.mark.parametrize('rule,threshold',[('unknown',0),('threshold',float('nan')),('threshold',True)])
def test_invalid_control_never_creates_fallback(rule,threshold):
    with pytest.raises(ValueError):selection_control(control_systems(IMAGE)['open-seed'],rule=rule,threshold=threshold)


@pytest.mark.parametrize('name,expected',[
    ('open-accept-all',['accept','accept']),('open-reject-all',['reject','reject']),
    ('open-score-3',['reject','accept']),('open-score-4',['reject','accept'])])
def test_literal_baseline_source_runs_only_in_container_and_handles_empty_cycle(name,expected):
    executor=DockerCodeExecutor()
    node=next(n for n in control_systems(executor.image_id)[name].mechanisms if n.mechanism_id=='world.selection')
    world={'conferences':{'conferences':[{'conference_id':'C','submitted_papers':[{'id':'p1'},{'id':'p2'}],
        'reviews':{'p1':[{'overall_score':2.}],'p2':[{'overall_score':4.}]}}]}}
    context={'inputs':{p.port_id:[] for p in node.inputs},'parameters':{
        k:v for k,v in node.parameters.items() if k not in {'runtime_image_id','code_artifact'}},
        'state':{},'period':1,'random_seed':42}
    context['inputs']['observations']=[{'payload':world}]
    result=executor.execute(node.parameters['code_artifact'],context).result
    assert [x['payload']['decision'] for x in result['outputs']['decisions']]==expected
    world['conferences']['conferences'][0]['submitted_papers']=[]
    result=executor.execute(node.parameters['code_artifact'],context).result
    assert result['outputs']['decisions']==[{'payload':{'empty_cycle':True}}]


@pytest.mark.parametrize('name',['legacy','open-seed','open-rank-rate','open-accept-all',
    'open-reject-all','open-score-3','open-score-4','open-no-review-accept-all'])
def test_original_native_lifecycle_consumes_each_control_without_loss_fabrication(
        tmp_path,fixed_corpus,monkeypatch,name):
    from tests.runtime import test_portable_checkpoint_integration as fixture
    from tests.system.test_native_science_kernel import make_sim
    from utopia.optimization.native_world import measure_native_world
    image=DockerCodeExecutor().image_id
    spec=control_systems(image)[name]
    monkeypatch.setitem(fixture.BINDING,'cell',spec.fingerprint)
    sim,_=make_sim(tmp_path/name,native=NativeScienceKernel(spec))
    try:
        sim.run()
        metrics=measure_native_world(sim,run_id='SCRIPTED-'+name)['metrics']
        if name=='open-no-review-accept-all':
            assert metrics['native.review_records']['value']==0
            assert metrics['native.accepted_peer_score_sum']['value']==0
        if name=='open-reject-all':assert metrics['native.accepted_decisions']['value']==0
    finally:
        sim.llm.response_cache.close()
