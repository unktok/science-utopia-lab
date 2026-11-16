"""SCRIPTED data-only signed arithmetic, not new scientific evaluations."""
from copy import deepcopy
import csv
import json
import math
from types import SimpleNamespace

import pytest

from scripts.reports import native_corrected_choice_content_v1 as module
from tests.reports.test_native_corrected_choice_readout_v1 import fixture as original_fixture, seal
from tests.reports.test_native_planning_content_contributions_v1 import record
from utopia.optimization.native_numeric_designer import save, checked


def fixture(*, missing=False):
    plan, audit, slots, refs = original_fixture(null_free=missing)
    # Preserve the source fixture's explicitly SCRIPTED loss specs/selection.
    # Additional native metrics exercise content joins, not actual U/C estimates.
    observations = list(refs.values()) + [e['observation'] for e in slots if e['observation'] is not None]
    for o in observations:
        records = [record('positive'), record('negative', (2, 2, 2)),
                   record('third', (3, 3, 4)), record('neutral', (3, 3, 3)), record('neutral', (3, 3, 3))]
        m, = o['metadata']['measurements']
        m['common_content_observer'] = seal({'accepted_decisions': records, 'unique_contents': 4})
        for k, v in {'native.accepted_decisions': 5,
                     'native.common_content_score_sum': math.fsum(r['rating']['mean_score'] for r in records),
                     'native.common_content_utility_sum': math.fsum(r['rating']['mean_score']-3 for r in records)}.items():
            m['metrics'][k] = {'status': 'measured', 'value': v}
    return plan, audit, slots, refs


def test_all27_logical_rows_keep_repeated_occurrences_negative_signs_and_fractional_float_distinction():
    p, a, slots, refs = fixture(); r = module.derive(p, a, slots, refs)
    assert len(r['rows']) == 27 and len({x['cell_id'] for x in r['rows']}) == 27
    assert r['accepted_occurrences'] == 135 and r['distinct_content_hashes'] == 4
    assert r['sign_counts'] == {'positive': 54, 'zero': 54, 'negative': 27}
    c = r['rows'][0]['content']
    assert c['exact_U_by_sign'] == {'positive': '4/3', 'zero': '0', 'negative': '-1'}
    assert c['exact_U'] == '1/3' and c['recorded_U'] != float(1/3)
    assert c['fixed_record_deletion_arithmetic_gain'] == '1'
    assert [x['occurrence_index'] for x in c['accepted_records']] == [0, 1, 2, 3, 4]
    assert not any(r[k] for k in ('new_model_calls', 'new_native_worlds', 'new_code_executions', 'loss_changed', 'selection_changed', 'publication_ready'))


def test_generation_nulls_remain_rows_without_content_or_imputed_utility():
    r = module.derive(*fixture(missing=True))
    nulls = [x for x in r['rows'] if x['status'] == 'generation-null']
    assert len(r['rows']) == 27 and len(nulls) == 4 and r['coverage']['physical_worlds'] == 23
    assert all(x['content'] is x['assigned_loss'] is x['observation_canonical_sha256'] is None for x in nulls)
    assert r['accepted_occurrences'] == 115


def test_execution_null_is_unavailable_not_zero_or_partial_complete_panel():
    failed = {'status': 'failed', 'loss': None, 'metadata': {'measurements': []}}
    assert module.summarize_observation(failed, {}) is None
    for changed in ({**failed, 'loss': 0}, {**failed, 'metadata': {'measurements': [{}]}}):
        with pytest.raises(ValueError): module.summarize_observation(changed, {})


def test_completed_empty_set_is_measured_zero_and_not_an_execution_null():
    observation = {'status': 'complete', 'loss': 0, 'metadata': {'measurements': [{
        'common_content_observer': seal({'accepted_decisions': [], 'unique_contents': 0}),
        'metrics': {k: {'status': 'measured', 'value': v} for k, v in {
            'native.accepted_decisions': 0, 'native.common_content_score_sum': 0.,
            'native.common_content_utility_sum': 0.}.items()}}]}}
    content = module.summarize_observation(observation, {})
    assert content is not None and content['recorded_U'] == 0 and content['accepted_records'] == []
    assert content['fixed_record_deletion_arithmetic_gain'] == '0'


