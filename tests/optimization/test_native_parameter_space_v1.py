"""Native program adapter and SCRIPTED scalar feedback, not scientific gains."""
from copy import deepcopy

import pytest

from utopia.optimization.blackbox import AdaptiveRandomSearch, Observation
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_fixed_production_domain import CATALOG_PLANNING_SCOPE, catalog_planning_design_space
from utopia.optimization.native_parameter_space_v1 import NativeParameterSpace, NativeParameterOptimizer, parameter_domain
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_planning_controls import planning_controls

IMAGE='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def space():
    anchor=planning_controls(IMAGE,seed=61001)['assignment-reserve21-no-review-all']
    coordinates=[{'mechanism_id':'developer-liquidity-director','path':'/parameters/reserve_units',
                  'lower':1,'upper':40,'integer':True}]
    contract=parameter_domain(anchor,coordinates,world_law_scope=CATALOG_PLANNING_SCOPE)
    return NativeParameterSpace(anchor,contract)


def test_actual_existing_consumer_numeric_field_is_mutable_without_changing_source_or_native_law():
    s=space(); original=deepcopy(s.binding)
    for value in (1,10,20,21,22,40):
        candidate=s.candidate({'coordinate-0':value})
        node=next(n for n in candidate['mechanisms'] if n['mechanism_id']=='developer-liquidity-director')
        assert node['parameters']['reserve_units']==value
        assert "context['parameters']['reserve_units']" in node['parameters']['code_artifact']['source']
        old=next(n for n in original['anchor']['mechanisms'] if n['mechanism_id']=='developer-liquidity-director')
        assert node['parameters']['code_artifact']==old['parameters']['code_artifact']
        assert candidate['connections']==original['anchor']['connections']
        assert candidate['schedules']==original['anchor']['schedules']
        broad=catalog_planning_design_space(SystemSpec.from_dict(original['anchor']),'code-and-graph')
        require_candidate_in_space(SystemSpec.from_dict(original['anchor']),SystemSpec.from_dict(candidate),broad)
    assert s.binding==original and s.binding_sha256==digest(original)
    exposed=s.binding;exposed['anchor']['metadata']['not_internal']=True
    assert s.binding==original


@pytest.mark.parametrize('value',[True,21.,0,41,float('nan'),float('inf'),'21'])
def test_numeric_values_are_not_clamped_coerced_or_repaired(value):
    with pytest.raises(ValueError):space().candidate({'coordinate-0':value})


@pytest.mark.parametrize('key',['source','seed','schedule','wire','unlisted-parameter'])
def test_candidate_cannot_change_any_other_field(key):
    s=space(); candidate=deepcopy(s.binding['anchor'])
    if key=='source':
        node=next(n for n in candidate['mechanisms'] if n['mechanism_id']=='developer-liquidity-director')
        node['parameters']['code_artifact']['source']+='\n# SCRIPTED unpermitted source change\n'
    if key=='seed':candidate['initial_state']['seed']=999
    if key=='schedule':candidate['schedules'][0]['phase']+=1
    if key=='wire':candidate['connections'].pop()
    if key=='unlisted-parameter':candidate['mechanisms'][-1]['parameters']['unlisted']=1
    with pytest.raises(ValueError):s.validate(candidate)


def test_sampling_and_bounded_mutation_are_deterministic_and_leave_inputs_literal():
    s=space(); point=s.candidate({'coordinate-0':21}); before=deepcopy(point)
    for index in range(20):
        assert s.sample(seed=7,proposal_index=index)==s.sample(seed=7,proposal_index=index)
        a=s.mutate(point,seed=7,proposal_index=index,scale=.2)
        assert a==s.mutate(point,seed=7,proposal_index=index,scale=.2)
        assert 13 <= s.values(a)['coordinate-0'] <= 29
    assert point==before


def test_existing_ask_tell_optimizer_consumes_scalar_feedback_and_restores_with_same_bound_space():
    s=space(); optimizer=AdaptiveRandomSearch(s,seed=13,initial_random=1)
    first,=optimizer.ask()
    value=s.values(first.candidate)['coordinate-0']
    observation=Observation('SCRIPTED-first',first.suggestion_id,first.candidate,'complete',float((value-17)**2),
                            {'classification':'SCRIPTED scalar, not a native scientific result'})
    optimizer.tell([observation])
    saved=deepcopy(optimizer.state_dict())
    clone_space=NativeParameterSpace(s.binding['anchor'],s.binding['design_space'])
    restored=AdaptiveRandomSearch.from_state(clone_space,saved)
    a,=optimizer.ask(); b,=restored.ask()
    assert a.to_dict()==b.to_dict() and a.based_on_observation_id=='SCRIPTED-first'
    optimizer.tell([Observation('SCRIPTED-known-null',a.suggestion_id,a.candidate,'failed',None)])
    assert optimizer.state_dict()['observations'][-1]['loss'] is None


