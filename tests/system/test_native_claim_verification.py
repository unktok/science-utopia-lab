from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import json

import pytest

from utopia.system import (ChannelKind, MechanismFamily, MechanismSpec, PortSpec,
                           ConnectionSpec, ScheduleSpec)
from utopia.system.native_kernel import NativeScienceKernel,legacy_world_system
from utopia.system.native_claim_verification import (CLAIM,VERDICT,IMPLEMENTATION,evaluate_claim,verify_claims)
from utopia.system.runtime import DeliveredValue,MechanismContext,GraphRuntimeError


def fixture():
    kernel=NativeScienceKernel(legacy_world_system())
    paper=SimpleNamespace(id='actual-paper',review_history=[
        {'year':1,'decision':'accept','reviews':[{'overall_score':3},{'overall_score':4}]},
        {'year':2,'decision':'reject','reviews':[{'overall_score':2}]}])
    kernel._simulation=SimpleNamespace(paper_tracker=SimpleNamespace(papers_by_id={paper.id:paper}),
        ecosystem=SimpleNamespace(agent_population={'researcher':SimpleNamespace(can_author=True)}))
    kernel._frame={'year':2}
    node=MechanismSpec('independent-verifier',MechanismFamily.CUSTOM,IMPLEMENTATION,
        inputs=(PortSpec('claims',ChannelKind.ARTIFACT,CLAIM,required=False),),
        outputs=(PortSpec('verifications',ChannelKind.ARTIFACT,VERDICT,required=False),))
    ctx=MechanismContext(kernel.spec.system_id,kernel.spec.fingerprint,node,2,200,'annual',{}, {}, {})
    return kernel,ctx


def claim(identity='first',value=2,**fields):
    return {'schema':CLAIM,'claim_id':identity,'metric':'accepted-decisions','after_year':0,
            'through_year':1,'asserted_value':value,'supersedes':None,**fields}


def delivered(body,actor='researcher'):
    return DeliveredValue(ChannelKind.ARTIFACT,CLAIM,body,(actor,),(),('actual-author-event',),
                          'authored-institution','claims',1,2)


def test_false_claim_is_not_self_certified_and_correction_preserves_it():
    kernel,ctx=fixture()
    first=verify_claims(kernel,replace(ctx,inputs={'claims':(delivered(claim()),)}))
    verdict=first.next_state['records']['first']
    assert not verdict['matches_native_records'] and verdict['expected_value']==1
    corrected=claim('corrected',1,supersedes='first')
    second=verify_claims(kernel,replace(ctx,state=first.next_state,inputs={'claims':(delivered(corrected),)}))
    assert second.next_state['records']['first']==verdict
    assert second.next_state['records']['corrected']['matches_native_records']
    assert second.next_state['records']['corrected']['superseded_verification_sha256']


@pytest.mark.parametrize('metric,value',[('accepted-decisions',1),('rejected-decisions',1),('review-records',3)])
def test_expected_values_use_actual_records_and_interval_not_candidate_world(metric,value):
    kernel,_=fixture()
    result=evaluate_claim(kernel,claim(value=value,metric=metric,through_year=2),year=2)
    assert result['matches_native_records'] and result['expected_value']==value
    assert result['native_record_count']==2


@pytest.mark.parametrize('fields',[{'asserted_value':True},{'asserted_value':1.}, {'through_year':3},
    {'after_year':1,'through_year':1},{'metric':'invented-quality'},{'matches_native_records':True}])
def test_unknown_or_privileged_fields_cannot_assign_truth(fields):
    kernel,_=fixture()
    with pytest.raises(GraphRuntimeError):evaluate_claim(kernel,claim(**fields),year=2)


def test_later_bad_record_cannot_partially_commit_or_rewrite_prior_claim():
    kernel,ctx=fixture();state={'records':{}}
    with pytest.raises(GraphRuntimeError):
        verify_claims(kernel,replace(ctx,state=state,inputs={'claims':(
            delivered(claim('ok',1)),delivered(claim('bad',1,supersedes='unknown')))}))
    assert state=={'records':{}}
    result=verify_claims(kernel,replace(ctx,inputs={'claims':(delivered(claim('old',1)),)}))
    with pytest.raises(GraphRuntimeError,match='reused'):
        verify_claims(kernel,replace(ctx,state=result.next_state,inputs={'claims':(delivered(claim('old',2)),)}))


def test_verifier_is_opt_in_without_new_default_scientific_phases():
    kernel,_=fixture()
    assert (IMPLEMENTATION,1) in kernel._registry().registered
    assert not any(n.implementation==IMPLEMENTATION for n in kernel.spec.mechanisms)


