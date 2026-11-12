"""Scripted tables, missingness and real figure IO; not native science evidence."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_instruction_timing_summary_v1 as module
from utopia.optimization.native_numeric_designer import save, checked
from utopia.system.design_patch import digest


def report():
    worlds = []
    for condition, loss in zip(module.CONDITIONS, (-2., -3., -2.)):
        row = {'wire_index': 3, 'year': 1, 'payload_sha256': digest(condition),
            'literal_instruction_present': condition == 'early',
            'frame_status': 'literal-displayed-candidates', 'reply_status': 'literal-direction-object',
            'selected_topic': 'SCRIPTED short', 'selected_catalog_duration_years': 1,
            'minimum_displayed_duration_years': 1, 'selected_is_shortest_displayed': True,
            'unique_actor_attribution': True, 'matching_actual_memory_actor_ids': ['SCRIPTED actor']}
        worlds.append({'identity': 'SCRIPTED-'+condition, 'condition': condition, 'seed': 61001,
            'scores': {'throughput': loss, 'content-utility': 0.},
            'annual': [{'year': year, 'authors': [{'id': 'SCRIPTED actor', 'resources': 30-year,
                'is_active': True, 'project_start_year': 1, 'project_end_year': 2,
                'newest_direction': {'direction': 'SCRIPTED short'}}]} for year in (1, 2, 3, 4)],
            'direction_requests': [row], 'direction_memories': [{'SCRIPTED': True}],
            'stored_instructions': [] if condition == 'cut' else [{'SCRIPTED': True}],
            'physical_wire_requests': 5, 'committed_responses': 4, 'wire_without_committed_reply': 1})
    r = {'schema': 'scienceutopia.native-instruction-timing-report.v1',
        'scientific_source_commit': 'a'*40, 'plan_sha256': 'b'*64, 'audit_content_sha256': 'c'*64,
        'raw_inventory_sha256': 'd'*64, 'worlds': worlds, 'new_model_calls': 0,
        'new_code_executions': 0, 'policy_selection': False}
    return {**r, 'content_sha256': digest(r)}


def reseal(r):
    return {**r, 'content_sha256': digest({k: v for k, v in r.items() if k != 'content_sha256'})}


def test_attempts_memories_and_known_denominators_remain_separate():
    r = report(); unknown = {**r['worlds'][0]['direction_requests'][0], 'wire_index': 4,
        'selected_topic': None, 'selected_catalog_duration_years': None,
        'minimum_displayed_duration_years': None, 'selected_is_shortest_displayed': None,
        'unique_actor_attribution': False, 'matching_actual_memory_actor_ids': [],
        'reply_status': 'no-committed-response', 'frame_status': 'unassessed-frame'}
    r['worlds'][0]['direction_requests'].append(unknown); r = reseal(r); before = digest(r)
    s = module.summarize(r); w = s['worlds'][0]
    assert digest(r) == before and len(s['decisions']) == 4
    assert w['direction_request_attempts'] == 2 and w['committed_direction_memories'] == 1
    assert w['known_selected_duration_attempts'] == 1 and w['mean_catalog_duration_on_known_attempts'] == 1
    assert w['shortest_displayed_assessable_attempts'] == 1
    assert s['decisions'][1]['displayed_shorter_alternative_to_selected'] is None
    assert w['annual'][0]['total_author_resources'] == 29
    assert s['worlds'][1]['loss_difference_from_cut']['throughput'] == -1
    assert not s['new_native_worlds'] and not s['policy_selection']


def test_unlisted_catalog_selection_and_missing_duration_are_not_failure_or_zero():
    r = report(); row = r['worlds'][0]['direction_requests'][0]
    row.update(selected_topic='SCRIPTED related unlisted', selected_catalog_duration_years=2,
               selected_is_shortest_displayed=None)
    r['worlds'][1]['direction_requests'] = []
    s = module.summarize(reseal(r))
    assert s['worlds'][0]['known_selected_duration_attempts'] == 1
    assert s['worlds'][0]['shortest_displayed_assessable_attempts'] == 0
    assert s['decisions'][0]['displayed_shorter_alternative_to_selected'] is None
    assert s['worlds'][1]['mean_catalog_duration_on_known_attempts'] is None


@pytest.mark.parametrize('change', ['missing-control', 'duplicate-wire', 'bad-year', 'different-seed',
                                   'nan-loss', 'ambiguous-claimed-unique', 'bad-duration'])
def test_bad_scope_or_lost_identity_is_rejected(change):
    r = report()
    if change == 'missing-control': r['worlds'].pop()
    if change == 'duplicate-wire': r['worlds'][0]['direction_requests'] *= 2
    if change == 'bad-year': r['worlds'][0]['annual'].pop()
    if change == 'different-seed': r['worlds'][1]['seed'] = 61002
    if change == 'nan-loss': r['worlds'][0]['scores']['throughput'] = float('nan')
    if change == 'ambiguous-claimed-unique': r['worlds'][0]['direction_requests'][0]['matching_actual_memory_actor_ids'] = ['a', 'b']
    if change == 'bad-duration': r['worlds'][0]['direction_requests'][0]['selected_catalog_duration_years'] = 0
    with pytest.raises(ValueError): module.summarize(reseal(r))


def test_actual_double_export_is_byte_deterministic_and_has_all_rows(tmp_path, monkeypatch):
    inputs = tmp_path/'inputs'; inputs.mkdir(); r = report()
    for n in ('one', 'two'): save(inputs/(n+'.json'), {k: v for k, v in r.items() if k != 'content_sha256'})
    monkeypatch.setattr(module, 'pinned_revision', lambda _: 'e'*40)
    hashes = []
    for name in ('first', 'second'):
        out = tmp_path/name
        module.export(SimpleNamespace(one=inputs/'one.json', two=inputs/'two.json', output=out))
        hashes.append({p.name: module.file_sha256(p) for p in out.iterdir()})
        summary = checked(json.loads((out/'summary.json').read_text()))
        assert len(summary['decisions']) == 3
        assert len((out/'direction-attempts.csv').read_text().splitlines()) == 4
        assert (out/'choice-years.png').stat().st_size > 10000
    assert hashes[0] == hashes[1]
    with pytest.raises(ValueError, match='distinct reports'):
        module.export(SimpleNamespace(one=inputs/'one.json', two=inputs/'one.json', output=tmp_path/'bad'))
    with pytest.raises(ValueError, match='fresh separate'):
        module.export(SimpleNamespace(one=inputs/'one.json', two=inputs/'two.json', output=inputs/'nested'))


def test_five_actor_layout_keeps_multiple_and_unknown_attempts(tmp_path):
    r = report()
    for w in r['worlds']:
        example = w['direction_requests'][0]; w['direction_requests'] = []
        for state in w['annual']:
            state['authors'] = [{**state['authors'][0], 'id': 'SCRIPTED actor '+str(i)} for i in range(5)]
        for i in range(5):
            for year in (1, 3):
                w['direction_requests'].append({**example, 'wire_index': len(w['direction_requests']),
                    'year': year, 'matching_actual_memory_actor_ids': ['SCRIPTED actor '+str(i)],
                    'selected_catalog_duration_years': i % 3+1,
                    'literal_instruction_present': w['condition'] == 'early' or
                        (w['condition'] == 'late' and year == 3)})
        # Multiple attempts at one native actor/year do not become extra years.
        w['direction_requests'].append({**w['direction_requests'][0], 'wire_index': 20,
            'selected_catalog_duration_years': None, 'selected_is_shortest_displayed': None})
        w['direction_requests'].append({**example, 'wire_index': 21,
            'selected_catalog_duration_years': None, 'selected_is_shortest_displayed': None,
            'unique_actor_attribution': False, 'matching_actual_memory_actor_ids': []})
    summary = module.summarize(reseal(r)); module.render(summary, tmp_path)
    assert len(summary['decisions']) == 36
    svg = (tmp_path/'choice-years.svg').read_text()
    assert '1, ?' in svg and 'unattributed' in svg and 'actor 5' in svg
    assert 'actor 6' not in svg
