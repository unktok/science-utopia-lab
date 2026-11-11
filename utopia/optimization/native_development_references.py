"""Common same-study developer observations, not invented or fallback policies."""
from .blackbox import Observation,Suggestion
from .loss import evaluate_loss,validate_loss_spec,loss_spec_sha256
from .native_discrete_policy import verify_native_observation
from .native_numeric_designer import checked
from utopia.system.design_patch import clone,digest

SCHEMA='scienceutopia.native-development-references.v1'


def build_context(pairs,*,world,seeds,loss_spec):
    body={'schema':SCHEMA,'world':clone(world),'seeds':list(seeds),'original_loss_spec':clone(loss_spec),
        'pairs':clone(pairs),'scope':'Declared common developer observations; receipt validation is not an independent full raw audit.',
        'new_model_calls':0,'new_native_worlds':0,'baseline_fallback':False}
    body['content_sha256']=digest(body)
    return validate_context(body,target_world=world,target_seeds=seeds)


def validate_context(context,*,target_world=None,target_seeds=None):
    checked(context)
    if (context.get('schema')!=SCHEMA or not context.get('pairs')
            or context.get('new_model_calls')!=0 or context.get('new_native_worlds')!=0
            or context.get('baseline_fallback') is not False):raise ValueError('explicit immutable development references required')
    if target_world is not None and context['world']!=target_world:raise ValueError('development reference world differs')
    if target_seeds is not None and context['seeds']!=list(target_seeds):raise ValueError('development reference seeds differ')
    validate_loss_spec(context['original_loss_spec']);seen=set()
    for pair in context['pairs']:
        suggestion=Suggestion.from_dict(pair['suggestion']);observation=Observation.from_dict(pair['observation'])
        if suggestion.to_dict()!=pair['suggestion'] or observation.to_dict()!=pair['observation']:
            raise ValueError('canonical native reference pairs required without journal envelopes')
        if suggestion.suggestion_id in seen:raise ValueError('duplicate developer reference identity')
        seen.add(suggestion.suggestion_id);m=observation.metadata
        evaluated=evaluate_loss(context['original_loss_spec'],m['measurements'])
        if (observation.status!='complete' or observation.suggestion_id!=suggestion.suggestion_id
                or observation.candidate!=suggestion.candidate or m.get('technical_failures')
                or evaluated['status']!='complete' or evaluated['loss']!=observation.loss
                or evaluated!=m['loss_evaluation']
                or m['loss_spec_sha256']!=loss_spec_sha256(context['original_loss_spec'])):
            raise ValueError('complete literal native developer reference required')
        contract=context['world'].get('measurement_adapter_contract')
        if contract is not None and any(row.get('measurement_adapter_contract_sha256')!=digest(contract) for row in m['measurements']):
            raise ValueError('developer reference measurement contract differs')
        verify_native_observation(observation,context['world'],context['seeds'])
        if 'world_conditions' in context['world']:
            from utopia.runtime.checkpointing import read_portable_checkpoint
            for run in m['runs']:
                state=read_portable_checkpoint(run['checkpoint_path'])
                if state['portable']['contract']['binding']['science_config'].get('world_conditions')!=context['world']['world_conditions']:
                    raise ValueError('developer reference native world conditions differ')
    return clone(context)


def objective_view(context,loss_spec):
    """Only the declared arithmetic changes; original observations stay exact."""
    validate_loss_spec(loss_spec);pairs=[];summary=[]
    for pair in context['pairs']:
        original=pair['observation'];m=clone(original['metadata']);evaluated=evaluate_loss(loss_spec,m['measurements'])
        if evaluated['status']!='complete':raise ValueError('common developer reference objective is unavailable')
        m.update(loss_evaluation=evaluated,loss_spec_sha256=loss_spec_sha256(loss_spec),
            development_reference={'context_sha256':context['content_sha256'],
                'original_observation_sha256':digest(original),'original_loss':original['loss'],
                'not_a_new_candidate_or_world':True})
        observation={**clone(original),'observation_id':'developer-reference-rescore-'+digest({
            'context':context['content_sha256'],'original':original['observation_id'],'loss_spec':loss_spec_sha256(loss_spec)}),
            'loss':evaluated['loss'],'metadata':m}
        pairs.append({'suggestion':clone(pair['suggestion']),'observation':observation})
        summary.append({'reference':pair['suggestion']['suggestion_id'],'loss':evaluated['loss'],
            'system_fingerprint':m['system_fingerprint'],'metrics':[clone(v['metrics']) for v in m['measurements']]})
    return {'observations':pairs,'context':{'context_sha256':context['content_sha256'],'summary':summary,
        'baseline_fallback':False,'scope':'Common measured developer policies; final selection still requires an explicit submitted candidate.'}}
