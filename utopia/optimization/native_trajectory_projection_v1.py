"""Fixed-field view of a completed native checkpoint, not a new simulator.

Callers must separately establish physical/source evidence and allowed own-data
access. These checks bind and reconcile the supplied data; they are not a full
audit, a causal explanation, a loss or an institutional admission criterion.
No files, models, generated Python, network or optimizer state are accessed.
"""
import math
import re
from types import SimpleNamespace

from utopia.funding.accounting import ResourceLedger
from utopia.system import SystemSpec
from utopia.system.design_patch import digest

SCHEMA = 'scienceutopia.native-trajectory-projection.v1'
EVENT_TYPES = (
    'native.system.phase_executed', 'generated.code_executed',
    'native.domain.project_applied', 'native.domain.catalog_project_validated',
    'native.system.research_plan_applied', 'native.system.resource_transferred',
    'native.system.context_delivered', 'native.tensor.executed',
    'native.process.iteration', 'native.process.completed',
)


def _integer(value, label, *, lower=0):
    if type(value) is not int or value < lower:
        raise ValueError('literal integer required: ' + label)
    return value


def _number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite number required: ' + label)
    return value


def _text(value, label):
    if not isinstance(value, str) or not value:
        raise ValueError('nonempty string required: ' + label)
    return value


def _assignment(value):
    """Literal recorded assignment, never an inferred plan or duration."""
    return {'actor_id': _text(value['actor_id'], 'assignment actor'),
        'topic': _text(value['direction']['topic'], 'assignment topic'),
        'duration': _integer(value['direction']['years'], 'assignment duration', lower=1),
        'start_year': _integer(value['project_start_year'], 'assignment start', lower=1),
        'end_year': _integer(value['project_end_year'], 'assignment end', lower=1)}


