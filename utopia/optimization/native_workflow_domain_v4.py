"""Prospective workflow authority over the original native scientist world.

The old v3 fixed-calendar domain is intentionally not changed. This domain
fixes native effects/contracts, not their schedules. It accepts whole graphs,
including new institutional code and wiring, rather than a menu of policies.
Technical conformance is not a loss, novelty gate or improvement claim.
"""
from collections import Counter
from dataclasses import replace

from utopia.system.model import ConnectionSpec
from utopia.system.native_migration import native_execution_nodes
from utopia.system.validation import validate_system_spec
from .native_fixed_production_domain import CATALOG_PLANNING_SCOPE, fixed_nodes, free_native

SCOPE = 'fixed-native-effects-workflow-v4'
PHASE_EVENT = 'native.system.phase_executed'
PLAN_EVENT = 'native.system.research_plan_applied'
CORE_STAGES = frozenset(('open', 'resubmissions', 'research', 'plan-effects',
    'collaboration', 'submission', 'costs', 'publication', 'citation-potential',
    'funding', 'communication', 'close'))
PLAN_PORTS = frozenset((('research-plan-effects', 'plans'),
    ('research-plan-effects', 'amendments'), ('world.collaboration', 'plans'),
    ('world.submission', 'plans'), ('world.submission', 'papers'),
    ('world.funding', 'papers')))
MUTATORS = frozenset(('native.domain.commands.v1', 'native.world.resource-transfers.v1'))


def execution_order(spec):
    """Actual annual runner order; descriptive metadata is not authority."""
    validate_system_spec(spec).require_valid()
    if (len(spec.schedules) != len(spec.mechanisms)
            or any(s.trigger != 'annual' for s in spec.schedules)):
        raise ValueError('workflow-v4 requires exactly one annual schedule per node')
    return tuple(s.mechanism_id for s in sorted(spec.schedules,
        key=lambda s: (s.phase, s.mechanism_id)))


def _protected(anchor):
    nodes = fixed_nodes(anchor, scope=CATALOG_PLANNING_SCOPE)
    stages = [n.implementation.split('.')[2] for n in nodes.values()]
    if Counter(stages) != Counter(CORE_STAGES):
        raise ValueError('workflow-v4 requires one complete native activity/effect anchor')
    return nodes


