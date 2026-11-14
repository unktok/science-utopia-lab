"""A prescribed active code/wire change for SOFTWARE proof, never discovery."""
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.system import SystemSpec
from utopia.system.design_patch import clone


def authored_program(request):
    target = post_funding_cost_control(SystemSpec.from_dict(request['design_space_anchor'])).to_dict()
    old, new = 'developer-catalog-agenda', 'authored-long-horizon-office'
    node = next(n for n in target['mechanisms'] if n['mechanism_id'] == old)
    node['mechanism_id'] = new
    artifact = node['parameters']['code_artifact']
    literal = 'direction = min(candidates, key=lambda d: (d[\'years\'], d[\'topic\']))'
    assert artifact['source'].count(literal) == 1
    artifact['source'] = artifact['source'].replace(literal, literal.replace('min(', 'max('))
    artifact['source'] = artifact['source'].replace('shortest displayed duration', 'longest displayed duration')
    artifact['label'] = 'SCRIPTED authored long-horizon algorithm, not a searched discovery'
    for schedule in target['schedules']:
        if schedule['mechanism_id'] == old: schedule['mechanism_id'] = new
    for edge in target['connections']:
        for key in ('source_mechanism', 'target_mechanism'):
            if edge[key] == old: edge[key] = new
    return {'operations': [{'op': 'replace', 'path': '/' + key, 'value': clone(target[key])}
        for key in ('mechanisms', 'schedules', 'connections')], 'factors': [], 'continuous': [],
        'rationale': 'SCRIPTED active authored institution changes legal catalog choices and downstream native scientist inputs; not an optimized or useful invention claim'}
