"""Pure SCRIPTED readout fixtures; not actual native/cold/unused evidence."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from scripts.reports import native_priority_fixed_evaluation_v1 as module
from scripts.native_priority_fixed_bank_v1 import freeze_bank, planned_jobs
from scripts.reports.native_priority_method_readout_v1 import METHODS, OBJECTIVES
from tests.reports.test_native_priority_fixed_bank_v1 import inputs
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def seal(value):
    value = {k: v for k, v in deepcopy(value).items() if k != 'content_sha256'}
    return {**value, 'content_sha256': digest(value)}


def fixture(*, missing=False, failed=False, different=False):
    original, old_audit, slots, refs = inputs()
    if missing:
        target = (METHODS[2], 0, OBJECTIVES[0])
        for entry in slots:
            s = entry['slot']
            if (s['method'], s['replication'], s['objective']) == target:
                entry.update(suggestion=None, observation=None, generation_error={'SCRIPTED': 'generation failure'})
        old_audit['worlds'] = [w for w in old_audit['worlds']
            if (w.get('method'), w.get('optimizer_history'), w.get('objective')) != target]
        old_audit['closure']['terminal']['observations'] = 25
        old_audit['selection']['selected'][target[0]]['0'][target[2]] = {'loss': None, 'completed_submissions': 0,
            'all_tied_ids': [], 'selected_id': None, 'system': None, 'reference_loss': -10.}
        old_audit['selection'] = seal(old_audit['selection']); old_audit = seal(old_audit)
    bank = freeze_bank(original, old_audit, slots, refs)
    if different:
        # This is a synthetic bank perturbation, not a fabricated native gain.
        bank['entries'][3]['system']['SCRIPTED-literal-program-difference'] = True
        bank = seal(bank)
    jobs = planned_jobs(bank, deepcopy(module.SEEDS))['jobs']
    p = seal({'schema': module.STUDY + '.plan', 'source_commit': 'c' * 40, 'fixed_selection': bank,
        'origin_audit_content_sha256': old_audit['content_sha256'], 'losses': original['losses'],
        'evaluation': {'seeds': deepcopy(module.SEEDS)}, 'jobs': jobs,
        'claims': {'candidate_reselection': False, 'reference_fallback': False}})
    worlds = []
    for job in jobs:
        status = 'failed' if failed and job['seed'] == module.SEEDS[1] else 'complete'
        value = -7. if job['system'].get('SCRIPTED-literal-program-difference') else -10.
        metrics = {k: {'status': 'measured', 'value': value} for k in p['losses']}
        metrics.update({k: {'status': 'measured', 'value': 1.} for k in module.METRICS})
        measurements = [{'run_id': job['identity'], 'metrics': metrics,
            'native_workflow_interval': {'SCRIPTED': 'not actual v6 proof'},
            module.INSTRUMENT: {'annual': [{'year': 1, 'collected_activity_cost': 1., 'uncollected_activity_cost': 0.}]}}]
        if status == 'failed': measurements = []
        scores = {k: evaluate_loss(v, measurements)['loss'] for k, v in p['losses'].items()}
        worlds.append({**deepcopy(job), 'role': 'selection-fixed-evaluation', 'status': status,
            'measurements': measurements, 'scores': scores})
    audit = seal({'schema': module.STUDY + '.audit', 'source_commit': p['source_commit'],
        'plan_sha256': p['content_sha256'], 'source_proof': {'status': 'verified-exact-source-closure',
            'SCRIPTED': 'synthetic assertion, not original-source provenance'},
        'closure': {'terminal': {'status': 'closed', 'completed_jobs': len(jobs)}},
        'worlds': worlds, 'fixed_selection': deepcopy(bank),
        'origin_audit_content_sha256': old_audit['content_sha256'], 'held_out_world_seeds': True,
        'new_model_calls': 0, 'new_code_executions': 0})
    return p, audit


def test_all_labels_conditions_and_predeclared_contrasts_with_physical_sharing():
    p, a = fixture(); before = deepcopy((p, a)); result = module.summarize(p, a)
    assert (p, a) == before
    assert result['coverage'] == {'logical_policy_labels': 15, 'logical_rows': 30, 'physical_worlds': 2,
        'complete_physical_worlds': 2, 'failed_physical_worlds': 0, 'selection_unavailable_rows': 0}
    assert len(result['contrast_definitions']) == 54 and len(result['fixed_policy_contrasts']) == 108
    assert len({d['id'] for d in result['contrast_definitions']}) == 54
    assert all(c['same_physical_job'] and all(v == 0 for v in c['differences'].values())
        for c in result['fixed_policy_contrasts'])
    assert all(row['annual_resources'] for row in result['physical_rows'])
    assert all('development_initial_reference_label' in row for row in result['logical_rows'] if row['role'] == 'own-selection')
    assert not result['selection_changed'] and not result['method_superiority_claimed'] and not result['publication_ready']


def test_failed_physical_world_is_not_zero_or_replaced_by_another_condition():
    p, a = fixture(failed=True); result = module.summarize(p, a)
    assert result['coverage']['failed_physical_worlds'] == 1
    assert sum(row['status'] == 'failed' for row in result['logical_rows']) == 15
    assert all(all(v is None for v in row['differences'].values())
        for row in result['fixed_policy_contrasts'] if row['seed'] == module.SEEDS[1])
    for summary in result['descriptive_contrast_summaries']:
        assert all(s['available_pairs'] == 1 and s['missing_seeds'] == [module.SEEDS[1]] for s in summary['scores'].values())


def test_absent_selection_retains_two_logical_null_rows_without_fallback():
    p, a = fixture(missing=True); result = module.summarize(p, a)
    assert result['coverage']['logical_rows'] == 30 and result['coverage']['selection_unavailable_rows'] == 2
    missing = [r for r in result['logical_rows'] if not r['selection_available']]
    assert all(r['physical_job'] is None and r['status'] == 'selection-unavailable'
        and all(v is None for v in r['scores'].values()) for r in missing)
    assert any(row['left_status'] == 'selection-unavailable' for row in result['fixed_policy_contrasts'])


def test_method_contrast_direction_is_literal_left_minus_right():
    p, a = fixture(different=True); result = module.summarize(p, a)
    rows = [r for r in result['fixed_policy_contrasts'] if r['kind'] == 'fixed-method-selected-policies'
        and r['left'].endswith('/history-0/' + OBJECTIVES[0]) and METHODS[0] in r['left']]
    assert len(rows) == 4 and all(all(v == 3. for v in r['differences'].values()) for r in rows)


@pytest.mark.parametrize('edit', ['drop', 'reorder', 'duplicate', 'score', 'foreign-label',
                                'selection', 'stopped', 'held-out', 'new-call'])
def test_inconsistent_projection_never_claims_an_exact_fixed_evaluation(edit):
    p, a = fixture()
    if edit == 'drop': a['worlds'].pop()
    elif edit == 'reorder': a['worlds'].reverse()
    elif edit == 'duplicate': a['worlds'][-1] = deepcopy(a['worlds'][0])
    elif edit == 'score': a['worlds'][0]['scores'][OBJECTIVES[0]] = 0.
    elif edit == 'foreign-label': a['worlds'][0]['labels'][0] = 'foreign'
    elif edit == 'selection': a['fixed_selection']['entries'][-1]['selected_id'] = 'reselected'
    elif edit == 'stopped': a['closure']['terminal']['status'] = 'stopped'
    elif edit == 'held-out': a['held_out_world_seeds'] = False
    else: a['new_model_calls'] = 1
    a = seal(a)
    with pytest.raises(ValueError): module.summarize(p, a)


def export_fixture(root, monkeypatch):
    p, a = fixture(); raw = root / 'raw'; raw.mkdir(); reader = root / 'reader'; reader.mkdir()
    frozen = root / 'scientific'; frozen.mkdir()
    p['origin'] = {k: str(root / ('original-' + k)) for k in ('run', 'source', 'analysis', 'readouts')}; p = seal(p)
    a['plan_sha256'] = p['content_sha256']; a['closure']['started'] = save(raw / 'started.json', {'SCRIPTED': 'start'})
    a['closure']['terminal'] = save(raw / 'terminal.json', a['closure']['terminal'])
    save(raw / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    inventory = module._inventory(raw); a.update(raw_inventory_sha256=digest(inventory), raw_files=len(inventory)); a = seal(a)
    audits = [root / ('audit-' + str(i) + '.json') for i in (1, 2)]
    costs = [root / ('cost-' + str(i) + '.json') for i in (1, 2)]
    for f in audits: save(f, {k: v for k, v in a.items() if k != 'content_sha256'})
    for f in costs: save(f, {'source_commit': p['source_commit'], 'plan_sha256': p['content_sha256'],
        'input_audit_content_sha256': a['content_sha256'], 'raw_inventory_sha256': digest(inventory),
        'new_model_calls': 0, 'new_code_executions': 0})
    monkeypatch.setattr(module, 'ROOT', reader); monkeypatch.setattr(module, 'pinned_revision', lambda root: p['source_commit'])
    return SimpleNamespace(run=raw, frozen_source=frozen, audit_one=audits[0], audit_two=audits[1],
        cost_one=costs[0], cost_two=costs[1], output=root / 'out-1')


def test_two_external_scripted_exports_match_without_rendering_or_empty_path_claim(monkeypatch):
    with tempfile.TemporaryDirectory(prefix='scienceutopia-fixed-readout-') as directory:
        root = Path(directory); args = export_fixture(root, monkeypatch); module.export(args)
        first = args.output; args.output = root / 'out-2'; module.export(args)
        assert {p.name: p.read_bytes() for p in first.iterdir()} == {p.name: p.read_bytes() for p in args.output.iterdir()}
        assert {p.name for p in first.iterdir()} == {'report.json', 'logical-scores.csv', 'contrasts.csv', 'manifest.json'}
        result = module.read(first / 'report.json')
        assert not result['behavior_evidence']['complete_observed_input_classes']
        assert all(t['status'] == 'observed-path-unavailable' for t in result['behavior_evidence']['traces'])
        assert result['cost_summary']['scientist'] is None  # Missing diagnostic is not zero usage.


def test_same_file_pairs_and_resolved_source_destinations_stop_before_output(monkeypatch):
    with tempfile.TemporaryDirectory(prefix='scienceutopia-fixed-readout-guards-') as directory:
        root = Path(directory); args = export_fixture(root, monkeypatch)
        original = args.audit_two; args.audit_two = args.audit_one
        with pytest.raises(ValueError, match='distinct matching'): module.export(args)
        assert not args.output.exists(); args.audit_two = original
        alias = root / 'source-alias'; alias.symlink_to(args.frozen_source, target_is_directory=True)
        for target in (module.ROOT / 'out', args.frozen_source / 'out', alias / 'out', args.run / 'out'):
            args.output = target
            with pytest.raises(ValueError, match='outside reader'): module.export(args)
            assert not target.exists()
