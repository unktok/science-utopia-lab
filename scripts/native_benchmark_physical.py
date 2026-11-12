"""Seed/horizon-explicit native physical audit; no model or source execution.

Historical default horizons are preserved. Reuse strict response/code/domain
primitives, with caller-declared environment conditions for this study.
"""
import json
from pathlib import Path
import sqlite3

from scripts.analyze_native_autonomous_search_v14 import zero_http_response_proofs
from scripts.analyze_native_open_v7 import (
    RESPONSE_ACTUAL,code_proofs,domain_proofs,context_input_proofs,physical_initial_identity)
from scripts.audit_native_objective_v5 import checkpoint_measurements
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.native_kernel import NativeScienceKernel
from utopia.optimization.native_code_trace import validate_record
from utopia.utils.data_utils import file_sha256


def native_capacity_conditions_proof(state,conditions):
    """Actual checkpoint runtime fields, not only the declared response binding."""
    from utopia.optimization.native_factory import checked_world_conditions
    conditions=checked_world_conditions(conditions)
    if conditions is None or conditions['schema']!='scienceutopia.native-world-conditions.v2':
        raise ValueError('explicit native capacity condition scope required')
    capacity={k:conditions[k] for k in ('papers_per_project','funding_budget_mode','funding_budget_slots_frac')}
    actual_simulation=state['portable']['contract']['simulation']
    if (any(actual_simulation.get(k)!=v for k,v in capacity.items())
            or state['project_cost_policy']['papers_per_project']!=capacity['papers_per_project']
            or state['initial_university_count']!=5 or state['initial_industry_count']!=0):
        raise ValueError('actual native initial production/funding capacity differs from conditions')
    return capacity


def initial_world_conditions_proof(state,conditions,seed):
    """Verify actual founder records, not just declared configuration metadata."""
    from utopia.optimization.native_factory import checked_world_conditions
    from utopia.simulation import build_population_blueprint
    from utopia.system.design_patch import digest
    conditions=checked_world_conditions(conditions)
    if conditions is None:raise ValueError('explicit initial conditions required')
    blueprint=build_population_blueprint(5,1,seed,strategy_mix=['balanced'],
        resource_profile=conditions['population_resource_profile'],base_funding=conditions['initial_funding'])
    expected={r['researcher_name']:{'resources':r['initial_funding'],'initial_funding':r['initial_funding'],
        'resource_band':r['resource_band'],'is_active':True} for r in blueprint}
    authors=[a for a in state['ecosystem_data']['agents'] if a['can_author']]
    actual={a['id']:{k:a.get(k) for k in ('resources','initial_funding','resource_band','is_active')} for a in authors}
    if len(actual)!=len(authors) or actual!=expected:
        raise ValueError('actual native initial resource population differs from conditions')
    logging=conditions['log_resource_ledger']
    if (state['project_cost_policy']['log_resource_ledger'] is not logging
            or ('resource_ledger' in state)!=logging):
        raise ValueError('actual native initial ledger differs from conditions')
    proof={'conditions':conditions,'actual_author_records_sha256':digest(actual),
        'actual_initial_total':sum(a['resources'] for a in actual.values()),
        'actual_author_resources':{k:v['resources'] for k,v in sorted(actual.items())},
        'ledger_present':logging,'new_model_calls':0,'new_code_executions':0}
    if conditions['schema']=='scienceutopia.native-world-conditions.v2':
        capacity=native_capacity_conditions_proof(state,conditions)
        proof['actual_native_capacity']=capacity
        proof['fixed_annual_slot_cap']=(None if capacity['funding_budget_mode']=='track'
            else int(round(capacity['funding_budget_slots_frac']*state['initial_university_count'])))
    return proof


