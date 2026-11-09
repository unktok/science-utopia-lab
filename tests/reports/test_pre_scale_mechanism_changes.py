"""SYNTHETIC literal-change QA; no model, world or authored source execution."""
from copy import deepcopy
import json
import subprocess
import sys

import pytest

from scripts.reports.pre_scale_mechanism_changes_v1 import describe, literal_changes, project
from scripts.reports.pre_scale_search_v1 import summarize
from tests.reports.test_pre_scale_search_report import fixture, rehash
from tests.reports.test_pre_scale_search_v1 import plan
from utopia.system.design_patch import digest


def base():
    return deepcopy(plan()['reference_systems']['open-seed'])


def submit(report, candidate, *, status='complete'):
    slot = report['search_slots'][0]
    slot.update(status=status, own_loss=0 if status == 'complete' else None,
        system_sha256=digest(candidate))
    report['systems_by_sha256'][digest(candidate)] = candidate
    return rehash(report)


def test_all_null_slots_remain_unsubmitted_and_inputs_are_unchanged(tmp_path):
    report = summarize(fixture(tmp_path)); original = deepcopy(report)
    result = project(report)
    assert report == original and len(result['rows']) == 16
    assert all(r['difference_from_common_initial'] is None for r in result['rows'])
    assert result['new_model_calls'] == result['new_authored_code_executions'] == 0
    assert result['semantic_novelty_or_effect_inferred'] is False


def test_failed_submitted_source_remains_visible_and_is_never_executed(tmp_path):
    report = summarize(fixture(tmp_path)); candidate = base()
    node = next(m for m in candidate['mechanisms'] if m['mechanism_id'] == 'world.selection')
    node['parameters']['code_artifact']['source'] = "raise RuntimeError('MUST NOT RUN')\n"
    result = project(submit(report, candidate, status='failed'))
    row = result['rows'][0]; diff = row['difference_from_common_initial']
    assert row['status'] == 'failed' and row['own_loss'] is None
    assert diff['changed_mechanism_categories'] == {'literal-source': 1}
    assert diff['nodes_added'] == diff['nodes_removed'] == []
    assert not diff['connections_literal_changed'] and not diff['schedules_literal_changed']
    assert diff['mechanism_changes'][0]['mechanism_id'] == 'world.selection'


def test_parameter_change_is_not_labelled_source_or_graph_change():
    before = base(); after = deepcopy(before)
    next(m for m in after['mechanisms'] if m['mechanism_id'] == 'information-office')['parameters']['max_records'] = 0
    result = describe(before, after)
    assert result['changed_mechanism_categories'] == {'parameter-or-program': 1}
    assert result['mechanism_changes'][0]['changes'][0]['after']['value'] == 0
    assert not result['connections_literal_changed'] and result['nodes_added'] == []


def test_process_wrapped_source_is_still_a_literal_source_change():
    before = base(); after = deepcopy(before)
    node = next(m for m in after['mechanisms'] if m['mechanism_id'] == 'open-source')
    node['parameters']['delegate']['parameters']['code_artifact']['source'] += '# SYNTHETIC comment only\n'
    result = describe(before, after)
    assert result['changed_mechanism_categories'] == {'literal-source': 1}
    assert result['mechanism_changes'][0]['mechanism_id'] == 'open-source'


def test_new_node_and_schedule_are_not_collapsed_to_parameter_changes():
    before = base(); after = deepcopy(before)
    node = deepcopy(next(m for m in after['mechanisms'] if m['mechanism_id'] == 'information-office'))
    node['mechanism_id'] = 'SYNTHETIC-extra-office'
    after['mechanisms'].append(node)
    after['schedules'].append({'mechanism_id': node['mechanism_id'], 'phase': 195, 'trigger': 'annual'})
    result = describe(before, after)
    assert result['nodes_added'] == ['SYNTHETIC-extra-office'] and result['nodes_removed'] == []
    assert result['schedules_literal_changed'] and result['node_order_changed']
    inverse = describe(after, before)
    assert inverse['nodes_removed'] == ['SYNTHETIC-extra-office']


def test_order_changes_are_literal_not_claimed_semantic_equivalence_or_novelty():
    before = base(); after = deepcopy(before)
    after['connections'].reverse(); after['schedules'].reverse(); after['mechanisms'].reverse()
    result = describe(before, after)
    assert result['connections_literal_changed'] and result['schedules_literal_changed']
    assert result['node_order_changed'] and result['mechanism_changes'] == []
    assert result['nodes_added'] == result['nodes_removed'] == []


