"""Synthetic auditor/figure contracts only; never native/Qwen evidence."""
from copy import deepcopy
import hashlib
import json

import pytest

from scripts.analyze_native_method_paths_v10 import (
    ACTUAL, RAW_SCHEMA, SCHEMA, SCHEDULE, _arm_summary, _physical_ledger, _sequence,
)
from scripts.figures.native_method_paths_v10 import FIXTURE, create, read_report
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


def h(value): return hashlib.sha256(value.encode()).hexdigest()


def test_sequence_retains_exact_interleave_and_null_failure():
    rows = [{**item, 'theta': .5} for item in SCHEDULE]
    steps = [{**item, 'proposal': {}} for item in SCHEDULE]
    assert _sequence({'status': 'complete', 'endpoints': rows, 'steps': steps,
                      'failures': []}, True) == (rows, steps, [])
    changed = deepcopy(rows); changed[1]['name'] = 'gradient-1'
    with pytest.raises(ValueError, match='schedule'):
        _sequence({'status': 'complete', 'endpoints': changed, 'steps': steps,
                   'failures': []}, True)
    failure = {'loss': None, 'name': 'gradient-1'}
    assert _sequence({'status': 'stopped-with-preserved-failure',
        'endpoints': rows[:2], 'steps': steps[:3], 'failures': [failure]}, False)[2] == [failure]
    failure['loss'] = 999.
    with pytest.raises(ValueError, match='became loss'):
        _sequence({'status': 'stopped-with-preserved-failure',
            'endpoints': rows[:2], 'steps': steps[:3], 'failures': [failure]}, False)


def test_v10_ledger_accepts_only_v10_world_names(tmp_path):
    (tmp_path/'worlds/gradient-0').mkdir(parents=True)
    world = {'seed': 42, 'model_digest': 'a'*64, 'corpus_sha256': 'b'*64,
             'source_commit': 'c'*40}
    result = _physical_ledger(tmp_path, set(), world, {'prepared': {'prefix_count': 53}})
    assert result['worlds'][0]['name'] == 'gradient-0'
    assert result['worlds'][0]['status'] == 'partial-before-response-journal'
    (tmp_path/'worlds/calibration-0').mkdir()
    with pytest.raises(ValueError, match='undeclared v10'):
        _physical_ledger(tmp_path, set(), world, {'prepared': {'prefix_count': 53}})


def test_arm_summary_keeps_current_worse_noop_and_earliest_tie():
    historical = [{'name': name, 'theta': theta,
        'endpoint': {'native_loss': loss}} for name, theta, loss in
        [('h0', .2, .9), ('h1', .5, .9), ('h2', .8, .8)]]
    rows = [{'name': f'g{i}', 'theta': theta, 'endpoint': {'native_loss': loss}}
            for i, (theta, loss) in enumerate([(.5, 1.2), (.5, 1.2), (.7, .8)])]
    result = _arm_summary('gradient', rows, historical)
    assert [r['theta'] for r in result['current_path']] == [.5, .5, .7]
    assert [r['theta'] for r in result['incumbent_path']] == [.8, .8, .8]
    assert result['final_incumbent']['origin'] == 'shared-historical'
    assert result['best_fresh_minus_initial_center'] == pytest.approx(-.1)
    assert result['best_fresh_minus_best_historical'] == 0.


def fixture_report():
    historical = [{'name': f'h{i}', 'theta': theta, 'native_loss': loss,
        'checkpoint_sha256': h(f'h{i}')} for i, (theta, loss) in enumerate([(.2,.9),(.5,.9),(.8,.8)])]
    arms = {}
    endpoints = []
    for arm, offset in [('gradient', 0.), ('blackbox', .05)]:
        current = [{'name': f'{arm}-{i}', 'theta': .5+i*.05,
                    'loss': .9-i*.02+offset} for i in range(3)]
        incumbent = [{'origin': 'shared-historical', 'name': 'h2', 'theta': .8, 'loss': .8}
                     for _ in range(3)]
        arms[arm] = {'current_path': current, 'incumbent_path': incumbent,
            'historical_observations_charged': 3, 'fresh_attempts': 3}
        endpoints += [{**row, 'arm': arm, 'step': i} for i, row in enumerate(current)]
    report = {'schema': SCHEMA, 'classification': FIXTURE, 'status': 'complete',
        'source_commit': 'a'*40, 'technical_validity': {'completed_worlds': 6, 'failures': []},
        'comparison': {'equal_fresh_native_attempt_budget': 3,
            'optimizer_superiority_claim': False},
        'held_out_metrics': {'status': 'not-measured'}, 'shared_historical': {'rows': historical},
        'arms': arms, 'endpoints': endpoints, 'physical_reply_count': 10,
        'logical_response_count': 20, 'replayed_response_count': 10}
    report['content_sha256'] = digest(report)
    return report


def test_figure_reader_requires_complete_equal_budget_truthful_scope(tmp_path):
    report = fixture_report(); path = tmp_path/'audit.json'; path.write_text(json.dumps(report))
    assert read_report(path, 'a'*40, allow_synthetic=True)['arms']['gradient']['fresh_attempts'] == 3
    changed = deepcopy(report); changed['comparison']['optimizer_superiority_claim'] = True
    changed['content_sha256'] = digest({k:v for k,v in changed.items() if k!='content_sha256'})
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='scope'):
        read_report(path, 'a'*40, allow_synthetic=True)

    masquerade = fixture_report(); masquerade['classification'] = ACTUAL
    masquerade['content_sha256'] = digest({k:v for k,v in masquerade.items() if k!='content_sha256'})
    path.write_text(json.dumps(masquerade))
    with pytest.raises(ValueError, match='source/objective/claim proof'):
        read_report(path, 'a'*40)


def test_figure_is_deterministic_and_zero_call(tmp_path):
    report = fixture_report(); path = tmp_path/'audit.json'; path.write_text(json.dumps(report))
    first = create(path, tmp_path/'paths', 'a'*40, allow_synthetic=True)
    hashes = {key: file_sha256(value['path']) for key, value in first['outputs'].items()}
    second = create(path, tmp_path/'paths', 'a'*40, allow_synthetic=True)
    assert hashes == {key: file_sha256(value['path']) for key, value in second['outputs'].items()}
    assert first['new_model_calls'] == first['new_native_worlds'] == 0
    assert not first['optimizer_superiority_claim'] and not first['held_out_claim']


def test_schema_names_are_forward_only_v10():
    assert RAW_SCHEMA == 'scienceutopia.native-method-paths.v10'
    assert SCHEMA == 'scienceutopia.native-method-paths-audit.v10'