@pytest.mark.parametrize('body',[claim(identity=[]),claim(metric={}),None,[],{'claim_id':[]}])
def test_untrusted_json_shapes_are_rejected_as_graph_errors(body):
    kernel,ctx=fixture()
    with pytest.raises(GraphRuntimeError):
        verify_claims(kernel,replace(ctx,inputs={'claims':(delivered(body),)}))


def test_seeded_state_cannot_forge_a_matching_verdict_and_skip_verification():
    kernel,ctx=fixture()
    original=verify_claims(kernel,replace(ctx,inputs={'claims':(delivered(claim()),)}))
    forged=deepcopy(original.next_state)
    forged['records']['first']['matches_native_records']=True
    with pytest.raises(GraphRuntimeError,match='differs from actual'):
        verify_claims(kernel,replace(ctx,state=forged,inputs={'claims':(delivered(claim()),)}))


CLAIM_SOURCE='''def step(context):
    year=context['period']
    state=context['state']
    world=context['inputs']['world'][0]['payload']
    actors=[a['id'] for a in world['ecosystem']['agents'] if a['can_author']]
    if year==1:
        expected=sum(r['decision']=='accept' for p in world['papers']['papers']
                     for r in p['review_history'] if r['year']==1)
        state={'observed_first_year_count':expected}
        identity='initial-claim';value=expected+1;supersedes=None
    elif year==2:
        identity='corrected-claim';value=state['observed_first_year_count'];supersedes='initial-claim'
    else:
        return {'outputs':{'claims':[]},'state':state}
    claim={'schema':'native-world-count-claim-v1','claim_id':identity,
        'metric':'accepted-decisions','after_year':0,'through_year':1,
        'asserted_value':value,'supersedes':supersedes}
    return {'outputs':{'claims':[{'actor_ids':actors,'payload':claim}]},'state':state}
'''


def claim_system(image):
    from utopia.system.native_kernel import WORLD_ARTIFACT
    from utopia.system.native_claim_verification import attach_claim_verifier
    from utopia.system.code_mechanisms import CODE_SCHEMA
    base=legacy_world_system()
    node=MechanismSpec('empirical-claim-office',MechanismFamily.CUSTOM,'code.python.v1',
        inputs=(PortSpec('world',ChannelKind.ARTIFACT,WORLD_ARTIFACT),),
        outputs=(PortSpec('claims',ChannelKind.ARTIFACT,CLAIM,required=False),),
        parameters={'runtime_image_id':image,'code_artifact':{'schema':CODE_SCHEMA,
            'label':'Scripted false assertion and correction about actual native decisions',
            'source':CLAIM_SOURCE,'inputs':{'world':{'type':'object'}},
            'outputs':{'claims':{'type':'object'}},'state_schema':{'type':'object'}}})
    base=replace(base,mechanisms=(*base.mechanisms,node),
        schedules=(*base.schedules,ScheduleSpec(node.mechanism_id,190)),
        connections=(*base.connections,ConnectionSpec('world.publication','world',node.mechanism_id,
            'world',ChannelKind.ARTIFACT)))
    return attach_claim_verifier(base,source=node.mechanism_id,source_port='claims')


# This test runs the original simulator and real networkless Docker executor,
# but scripted corpus/HTTP. It is NOT an experiment with live scientist models.
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


def test_authored_claim_independent_verification_correction_and_actual_scientist_input(tmp_path,fixed_corpus):
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.code_mechanisms import DockerCodeExecutor
    image='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'
    kernel=NativeScienceKernel(claim_system(image),code_executor=DockerCodeExecutor(image))
    sim,calls=make_sim(tmp_path/'claims',native=kernel)
    try:
        sim.run()
        records=kernel.graph_checkpoint['mechanism_states']['claim-verifier']['records']
        assert not records['initial-claim']['matches_native_records']
        assert records['corrected-claim']['matches_native_records']
        assert records['corrected-claim']['expected_value']==records['initial-claim']['expected_value']
        events=[e for e in kernel.events if e.event_type=='native.system.claim_verified']
        assert len(events)==2 and all(e.provenance['input_event_ids'] for e in events)
        def text(payload):
            return '\n'.join(m['content'] if isinstance(m['content'],str) else
                '\n'.join(part['text'] for part in m['content'] if part['type']=='text')
                for m in payload['messages'])
        directions={y:[text(p)
                       for (ctx,_,_),p in calls if ctx[:2]==('phase1_directions',y)]
                    for y in (1,2,3)}
        assert all(VERDICT not in p for p in directions[1])
        assert any('initial-claim' in p and '"matches_native_records": false' in p for p in directions[2])
        assert any('corrected-claim' in p and '"matches_native_records": true' in p for p in directions[3])
        assert all('initial-claim' in p for p in directions[3])
    finally:
        sim.llm.response_cache.close()
