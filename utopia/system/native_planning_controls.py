"""Explicit planning/allocation/selection references, not generated inventions."""
from utopia.optimization.native_benchmark_controls import selection_control, without_review
from .native_capacity_controls import capacity_allocation_control
from .native_catalog_planning import catalog_agenda_control
from .native_information_institution import information_system
from .native_liquidity_controls import liquidity_control

ORDER = (
    'cut-reserve21-all', 'advice-reserve21-all', 'assignment-reserve21-all',
    'assignment-reserve10-all', 'assignment-equalization-all',
    'assignment-reserve21-score3', 'assignment-reserve21-no-review-all',
    'assignment-reserve21-no-review-reject',
)


def planning_controls(image_id, *, seed):
    """Same native production and available catalog authority in all references.

    Reserve10 is a permitted parameter, not a claim of superior participation.
    Original zero-resource activity semantics remain unchanged and observable.
    Native score3 is not the independent content observer's opinion.
    """
    specs = {}
    for label in ORDER:
        base = information_system(image_id, seed=seed)
        rule = 'threshold' if label.endswith('score3') else 'reject-all' if label.endswith('reject') else 'accept-all'
        selected = selection_control(base, rule=rule, threshold=3. if rule == 'threshold' else 0.)
        if 'no-review' in label: selected = without_review(selected)
        allocation = liquidity_control(selected, image_id) if 'equalization' in label else capacity_allocation_control(
            selected, image_id, rule='reserve-proximity', reserve_units=10 if 'reserve10' in label else 21)
        mode = 'cut' if label.startswith('cut-') else 'information' if label.startswith('advice-') else 'project'
        specs[label] = catalog_agenda_control(allocation, image_id, actuation=mode)
    return specs