def project_checkpoint(state, *, source_commit, system_fingerprint, seed, years, checkpoint_file_sha256):
    """Project completed fresh-world data; never infer missing annual vectors.

    Resource rows come from closed annual ledger records, not final resources
    copied backwards. Plan snapshots, applied commands and tracked new content
    are distinct; tracked content counts do not count all submission attempts.
    A failed projection raises, not a fabricated trace or scientific penalty.
    This prototype is not connected to any author/campaign or measurement hook.
    The caller binds actual checkpoint bytes. Decoded native states can contain
    sets, tuples and shared references; hashing them as ordinary JSON is wrong.
    This pure function checks digest syntax, not the caller's file/physical proof.
    """
    _integer(years, 'horizon', lower=1); _integer(seed, 'seed')
    if not isinstance(checkpoint_file_sha256, str) or not re.fullmatch('[0-9a-f]{64}', checkpoint_file_sha256):
        raise ValueError('caller-bound checkpoint file SHA256 required')
    native = state['native_system']; contract = state['portable']['contract']
    binding = contract['binding']
    _integer(state['year'], 'checkpoint year', lower=1)
    _integer(native['last_year'], 'kernel year', lower=1)
    _integer(binding['seed'], 'bound seed')
    if (state['year'] != years or state['phase'] != 5 or native['last_year'] != years
            or binding['seed'] != seed or binding['science_config']['source_commit'] != source_commit
            or binding['cell'] != system_fingerprint
            or SystemSpec.from_dict(native['spec']).fingerprint != system_fingerprint
            or contract['native_system']['system_fingerprint'] != system_fingerprint):
        raise ValueError('completed source/system/seed/horizon binding differs')
    ledger = ResourceLedger(state['resource_ledger'])
    if set(ledger.years) != {str(y) for y in range(1, years + 1)}:
        raise ValueError('complete consecutive closed ledger years required')
    events = native['events']; event_ids = set(); prior_sequence = -1; prior_year = 0
    for event in events:
        year = _integer(event['year'], 'event year', lower=1)
        sequence = _integer(event['sequence'], 'event sequence')
        if (year > years or year < prior_year or sequence <= prior_sequence
                or event['event_id'] in event_ids):
            raise ValueError('event chronology/identity differs')
        event_ids.add(event['event_id']); prior_sequence = sequence; prior_year = year
    papers = state['paper_tracker']['papers']; ids = set()
    for paper in papers:
        identity = _text(paper['id'], 'paper id')
        if identity in ids or _integer(paper['year'], 'tracked paper year', lower=1) > years:
            raise ValueError('tracked paper identity/year differs')
        ids.add(identity)
        for decision in paper['review_history']:
            if (_integer(decision['year'], 'decision year', lower=1) > years
                    or decision['decision'] not in ('accept', 'reject')):
                raise ValueError('literal accept/reject history in horizon required')
    annual = []; previous = {}
    for year in range(1, years + 1):
        rows = ledger.years[str(year)]; population = {}
        for identity, row in rows.items():
            if row['researcher_id'] != identity or _integer(row['year'], 'accounting year', lower=1) != year:
                raise ValueError('annual actor identity differs')
            if type(row['opening_active']) is not bool or type(row['closing_active']) is not bool:
                raise ValueError('recorded annual activity flags required')
            for key in ('opening_balance', 'closing_balance', 'residual', 'uncollected_cost', *ledger.categories):
                _number(row[key], key)
            if (row['opening_balance'] < 0 or row['closing_balance'] < 0
                    or any(row[key] < 0 for key in ('uncollected_cost', *ledger.categories))):
                raise ValueError('nonnegative actual balances/collected amounts required')
            if identity in previous and row['opening_balance'] != previous[identity]['closing_balance']:
                raise ValueError('annual opening does not match preceding closing')
            population[identity] = SimpleNamespace(id=identity, can_author=True,
                resources=row['closing_balance'], is_active=row['closing_active'])
        reconciled = ledger.reconcile(year, population, require_closed=True)
        if {r['researcher_id']: r for r in reconciled} != rows:
            raise ValueError('recorded category/activity totals differ from ledger reconciliation')
        actors = [{'actor_id': identity, **{key: row[key] for key in
            ('opening_balance', 'closing_balance', 'opening_active', 'closing_active',
             'residual', 'uncollected_cost', *ledger.categories)}} for identity, row in sorted(rows.items())]
        phases = []; commands = []; plans = []; counts = {kind: 0 for kind in EVENT_TYPES}
        omitted_events = 0
        for event in events:
            if event['year'] != year:
                continue
            kind = event['event_type']
            if kind in counts: counts[kind] += 1
            else: omitted_events += 1
            if kind == 'native.system.phase_executed':
                phases.append({'event_id': event['event_id'], 'sequence': event['sequence'],
                    'mechanism_id': event['provenance']['mechanism_id'],
                    'stage': event['payload']['stage'], 'phase': event['phase']})
            elif kind == 'native.domain.project_applied':
                commands.append({'event_id': event['event_id'],
                    'assignment': _assignment(event['payload']['assignment'])})
            elif kind == 'native.system.research_plan_applied':
                plans.append({'event_id': event['event_id'], 'assignments': [
                    _assignment(a) for a in event['payload']['base_plan']['plan']['assignments']]})
        decisions = [(p['id'], d['decision']) for p in papers for d in p['review_history'] if d['year'] == year]
        annual.append({'year': year, 'authors': actors,
            'native_phases_in_recorded_order': phases, 'recorded_event_counts': counts,
            'omitted_other_event_count': omitted_events,
            'applied_project_commands': commands, 'base_native_plan_snapshots': plans,
            'new_tracked_contents': sum(p['year'] == year for p in papers),
            'accepted_decision_occurrences': sum(d == 'accept' for _, d in decisions),
            'accepted_distinct_contents_this_year': len({p for p, d in decisions if d == 'accept'}),
            'rejected_decision_occurrences': sum(d == 'reject' for _, d in decisions)})
        previous = rows
    result = {'schema': SCHEMA, 'source_commit': source_commit, 'system_fingerprint': system_fingerprint,
        'seed': seed, 'years': years, 'checkpoint_file_sha256': checkpoint_file_sha256, 'annual': annual,
        'omitted_fields': ['paper title/abstract/topics, reviewer/critic bodies and written scores',
            'institution-generated free prose and nonselected event types/payloads',
            'operational paths/clocks and nonprojected checkpoint fields'],
        'scope': 'Fixed-field native records, not inferred within-phase vectors, scientific value, '
            'a causal explanation, full physical/source audit or authority to expose another bank/unused data.',
        'author_or_measurement_connection_implemented': False, 'loss_or_eligibility_changed': False,
        'new_model_calls': 0, 'new_code_executions': 0}
    result['content_sha256'] = digest(result)
    return result
