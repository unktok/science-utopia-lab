import json
from pathlib import Path

from scripts.figures.native_fixed_evaluation_paper_v1 import export
from scripts.reports.native_fixed_evaluation_reproduce_v1 import validate

ROOT = Path(__file__).resolve().parents[2]


def test_actual_print_views_rebuild_without_changing_full_report(tmp_path):
    source = ROOT / 'research/data/native-fixed-evaluation-v1/report.json'
    before = source.read_bytes(); r = validate(json.loads(before))
    assert len(r['evaluation_rows']) == 36 and r['unavailable_label_seed_rows'] == 6
    for name in ('a', 'b'): export(source, tmp_path / name)
    files = {p.name for p in (tmp_path / 'a').iterdir()}
    assert files == {'manifest.json', 'fixed-submission-comparison.png',
                     'fixed-submission-comparison.svg', 'stopped-search-paths.png', 'stopped-search-paths.svg'}
    assert all((tmp_path / 'a' / n).read_bytes() == (tmp_path / 'b' / n).read_bytes() for n in files)
    assert source.read_bytes() == before
    manifest = json.loads((tmp_path / 'a/manifest.json').read_text())
    assert manifest['new_model_calls'] == manifest['new_native_worlds'] == 0
    assert manifest['input_report_content_sha256'] == r['content_sha256']
