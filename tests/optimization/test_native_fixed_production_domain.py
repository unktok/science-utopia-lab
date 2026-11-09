from copy import deepcopy
from dataclasses import replace

import pytest

from utopia.optimization.native_design_space import require_candidate_in_space,validate_design_space
from utopia.system import SystemSpec
from utopia.system.native_information_institution import information_system,information_design_space
from utopia.optimization.native_benchmark_controls import selection_control,without_review

IMAGE='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def fixture():
    anchor=information_system(IMAGE)
    return anchor,information_design_space(anchor,'code-and-graph',fixed_production=True)


def test_pilot_domain_is_explicit_and_does_not_add_an_outcome_veto():
    anchor,domain=fixture()
    for rule in ('accept-all','reject-all'):
        require_candidate_in_space(anchor,without_review(selection_control(anchor,rule=rule)),domain)
    data=anchor.to_dict()
    next(n for n in data['mechanisms'] if n['mechanism_id']=='information-office')['parameters']['code_artifact']['source']+='\n# arbitrary new authored institution\n'
    require_candidate_in_space(anchor,SystemSpec.from_dict(data),domain)
    reordered=replace(anchor,connections=tuple(reversed(anchor.connections)))
    require_candidate_in_space(anchor,reordered,domain)


@pytest.mark.parametrize('mutation',['remove','schedule','capability','amendment','duplicate','image'])
def test_production_changes_are_technical_domain_violations_not_scientific_losses(mutation):
    anchor,domain=fixture();data=anchor.to_dict()
    if mutation=='remove':
        data['mechanisms']=[n for n in data['mechanisms'] if n['mechanism_id']!='world.costs']
        data['schedules']=[s for s in data['schedules'] if s['mechanism_id']!='world.costs']
        data['connections']=[e for e in data['connections'] if 'world.costs' not in (e['source_mechanism'],e['target_mechanism'])]
    elif mutation=='schedule':
        next(s for s in data['schedules'] if s['mechanism_id']=='world.research')['phase']+=1
    elif mutation=='capability':
        next(n for n in data['mechanisms'] if n['mechanism_id']=='open-domain-actions')['parameters']['capabilities']['roles']['open-planner'].append('native.project')
    elif mutation=='amendment':
        data['connections'].append({'source_mechanism':'world.research','source_port':'plans',
            'target_mechanism':'research-plan-effects','target_port':'amendments','channel':'artifact','latency':0})
    elif mutation=='duplicate':
        node=deepcopy(next(n for n in data['mechanisms'] if n['mechanism_id']=='world.research'))
        node['mechanism_id']='double-production';data['mechanisms'].append(node)
        data['schedules'].append({'mechanism_id':'double-production','phase':60,'trigger':'annual'})
    else:
        next(n for n in data['mechanisms'] if n['mechanism_id']=='information-office')['parameters']['runtime_image_id']='sha256:'+'1'*64
    with pytest.raises(ValueError):
        require_candidate_in_space(anchor,SystemSpec.from_dict(data),domain)


def test_legacy_free_domain_is_not_relabelled_fixed_production():
    anchor,domain=fixture();legacy=information_design_space(anchor,'code-and-graph')
    assert 'world_law_scope' not in legacy
    data=anchor.to_dict()
    next(n for n in data['mechanisms'] if n['mechanism_id']=='open-domain-actions')['parameters']['capabilities']['roles']['open-planner'].append('native.project')
    require_candidate_in_space(anchor,SystemSpec.from_dict(data),legacy)
    domain['world_law_scope']='unknown'
    with pytest.raises(ValueError,match='unknown'):
        validate_design_space(anchor,domain)
