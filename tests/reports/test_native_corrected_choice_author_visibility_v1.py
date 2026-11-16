"""Corrected-profile real journal formats; upstream closure/Git are SCRIPTED."""
from pathlib import Path

import pytest

from scripts.reports import export_native_author_visibility_v1 as base
from scripts.reports import export_native_corrected_choice_author_visibility_v1 as module
from tests.reports.test_export_native_author_visibility_v1 import fixture, forbid_new_science


@pytest.mark.parametrize('missing', [False, True])
def test_new_profile_all8_double_export_keeps_four_generations_and_null(tmp_path, monkeypatch, missing):
    args, roots, calls, _ = fixture(tmp_path, monkeypatch, missing=missing, corrected=True)
    before = base._inventory(roots['raw']); module.export(args)
    first = args.output; args.output = tmp_path / 'other'; module.export(args)
    assert set(base.same_files(first, args.output)) == {'report.json', 'steps.csv', 'manifest.json'}
    result = base.read(first / 'report.json')
    assert result['schema'] == 'scienceutopia.native-corrected-choice-author-visibility.v1.all8-join'
    assert result['recorded_sessions'] == (7 if missing else 8)
    assert len({row['cell_id'] for row in result['rows']}) == 8
    assert base.read(first / 'manifest.json')['schema'] == module.SCHEMA
    if missing: assert result['rows'][0]['visibility'] is result['rows'][0]['loss'] is None
    assert before == base._inventory(roots['raw']) and len(calls) == 2


def test_new_visibility_export_rejects_old_author_chain_instead_of_relabeling(tmp_path, monkeypatch):
    args, _, _, _ = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='normally closed'): module.export(args)
    assert not args.output.exists()


@pytest.mark.parametrize('place', ['reader', 'raw', 'science', 'author_source', 'authors', 'alias', 'existing'])
def test_new_visibility_output_preflight_stops_before_reading_or_source_binding(tmp_path, monkeypatch, place):
    args, roots, _, _ = fixture(tmp_path, monkeypatch, corrected=True)
    if place == 'alias':
        alias = tmp_path / 'alias'; alias.symlink_to(roots['reader']); args.output = alias / 'out'
    elif place == 'existing': args.output = roots['closure']
    else: args.output = roots[place] / 'out'
    monkeypatch.setattr(base, 'pinned_revision', lambda *a: pytest.fail('preflight must come before source binding'))
    with pytest.raises(ValueError, match='fresh output outside'): module.export(args)
