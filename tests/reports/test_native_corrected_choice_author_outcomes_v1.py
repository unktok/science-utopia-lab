"""Four-step SCRIPTED journals/pure joins, not native or source provenance."""
import csv
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from scripts.reports import native_corrected_choice_author_outcomes_v1 as module
from scripts.reports import native_priority_author_outcomes_v1 as base
from tests.reports import test_native_priority_author_outcomes_v1 as legacy
from tests.reports.test_native_corrected_choice_readout_v1 import fixture as corrected_fixture
from utopia.optimization.native_numeric_designer import save


def fixture(monkeypatch):
    monkeypatch.setattr(legacy, 'original_fixture', corrected_fixture)
    return legacy.fixture()


def test_all_four_generations_and_both_objectives_keep_actions_paths_and_losses(monkeypatch):
    report, authors = fixture(monkeypatch); result = module.join(report, authors)
    assert result['schema'] == module.SCHEMA and len(result['rows']) == 8
    assert {row['replication'] for row in result['rows']} == {0}
    assert {row['generation'] for row in result['rows']} == {0, 1, 2, 3}
    assert len({row['cell_id'] for row in result['rows']}) == 8
    assert all(row['observed_full_inputs_match_a_complete_parent'] for row in result['rows'])
    assert all(group['declared_cells'] == group['recorded_sessions'] == 4 for group in result['by_objective'].values())
    assert not result['selection_changed'] and not result['publication_ready']
    with pytest.raises(ValueError): base.join(report, authors)


def test_original_legacy_report_is_not_relabelled_as_corrected():
    report, authors = legacy.fixture()
    with pytest.raises(ValueError): module.join(report, authors)


@pytest.mark.parametrize('missing', [False, True])
def test_actual_plain_four_record_campaign_and_staged_collection_formats(tmp_path, monkeypatch, missing):
    fixture(monkeypatch)
    p, report, states = legacy.original_journals(tmp_path, missing_generation=missing)
    assert p['generations'] == 4 and len(states) == 2
    authors, inputs = module.collect(tmp_path, p, report); result = module.join(report, authors)
    assert inputs and len(result['rows']) == 8
    assert all(len(state['records']) == 4 for state in states.values())
    assert (authors[0]['session'] is None) is missing
    assert result['by_objective'][module.OBJECTIVES[0]]['session_evidence_unavailable'] == int(missing)


@pytest.mark.parametrize('missing', [False, True])
def test_public_pair_exports_all8_with_explicit_corrected_origin_profile(tmp_path, monkeypatch, missing):
    fixture(monkeypatch); raw = tmp_path / 'raw'
    p, report, _ = legacy.original_journals(raw, missing_generation=missing)
    roots = {key: tmp_path / key for key in ('source', 'analysis', 'readouts', 'reader')}
    for root in roots.values(): root.mkdir()
    save(raw / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'}); (raw / 'writer.lock').touch()
    report_dir = roots['readouts'] / 'report-1'; report_dir.mkdir()
    save(report_dir / 'report.json', {k: v for k, v in report.items() if k != 'content_sha256'})
    cost = roots['analysis'] / 'costs-1.json'; save(cost, {'scope': 'SCRIPTED complete cost scope'})
    monkeypatch.setattr(base, 'ROOT', roots['reader'])
    monkeypatch.setattr(base, 'pinned_revision', lambda root: 'c' * 40 if root == roots['reader'] else p['source_commit'])
    calls = []
    def origin(value, **kwargs):
        calls.append(kwargs); return p, {'SCRIPTED': 'not actual source-bound closure'}, {}
    monkeypatch.setattr(base, 'origin_evidence', origin)
    monkeypatch.setattr(base, 'evidence_files', lambda origin: [raw / 'plan.json', cost, report_dir / 'report.json'])
    def forbidden(*args, **kwargs): pytest.fail('read-only author export cannot call models/execute source')
    monkeypatch.setattr('requests.Session.post', forbidden)
    monkeypatch.setattr('openai.OpenAI.__init__', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)
    before = base._inventory(raw)
    with tempfile.TemporaryDirectory(prefix='scienceutopia-corrected-author-fixture-') as directory:
        outputs = [Path(directory) / str(i) for i in (1, 2)]
        for output in outputs:
            module.export(SimpleNamespace(output=output, origin_run=raw,
                **{'origin_' + key: roots[key] for key in ('source', 'analysis', 'readouts')}))
        first = {f.name: f.read_bytes() for f in outputs[0].iterdir()}
        assert first == {f.name: f.read_bytes() for f in outputs[1].iterdir()}
        assert module.read(outputs[0] / 'report.json')['schema'] == module.SCHEMA
        assert module.read(outputs[0] / 'manifest.json')['schema'] == module.SCHEMA + '.export'
        with (outputs[0] / 'authors.csv').open() as stream: rows = list(csv.DictReader(stream))
        assert len(rows) == 8 and {row['generation'] for row in rows} == {'0', '1', '2', '3'}
        if missing: assert rows[0]['loss'] == rows[0]['completed_steps'] == ''
    assert before == base._inventory(raw) and calls == [{'profile': module.PROFILE}] * 2
