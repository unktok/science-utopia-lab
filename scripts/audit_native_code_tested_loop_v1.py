"""Original-source cold audit of a normally closed code-tested native loop."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root,output):
    from scripts import run_native_code_tested_loop_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    from scripts.audit_native_institution_loop_v1 import request_at,require_age,epoch
    from scripts.audit_pre_scale_search_v1 import forward_evidence
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_benchmark_physical import physical_proof
    from utopia.optimization.native_bounded_staged_designer import replay
    from utopia.optimization.native_designer_preflight import require_certificate,EXECUTION_SCOPE
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.blackbox import Observation
    from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
    from utopia.system import SystemSpec
    from utopia.system.design_patch import clone,digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh audit outside scientific raw/source required')
    read=driver.read
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=_inventory(root);p=driver.require_plan(root)
        start,end=read(root/'started.json'),read(root/'terminal.json')
        if (end['schema']!=driver.SCHEMA+'.terminal' or start['schema']!=driver.SCHEMA+'.start'
                or end['status']!='closed' or start['plan_sha256']!=p['content_sha256']
                or epoch(end['ended_utc'])<epoch(start['started_utc'])):
            raise ValueError('normal code-tested loop closure required')
        prior=read(root/'preceding-closed.json')['terminal']
        if prior['status']!='closed':raise ValueError('preceding science/audit did not close')
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=[
            'scripts/run_native_code_tested_loop_v1.py','scripts/native_benchmark_physical.py',
            'scripts/run_native_institution_loop_v1.py','scripts/run_pre_scale_search_v1.py'],
            resources=[driver.PROTOCOL,driver.BANK_MANIFEST])
        controllers={}
        for arm in p['arm_order']:
            c=replay_campaign(root/'search/run-00'/arm.replace(':','--')/'campaign','blackbox')
            expected={**clone(p['campaign_bindings']['run-00'][arm]),'mode':'blackbox',
                'learning_rate':.1,'strategy_learning_rate':.1,'strategy_baseline':0.,
                'exploration':.1,'proposal_feedback':'matched-loss'}
            if c.binding!=expected or c.state['pending'] is not None or len(c.state['records'])!=2:
                raise ValueError('exact terminal campaign/slot binding required')
            controllers[arm]=c
        selected=read(root/'selection.json')
        if {k:v for k,v in selected.items() if k!='content_sha256'}!=driver.selection(root,p,frozen_utc=selected['frozen_utc']):
            raise ValueError('development selection differs from assigned losses and all ties')
        if (root/'evaluation').exists():raise ValueError('unplanned evaluation directory')

        class Reply:
            def __init__(self,data):self.data=data
            def raise_for_status(self):pass
            def json(self):return self.data
        class Backend:
            def get(self,url,timeout):
                if url.endswith('/api/version'):return Reply({'version':p['backend']['ollama_version']})
                if url.endswith('/api/tags'):return Reply({'models':[{'name':p['designer']['model'],'digest':p['designer']['model_digest']}]})
                raise ValueError('offline metadata adapter cannot dispatch')

        readiness=[];authoring=[];expected_authors=set();expected_cells=set();expected_caches=set();worlds=[]
        def physical(directory,identity,system,role,observation=None,objective='throughput'):
            spec=SystemSpec.from_dict(system);standalone=observation is None
            o=read(directory/'observation.json') if standalone else observation
            if standalone:
                dispatched=read(directory/'started.json')
                if (dispatched['identity'],dispatched['system'],dispatched['seed'],dispatched['role'])!=(identity,system,61001,role):
                    raise ValueError('reference dispatch differs')
            if (o['suggestion_id']!=identity or o['candidate']!=system
                    or o['metadata']['system_fingerprint']!=spec.fingerprint
                    or o['metadata']['loss_spec_sha256']!=loss_spec_sha256(p['losses'][objective])):
                raise ValueError('native observation identity/loss differs')
            cell=directory/'worlds'/(identity+'-s61001');expected_cells.add(cell.resolve())
            if not cell.is_dir():raise ValueError('physical world evidence missing')
            cache=cell/'replies/responses.sqlite'
            if cache.exists():expected_caches.add(cache.resolve())
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist',allow_unconfirmed=o['status']=='failed')
            if forward_evidence(o):
                if o['status']=='complete':verify_native_observation(Observation.from_dict(o),p['world'],[61001])
                proof=physical_proof(cell,spec,world=p['world'],seed=61001,years=4,evidence=o['metadata']['runs'][0])
                if o['metadata']['measurements']!=[proof['measurement']]:raise ValueError('measurement differs from checkpoint')
            else:
                if cache.exists() and not gate['confirmed']:raise ValueError('scientist responses followed unconfirmed role load')
                proof=physical_proof(cell,spec,world=p['world'],seed=61001,years=4) if cache.exists() else {'status':'pre-response-journal-failure'}
            scores={k:evaluate_loss(v,o['metadata']['measurements']) for k,v in p['losses'].items()}
            if o['loss']!=scores[objective]['loss'] or o['metadata']['loss_evaluation']!=scores[objective]:
                raise ValueError('loss differs from actual components')
            if standalone and {k:v for k,v in read(directory/'cross-scores.json').items() if k!='content_sha256'}!=scores:
                raise ValueError('reference cross-scores differ')
            worlds.append({'identity':identity,'role':role,'seed':61001,'system':system,'status':o['status'],
                'scores':{k:v['loss'] for k,v in scores.items()},'physical_proof':proof,'loaded':gate})

        for label in p['reference_order']:
            physical(root/'references'/label,'reference-'+label,p['reference_systems'][label],'developer-reference')
        for slot in p['schedule']:
            arm,g=slot['arm'],slot['generation'];c=controllers[arm];record=c.state['records'][g]
            directory=root/'search/run-00'/arm.replace(':','--');base=directory/f'readiness-{g}'/'editor-readiness'
            replay(base);cert=read(base/'calibration/certificate.json')
            proof=require_certificate(base/'calibration/certificate.json',p['designer'],protocol='staged-v15',
                session=Backend(),now=cert['completed_epoch'],scope=EXECUTION_SCOPE,conversation_profile=BOUNDED_AUTHORING)
            if (cert['plan']['request']!=request_at(c,g) or cert['plan']['backend']!=p['backend']
                    or cert['plan']['runtime']!=p['runtime'] or proof['post_edit_component_contract']!=p['post_edit_contract']):
                raise ValueError('fresh readiness differs from source/request/mode')
            readiness.append({'arm':arm,'generation':g,'certificate':cert,'cold_proof':proof})
            generation=directory/'authoring'/('generation-'+record['request_sha256']);expected_authors.add(generation.resolve())
            definition=replay(generation);intent=read(generation/'intent.json')
            if (definition!=record['definition'] or intent['request']!=record['request']
                    or intent['source_commit']!=p['source_commit'] or intent['provider']!=p['designer']
                    or intent['post_edit_component_bank']!=p['component_bank'] or intent['seconds']!=1800
                    or intent['certificate']!=str((base/'calibration/certificate.json').resolve())):
                raise ValueError('literal proposal or test-bank binding differs')
            for path in (generation/'wire').glob('dispatch-*.intent.json'):require_age(read(path)['started_utc'],cert['completed_epoch'])
            responses=list((generation/'authoring').glob('generation-*/response.json'))
            if len(responses)!=1:raise ValueError('one exact staged response per proposal required')
            staged=read(responses[0])
            authoring.append({'arm':arm,'generation':g,'request_sha256':record['request_sha256'],
                'definition':record['definition'],'generation_error':record['generation_error'],
                'component_testing':staged['component_testing'],'raw_directory':str(generation)})
            for draw,o in zip(record['draws'],record['observations']):
                if o is not None:physical(directory,draw['suggestion']['suggestion_id'],o['candidate'],'search:'+arm,
                    observation=o,objective=p['assignments'][arm]['objective'])
        if (expected_cells!={v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or expected_caches!={v.resolve() for v in root.rglob('responses.sqlite')}
                or expected_authors!={v.parent.resolve() for v in root.glob('search/run-00/*/authoring/generation-*/intent.json')}
                or set(p['reference_order'])!={v.name for v in (root/'references').iterdir()}):
            raise ValueError('unaccounted physical world/cache/author/reference')
        calibration_wires={root/'search/run-00'/s['arm'].replace(':','--')/f'readiness-{s["generation"]}'/'editor-readiness/wire'
            for s in p['schedule']}
        expected_wires=calibration_wires|{v/'wire' for v in expected_authors}
        actual_wires={v.parent for v in root.rglob('dispatch-*.intent.json')}
        if not calibration_wires<=actual_wires<=expected_wires:
            raise ValueError('unaccounted designer dispatch directory')
        if before!=_inventory(root):raise ValueError('raw code-tested loop changed during cold audit')
        result={'schema':'scienceutopia.native-code-tested-loop-audit.v1','source_commit':p['source_commit'],
            'plan_sha256':p['content_sha256'],'source_proof':source,'closure':{'started':start,'terminal':end},
            'selection':selected,'worlds':worlds,'readiness':readiness,'authoring':authoring,
            'raw_inventory_sha256':digest(before),'raw_files':len(before),'analysis_adapter_sha256':file_sha256(Path(__file__)),
            'new_model_calls':0,'new_code_executions':0,'held_out_evaluation':False,'publication_ready':False}
        result['content_sha256']=digest(result);write_json_atomic(output,result,sort_keys=True,allow_nan=False)
        print(json.dumps({'audit':str(output),'worlds':len(worlds),'content_sha256':result['content_sha256']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:worker(a.run,a.output);return
    if json.loads((a.run/'terminal.json').read_text()).get('status')!='closed':raise ValueError('closed code-tested loop required')
    script=Path(__file__).resolve();before=hashlib.sha256(script.read_bytes()).hexdigest()
    response=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(script),'--worker','--run',str(a.run.resolve()),
        '--frozen-source',str(a.frozen_source.resolve()),'--output',str(a.output.resolve())],
        cwd=a.frozen_source,env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if hashlib.sha256(script.read_bytes()).hexdigest()!=before:raise ValueError('audit adapter changed')
    if response.returncode:raise SystemExit(response.returncode)


if __name__=='__main__':main()
