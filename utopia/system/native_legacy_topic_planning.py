"""Explicit original core-plus-related topic actuation, not a new research law.

The historical core-only catalog capability is unchanged. This new capability
validates an authored choice, never chooses a shortest or higher-merit topic.
"""
from copy import deepcopy

from .code_mechanisms import sha
from .native_catalog_planning import catalog_contract, validate_catalog_assignment
from .runtime import GraphRuntimeError, MechanismEvent

ACTION = 'native.legacy-topic-project.v1'
EVENT = 'native.domain.legacy_topic_project_validated'


def eligible_topics(actor, *, catalog):
    """Original non-strict core/related union intersected with actual catalog.

    The original resolver looks up a selected permitted topic in DIRECTIONS_DICT.
    Unknown related labels are not invented into executable project directions.
    """
    rows = catalog['directions']
    if (catalog.get('schema') != 'scienceutopia.native-direction-catalog.v1'
            or sha(rows) != catalog.get('directions_sha256')
            or len({d['topic'] for d in rows}) != len(rows)):
        raise GraphRuntimeError('exact native catalog identity required')
    actual = {d['topic']: d for d in rows}
    core = actor.get('expertise')
    if (not isinstance(core, list) or not core
            or any(not isinstance(t, str) or t not in actual for t in core)):
        raise GraphRuntimeError('actual nonempty native core expertise required')
    topics = set(core)
    for topic in core:
        topics.update(actual[topic]['related_topics'])
    return sorted(topics & actual.keys())


def validate_legacy_topic_assignment(assignment, actor, *, year, catalog):
    """Reuse exact native content/duration/idle-state checks with explicit union."""
    expanded = deepcopy(actor)
    expanded['expertise'] = eligible_topics(actor, catalog=catalog)
    return validate_catalog_assignment(assignment, expanded, year=year, catalog=catalog)


def apply_legacy_topic_project(tx, payload, principal):
    from .native_open_domain import _native_project
    simulation = tx.kernel._simulation
    if getattr(simulation, 'is_exploration_experiment', None) is not False:
        raise GraphRuntimeError('legacy-topic project requires original non-strict native topic support')
    assignment = payload['assignment']
    if not isinstance(assignment, dict) or not isinstance(assignment.get('actor_id'), str):
        raise GraphRuntimeError('legacy-topic project requires an explicit native actor')
    actor = tx.require_native_author(assignment['actor_id'])
    if getattr(actor, '_filtered_candidates', None):
        raise GraphRuntimeError('legacy-topic project cannot replace filtered native candidates')
    expertise = getattr(actor, 'expertise', None)
    if not isinstance(expertise, list) or not expertise or any(not hasattr(d, 'to_dict') for d in expertise):
        raise GraphRuntimeError('actual original native expertise objects required')
    catalog = catalog_contract()
    actual = {d['topic']: d for d in catalog['directions']}
    if any(d.to_dict() != actual.get(d.topic) for d in expertise):
        raise GraphRuntimeError('native core expertise content differs from original catalog')
    snapshot = {'id': actor.id, 'can_author': actor.can_author, 'is_active': actor.is_active,
        'project_end_year': actor.project_end_year, 'expertise': [d.topic for d in expertise]}
    validate_legacy_topic_assignment(assignment, snapshot, year=tx.context.period, catalog=catalog)
    _native_project(tx, payload, principal)
    tx.events.append(MechanismEvent(EVENT, actor_ids=(actor.id,), payload={
        'origin_actor_id': principal, 'command_key': tx.command_key,
        'catalog_sha256': catalog['directions_sha256'], 'eligible_actor_before': snapshot,
        'eligible_topics': eligible_topics(snapshot, catalog=catalog),
        'assignment': deepcopy(assignment), 'shortest_or_merit_rule_enforced': False}))
