"""Observed instruction inputs and native topic/duration choices, no inference."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_institution_effect_trace_v1 import checkpoint
from utopia.agents.research_direction import DIRECTIONS_DICT
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-instruction-timing-report.v1'


def direction_input(wire, response, memories, message, catalog):
    """Parse only the source-defined direction frame; ambiguity stays visible."""
    payload=wire['payload']
    schema=payload.get('response_format',{}).get('json_schema',{})
    if schema.get('name')!='research_direction_selection':return None
    texts=[m.get('content') for m in payload.get('messages',[]) if isinstance(m.get('content'),str)]
    frames=[s for s in texts if '## Directions You Can Choose From' in s]
    candidates=[];frame_status='unassessed-frame'
    if len(frames)==1 and '## Your Task' in frames[0]:
        frame=frames[0].split('## Directions You Can Choose From',1)[1].split('## Your Task',1)[0]
        blocks=re.findall(r'### Direction [0-9]+: ([^\n]+)\n(.*?)(?=### Direction [0-9]+:|\Z)',frame,re.S)
        for topic,body in blocks:
            duration=re.findall(r'^- Expected Project Duration: ([0-9]+) year\(s\)',body,re.M)
            if len(duration)!=1:break
            topic=topic.strip();years=int(duration[0])
            candidates.append({'topic':topic,'displayed_duration_years':years,
                'matches_original_catalog':None if topic not in catalog else catalog[topic]==years})
        else:
            if blocks and len({c['topic'] for c in candidates})==len(candidates):frame_status='literal-displayed-candidates'
        if frame_status!='literal-displayed-candidates':candidates=[]
    selected=None;reply_status='no-committed-response'
    if response is not None:
        try:
            body=response['choices'][0]['message']['content'];parsed=json.loads(body)
            if isinstance(parsed,dict) and all(isinstance(parsed.get(k),str) for k in ('topic','detailed_focus','reason')):
                selected={k:parsed[k] for k in ('topic','detailed_focus','reason')};reply_status='literal-direction-object'
            else:reply_status='not-a-literal-direction-object'
        except (ValueError,KeyError,IndexError,TypeError):reply_status='not-a-literal-direction-object'
    matches=[]
    if selected is not None:
        matches=[m['actor_id'] for m in memories if m['year']==wire['year']
            and m['topic']==selected['topic'] and m['detailed_focus']==selected['detailed_focus']
            and m['reason']==selected['reason']]
    minimum=min((c['displayed_duration_years'] for c in candidates),default=None)
    shown=next((c for c in candidates if selected is not None and c['topic']==selected['topic']),None)
    return {'year':wire['year'],'payload_sha256':wire['payload_sha256'],
        'literal_instruction_present':any(message in text for text in texts),
        'frame_status':frame_status,'displayed_candidates':candidates,
        'minimum_displayed_duration_years':minimum,'reply_status':reply_status,
        'selected_topic':None if selected is None else selected['topic'],
        'selected_catalog_duration_years':None if selected is None else catalog.get(selected['topic']),
        'selected_is_shortest_displayed':None if shown is None else shown['displayed_duration_years']==minimum,
        'matching_actual_memory_actor_ids':sorted(matches),
        'unique_actor_attribution':len(matches)==1,
        'literal_response_choices_sha256':None if response is None else digest(response.get('choices'))}


def native_history(states, message, catalog):
    annual=[]
    for state in states:
        annual.append({'year':state['year'],'authors':[
            {k:a.get(k) for k in ('id','resources','is_active','project_start_year','project_end_year','newest_direction')}
            for a in state['ecosystem_data']['agents'] if a['can_author']]})
    memories=[];messages=[]
    for actor in states[-1]['ecosystem_data']['agents']:
        if not actor['can_author']:continue
        for m in actor['memory_bank']:
            if m.get('type')=='select_research_direction':
                memories.append({'actor_id':actor['id'],'year':m['year'],'topic':m['direction'],
                    'catalog_duration_years':catalog.get(m['direction']),'detailed_focus':m.get('detailed_focus'),
                    'reason':m.get('thought'),'literal_memory_sha256':digest(m)})
        for m in actor.get('institutional_context',[]):
            if m.get('source')=='developer-instruction-office':
                messages.append({'actor_id':actor['id'],'message_id':m['message_id'],
                    'emitted_year':m['emitted_year'],'received_year':m['received_year'],
                    'literal_declared_instruction':m.get('payload')=={
                        'schema':'native-developer-static-instruction-v1','instruction':message},
                    'literal_message_sha256':digest(m)})
    return annual,memories,messages


def completed_pairs(cell):
    wires=[json.loads(line) for line in (cell/'wire-requests.jsonl').read_text().splitlines()]
    if any(digest(w['payload'])!=w['payload_sha256'] for w in wires):raise ValueError('original wire hash differs')
    with sqlite3.connect((cell/'replies/responses.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        replies=db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    offset=0;completed={}
    for payload_sha,outcome,body,body_sha in replies:
        if outcome!='response' or hashlib.sha256(body.encode()).hexdigest()!=body_sha:raise ValueError('original response body differs')
        while offset<len(wires) and wires[offset]['payload_sha256']!=payload_sha:offset+=1
        if offset==len(wires):raise ValueError('original ordered request/reply join differs')
        completed[offset]=json.loads(body);offset+=1
    return wires,completed


def export(args):
    root,out=args.run.resolve(),args.output.resolve();source=pinned_revision(ROOT)
    if out.exists() or out.is_relative_to(root):raise ValueError('fresh report outside scientific raw required')
    if args.audit_one.read_bytes()!=args.audit_two.read_bytes():raise ValueError('two matching original audits required')
    paths=[root/'plan.json',args.audit_one,args.audit_two];hashes={str(p):file_sha256(p) for p in paths}
    plan,audit=[checked(json.loads(p.read_text())) for p in paths[:2]]
    before=_inventory(root)
    if (plan['schema']!='scienceutopia.native-instruction-timing-support.v1.plan'
            or audit['schema']!='scienceutopia.native-instruction-timing-support-audit.v1'
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or audit['closure']['terminal']['status']!='closed' or len(audit['worlds'])!=3
            or audit['source_proof']['status']!='verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions'] or digest(before)!=audit['raw_inventory_sha256']):
        raise ValueError('normally closed exact source/audit/raw required')
    # Read the original source's catalog, never the reader's possibly changed one.
    if plan['source_commit']!=source:raise ValueError('run this report from the frozen scientific source')
    catalog={name:d.years for name,d in DIRECTIONS_DICT.items()};worlds=[]
    if [w['identity'] for w in audit['worlds']]!=[j['identity'] for j in plan['jobs']]:
        raise ValueError('exact three declared identities and order required')
    for w,job in zip(audit['worlds'],plan['jobs']):
        if w['system']!=job['system'] or w['status']!='complete':raise ValueError('complete literal control required')
        cell=Path(w['loaded']['context']).resolve().parent
        if not cell.is_relative_to(root):raise ValueError('original world outside audited raw')
        states=[checkpoint(cell,item,w['system']) for item in w['physical_proof']['annual_checkpoints']]
        if [s['year'] for s in states]!=[1,2,3,4]:raise ValueError('all four original annual states required')
        annual,memories,messages=native_history(states,plan['instruction'],catalog)
        wires,replies=completed_pairs(cell)
        directions=[]
        for i,wire in enumerate(wires):
            result=direction_input(wire,replies.get(i),memories,plan['instruction'],catalog)
            if result is not None:directions.append({'wire_index':i,**result})
        worlds.append({'identity':w['identity'],'condition':w['condition'],'seed':w['seed'],
            'scores':w['scores'],'annual':annual,'direction_memories':memories,'stored_instructions':messages,
            'direction_requests':directions,'physical_wire_requests':len(wires),
            'committed_responses':len(replies),'wire_without_committed_reply':len(wires)-len(replies)})
    result={'schema':SCHEMA,'scientific_source_commit':source,'plan_sha256':plan['content_sha256'],
        'audit_content_sha256':audit['content_sha256'],'raw_inventory_sha256':digest(before),'worlds':worlds,
        'scope':'Actual native choice traces. Displayed candidates need not exhaust legacy allowed related topics; '
            'an unlisted selection is not declared invalid. Unparseable frames/replies and ambiguous actor matches '
            'stay explicit, without repaired output or guessed attribution. Stored instructions, content in a '
            'request, chosen topic and completed outcomes are distinct evidence. No pure mediation, independent '
            'replication, program equivalence, scientific truth or policy improvement is inferred.',
        'new_model_calls':0,'new_code_executions':0,'policy_selection':False,'publication_ready':False}
    if before!=_inventory(root) or hashes!={str(p):file_sha256(p) for p in paths} or pinned_revision(ROOT)!=source:
        raise ValueError('raw inputs or frozen reader source changed')
    out.mkdir(parents=True);save(out/'report.json',result)
    save(out/'manifest.json',{'schema':SCHEMA+'.export','inputs':hashes,'scientific_source_commit':source,
        'report_sha256':file_sha256(out/'report.json'),'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'worlds':len(worlds),'direction_requests':sum(len(w['direction_requests']) for w in worlds),
        'report_sha256':file_sha256(out/'report.json')}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    export(p.parse_args())


if __name__=='__main__':main()
