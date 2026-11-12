"""Read-only original-source closure of every capacity T/P proposal and world."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = 'scienceutopia.native-capacity-objective-loop-audit.v1'


def worker(root, output):
    from scripts import run_native_capacity_objective_loop_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    from scripts.audit_native_institution_loop_v1 import request_at, require_age, epoch
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from utopia.optimization.blackbox import Observation, Suggestion
    from utopia.optimization.native_active_founders import measure_from_checkpoints
    from utopia.optimization.native_bounded_staged_designer import replay
    from utopia.optimization.native_development_references import build_context
    from utopia.optimization.native_designer_preflight import require_certificate, EXECUTION_SCOPE
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.loss import evaluate_loss
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256
    root,output = Path(root).resolve(),Path(output).resolve(); read=driver.read
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh external cold audit required')
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=_inventory(root); p=driver.require_plan(root); start=read(root/'started.json'); end=read(root/'terminal.json')
        if (start['schema']!=driver.SCHEMA+'.start' or end['schema']!=driver.SCHEMA+'.terminal'
                or start['plan_sha256']!=p['content_sha256'] or end['status']!='closed' or end['complete_references']!=5
                or epoch(end['ended_utc'])<epoch(start['started_utc']) or (root/'observer').exists() or (root/'evaluation').exists()):
            raise ValueError('normal exact capacity pilot closure, no critic or unplanned evaluation required')
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=[
            'scripts/run_native_capacity_objective_loop_v1.py','scripts/audit_native_capacity_objective_loop_v1.py',
            'scripts/native_benchmark_physical.py'],resources=[driver.PROTOCOL,driver.BANK_MANIFEST,driver.P_LOSS])
        class Reply:
            def __init__(self,data):self.data=data
            def raise_for_status(self):pass
            def json(self):return self.data
        class Backend:
            def get(self,url,timeout):
                if url.endswith('/api/version'):return Reply({'version':p['backend']['ollama_version']})
                if url.endswith('/api/tags'):return Reply({'models':[{'name':p['designer']['model'],'digest':p['designer']['model_digest']}]})
                raise ValueError('cold backend adapter cannot dispatch')
        calibration_wires=set()
        def calibration(base, request, not_before):
            replay(base); cert=read(base/'calibration/certificate.json')
            cp=require_certificate(base/'calibration/certificate.json',p['designer'],protocol='staged-v15',session=Backend(),
                now=cert['completed_epoch'],scope=EXECUTION_SCOPE,conversation_profile=BOUNDED_AUTHORING)
            if (cert['plan']['request']!=request or cert['plan']['backend']!=p['backend']
                    or cert['plan']['runtime']!=p['runtime'] or cp['post_edit_component_contract']!=p['post_edit_contract']
                    or cert['plan']['created_epoch']<not_before):
                raise ValueError('fresh exact source/history/backend/fixture readiness required')
            calibration_wires.add(base/'wire');return cert,cp
        def binding(objective, context=None):
            value={'initial_system':p['initial_system'],'loss_spec':p['losses'][objective],
                'world':p['world'],'seeds':[driver.SEED],'strategies':p['strategies'],'mode':'blackbox',
                'seed':p['optimizer_seed'],'learning_rate':.1,'strategy_learning_rate':.1,
                'strategy_baseline':0.,'exploration':.1,'design_space':p['design_space']}
            if context is not None:value['development_references']=context
            return value
        prototype=replay_campaign(root/'initial-readiness/campaign','blackbox')
        if prototype.binding!=binding('throughput') or prototype.state['records'] or prototype.state['pending'] is not None:
            raise ValueError('empty prototype controller, not imported scientific history, required')
        initial_cert,initial_cp=calibration(root/'initial-readiness/editor-readiness',request_at(prototype,0),epoch(start['started_utc']))
        worlds=[];pairs=[];expected_cells=set();expected_caches=set();expected_authors=set()
        def physical(directory,identity,system,role,observation=None,objective='throughput'):
            spec=SystemSpec.from_dict(system);standalone=observation is None
            if standalone:
                o=read(directory/'observation.json');o={k:v for k,v in o.items() if k!='content_sha256'}
                dispatched=read(directory/'started.json');s=Suggestion.from_dict(dispatched['suggestion'])
                if (s.suggestion_id!=identity or s.candidate!=system or s.phase!='developer-reference'
                        or dispatched['seed']!=driver.SEED or epoch(dispatched['started_utc'])<initial_cert['completed_epoch']):
                    raise ValueError('reference dispatch predates fresh initial readiness or differs')
            else:o=observation
            cell=directory/'worlds'/(identity+'-s'+str(driver.SEED));expected_cells.add(cell)
            if not cell.is_dir():raise ValueError('actual native cell required')
            cache=cell/'replies/responses.sqlite'
            if cache.exists():expected_caches.add(cache)
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist',allow_unconfirmed=o['status']=='failed')
            m=o['metadata'];runs=m['runs'];measurements=m['measurements']
            if len(runs)>1 or len(measurements)>1 or measurements and not runs:
                raise ValueError('one actual world and measurement or explicit technical null required')
            if runs:
                proof=physical_proof(cell,spec,world=p['world'],seed=driver.SEED,years=4,evidence=runs[0])
                if measurements:
                    checkpoint=Path(runs[0]['checkpoint_path'])
                    paths=[checkpoint.parent/f'portable_checkpoint_year_{year}.json.gz' for year in range(5)]
                    rebuilt={**measure_from_checkpoints(proof['measurement'],paths),
                        'measurement_adapter_contract_sha256':digest(p['measurement_contract'])}
                    if measurements!=[rebuilt] or m['technical_failures']:
                        raise ValueError('cold original checkpoints and full T/P measurement differ')
                elif not m['technical_failures'] or o['status']!='failed':
                    raise ValueError('completed physical world without measurement needs explicit technical null')
            else:
                if o['status']!='failed' or not m['technical_failures']:
                    raise ValueError('unobserved world cannot gain a loss')
                if cache.exists() and not gate['confirmed']:raise ValueError('responses follow unconfirmed role load')
                proof=physical_proof(cell,spec,world=p['world'],seed=driver.SEED,years=4) if cache.exists() else {'status':'pre-response-journal-failure'}
            scores={k:evaluate_loss(v,measurements) for k,v in p['losses'].items()}
            if (o['candidate']!=system or o['suggestion_id']!=identity or o['loss']!=scores[objective]['loss']
                    or m['loss_evaluation']!=scores[objective] or (o['status']=='complete')!=(scores[objective]['status']=='complete')):
                raise ValueError('original submitted system and assigned loss differ')
            if standalone:
                if ({k:v for k,v in read(directory/'cross-scores.json').items() if k!='content_sha256'}!=scores
                        or o['status']!='complete' or any(v['status']!='complete' for v in scores.values())):
                    raise ValueError('all five complete common cross-scores required')
                pairs.append({'suggestion':s.to_dict(),'observation':Observation.from_dict(o).to_dict()})
            worlds.append({'identity':identity,'role':role,'seed':driver.SEED,'system':system,'status':o['status'],
                'scores':{k:v['loss'] for k,v in scores.items()},'physical_proof':proof,'loaded':gate})
        for label in p['reference_order']:
            physical(root/'references'/label,'reference-'+label,p['reference_systems'][label],'developer-reference')
        context=build_context(pairs,world=p['world'],seeds=[driver.SEED],loss_spec=p['losses']['throughput'])
        if context!=read(root/'developer-reference-context.json'):raise ValueError('common developer context differs')
        ready=read(root/'developer-reference-context-ready.json')
        if ready['context_sha256']!=context['content_sha256'] or ready['complete_references']!=5:
            raise ValueError('reference readiness differs')
        controllers={}
        for objective in p['objectives']:
            c=replay_campaign(root/'search'/objective/'campaign','blackbox')
            if c.binding!=binding(objective,context) or c.state['pending'] is not None or len(c.state['records'])!=2:
                raise ValueError('exact two terminal own proposals per objective required')
            controllers[objective]=c
        selected=read(root/'selection.json')
        expected=driver.selection(root,p,context,frozen_utc=selected['frozen_utc'],campaign_loader=lambda r,p,o,c:controllers[o])
        if expected!={k:v for k,v in selected.items() if k!='content_sha256'}:
            raise ValueError('literal own selection or tie set differs')
        readiness=[];authoring=[]
        for slot in p['schedule']:
            objective,g=slot['objective'],slot['generation'];c=controllers[objective];record=c.state['records'][g]
            directory=root/'search'/objective;base=directory/f'readiness-{g}'/'editor-readiness'
            cert,cp=calibration(base,request_at(c,g),epoch(ready['completed_utc']))
            readiness.append({'objective':objective,'generation':g,'certificate':cert,'cold_proof':cp})
            generation=directory/'authoring'/('generation-'+record['request_sha256']);expected_authors.add(generation)
            wrapper_error=None
            try:definition=replay(generation)
            except Exception as error:
                wrapper_error={'type':type(error).__name__,'message':str(error)[:2000],'loss':None};definition=None
                if record['definition'] is not None or record['generation_error']!=wrapper_error:raise
            intent=read(generation/'intent.json')
            if (definition!=record['definition'] or intent['request']!=record['request']
                    or intent['source_commit']!=p['source_commit'] or intent['provider']!=p['designer']
                    or intent['post_edit_component_bank']!=p['component_bank'] or intent['seconds']!=1800
                    or intent['maximum_posts']!=16 or intent['certificate']!=str((base/'calibration/certificate.json').resolve())):
                raise ValueError('literal proposal/executor/budget binding differs')
            for path in (generation/'wire').glob('dispatch-*.intent.json'):require_age(read(path)['started_utc'],cert['completed_epoch'])
            responses=list((generation/'authoring').glob('generation-*/response.json'))
            if wrapper_error is None and len(responses)!=1 or len(responses)>1:
                raise ValueError('exact staged terminal response accounting required')
            staged=read(responses[0]) if responses else None
            authoring.append({'objective':objective,'generation':g,'request_sha256':record['request_sha256'],
                'definition':record['definition'],'generation_error':record['generation_error'],'wrapper_error':wrapper_error,
                'component_testing':None if staged is None else staged['component_testing'],'raw_directory':str(generation)})
            for draw,o in zip(record['draws'],record['observations']):
                if o is not None and draw['suggestion'] is not None:
                    physical(directory,draw['suggestion']['suggestion_id'],o['candidate'],'search:'+objective,observation=o,objective=objective)
        actual_wires={v.parent for v in root.rglob('dispatch-*.intent.json')}
        if (expected_cells!={v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or expected_caches!={v.resolve() for v in root.rglob('responses.sqlite')}
                or expected_authors!={v.parent.resolve() for v in root.glob('search/*/authoring/generation-*/intent.json')}
                or set(p['reference_order'])!={v.name for v in (root/'references').iterdir()}
                or not calibration_wires<=actual_wires<=calibration_wires|{v/'wire' for v in expected_authors}
                or before!=_inventory(root)):
            raise ValueError('unaccounted or changed native cells/caches/designer calls/references')
        driver.save(output,{'schema':SCHEMA,'source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],
            'source_proof':source,'closure':{'started':start,'terminal':end},'selection':selected,'worlds':worlds,
            'developer_references':context,'initial_readiness':{'certificate':initial_cert,'cold_proof':initial_cp},
            'readiness':readiness,'authoring':authoring,'raw_inventory_sha256':digest(before),'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)),'new_model_calls':0,'new_code_executions':0,
            'held_out_evaluation':False,'scientific_truth_measured':False,'publication_ready':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:worker(a.run,a.output);return
    result=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(Path(__file__).resolve()),'--worker','--run',str(a.run.resolve()),
        '--frozen-source',str(a.frozen_source.resolve()),'--output',str(a.output.resolve())],cwd=a.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
