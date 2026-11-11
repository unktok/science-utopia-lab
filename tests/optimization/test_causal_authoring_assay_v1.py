import json

import pytest

from scripts import run_causal_authoring_assay_v1 as assay
from tests.optimization.test_native_causal_design import anchor
from utopia.optimization.native_benchmark_controls import objective_specs
from utopia.optimization.native_causal_design import OPTION
from utopia.optimization.native_numeric_designer import save, checked
from utopia.system.design_patch import digest
from utopia.system.native_information_institution import information_design_space


def original(history=0):
    system = anchor()
    return {'parent_system': system.to_dict(), 'design_space_anchor': system.to_dict(),
        'design_space': information_design_space(system, 'code-and-graph', fixed_production=True),
        'strategy_provenance': {'kind': 'code-and-graph'}, 'generation': history,
        'loss_spec': objective_specs()['efficiency'], 'history': [{'literal': 'failure'}]*history,
        'observations': [], 'world_binding': {'source_commit': assay.HISTORICAL_SOURCE},
        'rng_seed': 123, 'feedback_policy': {'name': 'matched-loss'}}


def test_pair_only_changes_context_and_keeps_historical_evidence_literal():
    old = original(1); before = json.dumps(old, sort_keys=True)
    pair = assay.request_pair(old, source='NEW', archive={'file_sha256': 'RAW'})
    assert json.dumps(old, sort_keys=True) == before
    off, on = pair['off'], pair['on']
    assert OPTION not in off and on[OPTION] is True
    for value in (off, on):
        for key in ('history', 'observations', 'world_binding', 'parent_system', 'loss_spec', 'rng_seed'):
            assert value[key] == old[key]
        assert value['feedback_policy']['historical_measurements_are_not_new_candidate_losses']
        assert value['design_space']['world_law_scope'] == 'fixed-native-production-review-routing-v2'
    on.pop(OPTION)
    on['strategy_provenance'][OPTION] = False
    assert on == off


def setup_run(tmp_path, monkeypatch):
    plan = {'source_commit': 'NEW', 'designer': {}, 'backend': 'BACK', 'runtime': 'RUNTIME',
        'calibration_slot_ids': {'off': 'off', 'on': 'on'},
        'slots': [{'id': c, 'condition': c, 'request': {'condition': c}} for c in ('off', 'on')]}
    save(tmp_path/'plan.json', plan)
    monkeypatch.setattr(assay, 'require_environment', lambda: None)
    monkeypatch.setattr(assay, 'require_plan', lambda root: plan)
    monkeypatch.setattr(assay, 'planned_cases', lambda *args: [1])
    return plan


def test_failed_readiness_stops_without_any_candidate_or_refill(tmp_path, monkeypatch):
    setup_run(tmp_path, monkeypatch)
    calls = []
    def execute(path, **kwargs):
        calls.append(kwargs['kind'])
        return {'passed': False}
    monkeypatch.setattr(assay, 'execute', execute)
    assay.run(tmp_path)
    result = checked(assay.read(tmp_path/'terminal.json'))
    assert result['status'] == 'stopped' and result['slots'] == []
    assert calls == ['calibration']
    with pytest.raises(ValueError, match='already consumed'):
        assay.run(tmp_path)
    assert calls == ['calibration']


@pytest.mark.parametrize('unknown', [False, True])
def test_known_failure_charges_slot_but_unknown_completion_stops_everything(tmp_path, monkeypatch, unknown):
    setup_run(tmp_path, monkeypatch)
    calls = []
    def execute(path, **kwargs):
        calls.append((kwargs['kind'], path.name))
        if kwargs['kind'] == 'calibration':
            save(path/'calibration/certificate.json', {'plan': {'request': kwargs['request'],
                'backend': 'BACK', 'runtime': 'RUNTIME'}})
            return {'passed': True}
        if unknown:
            raise assay.CompletionUnknown('HTTP response missing')
        raise ValueError('known terminal candidate failure')
    monkeypatch.setattr(assay, 'execute', execute)
    assay.run(tmp_path)
    result = checked(assay.read(tmp_path/'terminal.json'))
    assert len([x for x in calls if x[0] == 'proposal']) == (1 if unknown else 2)
    assert len(result['slots']) == (0 if unknown else 2)
    assert result['status'] == ('stopped' if unknown else 'complete')
    if unknown:
        assert result['completion_unknown'] is True


def test_wire_usage_never_imputes_missing_counts_as_zero(tmp_path):
    save(tmp_path/'dispatch-000.intent.json', {'request': 'raw'})
    save(tmp_path/'dispatch-000.http.json', {'http_status': 200,
        'raw_http_response': json.dumps({'done': False})})
    rows = assay.wire_usage(tmp_path)
    assert rows[0]['prompt_tokens'] is rows[0]['output_tokens'] is None
    assert rows[0]['done'] is False


def test_diff_keeps_literal_code_edits_and_wiring_separate():
    assert assay.differences({'source':'x', 'connections':[]}, {'source':'x ', 'connections':[]}) == ['/source']
    assert assay.differences({'connections':[]}, {'connections':[{}]}) == ['/connections']
