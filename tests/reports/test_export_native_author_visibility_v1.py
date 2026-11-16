"""SCRIPTED origin/Git provenance; real journals/locks/CLI and deterministic files.

This is not the real closed study, a fresh native audit or model readiness.
"""
import csv
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from scripts.reports import export_native_author_visibility_v1 as e
from scripts.reports.native_author_step_summary_v1 import read_session
from tests.optimization.test_native_world import loss_spec
from tests.reports.test_native_author_visibility_v1 import journal
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

READER, AUTHOR, SCIENCE = '1' * 40, '2' * 40, '3' * 40


def fixture(tmp_path, monkeypatch, *, missing=False):
    roots = {k: tmp_path / k for k in ('reader', 'author_source', 'science', 'raw', 'authors', 'closure', 'readouts')}
    for p in roots.values(): p.mkdir()
    monkeypatch.setattr(e, 'ROOT', roots['reader'])
    heads = {roots['reader']: READER, roots['author_source']: AUTHOR, roots['science']: SCIENCE}
    monkeypatch.setattr(e, 'pinned_revision', lambda p: heads[Path(p)])
    schedule = [{'method': 'free-code-graph', 'replication': h, 'objective': o, 'generation': g}
        for g in (0, 1) for h in (0, 1) for o in ('content-utility', 'resource-aware-content')]
    p = save(roots['raw'] / 'plan.json', {'schema': 'scienceutopia.native-priority-method-comparison.v1.plan',
        'source_commit': SCIENCE, 'schedule': schedule,
        'losses': {o: loss_spec() for o in ('content-utility', 'resource-aware-content')}})
    (roots['raw'] / 'writer.lock').touch()
    rows = []; original_inputs = {str(roots['raw'] / 'plan.json'): file_sha256(roots['raw'] / 'plan.json')}
    for i, slot in enumerate(schedule):
        request = {'loss_spec': loss_spec(), 'generation': slot['generation'], 'SCRIPTED': 'no inference'}
        sha = digest(request)
        directory = (roots['raw'] / 'search/free-code-graph' / ('history-' + str(slot['replication']))
            / slot['objective'] / 'authoring' / ('proposal-' + sha) / 'editor-session/authoring' / ('generation-' + sha))
        session = None
        if not (missing and i == 0):
            directory.mkdir(parents=True); journal(directory, generation=slot['generation'])
            session = read_session(directory); original_inputs.update(session['file_sha256'])
        rows.append({'cell_id': e.cell_id(slot), 'replication': slot['replication'],
            'objective': slot['objective'], 'generation': slot['generation'],
            'status': 'generation-null' if session is None else 'complete',
            'loss': None if session is None else float(i), 'request_sha256': sha, 'session': session})
    audit = {'raw_inventory_sha256': digest(e._inventory(roots['raw']))}
    report = {'schema': 'scienceutopia.native-priority-author-outcomes.v1', 'rows': rows,
        'scientific_source_commit': SCIENCE, 'analysis_source_commit': AUTHOR,
        'original_raw_inventory_sha256': audit['raw_inventory_sha256'],
        'new_model_calls': 0, 'new_code_executions': 0, 'selection_changed': False}
    one = roots['authors'] / 'report-1'; one.mkdir()
    save(one / 'report.json', report); (one / 'authors.csv').write_text('SCRIPTED,not real scientific export\n')
    save(one / 'manifest.json', {'analysis_source_commit': AUTHOR, 'scientific_source_commit': SCIENCE,
        'new_model_calls': 0, 'new_code_executions': 0, 'input_files': original_inputs,
        'files': {p.name: file_sha256(p) for p in one.iterdir()}})
    shutil.copytree(one, roots['authors'] / 'report-2')
    save(roots['authors'] / 'started.json', {'schema': e.PRECEDING,
        'analysis_source_commit': AUTHOR, 'scientific_source_commit': SCIENCE,
        'new_inference_allowed': False, 'retry_failed_stages': False,
        'plan_file_sha256': file_sha256(roots['raw'] / 'plan.json'), 'origin': {
            'run': str(roots['raw']), 'source': str(roots['science']),
            'analysis': str(roots['closure']), 'readouts': str(roots['readouts'])}})
    ended = save(roots['authors'] / 'ended.json', {'status': 'closed', 'new_model_calls': 0,
        'new_native_worlds': 0, 'steps': [{'stage': 'report-1', 'exit_code': 0},
            {'stage': 'report-2', 'exit_code': 0}],
        'report_files': {p.name: file_sha256(p) for p in one.iterdir()}})
    monkeypatch.setattr(e, 'evidence_files', lambda origin: [roots['raw'] / 'plan.json'])
    origins = []
    def origin(origin):
        # Actual API shape; only provenance upstream is SCRIPTED here.
        assert origin['input_files'] == {str(roots['raw'] / 'plan.json'): file_sha256(roots['raw'] / 'plan.json')}
        origins.append(origin)
        return p, audit, {'SCRIPTED': 'no new candidate bank or world'}
    monkeypatch.setattr(e, 'origin_evidence', origin)
    args = SimpleNamespace(run=roots['raw'], author_outcomes=roots['authors'],
        author_source=roots['author_source'], scientific_source=roots['science'], output=tmp_path / 'out')
    return args, roots, origins, ended


