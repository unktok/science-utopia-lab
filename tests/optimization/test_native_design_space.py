"""Nested freedom and pre-execution domain QA; no scientific model calls."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest

from utopia.optimization.native_design_space import (
    make_design_space,require_candidate_in_space,random_parameter_definition,source_paths)
from utopia.optimization.native_benchmark_controls import control_systems,selection_control,objective_specs
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.system import SystemSpec
from utopia.system.design_patch import make_patch,digest
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus

IMAGE='sha256:'+'a'*64


def seed():return control_systems(IMAGE)['open-seed']


def candidate_with(path,value):
    data=seed().to_dict()
    from utopia.optimization.native_design_space import _set
    _set(data,path,value)
    return SystemSpec.from_dict(data)


def campaign(path,kind='parameters',feedback='matched-loss'):
    anchor=seed()
    return NativeAdaptiveDesignCampaign(path,initial_system=anchor,loss_spec=objective_specs()['throughput'],
        seeds=[42],world_binding={'source_commit':'SCRIPTED','model_digest':'SCRIPTED','corpus_sha256':'SCRIPTED'},
        strategies={'proposer':{'method':'SCRIPTED'}},mode='blackbox',proposal_feedback=feedback,
        design_space=make_design_space(anchor,kind))


def test_all_nested_domains_accept_same_anchor_and_include_wrapped_source():
    anchor=seed()
    for kind in ['parameters','code-fixed-graph','code-and-graph']:
        c=make_design_space(anchor,kind)
        require_candidate_in_space(anchor,anchor,c)
        assert len(c['numeric_coordinates'])==6 and len(c['code_paths'])==3
        assert any('/delegate/' in p for p in c['code_paths'])


@pytest.mark.parametrize('kind',['parameters','code-fixed-graph','code-and-graph'])
def test_same_numeric_edit_is_legal_in_every_larger_domain(kind):
    anchor=seed();c=make_design_space(anchor,kind)
    require_candidate_in_space(anchor,candidate_with('/mechanisms/15/parameters/program/parameters/bias',.75),c)


def test_code_is_not_parameter_tuning_and_does_not_require_a_novelty_gate():
    anchor=seed();modified=selection_control(anchor,rule='accept-all').to_dict()
    # Only the literal source differs; scientific rule is irrelevant to membership.
    original=anchor.to_dict();original['mechanisms'][7]['parameters']['code_artifact']['source']=modified['mechanisms'][7]['parameters']['code_artifact']['source']
    changed=SystemSpec.from_dict(original)
    with pytest.raises(ValueError,match='exceeds'):require_candidate_in_space(anchor,changed,make_design_space(anchor,'parameters'))
    for kind in ['code-fixed-graph','code-and-graph']:
        require_candidate_in_space(anchor,changed,make_design_space(anchor,kind))


def test_valid_structure_and_cosmetic_or_state_edits_cannot_escape_fixed_graph():
    anchor=seed()
    changed=replace(anchor,metadata={**anchor.metadata,'extra':'literal graph experiment'})
    for kind in ['parameters','code-fixed-graph']:
        with pytest.raises(ValueError,match='exceeds'):require_candidate_in_space(anchor,changed,make_design_space(anchor,kind))
    require_candidate_in_space(anchor,changed,make_design_space(anchor,'code-and-graph'))
    data=anchor.to_dict();data['mechanisms'].reverse();changed=SystemSpec.from_dict(data)
    with pytest.raises(ValueError):require_candidate_in_space(anchor,changed,make_design_space(anchor,'code-fixed-graph'))


@pytest.mark.parametrize('value',[True,float('nan'),99.])
def test_numeric_type_finiteness_and_bounds_cannot_be_evaded(value):
    anchor=seed()
    # SystemSpec construction or graph validation may reject a malformed tensor first.
    with pytest.raises((ValueError,TypeError)):
        changed=candidate_with('/mechanisms/15/parameters/program/parameters/bias',value)
        require_candidate_in_space(anchor,changed,make_design_space(anchor,'parameters'))


def test_fixed_world_seed_is_not_a_search_coordinate_even_for_free_graph():
    anchor=seed();changed=replace(anchor,initial_state={**anchor.initial_state,'seed':43})
    with pytest.raises(ValueError,match='world seed'):
        require_candidate_in_space(anchor,changed,make_design_space(anchor,'code-and-graph'))


@pytest.mark.parametrize('feedback',['matched-loss','technical-only'])
def test_active_prompt_and_archives_expose_exact_domain_in_both_feedback_groups(tmp_path,feedback):
    from tests.optimization.test_native_bounded_author_context_v45 import frame
    from utopia.optimization.native_staged_author_v15 import initial_draft
    c=campaign(tmp_path,feedback=feedback);r=c._request([],c._strategy_initial(),1)
    assert r['design_space']==c.binding['design_space']
    assert r['design_space_anchor']==c.initial.to_dict()
    view=json.loads(frame(r,initial_draft(r),[])[0])
    assert view['declared_benchmark_design_space']==r['design_space']


def test_compile_rejects_out_of_domain_proposal_before_any_native_world(tmp_path):
    c=campaign(tmp_path);calls=[]
    def author(request):
        return {'base_patch':make_patch(SystemSpec.from_dict(request['parent_system']),[
            {'op':'add','path':'/metadata/outside','value':1}]),'factors':[],'continuous':[],
            'provenance':{'author':'SCRIPTED-domain-violation'}}
    def forbidden(*args):calls.append(args);pytest.fail('must reject before native evaluation')
    r=c.advance(simulation_factory=forbidden,generators={'proposer':author},count=1)
    assert not calls and r['generation_error']['loss'] is None
    assert r['definition']['provenance']['author']=='SCRIPTED-domain-violation'
    assert 'exceeds' in r['generation_error']['message']
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    assert replay_campaign(tmp_path,'blackbox').state==c.state


def test_staged_validation_reports_domain_violation_before_finish_without_repair(tmp_path):
    from utopia.optimization.native_staged_author_v15 import initial_draft,transition
    c=campaign(tmp_path);r=c._request([],c._strategy_initial(),1);state=initial_draft(r)
    kwargs={'binding_sha256':'b'*64,'provider_binding':{'image_id':IMAGE}}
    state,receipt=transition(state,{'tool':'edit','operations':[
        {'op':'add','path':'/metadata/outside','value':1}]},r,**kwargs)
    assert receipt['ok']
    before=deepcopy(state)
    state,receipt=transition(state,{'tool':'validate'},r,**kwargs)
    assert receipt['ok'] and receipt['result']['valid'] is False
    assert 'exceeds' in json.dumps(receipt) and state==before
    clean=initial_draft(r)
    _,receipt=transition(clean,{'tool':'validate'},r,**kwargs)
    assert receipt['result']['valid'] is True


def test_uniform_parameter_baseline_is_deterministic_legal_and_does_not_mutate_request(tmp_path):
    c=campaign(tmp_path);request=c._request([],c._strategy_initial(),1);before=deepcopy(request)
    a=random_parameter_definition(request)
    assert a==random_parameter_definition(request) and request==before
    record={'request':request,'definition':a,'version_sha256':digest(a)}
    _,draws=c._compile(record)
    proposed=SystemSpec.from_dict(draws[0]['suggestion']['candidate'])
    require_candidate_in_space(c.initial,proposed,c.binding['design_space'])
    assert proposed.fingerprint!=c.initial.fingerprint


def test_omitted_domain_preserves_legacy_binding_and_prompt(tmp_path):
    from tests.optimization.test_native_adaptive_search import create
    c=create(tmp_path,mode='blackbox')
    assert 'design_space' not in c.binding
    assert 'design_space' not in c._request([],c._strategy_initial(),1)


def test_http_budget_exhaustion_remains_null_after_native_domain_error_handling(
        tmp_path,monkeypatch,fixed_corpus):
    # Original Simulation/lifecycle with scripted corpus/HTTP: integration QA,
    # never a new real-LLM scientific result.
    from tests.runtime import test_portable_checkpoint_integration as fixture
    from tests.system.test_native_science_kernel import make_sim
    from utopia.optimization.native_factory import record_native_http
    from utopia.optimization.native_world import evaluate_native_suggestion
    from utopia.optimization.blackbox import Suggestion
    from utopia.system.native_kernel import NativeScienceKernel,legacy_world_system
    system=legacy_world_system();wire=tmp_path/'physical-wire.jsonl';models=[]
    monkeypatch.setitem(fixture.BINDING,'cell',system.fingerprint)
    def factory(spec,seed,run_id):
        sim,_=make_sim(tmp_path/'SCRIPTED-world',native=NativeScienceKernel(spec))
        record_native_http(sim.llm,sim,wire,maximum_attempts=2);models.append(sim.llm)
        return sim
    observation=evaluate_native_suggestion(Suggestion('SCRIPTED-budget',system.to_dict(),0,'software-QA'),
        seeds=[42],simulation_factory=factory,loss_spec=objective_specs()['throughput'])
    assert observation.status=='failed' and observation.loss is None
    assert observation.metadata['measurements']==[] and observation.metadata['technical_failures']
    assert models[0].http_budget_exhausted is True and len(wire.read_text().splitlines())==2


def test_unrelated_portable_stop_is_not_reclassified_as_a_completed_null_slot():
    from utopia.runtime.checkpointing import PortableStop
    from utopia.optimization.native_world import evaluate_native_suggestion
    from utopia.optimization.blackbox import Suggestion
    def stop(*a):raise PortableStop('SCRIPTED user or unrelated transport stop')
    with pytest.raises(PortableStop):
        evaluate_native_suggestion(Suggestion('SCRIPTED-stop',seed().to_dict(),0,'software-QA'),
            seeds=[42],simulation_factory=stop,loss_spec=objective_specs()['throughput'])
