"""Pure prospective V2 study specification; no model calls or dispatch."""
from pathlib import Path
from copy import deepcopy

from utopia.optimization.native_benchmark_controls import control_systems,objective_specs,selection_control,without_review
from utopia.optimization.native_design_space import make_design_space
from utopia.optimization.native_authoring_recovery_v44 import MAX_STEPS
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_designer_decoding_v24 import decoding_contracts
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_search_v14 import validate_provider_binding
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-design-freedom-study.v2'
PROTOCOL='research/protocols/campaigns/native-design-freedom-v2.md'
CLASSIFICATION='actual-native-design-freedom-study-v2'
OBJECTIVES=('throughput','selective')
METHODS=('parameters','code-fixed-graph','code-and-graph','technical-only','random')
SEARCH_SEEDS=(42,1031,2063)
EVALUATION_SEEDS=(31001,31013,31019,31033,31039)
GENERATIONS=4


def build_plan(*,source,scientist,designer,runtime_seed,backend,seed_usage_sha256=None):
    validate_provider_binding(scientist);validate_designer_binding(designer,scientist_binding=scientist)
    if not isinstance(source,str) or len(source)!=40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('exact source pin required')
    if (backend.get('model')!=designer['model'] or backend.get('model_digest')!=designer['model_digest']
            or not isinstance(backend.get('ollama_version'),str) or not backend['ollama_version']):
        raise ValueError('designer backend/model metadata required')
    references=control_systems(scientist['image_id']);anchor=references['open-seed']
    references['open-no-review-reject-all']=without_review(selection_control(anchor,rule='reject-all'))
    losses=objective_specs();experiment={'protocol':PROTOCOL,'role':'development-matched-search'}
    world={**deepcopy(scientist),'source_commit':source,'years':2,
        'runtime_seed_binding':deepcopy(runtime_seed),'experiment':experiment,'classification':CLASSIFICATION}
    bindings={};assignments={}
    # This order is data, rotated per generation/run, never outcome-adapted.
    order=[f'{obj}:{method}' for method in METHODS for obj in OBJECTIVES]
    for run_index,search_seed in enumerate(SEARCH_SEEDS):
        current={}
        for arm in order:
            objective,method=arm.split(':')
            domain='parameters' if method=='random' else 'code-and-graph' if method=='technical-only' else method
            strategy='uniform-parameter' if method=='random' else 'local-bounded-author'
            current[arm]={'initial_system':anchor.to_dict(),'loss_spec':deepcopy(losses[objective]),
                'world':deepcopy(world),'seeds':[42],'strategies':{strategy:{
                    'kind':'uniform-parameter' if method=='random' else 'literal-local-LLM-system-proposal',
                    'protocol':PROTOCOL,'source_commit':source}},
                'mode':'blackbox','seed':search_seed,'learning_rate':.1,'strategy_learning_rate':.1,
                'strategy_baseline':0.,'exploration':.1,
                'proposal_feedback':'technical-only' if method=='technical-only' else 'matched-loss',
                'design_space':make_design_space(anchor,domain)}
            assignments[arm]={'objective':objective,'method':method,'strategy':strategy,'domain':domain}
        bindings[f'run-{run_index:02d}']=current
    schedules={}
    for r in range(len(SEARCH_SEEDS)):
        schedule=[]
        for generation in range(GENERATIONS):
            offset=(r+generation)%len(order)
            schedule.extend({'arm':arm,'generation':generation} for arm in order[offset:]+order[:offset])
        schedules[f'run-{r:02d}']=schedule
    plan={'schema':SCHEMA,'source_commit':source,'protocol':PROTOCOL,
        'protocol_sha256':file_sha256(ROOT/PROTOCOL),'classification':CLASSIFICATION,
        'scientist':deepcopy(scientist),'designer':deepcopy(designer),'backend':deepcopy(backend),
        'runtime_seed_binding':deepcopy(runtime_seed),'initial_system':anchor.to_dict(),
        'world':world,'experiment':experiment,'losses':losses,'objectives':list(OBJECTIVES),
        'methods':list(METHODS),'assignments':assignments,'campaign_bindings':bindings,
        'schedules':schedules,'generations':GENERATIONS,
        'reference_systems':{k:v.to_dict() for k,v in references.items()},
        'evaluation_seed_usage_sha256':seed_usage_sha256,
        'evaluation':{'seeds':list(EVALUATION_SEEDS),'years':[2],
            'extended':[{'seed':EVALUATION_SEEDS[0],'years':4}],
            'maximum_selected_labels':10,'maximum_reference_labels':9,'maximum_physical_worlds':114,
            'freeze_selection_before_any_evaluation':True,'same_policy_shared_explicitly':True,
            'policy_seed_projection':'Replace only initial_state.seed for each evaluated environment; preserve immutable original and policy hash.'},
        'budget':{'search_slots':120,'reference_slots':9,'maximum_search_and_reference_worlds':129,
            'LLM_candidate_slots':96,'maximum_author_POSTs':96*MAX_STEPS,
            'maximum_calibration_POSTs':120,'calibration_per_run_POSTs':40,
            'maximum_total_worlds_including_evaluation':243,'refill':False,
            'scientist_HTTP_attempts_per_two_year_world':512,'scientist_HTTP_attempts_per_four_year_world':1024},
        'designer_settings':{'max_steps':MAX_STEPS,'max_tokens':8192,'conversation_profile':BOUNDED_AUTHORING,
            'decoding':decoding_contracts('staged-v15',conversation_profile=BOUNDED_AUTHORING)},
        'selection':{'include_common_initial_reference':True,'rule':'minimum declared loss only',
            'ties':'retain all exact tied IDs; physically evaluate first in frozen chronology',
            'pooling':'all groups also receive a separate pooled loss-only ranking; arm labels are not merit vetoes'},
        'claims':{'method_superiority_required':False,'different_winners_required':False,
            'scientific_quality_established_by_proxy':False,'world_seed_replications_in_search':1,
            'fresh_search_runs':3,'LLM_source_probability_known':False}}
    plan['content_sha256']=digest(plan)
    return plan


def policy_identity(system):
    """Explicitly separate the fixed policy from evaluation environment seed."""
    data=deepcopy(system)
    data['initial_state'].pop('seed',None)
    return digest(data)


def evaluation_design(system,seed):
    from utopia.system import SystemSpec,validate_system_spec
    if type(seed) is not int or seed not in EVALUATION_SEEDS:
        raise ValueError('explicit declared nonhistorical evaluation seed required')
    data=deepcopy(system);data['initial_state']['seed']=seed
    result=SystemSpec.from_dict(data);validate_system_spec(result).require_valid()
    if policy_identity(result.to_dict())!=policy_identity(system):
        raise ValueError('evaluation projection changes scientific policy')
    return result
