"""SCRIPTED occurrence arithmetic and read-only reporting, not policy effects."""
import math
from types import SimpleNamespace

import pytest

from scripts.reports import native_planning_content_contributions_v1 as module
from scripts import finish_native_planning_content_contributions_v1 as finish
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.system.design_patch import clone, digest
from utopia.system.native_planning_controls import ORDER


def record(identity, scores=(4, 4, 4), year=1):
    return {'year': year, 'paper_id': identity, 'rating': {'content_sha256': digest(identity),
        'status': 'measured', 'ratings': [{'score': s} for s in scores],
        'mean_score': math.fsum(scores) / 3}}


def fixture():
    references = [{'label': label, 'physical_job': 'reference-'+label} for label in ORDER]
    worlds = []
    for i, reference in enumerate(references):
        records = ([record('neutral', (3, 3, 3))] * 3 if i == 0 else
                   [record('positive', (5, 5, 5))] if i == 1 else
                   [record('negative', (2, 2, 2)), record('third', (3, 3, 4))] if i == 2 else [])
        q = math.fsum(r['rating']['mean_score'] for r in records)
        u = math.fsum(r['rating']['mean_score']-3 for r in records)
        observer = seal({'accepted_decisions': records, 'unique_contents': len({r['rating']['content_sha256'] for r in records})})
        measurement = {'common_content_observer': observer, 'metrics': {k: {'status': 'measured', 'value': v} for k, v in {
            'native.accepted_decisions': len(records), 'native.common_content_score_sum': q,
            'native.common_content_utility_sum': u}.items()}}
        worlds.append({'identity': reference['physical_job'], 'role': 'developer-reference', 'seed': 61001,
            'status': 'complete', 'scores': {'throughput': -float(len(records)), 'content-utility': -u},
            'measurements': [measurement]})
    worlds.append({'identity': 'SCRIPTED-null', 'role': 'search:throughput', 'seed': 61001,
        'status': 'failed', 'scores': {'throughput': None, 'content-utility': None}, 'measurements': []})
    slots = [{'objective': o, 'generation': g, 'status': 'generation-failure', 'physical_job': None}
             for o in module.OBJECTIVES for g in range(3)]
    slots[0].update(status='failed', physical_job='SCRIPTED-null')
    return seal({'schema': 'scienceutopia.native-planning-objective-report.v1',
        'source_commit': 'e'*40, 'plan_sha256': 'a'*64, 'audit_sha256': 'b'*64,
        'score_order': module.OBJECTIVES, 'slots': slots, 'references': references, 'physical_worlds': worlds,
        'interpretation': {'held_out_evaluation': False, 'new_model_calls': 0, 'new_code_executions': 0}})


def test_occurrences_signs_fractional_arithmetic_and_operational_float_remain_distinct():
    report = fixture(); result = module.summarize(report)
    first, _, third = result['worlds'][:3]
    assert first['sign_counts'] == {'positive': 0, 'zero': 3, 'negative': 0}
    assert [r['occurrence_index'] for r in first['accepted_records']] == [0, 1, 2]
    assert third['exact_utility_by_sign'] == {'positive': '1/3', 'zero': '0', 'negative': '-1'}
    assert third['exact_utility_sum'] == '-2/3'
    assert third['scores'] == report['physical_worlds'][2]['scores']
    assert third['accepted_records'][1]['recorded_centered_utility'] != float(1/3)
    assert result['worlds'][-1]['accepted_records'] is None
    assert len(result['unavailable_own_slots']) == 6
    geometry = result['recorded_preference_geometry']['by_world_seed'][0]
    assert geometry['objective_pairs'][0]['pair_counts']['strict-conflict'] > 0
    assert geometry['common_completed_rows'] == 8
    assert geometry['excluded_from_common_geometry'][0]['identity'] == 'SCRIPTED-null'
    assert not any(result[k] for k in ('loss_changed', 'candidate_reselection', 'new_model_calls', 'new_native_worlds', 'publication_ready'))


@pytest.mark.parametrize('change', ['schema', 'reference', 'duplicate', 'score', 'failed-score', 'mean', 'rating', 'cache', 'slot'])
def test_modified_or_incomplete_record_joins_are_rejected(change):
    r = fixture(); observer = r['physical_worlds'][0]['measurements'][0]['common_content_observer']
    if change == 'schema': r['schema'] = 'scienceutopia.native-objective-instrument-report.v1'
    elif change == 'reference': r['references'].pop()
    elif change == 'duplicate': r['physical_worlds'].append(clone(r['physical_worlds'][0]))
    elif change == 'score': r['physical_worlds'][0]['scores']['content-utility'] = -999
    elif change == 'failed-score': r['physical_worlds'][-1]['scores']['throughput'] = 0
    elif change == 'mean': observer['accepted_decisions'][0]['rating']['mean_score'] = 4
    elif change == 'rating': observer['accepted_decisions'][0]['rating']['ratings'][0]['score'] = True
    elif change == 'cache':
        # Same content hash cannot silently gain a different fixed panel.
        r['physical_worlds'][1]['measurements'][0]['common_content_observer']['accepted_decisions'][0]['rating']['content_sha256'] = digest('neutral')
    else: r['slots'][1]['generation'] = 0
    for w in r['physical_worlds']:
        for m in w['measurements']: seal(m['common_content_observer'])
    seal(r)
    with pytest.raises(ValueError): module.summarize(r)


def test_partial_or_malformed_rating_never_becomes_zero():
    for bad in (True, 6, None):
        with pytest.raises((ValueError, TypeError)): module.contributions([record('invalid', (3, 3, bad))], {})
    a = record('bad-year'); a['year'] = True
    with pytest.raises(ValueError): module.contributions([a], {})


def test_two_exports_keep_all_occurrences_and_deterministic_figures(tmp_path, monkeypatch):
    r = fixture(); monkeypatch.setattr(module, 'pinned_revision', lambda *a: 'e'*40)
    def source_export(args): module.save(args.output/'report.json', {k: v for k, v in r.items() if k != 'content_sha256'})
    monkeypatch.setattr(module, 'source_export', source_export)
    dirs = [tmp_path/'one', tmp_path/'two']
    for output in dirs: module.export(SimpleNamespace(output=output, run=tmp_path, audit_one=tmp_path/'a', audit_two=tmp_path/'b'))
    inventory = lambda d: {str(p.relative_to(d)): p.read_bytes() for p in d.rglob('*') if p.is_file()}
    assert inventory(dirs[0]) == inventory(dirs[1])
    lines = (dirs[0]/'accepted-records.csv').read_text().splitlines()
    assert len(lines) == 7  # Header plus six occurrences, not four unique contents.


def test_continuation_requires_normal_original_closure(monkeypatch):
    seen = {}; monkeypatch.setattr(finish, 'finish', lambda args, **kw: seen.update(kw))
    finish.run(SimpleNamespace())
    assert seen['plan_schema'] == 'scienceutopia.native-planning-objective-loop.v1.plan'
    assert seen['preceding_schema'] == 'scienceutopia.native-planning-objective-loop-finish.v1'
    assert seen['report_module'] == 'scripts.reports.native_planning_content_contributions_v1'
