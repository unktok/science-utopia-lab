"""Passive collected-resource measurement of complete original-world trajectories.

This is model-internal resource use, not money, compute, scientific value or a
promotion rule. Importing it does not adopt or modify an optimization objective.
"""
from copy import deepcopy
import math
from pathlib import Path
from types import SimpleNamespace

from utopia.funding.accounting import ResourceLedger
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-collected-resource-cost.v1'
METRIC = 'native.collected_activity_resource_cost'
UNCOLLECTED_METRIC = 'native.uncollected_activity_resource_cost'
INSTRUMENT = 'collected_resource_cost_instrument'
COST_CATEGORIES = ('annual_research_cost', 'production_submission_cost',
                   'resubmission_cost', 'funding_application_cost')
CONTRACT = {
    'schema': SCHEMA,
    'included_collected_cost_categories': list(COST_CATEGORIES),
    'excluded_flow_categories': ['grant_income', 'industry_income',
                                 'institution_transfer_in', 'institution_transfer_out'],
    'population': 'all native can_author actors, including later entrants and inactive actors',
    'period': 'complete original annual ledgers1..declared num_years; year0 excluded',
    'uncollected_cost': 'separate diagnostic; never imputed as collected consumption',
    'units': 'native resource units, not money, compute, energy or welfare',
}


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _ledger(state, year):
    """Validate literal ledger evidence before asking its native reconciler."""
    raw = state.get('resource_ledger')
    if (not isinstance(raw, dict) or raw.get('schema_version') != 1
            or not isinstance(raw.get('transactions'), list)
            or not isinstance(raw.get('years'), dict)
            or set(raw['years']) != {str(y) for y in range(1, year + 1)}
            or not isinstance(raw.get('entry_years'), dict)):
        raise ValueError('complete original resource ledger required, not an unknown zero')
    ledger = ResourceLedger(raw)
    for event in ledger.transactions:
        if (not isinstance(event, dict) or type(event.get('year')) is not int
                or not 1 <= event['year'] <= year
                or event.get('category') not in ledger.categories
                or not isinstance(event.get('researcher_id'), str)
                or type(event.get('active_after')) is not bool
                or any(not _number(event.get(k)) for k in
                       ('requested_delta', 'delta', 'balance_before', 'balance_after', 'uncollected_cost'))
                or min(event['balance_before'], event['balance_after'], event['uncollected_cost']) < 0):
            raise ValueError('literal finite native resource transaction required')
        if ((event['category'] in ledger.income_categories and event['requested_delta'] < 0)
                or (event['category'] not in ledger.income_categories and event['requested_delta'] > 0)
                or not math.isclose(event['uncollected_cost'],
                    max(0, event['delta'] - event['requested_delta']), rel_tol=0, abs_tol=1e-9)):
            raise ValueError('native resource transaction sign or uncollected amount differs')
    return ledger


