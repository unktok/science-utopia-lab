"""Cold physical/critic audit of frozen T/U policies on unused world seeds."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root,output,*,study='count-content-v1'):
    priority_fixed = study == 'priority-fixed-v1'
    workflow = study in ('workflow-v1', 'longitudinal-v1', 'priority-fixed-v1')
    topic_pilot = study == 'legacy-topic-v1'
    terminal_pilot = study == 'terminal-cost-v1'
    resource_pilot = topic_pilot or terminal_pilot or priority_fixed
    pilot = study in ('legacy-choice-v1', 'legacy-topic-v1', 'terminal-cost-v1')
    if study=='count-content-v1':
        from scripts import run_native_objective_fixed_evaluation_v1 as driver
        audit_schema='scienceutopia.native-objective-fixed-evaluation-audit.v1'
        source_scripts=['scripts/run_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif study=='planning-v1':
        from scripts import run_native_planning_fixed_evaluation_v1 as driver
        audit_schema='scienceutopia.native-planning-fixed-evaluation-audit.v1'
        source_scripts=['scripts/run_native_planning_fixed_evaluation_v1.py',
            'scripts/run_native_objective_fixed_evaluation_v1.py',
            'scripts/audit_native_planning_fixed_evaluation_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif study=='joint-v1':
        from scripts import run_native_joint_fixed_evaluation_v1 as driver
        audit_schema='scienceutopia.native-joint-fixed-evaluation-audit.v1'
        source_scripts=['scripts/run_native_joint_fixed_evaluation_v1.py',
            'scripts/audit_native_joint_fixed_evaluation_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif study=='workflow-v1':
        from scripts import run_native_workflow_fixed_evaluation_v1 as driver
        audit_schema='scienceutopia.native-workflow-fixed-evaluation-audit.v1'
        source_scripts=['scripts/run_native_workflow_fixed_evaluation_v1.py',
            'scripts/run_native_objective_fixed_evaluation_v1.py',
            'scripts/run_native_workflow_objective_loop_v1.py',
            'scripts/run_native_objective_instrument_loop_v1.py',
            'scripts/audit_native_workflow_fixed_evaluation_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif study=='longitudinal-v1':
        from scripts import run_native_longitudinal_fixed_evaluation_v1 as driver
        audit_schema='scienceutopia.native-longitudinal-fixed-evaluation-audit.v1'
        source_scripts=['scripts/run_native_longitudinal_fixed_evaluation_v1.py',
            'scripts/audit_native_longitudinal_fixed_evaluation_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif priority_fixed:
        from scripts import run_native_priority_fixed_evaluation_v1 as driver
        audit_schema='scienceutopia.native-priority-fixed-evaluation.v1.audit'
        source_scripts=['scripts/run_native_priority_fixed_evaluation_v1.py',
            'scripts/native_priority_fixed_bank_v1.py', 'scripts/native_benchmark_seed_usage.py',
            'scripts/reports/native_priority_method_readout_v1.py',
            'scripts/run_native_objective_fixed_evaluation_v1.py',
            'scripts/run_native_topic_free_optimization_v1.py',
            'scripts/run_native_workflow_objective_loop_v1.py',
            'scripts/run_native_objective_instrument_loop_v1.py',
            'scripts/run_native_legacy_topic_pilot_v1.py',
            'scripts/audit_native_priority_fixed_evaluation_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif terminal_pilot:
        from scripts import run_native_terminal_cost_pilot_v1 as driver
        audit_schema='scienceutopia.native-terminal-cost-pilot-audit.v1'
        source_scripts=['scripts/run_native_terminal_cost_pilot_v1.py',
            'scripts/run_native_legacy_topic_pilot_v1.py',
            'scripts/run_native_legacy_choice_pilot_v1.py',
            'scripts/audit_native_terminal_cost_pilot_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif topic_pilot:
        from scripts import run_native_legacy_topic_pilot_v1 as driver
        audit_schema='scienceutopia.native-legacy-topic-pilot-audit.v1'
        source_scripts=['scripts/run_native_legacy_topic_pilot_v1.py',
            'scripts/run_native_legacy_choice_pilot_v1.py',
            'scripts/audit_native_legacy_topic_pilot_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    elif pilot:
        from scripts import run_native_legacy_choice_pilot_v1 as driver
        audit_schema='scienceutopia.native-legacy-choice-pilot-audit.v1'
        source_scripts=['scripts/run_native_legacy_choice_pilot_v1.py',
            'scripts/audit_native_legacy_choice_pilot_v1.py',
            'scripts/audit_native_objective_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
    else:raise ValueError('explicit known fixed-evaluation study or legacy-choice pilot required')
    group = 'controls' if pilot else 'evaluation'
    role = driver.ROLE if pilot else 'selection-fixed-evaluation'
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_observer_physical_v1 import ColdObserver,accepted_request_keys,reconstruct_measurement
    from scripts.audit_native_institution_loop_v1 import epoch
    from utopia.optimization.blackbox import Suggestion,Observation
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    root,output=Path(root).resolve(),Path(output).resolve();read=driver.read
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh audit outside scientific source/raw required')
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);before=_inventory(root);p=driver.require_plan(root)
        start,end=read(root/'started.json'),read(root/'terminal.json')
        if (start['schema']!=driver.SCHEMA+'.start' or end['schema']!=driver.SCHEMA+'.terminal'
                or start['plan_sha256']!=p['content_sha256'] or end['status']!='closed'
                or end['completed_jobs']!=len(p['jobs']) or epoch(end['ended_utc'])<epoch(start['started_utc'])):
            raise ValueError('normal fixed-evaluation closure required')
        for i in range(0 if pilot else len(p['evaluation']['seed_usage'])):
            prepared=read(root/f'seed-usage-{i:02d}.json');dispatched=read(root/f'pre-dispatch-seed-usage-{i:02d}.json')
            if (prepared['content_sha256']!=p['evaluation']['seed_usage'][i]
                    or not dispatched['valid'] or dispatched['errors'] or dispatched['prior_matching_runs']
                    or dispatched['root']!=prepared['root'] or dispatched['seeds']!=p['evaluation']['seeds']
                    or not epoch(prepared['checked_utc'])<=epoch(dispatched['checked_utc'])<=epoch(start['started_utc'])):
                raise ValueError('literal pre-dispatch unused-seed proof differs')
            if priority_fixed and (dispatched.get('schema') != 'scienceutopia.native-benchmark-seed-usage.v4'
                    or dispatched.get('strict_path_coverage') is not True
                    or dispatched.get('excluded_software_verification_paths')):
                raise ValueError('strict all-path pre-dispatch inventory required')
            if workflow and 'seed_software_exclusions' in p:
                from scripts.native_benchmark_seed_usage import require_inventory_policy
                for receipt in (prepared, dispatched):
                    require_inventory_policy(receipt, p['seed_software_exclusions'])
        resources=[p['protocol']]
        if workflow and 'seed_software_exclusions' in p:
            source_scripts.append('scripts/native_benchmark_seed_usage.py')
            if not priority_fixed: resources.append(p['seed_inventory_protocol']['path'])
        if (workflow or pilot) and 'operational_protocol' in p:
            resources.append(p['operational_protocol']['path'])
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=source_scripts,resources=resources)
        observer=ColdObserver(root/'observer',p['observer_contract']);observer_audit=observer.audit()
        if observer_audit!=read(root/'observer-audit.json'):raise ValueError('literal observer audit differs')
        cells=set();caches=set();keys=set();worlds=[]
        for job in p['jobs']:
            directory=root/group/job['identity'];dispatched=read(directory/'started.json')
            suggestion=Suggestion(job['identity'],job['system'],0,role)
            actual_job = dispatched['job'] if pilot else dispatched
            if (any(actual_job[k]!=v for k,v in job.items()) or dispatched['suggestion']!=suggestion.to_dict()
                    or not epoch(start['started_utc'])<=epoch(dispatched['started_utc'])<=epoch(end['ended_utc'])):
                raise ValueError('literal frozen evaluation dispatch differs')
            spec=SystemSpec.from_dict(job['system']);o=read(directory/'observation.json');m=o['metadata']
            if (o['suggestion_id']!=job['identity'] or o['candidate']!=job['system']
                    or m['system_fingerprint']!=spec.fingerprint
                    or m['loss_spec_sha256']!=loss_spec_sha256(p['losses']['throughput'])):
                raise ValueError('fixed native observation identity/loss differs')
            cell=directory/'worlds'/(job['identity']+'-s'+str(job['seed']));cells.add(cell)
            if workflow or pilot:
                from utopia.optimization.native_scientist_transport_v1 import require_cell_transport
                require_cell_transport(cell,p,spec,seed=job['seed'],failed=o['status']=='failed')
            cache=cell/'replies/responses.sqlite'
            if cache.exists():caches.add(cache)
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist',allow_unconfirmed=o['status']=='failed')
            runs,measurements=m['runs'],m['measurements']
            if len(runs)>1 or len(measurements)>1 or (measurements and not runs):raise ValueError('ambiguous fixed native observation')
            if runs:
                proof=physical_proof(cell,spec,world=p['world'],seed=job['seed'],years=4,evidence=runs[0])
                state=read_portable_checkpoint(runs[0]['checkpoint_path']);keys.update(accepted_request_keys(state,p['observer_contract']))
                if measurements:
                    rebuilt=reconstruct_measurement(state,proof['measurement'],observer)
                    if resource_pilot:
                        rebuilt=driver.additional_from_checkpoints(rebuilt,cell)
                    if workflow or pilot:
                        rebuilt={**rebuilt,'native_workflow_interval':driver.interval(
                            p,spec,state['native_system']['events'],job['seed'])}
                    if measurements!=[rebuilt] or m['technical_failures']:raise ValueError('literal additional measurement differs')
                    verify_native_observation(Observation.from_dict(o),p['world'],[job['seed']])
                elif o['status']!='failed' or not m['technical_failures']:raise ValueError('missing observer measurement without failure')
            else:
                if o['status']!='failed' or not m['technical_failures']:raise ValueError('unobserved job cannot acquire a loss')
                if cache.exists() and not gate['confirmed']:raise ValueError('responses follow unconfirmed role load')
                proof=physical_proof(cell,spec,world=p['world'],seed=job['seed'],years=4) if cache.exists() else {'status':'pre-response-journal-failure'}
            scores={k:evaluate_loss(v,measurements) for k,v in p['losses'].items()}
            if (o['loss']!=scores['throughput']['loss'] or m['loss_evaluation']!=scores['throughput']
                    or (o['status']=='complete')!=(scores['throughput']['status']=='complete')
                    or read(directory/'cross-scores.json')!={**scores,'content_sha256':digest(scores)}):
                raise ValueError('literal cross-score/status differs')
            worlds.append({**job,'role':role,'status':o['status'],
                'scores':{k:v['loss'] for k,v in scores.items()},'measurements':measurements,
                'physical_proof':proof,'loaded':gate})
        if (cells!={v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or caches!={v.resolve() for v in root.rglob('responses.sqlite')}
                or {v.name for v in (root/group).iterdir()}!={j['identity'] for j in p['jobs']}
                or not {r['key'] for r in observer_audit['rows']}<=keys
                or list(root.rglob('dispatch-*.intent.json'))):raise ValueError('unaccounted fixed world/critic/designer dispatch')
        progress=json.loads((root/'progress.json').read_text())
        if progress['stage']!='closed' or progress['active'] is not None:raise ValueError('fixed evaluation final progress differs')
        if before!=_inventory(root):raise ValueError('raw evaluation changed during cold proof')
        result={'schema':audit_schema,'source_commit':p['source_commit'],
            'plan_sha256':p['content_sha256'],'source_proof':source,'closure':{'started':start,'terminal':end},
            'origin_audit_content_sha256':p['origin_audit_content_sha256'],
            'worlds':worlds,'observer':observer_audit,'raw_inventory_sha256':digest(before),'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)),'new_model_calls':0,'new_code_executions':0,
            'held_out_world_seeds':not pilot,'independent_optimizer_replications':False,'publication_ready':False}
        if pilot:
            result.update(development_seed_reused=True, policy_selection=False, automatic_invention=False)
            if (len(worlds) != (2 if resource_pilot else 3) or any(w['status'] != 'complete' for w in worlds)
                    or len({digest(w['physical_proof']['initial_identity']) for w in worlds}) != 1
                    or end['held_out_world_seeds'] or end['policy_selection'] or end['automatic_invention']):
                raise ValueError('all declared same-initial-society controls without selection required')
        else:
            result['fixed_selection']=p['fixed_selection']
        result['content_sha256']=digest(result);write_json_atomic(output,result,sort_keys=True,allow_nan=False)
        print(json.dumps({'audit':str(output),'worlds':len(worlds),'content_sha256':result['content_sha256']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:worker(a.run,a.output);return
    if json.loads((a.run/'terminal.json').read_text())['status']!='closed':raise ValueError('normal fixed evaluation closure required')
    result=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(Path(__file__).resolve()),'--worker','--run',str(a.run.resolve()),
        '--frozen-source',str(a.frozen_source.resolve()),'--output',str(a.output.resolve())],cwd=a.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
