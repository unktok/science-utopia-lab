"""Byte retention of a clearly marked SCRIPTED alias example, not new science."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256


def test_retained_scripted_alias_bundle_keeps_both_scopes_and_missing_own_rows():
    root = Path(__file__).resolve().parents[2]
    data = root / 'research/data/native-joint-incumbent-preparation-v1'
    values = {name: checked(json.loads((data / name).read_text()))
        for name in ('aliases.json', 'report.json', 'manifest.json', 'freeze-manifest.json')}
    report, aliases = values['report.json'], values['aliases.json']
    assert report['data_identity']['dataset'] == 'explicit-QA-fixture'
    assert report['frozen_aliases'] == aliases
    assert values['manifest.json']['analysis_source_commit'] == report['analysis_source_commit']
    for manifest in (values['manifest.json'], values['freeze-manifest.json']):
        assert manifest['new_native_worlds'] == manifest['new_model_calls'] == 0
        assert manifest['aliases_content_sha256'] == aliases['content_sha256']
        for name, expected in manifest['files'].items(): assert file_sha256(data / name) == expected
    assert len(aliases['aliases']) == 16 and len(report['logical_rows']) == 32
    assert len(report['fixed_policy_contrasts']) == 32 and len(report['own_minus_incumbent']) == 16
    assert report['original_physical_worlds'] == 18
    assert len({r['physical_job'] for r in report['logical_rows'] if r['physical_job'] is not None}) == 6
    unavailable = [r for r in report['logical_rows'] if r['physical_job'] is None]
    assert len(unavailable) == 2
    assert all(r['history'] == 'numeric:content-utility' and r['readout'] == 'own-submission'
        and all(v is None for v in r['scores'].values()) for r in unavailable)
    assert not report['interpretation']['selection_uses_evaluation_outcomes']
    assert not report['interpretation']['publication_ready']
