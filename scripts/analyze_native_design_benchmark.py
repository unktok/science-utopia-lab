#!/usr/bin/env python3
"""Original-source read-only audit of the complete matched V2 research study."""
import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from scripts import run_native_design_benchmark as driver
from scripts import native_design_benchmark_plan as spec
from scripts.native_benchmark_source import source_proofs
from scripts.native_benchmark_physical import physical_proof
from scripts.analyze_native_autonomous_search_v14 import read,_inventory,replay_campaign,audit_native_campaign
from scripts.analyze_native_staged_search_v15 import audit_authoring
from scripts.analyze_native_warmstart_v45 import _certificate_proof
from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
from utopia.optimization.native_loaded_roles_v38 import replay_loaded_context
from utopia.optimization.native_scientist_load_v38 import replay_load
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def loaded(path,context,*,provider,purpose,role,allow_unconfirmed=False):
    proof=replay_load(read(path.with_suffix('.started.json')),read(path) if path.exists() else None,
        provider=provider,purpose=purpose,role=role)
    valid=replay_loaded_context(read(context),expected={role:provider},purpose=purpose) if context.exists() else False
    confirmed=proof['empty_prompt_load_confirmed'] and valid
    if not confirmed and not allow_unconfirmed:
        raise ValueError('study role/context is failed or unknown')
    return {'load':str(path),'context':str(context),'proof':proof,'confirmed':confirmed}


def observation_proof(root,plan,*,identity,system,seed,years,role):
    root=Path(root);o=read(root/'observation.json');s=SystemSpec.from_dict(system)
    started=read(root/'started.json')
    if {k:started.get(k) for k in ['identity','seed','years','candidate_sha256','role']}!={
            'identity':identity,'seed':seed,'years':years,'candidate_sha256':digest(system),'role':role}:
        raise ValueError('study observation dispatch binding differs')
    if (o['suggestion_id']!=identity or o['observation_id']!='observation-'+identity or o['candidate']!=system
            or o['metadata']['world_backend']!='native-research-world'
            or o['metadata']['system_fingerprint']!=s.fingerprint
            or o['metadata']['loss_spec_sha256']!=loss_spec_sha256(plan['losses']['throughput'])):
        raise ValueError('study observation policy/seed/identity differs')
    scores={k:evaluate_loss(loss,o['metadata']['measurements']) for k,loss in plan['losses'].items()}
    if (read(root/'cross-scores.json')!=scores or o['loss']!=scores['throughput']['loss']
            or o['metadata']['loss_evaluation']!=scores['throughput']):
        raise ValueError('study observation scores differ from exact measurements')
    cells=list((root/'worlds').glob('*'))
    if len(cells)!=1 or cells[0].name!=identity+'-s'+str(seed):
        raise ValueError('study observation has undeclared/missing physical worlds')
    cell=cells[0]
    load=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=plan['scientist'],
        purpose='before-native-world:'+cell.name,role='scientist',allow_unconfirmed=o['status']=='failed')
    if o['status']=='complete':
        if len(o['metadata']['runs'])!=1 or o['metadata']['technical_failures']:
            raise ValueError('complete observation has ambiguous/failing native evidence')
        proof=physical_proof(cell,s,world=plan['world'],seed=seed,years=years,evidence=o['metadata']['runs'][0])
        if o['metadata']['measurements']!=[proof['measurement']]:
            raise ValueError('measurement does not match original physical checkpoint')
    elif o['status']=='failed' and o['loss'] is None and not o['metadata']['measurements']:
        if (cell/'replies/responses.sqlite').exists():
            if not load['confirmed']:raise ValueError('physical inference lacks a preceding confirmed role/context')
            proof=physical_proof(cell,s,world=plan['world'],seed=seed,years=years)
        else:proof={'status':'pre-response-journal-failure','loss':None,'files':_inventory(cell)}
    else:raise ValueError('unknown study observation outcome/null semantics')
    return {'observation':o,'scores':scores,'physical_proof':proof,'loaded':load}


