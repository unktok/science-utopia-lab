"""Literal native input-frame readout; no mocked result is science evidence."""
import hashlib
import json
import sqlite3

import pytest

from scripts.reports.native_instruction_timing_v1 import direction_input, native_history, completed_pairs
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
