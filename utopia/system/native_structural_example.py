"""Developer-authored structural QA seed, NOT LLM discovery or a policy menu.

Two arbitrary Python nodes introduce an agenda protocol and translate it into
native actions. The original scientific phases remain intact. Generated designs
may replace any of this code, protocol or graph via the unrestricted patch API.
"""
from dataclasses import replace

from . import (AgentTypeSpec, ArtifactTypeSpec, ChannelKind, ConnectionSpec,
               MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec)
from .code_mechanisms import CODE_SCHEMA
from .design_patch import apply_design_patch
from .native_kernel import WORLD_ARTIFACT
from .native_open_domain import STATE_ARTIFACT, add_domain_action_receiver
from .native_process import compile_dependencies
from .native_structural_authoring import explicit_graph_patch

AGENDA = 'research-agenda-v8'
COMMANDS = 'institution-command-v8'
MARKER = 'STRUCTURAL_V8_PLAN'

PLANNER_SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    year = context['period']
    authors = [a['id'] for a in world['ecosystem']['agents'] if a['can_author'] and a['is_active']]
    assignments = [{'actor_id': actor, 'direction': {'topic':'Collaborative error analysis',
        'focus_areas':['replication'], 'years':1, 'keywords':['replication'], 'related_topics':[]},
        'detailed_focus':'STRUCTURAL_V8_PLAN collaborative error analysis',
        'reason':'authored agenda initiative', 'project_start_year':year, 'project_end_year':year}
        for actor in authors[:context['parameters']['assigned_authors']]]
    agenda = {'year':year, 'members':authors, 'assignments':assignments,
        'cooperative':world.get('open_domain', {}).get('actors', {}).get('agenda-board'),
        'native_paper_ids':[paper['id'] for paper in world['papers']['papers'][:1]]}
    return {'outputs':{'agenda':[{'payload':agenda}]},
        'state':{'years':context['state'].get('years', 0) + 1}}
'''

ADAPTER_SOURCE = '''def step(context):
    agenda = context['inputs']['agenda'][0]['payload']
    year, old = agenda['year'], agenda['cooperative']
    commands = []
    def emit(name, action, payload, principal='agenda-board'):
        commands.append({'payload':{'schema':'native-domain-command-v1',
            'command_id':str(year) + '-' + name, 'actor_id':principal, 'action':action, 'payload':payload}})
    if old is None:
        emit('found','actor.create',{'id':'agenda-board','type':'agenda-cooperative-v8',
            'roles':['agenda-curator-v8'],'state':{'cycles':0}},'$mechanism')
    revision = old['revision'] if old else 0
    emit('remember','actor.update',{'id':'agenda-board','expected_revision':revision,
        'roles':['agenda-curator-v8'],'state':{'cycles':revision + 1,'last_year':year}})
    record = 'agenda-record-' + str(year)
    emit('record','artifact.create',{'id':record,'type':'agenda-record-v8','owner_actor':'agenda-board',
        'content':{'assignments':agenda['assignments']}, 'actor_ids':['agenda-board'] + agenda['members'],
        'artifact_ids':[], 'native_paper_ids':agenda['native_paper_ids']})
    if agenda['members']:
        emit('context','native.context',{'actor_ids':agenda['members'],
            'content':{'proposal':'STRUCTURAL_V8_PLAN collaborative error analysis'},'artifact_ids':[record]})
    for index, assignment in enumerate(agenda['assignments']):
        emit('project-' + str(index),'native.project',{'assignment':assignment})
    return {'outputs':{'commands':commands}, 'state':{'last_year':year}}
