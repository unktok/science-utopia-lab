"""Read-only projection of a CLOSED original-source V2 audit, never a new audit.

No model, code mechanism, simulator or inference endpoint is executed. Keep all
failed slots, exact ties, shared physical evaluations and missing pairs visible.
"""
from copy import deepcopy
from datetime import datetime
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json,write_json_atomic

SCHEMA='scienceutopia.native-design-freedom-study.v2'


def checked(value,schema):
    if (value.get('schema')!=schema or value.get('content_sha256')!=digest(
            {k:v for k,v in value.items() if k!='content_sha256'})):
        raise ValueError('exact input schema/content hash required')


def number(value):
    if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
        raise ValueError('scores must be finite nonboolean numbers or explicit null')
    return value


def descriptive(rows,key):
    values=[number(row.get(key)) for row in rows]
    known=[v for v in values if v is not None]
    return {'scheduled':len(rows),'available':len(known),'missing':len(rows)-len(known),
        'values':values,'mean':statistics.mean(known) if known else None,
        'population_sd':statistics.pstdev(known) if known else None,
        'minimum':min(known) if known else None,'maximum':max(known) if known else None,
        'conditioned_on_available_pairs_or_scores':True,'missing_imputed':False}


def physical_summary(proof):
    if proof is None:return None
    return {'exact_full_proof_sha256':digest(proof),
        'response_costs':{k:proof.get('response_proof',{}).get(k) for k in
            ['researcher_responses','wire_requests','uncheckpointed_responses']},
        'code_costs':{k:proof.get('code_proof',{}).get(k) for k in
            ['recorded_executions','committed_events','ambiguous_native_event_count','one_to_one_physical_execution_proven']},
        'annual_checkpoints':deepcopy(proof.get('annual_checkpoints')),
        'native_counts':deepcopy(proof.get('native_counts')),
        'full_physical_evidence_retained_in_input_audit':True}


