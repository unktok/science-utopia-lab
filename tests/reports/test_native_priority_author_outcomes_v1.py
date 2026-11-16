"""SCRIPTED post-closure join fixtures, not native or original-source proof."""
from copy import deepcopy
import csv
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from scripts.reports import native_priority_author_outcomes_v1 as r
from scripts.reports.native_priority_method_readout_v1 import analyze
from tests.reports.test_native_priority_method_readout_v1 import fixture as original_fixture
from utopia.system.design_patch import digest
from utopia.optimization.native_numeric_designer import save
from utopia.utils.data_utils import write_json_atomic
from tests.reports.test_native_author_step_summary_v1 import session as write_scripted_session


def seal(value):
    value = {k: deepcopy(v) for k, v in value.items() if k != 'content_sha256'}
    return {**value, 'content_sha256': digest(value)}


def fixture():
    p, a, slots, refs = original_fixture(); report = analyze(p, a, slots, refs)
    identities = [('reference/' + v['label'], v['status']) for v in report['references']]
    identities += [(v['cell_id'], v['status']) for v in report['slots']]
    report['behavior_evidence'] = {'traces': [{'identity': identity, 'status': status,
        'requests': {'ordered_full_request_payload_sha256': 'SCRIPTED same input'}}
        for identity, status in identities]}
    authors = []
    for row in report['slots']:
        if row['method'] != r.METHODS[2]: continue
        authors.append({'cell_id': row['cell_id'], 'request_sha256': digest(row['cell_id']),
            'parent_program_sha256': row['literal_system_sha256'],
            'submitted_program_sha256': row['literal_system_sha256'],
            'parent_observation_id': 'SCRIPTED-parent-' + row['objective'],
            'parent_loss': -10. if row['objective'] == r.OBJECTIVES[0] else -9.,
            'session': {'terminal_record_present': True, 'terminal_status': 'generated',
                'explicit_finish_observed': True, 'completed_steps': 4, 'attempted_edit_steps': 0,
                'successful_document_changes': 0, 'duplicate_unchanged_read_observations': 1}})
    return seal(report), authors


def test_all_eight_compound_cells_keep_actions_programs_observed_inputs_and_losses_separate():
    report, authors = fixture(); result = r.join(report, authors)
    assert len(result['rows']) == len({v['cell_id'] for v in result['rows']}) == 8
    assert {v['suggestion_id'] for v in result['rows']} == {'shared-id-g0', 'shared-id-g1'}
    assert all(v['literal_submitted_program_equals_parent'] for v in result['rows'])
    assert all(v['observed_full_inputs_match_a_complete_parent'] for v in result['rows'])
    assert all(v['own_minus_measured_parent'] == -1. for v in result['rows'])
    assert all(v['session']['attempted_edit_steps'] == 0 for v in result['rows'])
    # Deliberately synthetic equal-program/different-loss data are NOT physics
    # or causal proof. A join must not fabricate edits to explain an outcome.
    for group in result['by_objective'].values():
        assert group['declared_cells'] == group['recorded_sessions'] == 4
        assert group['known_session_completed_steps'] == 16
    assert not result['selection_changed'] and not result['publication_ready']


def test_generation_null_and_missing_session_are_kept_as_unknown_not_zero_or_baseline():
    report, authors = fixture(); target = next(v for v in report['slots'] if v['cell_id'] == authors[0]['cell_id'])
    target.update(status='generation-null', loss=None, literal_system_sha256=None, graph_delta=None)
    authors[0].update(submitted_program_sha256=None, session=None)
    result = r.join(seal(report), authors); row = result['rows'][0]
    assert row['status'] == 'generation-null' and row['loss'] is None
    assert row['session'] is None and row['session_evidence_status'] == 'unavailable-not-zero'
    assert row['own_minus_measured_parent'] is row['own_minus_initial_reference'] is None
    assert row['observed_full_inputs_match_a_complete_parent'] is None
    group = result['by_objective'][row['objective']]
    assert group['declared_cells'] == 4 and group['recorded_sessions'] == 3
    assert group['session_evidence_unavailable'] == 1 and group['known_session_completed_steps'] == 12


def test_a_changed_program_or_adverse_outcome_does_not_get_hidden_by_a_no_edit_label():
    report, authors = fixture(); row = next(v for v in report['slots'] if v['cell_id'] == authors[0]['cell_id'])
    row.update(literal_system_sha256='f' * 64, loss=4.)
    authors[0]['submitted_program_sha256'] = row['literal_system_sha256']
    result = r.join(seal(report), authors)['rows'][0]
    assert not result['literal_submitted_program_equals_parent']
    assert result['loss'] == 4. and result['own_minus_measured_parent'] == 14.
    assert result['session']['attempted_edit_steps'] == 0  # Other distribution edits can produce a candidate.


