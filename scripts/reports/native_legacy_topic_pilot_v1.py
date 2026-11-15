"""Literal paired topic-control readout; no inference, execution or reselection."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_content_overlap_v1 import overlap
from scripts.reports.native_institution_effect_trace_v1 import checkpoint
from scripts.reports.native_instruction_timing_v1 import completed_pairs
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_resource_cost import METRIC, UNCOLLECTED_METRIC
from utopia.system.design_patch import clone, digest
from utopia.system.native_legacy_topic_planning import EVENT
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-legacy-topic-pilot-readout.v1'


def summarize_world(root,world):
    cell=Path(world['loaded']['context']).resolve().parent
    if not cell.is_relative_to(root): raise ValueError('audited world outside original raw')
    states=[checkpoint(cell,item,world['system']) for item in world['physical_proof']['annual_checkpoints']]
    if world['status']!='complete' or [s['year'] for s in states]!=[1,2,3,4]:
        raise ValueError('complete original four-year world required')
    events=[e for e in states[-1]['native_system']['events'] if e['event_type']==EVENT]
    assignments=[]
    for event in events:
        p=event['payload']; a=p['assignment']; topic=a['direction']['topic']
        assignments.append({'year':event['year'],'actor_id':a['actor_id'],'topic':topic,
            'original_duration':a['direction']['years'],'project_start_year':a['project_start_year'],
            'project_end_year':a['project_end_year'],'outside_core':topic not in p['eligible_actor_before']['expertise'],
            'core_expertise':clone(p['eligible_actor_before']['expertise']),
            'eligible_topics':clone(p['eligible_topics']),'catalog_sha256':p['catalog_sha256'],
            'event_id':event['event_id'],'command_key':p['command_key']})
    if len(assignments)!=len(world['physical_proof']['native_counts']['project_assignments_verified']):
        raise ValueError('actual validation/effect count differs')
    annual=[{'year':s['year'],'authors':[{k:clone(a.get(k)) for k in
        ('id','resources','is_active','expertise','newest_direction','project_start_year','project_end_year')}
        for a in s['ecosystem_data']['agents'] if a['can_author']]} for s in states]
    measurement,=world['measurements']; metrics=measurement['metrics']
    if any(metrics[k]['status']!='measured' for k in (METRIC,UNCOLLECTED_METRIC)):
        raise ValueError('actual collected and separate uncollected resource measurement required')
    wires,replies=completed_pairs(cell)
    sequences={'wire_requests':len(wires),'completed_responses':len(replies),
        'wire_inputs_without_committed_reply':len(wires)-len(replies),
        'ordered_full_request_payload_sha256':digest([w['payload'] for w in wires]),
        'ordered_literal_response_choices_sha256':digest([replies[i]['choices'] for i in sorted(replies)])}
    return ({k:clone(world[k]) for k in ('identity','condition','seed','status','scores')}|{
        'resource_cost':metrics[METRIC]['value'],'uncollected_activity_cost':metrics[UNCOLLECTED_METRIC]['value'],
        'assignments':assignments,'outside_core_assignments':sum(a['outside_core'] for a in assignments),
        'annual':annual,'request_sequence':sequences,
        'accepted_content':clone(measurement['common_content_observer']['accepted_decisions'])},wires)


def export(args):
    root,frozen,out=args.run.resolve(),args.frozen_source.resolve(),args.output.resolve()
    source=pinned_revision(frozen); reader=pinned_revision(ROOT)
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen) or out.is_relative_to(ROOT):
        raise ValueError('fresh readout outside original raw and source required')
    paths=[root/'plan.json',args.audit_one.resolve(),args.audit_two.resolve()]
    if paths[1]==paths[2] or paths[1].read_bytes()!=paths[2].read_bytes():
        raise ValueError('two distinct matching original-source audits required')
    inputs={str(p):file_sha256(p) for p in paths}; before=_inventory(root)
    plan,audit=[checked(json.loads(p.read_text())) for p in paths[:2]]
    if (plan['schema']!='scienceutopia.native-legacy-topic-pilot.v1.plan'
            or audit['schema']!='scienceutopia.native-legacy-topic-pilot-audit.v1'
            or plan['source_commit']!=source or audit['source_commit']!=source
            or audit['plan_sha256']!=plan['content_sha256']
            or audit['closure']['terminal']!=checked(json.loads((root/'terminal.json').read_text()))
            or audit['closure']['terminal']['status']!='closed'
            or audit['source_proof']['status']!='verified-exact-source-closure'
            or digest(before)!=audit['raw_inventory_sha256'] or len(audit['worlds'])!=2
            or [j['condition'] for j in plan['jobs']]!=['core-only','core-plus-related']
            or audit['automatic_invention'] or audit['policy_selection'] or audit['held_out_world_seeds']):
        raise ValueError('normally closed exact two-control original source/audit/raw required')
    worlds,wires=[],[]
    for job,world in zip(plan['jobs'],audit['worlds']):
        if any(world[k]!=v for k,v in job.items()): raise ValueError('literal ordered developer control differs')
        row,sequence=summarize_world(root,world); worlds.append(row); wires.append(sequence)
    left,right=[[w['payload'] for w in seq] for seq in wires]
    n=next((i for i,(a,b) in enumerate(zip(left,right)) if a!=b),min(len(left),len(right)))
    identical=left==right
    first=None if identical else {'wire_index':n,'zero_based':True,
        'left':None if n==len(left) else {'year':wires[0][n]['year'],'payload_sha256':digest(left[n])},
        'right':None if n==len(right) else {'year':wires[1][n]['year'],'payload_sha256':digest(right[n])}}
    result={'schema':SCHEMA,'analysis_source_commit':reader,'scientific_source_commit':source,
        'plan_sha256':plan['content_sha256'],'audit_content_sha256':audit['content_sha256'],
        'raw_inventory_sha256':digest(before),'worlds':worlds,
        'accepted_content_overlap':overlap(worlds[0]['accepted_content'],worlds[1]['accepted_content']),
        'full_scientist_request_sequences_equal':identical,'first_literal_request_difference':first,
        'scope':'Two same-authority hand rules on one reused condition. Actual original assignments/calendars, '
        'full literal request paths, fixed opinion content overlap and collected native costs. No invented '
        'institution, independent replication, global optimum, causal mediation or scientific truth claim.',
        'new_model_calls':0,'new_code_executions':0,'loss_or_selection_changed':False,
        'held_out_evaluation':False,'automatic_invention':False,'publication_ready':False}
    if (before!=_inventory(root) or inputs!={str(p):file_sha256(p) for p in paths}
            or pinned_revision(frozen)!=source or pinned_revision(ROOT)!=reader):
        raise ValueError('original raw or bound source changed during readout')
    out.mkdir(parents=True); save(out/'report.json',result)
    columns=['condition','seed','throughput','content-utility','resource_cost',
             'uncollected_activity_cost','project_assignments','outside_core_assignments','scientist_requests']
    with (out/'controls.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns); writer.writeheader()
        writer.writerows({k:(w['scores'][k] if k in w['scores'] else len(w['assignments'])
            if k=='project_assignments' else w['request_sequence']['wire_requests']
            if k=='scientist_requests' else w[k]) for k in columns} for w in worlds)
    save(out/'manifest.json',{'schema':SCHEMA+'.export','inputs':inputs,
        'analysis_source_commit':reader,'adapter_file_sha256':file_sha256(Path(__file__)),
        'files':{p.name:file_sha256(p) for p in sorted(out.iterdir())},'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'worlds':len(worlds),'assignments':[len(w['assignments']) for w in worlds]}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    keys=('run','frozen-source','audit-one','audit-two','output')
    for key in keys: parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if os.environ.get('SCIENCE_UTOPIA_COLD_TOPIC_READOUT_WORKER')=='1': export(args); return
    result=subprocess.run([sys.executable,'-B','-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()),str(Path(__file__).resolve()),
        *[v for key in keys for v in ('--'+key,str(getattr(args,key.replace('-','_')).resolve()))]],
        cwd=args.frozen_source,env={**os.environ,'PYTHONHASHSEED':'42',
            'SCIENCE_UTOPIA_COLD_TOPIC_READOUT_WORKER':'1'},timeout=1800,check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__=='__main__': main()
