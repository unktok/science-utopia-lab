"""Read-only timestamped observation of pre-scale journals, never a heartbeat.

Known files and outcomes are projected; an absent terminal record stays unknown.
This exporter does not run models, code, campaigns or original-source audits.
"""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.replay.campaign_adapter import web_event_stream_hash
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic

SCHEMA='scienceutopia.pre-scale-observatory.v1'
REFERENCES=('open-seed','legacy','reviewed-accept-all','no-review-accept-all',
    'no-review-reject-all','information-disconnected')


def read(path):
    return checked(json.loads(Path(path).read_text()))


def stage_projection(root,plan):
    """Stage journals describe recorded dispatch/completion, never liveness."""
    result={'observed_stage':None,'stage_error_type':None,'status':'prepared-no-stage-terminal'}
    for stage in ('readiness','search','evaluation'):
        path=root/(stage+'.started.json');end_path=root/(stage+'.ended.json')
        if end_path.exists() and not path.exists():raise ValueError('stage end without its dispatch record')
        if not path.exists():continue
        start=read(path)
        if start['stage']!=stage or start['plan_sha256']!=plan['content_sha256']:
            raise ValueError('stage dispatch plan differs')
        result.update(observed_stage=stage,status='stage-started-no-terminal',stage_error_type=None)
        if not end_path.exists():continue
        end=read(end_path)
        if (any(end.get(k)!=v for k,v in start.items() if k!='content_sha256')
                or end['status'] not in ('closed','stopped')
                or datetime.fromisoformat(end['ended_utc'])<datetime.fromisoformat(start['started_utc'])):
            raise ValueError('stage completion differs from original dispatch')
        result.update(status='stage-closed' if end['status']=='closed' else 'stage-stopped',
            stage_error_type=end.get('error_type') if end['status']=='stopped' else None)
    return result


def reference_projection(root,plan):
    if 'reference_order' not in plan and 'reference_systems' not in plan:return None
    order=plan['reference_order']
    if len(order)!=6 or set(order)!=set(REFERENCES) or set(plan['reference_systems'])!=set(order):
        raise ValueError('six unique declared reference systems required')
    rows=[]
    for name in order:
        cell=root/'references'/name
        row={'id':name,'seed':41001,'status':'not-dispatched','scores':None,'observation_sha256':None}
        started=cell/'started.json';observation=cell/'observation.json'
        if started.exists():
            start=read(started)
            if (start['identity']!='reference-'+name or start['seed']!=41001
                    or start['role']!='developer-reference'
                    or digest(start['system'])!=digest(plan['reference_systems'][name])):
                raise ValueError('reference dispatch differs from its declared system/seed')
            row['status']='started-no-terminal-observation'
        if observation.exists():
            if not started.exists():raise ValueError('reference observation without dispatch intent')
            o=read(observation);cross=read(cell/'cross-scores.json')
            if o['suggestion_id']!='reference-'+name or o['status'] not in ('complete','failed','invalid'):
                raise ValueError('reference terminal identity/status differs')
            scores={key:cross[key]['loss'] for key in ('throughput','efficiency','selective')}
            if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v)) for v in scores.values()):
                raise ValueError('reference losses must remain finite numbers or unknown')
            if o['status']=='complete' and any(v is None for v in scores.values()):
                raise ValueError('complete reference lacks actual measured cross-scores')
            if o['status']!='complete' and any(v is not None for v in scores.values()):
                raise ValueError('failed reference may not acquire a numerical loss')
            row.update(status=o['status'],scores=scores if o['status']=='complete' else None,
                observation_sha256=file_sha256(observation))
        rows.append(row)
    return rows


def readiness_projection(root,plan):
    result={'numeric':None,'editor':None}
    numeric=root/'numeric-readiness/certificate.json'
    if numeric.exists():
        c=read(numeric)
        if c['provider']!=plan['designer'] or c['runtime']!=plan['runtime'] or type(c['passed']) is not bool:
            raise ValueError('search numerical readiness binding differs')
        cases=c['cases']
        if (len(cases)>2 or any(type(case['submitted']) is not bool for case in cases)
                or len({case['objective'] for case in cases})!=len(cases)
                or any(case['objective'] not in ('throughput','efficiency') for case in cases)):
            raise ValueError('invalid numerical readiness cases')
        count=sum(case['submitted'] for case in cases)
        if count>2 or (c['passed'] and count!=2):
            raise ValueError('search numerical readiness counts differ')
        result['numeric']={'accepted':count,'total':2,'passed':c['passed'],'certificate_sha256':c['content_sha256']}
    editor=root/'editor-readiness/calibration/certificate.json'
    if editor.exists():
        c=read(editor);binding=c['plan']
        if (binding['source_commit']!=plan['source_commit'] or binding['provider']!=plan['designer']
                or binding['runtime']!=plan['runtime'] or type(c['all_controls_passed']) is not bool
                or len(binding['cases'])!=28 or len(c['records'])>28
                or any(type(record['ok']) is not bool for record in c['records'])):
            raise ValueError('search editor readiness binding/count differs')
        count=sum(record['ok'] for record in c['records'])
        if c['all_controls_passed'] and count!=28:raise ValueError('editor pass lacks all declared controls')
        result['editor']={'accepted':count,'total':28,'passed':c['all_controls_passed'],'certificate_sha256':c['content_sha256']}
    return result


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
    search={'status':'not-dispatched','observed_stage':None,'stage_error_type':None,'source_commit':None,'candidate_slots':[],
        'selection_fixed':False,'evaluation_observations':0,'evaluation_plan_worlds':None}
    if search_run is not None:
        other=Path(search_run);p=read(other/'plan.json')
        if p.get('schema')!='scienceutopia.pre-scale-search.v1.plan':raise ValueError('explicit search plan required')
        search.update(stage_projection(other,p),source_commit=p['source_commit'])
        references=reference_projection(other,p)
        if references is not None:search['reference_worlds']=references
        search['readiness']=readiness_projection(other,p)
        for arm in p['arm_order']:
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
