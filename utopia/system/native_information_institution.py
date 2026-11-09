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


def information_design_space(anchor, kind):
    contract = make_design_space(anchor, kind)
    # Replace the old example's now-inert repetition coordinate with a value
    # the dossier source actually consumes. This is a new prospective domain.
    contract['numeric_coordinates'][-1] = {'mechanism_id':'information-office',
        'path':'/parameters/max_records', 'lower':0., 'upper':6., 'integer':True}
    validate_design_space(anchor, contract)
    return contract
