"""Compact actual source-read evidence, not runtime/calibration or model gains."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked


def test_prospective_scope_preserves_native_bytes_and_legacy_rejection():
    root = Path(__file__).resolve().parents[2]
    r = checked(json.loads((root/'research/results/native-longitudinal-source-scope-retained-v1.json').read_text()))
    assert r['base_native_source_commit'] == 'f47270b967fa167d59df759bebe7b6b104b383d3'
    assert r['source_commit'] == 'f2c0d1aabdfbf68893b1ecf5c711a163d7fe9b96'
    assert r['inherited_native_files'] == 273
    assert len(r['declared_author_modules']) == 4 and len(r['added_author_modules']) == 1
    assert all(x['literal_changed'] and x['base_sha256'] != x['prospective_sha256']
        for x in r['declared_author_modules'].values())
    assert r['legacy_guard_actual_rejection'] == {'type': 'ValueError',
        'error': 'original scientist/effect source differs: utopia/optimization/native_adaptive_search.py'}
    assert not r['legacy_guard_modified']
    assert r['guard']['path'] == 'scripts/native_longitudinal_source_scope_v1.py'
    assert r['targeted_tests']['passed'] == 41 and r['new_model_calls'] == 0
    for key in ('runner_cold_integration_proved', 'real_backend_readiness_proved',
                'scientific_gain_claimed', 'publication_ready'):
        assert not r[key]
    assert r['earlier_scope_snapshot']['content_sha256'] != r['scope_content_sha256']
    assert 'Did not yet bind' in r['earlier_scope_snapshot']['limitation']
