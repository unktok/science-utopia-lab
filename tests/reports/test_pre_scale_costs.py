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