def code_attempt_proof(cell,spec,world):
    """Absent historical journals are unknown, not zero failed attempts."""
    cell=Path(cell);path=cell/'code-contexts.jsonl.attempts.jsonl'
    if not path.exists():return None
    from utopia.optimization.native_code_trace import recorded_attempts
    attempts=recorded_attempts(cell/'code-contexts.jsonl',binding={
        'source_commit':world['source_commit'],'system_fingerprint':spec.fingerprint,'run_id':cell.name})
    return {'file_sha256':file_sha256(path),
        'counts':{k:sum(a['status']==k for a in attempts) for k in ('returned','raised','pending')},
        'remote_completion_inferred':False,
        'unreturned_intents':[a['intent']['content_sha256'] for a in attempts if a['status']!='returned']}


def physical_proof(cell,spec,*,world,seed,years,evidence=None):
    cell=Path(cell).resolve();cache=cell/'replies/responses.sqlite'
    if not cache.is_file():raise ValueError('physical proof requires the actual response binding')
    with sqlite3.connect(cache.as_uri()+'?mode=ro',uri=True) as db:
        records=db.execute('SELECT binding FROM metadata').fetchall()
    if len(records)!=1:raise ValueError('one immutable native response binding required')
    binding=json.loads(records[0][0]);config=binding['science_config']
    from utopia.optimization.native_factory import checked_world_conditions
    conditions=checked_world_conditions(world.get('world_conditions'))
    if config.get('world_conditions')!=conditions or ('world_conditions' in config)!=(conditions is not None):
        raise ValueError('physical initial world-condition binding differs')
    if (binding['cell']!=spec.fingerprint or binding['seed']!=seed
            or binding['model']!=world['model'] or binding['model_revision']!=world['model_digest']
            or binding['corpus_sha256']!=world['corpus_sha256']
            or config['source_commit']!=world['source_commit'] or config['years']!=years
            or config['corpus_years']!=4 or config['runtime_seed_binding']!=world['runtime_seed_binding']
            or config['experiment']!=world['experiment']
            or config['population']!={'institutions':5,'per_institution':1,'strategy':'balanced'}
            or config['thinking_override'] is not False or config['max_tokens']!=768
            or config['maximum_http_attempts']!=(512 if years==2 else 1024)
            or config['lab_inference_serialized'] is not True):
        raise ValueError('physical source/model/data/seed/horizon/budget differs')
    if json.loads((cell/'system.json').read_text())!=spec.to_dict():
        raise ValueError('physical SystemSpec differs from declared policy/seed projection')
    paths=sorted(cell.rglob('portable_checkpoint_year_*.json.gz'),
        key=lambda p:int(p.name.split('_year_')[1].split('.')[0]))
    if not paths:
        if evidence is not None:raise ValueError('actual native initial checkpoint required')
        # A factory can fail after creating its empty bound cache but before
        # the first world checkpoint (e.g. incompatible runtime image). This
        # is a technical null, not an invented initialized/completed world.
        response=zero_http_response_proofs(cell,binding,[],complete=False,protocol={},
            classification=RESPONSE_ACTUAL,maximum_year=years)
        code=code_proofs(cell,spec,{'events':[]},world,cell.name,complete=False)
        attempts=code_attempt_proof(cell,spec,world)
        if attempts is not None:code['attempt_journal']=attempts
        if response['wire_requests'] or response['researcher_responses'] or code['recorded_executions']:
            raise ValueError('physical activity without original initial checkpoint')
        return {'status':'technical-failure-before-initial-checkpoint','seed':seed,'years':years,
            'through_committed_year':None,'initial_identity':None,'response_proof':response,
            'code_proof':code,'annual_checkpoints':[],'measurement':None,'checkpoint_sha256':None,
            'new_model_calls':0,'new_code_executions':0}
    previous_events=[];previous_elapsed=0.;counts=[];annual=[];last=None;initial=None
    for i,path in enumerate(paths):
        state=read_portable_checkpoint(path)
        if (state['year']!=i or state['phase']!=(0 if i==0 else 5) or i>years
                or state['portable']['contract']['binding']!=binding
                or state['native_system']['spec']!=spec.to_dict()
                or state['portable']['contract']['native_system']['system_fingerprint']!=spec.fingerprint
                or state['portable']['contract']['model']!=binding['model']
                or state['portable']['contract']['model_revision']!=binding['model_revision']
                or state['rag']['ordered_documents_sha256']!=world['corpus_sha256']):
            raise ValueError('native annual checkpoint lineage differs')
        if conditions is not None and conditions['schema']=='scienceutopia.native-world-conditions.v2':
            native_capacity_conditions_proof(state,conditions)
        kernel=NativeScienceKernel(spec,checkpoint=state['native_system'])
        if kernel.design_history:raise ValueError('fresh evaluation unexpectedly migrated its design')
        events=state['native_system']['events']
        if events[:len(previous_events)]!=previous_events:raise ValueError('native event prefix changed')
        elapsed=state['portable']['llm_call_stats'].get('elapsed_seconds',0.)
        if elapsed<previous_elapsed:raise ValueError('native inference duration counter rewound')
        if i==0:
            if events or state['native_system']['last_year']!=0 or state['portable']['response_cache_count']!=0:
                raise ValueError('fresh initial checkpoint contains preexisting results')
            initial=state
        else:
            counts.append(state['portable']['response_cache_count'])
            annual.append({'year':i,'checkpoint_sha256':file_sha256(path),
                'llm_call_stats':state['portable']['llm_call_stats'],
                'interval_llm_elapsed_seconds':elapsed-previous_elapsed,
                'response_count':counts[-1]})
        previous_events=events;previous_elapsed=elapsed;last=state
    complete=evidence is not None
    if complete:
        if (last['year']!=years or Path(evidence['checkpoint_path']).resolve()!=paths[-1].resolve()
                or evidence['checkpoint_sha256']!=file_sha256(paths[-1])
                or evidence['seed']!=seed or evidence['run_id']!=cell.name
                or evidence['system_fingerprint']!=spec.fingerprint
                or evidence['event_stream_hash']!=last['native_system']['event_stream_hash']):
            raise ValueError('completed evidence differs from original terminal checkpoint')
    response=zero_http_response_proofs(cell,binding,counts,complete=complete,protocol={},
        classification=RESPONSE_ACTUAL,maximum_year=years)
    if response['wire_requests']>config['maximum_http_attempts']:
        raise ValueError('actual HTTP attempts exceeded the declared native budget')
    if any(int(y)>years for y in response['responses_by_physical_year']):
        raise ValueError('physical request exceeds the declared world horizon')
    code=code_proofs(cell,spec,last['native_system'],world,cell.name,complete=complete)
    attempts=code_attempt_proof(cell,spec,world)
    if attempts is not None:code['attempt_journal']=attempts
    proof={'status':'complete' if complete else 'partial-or-technical-failure','seed':seed,'years':years,
        'through_committed_year':last['year'],'initial_identity':physical_initial_identity(initial),
        'response_proof':response,'code_proof':code,'annual_checkpoints':annual,
        'measurement':checkpoint_measurements(paths[-1],cell.name,spec.fingerprint) if complete else None,
        'checkpoint_sha256':file_sha256(paths[-1]),'new_model_calls':0,'new_code_executions':0}
    if conditions is not None:
        proof['world_conditions_proof']=initial_world_conditions_proof(initial,conditions,seed)
    if complete:
        authors=[a for a in initial['ecosystem_data']['agents'] if a['can_author']]
        if len(authors)!=5:raise ValueError('actual original population is not five researchers')
        code_path=cell/'code-contexts.jsonl'
        rows=[validate_record(json.loads(line)) for line in code_path.read_text().splitlines()] if code_path.exists() else []
        proof['native_counts']=domain_proofs(last,NativeScienceKernel(spec,checkpoint=last['native_system']),rows)
        proof['context_input_proof']=context_input_proofs(cell,last)
    return proof