'''

AGENDA_SCHEMA = {'type':'object', 'required':['year','members','assignments','cooperative','native_paper_ids'],
    'additionalProperties':False, 'properties':{
        'year':{'type':'integer'}, 'members':{'type':'array','items':{'type':'string'}},
        'assignments':{'type':'array','items':{'type':'object'}},
        'cooperative':{'type':['object','null']},
        'native_paper_ids':{'type':'array','items':{'type':'string'}}}}


def structural_agenda_patch(parent, image_id, *, planner_source=PLANNER_SOURCE,
                            adapter_source=ADAPTER_SOURCE, assigned_authors=1):
    """Replace the old open-source region with a complete three-node institution.

    The example explicitly removes every old incident edge, supplies all source,
    schemas, capabilities and new wires, then asks the dependency compiler ONLY
    for topological schedules. It does not select a scientific optimum.
    """
    if type(assigned_authors) is not int or assigned_authors < 0:
        raise ValueError('assigned_authors must be a nonnegative integer')
    removed = {'open-source','open-domain-actions'}
    present = {node.mechanism_id for node in parent.mechanisms}
    if not removed <= present:
        raise ValueError('developer example requires the v7 open-source region')
    def code(identity, input_port, output_port, input_type, output_type, source, input_schema, output_schema, **params):
        return MechanismSpec(identity,MechanismFamily.CUSTOM,'code.python.v1',
            inputs=(PortSpec(input_port,ChannelKind.ARTIFACT,input_type),),
            outputs=(PortSpec(output_port,ChannelKind.ARTIFACT,output_type),),
            parameters={'runtime_image_id':image_id,'code_artifact':{'schema':CODE_SCHEMA,
                'label':'Developer structural software QA; not generated research', 'source':source,
                'inputs':{input_port:input_schema}, 'outputs':{output_port:output_schema},
                'state_schema':{'type':'object'}}, **params})
    planner=code('agenda-planner','world','agenda',WORLD_ARTIFACT,AGENDA,
        planner_source,{'type':'object'},AGENDA_SCHEMA,assigned_authors=assigned_authors)
    adapter=code('agenda-commands','agenda','commands',AGENDA,COMMANDS,
        adapter_source,AGENDA_SCHEMA,{'type':'object'})
    base=replace(parent,
        mechanisms=tuple(n for n in parent.mechanisms if n.mechanism_id not in removed) + (planner,adapter),
        connections=tuple(e for e in parent.connections if e.source_mechanism not in removed and e.target_mechanism not in removed),
        schedules=tuple(s for s in parent.schedules if s.mechanism_id not in removed) + (
            ScheduleSpec(planner.mechanism_id,10),ScheduleSpec(adapter.mechanism_id,20)),
        agent_types=(*parent.agent_types,AgentTypeSpec('agenda-cooperative-v8',('agenda-curator-v8',))),
        artifact_types=(*parent.artifact_types,ArtifactTypeSpec(AGENDA),ArtifactTypeSpec(COMMANDS),
            ArtifactTypeSpec('agenda-record-v8')))
    base=add_domain_action_receiver(base,source=adapter.mechanism_id,source_port='commands',receiver='agenda-effects',
        capabilities={'bootstrap':['actor.create'],'roles':{'agenda-curator-v8':[
            'actor.update','artifact.create','native.context','native.project']}})
    # Explicit actual state-effect dependency. No source or native action is
    # inferred by the ordering compiler; the native phase tolerates extra inputs.
    base=replace(base,mechanisms=tuple(replace(node,inputs=(*node.inputs,
        PortSpec('agenda-applied',ChannelKind.ARTIFACT,STATE_ARTIFACT)))
        if node.mechanism_id=='world.research' else node for node in base.mechanisms),
        connections=(*base.connections,
            ConnectionSpec('world.open','world',planner.mechanism_id,'world',ChannelKind.ARTIFACT),
            ConnectionSpec(planner.mechanism_id,'agenda',adapter.mechanism_id,'agenda',ChannelKind.ARTIFACT),
            ConnectionSpec('agenda-effects','domain','world.research','agenda-applied',ChannelKind.ARTIFACT)))
    ordered=compile_dependencies(base,{node.mechanism_id:[] for node in base.mechanisms})
    original=parent.to_dict()
    final=ordered.to_dict()
    patch=explicit_graph_patch(parent,remove_nodes=sorted(removed),
        put_nodes=[node for node in final['mechanisms'] if node not in original['mechanisms']],
        disconnect=[edge for edge in original['connections'] if edge not in final['connections']],
        connect=[edge for edge in final['connections'] if edge not in original['connections']],
        schedules=final['schedules'],agent_types=final['agent_types'],artifact_types=final['artifact_types'],metadata=final['metadata'],
        rationale='Explicit developer-authored structural agenda, original science phases preserved')
    assert apply_design_patch(parent,patch).fingerprint==ordered.fingerprint
    return patch