def test_removed_wire_and_changed_port_are_recorded_as_structure_not_source():
    before = base(); after = deepcopy(before)
    after['connections'].pop()
    node = next(m for m in after['mechanisms'] if m['mechanism_id'] == 'information-office')
    node['inputs'][0]['required'] = False
    result = describe(before, after)
    assert result['connections_literal_changed'] and not result['schedules_literal_changed']
    assert result['changed_mechanism_categories'] == {'mechanism-interface': 1}


def test_duplicate_node_identity_cannot_hide_a_literal_change():
    before = base(); after = deepcopy(before)
    after['mechanisms'].append(deepcopy(after['mechanisms'][0]))
    with pytest.raises(ValueError, match='unique mechanism identities'):
        describe(before, after)


@pytest.mark.parametrize('before,after', [({'x': None}, {}), ({}, {'x': None}),
    ({'x': {}}, {}), ({}, {'x': []}), ([None], []), ([], [[]])])
def test_absent_null_and_empty_containers_remain_distinct(before, after):
    rows = literal_changes(before, after)
    assert len(rows) == 1
    assert rows[0]['before']['present'] != rows[0]['after']['present']


@pytest.mark.parametrize('before,after', [(False, 0), (1, 1.0), ({}, []), ('1', 1)])
def test_json_types_are_not_silently_equated(before, after):
    rows = literal_changes(before, after)
    assert len(rows) == 1 and rows[0]['before']['sha256'] != rows[0]['after']['sha256']


def test_long_source_remains_hash_bound_without_duplicating_body():
    before = base(); after = deepcopy(before)
    node = next(m for m in after['mechanisms'] if m['mechanism_id'] == 'world.selection')
    source = node['parameters']['code_artifact']['source'] + '# SYNTHETIC metadata only\n'
    node['parameters']['code_artifact']['source'] = source
    row = describe(before, after)['mechanism_changes'][0]['changes'][0]
    assert row['after'] == {'present': True, 'sha256': digest(source), 'value': None, 'value_omitted': True}


@pytest.mark.parametrize('problem', ['wrong-schema', 'changed-content', 'missing-slot', 'duplicate-slot',
    'missing-baseline', 'wrong-policy-key', 'missing-policy', 'invented-null-policy', 'changed-arm'])
def test_inconsistent_retained_reports_are_rejected(tmp_path, problem):
    report = summarize(fixture(tmp_path))
    if problem == 'wrong-schema': report['schema'] = 'not-a-closed-pre-scale-report'
    elif problem == 'changed-content': report['source_commit'] = 'BAD'
    elif problem == 'missing-slot': report['search_slots'].pop()
    elif problem == 'duplicate-slot': report['search_slots'][-1] = deepcopy(report['search_slots'][0])
    elif problem == 'missing-baseline': report['references'] = [r for r in report['references'] if r['row_id'] != 'reference:open-seed']
    elif problem == 'wrong-policy-key': report['systems_by_sha256']['0'*64] = base()
    elif problem == 'missing-policy':
        submit(report, base()); report['systems_by_sha256'].pop(digest(base()))
    elif problem == 'changed-arm': report['search_slots'][0]['arm'] = 'efficiency:random'
    else: report['search_slots'][0]['system_sha256'] = digest(base())
    if problem != 'changed-content': rehash(report)
    with pytest.raises(ValueError): project(report)


def test_noop_submission_has_explicit_empty_difference_not_an_unsubmitted_slot(tmp_path):
    result = project(submit(summarize(fixture(tmp_path)), base()))
    diff = result['rows'][0]['difference_from_common_initial']
    assert diff is not None and diff['mechanism_changes'] == []
    assert diff['nonmechanism_section_changes'] == {} and diff['baseline_sha256'] == diff['candidate_sha256']


def test_cli_is_read_only_reproducible_and_refuses_existing_output(tmp_path):
    report = submit(summarize(fixture(tmp_path/'SYNTHETIC-raw')), base())
    path = tmp_path/'SYNTHETIC-report.json'; path.write_text(json.dumps(report))
    original = path.read_bytes(); outputs = [tmp_path/f'SYNTHETIC-result-{i}.json' for i in range(2)]
    for output in outputs:
        subprocess.run([sys.executable, '-m', 'scripts.reports.pre_scale_mechanism_changes_v1',
            '--report', str(path), '--output', str(output)], check=True, capture_output=True, text=True)
    assert outputs[0].read_bytes() == outputs[1].read_bytes() and path.read_bytes() == original
    rejected = subprocess.run([sys.executable, '-m', 'scripts.reports.pre_scale_mechanism_changes_v1',
        '--report', str(path), '--output', str(outputs[0])], capture_output=True, text=True)
    assert rejected.returncode != 0 and 'fresh independent output' in rejected.stderr
    assert path.read_bytes() == original
