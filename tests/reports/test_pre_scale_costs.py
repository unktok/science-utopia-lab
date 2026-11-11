"""Synthetic raw cost cases; aliases/unknowns never become free computation."""
from copy import deepcopy
import json

import pytest

from scripts.reports.pre_scale_costs_v1 import analyze,numeric_event,staged_event,classify_numeric,classify_staged
from scripts.reports.native_auxiliary_costs import summarize
from scripts.analyze_native_open_v7 import _inventory
from utopia.system.design_patch import digest


def hashed(value):return {**value,'content_sha256':digest(value)}


def numeric():
    intent=hashed({'provider':{'model':'SCRIPTED-designer'}})
    body={'model':'SCRIPTED-designer','done':True,'done_reason':'stop',
        'prompt_eval_count':10,'prompt_eval_cached_count':11,'eval_count':2}
    transport={'request_payload':{'model':'SCRIPTED-designer'},'http_status':200,
        'raw_http_response':json.dumps(body),'response_payload':body,
        'prompt_tokens':10,'completion_tokens':2,'elapsed_seconds':3.}
    response=hashed({'intent_sha256':intent['content_sha256'],'transport':transport,'elapsed_seconds':4.})
    return intent,response


def test_numeric_provider_fields_and_transport_aliases_are_separate_not_summed():
    i,r=numeric();e=numeric_event('numeric-readiness/authoring/generation-X/call-0.intent.json',i,r,model='SCRIPTED-designer')
    assert e['kind']=='numeric-readiness' and e['final_response_reported']
    assert e['native_cache_subset_status']=='cached-exceeds-prompt'
    result=summarize([e])['measurements']
    assert result['native_prompt_eval_count']['recorded_sum']==10
    assert result['transport_prompt_tokens']['recorded_sum']==10
    assert result['native_prompt_eval_cached_count']['recorded_sum']==11
    assert result['provider_total_duration_ns']['recorded_sum'] is None
    assert result['caller_elapsed_seconds']['recorded_sum']==4.
    assert result['transport_seconds']['recorded_sum']==3.


def test_unknown_numeric_response_retains_missing_usage_and_unknown_dispatch():
    i,_=numeric();e=numeric_event('search/run-00/arm/authoring/generation-X/call-0.intent.json',i,None,model='SCRIPTED-designer')
    r=summarize([e])
    assert e['kind']=='numeric-proposal' and r['request_intents']==1
    assert r['known_HTTP_response']==0 and r['recorded_POST_attempt']==0
    assert not e['completion_record_available'] and not e['final_response_reported']
    assert all(v['recorded_sum'] is None for v in r['measurements'].values())


def staged(raw='not-json',**extra):
    i=hashed({'wire_utf8':json.dumps({'model':'SCRIPTED-designer'})})
    r=hashed({'intent_sha256':i['content_sha256'],'http_status':200,
        'raw_http_response':raw,'elapsed_seconds':2.,**extra})
    return i,r


def test_malformed_or_nonfinal_staged_http_is_not_a_completed_generation_or_zero_cost():
    for raw in ('not-json',json.dumps({'model':'SCRIPTED-designer','done':False})):
        i,r=staged(raw)
        e=staged_event('editor-readiness/wire/dispatch-000.intent.json',i,r,model='SCRIPTED-designer')
        assert e['kind']=='editor-readiness' and e['known_HTTP_response']
        assert not e['final_response_reported']
        assert summarize([e])['measurements']['native_eval_count']['recorded_sum'] is None


def test_staged_transport_failure_retains_observed_time_but_unknown_usage():
    i=hashed({'wire_utf8':json.dumps({'model':'SCRIPTED-designer'})})
    r=hashed({'intent_sha256':i['content_sha256'],'elapsed_seconds':900.,
        'completion_unknown':True,'error_type':'Timeout'})
    e=staged_event('search/run-00/arm/authoring/generation-X/wire/dispatch-000.intent.json',i,r,model='SCRIPTED-designer')
    assert e['status']=='error' and not e['known_HTTP_response']
    assert e['values']['transport_seconds']==900. and e['values']['native_eval_count'] is None