@pytest.mark.parametrize('missing', [False, True])
def test_export_real_journals_to_two_matching_three_file_sets_without_science(tmp_path, monkeypatch, missing):
    args, roots, calls, _ = fixture(tmp_path, monkeypatch, missing=missing)
    before = e._inventory(roots['raw']); e.export(args)
    first = args.output; args.output = tmp_path / 'other'; e.export(args)
    assert set(e.same_files(first, args.output)) == {'report.json', 'steps.csv', 'manifest.json'}
    assert before == e._inventory(roots['raw']) and len(calls) == 2
    report = e.read(first / 'report.json'); assert len(report['rows']) == 8
    assert report['recorded_sessions'] == (7 if missing else 8)
    with (first / 'steps.csv').open() as stream: rows = list(csv.DictReader(stream))
    assert len({r['cell_id'] for r in rows}) == 8
    assert len(rows) == (36 if missing else 40)
    assert report['rows'][-1]['loss'] == 7. and not report['publication_ready']
    if missing:
        assert report['rows'][0]['loss'] is None
        assert rows[0]['row_kind'] == 'missing-session' and rows[0]['native_loss'] == ''


@pytest.mark.parametrize('place', ['reader', 'science', 'raw', 'authors', 'author_source', 'alias', 'existing'])
def test_destination_preflight_precedes_original_reads_or_source_binding(tmp_path, monkeypatch, place):
    args, roots, _, _ = fixture(tmp_path, monkeypatch)
    if place == 'alias':
        alias = tmp_path / 'alias'; alias.symlink_to(roots['reader']); args.output = alias / 'out'
    elif place == 'existing': args.output = roots['closure']
    else: args.output = roots[place] / 'out'
    def forbidden(*a): pytest.fail('invalid destination must stop before source binding')
    monkeypatch.setattr(e, 'pinned_revision', forbidden)
    with pytest.raises(ValueError, match='fresh output outside'): e.export(args)


@pytest.mark.parametrize('change', ['stopped', 'new-calls', 'paired-file', 'manifest-file', 'raw-input', 'author-head'])
def test_changed_provenance_stops_before_creating_output(tmp_path, monkeypatch, change):
    args, roots, _, ended = fixture(tmp_path, monkeypatch)
    if change in ('stopped', 'new-calls'):
        p = roots['authors'] / 'ended.json'; p.rename(roots['authors'] / 'original-ended.json')
        new = {k:v for k,v in ended.items() if k != 'content_sha256'}
        new['status' if change == 'stopped' else 'new_model_calls'] = 'stopped' if change == 'stopped' else 1
        save(p, new)
    elif change == 'paired-file': (roots['authors'] / 'report-2/authors.csv').write_text('changed\n')
    elif change == 'manifest-file': (roots['authors'] / 'report-1/manifest.json').write_text('{}\n')
    elif change == 'raw-input':
        p = next(roots['raw'].rglob('step-00.started.json')); p.write_text(p.read_text() + '\n')
    else:
        old = e.pinned_revision
        monkeypatch.setattr(e, 'pinned_revision', lambda p: 'f' * 40 if p == roots['author_source'] else old(p))
    with pytest.raises((ValueError, KeyError)): e.export(args)
    assert not args.output.exists()


def test_mutation_after_journal_read_is_not_hidden_by_joined_values(tmp_path, monkeypatch):
    args, roots, _, _ = fixture(tmp_path, monkeypatch); original = e.read_visibility; mutated = []
    def read_and_change(path):
        value = original(path)
        if not mutated:
            target = path / 'step-00.started.json'; target.write_text(target.read_text() + '\n'); mutated.append(target)
        return value
    monkeypatch.setattr(e, 'read_visibility', read_and_change)
    with pytest.raises(ValueError, match='changed during export'): e.export(args)
    assert mutated and not args.output.exists()


def test_public_cli_parser_forwards_all_path_names(tmp_path, monkeypatch):
    captured = []
    names = ('run', 'author-outcomes', 'author-source', 'scientific-source', 'output')
    monkeypatch.setattr('sys.argv', ['export'] + [v for k in names for v in ('--' + k, str(tmp_path / k))])
    monkeypatch.setattr(e, 'export', captured.append); e.main()
    assert len(captured) == 1
    for name in names: assert getattr(captured[0], name.replace('-', '_')) == tmp_path / name
