"""Literal native input-frame readout; no mocked result is science evidence."""
import hashlib
import json
import sqlite3

import pytest

from scripts.reports.native_instruction_timing_v1 import direction_input, native_history, completed_pairs
from scripts.reports import native_instruction_timing_v1 as module
from tests.reports.test_native_instruction_timing_support_v1 import prospective_plan
from utopia.optimization.native_numeric_designer import save, checked
from utopia.system.design_patch import digest

MESSAGE='SCRIPTED advice, not an actual research condition'
CATALOG={'short':1,'long':3,'related':2}


def wire(text=None):
    if text is None:
        text='''## Directions You Can Choose From
### Direction 1: short
- Focus Areas: A
- Expected Project Duration: 1 year(s)
- Keywords: B
### Direction 2: long
- Focus Areas: C
- Expected Project Duration: 3 year(s)
- Keywords: D
## Your Task
Choose an allowed topic.'''
    p={'messages':[{'role':'user','content':text}],
        'response_format':{'type':'json_schema','json_schema':{'name':'research_direction_selection'}}}
    return {'year':1,'payload':p,'payload_sha256':digest(p)}


def response(topic='short'):
    return {'choices':[{'message':{'content':json.dumps({
        'topic':topic,'detailed_focus':'SCRIPTED focus','reason':'SCRIPTED reason'})},'finish_reason':'stop'}]}


def memory(actor='actor'):
    return {'actor_id':actor,'year':1,'topic':'short','detailed_focus':'SCRIPTED focus','reason':'SCRIPTED reason'}


def test_literal_input_candidates_choices_and_presence_are_separate():
    w=wire();r=direction_input(w,response(),[memory()],MESSAGE,CATALOG)
    assert not r['literal_instruction_present'] and r['selected_is_shortest_displayed']
    assert r['minimum_displayed_duration_years']==1 and r['selected_catalog_duration_years']==1
    assert r['unique_actor_attribution'] and r['matching_actual_memory_actor_ids']==['actor']
    assert all(c['matches_original_catalog'] for c in r['displayed_candidates'])
    w=wire(MESSAGE+'\n'+w['payload']['messages'][0]['content'])
    r=direction_input(w,response('long'),[],MESSAGE,CATALOG)
    assert r['literal_instruction_present'] and not r['selected_is_shortest_displayed']
    assert not r['unique_actor_attribution']


def test_unlisted_allowed_related_topic_and_ambiguous_actor_are_not_invented():
    r=direction_input(wire(),response('related'),[],MESSAGE,CATALOG)
    assert r['selected_is_shortest_displayed'] is None and r['selected_catalog_duration_years']==2
    r=direction_input(wire(),response(),[memory('one'),memory('two')],MESSAGE,CATALOG)
    assert r['matching_actual_memory_actor_ids']==['one','two'] and not r['unique_actor_attribution']


def test_bad_frames_or_response_remain_explicit_without_output_salvage():
    w=wire();w['payload']['messages'].append(w['payload']['messages'][0])
    r=direction_input(w,response(),[],MESSAGE,CATALOG)
    assert r['frame_status']=='unassessed-frame' and r['displayed_candidates']==[]
    malformed={'choices':[{'message':{'content':'prefix {"topic":"short"} trailing'}}]}
    r=direction_input(wire(),malformed,[],MESSAGE,CATALOG)
    assert r['reply_status']=='not-a-literal-direction-object' and r['selected_topic'] is None
    assert direction_input(wire(),None,[],MESSAGE,CATALOG)['reply_status']=='no-committed-response'


