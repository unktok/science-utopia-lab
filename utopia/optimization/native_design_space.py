"""Nested benchmark design freedoms, enforced before native evaluation.

These are explicit experimental search domains, not novelty/fairness/merit
policies. No proposal is repaired, projected or relabeled into the domain.
"""
import math

from utopia.system import SystemSpec, validate_system_spec
from utopia.system.design_patch import clone, digest, pointer

SCHEMA = 'scienceutopia.native-benchmark-design-space.v2'
KINDS = {'parameters', 'code-fixed-graph', 'code-and-graph'}


def _get(document, path):
    value = document
    for key in pointer(path):
        value = value[int(key)] if isinstance(value,list) else value[key]
    return value


def _set(document,path,value):
    tokens=pointer(path);parent=document
    for key in tokens[:-1]:
        parent=parent[int(key)] if isinstance(parent,list) else parent[key]
    key=tokens[-1];parent[int(key) if isinstance(parent,list) else key]=value


def source_paths(document):
    """Include literal process delegates without executing/importing them."""
    result=[]
    def visit(value,path):
        if isinstance(value,dict):
            if value.get('implementation')=='code.python.v1':
                _get(value,'/parameters/code_artifact/source')
                result.append(path+'/parameters/code_artifact/source')
            for k,v in value.items():
                visit(v,path+'/'+str(k).replace('~','~0').replace('/','~1'))
        elif isinstance(value,list):
            for i,v in enumerate(value):visit(v,path+'/'+str(i))
    visit(document,'')
    return result


def make_design_space(anchor,kind):
    if kind not in KINDS:raise ValueError('unknown declared benchmark design freedom')
    data=anchor.to_dict();index={n['mechanism_id']:i for i,n in enumerate(data['mechanisms'])}
    coordinates=[]
    for name,local,lo,hi,integer in [
        ('addressed-selection','/parameters/program/parameters/thresholds/0/0',0.,5.,False),
        ('addressed-selection','/parameters/program/parameters/thresholds/1/0',0.,5.,False),
        ('addressed-selection','/parameters/program/parameters/bias',-4.,4.,False),
        ('addressed-selection','/parameters/program/parameters/memory_cost',0.,.1,False),
        ('open-memory-router','/parameters/program/parameters/threshold',0.,1.,False),
        ('open-source','/parameters/count',1.,4.,True)]:
        path='/mechanisms/'+str(index[name])+local
        _get(data,path)
        coordinates.append({'mechanism_id':name,'path':local,'lower':lo,'upper':hi,'integer':integer})
    contract={'schema':SCHEMA,'kind':kind,'anchor_sha256':digest(data),
        'numeric_coordinates':coordinates,
        'code_paths':source_paths(data),
        'scope':{'parameters':'Only these existing numeric coordinates; no source, schemas, nodes, wires or state edits.',
            'code-fixed-graph':'These numeric coordinates plus literal existing Python sources (including process delegates); all other fields and graph contracts fixed.',
            'code-and-graph':'Any valid SystemSpec code, mechanisms, wiring and process edits; experimental seed remains fixed.'}[kind],
        'violation_policy':'Technical null before world execution; never repair, project or refill.'}
    validate_design_space(anchor,contract)
    return contract