def test_future_matching_parent_program_is_not_used_as_a_preceding_observed_control():
    report, authors = fixture(); target = next(v for v in report['slots'] if v['cell_id'] == authors[0]['cell_id'])
    later = next(v for v in report['slots'] if v['slot_index'] > target['slot_index'])
    later['literal_system_sha256'] = 'f' * 64; authors[0]['parent_program_sha256'] = 'f' * 64
    result = r.join(seal(report), authors)['rows'][0]
    assert not result['prior_exact_parent_complete_path_ids']
    assert result['observed_full_inputs_match_a_complete_parent'] is None


@pytest.mark.parametrize('changed', ['missing', 'reorder', 'duplicate', 'program', 'no-session', 'no-finish', 'no-terminal'])
def test_incomplete_or_contradictory_author_outcome_join_is_rejected(changed):
    report, authors = fixture()
    if changed == 'missing': authors.pop()
    elif changed == 'reorder': authors[0], authors[1] = authors[1], authors[0]
    elif changed == 'duplicate': authors[1] = deepcopy(authors[0])
    elif changed == 'program': authors[0]['submitted_program_sha256'] = 'f' * 64
    elif changed == 'no-session': authors[0]['session'] = None
    elif changed == 'no-finish': authors[0]['session']['explicit_finish_observed'] = False
    else: authors[0]['session']['terminal_record_present'] = False
    with pytest.raises(ValueError): r.join(report, authors)


@pytest.mark.parametrize('destination', ['source', 'raw', 'closure', 'readouts', 'reader', 'alias', 'existing'])
def test_export_rejects_original_or_reader_destinations_before_loading_sources(tmp_path, monkeypatch, destination):
    roots = {k: tmp_path / k for k in ('run', 'source', 'analysis', 'readouts', 'reader')}
    for p in roots.values(): p.mkdir()
    alias = tmp_path / 'outside-looking'; alias.symlink_to(roots['reader'])
    outputs = {'source': roots['source'] / 'new', 'raw': roots['run'] / 'new',
        'closure': roots['analysis'] / 'new', 'readouts': roots['readouts'] / 'new',
        'reader': roots['reader'] / 'new', 'alias': alias / 'new', 'existing': tmp_path / 'already'}
    outputs['existing'].mkdir()
    monkeypatch.setattr(r, 'ROOT', roots['reader'])
    def forbidden(*a): pytest.fail('destination guard must precede source/evidence loading')
    monkeypatch.setattr(r, 'pinned_revision', forbidden)
    args = SimpleNamespace(output=outputs[destination], **{'origin_' + k: roots[k]
        for k in ('run', 'source', 'analysis', 'readouts')})
    with pytest.raises(ValueError, match='fresh output outside'): r.export(args)
    assert outputs[destination].exists() is (destination == 'existing')


def original_journals(tmp_path, *, missing_generation=False):
    p, _, original_slots, _ = original_fixture(); report, authors = fixture(); states = {}
    for author in authors:
        row = next(x for x in report['slots'] if x['cell_id'] == author['cell_id'])
        entry = next(x for x in original_slots if x['slot']['method'] == row['method']
            and x['slot']['replication'] == row['replication'] and x['slot']['objective'] == row['objective']
            and x['slot']['generation'] == row['generation'])
        history = tmp_path / 'search' / row['method'] / ('history-' + str(row['replication'])) / row['objective']
        request = {'generation': row['generation'], 'loss_spec': p['losses'][row['objective']],
            'based_on_observation_id': author['parent_observation_id'],
            'parent_system': entry['parent_system'], 'observations': [{'observation': {
                'observation_id': author['parent_observation_id'], 'candidate': entry['parent_system'],
                'status': 'complete', 'loss': author['parent_loss']}}]}
        request_sha = digest(request); definition = {'SCRIPTED': 'not executable authored distribution'}
        missing = missing_generation and row['cell_id'] == authors[0]['cell_id']
        record = {'request': request, 'request_sha256': request_sha, 'definition': definition,
            'draws': [] if missing else [{'suggestion': entry['suggestion']}],
            'observations': [] if missing else [entry['observation']]}
        states.setdefault(history, {'pending': None, 'records': []})['records'].append(record)
        if missing:
            row.update(status='generation-null', loss=None, literal_system_sha256=None,
                graph_delta=None, generation_error={'type': 'SCRIPTED-before-session-failure'})
        else:
            proposal = history / 'authoring' / ('proposal-' + request_sha)
            directory = proposal / 'editor-session/authoring' / ('generation-' + request_sha)
            directory.mkdir(parents=True)
            write_scripted_session(directory, request=request, definition=definition)
            save(proposal / 'result.json', {'definition': definition, 'SCRIPTED': 'returned result only'})
    for history, state in states.items(): write_json_atomic(history / 'campaign/native-adaptive-state.json', state)
    return p, seal(report), states