def require_workflow_candidate(anchor, candidate, *, structure_only=False):
    """Check literal candidate; never synthesize a corrected graph or source.

    Native production, paper identities, costs, grants and effect bridges retain
    their original implementations. Their order and institutional wiring may
    change subject to actual data causality and a completed ledger boundary.
    This finite family has one annual invocation per graph node; the general
    engine's bounded custom process delegates remain available inside a node.
    """
    execution_order(anchor)
    order = execution_order(candidate)
    protected = _protected(anchor)
    nodes = {n.mechanism_id: n for n in candidate.mechanisms}
    for identity, node in protected.items():
        if nodes.get(identity) != node:
            raise ValueError('workflow-v4 fixes the native effect contract: ' + identity)
    # Unwrap process delegates as well as direct nodes. Counting is essential:
    # a second wrapper can otherwise hide an identical protected delegate ID.
    actual = native_execution_nodes(candidate)
    effects = [n for n in actual if n.implementation.startswith(('native.phase.', 'native.activity.'))
        and n.implementation not in free_native(CATALOG_PLANNING_SCOPE)]
    if (Counter(n.mechanism_id for n in effects) != Counter(protected.keys())
            or any(protected.get(n.mechanism_id) != n for n in effects)):
        raise ValueError('workflow-v4 forbids duplicated/wrapped/replaced native effects')
    if candidate.initial_state != anchor.initial_state:
        raise ValueError('workflow-v4 fixes native initial state and RNG binding')
    incoming = lambda spec: Counter(e for e in spec.connections
        if (e.target_mechanism, e.target_port) in PLAN_PORTS)
    if incoming(candidate) != incoming(anchor):
        raise ValueError('workflow-v4 fixes actual native plan and paper origins')
    images = {n.parameters['runtime_image_id'] for n in native_execution_nodes(anchor)
        if n.implementation == 'code.python.v1'}
    for node in actual:
        if node.implementation == 'native.researcher.work.v15':
            raise ValueError('extra research production is outside fixed-effect workflow-v4')
        grants = node.parameters.get('capabilities')
        if grants is not None:
            if (not isinstance(grants, dict) or not isinstance(grants.get('bootstrap'), list)
                    or not isinstance(grants.get('roles'), dict)
                    or any(not isinstance(v, list) for v in grants['roles'].values())):
                raise ValueError('workflow-v4 requires explicit capability lists')
            if any('native.project' in v for v in [grants['bootstrap'], *grants['roles'].values()]):
                raise ValueError('arbitrary project reassignment is outside workflow-v4')
        if node.implementation == 'code.python.v1' and node.parameters.get('runtime_image_id') not in images:
            raise ValueError('workflow-v4 code requires the pinned runtime image')
    rank = {identity: i for i, identity in enumerate(order)}
    stages = {n.implementation.split('.')[2]: identity for identity, n in protected.items()}
    if order[0] != stages['open']:
        raise ValueError('native year opening must execute first')
    for edge in candidate.connections:
        if edge.latency == 0 and rank[edge.source_mechanism] >= rank[edge.target_mechanism]:
            raise ValueError('zero-latency data must precede its consumer; declare delayed memory explicitly')
    # Minimal intrinsic preconditions, not the historical serial calendar.
    # Research/collaboration/submission dependencies also follow typed plan edges.
    for before, after in (('resubmissions', 'submission'), ('submission', 'costs'),
            ('submission', 'publication'), ('submission', 'funding'),
            ('publication', 'citation-potential'), ('funding', 'communication')):
        if rank[stages[before]] >= rank[stages[after]]:
            raise ValueError('native workflow prerequisite differs: ' + before + ' -> ' + after)
    close = rank[stages['close']]
    if any(rank[identity] >= close for identity in protected if identity != stages['close']):
        raise ValueError('native effects must finish before the annual ledger closes')
    for outer, delegate in zip(candidate.mechanisms, actual):
        if delegate.implementation in MUTATORS and rank[outer.mechanism_id] >= close:
            raise ValueError('native mutation must execute before the annual ledger closes')
    if structure_only:
        base, proposed = anchor.to_dict(), candidate.to_dict()
        for field in ('connections', 'schedules'):
            base.pop(field); proposed.pop(field)
        if base != proposed:
            raise ValueError('structure-only contrast changes more than wiring/schedules')
    return True


def edit_workflow(anchor, *, phase_updates, rewires):
    """Literal graph edits, with exact old edges and no auto-repair/rescheduling.

    ``rewires`` is a sequence of (old ConnectionSpec, new ConnectionSpec) pairs.
    Unknown IDs, nonunique/absent edges and duplicate replacements fail. The
    helper deliberately does not rewrite metadata, sources or parameters.
    Whole-SystemSpec candidates need not be produced by this helper.
    """
    if not isinstance(phase_updates, dict) or any(
            type(v) is not int or v < 0 for v in phase_updates.values()):
        raise ValueError('explicit nonnegative integer phase updates required')
    known = Counter(s.mechanism_id for s in anchor.schedules)
    if any(known[k] != 1 for k in phase_updates):
        raise ValueError('phase update must name an existing uniquely scheduled node')
    connections = list(anchor.connections)
    used = set()
    for old, new in rewires:
        if (not isinstance(old, ConnectionSpec) or not isinstance(new, ConnectionSpec)
                or old in used or anchor.connections.count(old) != 1):
            raise ValueError('rewire requires one exact unused original edge')
        used.add(old)
        connections[anchor.connections.index(old)] = new
    candidate = replace(anchor, connections=tuple(connections), schedules=tuple(
        replace(s, phase=phase_updates[s.mechanism_id]) if s.mechanism_id in phase_updates else s
        for s in anchor.schedules))
    require_workflow_candidate(anchor, candidate, structure_only=True)
    return candidate


