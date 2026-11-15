"""Original-effect whole-graph domain with explicit legacy-topic authority.

No old fixed-production/workflow scope gains this capability implicitly.
"""
from .native_workflow_domain_v4 import _require_workflow_candidate, _verify_workflow_witnesses
from utopia.system.native_legacy_topic_planning import ACTION

SCOPE = 'fixed-native-effects-legacy-topic-workflow-v5'


def require_legacy_topic_workflow_candidate(anchor, candidate):
    return _require_workflow_candidate(anchor, candidate, allowed_extra_project_actions=(ACTION,))


def verify_legacy_topic_workflow_interval(anchor, candidate, events, *, years):
    """Actual fixed-effect witnesses under the explicit new authority, not v4."""
    require_legacy_topic_workflow_candidate(anchor, candidate)
    result = _verify_workflow_witnesses(anchor, candidate, events, years=years)
    return {**result, 'schema': 'scienceutopia.native-workflow-interval.v5', 'scope': SCOPE}


def legacy_topic_workflow_design_space(anchor, *, kind='code-and-graph'):
    """Same whole-system design domain, explicit optional narrower comparators."""
    from .native_design_space import make_design_space, validate_design_space
    contract = make_design_space(anchor, kind)
    contract['world_law_scope'] = SCOPE
    contract['scope'] += (
        ' Original native effect contracts, initial state/RNG, plan/paper origins and pinned code image'
        ' stay fixed; institutional source, mechanisms, wiring and schedules may change subject to'
        ' original data/effect/annual-ledger prerequisites. The explicit native.legacy-topic-project.v1'
        ' capability permits an active idle author to start a core or directly related topic from the'
        ' original native non-strict catalog union, with exact native content and duration. It grants'
        ' no arbitrary native.project, ongoing-project interruption, invented topic or extra production.'
        ' Researcher weights and original research/retrieval/submission/funding/cost consumers are unchanged.'
        ' No shortest-topic rule, loss, fairness, novelty or improvement requirement is imposed.')
    return validate_design_space(anchor, contract)
