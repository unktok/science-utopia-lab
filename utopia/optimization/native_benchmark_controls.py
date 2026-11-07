"""Explicit developer controls in the unchanged native researcher world.

These are baselines, never discoveries or hidden repairs of authored proposals.
The score threshold reads original reviews; empty cycles use the existing
native empty_cycle sentinel, not fabricated paper/conference identities.
"""
from dataclasses import replace

from utopia.system import SystemSpec, validate_system_spec
from utopia.system.native_kernel import legacy_world_system
from utopia.system.native_open_examples import open_native_system
from utopia.system.native_selection_slot import RANK_RATE_SOURCE
from utopia.system.design_patch import clone

THRESHOLD_SOURCE = '''def step(context):
    world = context['inputs']['observations'][0]['payload']
    rule = context['parameters']['control_rule']
    threshold = context['parameters']['score_threshold']
    decisions = []
    for conf in world['conferences']['conferences']:
        for paper in conf['submitted_papers']:
            reviews = conf['reviews'].get(paper['id'], [])
            score = sum(r['overall_score'] for r in reviews) / len(reviews) if reviews else 0.0
            accepted = rule == 'accept-all' or (rule == 'threshold' and bool(reviews) and score >= threshold)
            decisions.append({'payload': {'paper_id': paper['id'],
                'conference_id': conf['conference_id'], 'decision': 'accept' if accepted else 'reject',
                'final_score': score}})
    return {'outputs': {'decisions': decisions or [{'payload': {'empty_cycle': True}}],
        'next': [{'payload': {'year': context['period']}}], 'world': [{'payload': world}]},
        'state': {'cycles': context['state'].get('cycles', 0) + 1}}
'''


def selection_control(parent, *, rule, threshold=0.):
    if rule not in {'accept-all', 'reject-all', 'threshold', 'rank-rate'}:
        raise ValueError('unknown explicitly developer-authored control')
    if type(threshold) not in (int, float) or not 0 <= threshold <= 5:
        raise ValueError('threshold must be finite within the native reviewer scale')
    data = clone(parent.to_dict())
    node = next(n for n in data['mechanisms'] if n['mechanism_id'] == 'world.selection')
    if node['implementation'] != 'code.python.v1':
        raise ValueError('control needs an existing literal selection code slot')
    params = node['parameters']
    params['code_artifact']['source'] = RANK_RATE_SOURCE if rule == 'rank-rate' else THRESHOLD_SOURCE
    params['code_artifact']['label'] = 'Developer benchmark control: ' + rule
    if rule != 'rank-rate':
        params.update(control_rule=rule, score_threshold=float(threshold))
    result = SystemSpec.from_dict(data)
    validate_system_spec(result).require_valid()
    return result


def without_review(parent):
    """An explicit structural control, not an assumed zero-cost review proxy."""
    # The seed's review successor and world observation consumers are rewired
    # to the preceding real cost stage. Other native phases remain untouched.
    edges = [replace(e, source_mechanism='world.costs') if e.source_mechanism == 'world.review' else e
        for e in parent.connections if e.target_mechanism != 'world.review']
    result = replace(parent,
        mechanisms=tuple(n for n in parent.mechanisms if n.mechanism_id != 'world.review'),
        schedules=tuple(s for s in parent.schedules if s.mechanism_id != 'world.review'),
        connections=tuple(edges))
    validate_system_spec(result).require_valid()
    return result


def control_systems(image_id):
    seed = open_native_system(image_id)
    systems = {'legacy': legacy_world_system(), 'open-seed': seed,
        'open-rank-rate': selection_control(seed, rule='rank-rate'),
        'open-accept-all': selection_control(seed, rule='accept-all'),
        'open-reject-all': selection_control(seed, rule='reject-all'),
        'open-score-3': selection_control(seed, rule='threshold', threshold=3.),
        'open-score-4': selection_control(seed, rule='threshold', threshold=4.),
        'open-no-review-accept-all': without_review(selection_control(seed, rule='accept-all'))}
    for spec in systems.values():
        validate_system_spec(spec).require_valid()
    return systems


def objective_specs():
    """A fixed trade-off, not an undisclosed normative acceptance constraint."""
    from pathlib import Path
    import json
    root = Path(__file__).resolve().parents[2] / 'research/objectives/losses'
    losses = {name: json.loads((root / (identity + '.json')).read_text()) for name, identity in [
        ('throughput', 'native-joint-v5-throughput'),
        ('efficiency', 'native-reviewed-production-efficiency-v13')]}
    losses['selective'] = {'schema': 'scienceutopia.loss-spec.v1',
        'id': 'native-selective-production-benchmark-v2', 'version': '1',
        'status': 'engineering-only', 'optimization_seed_role': 'development', 'direction': 'minimize',
        'per_run': {'intercept': 0., 'terms': [
            {'metric_id': 'native.accepted_decisions', 'slice_id': None, 'coefficient': 4.},
            {'metric_id': 'native.accepted_peer_score_sum', 'slice_id': None, 'coefficient': -1.},
            {'metric_id': 'native.review_records', 'slice_id': None, 'coefficient': .1}]},
        'across_seeds': {'aggregation': 'mean_plus_population_sd', 'dispersion_weight': 0., 'minimum_valid_runs': 1}}
    return losses
