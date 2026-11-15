"""Prospective three-objective study arithmetic, not a change to old T/U."""
from .loss import validate_loss_spec
from .native_resource_cost import METRIC
from utopia.system.design_patch import clone

OBJECTIVES = ('throughput', 'content-utility', 'resource-aware-content')
RESOURCE_COEFFICIENT = 0.1


def objective_specs(original):
    if set(original) != {'throughput', 'content-utility'}:
        raise ValueError('literal original T/U loss pair required')
    for spec in original.values():
        validate_loss_spec(spec)
    if original['content-utility']['per_run'] != {
        'intercept': 0., 'terms': [{'metric_id': 'native.common_content_utility_sum',
                                  'slice_id': None, 'coefficient': -1.}]}:
        raise ValueError('original centered common-content arithmetic required')
    result = clone(original)
    cost = clone(original['content-utility'])
    cost.update(id='native-topic-resource-aware-content-v1', version='1',
        status='prospective-development-preference-not-policy-welfare',
        interpretation='Minimize -U + 0.1 K. U is the original centered fixed-model content '
        'opinion, not truth. K is actual collected original activity cost, not money or compute. '
        'Ten resource units trade against one utility unit by an explicit developer-chosen '
        'preference, not an empirically identified social value. Historical T/U are unchanged. '
        'No hidden activity, fairness, novelty, improvement or adoption constraint.')
    cost['per_run']['terms'].append({'metric_id': METRIC, 'slice_id': None,
                                   'coefficient': RESOURCE_COEFFICIENT})
    validate_loss_spec(cost)
    result[OBJECTIVES[-1]] = cost
    return result