@pytest.mark.parametrize('scale',[True,0,-1,1.1,float('nan')])
def test_invalid_mutation_scale_rejects_without_projection(scale):
    s=space()
    with pytest.raises(ValueError):s.mutate(s.binding['anchor'],seed=1,proposal_index=0,scale=scale)


def test_old_default_parameter_domain_is_not_silently_expanded():
    anchor=SystemSpec.from_dict(space().binding['anchor'])
    old=catalog_planning_design_space(anchor,'parameters')
    assert len(old['numeric_coordinates'])==6
    assert not any(c['path']=='/parameters/reserve_units' for c in old['numeric_coordinates'])


def test_float_coordinates_and_bound_optimizer_restore_preserve_space_and_outer_checksum(tmp_path):
    from utopia.optimization.native_numeric_designer import save
    anchor=SystemSpec.from_dict(space().binding['anchor'])
    coords=[{'mechanism_id':'addressed-selection','path':'/parameters/program/parameters/bias',
             'lower':-4.,'upper':4.,'integer':False}]
    s=NativeParameterSpace(anchor,parameter_domain(anchor,coords,world_law_scope=CATALOG_PLANNING_SCOPE))
    optimizer=NativeParameterOptimizer(s,seed=31,initial_random=1)
    first,=optimizer.ask()
    value=s.values(first.candidate)['coordinate-0']
    assert type(value) is float and -4 <= value <= 4
    optimizer.tell([Observation('SCRIPTED-float',first.suggestion_id,first.candidate,'complete',value)])
    saved=save(tmp_path/'state.json',optimizer.state_dict())
    before=deepcopy(saved)
    restored=NativeParameterOptimizer.from_state(s,saved)
    assert saved==before
    assert optimizer.ask()[0].to_dict()==restored.ask()[0].to_dict()
    other=deepcopy(coords);other[0]['upper']=5.
    changed=NativeParameterSpace(anchor,parameter_domain(anchor,other,world_law_scope=CATALOG_PLANNING_SCOPE))
    with pytest.raises(ValueError,match='exact expected'):
        NativeParameterOptimizer.from_state(changed,saved)
    saved['optimizer']['proposal_index']+=1
    with pytest.raises(ValueError):
        NativeParameterOptimizer.from_state(s,saved)


@pytest.mark.parametrize('seed,index',[(True,0),(1,True),(1,-1),(1,0.5)])
def test_sampling_seed_and_index_are_literal_integers(seed,index):
    with pytest.raises(ValueError):space().sample(seed=seed,proposal_index=index)


@pytest.mark.parametrize('state',[None,[],1,'state'])
def test_bad_saved_state_shapes_do_not_become_implicit_initialization(state):
    with pytest.raises(ValueError):NativeParameterOptimizer.from_state(space(),state)


@pytest.mark.parametrize('scale',[True,None,'0.2',0,float('inf')])
def test_optimizer_configuration_rejects_invalid_scale_before_any_proposal(scale):
    with pytest.raises(ValueError):NativeParameterOptimizer(space(),seed=1,mutation_scale=scale)


def test_coordinate_must_already_exist_instead_of_installing_a_consumer():
    anchor=SystemSpec.from_dict(space().binding['anchor'])
    coordinates=[{'mechanism_id':'developer-liquidity-director','path':'/parameters/invented',
                  'lower':0,'upper':1,'integer':True}]
    with pytest.raises(ValueError,match='existing literal'):
        parameter_domain(anchor,coordinates,world_law_scope=CATALOG_PLANNING_SCOPE)


@pytest.mark.parametrize('change',['float-version','missing-field','ignored-root-key'])
def test_noncoordinate_fields_are_not_accepted_after_systemspec_normalization(change):
    s=space();candidate=deepcopy(s.binding['anchor'])
    if change=='float-version':candidate['version']=float(candidate['version'])
    if change=='missing-field':candidate.pop('metadata')
    if change=='ignored-root-key':candidate['extra-unknown-field']=True
    with pytest.raises(ValueError):s.validate(candidate)