def test_saved_memory_project_state_and_once_only_delivery_are_not_rewritten():
    actor={'id':'a','can_author':True,'resources':30,'is_active':True,
        'project_start_year':1,'project_end_year':2,'newest_direction':{'direction':'short'},
        'memory_bank':[{'type':'select_research_direction','year':1,'direction':'short',
            'detailed_focus':'SCRIPTED focus','thought':'SCRIPTED reason','timestamp':99}],
        'institutional_context':[{'source':'developer-instruction-office','message_id':'literal',
            'emitted_year':1,'received_year':1,'payload':{
                'schema':'native-developer-static-instruction-v1','instruction':MESSAGE}}]}
    state={'year':4,'ecosystem_data':{'agents':[actor]}}
    before=digest(state);annual,memories,messages=native_history([state],MESSAGE,CATALOG)
    assert digest(state)==before
    assert annual[0]['authors'][0]['project_end_year']==2
    assert memories[0]['catalog_duration_years']==1 and memories[0]['literal_memory_sha256']==digest(actor['memory_bank'][0])
    assert len(messages)==1 and messages[0]['literal_declared_instruction']


def test_ordered_actual_sqlite_pair_api_retains_uncommitted_inputs(tmp_path):
    (tmp_path/'replies').mkdir();a=wire('a');b=wire('b')
    (tmp_path/'wire-requests.jsonl').write_text('\n'.join(json.dumps(w) for w in [a,a,b])+'\n')
    with sqlite3.connect(tmp_path/'replies/responses.sqlite') as db:
        db.execute('CREATE TABLE replies (payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        body=json.dumps(response());sha=hashlib.sha256(body.encode()).hexdigest()
        for w in (a,b):db.execute('INSERT INTO replies VALUES (?,?,?,?)',(w['payload_sha256'],'response',body,sha))
    wires,replies=completed_pairs(tmp_path)
    assert len(wires)==3 and list(replies)==[0,2]
    with sqlite3.connect(tmp_path/'replies/responses.sqlite') as db:db.execute("UPDATE replies SET data_sha='wrong'")
    with pytest.raises(ValueError,match='response body'):completed_pairs(tmp_path)


def test_full_export_api_keeps_three_cases_and_literal_sealed_outputs(tmp_path,monkeypatch):
    from types import SimpleNamespace
    p=prospective_plan();root=tmp_path/'raw';root.mkdir();save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    worlds=[];states={}
    for job in p['jobs']:
        cell=root/'controls'/job['identity']/'worlds'/(job['identity']+'-s61001');(cell/'replies').mkdir(parents=True)
        with sqlite3.connect(cell/'replies/responses.sqlite') as db:
            db.execute('CREATE TABLE replies (payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        (cell/'wire-requests.jsonl').write_text('')
        for year in (1,2,3,4):states[cell.name,year]={'year':year,'ecosystem_data':{'agents':[]}}
        worlds.append({**job,'status':'complete','scores':{'throughput':0,'content-utility':0},
            'loaded':{'context':str(cell/'loaded-role-context-000.json')},
            'physical_proof':{'annual_checkpoints':[{'year':year,'SCRIPTED':'decoder mocked'} for year in (1,2,3,4)]}})
    a={'schema':'scienceutopia.native-instruction-timing-support-audit.v1','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'closure':{'terminal':{'status':'closed'}},
        'source_proof':{'status':'verified-exact-source-closure','SCRIPTED':True},
        'new_model_calls':0,'new_code_executions':0,'worlds':worlds,
        'raw_inventory_sha256':digest(module._inventory(root))}
    one,two=tmp_path/'audit-one.json',tmp_path/'audit-two.json';save(one,a);save(two,a)
    monkeypatch.setattr(module,'pinned_revision',lambda *args:p['source_commit'])
    monkeypatch.setattr(module,'checkpoint',lambda cell,item,system:states[cell.name,item['year']])
    before=module._inventory(root)
    for name in ('export-one','export-two'):
        module.export(SimpleNamespace(run=root,audit_one=one,audit_two=two,output=tmp_path/name))
    assert (tmp_path/'export-one/report.json').read_bytes()==(tmp_path/'export-two/report.json').read_bytes()
    report=checked(json.loads((tmp_path/'export-one/report.json').read_text()))
    assert len(report['worlds'])==3 and all(w['direction_requests']==[] for w in report['worlds'])
    assert not report['policy_selection'] and not report['new_model_calls']
    assert module._inventory(root)==before