def project(plan,audit,*,expected_source):
    checked(plan,SCHEMA);checked(audit,SCHEMA+'.audit')
    if (plan['source_commit']!=expected_source or audit['source_commit']!=expected_source
            or audit['plan_sha256']!=plan['content_sha256']
            or audit['source_proofs']['status']!='verified-exact-source-closure'
            or audit['raw_inventory_unchanged'] is not True
            or audit['new_model_calls']!=0 or audit['new_code_executions']!=0):
        raise ValueError('closed exact-source audit/protocol binding required')
    checked(audit['selection'],SCHEMA+'.selection')
    if audit['selection']['plan_sha256']!=plan['content_sha256']:
        raise ValueError('selection differs from study plan')
    if set(audit['selection']['selected'])!=set(plan['assignments']):raise ValueError('selected arms differ')
    if set(audit['runs'])!=set(plan['campaign_bindings']):raise ValueError('search runs differ')
    arms={};all_rows=[]
    for run,bindings in plan['campaign_bindings'].items():
        if set(audit['runs'][run])!=set(bindings):raise ValueError('search arms differ')
        arms[run]={}
        for arm,binding in bindings.items():
            result=audit['runs'][run][arm];assignment=plan['assignments'][arm]
            if (result['binding']!=binding or not result['terminal'] or result['pending'] is not None
                    or result['consumed_native_slots']!=plan['generations']
                    or len(result['observations'])!=plan['generations']):
                raise ValueError('search lacks all declared terminal slots')
            rows=[];incumbent=None
            baseline=number(audit['references']['open-seed']['scores'][assignment['objective']]['loss'])
            incumbent=baseline
            for g,row in enumerate(result['observations']):
                if row['generation']!=g:raise ValueError('generation chronology differs')
                scores={k:number(row['cross_scores'][loss['id']]) for k,loss in plan['losses'].items()}
                own=number(row['own_loss'])
                if own!=scores[assignment['objective']]:raise ValueError('assigned loss differs from cross-score')
                if own is not None and row['status']!='complete':raise ValueError('failed assigned loss is numeric')
                if own is not None:incumbent=own if incumbent is None else min(incumbent,own)
                projected={'row_id':run+':'+arm+':g'+str(g),'run':run,'arm':arm,'generation':g,
                    'controller_seed':binding['seed'],'world_seed':42,'status':row['status'],
                    'own_loss':own,'cross_scores':scores,'best_including_initial_so_far':incumbent,
                    'system_fingerprint':row['system_fingerprint'],'checkpoint_sha256':row['checkpoint_sha256'],
                    'metrics':deepcopy(row['metrics']),'lineage':deepcopy(row['lineage']),
                    'physical_forward_completed':row['physical_proof'] is not None,
                    'physical_evidence':physical_summary(row['physical_proof'])}
                rows.append(projected);all_rows.append(projected)
            arms[run][arm]={**deepcopy(assignment),'rows':rows,'initial_loss':baseline,
                'best_including_initial':incumbent,'valid_assigned_losses':sum(r['own_loss'] is not None for r in rows),
                'native_costs':{k:deepcopy(result[k]) for k in ['physical_native_worlds',
                    'physical_world_directory_count','physical_researcher_responses','physical_wire_requests',
                    'recorded_code_executions_including_partial','completed_researcher_model_call_seconds']},
                'designer_costs':{k:deepcopy(v) for k,v in result.get('designer',{}).items() if k!='proofs'},
                'designer_absent_by_design':assignment['method']=='random'}
    if len(all_rows)!=plan['budget']['search_slots']:raise ValueError('scheduled slot count differs')
    histories={}
    for arm in plan['assignments']:
        values=[{'run':run,'controller_seed':plan['campaign_bindings'][run][arm]['seed'],
            'initial_loss':body[arm]['initial_loss'],'best_including_initial':body[arm]['best_including_initial'],
            'valid_assigned_losses':body[arm]['valid_assigned_losses']}
            for run,body in arms.items()]
        histories[arm]={'histories':values,'summary':descriptive(values,'best_including_initial'),
            'unit':'controller history on the SAME development world seed42, not independent world replication'}
    jobs=audit['evaluation_jobs']
    if len(jobs)>plan['evaluation']['maximum_physical_worlds']:raise ValueError('evaluation budget differs')
    if set(audit['evaluated'])!={j['job_id'] for j in jobs}:raise ValueError('physical evaluation jobs differ')
    evaluation=[];lookup={};conditions=[]
    for seed in plan['evaluation']['seeds']:
        for years in plan['evaluation']['years']:conditions.append((seed,years))
    conditions += [(c['seed'],c['years']) for c in plan['evaluation']['extended']]
    for job in jobs:
        proof=audit['evaluated'][job['job_id']];o=proof['observation']
        row={**{k:deepcopy(job[k]) for k in ['job_id','policy_sha256','labels','seed','years']},
            'observation_status':o['status'],
            'cross_scores':{k:number(proof['scores'][k]['loss']) for k in plan['losses']},
            'raw_measurements':deepcopy(o['metadata']['measurements']),
            'technical_failures':deepcopy(o['metadata']['technical_failures']),
            'physical_evidence':physical_summary(proof['physical_proof'])}
        evaluation.append(row)
        for label in job['labels']:
            key=(label,job['seed'],job['years'])
            if key in lookup:raise ValueError('duplicate physical evaluation label/condition')
            lookup[key]=row
    expected_labels={'reference:'+k for k in plan['reference_systems']}
    expected_labels.update('selected:'+k for k,v in audit['selection']['selected'].items() if v['system'] is not None)
    if set(lookup)!={(label,seed,years) for label in expected_labels for seed,years in conditions}:
        raise ValueError('missing or undeclared evaluated label/condition')
    paired={}
    for arm,selection in audit['selection']['selected'].items():
        paired[arm]={}
        if selection['system'] is None:continue
        label='selected:'+arm
        for reference in plan['reference_systems']:
            comparison={}
            for objective in plan['losses']:
                horizons={}
                for years in sorted({y for _,y in conditions}):
                    pairs=[]
                    for seed,h in conditions:
                        if h!=years:continue
                        target=lookup[(label,seed,years)];baseline=lookup[('reference:'+reference,seed,years)]
                        a,b=target['cross_scores'][objective],baseline['cross_scores'][objective]
                        pairs.append({'seed':seed,'years':years,'target_job_id':target['job_id'],
                            'reference_job_id':baseline['job_id'],'physically_shared':target['job_id']==baseline['job_id'],
                            'target_loss':a,'reference_loss':b,'difference':a-b if a is not None and b is not None else None})
                    horizons[str(years)]={'pairs':pairs,'summary':descriptive(pairs,'difference'),
                        'negative_difference_favors_selected':True,
                        'single_seed_diagnostic':len(pairs)==1}
                comparison[objective]=horizons
            paired[arm][reference]=comparison
    start,end=audit['writer']['started'],audit['writer']['ended']
    wall=(datetime.fromisoformat(end['ended_utc'])-datetime.fromisoformat(start['started_utc'])).total_seconds()
    if end['status']!='exited' or end['exit_code']!=0 or wall<0:raise ValueError('writer not closed normally')
    selection={k:deepcopy(v) for k,v in audit['selection'].items() if k not in ('all_rows','reference_systems')}
    selection['projection_omits_unselected_source_bodies']=True
    result={'schema':SCHEMA+'.report','classification':plan['classification'],
        'source_commit':expected_source,'plan_sha256':plan['content_sha256'],
        'input_audit_content_sha256':audit['content_sha256'],'selection':selection,
        'search_arms':arms,'development_history_summary':histories,'all_candidate_rows':all_rows,
        'evaluation':evaluation,'paired_vs_all_references':paired,
        'reference_scores':{k:{name:number(v['loss']) for name,v in entry['scores'].items()}
            for k,entry in audit['references'].items()},
        'physical_evaluation_jobs':len(jobs),'logical_evaluation_labels':len(expected_labels),
        'wall_seconds':wall,'calibrations':deepcopy(audit['certificates']),
        'loads':deepcopy(audit['designer_loads']),
        'interpretation':{'projection_is_not_a_new_raw_audit':True,'losses_define_ranking':True,
            'controller_histories_are_not_independent_world_seeds':True,
            'researchers_and_years_are_not_independent_replicates':True,
            'shared_policy_jobs_are_not_additional_observations':True,
            'horizons_at_the_same_seed_are_not_independent':True,
            'conditional_available_means_are_not_complete_expectations':True,
            'nulls_imputed':False,'method_superiority_established_by_report':False,
            'real_scientific_benefit_established_by_report':False},
        'new_model_calls':0,'new_code_executions':0}
    result['content_sha256']=digest(result)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--expected-source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv)
    if a.output.exists() or a.output.resolve().is_relative_to(a.plan.resolve().parent):
        p.error('fresh report output outside raw plan directory required')
    original={path:path.read_bytes() for path in [a.plan,a.audit]}
    data={path:decode_json(body.decode(),strict=True,finite_floats=True) for path,body in original.items()}
    result=project(data[a.plan],data[a.audit],expected_source=a.expected_source)
    if any(path.read_bytes()!=body for path,body in original.items()):raise ValueError('input evidence changed')
    result['projection_inputs']={str(path):hashlib.sha256(body).hexdigest() for path,body in original.items()}
    result['content_sha256']=digest({k:v for k,v in result.items() if k!='content_sha256'})
    write_json_atomic(a.output,result,sort_keys=True,allow_nan=False,indent=2)
    print({'content_sha256':result['content_sha256'],'candidate_slots':len(result['all_candidate_rows'])})
    return 0


if __name__=='__main__':raise SystemExit(main())
