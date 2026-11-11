"""Read-only operational-order evidence, not an oracle for arbitrary code.

This describes the declared native graph. It does not execute source, certify
semantic equivalence, infer an optimal institution or supply scientific losses.
Native handlers share persistent world state: wires are not a complete causal DAG.
"""
from utopia.system import SystemSpec, validate_system_spec
from utopia.system.design_patch import digest

SCHEMA = 'scienceutopia.native-causal-design.v1'
FILENAME = 'reference/causal-design.json'
OPTION = 'causal_design_context'
PRESENTATION = 'causal_design_presentation'
REVIEWS = {'native.phase.review.v1', 'native.phase.review.with-routing.v13'}


def context_fields(provenance):
    """Explicit future presentation; absent/file retains the original assay ABI."""
    flag = provenance.get(OPTION, False)
    if type(flag) is not bool:
        raise ValueError('causal design context must be an explicit boolean')
    mode = provenance.get(PRESENTATION, 'file')
    if mode not in ('file', 'inline') or PRESENTATION in provenance and not flag:
        raise ValueError('causal presentation requires enabled context and file/inline mode')
    result = {OPTION: True} if flag else {}
    if PRESENTATION in provenance:
        result[PRESENTATION] = mode
    return result


def describe(document):
    identity = digest(document)
    try:
        spec = SystemSpec.from_dict(document)
        validate_system_spec(spec).require_valid()
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        return {'schema': SCHEMA, 'system_sha256': identity, 'status': 'invalid-draft',
            'error_type': type(error).__name__, 'error': str(error),
            'interpretation': 'Edit the literal draft. No operational order inferred.'}
    nodes = {n.mechanism_id: n for n in spec.mechanisms}
    order = sorted(spec.schedules, key=lambda s: (s.phase, s.mechanism_id, s.trigger))
    phases = {n: [s.phase for s in order if s.mechanism_id == n] for n in nodes}
    rows = [{'mechanism_id': s.mechanism_id, 'phase': s.phase, 'trigger': s.trigger,
        'implementation': nodes[s.mechanism_id].implementation,
        'inputs': [p.port_id for p in nodes[s.mechanism_id].inputs],
        'outputs': [p.port_id for p in nodes[s.mechanism_id].outputs]} for s in order]
    reviews = [n.mechanism_id for n in spec.mechanisms if n.implementation in REVIEWS]
    costs = [n.mechanism_id for n in spec.mechanisms if n.implementation == 'native.phase.costs.v1']
    publications = {n.mechanism_id for n in spec.mechanisms if n.implementation == 'native.phase.publication.v1'}
    decision_edges = [e for e in spec.connections if e.target_mechanism in publications
        and e.target_port == 'decisions' and e.latency == 0]
    relations = []
    for edge in decision_edges:
        for review in reviews:
            if len(phases[edge.source_mechanism]) == len(phases[review]) == 1:
                relations.append({'review': review, 'review_phase': phases[review][0],
                    'decision_sender': edge.source_mechanism,
                    'decision_phase': phases[edge.source_mechanism][0],
                    'decision_sender_after_review': phases[edge.source_mechanism][0] > phases[review][0],
                    'scope': 'Declared within-year order, conditional on those executions occurring. '
                        'Later decisions cannot undo already-executed review calls; later years can differ.'})
    windows = []
    for cost in costs:
        for review in reviews:
            if len(phases[cost]) == len(phases[review]) == 1:
                lo, hi = phases[cost][0], phases[review][0]
                windows.append({'after_costs': cost, 'costs_phase': lo, 'before_review': review,
                    'review_phase': hi, 'two_integer_phases_available': hi - lo >= 3,
                    'scope': 'The typed native review-routing API needs an explicit snapshot and '
                        'an authored producer strictly between these actual phases. Its default '
                        '105/110 example phases are not valid in every native graph.'})
    result = {'schema': SCHEMA, 'system_sha256': identity, 'status': 'declared-graph-valid',
        'annual_order': rows, 'connections': [e.to_dict() if hasattr(e, 'to_dict') else {
            'source_mechanism': e.source_mechanism, 'source_port': e.source_port,
            'target_mechanism': e.target_mechanism, 'target_port': e.target_port,
            'channel': e.channel.value, 'latency': e.latency} for e in spec.connections],
        'review_decision_order': relations, 'pre_review_windows': windows,
        'boundaries': ['No authored Python, institution names or author rationales are interpreted as proven effects.',
            'Graph paths alone do not include shared native world state or all cross-year consequences.',
            'Same information, memory and action authority may let monolithic code emulate a graph.',
            'This is advice, not a validity/novelty/fitness veto. No objective or authored code is changed.'],
        'new_model_calls': 0, 'new_code_executions': 0}
    result['content_sha256'] = digest(result)
    return result