def from_states(states):
    """Measure saved annual ledgers without running agents, code or RNG.

    Physical/source/response audits remain separate prerequisites. These local
    checks do not certify that a trajectory came from an authorized experiment.
    """
    if not isinstance(states, list) or len(states) < 2:
        raise ValueError('initial and every declared annual native state required')
    contract = states[0]['portable']['contract']
    horizon = contract['simulation']['num_years']
    spec = states[0]['native_system']['spec']
    if type(horizon) is not int or horizon < 1 or len(states) != horizon + 1:
        raise ValueError('complete declared native horizon required, not a partial cost')
    annual = []
    previous = None
    for year, state in enumerate(states):
        if (type(state['year']) is not int or state['year'] != year
                or type(state['phase']) is not int or state['phase'] != (0 if year == 0 else 5)
                or type(state['native_system']['last_year']) is not int
                or state['native_system']['last_year'] != year
                or state['native_system']['spec'] != spec
                or state['portable']['contract'] != contract):
            raise ValueError('fresh fixed-contract complete native trajectory required')
        records = state['ecosystem_data']['agents']
        if (not isinstance(records, list)
                or any(not isinstance(a, dict) or not isinstance(a.get('id'), str)
                       or not a['id'] or type(a.get('can_author')) is not bool for a in records)
                or len({a['id'] for a in records}) != len(records)):
            raise ValueError('distinct literal native actor records required')
        authors = [a for a in records if a['can_author']]
        if any(type(a.get('is_active')) is not bool or not _number(a.get('resources'))
               or a['resources'] < 0 for a in authors):
            raise ValueError('literal finite author resources and activity flags required')
        ledger = _ledger(state, year)
        raw = ledger.to_dict()
        if year == 0:
            if raw['entry_years']:
                raise ValueError('fresh initial resource ledger required')
        else:
            if (ledger.transactions[:len(previous['transactions'])] != previous['transactions']
                    or any(raw['years'][y] != row for y, row in previous['years'].items())
                    or any(raw['entry_years'].get(a) != y for a, y in previous['entry_years'].items())
                    or any(e['year'] != year for e in ledger.transactions[len(previous['transactions']):])):
                raise ValueError('original cumulative resource ledger prefix changed')
            rows = raw['years'][str(year)]
            population = {a['id']: SimpleNamespace(**{k: a[k] for k in
                          ('id', 'can_author', 'resources', 'is_active')}) for a in authors}
            if set(rows) != set(population):
                raise ValueError('every native author requires an accounted annual balance')
            for aid, row in rows.items():
                if (row.get('researcher_id') != aid or type(row.get('year')) is not int
                        or row['year'] != year or type(row.get('opening_active')) is not bool
                        or type(row.get('closing_active')) is not bool
                        or row['closing_active'] != population[aid].is_active
                        or any(not _number(row.get(k)) or row[k] < 0 for k in
                               ('opening_balance', 'closing_balance'))):
                    raise ValueError('literal closed native annual balance required')
                prior_rows = previous['years'].get(str(year - 1), {})
                if aid in prior_rows and row['opening_balance'] != prior_rows[aid]['closing_balance']:
                    raise ValueError('unexplained resource change between annual boundaries')
            reconciled = ledger.reconcile(year, population, require_closed=True)
            costs = {category: math.fsum(row[category] for row in reconciled)
                     for category in COST_CATEGORIES}
            uncollected_by_category = {category: math.fsum(event['uncollected_cost']
                for event in ledger.transactions if event['year'] == year and event['category'] == category)
                for category in COST_CATEGORIES}
            uncollected = math.fsum(uncollected_by_category.values())
            if any(not math.isfinite(v) or v < 0 for v in [*costs.values(), uncollected]):
                raise ValueError('finite nonnegative collected and uncollected costs required')
            annual.append({'year': year, 'costs_by_category': costs,
                'uncollected_costs_by_category': uncollected_by_category,
                'collected_activity_cost': math.fsum(costs.values()),
                'uncollected_activity_cost': uncollected,
                'reconciled_authors': sorted(reconciled, key=lambda row: row['researcher_id']),
                'ledger_sha256': digest(raw)})
        previous = raw
    return {'schema': SCHEMA, 'contract': deepcopy(CONTRACT),
        'instrument_contract_sha256': digest(CONTRACT), 'annual': annual,
        'value': math.fsum(row['collected_activity_cost'] for row in annual),
        'uncollected_value': math.fsum(row['uncollected_activity_cost'] for row in annual),
        'world_contract_sha256': digest(contract), 'system_sha256': digest(spec),
        'scope': 'Passive reconstruction with native ResourceLedger.reconcile(require_closed=True). '
            'Actual collected costs only; income and conserving transfers excluded. '
            'Partial horizons, missing ledgers and inconsistent balances have unknown cost, '
            'never zero. Not scientific truth, social welfare, money, compute or a merit veto.',
        'new_model_calls': 0, 'new_code_executions': 0}


def measure_from_checkpoints(base, paths):
    """Append metrics without overwriting any existing measurement or raw file."""
    from utopia.system import SystemSpec
    paths = [Path(p) for p in paths]
    if len({p.name for p in paths}) != len(paths):
        raise ValueError('distinct original annual checkpoint names required')
    hashes = {p.name: file_sha256(p) for p in paths}
    states = [read_portable_checkpoint(p) for p in paths]
    result = from_states(states)
    if (base['system_fingerprint'] != SystemSpec.from_dict(states[-1]['native_system']['spec']).fingerprint
            or INSTRUMENT in base or METRIC in base['metrics'] or UNCOLLECTED_METRIC in base['metrics']):
        raise ValueError('completed literal native system and nonoverwriting instrument required')
    if hashes != {p.name: file_sha256(p) for p in paths}:
        raise ValueError('original native annual states changed during measurement')
    output = deepcopy(base)
    output['metrics'][METRIC] = {'status': 'measured', 'value': result['value']}
    output['metrics'][UNCOLLECTED_METRIC] = {'status': 'measured', 'value': result['uncollected_value']}
    output[INSTRUMENT] = {**result, 'checkpoint_sha256s': hashes}
    return output


def measure(simulation, base):
    """Existing native-world measurement_adapter entry point; no world changes."""
    if (simulation.native_system.last_year != simulation.num_years
            or base['system_fingerprint'] != simulation.native_system.spec.fingerprint):
        raise ValueError('completed literal native simulation required')
    paths = [Path(simulation.output_dir) / f'portable_checkpoint_year_{year}.json.gz'
             for year in range(simulation.num_years + 1)]
    output = measure_from_checkpoints(base, paths)
    if output[INSTRUMENT]['system_sha256'] != digest(simulation.native_system.spec.to_dict()):
        raise ValueError('live native system differs from original saved trajectory')
    return output
