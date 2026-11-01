"""Executable open-domain/process/tensor composition on the original world.

These are transparent developer examples, NOT a catalogue limiting generated
institutions and NOT evidence of discovery. All source remains sandboxed.
"""
from dataclasses import replace

from . import AgentTypeSpec, ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .code_mechanisms import CODE_SCHEMA
from .native_activity_contracts import activity_world_system
from .native_kernel import WORLD_ARTIFACT
from .native_open_domain import add_domain_action_receiver
from .native_process import CONTROL, compile_dependencies, controlled_activity
from .native_tensor_examples import tensor_selection_system
from .tensor_program import IMPLEMENTATION, SCHEMA


SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    year = context['period']
    old = world.get('open_domain', {}).get('actors', {}).get('cooperative')
    index = context['state'].get('iteration', 0) if context['state'].get('year') == year else 0
    authors = [a['id'] for a in world['ecosystem']['agents'] if a['can_author']]
    commands = []
    def emit(name, action, payload, actor='cooperative'):
        commands.append({'payload': {'schema':'native-domain-command-v1',
            'command_id': str(year) + '-' + str(index) + '-' + name,
            'actor_id':actor, 'action':action, 'payload':payload}})
    if old is None and index == 0:
        emit('found', 'actor.create', {'id':'cooperative', 'type':'open-cooperative',
            'roles':['open-planner'], 'state':{'rounds':0}}, '$mechanism')
    revision = (old['revision'] if old else 0) + index
    emit('remember', 'actor.update', {'id':'cooperative','expected_revision':revision,
        'roles':['open-planner'],'state':{'rounds':revision + 1, 'last_year':year}})
    artifact = 'open-record-' + str(year) + '-' + str(index)
    emit('record', 'artifact.create', {'id':artifact,'type':'open-protocol-record',
        'owner_actor':'cooperative','content':{'proposal':'OPEN_V7 cooperative replication', 'round':revision + 1},
        'actor_ids':['cooperative',authors[index % len(authors)]], 'artifact_ids':[],
        'native_paper_ids':[p['id'] for p in world['papers']['papers'][:1]]})
    emit('act', 'native.context', {'actor_ids':[authors[index % len(authors)]],
        'content':{'proposal':'OPEN_V7 cooperative replication', 'iteration':index}, 'artifact_ids':[artifact]})
    if index == 0:
        emit('project', 'native.project', {'assignment':{
            'actor_id':authors[0], 'direction':{'topic':'Cooperative replication', 'focus_areas':['replication'],
            'years':1,'keywords':['replication'],'related_topics':[]},
            'detailed_focus':'OPEN_V7 cooperative replication project', 'reason':'custom actor initiative',
            'project_start_year':year,'project_end_year':year}})
    return {'outputs':{'commands':commands}, 'state':{'year':year, 'iteration':index + 1}}
'''


def open_native_system(image_id, *, source=SOURCE, repetitions=2):
    """Original typed science plus arbitrary source, entities and recurrent policy.

    `source` is literal executable data passed to the pinned Docker executor.
    The dependency compiler preserves actual data edges; no successful scientific
    activities are fabricated when adding the new process.
    """
    base = tensor_selection_system(activity_world_system(), image_id=image_id)
    base = replace(base, agent_types=(*base.agent_types, AgentTypeSpec('open-cooperative', ('open-planner',))),
        artifact_types=(*base.artifact_types, ArtifactTypeSpec('open-protocol-record'),
            ArtifactTypeSpec('open-action-protocol'), ArtifactTypeSpec(CONTROL)))
    node = MechanismSpec('open-source', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('commands', ChannelKind.ARTIFACT, 'open-action-protocol'),),
        parameters={'runtime_image_id':image_id, 'code_artifact':{'schema':CODE_SCHEMA,
            'label':'Developer open-composition seed; later authorship tracked separately', 'source':source,
            'inputs':{'world':{'type':'object'}},'outputs':{'commands':{'type':'object'}}, 'state_schema':{'type':'object'}}})
    node = controlled_activity(node, count=repetitions, limit=4)
    base = replace(base, mechanisms=(*base.mechanisms,node), schedules=(*base.schedules, ScheduleSpec('open-source',10)),
        connections=(*base.connections, ConnectionSpec('world.open','world','open-source','world',ChannelKind.ARTIFACT)))
    base = add_domain_action_receiver(base, source='open-source', source_port='commands',
        capabilities={'bootstrap':['actor.create'], 'roles':{'open-planner':[
            'actor.update','artifact.create','native.context','native.project']}})
    def op(name, operation, *args, **attrs):
        return {'id':name, 'op':operation, 'args':list(args), 'attrs':attrs}
    program = {'schema':SCHEMA, 'inputs':{'incoming':[-1]},
        'parameters':{'threshold':.5, 'memory_gain':.001, 'write_logits':[2.,-1.],
            'query':[1.], 'keys':[[1.],[0.]]}, 'state':{'slots':[[0.],[0.]]},
        'nodes':[op('address','choose','parameter:write_logits'),
            op('remembered','attention','parameter:query','parameter:keys','state:slots'),
            op('penalty','mul','remembered','parameter:memory_gain'),
            op('margin','sub','input:incoming','parameter:threshold'),
            op('adjusted','sub','margin','penalty'), op('actions','gate','adjusted'),
            op('count','sum','input:incoming'),op('vector','reshape','count',shape=[1]),
            op('next-memory','memory_write','state:slots','address','vector')],
        'outputs':{'actions':'actions'},'updates':{'slots':'next-memory'}}
    protocol='native-tensor-decision-frame'
    router=MechanismSpec('open-memory-router',MechanismFamily.CUSTOM,IMPLEMENTATION,
        inputs=(PortSpec('signal',ChannelKind.ARTIFACT,protocol),),
        outputs=(PortSpec('actions',ChannelKind.ARTIFACT,protocol),),
        parameters={'program':program,'input_bindings':{'incoming':{'port':'signal','path':'/values'}}})
    base=replace(base,mechanisms=(*base.mechanisms,router),schedules=(*base.schedules,ScheduleSpec(router.mechanism_id,135)),
        connections=(*(e for e in base.connections if not (e.target_mechanism=='world.selection' and e.target_port=='accept')),
            ConnectionSpec('addressed-selection','accept',router.mechanism_id,'signal',ChannelKind.ARTIFACT),
            ConnectionSpec(router.mechanism_id,'actions','world.selection','accept',ChannelKind.ARTIFACT)))
    # All dependencies are explicit data. Preserve the original serial links in
    # this example; callers may detach/rewrite them with compile_dependencies.
    dependencies={n.mechanism_id:[] for n in base.mechanisms}
    dependencies['open-domain-actions']=['open-source']
    return compile_dependencies(base,dependencies)


def joint_engineering_loss():
    """Illustrative count proxy, NOT a claim about desirable science policy."""
    return {'schema':'scienceutopia.loss-spec.v1','id':'open-native-v7-engineering', 'version':'1',
        'status':'engineering-only','optimization_seed_role':'development','direction':'minimize',
        'per_run':{'intercept':0.,'terms':[
            {'metric_id':'native.accepted_decisions','slice_id':None,'coefficient':-1.},
            {'metric_id':'native.institutional_context_deliveries','slice_id':None,'coefficient':-.1}]},
        'across_seeds':{'aggregation':'mean_plus_population_sd','dispersion_weight':0.,'minimum_valid_runs':1}}