def post_funding_cost_control(anchor):
    """Hand-designed timing diagnostic, NOT an automatically invented winner.

    Move existing liquidity code/effects and annual cost after the native grant
    stage. Read the actual post-grant world, not a stale pre-grant snapshot.
    No source, numeric parameter, native node or money supply is edited.
    """
    phases = {s.mechanism_id: s.phase for s in anchor.schedules}
    grant = phases['world.funding']
    if phases['world.communication'] <= grant + 3:
        raise ValueError('explicit free phases required; never rescale the graph implicitly')
    changes = (
        ('world.submission', 'next', 'world.costs', 'after', 'world.funding'),
        ('world.costs', 'next', 'world.selection', 'after', 'world.submission'),
        ('world.funding', 'next', 'world.communication', 'after', 'world.costs'),
        ('world.costs', 'world', 'native-feature-extractor', 'observations', 'world.submission'),
        ('world.submission', 'world', 'developer-liquidity-director', 'world', 'world.funding'),
    )
    pairs = []
    for source, port, target, target_port, replacement in changes:
        found = [e for e in anchor.connections if (e.source_mechanism, e.source_port,
            e.target_mechanism, e.target_port, e.latency) == (source, port, target, target_port, 0)]
        if len(found) != 1:
            raise ValueError('timing control requires its exact declared anchor edge')
        pairs.append((found[0], replace(found[0], source_mechanism=replacement)))
    return edit_workflow(anchor, phase_updates={'developer-liquidity-director': grant + 1,
        'developer-liquidity-effects': grant + 2, 'world.costs': grant + 3}, rewires=pairs)


def verify_workflow_interval(anchor, candidate, events, *, years):
    """Check exactly-once original effect witnesses, not just graph parsing.

    The runner supplies owner provenance after an implementation returns; a
    generated code node cannot impersonate a protected owner by choosing an
    event name. This reader assumes retained events are independently bound to
    the actual native checkpoint/stream; it is not a substitute for cold audit.
    """
    require_workflow_candidate(anchor, candidate)
    if type(years) is not int or years < 1:
        raise ValueError('positive completed native interval required')
    nodes = _protected(anchor)
    phases = {s.mechanism_id: s.phase for s in candidate.schedules}
    counts = Counter()
    sequences = {y: {} for y in range(1, years + 1)}
    for event in events:
        e = event.to_dict() if hasattr(event, 'to_dict') else event
        p = e['provenance']; identity = p.get('mechanism_id')
        if identity not in nodes or e['event_type'] not in (PHASE_EVENT, PLAN_EVENT):
            continue
        n = nodes[identity]; stage = n.implementation.split('.')[2]
        expected = PLAN_EVENT if stage == 'plan-effects' else PHASE_EVENT
        year = e['year']
        if (type(year) is not int or year not in sequences or e['event_type'] != expected
                or (stage != 'plan-effects' and e['payload'].get('stage') != stage)
                or p.get('implementation') != n.implementation or p.get('implementation_version') != n.version
                or p.get('system_fingerprint') != candidate.fingerprint
                or p.get('system_id') != candidate.system_id or p.get('period') != year
                or p.get('trigger') != 'annual' or e['phase'] != phases[identity]):
            raise ValueError('native workflow execution witness binding differs')
        counts[year, identity] += 1
        sequences[year][identity] = e['sequence']
    expected_counts = Counter({(y, identity): 1 for y in range(1, years + 1) for identity in nodes})
    if counts != expected_counts:
        raise ValueError('native workflow effects are missing or duplicated')
    ordered = [identity for identity in execution_order(candidate) if identity in nodes]
    for year, observed in sequences.items():
        if [observed[n] for n in ordered] != sorted(set(observed.values())):
            raise ValueError('native workflow execution order differs')
    return {'schema': 'scienceutopia.native-workflow-interval.v4', 'scope': SCOPE,
        'system_fingerprint': candidate.fingerprint, 'years': years,
        'native_effects_per_year': len(nodes), 'effect_witnesses': sum(counts.values()),
        'execution_order': list(execution_order(candidate)), 'cold_audit_replaced': False}
