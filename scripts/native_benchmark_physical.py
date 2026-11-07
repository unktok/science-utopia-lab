"""Seed/horizon-explicit native physical audit; no model or source execution.

The historical fixed-seed auditors are left unchanged. Reuse their strict
response/code/domain primitives, with caller-declared environment conditions.
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


def physical_proof(cell,spec,*,world,seed,years,evidence=None):
    cell=Path(cell).resolve();cache=cell/'replies/responses.sqlite'
    if not cache.is_file():raise ValueError('physical proof requires the actual response binding')
    with sqlite3.connect(cache.as_uri()+'?mode=ro',uri=True) as db:
        records=db.execute('SELECT binding FROM metadata').fetchall()
    if len(records)!=1:raise ValueError('one immutable native response binding required')
    binding=json.loads(records[0][0]);config=binding['science_config']
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
    if not paths:raise ValueError('actual native initial checkpoint required')
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
    proof={'status':'complete' if complete else 'partial-or-technical-failure','seed':seed,'years':years,
        'through_committed_year':last['year'],'initial_identity':physical_initial_identity(initial),
        'response_proof':response,'code_proof':code,'annual_checkpoints':annual,
        'measurement':checkpoint_measurements(paths[-1],cell.name,spec.fingerprint) if complete else None,
        'checkpoint_sha256':file_sha256(paths[-1]),'new_model_calls':0,'new_code_executions':0}
    if complete:
        authors=[a for a in initial['ecosystem_data']['agents'] if a['can_author']]
        if len(authors)!=5:raise ValueError('actual original population is not five researchers')
        code_path=cell/'code-contexts.jsonl'
        rows=[validate_record(json.loads(line)) for line in code_path.read_text().splitlines()] if code_path.exists() else []
        proof['native_counts']=domain_proofs(last,NativeScienceKernel(spec,checkpoint=last['native_system']),rows)
        proof['context_input_proof']=context_input_proofs(cell,last)
    return proof
