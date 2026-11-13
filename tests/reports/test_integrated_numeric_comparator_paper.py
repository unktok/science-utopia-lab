"""Actual closed numeric data/source binding, not new inference or PDF layout."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-parameter-comparator-v1'


def load(path): return checked(json.loads(path.read_text()))


def test_all_six_new_slots_and_all_reused_controls_are_retained():
    r = load(DATA / 'report.json')
    slots = [v for v in r['slots'] if v['method'] == 'numeric-reserve']
    assert len(r['references']) == 8 and len(r['slots']) == 12 and len(slots) == 6
    assert [(v['objective'], v['generation'], v['reserve_units'], v['scores']['throughput'],
        v['scores']['content-utility']) for v in slots] == [
        ('throughput', 0, 3, -12, -7), ('content-utility', 0, 13, -12, -8),
        ('content-utility', 1, 27, -14, -9.333333333333332), ('throughput', 1, 10, -12, -7),
        ('throughput', 2, 12, -12, -7), ('content-utility', 2, 25, -14, -10)]
    assert all(v['status'] == 'complete' for v in slots)
    end = json.loads((DATA / 'dispatcher-end.json').read_text())
    assert end['status'] == 'closed' and len(end['steps']) == 7 and all(v['exit_code'] == 0 for v in end['steps'])
    for name, expected in end['report_files'].items():
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == expected


def test_known_reference_is_not_relabelled_as_generated_improvement():
    r = load(DATA / 'incumbents/report.json')
    final = {h['objective']: h['final'] for h in r['histories']}
    assert final['throughput']['best_known']['loss'] == -18 and final['throughput']['best_own']['loss'] == -12
    assert final['content-utility']['best_known']['loss'] == -13.333333333333332
    assert final['content-utility']['best_own']['loss'] == -10
    assert all(v['known_improvement_over_reference'] == 0 and v['best_known']['origin'] == 'reference'
        for v in final.values())
    assert len(final['throughput']['best_own']['all_tied_ids']) == 3
    assert [v['best_own']['loss'] for v in r['histories'][1]['path']] == [None, -8, -9.333333333333332, -10]
    figure = load(ROOT / 'paper/figures/native-numeric-paper-v1/manifest.json')
    assert figure['input_report_file_sha256'] == hashlib.sha256((DATA / 'incumbents/report.json').read_bytes()).hexdigest()
    assert figure['figure_width_inches'] == 5.5
    for name, expected in figure['files'].items():
        assert hashlib.sha256((ROOT / 'paper/figures/native-numeric-paper-v1' / name).read_bytes()).hexdigest() == expected


def test_all_world_input_classes_are_an_actual_double_export_not_two_partial_examples():
    r = load(DATA / 'observed-inputs/report.json')
    assert len(r['worlds']) == 6 and len(r['complete_observed_input_classes']) == 4
    group = next(v for v in r['complete_observed_input_classes'] if len(v['physical_ids']) == 3)
    assert group['all_literal_response_choices_equal'] and not group['all_full_provider_bodies_equal']
    assert all(w['requests']['wire_requests'] == 133 for w in r['worlds'] if w['identity'] in group['physical_ids'])
    assert sum(w['requests']['completed_responses'] for w in r['worlds']) == 664
    assert all(w['requests']['wire_inputs_without_committed_reply'] == 0 for w in r['worlds'])
    assert r['audit_content_sha256'] == load(DATA / 'report.json')['numeric_audit_sha256']


def test_recorded_costs_and_every_new_manuscript_table_row_match():
    costs = load(DATA / 'costs.json'); source = (ROOT / 'paper/integrated/native-numeric-comparator.tex').read_text()
    assert costs['scientist']['completed_responses'] == 664
    usage = costs['scientist']['provider_usage']
    assert usage['prompt_tokens']['recorded_sum'] == 704991 and usage['completion_tokens']['recorded_sum'] == 67549
    critic = costs['common_content_observer']
    assert critic['physical_requests'] == 93 and critic['usage']['prompt_tokens']['known_sum'] == 44481
    assert critic['usage']['output_tokens']['known_sum'] == 13766
    for row in ('1&T0&3&$-12$&$-7$&$-12$', '2&U0&13&$-12$&$-8$&$-8$',
        '3&U1&27&$-14$&$-9.3333$&$-9.3333$', '4&T1&10&$-12$&$-7$&$-12$',
        '5&T2&12&$-12$&$-7$&$-12$', '6&U2&25&$-14$&$-10$&$-10$'):
        assert row in source
    for marker in ('four exact observed full-input classes', 'post-hoc comparator', 'No designer LLM',
        'not global equivalence', '79 minutes 7 seconds', 'not a dedicated', 'no repair, refill'):
        assert marker in source
    receipt = json.loads((ROOT / 'research/results/native-parameter-comparator-closed-v1.json').read_text())
    elapsed = (datetime.fromisoformat(receipt['scientific_ended_UTC']) -
        datetime.fromisoformat(receipt['scientific_started_UTC'])).total_seconds()
    assert elapsed == receipt['scientific_elapsed_seconds'] == 4746.977303
