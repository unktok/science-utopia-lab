"""Explicit conserving-liquidity controls, not model-discovered institutions."""
from dataclasses import replace

from .model import ArtifactTypeSpec,ChannelKind,ConnectionSpec,MechanismFamily,MechanismSpec,PortSpec,ScheduleSpec
from .code_mechanisms import CODE_SCHEMA
from .native_kernel import WORLD_ARTIFACT
from .native_resource_transfers import add_resource_transfer_receiver
from .validation import validate_system_spec

PROTOCOL='native-developer-liquidity-command-v1'
SOURCE='''def step(context):
    world = context['inputs']['world'][0]['payload']
    actors = [a for a in world['ecosystem']['agents'] if a['can_author'] and a['is_active']]
    balances = {a['id']: a['resources'] for a in actors}
    target = int(sum(balances.values()) / len(actors)) if actors else 0
    recipients = sorted(balances, key=lambda k: (balances[k], k))
    donors = sorted(balances, key=lambda k: (-balances[k], k))
    commands = []
    for recipient in recipients:
        for donor in donors:
            if donor == recipient:
                continue
            amount = min(max(0, int(balances[donor] - target)), max(0, int(target - balances[recipient])))
            if amount:
                commands.append({'payload': {'transaction_id': 'liquidity-' + str(len(commands)),
                    'from_actor': donor, 'to_actor': recipient, 'amount': amount}})
                balances[donor] -= amount
                balances[recipient] += amount
    return {'outputs': {'funds': commands}, 'state': {'period': context['period'], 'transfers_requested': len(commands)}}
'''


def liquidity_control(anchor,image_id,*,connected=True):
    """Same computation on both arms; only the delivery edges differ.

    Preserve all native stages, including costs and production, and act between
    actual submission and annual costs. No funds or researcher are created.
    """
    if type(connected) is not bool:raise ValueError('explicit connection condition required')
    phases={s.mechanism_id:s.phase for s in anchor.schedules}
    if phases['world.costs']-phases['world.submission']<3:
        raise ValueError('explicit native submission-to-cost execution opportunity required')
    producer='developer-liquidity-director';receiver='developer-liquidity-effects'
    if any(n.mechanism_id in (producer,receiver) for n in anchor.mechanisms):raise ValueError('fresh explicit control node identities required')
    node=MechanismSpec(producer,MechanismFamily.CUSTOM,'code.python.v1',
        inputs=(PortSpec('world',ChannelKind.ARTIFACT,WORLD_ARTIFACT),),
        outputs=(PortSpec('funds',ChannelKind.RESOURCE,PROTOCOL,required=False),),
        parameters={'runtime_image_id':image_id,'code_artifact':{'schema':CODE_SCHEMA,
            'label':'Developer whole-unit liquidity reference, not autonomous invention','source':SOURCE,
            'inputs':{'world':{'type':'object'}},'outputs':{'funds':{'type':'object'}},'state_schema':{'type':'object'}}})
    spec=replace(anchor,artifact_types=(*anchor.artifact_types,ArtifactTypeSpec(PROTOCOL)),
        mechanisms=(*anchor.mechanisms,node),schedules=(*anchor.schedules,ScheduleSpec(producer,phases['world.costs']-2)),
        connections=(*anchor.connections,ConnectionSpec('world.submission','world',producer,'world',ChannelKind.ARTIFACT)))
    spec=add_resource_transfer_receiver(spec,source=producer,source_port='funds',receiver=receiver,phase=phases['world.costs']-1)
    if not connected:spec=replace(spec,connections=tuple(c for c in spec.connections if c.target_mechanism!=receiver))
    validate_system_spec(spec).require_valid();return spec
