"""Small all-slot SCRIPTED data fixtures, not new native observations."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest

from scripts.reports import native_priority_method_readout_v1 as r
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.system.design_patch import digest


def seal(value): return {**value, 'content_sha256': digest(value)}


def fixture():
    def loss(metric):
        return {'schema': 'scienceutopia.loss-spec.v1', 'id': 'SCRIPTED-' + metric,
            'version': '1', 'status': 'SCRIPTED-not-science', 'optimization_seed_role': 'development',
            'direction': 'minimize', 'per_run': {'intercept': 0.,
                'terms': [{'metric_id': metric, 'slice_id': None, 'coefficient': 1.}]},
            'across_seeds': {'aggregation': 'mean_plus_population_sd', 'dispersion_weight': 0., 'minimum_valid_runs': 1}}
    program = {'mechanisms': [{'mechanism_id': 'SCRIPTED-data-only', 'parameters': {}}],
               'connections': [], 'schedules': []}
    losses = {k: loss(k) for k in ('throughput', *r.OBJECTIVES)}
    order = [{'method': m, 'replication': h, 'objective': o, 'generation': g}
             for g in range(2) for h in range(2) for o in r.OBJECTIVES for m in r.METHODS]
    plan = seal({'schema': r.STUDY + '.plan', 'source_commit': 'a' * 40,
        'methods': list(r.METHODS), 'objectives': list(r.OBJECTIVES), 'replication_seeds': [1, 2],
        'generations': 2, 'schedule': order, 'losses': losses,
        'reference_order': ['zero', 'terminal', 'literal'], 'optimizer_reference_labels': ['zero', 'terminal']})
    worlds, refs, slots = [], {}, []

    def observed(identity, objective, values, *, key=None, status='complete'):
        measurements = [] if status != 'complete' else [{'run_id': 'SCRIPTED-' + identity,
            'metrics': {k: {'status': 'measured', 'value': v} for k, v in values.items()}}]
        scores = {k: evaluate_loss(spec, measurements) for k, spec in losses.items()}
        observation = {'observation_id': 'observation-' + identity, 'suggestion_id': identity,
            'candidate': deepcopy(program), 'status': status, 'loss': scores[objective]['loss'],
            'metadata': {'measurements': measurements, 'loss_evaluation': scores[objective],
                         'loss_spec_sha256': loss_spec_sha256(losses[objective]),
                         'technical_failures': [] if status == 'complete' else [{'SCRIPTED': 'native failure'}]}}
        world = {'role': 'developer-reference' if key is None else
            'workflow-own-proposal' if key[0] == r.METHODS[2] else 'numeric-own-proposal',
            'identity': identity, 'system': deepcopy(program), 'status': status,
            'scores': {k: s['loss'] for k, s in scores.items()}}
        if key is not None: world.update(method=key[0], optimizer_history=key[1], objective=key[2])
        worlds.append(world)
        return observation

    for label, u, c in [('zero', -10., -8.), ('terminal', -10., -9.), ('literal', -9., -7.)]:
        refs[label] = observed('workflow-reference-' + label, 'throughput',
                               {'throughput': -10., r.OBJECTIVES[0]: u, r.OBJECTIVES[1]: c})
    for slot in order:
        # Deliberately identical ids across EVERY method/history/objective.
        identity = 'shared-id-g' + str(slot['generation'])
        values = {'throughput': -10., r.OBJECTIVES[0]: -11., r.OBJECTIVES[1]: -10.}
        obs = observed(identity, slot['objective'], values, key=r.history_key(slot))
        slots.append({'slot': deepcopy(slot), 'suggestion': {'suggestion_id': identity, 'candidate': deepcopy(program)},
            'observation': obs, 'parent_system': deepcopy(program), 'generation_error': None})
    selected = {m: {str(h): {} for h in range(2)} for m in r.METHODS}
    for method in r.METHODS:
        for h in range(2):
            for objective in r.OBJECTIVES:
                selected[method][str(h)][objective] = {'loss': -11. if objective == r.OBJECTIVES[0] else -10.,
                    'completed_submissions': 2, 'all_tied_ids': ['shared-id-g0', 'shared-id-g1'],
                    'selected_id': 'shared-id-g0', 'system': deepcopy(program),
                    'reference_loss': -10. if objective == r.OBJECTIVES[0] else -9.}
    selection = seal({'selected': selected, 'baseline_fallback': False, 'held_out_evaluation': False})
    audit = seal({'schema': r.STUDY + '.audit', 'source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'source_proof': {'status': 'verified-exact-source-closure',
            'SCRIPTED': 'synthetic claim only, not proof of an actual run'},
        'closure': {'terminal': {'status': 'closed', 'consumed_slots': 24, 'observations': 27}},
        'worlds': worlds, 'selection': selection, 'new_model_calls': 0, 'new_code_executions': 0,
        'held_out_evaluation': False})
    return plan, audit, slots, refs


def test_all_24_compound_cells_and_27_worlds_survive_shared_suggestion_ids():
    p, a, slots, refs = fixture(); result = r.analyze(p, a, slots, refs)
    assert len(result['slots']) == len({s['cell_id'] for s in result['slots']}) == 24
    assert result['coverage'] == {'declared_own_slots': 24, 'complete_own_slots': 24,
        'generation_nulls': 0, 'execution_or_measurement_nulls': 0, 'physical_worlds': 27}
    assert result['nonunique_suggestion_ids_across_compound_cells'] == {'shared-id-g0': 12, 'shared-id-g1': 12}
    assert len(result['selected']) == len(result['paths']) == 12
    assert all(s['suggestion_id'] == 'shared-id-g0' for s in result['selected'])
    assert all(s['own_minus_reference'] < 0 for s in result['selected'])
    assert all(len(path) == 2 for path in result['paths'].values())
    assert not result['selection_changed'] and not result['method_superiority_claimed']
    assert not result['publication_ready'] and result['new_model_calls'] == result['new_code_executions'] == 0


@pytest.mark.parametrize('edit', ['drop-slot', 'reorder-slot', 'duplicate-world', 'wrong-method',
                                'changed-score', 'foreign-selection', 'missing-world', 'imputed-null'])
def test_contradictory_or_partial_projection_is_rejected(edit):
    p, a, slots, refs = fixture()
    if edit == 'drop-slot': slots.pop()
    elif edit == 'reorder-slot': slots[0], slots[1] = slots[1], slots[0]
    elif edit == 'duplicate-world': a['worlds'].append(deepcopy(a['worlds'][3]))
    elif edit == 'wrong-method': a['worlds'][3]['method'] = 'unlisted-method'
    elif edit == 'changed-score': slots[0]['observation']['loss'] = 0.
    elif edit == 'foreign-selection':
        a['selection']['selected'][r.METHODS[0]]['0'][r.OBJECTIVES[0]]['selected_id'] = 'reference-fallback'
    elif edit == 'missing-world': a['worlds'].pop()
    else:
        slots[0]['observation']['status'] = 'failed'  # Retained positive measurement cannot be a null.
    a = seal(r.literal(a))
    with pytest.raises(ValueError): r.analyze(p, a, slots, refs)


def test_generation_nulls_keep_slots_and_reference_incumbent_without_own_fallback():
    p, a, slots, refs = fixture(); method = r.METHODS[2]; objective = r.OBJECTIVES[0]
    for entry in slots:
        if r.history_key(entry['slot']) != (method, 0, objective): continue
        entry.update(suggestion=None, observation=None, generation_error={'type': 'SCRIPTED-generation-failure'})
    a['worlds'] = [w for w in a['worlds'] if w.get('method') != method or w.get('optimizer_history') != 0 or w['objective'] != objective]
    a['closure']['terminal']['observations'] = 25
    a['selection']['selected'][method]['0'][objective] = {'loss': None, 'completed_submissions': 0,
        'all_tied_ids': [], 'selected_id': None, 'system': None, 'reference_loss': -10.}
    a = seal(r.literal(a)); result = r.analyze(p, a, slots, refs)
    assert result['coverage']['generation_nulls'] == 2 and result['coverage']['physical_worlds'] == 25
    path = result['paths'][method + '/0/' + objective]
    assert all(x['observed_loss'] is x['best_own_loss'] is None for x in path)
    assert all(x['best_known_including_visible_parent'] == -10. for x in path)
    selected = next(s for s in result['selected'] if (s['method'], s['replication'], s['objective']) == (method, 0, objective))
    assert selected['cell_id'] is selected['loss'] is None


def test_export_path_guard_runs_before_reading_or_creating_source_local_destination(tmp_path, monkeypatch):
    reader = tmp_path / 'reader'; reader.mkdir(); alias = tmp_path / 'external-looking'; alias.symlink_to(reader)
    monkeypatch.setattr(r, 'ROOT', reader); monkeypatch.setattr(r, 'pinned_revision', lambda path: 'a' * 40)
    for out in (reader / 'out', alias / 'out', tmp_path / 'science/out', tmp_path / 'raw/out'):
        args = SimpleNamespace(run=tmp_path / 'raw', frozen_source=tmp_path / 'science', output=out)
        with pytest.raises(ValueError, match='outside reader'): r.export(args)
        assert not out.exists()


def test_plot_data_keeps_six_panels_twelve_histories_and_frozen_cells_without_rendering():
    from scripts.figures.native_priority_method_paths_v1 import plot_data
    p, a, slots, refs = fixture(); report = r.analyze(p, a, slots, refs)
    panels = plot_data(report)
    assert len(panels) == 6 and sum(len(p['histories']) for p in panels) == 12
    assert all(len(h['path']) == 2 for p in panels for h in p['histories'])
    assert len({h['selected_cell_id'] for p in panels for h in p['histories']}) == 12
    report['paths'][r.METHODS[0] + '/0/' + r.OBJECTIVES[0]].pop()
    with pytest.raises(ValueError, match='both actual generations'): plot_data(report)


def test_execution_null_keeps_its_world_and_never_becomes_zero_loss():
    p, a, slots, refs = fixture(); entry = slots[0]; o = entry['observation']
    o.update(status='failed', loss=None)
    o['metadata'].update(measurements=[], technical_failures=[{'type': 'SCRIPTED-technical-failure'}],
        loss_evaluation=evaluate_loss(p['losses'][entry['slot']['objective']], []))
    target = (*r.history_key(entry['slot']), o['suggestion_id'])
    world = next(w for w in a['worlds'] if r.world_key(w) == target)
    world.update(status='failed', scores={k: None for k in p['losses']})
    selected = a['selection']['selected'][r.METHODS[0]]['0'][r.OBJECTIVES[0]]
    selected.update(completed_submissions=1, all_tied_ids=['shared-id-g1'], selected_id='shared-id-g1')
    a = seal(r.literal(a)); result = r.analyze(p, a, slots, refs)
    assert result['coverage']['execution_or_measurement_nulls'] == 1
    assert result['coverage']['physical_worlds'] == 27 and result['coverage']['complete_own_slots'] == 23
    path = result['paths'][r.METHODS[0] + '/0/' + r.OBJECTIVES[0]]
    assert path[0]['observed_loss'] is path[0]['best_own_loss'] is None
    assert path[0]['best_known_including_visible_parent'] == -10. and path[1]['best_own_loss'] == -11.


@pytest.mark.parametrize('duplicated', ['audit', 'cost'])
def test_export_rejects_same_file_pair_before_projecting_any_observation(tmp_path, monkeypatch, duplicated):
    monkeypatch.setattr(r, 'ROOT', tmp_path / 'reader'); monkeypatch.setattr(r, 'pinned_revision', lambda path: 'a' * 40)
    audits = [tmp_path / 'a1', tmp_path / ('a1' if duplicated == 'audit' else 'a2')]
    costs = [tmp_path / 'c1', tmp_path / ('c1' if duplicated == 'cost' else 'c2')]
    args = SimpleNamespace(run=tmp_path / 'raw', frozen_source=tmp_path / 'science', output=tmp_path / 'out',
        audit_one=audits[0], audit_two=audits[1], cost_one=costs[0], cost_two=costs[1])
    with pytest.raises(ValueError, match='distinct matching paired'): r.export(args)
    assert not args.output.exists()
