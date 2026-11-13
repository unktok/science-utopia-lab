"""Cold original-source proof of all objective-search slots and critic evidence."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root,output,*,study='objective-v1'):
    if study == 'objective-v1':
        from scripts import run_native_objective_instrument_loop_v1 as driver
        reference_count, generation_count = 5, 4
        audit_schema = 'scienceutopia.native-objective-instrument-loop-audit.v1'
        driver_script = 'scripts/run_native_objective_instrument_loop_v1.py'
    elif study == 'planning-v1':
        from scripts import run_native_planning_objective_loop_v1 as driver
        reference_count, generation_count = 8, 3
        audit_schema = 'scienceutopia.native-planning-objective-loop-audit.v1'
        driver_script = 'scripts/run_native_planning_objective_loop_v1.py'
    elif study == 'parent-presentation-v1':
        from scripts import run_native_parent_presentation_loop_v1 as driver
        reference_count, generation_count = 8, 3
        audit_schema = 'scienceutopia.native-parent-presentation-loop-audit.v1'
        driver_script = 'scripts/run_native_parent_presentation_loop_v1.py'
    else:
        raise ValueError('explicit known original-source study required')
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    from scripts.audit_native_institution_loop_v1 import request_at,require_age,epoch
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_observer_physical_v1 import ColdObserver,reconstruct_measurement,accepted_request_keys
    from utopia.optimization.blackbox import Observation,Suggestion
    from utopia.optimization.native_bounded_staged_designer import replay
    from utopia.optimization.native_development_references import build_context
    from utopia.optimization.native_designer_preflight import require_certificate,EXECUTION_SCOPE
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.design_patch import clone,digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    root,output=Path(root).resolve(),Path(output).resolve();read=driver.read
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh audit outside scientific source/raw required')
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=_inventory(root);p=driver.require_plan(root);start=read(root/'started.json');end=read(root/'terminal.json')
        if (start['schema']!=driver.SCHEMA+'.start' or end['schema']!=driver.SCHEMA+'.terminal'
                or start['plan_sha256']!=p['content_sha256'] or end['status']!='closed' or end['complete_references']!=reference_count
                or epoch(end['ended_utc'])<epoch(start['started_utc'])):
            raise ValueError('normal exact objective-loop closure required')
        scripts=[driver_script,'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py']
        if study in ('planning-v1', 'parent-presentation-v1'): scripts += ['scripts/audit_native_planning_objective_loop_v1.py',
            'scripts/audit_native_objective_instrument_loop_v1.py']
        if study == 'parent-presentation-v1':
            scripts += ['scripts/audit_native_parent_presentation_loop_v1.py']
        resources=[driver.PROTOCOL,driver.BANK_MANIFEST,driver.CONTENT_LOSS]
        if study == 'parent-presentation-v1': resources.append(driver.MOTIVATION)
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=scripts,resources=resources)
        observer=ColdObserver(root/'observer',p['observer_contract']);observer_audit=observer.audit()
        if observer_audit!=read(root/'observer-audit.json'):raise ValueError('literal observer cold audit differs')
        expected_cells=set();expected_caches=set();expected_authors=set();eligible_critic_keys=set();worlds=[];pairs=[]

        def physical(directory,identity,system,role,observation=None,objective='throughput'):
            spec=SystemSpec.from_dict(system);standalone=observation is None
            o=read(directory/'observation.json') if standalone else observation
            if (o['suggestion_id']!=identity or o['candidate']!=system
                    or o['metadata']['system_fingerprint']!=spec.fingerprint
                    or o['metadata']['loss_spec_sha256']!=loss_spec_sha256(p['losses'][objective])):
                raise ValueError('actual native observation identity/loss differs')
            if standalone:
                dispatched=read(directory/'started.json');s=Suggestion.from_dict(dispatched['suggestion'])
                if (s.suggestion_id!=identity or s.candidate!=system or s.phase!='developer-reference'
                        or dispatched['seed']!=driver.SEED or epoch(dispatched['started_utc'])<epoch(start['started_utc'])):
                    raise ValueError('actual common reference dispatch differs')
            cell=directory/'worlds'/(identity+'-s'+str(driver.SEED));expected_cells.add(cell)
            if not cell.is_dir():raise ValueError('original physical world directory required')
            cache=cell/'replies/responses.sqlite'
            if cache.exists():expected_caches.add(cache)
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist',allow_unconfirmed=o['status']=='failed')
            m=o['metadata'];runs=m['runs'];measurements=m['measurements']
            if len(runs)>1 or len(measurements)>1 or (measurements and not runs):raise ValueError('ambiguous physical native observation')
            if runs:
                # A completed native world can have a technical observer failure.
                # Retain its physical base proof without inventing a loss/report.
                proof=physical_proof(cell,spec,world=p['world'],seed=driver.SEED,years=4,evidence=runs[0])
                state=read_portable_checkpoint(runs[0]['checkpoint_path'])
                eligible_critic_keys.update(accepted_request_keys(state,p['observer_contract']))
                if measurements:
                    rebuilt=reconstruct_measurement(state,proof['measurement'],observer)
                    if measurements!=[rebuilt] or m['technical_failures']:raise ValueError('native/common measurement differs from original state/replies')
                elif not m['technical_failures'] or o['status']!='failed':
                    raise ValueError('completed native world without measurement requires retained technical failure')
            else:
                if o['status']!='failed' or not m['technical_failures']:raise ValueError('unobserved world cannot acquire a scientific result')
                if cache.exists() and not gate['confirmed']:raise ValueError('scientist replies follow an unconfirmed role load')
                proof=physical_proof(cell,spec,world=p['world'],seed=driver.SEED,years=4) if cache.exists() else {'status':'pre-response-journal-failure'}
            scores={k:evaluate_loss(v,measurements) for k,v in p['losses'].items()}
            if (o['loss']!=scores[objective]['loss'] or m['loss_evaluation']!=scores[objective]
                    or (o['status']=='complete')!=(scores[objective]['status']=='complete')):
                raise ValueError('assigned native criterion differs from exact original measurement')
            if standalone:
                if {k:v for k,v in read(directory/'cross-scores.json').items() if k!='content_sha256'}!=scores:
                    raise ValueError('developer reference cross-scores differ')
                if o['status']!='complete' or any(s['status']!='complete' for s in scores.values()):
                    raise ValueError('normal closure requires all common references measured')
                pairs.append({'suggestion':s.to_dict(),'observation':Observation.from_dict(o).to_dict()})
            worlds.append({'identity':identity,'role':role,'seed':driver.SEED,'system':system,'status':o['status'],
                'scores':{k:v['loss'] for k,v in scores.items()},'physical_proof':proof,'loaded':gate})

        for label in p['reference_order']:
            physical(root/'references'/label,'reference-'+label,p['reference_systems'][label],'developer-reference')
        context=build_context(pairs,world=p['world'],seeds=[driver.SEED],loss_spec=p['losses']['throughput'])
        if context!=read(root/'developer-reference-context.json'):raise ValueError('common developer evidence differs')
        ready=read(root/'developer-reference-context-ready.json')
        if ready['context_sha256']!=context['content_sha256'] or ready['complete_references']!=reference_count:
            raise ValueError('developer reference availability differs')
        presentation_study = study == 'parent-presentation-v1'
        campaign_order = p['arm_order'] if presentation_study else p['objectives']
        def objective_for(arm): return p['arms'][arm]['objective'] if presentation_study else arm
        def strategies_for(arm):
            return (p['strategies_by_presentation'][p['arms'][arm]['presentation']]
                    if presentation_study else p['strategies'])
        controllers={}
        for arm in campaign_order:
            objective=objective_for(arm)
            c=replay_campaign(root/'search'/arm/'campaign','blackbox')
            expected={'initial_system':p['initial_system'],'loss_spec':p['losses'][objective],
                'world':p['world'],'seeds':[driver.SEED],'strategies':strategies_for(arm),'mode':'blackbox',
                'seed':p['optimizer_seed'],'learning_rate':.1,'strategy_learning_rate':.1,
                'strategy_baseline':0.,'exploration':.1,'design_space':p['design_space'],'development_references':context}
            if c.binding!=expected or c.state['pending'] is not None or len(c.state['records'])!=generation_count:
                raise ValueError('exact common-context campaign and four terminal own slots required')
            controllers[arm]=c
        selected=read(root/'selection.json')
        expected=driver.selection(root,p,context,frozen_utc=selected['frozen_utc'],campaign_loader=lambda r,p,o,c:controllers[o])
        if expected!={k:v for k,v in selected.items() if k!='content_sha256'}:raise ValueError('own-submission selection/ties differ')
        if (root/'evaluation').exists():raise ValueError('unplanned same-run evaluation')

        class Reply:
            def __init__(self,data):self.data=data
            def raise_for_status(self):pass
            def json(self):return self.data
        class Backend:
            def get(self,url,timeout):
                if url.endswith('/api/version'):return Reply({'version':p['backend']['ollama_version']})
                if url.endswith('/api/tags'):return Reply({'models':[{'name':p['designer']['model'],'digest':p['designer']['model_digest']}]})
                raise ValueError('cold metadata adapter cannot dispatch')
        readiness=[];authoring=[];calibration_wires=set();initial_readiness=None
        initial_modes = p['presentations'] if presentation_study else [None] if study == 'planning-v1' else []
        if presentation_study: initial_readiness = {}
        for presentation in initial_modes:
            initial_directory = root/'initial-readiness'
            if presentation is not None: initial_directory = initial_directory/presentation
            prototype=replay_campaign(initial_directory/'campaign','blackbox')
            expected={'initial_system':p['initial_system'],'loss_spec':p['losses']['throughput'],
                'world':p['world'],'seeds':[driver.SEED],
                'strategies':strategies_for('throughput-'+presentation) if presentation_study else p['strategies'],'mode':'blackbox',
                'seed':p['optimizer_seed'],'learning_rate':.1,'strategy_learning_rate':.1,
                'strategy_baseline':0.,'exploration':.1,'design_space':p['design_space']}
            if prototype.binding!=expected or prototype.state['records'] or prototype.state['pending'] is not None:
                raise ValueError('empty source-bound planning prototype required')
            base=initial_directory/'editor-readiness';replay(base)
            cert=read(base/'calibration/certificate.json')
            cp=require_certificate(base/'calibration/certificate.json',p['designer'],protocol='staged-v15',session=Backend(),
                now=cert['completed_epoch'],scope=EXECUTION_SCOPE,conversation_profile=BOUNDED_AUTHORING)
            if (cert['plan']['request']!=request_at(prototype,0) or cert['plan']['backend']!=p['backend']
                    or cert['plan']['runtime']!=p['runtime'] or cp['post_edit_component_contract']!=p['post_edit_contract']
                    or cert['plan']['created_epoch']<epoch(start['started_utc'])):
                raise ValueError('fresh initial planning readiness differs')
            for label in p['reference_order']:
                dispatched=read(root/'references'/label/'started.json')
                if epoch(dispatched['started_utc'])<cert['completed_epoch']:
                    raise ValueError('planning reference predates initial readiness')
            calibration_wires.add(base/'wire')
            proof={'certificate':cert,'cold_proof':cp}
            if presentation_study: initial_readiness[presentation]=proof
            else: initial_readiness=proof
        for slot in p['schedule']:
            objective,g=slot['objective'],slot['generation'];arm=slot['arm'] if presentation_study else objective
            c=controllers[arm];record=c.state['records'][g]
            directory=root/'search'/arm;base=directory/f'readiness-{g}'/'editor-readiness'
            replay(base);cert=read(base/'calibration/certificate.json')
            cp=require_certificate(base/'calibration/certificate.json',p['designer'],protocol='staged-v15',session=Backend(),
                now=cert['completed_epoch'],scope=EXECUTION_SCOPE,conversation_profile=BOUNDED_AUTHORING)
            if (cert['plan']['request']!=request_at(c,g) or cert['plan']['backend']!=p['backend']
                    or cert['plan']['runtime']!=p['runtime'] or cp['post_edit_component_contract']!=p['post_edit_contract']
                    or cert['plan']['created_epoch']<epoch(ready['completed_utc'])):
                raise ValueError('fresh readiness differs from actual history/reference/mode')
            readiness.append({'objective':objective,'generation':g,'certificate':cert,'cold_proof':cp,
                **({'arm':arm,'presentation':slot['presentation']} if presentation_study else {})})
            calibration_wires.add(base/'wire')
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
                raise ValueError('literal proposal/worker/probe binding differs')
            for path in (generation/'wire').glob('dispatch-*.intent.json'):require_age(read(path)['started_utc'],cert['completed_epoch'])
            responses=list((generation/'authoring').glob('generation-*/response.json'))
            if (wrapper_error is None and len(responses)!=1) or len(responses)>1:raise ValueError('exact staged terminal response accounting required')
            staged=read(responses[0]) if responses else None
            authoring.append({'objective':objective,'generation':g,'request_sha256':record['request_sha256'],
                'definition':record['definition'],'generation_error':record['generation_error'],'wrapper_error':wrapper_error,
                'component_testing':None if staged is None else staged['component_testing'],'raw_directory':str(generation),
                **({'arm':arm,'presentation':slot['presentation']} if presentation_study else {})})
            for draw,o in zip(record['draws'],record['observations']):
                if o is not None and draw['suggestion'] is not None:
                    physical(directory,draw['suggestion']['suggestion_id'],o['candidate'],'search:'+arm,observation=o,objective=objective)
        actual_critic_keys={r['key'] for r in observer_audit['rows']}
        if not actual_critic_keys<=eligible_critic_keys:raise ValueError('critic request has no accepted native content')
        if (expected_cells!={v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or expected_caches!={v.resolve() for v in root.rglob('responses.sqlite')}
                or expected_authors!={v.parent.resolve() for v in root.glob('search/*/authoring/generation-*/intent.json')}
                or set(p['reference_order'])!={v.name for v in (root/'references').iterdir()}):
            raise ValueError('unaccounted native world/cache/author/reference')
        actual_wires={v.parent for v in root.rglob('dispatch-*.intent.json')}
        if not calibration_wires<=actual_wires<=calibration_wires|{v/'wire' for v in expected_authors}:
            raise ValueError('unaccounted designer dispatch directory')
        if before!=_inventory(root):raise ValueError('raw objective study changed during cold proof')
        result={'schema':audit_schema,'source_commit':p['source_commit'],
            'plan_sha256':p['content_sha256'],'source_proof':source,'closure':{'started':start,'terminal':end},
            'selection':selected,'worlds':worlds,'observer':observer_audit,'developer_references':context,
            'readiness':readiness,'authoring':authoring,'raw_inventory_sha256':digest(before),'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)),'new_model_calls':0,'new_code_executions':0,
            'held_out_evaluation':False,'scientific_truth_measured':False,'publication_ready':False}
        if study in ('planning-v1', 'parent-presentation-v1'): result['initial_readiness']=initial_readiness
        result['content_sha256']=digest(result);write_json_atomic(output,result,sort_keys=True,allow_nan=False)
        print(json.dumps({'audit':str(output),'worlds':len(worlds),'content_sha256':result['content_sha256']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:worker(a.run,a.output);return
    if json.loads((a.run/'terminal.json').read_text())['status']!='closed':raise ValueError('normal objective-loop closure required')
    script=Path(__file__).resolve()
    result=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(script),'--worker','--run',str(a.run.resolve()),
        '--frozen-source',str(a.frozen_source.resolve()),'--output',str(a.output.resolve())],cwd=a.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
