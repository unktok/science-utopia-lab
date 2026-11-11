"""History-dependent information institution in the original scientist world.

Developer-authored mechanistic controls, not automatic discoveries. Python
stays in the existing pinned networkless executor. No project/calendar edits.
"""
from dataclasses import replace

from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
                          MechanismSpec, PortSpec, ScheduleSpec, validate_system_spec)
from utopia.system.code_mechanisms import CODE_SCHEMA
from utopia.system.native_kernel import WORLD_ARTIFACT, add_context_receiver
from utopia.system.native_open_examples import open_native_system
from utopia.optimization.native_design_space import make_design_space, validate_design_space

NOOP = "def step(context):\n    return {'outputs': {'commands': []}, 'state': {}}\n"
PROTOCOL = 'native-research-history-dossier-v1'
SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    year = context['period']
    mode = context['parameters']['information_mode']
    limit = context['parameters']['max_records']
    agents = [a for a in world['ecosystem']['agents'] if a['can_author']]
    papers = [p for p in world['papers']['papers'] if p['year'] <= year]
    outputs = []
    for actor in agents:
        selected = []
        for paper in papers:
            ids = paper['author_id'] if isinstance(paper['author_id'], list) else [paper['author_id']]
            if mode == 'personal' and actor['id'] not in ids:
                continue
            selected.append({'paper_id':paper['id'], 'title':paper['title'],
                'year':paper['year'], 'topics':paper.get('topics', []), 'status':paper['status'],
                'reviews':[{'year':r.get('year'), 'score':r.get('score'), 'decision':r.get('decision')}
                           for r in paper.get('review_history', []) if r.get('year',year) <= year]})
        selected.sort(key=lambda p:(p['year'],p['paper_id']), reverse=True)
        selected = selected[:limit]
        outputs.append({'actor_ids':[actor['id']], 'payload':{
            'schema':'native-research-history-dossier-v1', 'observed_through_year':year,
            'record_scope':'own-history' if mode == 'personal' else 'society-history',
            'records':selected,
            'interpretation':'Recorded publication history, not verified scientific truth. '
                'Use it as evidence when considering your next research choices; no change is required.'}})
    return {'outputs':{'dossiers':outputs}, 'state':{'last_year':year, 'records_seen':len(papers)}}
'''

# A simple same-authority comparator, not an invented institution. The literal
# message is independent of the observation except for actual recipient IDs.
# Moving its receiver therefore does not also move its observation/producer.
INSTRUCTION_PROTOCOL = 'native-developer-static-instruction-v1'
INSTRUCTION_SOURCE = '''def step(context):
    outputs = []
    if context['period'] == context['parameters']['first_period']:
        world = context['inputs']['world'][0]['payload']
        for actor in world['ecosystem']['agents']:
            if actor['can_author']:
                outputs.append({'actor_ids':[actor['id']], 'payload':{
                    'schema':'native-developer-static-instruction-v1',
                    'instruction':context['parameters']['instruction']}})
    return {'outputs':{'messages':outputs}, 'state':{'last_period':context['period']}}
