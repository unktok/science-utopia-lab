"""Non-veto project-field checks on returned code values and recorded inputs.

This executes only trusted, pure original assignment validators. It never runs
authored source, a command receiver, an agent, a world or an inferred repair.
"""
from pathlib import Path

from utopia.system.design_patch import digest
from utopia.system.native_catalog_planning import validate_catalog_assignment
from utopia.system.native_legacy_topic_planning import eligible_topics,validate_legacy_topic_assignment

SCOPE='recorded-direct-native-project-fields-v1'
BANK_OPTION='post_edit_project_delivery_scope'
SCHEMA='scienceutopia.recorded-native-project-fields.v1'
NOTE=('Returned component commands are also checked against the original pure '
    'catalog/legacy-topic assignment validators on that recorded fixture. This '
    'checks project fields and topic eligibility, not command authorization, '
    'atomic batches, actual future state, downstream execution or world success. '
    'It never repairs source, changes loss or vetoes finish. Other interfaces '
    'remain permitted and explicitly unassessed. Changed graph diagnostics are stale.')


def source_hashes():
    from utopia.system import native_catalog_planning, native_legacy_topic_planning
    from utopia.utils.data_utils import file_sha256
    return {p.name:file_sha256(p) for p in (Path(__file__),
        Path(native_catalog_planning.__file__),Path(native_legacy_topic_planning.__file__))}


def diagnose(document,producer_id,result,context,*,limit=16):
    """Bounded literal project fields, never a general native-validity verdict."""
    if type(limit) is not int or not 1<=limit<=64:
        raise ValueError('bounded project diagnostic rows required')
    report={'schema':SCHEMA,'document_sha256':digest(document),'producer_id':producer_id,
        'result_sha256':digest(result),'recorded_context_sha256':digest(context),
        'rows':[],'omitted_rows':0,'changes_validity':False,
        'authored_value_changed_by_host':False,'new_model_calls':0,
        'new_native_worlds':0,'new_source_executions':0,
        'scope':'Pure original project-field validators on recorded fixture state only. '
            'No command authorization, actual consumer execution, future-state compatibility '
            'or whole-world success is certified.'}
    nodes=document.get('mechanisms',[]) if isinstance(document,dict) else []
    edges=document.get('connections',[]) if isinstance(document,dict) else []
    nodes=nodes if isinstance(nodes,list) else [];edges=edges if isinstance(edges,list) else []
    owners=[n for n in nodes if isinstance(n,dict) and n.get('mechanism_id')==producer_id]
    if len(owners)!=1:
        report['resolution']='no-unique-literal-producer';return report
    outputs=result.get('outputs') if isinstance(result,dict) else None
    inputs=context.get('inputs') if isinstance(context,dict) else None
    world_frames=inputs.get('world') if isinstance(inputs,dict) else None
    snapshot=None
    if isinstance(world_frames,list) and len(world_frames)==1 and isinstance(world_frames[0],dict):
        snapshot=world_frames[0].get('payload')
    try:
        actors=snapshot['ecosystem']['agents']
        if not isinstance(actors,list):raise TypeError('recorded actors are not a list')
        ids=[a['id'] for a in actors]
        if len(set(ids))!=len(ids):raise ValueError('ambiguous recorded actor')
        actors={a['id']:a for a in actors}
        catalog=context['parameters']['catalog'];year=context['period']
        if type(year) is not int or year<1:raise ValueError('invalid recorded year')
    except (KeyError,TypeError,ValueError):
        report['resolution']='recorded-world-catalog-year-unavailable';return report
    validators={'native.catalog-project.v1':validate_catalog_assignment,
                'native.legacy-topic-project.v1':validate_legacy_topic_assignment}
    rows=[]
    for index,edge in enumerate(edges):
        if not isinstance(edge,dict) or edge.get('source_mechanism')!=producer_id:continue
        targets=[n for n in nodes if isinstance(n,dict) and n.get('mechanism_id')==edge.get('target_mechanism')]
        if len(targets)!=1 or targets[0].get('implementation')!='native.domain.commands.v1':continue
        base={'connection_path':f'/connections/{index}','source_port':edge.get('source_port'),
              'target_mechanism':edge.get('target_mechanism'),'target_port':edge.get('target_port')}
        incoming=[e for e in edges if isinstance(e,dict)
            and (e.get('target_mechanism'),e.get('target_port'))==
                (edge.get('target_mechanism'),edge.get('target_port'))]
        if (len(incoming)!=1 or type(edge.get('latency',0)) is not int or edge.get('latency',0)!=0
                or edge.get('target_port')!='commands'):
            rows.append({**base,'status':'not-assessed','reason':'fan-in-delayed-or-unknown-command-port'});continue
        frames=outputs.get(edge.get('source_port')) if isinstance(outputs,dict) else None
        if not isinstance(frames,list):
            rows.append({**base,'status':'not-assessed','reason':'recorded-command-frames-unavailable'});continue
        # Bound actual traversal as well as the returned report.
        for ordinal,frame in enumerate(frames):
            if len(rows)>=limit:
                report['omitted_rows']+=len(frames)-ordinal;break
            row={**base,'frame_index':ordinal,'status':'not-assessed'}
            command=frame.get('payload') if isinstance(frame,dict) else None
            if (not isinstance(command,dict) or not isinstance(command.get('action'),str)
                    or command['action'] not in validators):
                rows.append({**row,'reason':'not-a-supported-project-command'});continue
            row.update(action=command['action'],command_sha256=digest(command))
            try:
                assignment=command['payload']['assignment'];identity=assignment['actor_id']
                row['assigned_actor_id']=identity
                actor=actors[identity];direction=assignment['direction'];topic=direction.get('topic')
                eligible=(eligible_topics(actor,catalog=catalog) if command['action']=='native.legacy-topic-project.v1'
                          else actor['expertise'])
                actual={d['topic']:d for d in catalog['directions']}
                row['field_checks']={
                    'topic_eligible_for_recorded_actor':isinstance(topic,str) and topic in eligible,
                    'canonical_catalog_content_equal':isinstance(topic,str) and direction==actual.get(topic),
                    'native_start_and_duration_equal':type(direction.get('years')) is int
                        and direction['years']>=1 and assignment.get('project_start_year')==year
                        and assignment.get('project_end_year')==year+direction['years']-1}
                validators[command['action']](assignment,actors[identity],year=year,catalog=catalog)
                row['status']='compatible-recorded-project-fields'
            except (KeyError,TypeError,ValueError,RuntimeError,AttributeError) as error:
                row.update(status='incompatible-recorded-project-fields',
                    error_type=type(error).__name__,error_excerpt=str(error)[:256],
                    error_excerpt_is_partial=len(str(error))>256)
            rows.append(row)
    report['rows']=rows[:limit];report['omitted_rows']+=max(0,len(rows)-limit)
    return report
