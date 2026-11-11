"""Observed producer values versus direct tensor declarations; no program execution."""
from pathlib import Path

from utopia.optimization.native_contract_notices import downstream_tensor_contracts
from utopia.system.design_patch import clone,digest
from utopia.system.tensor_program import tensor_input_from_payload,validate_tensor_input

SCOPE='recorded-direct-tensor-inputs-v1'
BANK_OPTION='post_edit_tensor_delivery_scope'
SCHEMA='scienceutopia.recorded-tensor-delivery.v1'
NOTE=('Recorded component output frames are additionally compared with the current '
    'direct tensor consumers using the native payload conversion and input-shape checks. '
    'No tensor body, generated source or native world is executed for that comparison. '
    'A compatible recorded input does not certify downstream operations, other '
    'producers, schedules, future states or native execution. These diagnostics '
    'never change source, loss or permission to finish. A changed consumer makes '
    'an older document-bound diagnostic stale.')


def source_hashes():
    from utopia.utils.data_utils import file_sha256
    from utopia.system import tensor_program
    from utopia.optimization import native_contract_notices
    return {p.name:file_sha256(p) for p in (Path(__file__),Path(tensor_program.__file__),Path(native_contract_notices.__file__))}


def diagnose(document,producer_id,result,*,limit=16):
    """Finite literal observations, not inferred code output or graph validity."""
    if type(limit) is not int or not 1<=limit<=64:raise ValueError('bounded delivery diagnostic rows required')
    report={'schema':SCHEMA,'document_sha256':digest(document),'producer_id':producer_id,
        'result_sha256':digest(result),'rows':[],'omitted_rows':0,
        'changes_validity':False,'authored_value_changed_by_host':False,
        'new_model_calls':0,'new_native_worlds':0,'new_source_executions':0,'new_tensor_body_executions':0,
        'scope':'Current literal direct-edge tensor input declarations versus one recorded component result. '
            'No whole-world success, consumer operation/state/record alignment, timing or causal effect is inferred.'}
    nodes=document.get('mechanisms',[]) if isinstance(document,dict) else []
    edges=document.get('connections',[]) if isinstance(document,dict) else []
    nodes=nodes if isinstance(nodes,list) else [];edges=edges if isinstance(edges,list) else []
    owners=[i for i,n in enumerate(nodes) if isinstance(n,dict) and n.get('mechanism_id')==producer_id]
    if len(owners)!=1:
        report['resolution']='no-unique-literal-producer';return report
    # Full declarations remain bounded and are not copied into prompt diagnostics.
    notice=downstream_tensor_contracts(document,owners[0],limit=64,max_bytes=1_048_576)
    report['declaration_notices_complete']=notice['complete']
    report['omitted_declaration_notices']=notice['omitted_count']
    rows=[]
    for n in notice['notices']:
        declaration=n.get('declaration')
        if declaration is None:
            rows.append({'connection_path':n['connection_path'],'status':'not-assessed',
                'reason':'complete-declaration-not-in-notice','declaration_sha256':n['declaration_sha256']});continue
        edge=declaration['connection'];incoming=[e for e in edges if isinstance(e,dict)
            and e.get('target_mechanism')==edge['target_mechanism'] and e.get('target_port')==edge['target_port']]
        base={'connection_path':n['connection_path'],'consumer_filename':n['consumer_filename'],
            'declaration_sha256':n['declaration_sha256'],'source_port':edge['source_port'],
            'target_mechanism':edge['target_mechanism'],'target_port':edge['target_port']}
        if len(incoming)!=1 or type(edge.get('latency',0)) is not int or edge.get('latency',0)!=0:
            rows.append({**base,'status':'not-assessed','reason':'fan-in-or-delayed-delivery-not-reconstructed'});continue
        outputs=result.get('outputs') if isinstance(result,dict) else None
        frames=outputs.get(edge['source_port'],[]) if isinstance(outputs,dict) else None
        if not isinstance(frames,list) or len(frames)!=1 or not isinstance(frames[0],dict) or 'payload' not in frames[0]:
            rows.append({**base,'status':'not-assessed','reason':'one-recorded-payload-frame-required',
                'recorded_frames':len(frames) if isinstance(frames,list) else None});continue
        bound=declaration['bound_tensor_inputs']
        if not bound:rows.append({**base,'status':'not-assessed','reason':'no-declared-binding-on-port'})
        for binding in bound:
            row={**base,'tensor_input':binding['tensor_input'],'literal_binding':clone(binding['literal_binding']),
                'declared_shape':clone(binding.get('declared_shape')),'observed_shape':None,'status':'not-assessed'}
            shape=binding.get('declared_shape');path=binding['literal_binding'].get('path')
            if (not isinstance(shape,list) or len(shape)>3 or shape.count(-1)>1
                    or any(type(d) is not int or d==0 or d < -1 or d>256 for d in shape) or not isinstance(path,str)):
                row['reason']='invalid-or-missing-literal-shape-or-path'
            else:
                try:
                    value=tensor_input_from_payload(frames[0]['payload'],path,shape)
                    row['observed_shape']=list(value.shape)
                    validate_tensor_input(value,binding['tensor_input'],shape)
                    row['status']='compatible-recorded-input'
                except (ValueError,TypeError,KeyError,IndexError,RuntimeError) as error:
                    row.update(status='incompatible-recorded-input',error_type=type(error).__name__,
                        error_excerpt=str(error)[:256],error_excerpt_is_partial=len(str(error))>256)
            rows.append(row)
    report['rows']=rows[:limit];report['omitted_rows']=max(0,len(rows)-limit)
    return report