def validate_design_space(anchor,contract):
    fields={'schema','kind','anchor_sha256','numeric_coordinates','code_paths','scope','violation_policy'}
    allowed=(fields,fields|{'world_law_scope'})
    if (not isinstance(contract,dict) or set(contract) not in allowed
            or contract['schema']!=SCHEMA or contract['kind'] not in KINDS
            or contract['anchor_sha256']!=digest(anchor.to_dict())
            or not isinstance(contract['numeric_coordinates'],list) or not isinstance(contract['scope'],str)
            or not isinstance(contract['violation_policy'],str)
            or contract['code_paths']!=source_paths(anchor.to_dict())):
        raise ValueError('exact benchmark design-space/anchor contract required')
    if 'world_law_scope' in contract:
        from .native_fixed_production_domain import SCOPE,ROUTING_SCOPE,CATALOG_PLANNING_SCOPE,require_fixed_production
        from .native_workflow_domain_v4 import SCOPE as WORKFLOW_SCOPE, require_workflow_candidate
        if contract['world_law_scope'] == WORKFLOW_SCOPE:
            require_workflow_candidate(anchor,anchor)
        elif contract['world_law_scope'] in (SCOPE, ROUTING_SCOPE, CATALOG_PLANNING_SCOPE):
            require_fixed_production(anchor,anchor,scope=contract['world_law_scope'])
        else:
            raise ValueError('unknown explicit world-law scope')
    index={n.mechanism_id:i for i,n in enumerate(anchor.mechanisms)};seen=set()
    for c in contract['numeric_coordinates']:
        if (not isinstance(c,dict) or set(c)!={'mechanism_id','path','lower','upper','integer'}
                or c['mechanism_id'] not in index or type(c['integer']) is not bool
                or any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) for k in ('lower','upper'))
                or c['lower']>=c['upper'] or not c['path'].startswith('/parameters/')):
            raise ValueError('explicit finite existing numeric coordinate required')
        path='/mechanisms/'+str(index[c['mechanism_id']])+c['path']
        value=_get(anchor.to_dict(),path)
        if (path in seen or type(value) not in (int,float) or not math.isfinite(value)
                or not c['lower']<=value<=c['upper'] or c['integer'] and type(value) is not int
                or any(path.startswith(p+'/') or p.startswith(path+'/') or p==path for p in contract['code_paths'])):
            raise ValueError('coordinate overlaps source or is not an in-range numeric anchor')
        seen.add(path)
    return clone(contract)


def require_candidate_in_space(anchor,candidate,contract):
    validate_design_space(anchor,contract)
    validate_system_spec(candidate).require_valid()
    original,current=anchor.to_dict(),candidate.to_dict()
    if current['initial_state'].get('seed')!=original['initial_state'].get('seed'):
        raise ValueError('candidate changes the fixed experimental world seed')
    if 'world_law_scope' in contract:
        from .native_fixed_production_domain import require_fixed_production
        from .native_workflow_domain_v4 import SCOPE as WORKFLOW_SCOPE, require_workflow_candidate
        if contract['world_law_scope'] == WORKFLOW_SCOPE:
            require_workflow_candidate(anchor,candidate)
        else:
            require_fixed_production(anchor,candidate,scope=contract['world_law_scope'])
    if contract['kind']=='code-and-graph':return
    masked_original,masked_current=clone(original),clone(current)
    index={n.mechanism_id:i for i,n in enumerate(anchor.mechanisms)}
    try:
        for c in contract['numeric_coordinates']:
            path='/mechanisms/'+str(index[c['mechanism_id']])+c['path']
            value=_get(current,path)
            if (type(value) not in (int,float) or not math.isfinite(value)
                    or not c['lower']<=value<=c['upper'] or c['integer'] and type(value) is not int):
                raise ValueError('candidate numeric value outside the declared coordinate domain')
            _set(masked_original,path,None);_set(masked_current,path,None)
        if contract['kind']=='code-fixed-graph':
            for path in contract['code_paths']:
                if not isinstance(_get(current,path),str):raise ValueError('source must remain literal text')
                _set(masked_original,path,None);_set(masked_current,path,None)
    except (KeyError,IndexError,TypeError) as error:
        raise ValueError('candidate removes or reshapes a declared design-space field') from error
    if digest(masked_original)!=digest(masked_current):
        raise ValueError('candidate exceeds the explicitly declared '+contract['kind']+' design space')


def random_parameter_definition(request):
    """Uniform black-box coordinate baseline, not a code-invention method."""
    import random
    from utopia.system.design_patch import make_patch
    contract=request['design_space']
    if contract['kind']!='parameters':raise ValueError('uniform baseline needs the numeric domain')
    parent=SystemSpec.from_dict(request['parent_system'])
    index={n.mechanism_id:i for i,n in enumerate(parent.mechanisms)}
    rng=random.Random(request['rng_seed']);operations=[]
    for c in contract['numeric_coordinates']:
        value=(rng.randint(math.ceil(c['lower']),math.floor(c['upper'])) if c['integer'] else
            rng.uniform(c['lower'],c['upper']))
        operations.append({'op':'replace','path':'/mechanisms/'+str(index[c['mechanism_id']])+c['path'],
            'value':value})
    return {'base_patch':make_patch(parent,operations),'factors':[],'continuous':[],
        'provenance':{'author':'developer-declared-random-parameter-baseline',
            'method':'independent uniform numeric coordinates','seed':request['rng_seed']}}
