"""Closed O/E audit using unchanged original-source libraries, without dispatch.

This adapter can be developed after a study is pinned. It imports only standard
libraries in its parent, then starts a fresh interpreter with the explicitly
selected frozen source first on sys.path. No generated code is executed.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def stage_receipt(root, stage, plan_sha):
    start=json.loads((root/(stage+'.started.json')).read_text())
    end=json.loads((root/(stage+'.ended.json')).read_text())
    if (start.get('stage')!=stage or start.get('plan_sha256')!=plan_sha
            or end!={**start,'status':'closed','ended_utc':end.get('ended_utc')}
            or datetime.fromisoformat(end['ended_utc'])<datetime.fromisoformat(start['started_utc'])):
        raise ValueError('normal exact-stage closure required: '+stage)
    return {'started':start,'ended':end}


def actual_policy_order(plan, selection, jobs):
    """Every evaluation label/seed is checked, including explicitly shared jobs."""
    from scripts.native_design_benchmark_plan import policy_identity
    expected={**{'reference:'+k:plan['reference_systems'][k]
        for k in plan['evaluation']['reference_labels']},
        **{'selected:'+k:v['system'] for k,v in selection['selected'].items()}}
    pairs={}
    for job in jobs:
        if job['seed'] not in plan['evaluation']['seeds'] or policy_identity(job['system'])!=job['policy_sha256']:
            raise ValueError('evaluation policy/seed differs')
        for label in job['labels']:
            if label not in expected or expected[label] is None or policy_identity(expected[label])!=job['policy_sha256']:
                raise ValueError('evaluation sharing changes label provenance')
            key=(label,job['seed'])
            if key in pairs:raise ValueError('duplicated logical evaluation label/seed')
            pairs[key]=job['identity']
    wanted={(label,seed) for label,system in expected.items() if system is not None
        for seed in plan['evaluation']['seeds']}
    if set(pairs)!=wanted:raise ValueError('missing logical evaluation label/seed')
    return [{'label':label,'seed':seed,'physical_job':pairs[(label,seed)]} for label,seed in sorted(pairs)]


def worker(root,output):
    from scripts import run_pre_scale_search_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from scripts.analyze_native_design_benchmark import loaded
    from utopia.optimization.native_numeric_designer import checked,replay_numeric
    from utopia.optimization.native_bounded_staged_designer import replay as replay_editor
    from utopia.optimization.native_designer_preflight import require_certificate,EXECUTION_SCOPE
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.native_design_space import random_parameter_definition
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.blackbox import Observation
    from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest,clone
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    root=Path(root).resolve();output=Path(output).resolve();source=Path.cwd()
    if output.exists() or output.is_relative_to(source) or output.is_relative_to(root):
        raise ValueError('fresh external audit destination required')
    read=lambda path:checked(json.loads(Path(path).read_text()))
    before=_inventory(root);plan=driver.require_plan(root);closure=read(root/'complete.json')
    if pinned_revision(source)!=plan['source_commit']:raise ValueError('exact clean original source required')
    stages={k:stage_receipt(root,k,plan['content_sha256']) for k in ('readiness','search','evaluation')}
    for earlier,later in zip(('readiness','search'),('search','evaluation')):
        if datetime.fromisoformat(stages[later]['started']['started_utc'])<datetime.fromisoformat(stages[earlier]['ended']['ended_utc']):
            raise ValueError('scientific stages overlap or precede readiness')
    sources=source_proofs(source,plan['source_commit'],scripts=[
        'scripts/run_pre_scale_search_v1.py','scripts/native_benchmark_physical.py',
        'scripts/analyze_native_design_benchmark.py'],resources=[plan['protocol']])
    usages=[read(p) for p in sorted(root.glob('evaluation-seed-usage-*.json'))]
    if (not usages or [u['content_sha256'] for u in usages]!=plan['evaluation']['seed_usage']
            or any(not u['valid'] or u['errors'] or u['prior_matching_runs']
                or u['seeds']!=plan['evaluation']['seeds'] for u in usages)):
        raise ValueError('prospective evaluation seed inventory differs')
    rebuilt=driver.build_plan(source=plan['source_commit'],scientist=plan['scientist'],
        designer=plan['designer'],backend=plan['backend'],data_cache=plan['data_cache'],seed_usage=usages)
    if rebuilt!={k:v for k,v in plan.items() if k!='content_sha256'}:
        raise ValueError('frozen plan differs from original driver reconstruction')
    controllers={};authoring=[];worlds=[];expected_caches=set();expected_cells=set();expected_authors=set()
    def controller(base,unused_plan,run,arm):
        if arm not in controllers:
            b=plan['campaign_bindings'][run][arm]
            c=replay_campaign(root/'search'/run/arm.replace(':','--')/'campaign','blackbox')
            expected={**clone(b),'mode':'blackbox','learning_rate':.1,'strategy_learning_rate':.1,
                'strategy_baseline':0.,'exploration':.1,'proposal_feedback':'matched-loss'}
            if c.binding!=expected or c.state['pending'] is not None or len(c.state['records'])!=2:
                raise ValueError('campaign binding/terminal budget differs')
            controllers[arm]=c
        return controllers[arm]
    numeric_cert=read(root/'numeric-readiness/certificate.json')
    if (not numeric_cert['passed'] or numeric_cert['unattempted_cases']
            or numeric_cert['runtime']!=plan['runtime'] or numeric_cert['provider']!=plan['designer']
            or numeric_cert['backend']!=plan['backend'] or len(numeric_cert['cases'])!=2
            or [v['objective'] for v in numeric_cert['cases']]!=plan['objectives']):
        raise ValueError('numeric readiness not complete or differs from planned runtime/provider')
    for case in numeric_cert['cases']:
        directory=root/case['journal_relative'];r=replay_numeric(directory)
        b=read(directory/'binding.json')
        c=controller(root,plan,'run-00',case['objective']+':parameters')
        if (not case['submitted'] or r['definition'] is None or b['request']!=c._request([],c._strategy_initial(),1)
                or file_sha256(directory/'result.json')!=case['result_sha256']):
            raise ValueError('numerical readiness is not actual production request cold replay')
        expected_authors.add(directory.resolve())
    editor_cert=read(root/'editor-readiness/calibration/certificate.json')
    replay_editor(root/'editor-readiness')
    class MetadataResponse:
        def __init__(self,data):self.data=data
        def raise_for_status(self):pass
        def json(self):return self.data
    class RecordedBackend:
        def get(self,url,timeout):
            if url.endswith('/api/version'):return MetadataResponse({'version':plan['backend']['ollama_version']})
            if url.endswith('/api/tags'):return MetadataResponse({'models':[{'name':plan['designer']['model'],
                'digest':plan['designer']['model_digest']}]})
            raise ValueError('read-only historical metadata adapter cannot dispatch')
    cert_proof=require_certificate(root/'editor-readiness/calibration/certificate.json',plan['designer'],
        protocol='staged-v15',session=RecordedBackend(),now=editor_cert['completed_epoch'],
        scope=EXECUTION_SCOPE,conversation_profile=BOUNDED_AUTHORING)
    if editor_cert['plan']['backend']!=plan['backend']:raise ValueError('editor readiness backend differs')

    def physical(directory,identity,system,seed,role,observation=None,loss_name='throughput'):
        spec=SystemSpec.from_dict(system);standalone=observation is None
        o=read(directory/'observation.json') if standalone else observation
        if standalone:
            started=read(directory/'started.json')
            if (started['identity'],started['system'],started['seed'],started['role'])!=(identity,system,seed,role):
                raise ValueError('world dispatch differs from fixed job')
            if role=='selection-fixed-evaluation' and datetime.fromisoformat(started['started_utc'])<datetime.fromisoformat(selection['frozen_utc']):
                raise ValueError('evaluation precedes fixed selection')
        if (o['suggestion_id']!=identity or o['candidate']!=system
                or o['metadata']['loss_spec_sha256']!=loss_spec_sha256(plan['losses'][loss_name])):
            raise ValueError('native observation identity/policy/loss differs')
        cell=directory/'worlds'/(identity+'-s'+str(seed));expected_cells.add(cell.resolve())
        if not cell.is_dir():raise ValueError('missing declared physical world')
        cache=cell/'replies/responses.sqlite'
        if cache.exists():
            if cache.resolve() in expected_caches:raise ValueError('physical scientist cache reused')
            expected_caches.add(cache.resolve())
        gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=plan['scientist'],
            purpose='before-native-world:'+cell.name,role='scientist',allow_unconfirmed=o['status']=='failed')
        if o['status']=='complete':
            verify_native_observation(Observation.from_dict(o),plan['world'],[seed])
            if len(o['metadata']['runs'])!=1 or o['metadata']['technical_failures']:
                raise ValueError('complete world has missing/failed evidence')
            proof=physical_proof(cell,spec,world=plan['world'],seed=seed,years=4,evidence=o['metadata']['runs'][0])
            if o['metadata']['measurements']!=[proof['measurement']]:raise ValueError('checkpoint measurement differs')
        elif o['status']=='failed' and o['loss'] is None and not o['metadata']['measurements']:
            if cache.exists() and not gate['confirmed']:raise ValueError('physical requests lack confirmed role load')
            proof=physical_proof(cell,spec,world=plan['world'],seed=seed,years=4) if cache.exists() else {'status':'pre-response-journal-failure'}
        else:raise ValueError('invalid terminal world/null semantics')
        if 'context_input_proof' in proof:proof['legacy_literal_context_probe']=proof.pop('context_input_proof')
        scores={k:evaluate_loss(v,o['metadata']['measurements']) for k,v in plan['losses'].items()}
        if o['loss']!=scores[loss_name]['loss']:raise ValueError('loss differs from raw components')
        if standalone:
            recorded=read(directory/'cross-scores.json');recorded.pop('content_sha256')
            if recorded!=scores:raise ValueError('recorded cross-scores differ')
        row={'identity':identity,'role':role,'seed':seed,'system':system,'status':o['status'],
            'scores':{k:v['loss'] for k,v in scores.items()},'physical_proof':proof,'loaded':gate}
        worlds.append(row);return row

    for name in plan['reference_order']:
        physical(root/'references'/name,'reference-'+name,plan['reference_systems'][name],driver.SEED,'developer-reference')
    for slot in plan['schedule']:
        arm,g=slot['arm'],slot['generation'];c=controller(root,plan,'run-00',arm);r=c.state['records'][g]
        directory=root/'search/run-00'/arm.replace(':','--');method=plan['assignments'][arm]['method']
        generation=directory/'authoring'/('generation-'+r['request_sha256'])
        if method=='random':
            if random_parameter_definition(r['request'])!=r['definition']:raise ValueError('uniform draw differs')
        elif method=='parameters':
            expected_authors.add(generation.resolve());a=replay_numeric(generation)
            binding=read(generation/'binding.json')
            if binding['request']!=r['request'] or binding['provider']!=plan['designer'] or binding['backend']!=plan['backend']:
                raise ValueError('numeric consumed request/provider differs')
            if a['definition']!=r['definition']:raise ValueError('consumed numerical definition differs from raw')
            for intent in generation.glob('call-*.intent.json'):
                age=datetime.fromisoformat(read(intent)['started_utc']).timestamp()-numeric_cert['created_unix_seconds']
                if not 0<=age<=86400:raise ValueError('numeric dispatch readiness was stale or future')
        else:
            expected_authors.add(generation.resolve());a=replay_editor(generation)
            intent=read(generation/'intent.json')
            if intent['request']!=r['request'] or intent['provider']!=plan['designer'] or a!=r['definition']:
                raise ValueError('consumed staged definition differs from exact raw request')
            for dispatch in (generation/'wire').glob('dispatch-*.intent.json'):
                age=datetime.fromisoformat(read(dispatch)['started_utc']).timestamp()-editor_cert['completed_epoch']
                if not 0<=age<=86400:raise ValueError('staged dispatch readiness was stale or future')
        authoring.append({'arm':arm,'generation':g,'request_sha256':r['request_sha256'],
            'generation_error':r['generation_error'],'definition':r['definition'],
            'raw_directory':str(generation) if method!='random' else None})
        for draw,o in zip(r['draws'],r['observations']):
            if o is not None:physical(directory,draw['suggestion']['suggestion_id'],o['candidate'],driver.SEED,
                'search:'+arm,observation=o,loss_name=plan['assignments'][arm]['objective'])
    selection=read(root/'selection.json')
    rebuilt_selection=driver.selection_payload(root,plan,frozen_utc=selection['frozen_utc'],campaign_loader=controller)
    if selection!=rebuilt_selection:raise ValueError('selection differs from all exact original slots/ties/order')
    jobs=driver.evaluation_jobs(plan,selection);evaluation_plan=read(root/'evaluation-plan.json')
    if evaluation_plan!={**{'schema':driver.SCHEMA+'.evaluation-plan','selection_sha256':selection['content_sha256'],
            'jobs':jobs},'content_sha256':digest({'schema':driver.SCHEMA+'.evaluation-plan',
                'selection_sha256':selection['content_sha256'],'jobs':jobs})}:
        raise ValueError('evaluation job manifest differs')
    logical=actual_policy_order(plan,selection,jobs)
    for job in jobs:physical(root/'evaluation'/job['identity'],job['identity'],job['system'],job['seed'],'selection-fixed-evaluation')
    if (closure['plan_sha256']!=plan['content_sha256'] or closure['selection_sha256']!=selection['content_sha256']
            or closure['evaluation_physical_worlds']!=len(jobs)):
        raise ValueError('closure differs from actual fixed-selection jobs')
    if expected_cells!={p.resolve() for p in root.glob('**/worlds/*') if p.is_dir()}:
        raise ValueError('unaccounted physical worlds')
    if expected_caches!={p.resolve() for p in root.rglob('responses.sqlite')}:
        raise ValueError('unaccounted physical response cache')
    actual_authors={p.resolve() for p in (root/'numeric-readiness').glob('*/generation-*')}
    actual_authors.update(p.resolve() for p in (root/'search').glob('run-00/*/authoring/generation-*'))
    if expected_authors!=actual_authors:raise ValueError('unaccounted authoring journal')
    if {p.name for p in (root/'references').iterdir()}!=set(plan['reference_order']):
        raise ValueError('unaccounted reference slots')
    if {p.name for p in (root/'evaluation').iterdir()}!={j['identity'] for j in jobs}:
        raise ValueError('unaccounted evaluation slots')
    terminal=json.loads((root/'progress.json').read_text())
    expected_rows=[]
    for arm in plan['arm_order']:
        for g,r in enumerate(controllers[arm].state['records']):
            o=r['observations'][0] if r['observations'] else None
            expected_rows.append({'arm':arm,'generation':g,
                'status':'generation-failure' if r['generation_error'] else o['status'] if o else 'unknown',
                'loss':o['loss'] if o else None})
    if terminal!={'schema':driver.SCHEMA+'.progress','stage':'closed','active':None,
            'search_slots':expected_rows,'reference_observations':6,'evaluation_observations':len(jobs)}:
        raise ValueError('terminal progress differs from original slots')
    if before!=_inventory(root):raise ValueError('raw study changed during read-only audit')
    result={'schema':'scienceutopia.pre-scale-search-audit.v1','source_commit':plan['source_commit'],
        'plan_sha256':plan['content_sha256'],'source_proof':sources,'stages':stages,'worlds':worlds,
        'authoring':authoring,'selection':selection,'logical_evaluation':logical,
        'editor_readiness':cert_proof,'raw_inventory_sha256':digest(before),'raw_files':len(before),
        'analysis_adapter_sha256':file_sha256(Path(__file__)),
        'new_model_calls':0,'new_code_executions':0,
        'historical_backend_metadata_scope':'Source-owned saved provider/backend reconstructed for offline cold control replay, not a fresh backend observation',
        'analysis_scope':'New adapter; all native imports and driver reconstruction from the unchanged original clean source'}
    result['content_sha256']=digest(result)
    write_json_atomic(output,result,sort_keys=True,allow_nan=False)
    print(json.dumps({'audit':str(output),'content_sha256':result['content_sha256'],'physical_worlds':len(worlds)}))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--frozen-source',type=Path)
    p.add_argument('--worker',action='store_true');args=p.parse_args()
    if args.worker:worker(args.run,args.output);return
    if args.frozen_source is None or not (args.run/'complete.json').exists():
        raise ValueError('closed study and explicit original frozen source required; never audit a live writer')
    script=Path(__file__).resolve();before=hashlib.sha256(script.read_bytes()).hexdigest()
    command=[sys.executable,'-c','import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()),str(script),'--worker','--run',str(args.run.resolve()),'--output',str(args.output.resolve())]
    result=subprocess.run(command,cwd=args.frozen_source.resolve(),env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if hashlib.sha256(script.read_bytes()).hexdigest()!=before:raise ValueError('analysis adapter changed during audit')
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
