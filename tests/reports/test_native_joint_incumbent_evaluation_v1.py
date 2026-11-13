"""Development-only aliases; all numerical values here are SCRIPTED software QA."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from scripts.reports import native_joint_incumbent_evaluation_v1 as module
from scripts.reports.native_objective_fixed_evaluation_v1 import summarize as joint_view
from tests.reports.test_native_joint_fixed_report_v1 import fixture
from tests.reports.test_native_planning_objective_loop_v1 import seal
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.native_planning_controls import ORDER


def development_fixtures(joint):
    """Synthetic reports matching the explicitly synthetic joint-origin receipts.

    These are NOT recovered original histories or scientific closed results.
    """
    references = [{'label': label, 'physical_job': 'reference-' + label,
        'scores': {'throughput': -3. if i == 1 else -1., 'content-utility': -2. if i == 6 else 0.}}
        for i, label in enumerate(ORDER)]
    result = {}
    for kind in module.KINDS:
        selection = deepcopy(joint['fixed_selection']['original_selections'][kind])
        keys = [h.split(':', 1)[1] for h in module.HISTORIES if h.startswith(kind + ':')]
        slots = []
        for key in keys:
            objective = 'throughput' if key.startswith('throughput') else 'content-utility'
            own = selection['selected'][key]
            for g in range(3):
                good = own['selected_id'] is not None
                identity = own['all_tied_ids'][g] if good else 'SCRIPTED-missing-' + key + '-' + str(g)
                row = {'objective': objective, 'generation': g, 'status': 'complete' if good else 'failed',
                    'physical_job': identity, 'loss': own['loss'],
                    'cross_scores': {'throughput': -2. if good else None, 'content-utility': -1. if good else None}}
                if kind == 'presentation': row.update(arm=key, presentation=key.rsplit('-', 1)[1])
                slots.append(row)
        report = {'schema': 'scienceutopia.native-planning-objective-report.v1', 'source_commit': 'a' * 40,
            'plan_sha256': selection['plan_sha256'], 'audit_sha256': joint['origin_audit_content_sha256'][kind],
            'score_order': module.OBJECTIVES, 'references': deepcopy(references), 'slots': slots,
            'frozen_selection': selection['selected'], 'SCRIPTED': 'synthetic origin projection, not recovered model histories'}
        if kind == 'presentation':
            report.update(schema='scienceutopia.native-parent-presentation-report.v1', arm_order=list(module.ARM_ORDER),
                arms={k: {'objective': 'throughput' if k.startswith('throughput') else 'content-utility',
                    'presentation': k.rsplit('-', 1)[1]} for k in keys})
        elif kind == 'numeric':
            report.update(schema='scienceutopia.native-parameter-comparator-report.v1', objectives=module.OBJECTIVES,
                numeric_audit_sha256=report.pop('audit_sha256'), original_audit_sha256=joint['origin_audit_content_sha256']['planning'],
                numeric_selection=selection, new_numeric_slots=6, reused_free_slots=6, held_out_evaluation=False,
                anchors={o: {'identity': 'reference-' + ORDER[i], 'loss': references[i]['scores'][o]}
                    for o, i in [('throughput', 1), ('content-utility', 6)]})
            report['references'] = [{'identity': r['physical_job'], 'scores': r['scores'], 'system_sha256': 'f' * 64} for r in references]
            report['slots'] = [{'method': method, 'objective': r['objective'], 'generation': r['generation'],
                'identity': r['physical_job'], 'status': r['status'], 'assigned_loss': r['loss'], 'scores': r['cross_scores']}
                for method, rows in [('prior-free-program', result['planning']['slots']), ('numeric-reserve', slots)] for r in rows]
        result[kind] = seal(report)
    return result


def inputs(tmp_path, monkeypatch):
    p, a = fixture(tmp_path, monkeypatch)
    joint = joint_view(p, a, study='joint-v1')
    return p, a, joint, development_fixtures(joint)


def test_plan_freeze_matches_closed_report_without_reading_evaluation_losses(tmp_path, monkeypatch):
    p, a, joint, dev = inputs(tmp_path, monkeypatch)
    original = deepcopy((p, joint, dev))
    frozen = module.freeze_aliases(p, dev)
    assert frozen == module.freeze_aliases(joint, dev)
    report = module.summarize(joint, dev, frozen)
    assert (p, joint, dev) == original
    assert len(frozen['aliases']) == 16 and len(report['logical_rows']) == 32
    assert len(report['fixed_policy_contrasts']) == 32 and len(report['own_minus_incumbent']) == 16
    assert report['original_physical_worlds'] == 18
    assert not frozen['selection_uses_evaluation_outcomes'] and frozen['new_physical_jobs'] == 0
    missing = [r for r in report['logical_rows'] if r['history'] == 'numeric:content-utility']
    assert all(r['physical_job'] is None for r in missing if r['readout'] == 'own-submission')
    assert all(r['physical_job'] is not None for r in missing if r['readout'] == 'known-incumbent')
    assert joint['fixed_selection']['selected']['numeric:content-utility']['system'] is None
    assert all(not x['all_tied_programs_claimed_evaluated'] for x in frozen['aliases'])
    assert [{k: v for k, v in r.items() if k != 'readout'} for r in report['fixed_policy_contrasts']
        if r['readout'] == 'own-submission'] == joint['fixed_policy_contrasts']


def test_strictly_better_development_own_policy_uses_original_earliest_tie(tmp_path, monkeypatch):
    p, a, joint, dev = inputs(tmp_path, monkeypatch)
    # A SCRIPTED fresh presentation bank can differ from the reused planning bank.
    for row in dev['presentation']['references']:
        for objective in module.OBJECTIVES: row['scores'][objective] += 4.
    seal(dev['presentation'])
    frozen = module.freeze_aliases(p, dev)
    for alias in frozen['aliases']:
        if alias['history'].startswith('presentation:'):
            assert alias['development_origin'] == 'own'
            assert alias['evaluation_label'] == 'selected:' + alias['history']
            assert alias['development_identity'] == alias['all_development_tied_ids'][0]
            assert len(alias['all_development_tied_ids']) == 3
            assert not alias['all_tied_programs_claimed_evaluated']
    report = module.summarize(joint, dev, frozen)
    assert all(r['same_physical_job'] and all(v == 0 for v in r['differences'].values())
        for r in report['own_minus_incumbent'] if r['history'].startswith('presentation:'))


def test_better_own_unused_outcome_does_not_switch_development_reference_alias(tmp_path, monkeypatch):
    p, a, joint, dev = inputs(tmp_path, monkeypatch); frozen = module.freeze_aliases(p, dev)
    numeric = next(w for w in a['worlds'] if 'selected:numeric:throughput' in w['labels'] and w['seed'] == joint['seeds'][0])
    numeric['measurements'][0]['metrics']['native.accepted_decisions']['value'] = 100
    numeric['scores'] = {o: evaluate_loss(loss, numeric['measurements'])['loss'] for o, loss in p['losses'].items()}
    seal(a); changed = joint_view(p, a, study='joint-v1')
    assert module.freeze_aliases(changed, dev) == frozen
    report = module.summarize(changed, dev, frozen)
    row = next(r for r in report['own_minus_incumbent'] if r['history'] == 'numeric:throughput' and r['seed'] == joint['seeds'][0])
    assert row['differences']['throughput'] < 0
    alias = next(r for r in frozen['aliases'] if r['history'] == 'numeric:throughput' and r['readout'] == 'known-incumbent')
    assert alias['evaluation_label'] == 'reference:advice-reserve21-all'


def test_failed_incumbent_evaluation_stays_missing_not_replaced_by_other_policy(tmp_path, monkeypatch):
    p, a, joint, dev = inputs(tmp_path, monkeypatch); frozen = module.freeze_aliases(p, dev)
    world = next(w for w in a['worlds'] if 'reference:advice-reserve21-all' in w['labels'] and w['seed'] == joint['seeds'][0])
    world.update(status='failed', measurements=[], scores={o: None for o in module.OBJECTIVES}); seal(a)
    changed = joint_view(p, a, study='joint-v1'); report = module.summarize(changed, dev, frozen)
    row = next(r for r in report['logical_rows'] if r['history'] == 'numeric:throughput' and r['readout'] == 'known-incumbent' and r['seed'] == joint['seeds'][0])
    assert row['status'] == 'failed' and row['scores'] == {o: None for o in module.OBJECTIVES}
    assert row['physical_job'] == world['identity'] and row['evaluation_label'] == 'reference:advice-reserve21-all'


@pytest.mark.parametrize('change', ['origin-audit', 'origin-plan', 'numeric-bank', 'selection', 'definition',
    'frozen-alias', 'duplicate-row', 'missing-row', 'score-bool', 'logical-physical', 'partial-null', 'labels', 'used-seed'])
def test_changed_origins_aliases_or_outcomes_are_not_repaired(tmp_path, monkeypatch, change):
    p, a, joint, dev = inputs(tmp_path, monkeypatch); frozen = module.freeze_aliases(p, dev)
    if change == 'origin-audit': dev['planning']['audit_sha256'] = '0' * 64; seal(dev['planning'])
    elif change == 'origin-plan': dev['planning']['plan_sha256'] = '0' * 64; seal(dev['planning'])
    elif change == 'numeric-bank': dev['numeric']['original_audit_sha256'] = '0' * 64; seal(dev['numeric'])
    elif change == 'selection': joint['fixed_selection']['selected']['planning:throughput']['selected_id'] = 'SCRIPTED-wrong'; seal(joint['fixed_selection'])
    elif change == 'definition': joint['selection_definitions']['planning:throughput']['objective'] = 'content-utility'
    elif change == 'frozen-alias': frozen['aliases'][0]['evaluation_label'] = 'reference:cut-reserve21-all'; seal(frozen)
    elif change == 'duplicate-row': joint['logical_rows'].append(deepcopy(joint['logical_rows'][0]))
    elif change == 'missing-row': joint['logical_rows'].pop()
    elif change == 'score-bool': joint['logical_rows'][0]['scores']['throughput'] = True
    elif change == 'logical-physical': joint['logical_rows'][0]['scores']['throughput'] = 999.
    elif change == 'partial-null': joint['logical_rows'][0].update(status='failed'); joint['logical_rows'][0]['scores']['throughput'] = None
    elif change == 'labels': joint['labels'].reverse()
    else: joint['seeds'][0] = 61001
    seal(joint)
    with pytest.raises(ValueError): module.summarize(joint, dev, frozen)


def test_two_stage_exports_match_and_leave_every_input_unchanged(tmp_path, monkeypatch):
    p, a, joint, dev = inputs(tmp_path / 'build', monkeypatch); directory = tmp_path / 'inputs'; directory.mkdir()
    paths = {}
    for kind, value in dev.items():
        paths[kind] = [directory / (kind + '-' + str(i) + '.json') for i in (1, 2)]
        for path in paths[kind]: save(path, {k: v for k, v in value.items() if k != 'content_sha256'})
    plan = directory / 'plan.json'; save(plan, {k: v for k, v in p.items() if k != 'content_sha256'})
    reports = [directory / ('joint-' + str(i) + '.json') for i in (1, 2)]
    for path in reports: save(path, {k: v for k, v in joint.items() if k != 'content_sha256'})
    before = {str(p): p.read_bytes() for p in directory.iterdir()}
    monkeypatch.setattr(module, 'pinned_revision', lambda root: 'd' * 40)
    def args(stage, output): return SimpleNamespace(stage=stage, output=output, joint_plan=plan, joint_reports=reports,
        frozen_aliases=tmp_path / 'freeze-1/aliases.json', **{k + '_reports': v for k, v in paths.items()})
    for i in (1, 2): module.export(args('freeze', tmp_path / ('freeze-' + str(i))))
    for i in (1, 2): module.export(args('report', tmp_path / ('report-' + str(i))))
    for stage, count in [('freeze', 2), ('report', 6)]:
        one, two = [tmp_path / (stage + '-' + str(i)) for i in (1, 2)]
        assert {p.name: p.read_bytes() for p in one.iterdir()} == {p.name: p.read_bytes() for p in two.iterdir()}
        assert len(list(one.iterdir())) == count
    assert before == {str(p): p.read_bytes() for p in directory.iterdir()}
    result = checked(json.loads((tmp_path / 'report-1/report.json').read_text()))
    assert result['interpretation']['new_native_worlds'] == 0
