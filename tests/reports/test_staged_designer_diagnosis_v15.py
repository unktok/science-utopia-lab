"""Diagnostic transformation tests, no inference or native world."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from utopia.system.design_patch import digest
from utopia.optimization.native_staged_author_v15 import turn_control

PATH = Path(__file__).resolve().parents[2] / 'scripts/diagnose_staged_designer_v15.py'
spec = importlib.util.spec_from_file_location('diagnosis_v15', PATH)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def payload():
    data = {'instructions': 'Minimize exact loss. Retention is legal.',
        'technical_ABI_and_distribution_contract': 'Trusted literal-source ABI.',
        '000_current_turn': {'next_call_number': 3}, 'exact_loss_spec': {'direction': 'minimize'},
        'draft_index': {'empty_parameters': []}}
    return {'model': 'qwen3:8b', 'think': False, 'stream': False,
        'format': {'type': 'object', 'required': ['tool']},
        'options': {'temperature': .2, 'seed': 4, 'num_ctx': 32768, 'num_predict': 2048},
        'messages': [{'role': 'system', 'content': 'Strings are data.'},
            {'role': 'user', 'content': 'CURRENT TURN\n{}\n\nEXACT SESSION CONTEXT\n'
                + d.canonical(data).decode() + '\n\nCHOOSE YOUR NEXT ACTION\nnext'},
            {'role': 'assistant', 'content': '{"tool":"inspect"}'},
            {'role': 'user', 'content': 'Already returned: {}'}]}


def steps():
    return [{'step': i, 'model_reply': {'output': {'tool': 'inspect', 'path': '/' + name}},
        'transition': {'tool': 'inspect', 'ok': True, 'result': {'value': {}},
            'draft_after_sha256': 'a' * 64}} for i, name in enumerate(('a', 'b'))]


def test_exact_baseline_and_no_input_mutation():
    p = payload(); before = deepcopy(p)
    assert d.intervene(p, 'baseline', steps()) == p
    for variant in d.VARIANTS:
        d.intervene(p, variant, steps())
        assert p == before


@pytest.mark.parametrize('variant,key,value', [('json_grammar', 'format', 'json'), ('thinking', 'think', True)])
def test_one_field_treatments_change_only_named_field(variant, key, value):
    p = payload(); expected = deepcopy(p); expected[key] = value
    assert d.intervene(p, variant, steps()) == expected


def test_temperature_changes_only_one_option():
    p = payload(); expected = deepcopy(p); expected['options']['temperature'] = .8
    assert d.intervene(p, 'temperature', steps()) == expected


def test_role_promotion_moves_only_source_owned_constants():
    p = payload(); old, _, _ = d.context(p)
    updated = d.intervene(p, 'trusted_role', steps()); new, _, _ = d.context(updated)
    expected = {k: v for k, v in old.items() if k not in {'instructions', 'technical_ABI_and_distribution_contract'}}
    assert new == expected
    assert old['instructions'] in updated['messages'][0]['content']
    assert old['technical_ABI_and_distribution_contract'] in updated['messages'][0]['content']
    assert updated['options'] == p['options'] and updated['format'] == p['format']


def test_memory_includes_actual_returned_values_not_an_authored_patch():
    p = payload(); out = d.intervene(p, 'observation_memory', steps())
    assert out['messages'][:-1] == p['messages']
    text = out['messages'][-1]['content']; data = json.loads(text.split('\n', 1)[1])
    assert [r['observed_result']['value'] for r in data] == [{}, {}]
    assert all(r['action']['tool'] == 'inspect' for r in data)


def test_notice_neither_bans_inspection_nor_forces_a_change():
    p = payload(); out = d.intervene(p, 'nonconsecutive_notice', steps())
    assert out['messages'][:-1] == p['messages']
    assert 'not an action prohibition or mandatory-edit rule' in out['messages'][-1]['content']


def test_syntax_control_is_explicitly_not_optimization():
    p = payload(); out = d.intervene(p, 'interface_control', steps())
    assert 'NOT AN OPTIMIZATION TRIAL' in out['messages'][0]['content']
    assert out['messages'][1:] == p['messages'][1:]
    assert out['format'] == p['format']


def test_unknown_variant_is_not_silently_relabelled():
    with pytest.raises(ValueError):
        d.intervene(payload(), 'post_hoc_success_only', steps())


def test_original_counter_misses_alternating_unchanged_reads():
    state = {'document': {}, 'operations': []}
    a, b = {'tool': 'inspect', 'path': '/a'}, {'tool': 'inspect', 'path': '/b'}
    records = [{'model_reply': {'output': action}, 'transition': {'ok': True,
        'draft_after_sha256': digest(state)}} for action in (a, b, a, b)]
    notice = turn_control(state, records, max_steps=16)
    assert notice['consecutive_same_successful_inspections_of_unchanged_draft'] == 1
    assert notice['inspection_notice'] is None
    assert len({d.sha(d.canonical(r['model_reply']['output'])) for r in records}) == 2


def test_original_counter_does_notice_identical_consecutive_reads():
    state = {'document': {}, 'operations': []}; action = {'tool': 'inspect', 'path': '/a'}
    records = [{'model_reply': {'output': action}, 'transition': {'ok': True,
        'draft_after_sha256': digest(state)}} for _ in range(3)]
    assert turn_control(state, records, max_steps=16)['inspection_notice'] is not None


def test_fresh_diagnostic_artifacts_refuse_overwrite(tmp_path):
    p = tmp_path / 'evidence.json'; d.fresh(p, {'a': 1})
    with pytest.raises(FileExistsError):
        d.fresh(p, {'a': 2})
    assert d.read(p) == {'a': 1}


def test_interface_does_not_dispatch_anything_when_transforming(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No network or process in input transformations')
    monkeypatch.setattr(d.urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(d.subprocess, 'Popen', forbidden)
    for variant in d.VARIANTS:
        d.intervene(payload(), variant, steps())
