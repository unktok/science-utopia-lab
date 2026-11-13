"""Literal workflow proposals, not host interpretation of institutional prose.

This interface isolates wiring/order with fixed existing node implementations.
The larger workflow-v4 domain still allows arbitrary institutional code/nodes.
"""
from dataclasses import asdict, replace

from jsonschema import Draft202012Validator

from utopia.system import ChannelKind, ConnectionSpec, SystemSpec
from utopia.system.design_patch import clone, digest, make_patch
from .native_objective_view import loss_arithmetic
from .native_workflow_domain_v4 import SCOPE, require_workflow_candidate

SCHEMA = 'scienceutopia.native-workflow-submission.v1'


def _bound_systems(request):
    contract = request.get('design_space')
    if (not isinstance(contract, dict) or contract.get('kind') != 'code-and-graph'
            or contract.get('world_law_scope') != SCOPE):
        raise ValueError('explicit native workflow-v4 graph domain required')
    from .native_design_space import require_candidate_in_space
    anchor = SystemSpec.from_dict(request['design_space_anchor'])
    parent = SystemSpec.from_dict(request['parent_system'])
    require_candidate_in_space(anchor, parent, contract)
    require_workflow_candidate(anchor, parent, structure_only=True)
    return anchor, parent


def workflow_context(request):
    """Keep fixed implementations once, not once per historical observation.

    Exact source/parameters, including the catalog, remain visible. No prose
    surrogate replaces them, and no historical scalar/failed slot is removed.
    Response caches, critic rationales and full repeated candidate sources are
    not required to define this declared black-box structural action space.
    """
    anchor, parent = _bound_systems(request)
    observations, designs = [], {}
    for pair in request.get('observations', []):
        o, suggestion = pair['observation'], pair['suggestion']
        prior = SystemSpec.from_dict(suggestion['candidate'])
        require_workflow_candidate(anchor, prior, structure_only=True)
        # Literal index references preserve edge order, including intentionally
        # reordered connections. Only exactly identical fixed anchor edges are
        # referenced; no inferred semantic equivalence or policy deduplication.
        designs[prior.fingerprint] = graph_projection(anchor, prior)
        observations.append({'observation_id': o['observation_id'], 'status': o['status'], 'loss': o['loss'],
            'system_fingerprint': prior.fingerprint,
            'metrics': [clone(m['metrics']) for m in o.get('metadata', {}).get('measurements', [])],
            'technical_failures': clone(o.get('metadata', {}).get('technical_failures', []))})
    nulls = [{'request_sha256': h['request_sha256'], 'generation_error': clone(h['generation_error']),
        'literal_submission_failure': clone(h['definition'].get('workflow_submission_failure'))
            if isinstance(h.get('definition'), dict) else None}
        for h in request.get('history', []) if h.get('generation_error')]
    return {'schema': SCHEMA + '.context', 'request_sha256': digest(request),
        'generation': request['generation'], 'loss_spec': clone(request['loss_spec']),
        'loss_arithmetic': loss_arithmetic(request['loss_spec']),
        'world_binding': clone(request['world_binding']),
        'fixed_mechanisms': parent.to_dict()['mechanisms'],
        'fixed_artifact_types': parent.to_dict()['artifact_types'],
        'parent_schedules': parent.to_dict()['schedules'],
        'parent_connections': [{'index': i, **e} for i, e in enumerate(parent.to_dict()['connections'])],
        'history_anchor_connections': anchor.to_dict()['connections'],
        'history_anchor_schedules': anchor.to_dict()['schedules'],
        'observed_graphs': designs,
        'domain': clone(request['design_space']), 'observations': observations,
        'consumed_generation_nulls': nulls,
        'operations': 'Apply phase_updates, then remove original indexed connections simultaneously and append '
            'literal add_connections. No source/parameter/node edits. Empty updates/removals/additions retain '
            'the parent explicitly. Native stages still execute once with valid causal inputs; no auto-repair.',
        'scientific_merit_novelty_or_improvement_veto': False}