def analyze(root,source):
    root=Path(root).resolve();before=_inventory(root)
    try:
        closure=source_proofs(ROOT,source,scripts=['scripts/run_native_design_benchmark.py',
            'scripts/analyze_native_design_benchmark.py'],resources=[spec.PROTOCOL,
            'research/objectives/losses/native-joint-v5-throughput.json',
            'research/objectives/losses/native-reviewed-production-efficiency-v13.json'])
        plan=read(root/'plan.json')
        usage=read(root/'evaluation-seed-usage.json')
        if (usage['content_sha256']!=digest({k:v for k,v in usage.items() if k!='content_sha256'})
                or usage['valid'] is not True or usage['seeds']!=list(spec.EVALUATION_SEEDS)
                or usage['errors'] or usage['prior_matching_runs']):
            raise ValueError('evaluation seed history check is absent, failed or unknown')
        if plan!=spec.build_plan(source=source,scientist=plan['scientist'],designer=plan['designer'],
                runtime_seed=plan['runtime_seed_binding'],backend=plan['backend'],seed_usage_sha256=usage['content_sha256']):
            raise ValueError('study plan differs from source-pinned reconstruction')
        start,end=read(root/'writer.started.json'),read(root/'writer.ended.json')
        if (start.get('action')!='all' or start.get('source_commit')!=source or start.get('status')!='started'
                or end!={**start,'status':'exited','exit_code':0,'ended_utc':end.get('ended_utc')}
                or datetime.fromisoformat(end['ended_utc'])<datetime.fromisoformat(start['started_utc'])):
            raise ValueError('study writer is not the declared closed run')
        runs={};journals=set();caches=set();loads=[];certificates={};physical_dirs=set()
        for run,bindings in plan['campaign_bindings'].items():
            runs[run]={}
            first=None
            for arm,binding in bindings.items():
                directory=root/'search'/run/'arms'/arm.replace(':','--')
                c=replay_campaign(directory/'campaign','blackbox')
                if c.binding!=binding:raise ValueError('study campaign binding differs')
                assigned=plan['assignments'][arm]
                result=audit_native_campaign(directory,method='blackbox',world=plan['world'],
                    classification=spec.CLASSIFICATION,loss=plan['losses'][assigned['objective']],
                    initial_system=plan['initial_system'],expected_budget=4,experiment=plan['experiment'])
                if not result['terminal'] or result['consumed_native_slots']!=4:
                    raise ValueError('study arm lacks its four terminal slots')
                if assigned['method']!='random':
                    result['designer']=audit_authoring(directory/'authoring',result['records'],provider=plan['designer'],
                        designer=plan['designer_settings'],classification=spec.CLASSIFICATION)
                    if result['designer']['generations']!=4 or result['designer']['recorded_POST_attempts']>64:
                        raise ValueError('designer arm exceeds the declared finite budget')
                    journals.update((directory/'authoring'/('generation-'+p['request_sha256'])).resolve()
                        for p in result['designer']['proofs'])
                    for g in range(4):
                        purpose='before-design-study-proposal:'+run+':'+arm+':g'+str(g)
                        path=directory/f'designer-load-{g}.json'
                        loads.append(loaded(path,directory/f'designer-context-{g}.json',provider=plan['designer'],purpose=purpose,role='designer'))
                        when=read(path.with_suffix('.started.json'))['started_utc']
                        first=min(first,when) if first else when
                elif (directory/'authoring').exists():raise ValueError('random baseline has undeclared LLM authoring')
                for cache in result['physical_response_caches']:
                    p=Path(cache['path']).resolve()
                    if p in caches:raise ValueError('physical scientist cache reused across search slots')
                    caches.add(p)
                complete_ids={r['run_id'] for observation in result['observations'] if observation['status']=='complete'
                    for r in observation['observation']['metadata']['runs']}
                for cell in (directory/'worlds').glob('*'):
                    physical_dirs.add(cell.resolve())
                    gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',
                        provider=plan['scientist'],purpose='before-native-world:'+cell.name,role='scientist',
                        allow_unconfirmed=cell.name not in complete_ids)
                    if (cell/'replies/responses.sqlite').exists() and not gate['confirmed']:
                        raise ValueError('search response journal lacks confirmed preceding scientist context')
                    loads.append(gate)
                for proof in [*result['partial_physical_run_proofs']]:
                    if 'response_proof' in proof:
                        binding=proof['response_proof']['response_binding']
                        if binding['science_config']['maximum_http_attempts']!=512:
                            raise ValueError('partial search HTTP budget binding differs')
                for row in result['observations']:
                    proof=row.get('physical_proof')
                    if proof and 'response_proof' in proof:
                        binding=proof['response_proof']['response_binding']
                        if (binding['science_config']['maximum_http_attempts']!=512
                                or proof['response_proof']['wire_requests']>512):
                            raise ValueError('search HTTP budget binding/physical count differs')
                runs[run][arm]=result
            cal=root/'search'/run
            loads.append(loaded(cal/'calibration-load.json',cal/'calibration-context.json',provider=plan['designer'],
                purpose='before-design-study-calibration:'+run,role='designer'))
            certificate=read(cal/'preflight/certificate.json')
            if certificate['plan']['backend']!=plan['backend']:raise ValueError('calibration backend differs')
            view={'source_commit':source,'designer_provider_binding':plan['designer'],
                'readiness_scope':driver.EXECUTION_SCOPE,'conversation_profile':plan['designer_settings']['conversation_profile'],
                'budget':{'maximum_calibration_POSTs':40}}
            certificates[run]=_certificate_proof(cal,view,{'started':{'started_utc':first}})
            for p in cal.glob('arms/*/authoring/generation-*/step-*.started.json'):
                when=datetime.fromisoformat(read(p)['started_utc']).timestamp()
                if not 0<=when-certificate['completed_epoch']<=certificate['maximum_age_seconds']:
                    raise ValueError('actual designer dispatch has stale/future calibration')
        references={name:observation_proof(root/'references'/name,plan,identity='reference-'+name,
            system=system,seed=42,years=2,role='developer-reference') for name,system in plan['reference_systems'].items()}
        selection=read(root/'selection.json')
        def readonly(base,plan,run,arm):
            return replay_campaign(Path(base)/'search'/run/'arms'/arm.replace(':','--')/'campaign','blackbox')
        if selection!=driver.selection_payload(root,plan,frozen_utc=selection['frozen_utc'],campaign_loader=readonly):
            raise ValueError('frozen selection differs from all candidates and exact ties')
        jobs=driver.evaluation_jobs(plan,selection)
        if read(root/'evaluation-plan.json')!={'schema':spec.SCHEMA+'.evaluation-plan',
                'selection_sha256':selection['content_sha256'],'jobs':jobs}:
            raise ValueError('evaluation jobs differ from immutable selection/seed projection')
        evaluated={}
        for job in jobs:
            directory=root/'evaluation'/job['job_id']
            if datetime.fromisoformat(read(directory/'started.json')['started_utc'])<datetime.fromisoformat(selection['frozen_utc']):
                raise ValueError('evaluation began before candidate selection was frozen')
            evaluated[job['job_id']]=observation_proof(directory,plan,identity=job['job_id'],system=job['system'],
                seed=job['seed'],years=job['years'],role='selection-fixed-evaluation')
        for result in [*references.values(),*evaluated.values()]:
            cell=Path(result['loaded']['load']).parent
            physical_dirs.add(cell.resolve())
            loads.append(result['loaded'])
            cache=cell/'replies/responses.sqlite'
            if cache.exists():
                if cache.resolve() in caches:raise ValueError('reference/evaluation reused a physical cache')
                caches.add(cache.resolve())
        if caches!={p.resolve() for p in root.rglob('responses.sqlite')}:
            raise ValueError('unaccounted physical scientist response cache')
        if journals!={p.resolve() for p in root.rglob('generation-*') if p.is_dir()}:
            raise ValueError('unaccounted model-authored generation journal')
        if physical_dirs!={p.resolve() for p in root.glob('**/worlds/*')}:
            raise ValueError('unaccounted physical world directory')
        if {p.name for p in (root/'evaluation').iterdir()}!={j['job_id'] for j in jobs}:
            raise ValueError('undeclared or missing evaluation job directory')
        if {p.name for p in (root/'references').iterdir()}!=set(plan['reference_systems']):
            raise ValueError('undeclared or missing reference directory')
        expected_loads={Path(row['load']).with_suffix('.started.json').resolve() for row in loads}
        actual_loads={p.resolve() for p in root.rglob('*.started.json') if
            p.name.startswith(('role-load-','designer-load-','calibration-load.'))}
        if actual_loads!=expected_loads:raise ValueError('unaccounted role-load dispatch')
        progress_rows=[]
        for run,bindings in plan['campaign_bindings'].items():
            for arm in bindings:
                for g,r in enumerate(runs[run][arm]['records']):
                    o=r['observations'][0] if r['observations'] else None
                    progress_rows.append({'run':run,'arm':arm,'generation':g,
                        'status':'generation-failure' if r['generation_error'] else o['status'] if o else 'unknown',
                        'loss':o['loss'] if o else None})
        progress={'schema':spec.SCHEMA+'.progress','plan_sha256':plan['content_sha256'],
            'stage':'closed','active':None,'consumed_search_slots':120,'rows':progress_rows,
            'consumed_reference_slots':9,'consumed_evaluation_slots':len(jobs)}
        progress['content_sha256']=digest(progress)
        if read(root/'progress.json')!=progress:raise ValueError('terminal progress differs from all original slots')
        result={'schema':spec.SCHEMA+'.audit','source_commit':source,'plan_sha256':plan['content_sha256'],
            'source_proofs':closure,'input_inventory':before,'runs':runs,'references':references,
            'selection':selection,'evaluation_jobs':jobs,'evaluated':evaluated,
            'certificates':certificates,'designer_loads':loads,'writer':{'started':start,'ended':end},
            'new_model_calls':0,'new_code_executions':0,'raw_inventory_unchanged':True}
        result['content_sha256']=digest(result)
        return result
    finally:
        if _inventory(root)!=before:raise ValueError('study raw evidence changed during read-only audit')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--expected-source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    if a.output.exists() or a.output.resolve().is_relative_to(a.run.resolve()):p.error('fresh output outside raw root required')
    result=analyze(a.run,a.expected_source);write_json_atomic(a.output,result,sort_keys=True,allow_nan=False)
    print({'schema':result['schema'],'content_sha256':result['content_sha256']});return 0


if __name__=='__main__':raise SystemExit(main())