'''


def instruction_control(anchor, image_id, *, instruction, delivery_phase,
                        connected=True, first_period=1):
    """Add one literal message to original authors, with explicit delivery time.

    All variants retain the same producer, initial observation and code. Only
    the receiver schedule or delivery edge changes. No project/resource/paper
    effect is granted, and no interpretation of the instruction is implemented
    by the host. Off/on or early/late outcomes require fresh native evaluation;
    this builder does not measure them or claim a pure mediation estimand.
    """
    if (not isinstance(instruction, str) or not instruction.strip()
            or len(instruction.encode('utf-8')) > 8192):
        raise ValueError('explicit nonblank instruction of at most8192 UTF-8 bytes required')
    if type(connected) is not bool or type(first_period) is not int or first_period < 1:
        raise ValueError('explicit connection and positive first period required')
    validate_system_spec(anchor).require_valid()
    opening = [s.phase for s in anchor.schedules if s.mechanism_id == 'world.open']
    if len(opening) != 1:
        raise ValueError('one explicit native opening schedule required')
    producer_phase = opening[0] + 1
    # Native close is not the graph/year checkpoint: the existing history
    # office intentionally runs after it. Do not impose a new chronology law.
    if type(delivery_phase) is not int or delivery_phase <= producer_phase:
        raise ValueError('delivery must follow the opening producer')
    producer, receiver = 'developer-instruction-office', 'developer-instruction-receiver'
    if (any(n.mechanism_id in (producer, receiver) for n in anchor.mechanisms)
            or any(t.artifact_type_id == INSTRUCTION_PROTOCOL for t in anchor.artifact_types)):
        raise ValueError('fresh instruction control identities required')
    node = MechanismSpec(producer, MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('messages', ChannelKind.ARTIFACT, INSTRUCTION_PROTOCOL, required=False),),
        parameters={'runtime_image_id':image_id, 'instruction':instruction, 'first_period':first_period,
            'code_artifact':{'schema':CODE_SCHEMA,
                'label':'Developer static instruction comparator, not discovered institution',
                'source':INSTRUCTION_SOURCE, 'inputs':{'world':{'type':'object'}},
                'outputs':{'messages':{'type':'object'}}, 'state_schema':{'type':'object'}}})
    result = replace(anchor,
        artifact_types=(*anchor.artifact_types, ArtifactTypeSpec(INSTRUCTION_PROTOCOL)),
        mechanisms=(*anchor.mechanisms, node),
        schedules=(*anchor.schedules, ScheduleSpec(producer, producer_phase)),
        connections=(*anchor.connections, ConnectionSpec('world.open','world',producer,'world',ChannelKind.ARTIFACT)))
    result = add_context_receiver(result, source=producer, source_port='messages',
        receiver=receiver, phase=delivery_phase)
    if not connected:
        result = replace(result, connections=tuple(e for e in result.connections
            if e.target_mechanism != receiver))
    validate_system_spec(result).require_valid()
    return result


def information_system(image_id, *, condition='M1', seed=42):
    if condition not in ('M0', 'M1', 'M2', 'M3'):
        raise ValueError('explicit information intervention required')
    # Retain the original activity/tensor world but remove the old example's
    # direct project modification and unequal pre-planning context injection.
    base = open_native_system(image_id, source=NOOP, repetitions=1)
    data = base.to_dict(); data['initial_state']['seed'] = seed
    noop = next(n for n in data['mechanisms'] if n['mechanism_id']=='open-source')
    # An explicitly inert source emits no commands; declare that output as
    # optional on both the delegate and wrapper before any world is run.
    for outputs in (noop['outputs'], noop['parameters']['delegate']['outputs']):
        for port in outputs:
            if port['port_id']=='commands':
                port['required']=False
    receiver = next(n for n in data['mechanisms'] if n['mechanism_id']=='open-domain-actions')
    receiver['parameters']['capabilities']['roles']['open-planner'] = ['actor.update','artifact.create','native.context']
    from utopia.system import SystemSpec
    base = SystemSpec.from_dict(data)
    node = MechanismSpec('information-office', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('dossiers', ChannelKind.ARTIFACT, PROTOCOL),),
        parameters={'runtime_image_id':image_id, 'information_mode':'aggregate' if condition=='M2' else 'personal',
            'max_records':3, 'code_artifact':{'schema':CODE_SCHEMA,
                'label':'Developer history-dossier intervention, not discovered institution', 'source':SOURCE,
                'inputs':{'world':{'type':'object'}}, 'outputs':{'dossiers':{'type':'object'}},
                'state_schema':{'type':'object'}}})
    base = replace(base, artifact_types=(*base.artifact_types, ArtifactTypeSpec(PROTOCOL)),
        mechanisms=(*base.mechanisms,node), schedules=(*base.schedules,ScheduleSpec(node.mechanism_id,190)),
        connections=(*base.connections,ConnectionSpec('world.publication','world',node.mechanism_id,'world',ChannelKind.ARTIFACT)))
    base = add_context_receiver(base, source=node.mechanism_id, source_port='dossiers',
                                receiver='history-dossier-receiver', latency=1 if condition=='M3' else 0)
    if condition=='M0':
        # Same producer and compute budget, without information delivery.
        base = replace(base, connections=tuple(e for e in base.connections
                       if e.target_mechanism != 'history-dossier-receiver'))
    validate_system_spec(base).require_valid()
    return base


def information_design_space(anchor, kind, *, fixed_production=False):
    contract = make_design_space(anchor, kind)
    # Replace the old example's now-inert repetition coordinate with a value
    # the dossier source actually consumes. This is a new prospective domain.
    contract['numeric_coordinates'][-1] = {'mechanism_id':'information-office',
        'path':'/parameters/max_records', 'lower':0., 'upper':6., 'integer':True}
    if fixed_production:
        from utopia.optimization.native_fixed_production_domain import SCOPE,scope_description
        contract['world_law_scope']=SCOPE
        contract['scope']+=' '+scope_description(anchor)
    validate_design_space(anchor, contract)
    return contract