@pytest.mark.parametrize('missing', [False, True])
def test_actual_collection_paths_plain_campaigns_and_staged_public_formats_join_all_cells(tmp_path, missing):
    p, report, _ = original_journals(tmp_path, missing_generation=missing)
    authors, inputs = r.collect(tmp_path, p, report); result = r.join(report, authors)
    assert len(result['rows']) == 8 and inputs
    assert (authors[0]['session'] is None) is missing
    assert result['rows'][0]['status'] == ('generation-null' if missing else 'complete')
    assert result['by_objective'][r.OBJECTIVES[0]]['session_evidence_unavailable'] == int(missing)


@pytest.mark.parametrize('changed', ['pending', 'parent', 'returned-definition', 'request-objective'])
def test_collection_cannot_attach_foreign_request_parent_or_submitted_definition(tmp_path, changed):
    p, report, states = original_journals(tmp_path)
    history, state = next(iter(states.items())); record = state['records'][0]
    if changed == 'pending': state['pending'] = {'SCRIPTED': 'still active'}
    elif changed == 'parent': record['request']['observations'][0]['observation']['candidate'] = {'SCRIPTED': 'foreign'}
    elif changed == 'request-objective': record['request']['loss_spec'] = {'SCRIPTED': 'foreign loss'}
    else:
        proposal = history / 'authoring' / ('proposal-' + record['request_sha256']) / 'result.json'
        value = {'definition': {'SCRIPTED': 'different return'}}; value['content_sha256'] = digest(value)
        write_json_atomic(proposal, value)
    if changed != 'returned-definition':
        write_json_atomic(history / 'campaign/native-adaptive-state.json', state)
    with pytest.raises(ValueError): r.collect(tmp_path, p, report)


@pytest.mark.parametrize('missing', [False, True])
def test_public_export_has_three_matching_readonly_files_and_keeps_null_csv_cells(tmp_path, monkeypatch, missing):
    raw = tmp_path / 'raw'; p, report, _ = original_journals(raw, missing_generation=missing)
    roots = {k: tmp_path / k for k in ('source', 'analysis', 'readouts', 'reader')}
    for root in roots.values(): root.mkdir()
    save(raw / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    (raw / 'writer.lock').touch()
    report_dir = roots['readouts'] / 'report-1'; report_dir.mkdir()
    save(report_dir / 'report.json', {k: v for k, v in report.items() if k != 'content_sha256'})
    cost_path = roots['analysis'] / 'costs-1.json'
    save(cost_path, {'scope': 'SCRIPTED total campaign costs only', 'scientist': {'SCRIPTED': True}})
    # Source/closure provenance is explicitly SCRIPTED here, unlike actual
    # origin_evidence. Exercise collection/join/export, not native cold proof.
    monkeypatch.setattr(r, 'ROOT', roots['reader'])
    monkeypatch.setattr(r, 'pinned_revision', lambda root: 'c' * 40
        if root.resolve() == roots['reader'].resolve() else p['source_commit'])
    monkeypatch.setattr(r, 'origin_evidence', lambda origin: (p, {'SCRIPTED': True}, {}))
    monkeypatch.setattr(r, 'evidence_files', lambda origin: [raw / 'plan.json', cost_path, report_dir / 'report.json'])
    before = r._inventory(raw)
    with tempfile.TemporaryDirectory(prefix='priority-author-export-scripted-') as external:
        outputs = [Path(external) / ('export-' + str(i)) for i in (1, 2)]
        for output in outputs:
            r.export(SimpleNamespace(output=output, origin_run=raw,
                **{'origin_' + k: roots[k] for k in ('source', 'analysis', 'readouts')}))
        files = {p.name: p.read_bytes() for p in outputs[0].iterdir()}
        assert set(files) == {'report.json', 'authors.csv', 'manifest.json'}
        assert files == {p.name: p.read_bytes() for p in outputs[1].iterdir()}
        result = r.read(outputs[0] / 'report.json'); assert len(result['rows']) == 8
        assert result['original_campaign_cost_summary']['scope'] == 'SCRIPTED total campaign costs only'
        with (outputs[0] / 'authors.csv').open(newline='') as stream: rows = list(csv.DictReader(stream))
        assert len(rows) == 8
        if missing:
            assert rows[0]['status'] == 'generation-null'
            assert rows[0]['completed_steps'] == rows[0]['loss'] == rows[0]['own_minus_measured_parent'] == ''
        with pytest.raises(ValueError, match='fresh output'): r.export(SimpleNamespace(output=outputs[0],
            origin_run=raw, **{'origin_' + k: roots[k] for k in ('source', 'analysis', 'readouts')}))
    assert r._inventory(raw) == before