def test_forged_response_intent_or_model_is_rejected():
    i,r=numeric();r['intent_sha256']='x';r=hashed({k:v for k,v in r.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='response/intent'):numeric_event('numeric-readiness/call-0.intent.json',i,r,model='SCRIPTED-designer')
    with pytest.raises(ValueError,match='provider'):numeric_event('numeric-readiness/call-0.intent.json',i,None,model='other')


def empty_audit(root):
    p=hashed({'source_commit':'a'*40,'scientist':{'model':'SCRIPTED-scientist'},'designer':{'model':'SCRIPTED-designer'}})
    inventory=_inventory(root)
    a=hashed({'schema':'scienceutopia.pre-scale-information-audit.v1','source_commit':'a'*40,
        'plan_sha256':p['content_sha256'],'raw_inventory_sha256':digest(inventory),'raw_files':len(inventory),
        'source_proof':{'status':'verified-exact-source-closure'},
        'new_model_calls':0,'new_code_executions':0})
    return p,a


def test_projection_binds_exact_audited_raw_bytes_without_writing_them(tmp_path):
    p,a=empty_audit(tmp_path)
    with pytest.raises(ValueError,match='normal scientific closure'):analyze(tmp_path,p,a)
    assert _inventory(tmp_path)=={}
    (tmp_path/'new-unaccounted-record.json').write_text('{}')
    with pytest.raises(ValueError,match='inventory changed'):analyze(tmp_path,p,a)


def test_live_or_source_mismatched_audit_is_rejected_before_raw_read(tmp_path):
    p,a=empty_audit(tmp_path);a['schema']='live-progress';a=hashed({k:v for k,v in a.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='closed original-source'):analyze(tmp_path,p,a)


def test_per_proposal_and_initial_readiness_are_not_counted_as_free_design():
    for prefix in ('initial-readiness/', 'search/run-00/efficiency--parameters/readiness-1/'):
        assert classify_numeric(prefix+'numeric-readiness/authoring/generation-X/call-0.intent.json')=='numeric-readiness'
        assert classify_staged(prefix+'editor-readiness/wire/dispatch-000.intent.json')=='editor-readiness'
    assert classify_numeric('search/run-00/T/authoring/generation-X/call-0.intent.json')=='numeric-proposal'
    assert classify_staged('search/run-00/T/authoring/generation-X/wire/dispatch-000.intent.json')=='staged-proposal'


def test_native_loop_costs_cannot_treat_a_stopped_or_mismatched_terminal_as_closed(tmp_path):
    from utopia.optimization.native_numeric_designer import save
    p,_=empty_audit(tmp_path)
    start=save(tmp_path/'started.json',{'plan_sha256':p['content_sha256']})
    terminal=save(tmp_path/'terminal.json',{'status':'stopped'})
    inventory=_inventory(tmp_path)
    audit=hashed({'schema':'scienceutopia.native-institution-loop-audit.v1','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'raw_inventory_sha256':digest(inventory),'raw_files':len(inventory),
        'source_proof':{'status':'verified-exact-source-closure'},'new_model_calls':0,'new_code_executions':0,
        'closure':{'started':start,'terminal':terminal}})
    with pytest.raises(ValueError,match='loop closure'): analyze(tmp_path,p,audit)


@pytest.mark.parametrize('schema',['scienceutopia.native-institution-loop-stopped-audit.v1',
    'scienceutopia.native-objective-initial-stop-audit.v1'])
def test_stopped_audit_cost_scope_cannot_imply_selection_or_normal_closure(tmp_path,schema):
    from utopia.optimization.native_numeric_designer import save
    p,_=empty_audit(tmp_path)
    start=save(tmp_path/'started.json',{'plan_sha256':p['content_sha256']})
    terminal=save(tmp_path/'terminal.json',{'status':'stopped'})
    inventory=_inventory(tmp_path)
    a=hashed({'schema':schema,'source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'raw_inventory_sha256':digest(inventory),'raw_files':len(inventory),
        'source_proof':{'status':'verified-exact-source-closure'},'new_model_calls':0,'new_code_executions':0,
        'closure':{'started':start,'terminal':terminal,'scientific_study_closed':False},
        'selection':None,'logical_evaluation':[]})
    # Reaches the missing-cache guard, without inventing any successful world.
    with pytest.raises(ValueError,match='original scientist response journals'): analyze(tmp_path,p,a)
    a['selection']={'invented':'not legal'};a=hashed({k:v for k,v in a.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='stopped costs'): analyze(tmp_path,p,a)


@pytest.mark.parametrize('stopped',[False,True])
def test_new_content_critic_posts_are_not_lost_or_added_to_native_scientist_usage(tmp_path,stopped):
    from tests.reports.test_native_token_costs import cache
    from tests.optimization.test_common_content_observer import contract,Backend,PAPER
    from utopia.optimization.common_content_observer import CommonContentObserver
    from utopia.optimization.native_numeric_designer import save
    p=hashed({'source_commit':'a'*40,'scientist':{'model':'SCRIPTED','model_digest':'b'*64,'corpus_sha256':'c'*64},
        'designer':{'model':'SCRIPTED-designer'}})
    cache(tmp_path,p,'references/known/worlds/known/replies/responses.sqlite',[
        {'prompt_tokens':3,'completion_tokens':4,'total_tokens':7},None])
    observer=CommonContentObserver(tmp_path/'observer',contract(),backend=Backend());observer.rate(PAPER)
    critic=observer.audit()
    start=save(tmp_path/'started.json',{'plan_sha256':p['content_sha256']})
    end=save(tmp_path/'terminal.json',{'status':'stopped' if stopped else 'closed'});inventory=_inventory(tmp_path)
    a=hashed({'schema':'scienceutopia.native-objective-initial-stop-audit.v1' if stopped else 'scienceutopia.native-objective-instrument-loop-audit.v1','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'source_proof':{'status':'verified-exact-source-closure'},
        'new_model_calls':0,'new_code_executions':0,'closure':{'started':start,'terminal':end,'scientific_study_closed':False} if stopped else {'started':start,'terminal':end},
        'raw_inventory_sha256':digest(inventory),'raw_files':len(inventory),'observer':critic,
        **({'selection':None,'logical_evaluation':[]} if stopped else {})})
    result=analyze(tmp_path,p,a)
    assert result['scientist']['completed_responses']==2
    assert result['scientist']['provider_usage']['prompt_tokens']['recorded_sum']==3
    assert result['scientist']['provider_usage']['prompt_tokens']['missing_responses']==1
    common=result['common_content_observer']
    assert common['physical_requests']==3 and common['usage']['prompt_tokens']['known_sum']==213
    assert common['usage']['output_tokens']['known_sum']==27 and not common['overlap_with_native_response_caches']
    assert _inventory(tmp_path)==inventory
    if stopped:assert result['scientific_termination'].startswith('stopped;')
