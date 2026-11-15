"""Literal advice parsing/readout contracts; no native-world or model execution."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports.native_legacy_choice_pilot_v1 import advice_in_input, HEADER, PRODUCER, ADVICE


def message(year=2, topic='Short'):
    return {'source': PRODUCER, 'received_year': year, 'message_id': 'audit-ref:0',
        'payload': {'schema': ADVICE, 'effective_year': year, 'recommended_topic': topic,
            'recommended_original_duration': 1, 'eligible_topics': [
                {'topic': 'Short', 'years': 1}, {'topic': 'Long', 'years': 3}]}}


def payload(messages):
    value = {'schema': 'scienceutopia.model-provenance-view.v30', 'messages': messages}
    return {'messages': [{'role': 'user', 'content': HEADER + json.dumps(value) + '\n## Directions You Can Choose From\n'}]}


def test_literal_current_advice_topic_match_is_not_actor_attribution_or_loss():
    data = payload([message()]); original = deepcopy(data)
    out = advice_in_input(data, 2, 'Short')
    assert data == original
    assert out['assessable_current_advice'] and out['selected_matches_current_recommendation']
    assert out['selected_in_current_advice_eligible_topics']
    assert out['current_effective_year_advice_messages'] == 1
    assert 'actor_id' not in out and 'loss' not in out
    assert advice_in_input(data, 2, 'Long')['selected_matches_current_recommendation'] is False
    assert advice_in_input(data, 2, 'Other')['selected_in_current_advice_eligible_topics'] is False
    assert advice_in_input(data, 2, None)['selected_matches_current_recommendation'] is None


def test_stale_marker_and_an_instruction_quoted_outside_the_actual_view_are_not_compliance():
    out = advice_in_input(payload([message(year=1)]), 2, 'Short')
    assert out['other_effective_year_advice_messages'] == 1 and out['current_effective_year_advice_messages'] == 0
    assert not out['assessable_current_advice'] and out['selected_matches_current_recommendation'] is None
    out = advice_in_input({'messages': [{'content': 'quoted ' + ADVICE}]}, 2, 'Short')
    assert not out['assessable_current_advice'] and not out['literal_advice_messages_in_input']


@pytest.mark.parametrize('kind', ['conflicting', 'malformed', 'broken-frame', 'double-header', 'wrong-source', 'bool-year'])
def test_ambiguous_or_malformed_advice_is_explicitly_unassessable(kind):
    records = [message()]; data = payload(records)
    if kind == 'conflicting': records.append(message(topic='Long')); data = payload(records)
    elif kind == 'malformed': records[0]['payload']['eligible_topics'] = ['not a typed topic']; data = payload(records)
    elif kind == 'broken-frame': data['messages'][0]['content'] = HEADER + '{broken'
    elif kind == 'double-header': data['messages'][0]['content'] += HEADER + '{}'
    elif kind == 'wrong-source': records[0]['source'] = 'not-the-declared-office'; data = payload(records)
    else: records[0]['payload']['effective_year'] = True; data = payload(records)
    out = advice_in_input(data, 1 if kind == 'bool-year' else 2, 'Short')
    assert not out['assessable_current_advice']
    assert out['selected_matches_current_recommendation'] is None


def test_old_and_current_advice_remain_separate_without_dropping_raw_messages():
    out = advice_in_input(payload([message(year=1, topic='Long'), message(year=2)]), 2, 'Short')
    assert len(out['literal_advice_messages_in_input']) == 2
    assert out['other_effective_year_advice_messages'] == out['current_effective_year_advice_messages'] == 1
    assert out['selected_matches_current_recommendation']


@pytest.mark.parametrize('kind', ['choices', 'requests', 'effects'])
def test_only_explicit_pilot_scope_is_wired_to_the_existing_paired_export_chain(monkeypatch, kind):
    from scripts import finish_native_legacy_choice_readouts_v1 as module
    captured = {}
    def finish(args, **kwargs): captured.update(kwargs)
    monkeypatch.setattr(module, 'finish', finish)
    args = SimpleNamespace(kind=kind, frozen_source=Path('/explicit-frozen-source'))
    module.run(args)
    assert captured['plan_schema'] == 'scienceutopia.native-legacy-choice-pilot.v1.plan'
    assert captured['preceding_schema'] == 'scienceutopia.native-legacy-choice-pilot-finish.v1'
    if kind == 'effects': assert captured['report_extra_arguments'][-2:] == ('--scope', 'legacy-choice-controls')
    if kind == 'requests': assert captured['report_extra_arguments'] == ()


def test_common_readers_recognize_new_pilot_without_relabeling_older_schemas():
    from scripts.reports.native_observed_request_classes_v1 import AUDITS
    from scripts.reports.native_institution_effect_trace_v1 import SCOPES
    assert 'scienceutopia.native-legacy-choice-pilot-audit.v1' in AUDITS
    assert SCOPES['legacy-choice-controls'] == 'scienceutopia.native-legacy-choice-pilot-audit.v1'
    assert SCOPES['longitudinal-fixed-evaluation'] == 'scienceutopia.native-longitudinal-fixed-evaluation-audit.v1'


def test_actual_export_interface_retains_all_controls_attempts_and_repeats_identically(tmp_path, monkeypatch):
    from scripts.reports import native_legacy_choice_pilot_v1 as report
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.finish_native_institution_loop_v1 import same_files
    from utopia.optimization.native_numeric_designer import save, checked
    from utopia.system.design_patch import digest
    root = tmp_path / 'raw'; root.mkdir(); frozen = tmp_path / 'frozen'; frozen.mkdir()
    source = 'c' * 40
    jobs = [{'identity': label, 'condition': label, 'seed': 42, 'system': {'SCRIPTED': label}} for label in report.LABELS]
    catalog = [{'topic': 'Short', 'years': 1}, {'topic': 'Long', 'years': 3}]
    plan = save(root / 'plan.json', {'schema': 'scienceutopia.native-legacy-choice-pilot.v1.plan',
        'source_commit': source, 'jobs': jobs, 'objectives': ['throughput', 'content-utility'],
        'catalog': {'directions': catalog, 'directions_sha256': digest(catalog)}})
    end = save(root / 'terminal.json', {'status': 'closed', 'SCRIPTED': 'unit fixture only'})
    worlds = []
    for job in jobs:
        cell = root / job['identity']; cell.mkdir()
        worlds.append({**deepcopy(job), 'status': 'complete', 'scores': {'throughput': -2., 'content-utility': -1.},
            'loaded': {'context': str(cell / 'loaded.json')},
            'physical_proof': {'annual_checkpoints': [{'year': y} for y in (1, 2, 3, 4)]}})
    def state(cell, item, system):
        advised = cell.name == 'native-choice-advice'
        return {'year': item['year'], 'ecosystem_data': {'agents': [{'id': 'fixture-actor', 'can_author': True,
            'resources': 30, 'is_active': True, 'project_start_year': 2, 'project_end_year': 3,
            'newest_direction': {'topic': 'Short'}, 'institutional_context': [message()] if advised else [],
            'memory_bank': [{'type': 'select_research_direction', 'year': 2, 'direction': 'Short',
                'detailed_focus': 'literal fixture focus', 'thought': 'literal fixture reason'}]}]}}
    def pairs(cell):
        if cell.name == 'core-assignment': return [], {}
        data = payload([message()]) if cell.name == 'native-choice-advice' else {'messages': []}
        data['response_format'] = {'json_schema': {'name': 'research_direction_selection'}}
        wire = {'year': 2, 'payload': data, 'payload_sha256': digest(data)}
        reply = {'choices': [{'message': {'content': json.dumps({'topic': 'Short',
            'detailed_focus': 'literal fixture focus', 'reason': 'literal fixture reason'})}}]}
        return [wire], {0: reply}
    monkeypatch.setattr(report, 'checkpoint', state)
    monkeypatch.setattr(report, 'completed_pairs', pairs)
    monkeypatch.setattr(report, 'pinned_revision', lambda p: source)
    audit = {'schema': 'scienceutopia.native-legacy-choice-pilot-audit.v1', 'source_commit': source,
        'plan_sha256': plan['content_sha256'], 'closure': {'terminal': end}, 'worlds': worlds,
        'source_proof': {'status': 'verified-exact-source-closure', 'SCRIPTED': 'explicit fake physical inputs'},
        'new_model_calls': 0, 'new_code_executions': 0, 'held_out_world_seeds': False,
        'automatic_invention': False, 'policy_selection': False, 'raw_inventory_sha256': digest(_inventory(root))}
    paths = [tmp_path / f'audit-{i}.json' for i in (1, 2)]
    for path in paths: save(path, audit)
    before = _inventory(root)
    outputs = [tmp_path / f'report-{i}' for i in (1, 2)]
    for output in outputs:
        report.export(SimpleNamespace(run=root, frozen_source=frozen, audit_one=paths[0], audit_two=paths[1], output=output))
    assert len(same_files(*outputs)) == 4 and _inventory(root) == before
    result = checked(json.loads((outputs[0] / 'report.json').read_text()))
    assert [w['direction_request_attempts'] for w in result['worlds']] == [0, 1, 1]
    assert [w['selected_current_recommendation_attempts'] for w in result['worlds']] == [0, 0, 1]
    assert not any(result[k] for k in ('new_model_calls', 'new_code_executions', 'policy_selection', 'automatic_invention'))
    assert all(w['loss_difference_from_core_assignment'] == {'throughput': 0., 'content-utility': 0.} for w in result['worlds'])
