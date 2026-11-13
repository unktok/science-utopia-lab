"""Two isolated actual consumers, not actual-model or scientific loss evidence."""
from copy import deepcopy

from tests.optimization.test_native_parameter_space_v1 import space, IMAGE
from tests.system.test_native_capacity_controls import context
from utopia.system.code_mechanisms import DockerCodeExecutor


def test_generated_numeric_systems_change_actual_transfer_commands_without_minting_funds():
    s=space(); executor=DockerCodeExecutor(IMAGE); results={}
    for reserve in (20,21):
        system=s.candidate({'coordinate-0':reserve})
        node=next(n for n in system['mechanisms'] if n['mechanism_id']=='developer-liquidity-director')
        frame=context();frame['parameters']=deepcopy(node['parameters']);original=deepcopy(frame)
        outcome=executor.execute(node['parameters']['code_artifact'],frame)
        assert frame==original
        commands=outcome.result['outputs']['funds'];results[reserve]=commands
        balances={a['id']:a['resources'] for a in frame['inputs']['world'][0]['payload']['ecosystem']['agents']}
        for item in commands:
            p=item['payload'];balances[p['from_actor']]-=p['amount'];balances[p['to_actor']]+=p['amount']
        assert sum(balances.values())==62 and min(balances.values())>=0
    assert results[20][0]['payload']['to_actor']=='soon' and results[20][0]['payload']['amount']==2
    assert results[21][0]['payload']['to_actor']=='near' and results[21][0]['payload']['amount']==1
