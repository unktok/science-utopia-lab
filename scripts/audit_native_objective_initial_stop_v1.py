"""Cold proof of the specific stopped first objective study, never normal closure."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA='scienceutopia.native-objective-initial-stop-audit.v1'
ERROR='bounded post-edit configuration differs from bank/source/budget'


def require_initial_stop(plan,start,end):
    if (plan['schema']!='scienceutopia.native-objective-instrument-loop.v1.plan'
            or start['schema']!='scienceutopia.native-objective-instrument-loop.v1.start'
            or end['schema']!='scienceutopia.native-objective-instrument-loop.v1.terminal'
            or start['plan_sha256']!=plan['content_sha256'] or end['status']!='stopped'
            or end['stage']!='optimization' or end['complete_references']!=5
            or end['error_type']!='ValueError' or end['error']!=ERROR):
        raise ValueError('specific original first-proposal budget-guard stop required')


def worker(root,output):
    from scripts import run_native_objective_instrument_loop_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_observer_physical_v1 import ColdObserver,reconstruct_measurement,accepted_request_keys
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.audit_native_institution_loop_v1 import epoch,require_age
    from utopia.optimization.blackbox import Observation
    from utopia.optimization.native_bounded_staged_designer import replay
    from utopia.optimization.native_staged_author_v15 import replay_staged_generation
    from utopia.optimization.native_designer_preflight import require_certificate,EXECUTION_SCOPE
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.native_development_references import build_context
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.loss import evaluate_loss
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    root,output=Path(root).resolve(),Path(output).resolve();read=driver.read
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):raise ValueError('fresh audit outside stopped source/raw required')
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);before=_inventory(root);p=driver.require_plan(root)
        start,end=read(root/'started.json'),read(root/'terminal.json');require_initial_stop(p,start,end)
        if epoch(end['ended_utc'])<epoch(start['started_utc']) or (root/'selection.json').exists() or (root/'evaluation').exists():
            raise ValueError('stopped original cannot acquire selection or evaluation')
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=['scripts/run_native_objective_instrument_loop_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py'],
            resources=[driver.PROTOCOL,driver.BANK_MANIFEST,driver.CONTENT_LOSS])
        observer=ColdObserver(root/'observer',p['observer_contract']);observer_audit=observer.audit()
        worlds=[];pairs=[];cells=set();keys=set()
        for label in p['reference_order']:
            directory=root/'references'/label;identity='reference-'+label;system=p['reference_systems'][label]
            dispatched=read(directory/'started.json');o=read(directory/'observation.json');spec=SystemSpec.from_dict(system)
            if (o['status']!='complete' or o['suggestion_id']!=identity or o['candidate']!=system
                    or dispatched['suggestion']['suggestion_id']!=identity or dispatched['suggestion']['candidate']!=system
                    or dispatched['suggestion']['phase']!='developer-reference' or dispatched['seed']!=driver.SEED):
                raise ValueError('literal completed original reference required')
            verify_native_observation(Observation.from_dict(o),p['world'],[driver.SEED])
            cell=directory/'worlds'/(identity+'-s'+str(driver.SEED));cells.add(cell)
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist')
            run=o['metadata']['runs'][0];proof=physical_proof(cell,spec,world=p['world'],seed=driver.SEED,years=4,evidence=run)
            state=read_portable_checkpoint(run['checkpoint_path']);m=reconstruct_measurement(state,proof['measurement'],observer)
            keys.update(accepted_request_keys(state,p['observer_contract']))
            scores={k:evaluate_loss(v,[m]) for k,v in p['losses'].items()}
            if (o['metadata']['measurements']!=[m] or o['metadata']['technical_failures'] or o['loss']!=scores['throughput']['loss']
                    or o['metadata']['loss_evaluation']!=scores['throughput']
                    or read(directory/'cross-scores.json')!={**scores,'content_sha256':digest(scores)}):
                raise ValueError('original native/additional measurement differs')
            pairs.append({'suggestion':dispatched['suggestion'],'observation':Observation.from_dict(o).to_dict()})
            worlds.append({'identity':identity,'role':'developer-reference','seed':driver.SEED,'system':system,'status':'complete',
                'scores':{k:v['loss'] for k,v in scores.items()},'physical_proof':proof,'loaded':gate})
        context=build_context(pairs,world=p['world'],seeds=[driver.SEED],loss_spec=p['losses']['throughput'])
        if context!=read(root/'developer-reference-context.json'):raise ValueError('actual common reference context differs')
        c=replay_campaign(root/'search/throughput/campaign','blackbox');pending=c.state['pending']
        if c.state['records'] or pending is None or pending['generated'] or pending['compiled'] or pending['observations'] or pending['definition'] is not None:
            raise ValueError('original first pending/unadopted proposal boundary required')
        request=c._request([],c._validate(),1)
        if request!=pending['request'] or digest(request)!=pending['request_sha256']:raise ValueError('actual first author request differs')
        base=root/'search/throughput/readiness-0/editor-readiness';replay(base);cert=read(base/'calibration/certificate.json')
        class Reply:
            def __init__(self,value):self.value=value
            def raise_for_status(self):pass
            def json(self):return self.value
        class Backend:
            def get(self,url,timeout):
                if url.endswith('/api/version'):return Reply({'version':p['backend']['ollama_version']})
                if url.endswith('/api/tags'):return Reply({'models':[{'name':p['designer']['model'],'digest':p['designer']['model_digest']}]})
                raise ValueError('cold metadata cannot dispatch')
        cp=require_certificate(base/'calibration/certificate.json',p['designer'],protocol='staged-v15',session=Backend(),
            now=cert['completed_epoch'],scope=EXECUTION_SCOPE,conversation_profile=BOUNDED_AUTHORING)
        if cert['plan']['request']!=request or cp['post_edit_component_contract']!=p['post_edit_contract']:
            raise ValueError('actual readiness request/mode differs')
        generation=root/'search/throughput/authoring'/('generation-'+digest(request));intent=read(generation/'intent.json')
        if (intent['request']!=request or intent['source_commit']!=p['source_commit'] or intent['provider']!=p['designer']
                or intent['post_edit_component_bank']!=p['component_bank'] or intent['seconds']!=1800 or intent['maximum_posts']!=16):
            raise ValueError('literal bounded proposal binding differs')
        try:replay(generation)
        except ValueError as error:
            if str(error)!=ERROR:raise
        else:raise ValueError('original guarded replay unexpectedly succeeds; never relabel the stop')
        worker=read(generation/'worker-result.json');inner=generation/'authoring'/('generation-'+digest(request))
        definition=replay_staged_generation(inner,expected_request=request,expected_provider_binding=p['designer'])
        staged=read(inner/'response.json')
        if not worker.get('submitted') or worker.get('error_type') or definition!=worker['definition']:
            raise ValueError('literal submitted inner definition required, not repaired source')
        wires=list((generation/'wire').glob('dispatch-*.intent.json'))
        for path in wires:require_age(read(path)['started_utc'],cert['completed_epoch'])
        if (cells!={v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or {cell/'replies/responses.sqlite' for cell in cells}!={v.resolve() for v in root.rglob('responses.sqlite')}
                or {r['key'] for r in observer_audit['rows']}!=keys
                or list(root.glob('search/content-utility/campaign/*'))
                or {v.parent for v in root.glob('search/*/authoring/generation-*/intent.json')}!={generation}):
            raise ValueError('unaccounted reference/native world/critic/authoring activity')
        if before!=_inventory(root):raise ValueError('stopped original raw changed during cold proof')
        result={'schema':SCHEMA,'source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],'source_proof':source,
            'closure':{'started':start,'terminal':end,'scientific_study_closed':False},'worlds':worlds,'observer':observer_audit,
            'pending_controller_record':pending,'submitted_inner_definition':definition,'submitted_inner_definition_sha256':digest(definition),
            'actual_component_testing':staged['component_testing'],'proposal_posts':len(wires),'actual_readiness':cp,
            'pending_proposals':1,'unattempted_proposal_slots':7,'candidate_native_worlds':0,'selection':None,'logical_evaluation':[],
            'raw_inventory_sha256':digest(before),'raw_files':len(before),'analysis_adapter_sha256':file_sha256(Path(__file__)),
            'new_model_calls':0,'new_code_executions':0,'held_out_evaluation':False,'publication_ready':False}
        result['content_sha256']=digest(result);write_json_atomic(output,result,sort_keys=True,allow_nan=False)
        print(json.dumps({'audit':str(output),'worlds':len(worlds),'proposal_posts':len(wires),'study_closed':False,'content_sha256':result['content_sha256']}))


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
