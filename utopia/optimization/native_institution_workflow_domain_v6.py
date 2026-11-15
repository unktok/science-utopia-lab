"""Explicit original-world institutions may ask fixed scientists for typed work.

This is not extra native production: researcher-work returns response artifacts
and canonical receipts. Only separately connected original effect consumers
change papers/projects/resources. Old v4/v5 authority remains unchanged.
"""
from .native_workflow_domain_v4 import _require_workflow_candidate, _verify_workflow_witnesses
from utopia.system.native_legacy_topic_planning import ACTION

SCOPE='fixed-native-effects-institution-workflow-v6'


def require_institution_workflow_candidate(anchor,candidate):
    return _require_workflow_candidate(anchor,candidate,
        allowed_extra_project_actions=(ACTION,),allow_institutional_work=True)


def verify_institution_workflow_interval(anchor,candidate,events,*,years):
    require_institution_workflow_candidate(anchor,candidate)
    result=_verify_workflow_witnesses(anchor,candidate,events,years=years)
    from utopia.system.native_researcher_work import EVENT,validate_work_receipt
    work=[e.to_dict() if hasattr(e,'to_dict') else e for e in events]
    work=[e for e in work if e['event_type']==EVENT]
    for event in work:
        validate_work_receipt(event['payload'])
    return {**result,'schema':'scienceutopia.native-workflow-interval.v6','scope':SCOPE,
            'institutional_work_events':len(work)}


def institution_workflow_design_space(anchor,*,kind='code-and-graph'):
    from .native_design_space import make_design_space,validate_design_space
    contract=make_design_space(anchor,kind)
    contract['world_law_scope']=SCOPE
    contract['scope']+=(' Preserve original native effects, plan/paper origins, initial society/RNG, '
        'original catalog durations, causal data prerequisites and complete annual ledger. Arbitrary '
        'institutional source, nodes, ports, protocols, wires, schedules and bounded processes remain '
        'editable. Explicit native.legacy-topic-project.v1 may assign original core-plus-related '
        'topics to eligible idle authors without modifying ongoing projects or durations. '
        'native.researcher.work.v15 may ask existing fixed-model original researchers arbitrary '
        'authored tasks with typed response artifacts and exact receipts. This grants no extra '
        'native research production, fictitious paper/review results, resources, weights, personas '
        'or host privileges. Model-work calls count against the same declared total scientist '
        'HTTP/world bounds and retain native per-node/process caps. No shortest rule, novelty, '
        'fairness, minimum activity, usefulness or improvement veto is imposed.')
    return validate_design_space(anchor,contract)
