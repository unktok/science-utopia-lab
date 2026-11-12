"""Reference identity/domain checks, no execution or scientific merit assertion."""
from utopia.optimization.native_design_space import require_candidate_in_space
import pytest

from utopia.optimization.native_fixed_production_domain import catalog_planning_design_space
from utopia.system.native_catalog_planning import ACTION, SOURCE
from utopia.system.native_information_institution import information_design_space
from utopia.system.native_planning_controls import ORDER, planning_controls

IMAGE = 'sha256:' + 'a' * 64


def test_eight_literal_references_share_authority_native_law_and_original_catalog():
    refs = planning_controls(IMAGE, seed=61001); assert tuple(refs) == ORDER
    anchor = refs[ORDER[0]]
    with pytest.raises(ValueError, match='catalog project authority'):
        information_design_space(anchor, 'code-and-graph', fixed_production=True)
    domain = catalog_planning_design_space(anchor, 'code-and-graph')
    for label, spec in refs.items():
        require_candidate_in_space(anchor, spec, domain)
        agenda = next(n for n in spec.mechanisms if n.mechanism_id == 'developer-catalog-agenda')
        assert agenda.parameters['code_artifact']['source'] == SOURCE
        receiver = next(n for n in spec.mechanisms if n.mechanism_id == 'developer-catalog-effects')
        assert receiver.parameters['capabilities']['bootstrap'] == ['native.context', ACTION]
        assert spec.initial_state['seed'] == 61001
        assert ('world.review' not in {n.mechanism_id for n in spec.mechanisms}) == ('no-review' in label)


def test_reserve_and_selection_are_literal_rules_not_an_outer_quality_or_activity_veto():
    refs = planning_controls(IMAGE, seed=61001)
    for label, spec in refs.items():
        nodes = {n.mechanism_id: n for n in spec.mechanisms}
        allocation = nodes['developer-liquidity-director'].parameters
        if 'equalization' not in label:
            assert allocation['reserve_units'] == (10 if 'reserve10' in label else 21)
        selection = nodes['world.selection'].parameters
        assert selection['control_rule'] == ('threshold' if label.endswith('score3') else
            'reject-all' if label.endswith('reject') else 'accept-all')
        assert 'common_content_utility_sum' not in str(selection)
        assert 'active_founder_boundary_sum' not in str(selection)