def graph_projection(anchor, candidate):
    require_workflow_candidate(anchor, candidate, structure_only=True)
    phases = {s.mechanism_id: s.phase for s in anchor.schedules}
    return {'phase_updates_from_anchor': {s.mechanism_id: s.phase for s in candidate.schedules
            if s.phase != phases[s.mechanism_id]},
        'ordered_connections': [{'anchor_index': anchor.connections.index(e)} if e in anchor.connections
            else {'literal': {**asdict(e), 'channel': e.channel.value}} for e in candidate.connections]}


def submission_schema(context):
    identities = [n['mechanism_id'] for n in context['fixed_mechanisms']]
    edge = {'type': 'object', 'additionalProperties': False,
        'required': ['source_mechanism', 'source_port', 'target_mechanism', 'target_port', 'channel', 'latency'],
        'properties': {'source_mechanism': {'type': 'string', 'enum': identities},
            'target_mechanism': {'type': 'string', 'enum': identities},
            'source_port': {'type': 'string', 'minLength': 1}, 'target_port': {'type': 'string', 'minLength': 1},
            'channel': {'type': 'string', 'enum': [c.value for c in ChannelKind]},
            'latency': {'type': 'integer', 'minimum': 0}}}
    return {'type': 'object', 'additionalProperties': False,
        'required': ['phase_updates', 'remove_connections', 'add_connections', 'rationale'],
        'properties': {
            'phase_updates': {'type': 'object', 'additionalProperties': False,
                'properties': {identity: {'type': 'integer', 'minimum': 0} for identity in identities}},
            'remove_connections': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'integer', 'minimum': 0, 'maximum': len(context['parent_connections']) - 1}},
            'add_connections': {'type': 'array', 'maxItems': 128, 'items': edge},
            'rationale': {'type': 'string', 'minLength': 1, 'maxLength': 8000}}}


def compile_submission(request, submission):
    context = workflow_context(request)
    Draft202012Validator(submission_schema(context)).validate(submission)
    if (not submission['rationale'].strip()
            or any(type(value) is not int for value in submission['phase_updates'].values())
            or any(type(value) is not int for value in submission['remove_connections'])
            or any(type(e['latency']) is not int for e in submission['add_connections'])):
        raise ValueError('literal integer phases, indexes, latencies and nonblank rationale required')
    anchor, parent = _bound_systems(request)
    removals = set(submission['remove_connections'])
    new_edges = tuple(ConnectionSpec(**{**e, 'channel': ChannelKind(e['channel'])})
        for e in submission['add_connections'])
    candidate = replace(parent,
        schedules=tuple(replace(s, phase=submission['phase_updates'][s.mechanism_id])
            if s.mechanism_id in submission['phase_updates'] else s for s in parent.schedules),
        connections=tuple(e for i, e in enumerate(parent.connections) if i not in removals) + new_edges)
    require_workflow_candidate(anchor, candidate, structure_only=True)
    operations = [{'op': 'replace', 'path': '/' + key, 'value': candidate.to_dict()[key]}
        for key in ('connections', 'schedules') if candidate.to_dict()[key] != parent.to_dict()[key]]
    return {'base_patch': make_patch(parent, operations) if operations else None,
        'factors': [], 'continuous': [],
        'provenance': {'author': 'literal-local-workflow-submission', 'schema': SCHEMA,
            'submission_sha256': digest(submission), 'rationale': submission['rationale'],
            'retained_parent_explicitly': not operations, 'raw_values_changed_by_host': False,
            'fixed_implementations_scope_not_general_v4_ceiling': True}}


def control_submission(request):
    """Exercise all nested operation types with a literal identity transaction.

    This directed interface task is not evidence of autonomous free design.
    Copy equality is diagnostic; a different valid returned graph can pass the
    declared execution-readiness scope without being silently reset to identity.
    """
    _, parent = _bound_systems(request)
    last = parent.connections[-1]
    s = parent.schedules[0]
    return {'phase_updates': {s.mechanism_id: s.phase}, 'remove_connections': [len(parent.connections) - 1],
        'add_connections': [{**asdict(last), 'channel': last.channel.value}],
        'rationale': 'Interface control only; literal graph identity, not institutional invention.'}