@pytest.mark.parametrize('target', ['native-count', 'unique-count'])
def test_boolean_count_is_not_a_measured_single_occurrence(target):
    o = fixture()[3]['zero']; m, = o['metadata']['measurements']; row = record('single')
    m['common_content_observer'] = seal({'accepted_decisions': [row], 'unique_contents': 1})
    m['metrics'].update({k: {'status': 'measured', 'value': v} for k, v in {
        'native.accepted_decisions': 1, 'native.common_content_score_sum': 4.,
        'native.common_content_utility_sum': 1.}.items()})
    if target == 'native-count': m['metrics']['native.accepted_decisions']['value'] = True
    else: m['common_content_observer'] = seal({**m['common_content_observer'], 'unique_contents': True})
    with pytest.raises(ValueError): module.summarize_observation(o, {})


@pytest.mark.parametrize('change', ['missing-slot', 'old-profile', 'metric', 'unique', 'rating', 'shared-content'])
def test_incomplete_or_contradictory_content_does_not_pass_just_because_sealed(change):
    p, a, slots, refs = fixture(); m = slots[0]['observation']['metadata']['measurements'][0]
    obs = m['common_content_observer']
    if change == 'missing-slot': slots.pop()
    elif change == 'old-profile': p['schema'] = 'old-profile'; p = seal(p)
    elif change == 'metric': m['metrics']['native.common_content_utility_sum']['value'] = 99
    elif change == 'unique': obs['unique_contents'] = 5
    elif change == 'rating': obs['accepted_decisions'][0]['rating']['ratings'][0]['score'] = True
    else: obs['accepted_decisions'][0]['rating']['content_sha256'] = obs['accepted_decisions'][1]['rating']['content_sha256']
    m['common_content_observer'] = seal(obs)
    with pytest.raises(ValueError): module.derive(p, a, slots, refs)


def test_public_data_only_exports_match_without_science_or_rendering(tmp_path, monkeypatch):
    p, a, slots, refs = fixture(missing=True)
    roots = {k: tmp_path/k for k in ('run', 'source', 'analysis', 'readouts', 'reader')}
    for root in roots.values(): root.mkdir()
    save(roots['run']/'plan.json', {'source_commit': 'a'*40}); (roots['run']/'writer.lock').touch()
    monkeypatch.setattr(module, 'ROOT', roots['reader'])
    monkeypatch.setattr(module, 'pinned_revision', lambda root: 'b'*40)
    monkeypatch.setattr(module, 'evidence_files', lambda origin: [roots['run']/'plan.json'])
    calls = []
    def origin(value, **kw): calls.append(kw); return deepcopy(p), deepcopy(a), {}
    monkeypatch.setattr(module, 'origin_evidence', origin)
    monkeypatch.setattr(module, 'collect', lambda raw, plan: (deepcopy(slots), deepcopy(refs)))
    def forbidden(*args, **kwargs): pytest.fail('data-only reader must not call science')
    monkeypatch.setattr('requests.Session.post', forbidden)
    monkeypatch.setattr('openai.OpenAI.__init__', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)
    outputs = [tmp_path/'one', tmp_path/'two']
    before = module._inventory(roots['run'])
    for output in outputs:
        module.export(SimpleNamespace(output=output, **{'origin_'+k: roots[k] for k in ('run', 'source', 'analysis', 'readouts')}))
    assert {q.name: q.read_bytes() for q in outputs[0].iterdir()} == {q.name: q.read_bytes() for q in outputs[1].iterdir()}
    assert set(q.name for q in outputs[0].iterdir()) == {'report.json', 'accepted-records.csv', 'manifest.json'}
    with (outputs[0]/'accepted-records.csv').open() as stream: rows = list(csv.DictReader(stream))
    assert len(rows) == 115 and sum(x['sign']=='negative' for x in rows) == 23
    assert checked(json.loads((outputs[0]/'report.json').read_text()))['accepted_occurrences'] == 115
    assert before == module._inventory(roots['run']) and calls == [{'profile': 'corrected-choice-v1'}]*2


@pytest.mark.parametrize('target', ['run', 'source', 'analysis', 'readouts', 'reader'])
def test_source_local_output_rejected_before_creating_or_reading_original_evidence(tmp_path, monkeypatch, target):
    roots = {k: tmp_path/k for k in ('run', 'source', 'analysis', 'readouts', 'reader')}
    monkeypatch.setattr(module, 'ROOT', roots['reader'])
    def forbidden(*args, **kwargs): pytest.fail('path guard must precede evidence reads')
    monkeypatch.setattr(module, 'pinned_revision', forbidden)
    output = roots[target]/'out'
    with pytest.raises(ValueError):
        module.export(SimpleNamespace(output=output, **{'origin_'+k: roots[k] for k in ('run', 'source', 'analysis', 'readouts')}))
    assert not output.exists()
