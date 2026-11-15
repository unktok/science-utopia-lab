"""Prescribed institutional work for software proof, never a model invention."""
from dataclasses import replace
from tests.system.test_native_researcher_work_v15 import code_node
from utopia.system import SystemSpec, ConnectionSpec, ChannelKind, ScheduleSpec
from utopia.system.native_kernel import WORLD_ARTIFACT
from utopia.system.native_researcher_work import REQUEST, add_researcher_work_receiver

SOURCE="""def step(context):
    world = context['inputs']['world'][0]['payload']
    actor = next(a['id'] for a in world['ecosystem']['agents'] if a['can_author'])
    task = {'schema': 'native-researcher-work-request-v15',
        'request_id': 'scripted-task-' + str(context['period']), 'actor_id': actor,
        'instruction': 'SCRIPTED software task, not actual scientific evidence.',
        'content': {'question': 'SCRIPTED_INSTITUTIONAL_WORK'}, 'artifact_ids': [],
        'response_schema': {'type': 'object', 'properties': {'note': {'type': 'string'}},
            'required': ['note'], 'additionalProperties': False}}
    return {'outputs': {'tasks': [{'payload': task, 'actor_ids': [actor], 'artifact_ids': []}]}, 'state': {}}
"""


def work_system(parent, *, suffix='0'):
    opening=next(n for n in parent.mechanisms if n.implementation=='native.phase.open.v1')
    phase=next(s.phase for s in parent.schedules if s.mechanism_id==opening.mechanism_id)
    image=next(n.parameters['runtime_image_id'] for n in parent.mechanisms if n.implementation=='code.python.v1')
    producer=code_node('scripted-work-office-'+suffix,image,SOURCE,{'world':WORLD_ARTIFACT},{'tasks':REQUEST})
    stage=replace(parent,mechanisms=(*parent.mechanisms,producer),
        schedules=(*parent.schedules,ScheduleSpec(producer.mechanism_id,phase+1)),
        connections=(*parent.connections,ConnectionSpec(opening.mechanism_id,'world',producer.mechanism_id,
                                                       'world',ChannelKind.ARTIFACT)))
    return add_researcher_work_receiver(stage,source=producer.mechanism_id,source_port='tasks',
        receiver='scripted-work-receiver-'+suffix,phase=phase+2,max_requests_per_invocation=1)


def work_edit(request):
    parent=SystemSpec.from_dict(request['parent_system'])
    target=work_system(parent,suffix=str(request['generation']))
    before,after=parent.to_dict(),target.to_dict()
    return {'tool':'edit','operations':[{'op':'add','path':'/'+field+'/-','value':row}
        for field in ('artifact_types','mechanisms','schedules','connections')
        for row in after[field] if row not in before[field]]}
