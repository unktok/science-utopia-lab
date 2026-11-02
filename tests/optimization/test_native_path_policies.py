"""Policy-only synthetic observations, not native/Qwen evidence."""
from copy import deepcopy
import hashlib

import pytest

from utopia.optimization.native_path_policies import NativePathPolicy, validate_state
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def h(text): return hashlib.sha256(text.encode()).hexdigest()


def make(tmp_path, method='blackbox', losses=(.9,.9,.8), budget=3):
    return NativePathPolicy.create(tmp_path/'policy.json',method=method,
        historical=[{'theta':theta,'loss':loss,'provenance':{'historical_record_sha256':h(str(theta))}}
                    for theta,loss in zip([.2,.5,.8],losses)],
        loss_spec_sha256=h('fixed-loss'),world_binding={'source_commit':'a'*40,'model_digest':h('model')},
        fresh_budget=budget,gradient_rule={'learning_rate':.5,'trust_radius':.1,
            'temperature_schedule':[1.,.2,.05][:budget]} if method=='represented-gradient' else None)


def observation(policy,proposal,loss=1.,status='complete'):
    return {'theta':proposal['candidate_theta'],'status':status,'loss':loss,
        'loss_spec_sha256':policy.state['loss_spec_sha256'],
        'world_binding_sha256':digest(policy.state['world_binding']),
        'provenance':{'endpoint_record_sha256':h('endpoint'+str(proposal['sequence']))},
        **({'error':{'type':'SyntheticTechnicalFailure'}} if status!='complete' else {})}


def backward(policy,gradient):
    step=len(policy.state['events'])
    return {'coordinates':[policy.summary()['current_theta']],'gradient':[gradient],
        'temperature':[1.,.2,.05][step],'representation_sha256':h('operator'+str(step)),
        'native_derivative_verified':False,'full_native_world_autograd':False}


def test_blackbox_adapts_from_only_observed_losses_and_charges_shared_history(tmp_path):
    p=make(tmp_path)
    assert p.summary()['current_theta']==.5
    assert p.summary()['incumbent']['theta']==.8
    first=p.ask()
    assert first['candidate_theta']==.65
    assert first['interval']==[.5,.8]
    p.tell(first['content_sha256'],observation(p,first,.7))
    # New best .65 has two equal adjacent widths; lower interval breaks tie.
    second=p.ask()
    assert second['candidate_theta']==pytest.approx(.575)
    p.tell(second['content_sha256'],observation(p,second,2.))
    assert p.summary()['current_theta']==second['candidate_theta']
    assert p.summary()['incumbent']['theta']==.65
    third=p.ask()
    assert third['candidate_theta']==pytest.approx(.725)
    result=p.tell(third['content_sha256'],observation(p,third,.7))
    assert result['incumbent']['theta']==.65  # earliest equal loss stays best
    assert result['status']=='budget-complete'
    assert result['historical_observations_charged']==3
    assert result['total_observations_charged']==6
    with pytest.raises(ValueError,match='budget'):
        p.ask()


def test_blackbox_ties_are_earliest_observation_not_current_or_high_theta(tmp_path):
    p=make(tmp_path,losses=(1.,1.,1.))
    assert p.summary()['incumbent']['theta']==.2
    assert p.ask()['candidate_theta']==pytest.approx(.35)


def test_gradient_raw_step_schedule_noop_uphill_and_boundary_projection(tmp_path):
    p=make(tmp_path,'represented-gradient')
    first=p.ask(backward=backward(p,1.15e-15))
    assert first['candidate_theta']==.5-.5*1.15e-15  # no normalization
    p.tell(first['content_sha256'],observation(p,first,9.))
    assert p.summary()['current_theta']==first['candidate_theta']  # no merit gate
    assert p.summary()['incumbent']['theta']==.8
    second=p.ask(backward=backward(p,0.))
    assert second['unchanged'] and second['requested_step']==0.
    p.tell(second['content_sha256'],observation(p,second,9.))
    third=p.ask(backward=backward(p,-100.))
    assert third['candidate_theta']==pytest.approx(first['candidate_theta']+.1)
    assert third['gradient_rule']['temperature_schedule']==[1.,.2,.05]
    p.tell(third['content_sha256'],observation(p,third,10.))
    assert p.summary()['status']=='budget-complete'
    assert p.summary()['fresh_native_evaluations']==3


