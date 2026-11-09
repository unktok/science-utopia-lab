"""Read-only timestamped observation of pre-scale journals, never a heartbeat.

Known files and outcomes are projected; an absent terminal record stays unknown.
This exporter does not run models, code, campaigns or original-source audits.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.replay.campaign_adapter import web_event_stream_hash
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic

SCHEMA='scienceutopia.pre-scale-observatory.v1'


def read(path):
    return checked(json.loads(Path(path).read_text()))


def project(information_run,*,search_run=None,observed_utc=None):
    root=Path(information_run);plan=read(root/'plan.json')
    if plan.get('schema')!='scienceutopia.pre-scale-pilot.v1.plan':
        raise ValueError('explicit native information-study plan required')
    source=plan['source_commit']
    if not isinstance(source,str) or len(source)!=40:raise ValueError('exact source pin required')
    numeric=[];certificate=root/'numeric-readiness/certificate.json'
    if certificate.exists():
        cert=read(certificate)
        if cert['provider']!=plan['designer'] or cert['runtime']!=plan['runtime']:
            raise ValueError('numeric certificate source/model differs from its study')
        for case in cert['cases']:
            path=(root/case['journal_relative']/'result.json')
            if file_sha256(path)!=case['result_sha256']:raise ValueError('numeric terminal hash changed')
            result=read(path)
            numeric.append({'objective':case['objective'],'status':result['status'],
                'request_sha256':case['request_sha256'],'result_sha256':case['result_sha256'],
                'scientific_loss':None,'retained_parent_explicitly':
                    result['definition']['provenance']['retained_parent_explicitly'] if result['definition'] else None})
    rows=[]
    for seed in plan['mechanism_seeds']:
        for condition in ('M0','M1','M2','M3'):
            identity=condition+'-s'+str(seed);cell=root/'mechanisms'/identity
            row={'id':identity,'condition':condition,'seed':seed,'status':'not-dispatched',
                'scores':None,'observation_sha256':None}
            if (cell/'started.json').exists():
                start=read(cell/'started.json')
                if start['plan_sha256']!=plan['content_sha256'] or start['identity']!=identity:
                    raise ValueError('mechanism dispatch intent differs from plan')
                row['status']='started-no-terminal-observation'
            if (cell/'observation.json').exists():
                observation=read(cell/'observation.json');scores=read(cell/'cross-scores.json')
                if not (cell/'started.json').exists():raise ValueError('observation without dispatch intent')
                row.update(status=observation['status'],scores={k:scores[k]['loss'] for k in plan['losses']},
                    observation_sha256=file_sha256(cell/'observation.json'))
            rows.append(row)
    closure=root/'mechanisms-complete.json'
    if closure.exists():
        complete=read(closure)
        if complete['plan_sha256']!=plan['content_sha256']:
            raise ValueError('mechanism closure plan differs')
        for relative,identity in complete['all_observation_file_sha256'].items():
            if file_sha256(root/relative)!=identity:raise ValueError('closed observation changed')
        if len(complete['all_observation_file_sha256'])!=12 or any(r['status']!='complete' for r in rows):
            raise ValueError('mechanism closure does not cover all normal observations')
    search={'status':'not-dispatched','source_commit':None,'candidate_slots':[],
        'selection_fixed':False,'evaluation_observations':0,'evaluation_plan_worlds':None}
    if search_run is not None:
        other=Path(search_run);p=read(other/'plan.json')
        if p.get('schema')!='scienceutopia.pre-scale-search.v1.plan':raise ValueError('explicit search plan required')
        search.update(status='prepared-no-stage-terminal',source_commit=p['source_commit'])
        for arm in p['assignments']:
            path=other/'search'/'run-00'/arm.replace(':','--')/'campaign/native-adaptive-state.json'
            if not path.exists():continue
            state=json.loads(path.read_text())
            # This is a projection, not a replacement for full campaign replay.
            for generation,record in enumerate(state['records']):
                o=record['observations'][0] if record['observations'] else None
                search['candidate_slots'].append({'arm':arm,'generation':generation,
                    'status':'generation-failure' if record['generation_error'] else o['status'] if o else 'unknown',
                    'loss':o['loss'] if o else None})
        if (other/'selection.json').exists():
            s=read(other/'selection.json')
            if s['plan_sha256']!=p['content_sha256']:raise ValueError('selection source mismatch')
            search['selection_fixed']=True
        if (other/'evaluation-plan.json').exists():
            e=read(other/'evaluation-plan.json')
            if not search['selection_fixed'] or e['selection_sha256']!=s['content_sha256']:
                raise ValueError('evaluation precedes frozen selection')
            search['evaluation_plan_worlds']=len(e['jobs'])
        search['evaluation_observations']=len(list(other.glob('evaluation/*/observation.json')))
        if (other/'complete.json').exists():
            c=read(other/'complete.json')
            if (c['plan_sha256']!=p['content_sha256'] or not search['selection_fixed']
                    or c['selection_sha256']!=s['content_sha256']
                    or c['evaluation_physical_worlds']!=search['evaluation_observations']
                    or search['evaluation_plan_worlds']!=search['evaluation_observations']):
                raise ValueError('search closure is incomplete or mismatched')
            search['status']='recorded-closed'
    payload={'schema':SCHEMA,'observed_utc':observed_utc or datetime.now(timezone.utc).isoformat(),
        'observation_kind':'timestamped-journal-projection-not-live-heartbeat-or-independent-audit',
        'scope':'Actual local study journals. No synthetic outcomes or inferred wins.',
        'scientist_model':plan['scientist']['model'],'designer_model':plan['designer']['model'],
        'information':{'source_commit':source,'plan_sha256':plan['content_sha256'],
            'numeric_readiness':numeric,'worlds':rows,'closure_recorded':closure.exists()},
        'search':search,'boundaries':{'loss_is_not_scientific_truth':True,
            'unknown_is_not_zero':True,'source_specific_certificates':True,'no_submission_from_viewer':True}}
    return {'schema':SCHEMA+'.envelope','payload':payload,'payload_sha256':digest(payload),
        'web_sha256':web_event_stream_hash([payload])}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--information-run',type=Path,required=True);p.add_argument('--search-run',type=Path)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    envelope=project(args.information_run,search_run=args.search_run)
    write_json_atomic(args.output,envelope,sort_keys=True,allow_nan=False)
    print(json.dumps({'output':str(args.output),'snapshot_sha256':envelope['payload_sha256'],
        'native_inference_calls':0,'started_is_not_running':True}))


if __name__=='__main__':main()
