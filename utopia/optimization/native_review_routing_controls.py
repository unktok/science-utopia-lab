"""Explicit developer baselines, never manufactured candidate repairs."""
from dataclasses import replace

from utopia.system import ChannelKind, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CODE_SCHEMA
from utopia.system.native_review_routing import BATCH, PLAN, enable_review_routing

SOURCE = '''import hashlib, json
def step(context):
    batch = context['inputs']['batch'][0]['payload']
    limit = context['parameters']['reviewers_per_paper']
    tasks = []
    for paper in batch['papers']:
        for reviewer in paper['eligible_reviewer_ids'][:limit]:
            tasks.append(dict(conference_id=paper['conference_id'], paper_id=paper['paper_id'], reviewer_id=reviewer))
    command = dict(schema='native-review-routing-plan-v13', year=context['period'],
        batch_sha256=hashlib.sha256(json.dumps(batch,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest(),
        tasks=tasks)
    return dict(outputs={'routing':[{'payload':command}]}, state={})
'''


def routed_control(anchor, *, reviewers_per_paper, snapshot_phase, producer_phase):
    if type(reviewers_per_paper) is not int or not 0 <= reviewers_per_paper <= 64:
        raise ValueError('explicit bounded integer review count required')
    if type(snapshot_phase) is not int or type(producer_phase) is not int:
        raise ValueError('reference phases must be explicitly authored integers')
    images = {n.parameters['runtime_image_id'] for n in anchor.mechanisms
              if n.implementation == 'code.python.v1'}
    if len(images) != 1:
        raise ValueError('one pinned reference image required')
    identity = 'developer-review-coordinator'
    if identity in {n.mechanism_id for n in anchor.mechanisms}:
        raise ValueError('reference producer already exists')
    producer = MechanismSpec(identity, MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('batch', ChannelKind.ARTIFACT, BATCH),),
        outputs=(PortSpec('routing', ChannelKind.ARTIFACT, PLAN),),
        parameters={'runtime_image_id': next(iter(images)), 'reviewers_per_paper': reviewers_per_paper,
            'code_artifact': {'schema': CODE_SCHEMA, 'source': SOURCE,
                'label': 'Developer nested eligible-reviewer control, not a discovered institution',
                'inputs': {'batch': {'type': 'object'}}, 'outputs': {'routing': {'type': 'object'}},
                'state_schema': {'type': 'object'}}})
    source = replace(anchor, mechanisms=(*anchor.mechanisms, producer),
        schedules=(*anchor.schedules, ScheduleSpec(identity, producer_phase)))
    return enable_review_routing(source, source=identity, source_port='routing',
                                 snapshot_phase=snapshot_phase)