def test_noop_and_technical_failure_never_numeric_penalty(tmp_path):
    p=make(tmp_path,'represented-gradient')
    proposal=p.ask(backward=backward(p,0.))
    assert proposal['unchanged']
    failure=observation(p,proposal,None,'technical-failure')
    result=p.tell(proposal['content_sha256'],failure)
    assert result['status']=='terminal-technical-failure'
    assert result['fresh_native_evaluations']==0
    assert result['fresh_proposals_consumed']==1
    assert result['incumbent']['loss']==.8
    assert p.state['events'][0]['observation']['loss'] is None
    with pytest.raises(ValueError,match='terminal'):
        p.ask()


def test_resume_ask_tell_idempotency_and_stale_writers(tmp_path):
    p=make(tmp_path)
    stale=NativePathPolicy(p.path)
    proposal=p.ask()
    assert p.ask()==proposal
    with pytest.raises(ValueError,match='stale'):
        stale.ask()
    resumed=NativePathPolicy(p.path)
    assert resumed.ask()==proposal
    actual=observation(resumed,proposal,.1)
    result=resumed.tell(proposal['content_sha256'],actual)
    assert resumed.tell(proposal['content_sha256'],actual)==result
    changed=deepcopy(actual);changed['loss']=0.
    with pytest.raises(ValueError,match='different'):
        resumed.tell(proposal['content_sha256'],changed)
    reopened=NativePathPolicy(p.path)
    assert reopened.summary()==result


@pytest.mark.parametrize('mutation',[
    lambda b:b.update(coordinates=[.8]),
    lambda b:b.update(temperature=.05),
    lambda b:b.update(gradient=[float('nan')]),
    lambda b:b.update(gradient=[]),
    lambda b:b.update(native_derivative_verified=True),
    lambda b:b.update(full_native_world_autograd=True),
    lambda b:b.update(representation_sha256='unbound'),
])
def test_gradient_rejects_stale_wrong_temperature_nonfinite_or_exact_claim(tmp_path,mutation):
    p=make(tmp_path,'represented-gradient')
    b=backward(p,1.);mutation(b)
    with pytest.raises(ValueError):
        p.ask(backward=b)
    assert p.state['pending'] is None


@pytest.mark.parametrize('mutation',[
    lambda o:o.update(theta=.21),
    lambda o:o.update(loss_spec_sha256=h('wrong-loss')),
    lambda o:o.update(world_binding_sha256=h('wrong-world')),
    lambda o:o.update(loss=None),
    lambda o:o.update(loss=float('inf')),
    lambda o:o.update(provenance={}),
    lambda o:o.update(provenance={'endpoint_record_sha256':'missing'}),
    lambda o:o.update(error={'type':'still-error'}),
])
def test_tell_requires_exact_world_loss_and_endpoint_receipt(tmp_path,mutation):
    p=make(tmp_path);proposal=p.ask();actual=observation(p,proposal)
    mutation(actual)
    with pytest.raises(ValueError):p.tell(proposal['content_sha256'],actual)
    assert len(p.state['events'])==0


def test_resealed_tampered_history_is_replayed_not_trusted(tmp_path):
    p=make(tmp_path);proposal=p.ask()
    p.tell(proposal['content_sha256'],observation(p,proposal))
    tampered=deepcopy(p.state)
    tampered['events'][0]['proposal']['candidate_theta']=.7
    tampered['content_sha256']=digest({k:v for k,v in tampered.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='historical policy proposal'):
        validate_state(tampered)
    write_json_atomic(p.path,tampered,sort_keys=True,allow_nan=False)
    with pytest.raises(ValueError):NativePathPolicy(p.path)


def test_gradient_pending_backward_cannot_be_replaced(tmp_path):
    p=make(tmp_path,'represented-gradient');b=backward(p,1.)
    proposal=p.ask(backward=b)
    assert NativePathPolicy(p.path).ask()==proposal
    b['gradient']=[2.]
    with pytest.raises(ValueError,match='cannot be replaced'):p.ask(backward=b)


def test_existing_state_not_overwritten_and_blackbox_does_not_accept_gradient(tmp_path):
    p=make(tmp_path)
    with pytest.raises(ValueError,match='reopened'):make(tmp_path)
    with pytest.raises(ValueError,match='cannot consume'):p.ask(backward={'gradient':[1.]})
