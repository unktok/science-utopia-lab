"""Source/receipt documentation checks; never treats smoke data as outcomes."""
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_summary_source_and_successful_native_API_qa_without_result_claim():
    r = checked(json.loads((ROOT / 'research/results/native-catalog-summary-preparation-v1.json').read_text()))
    assert r['analysis_source_commit'] == 'b0cbbb85772693d4c5774d73d9e39624edcada10'
    for name in ('scripts/reports/native_catalog_actuation_summary_v1.py', 'scripts/finish_native_catalog_summary_v1.py'):
        assert subprocess.check_output(['git', 'show', r['analysis_source_commit'] + ':' + name], cwd=ROOT) == (ROOT / name).read_bytes()
    assert [q['tests'] for q in r['qa']] == [19, 35]
    assert all(not q['failures'] and not q['errors'] for q in r['qa'])
    assert set(r['smoke_PNGs_visually_reviewed']) == {'losses-and-activity.png', 'project-states.png'}
    assert 'SCRIPTED' in r['smoke_figure_data']
    assert not r['actual_scientific_figures_visually_reviewed']
    assert not r['new_model_calls'] and not r['new_native_worlds'] and not r['publication_ready']
    start = checked(r['actual_waiter_start'])
    assert start['analysis_source_commit'] == r['analysis_source_commit']
    assert start['new_inference_allowed'] is False and start['retry_failed_stages'] is False


def test_current_summary_document_links_exist():
    docs = ('research/components/native-catalog-summary-v1.md', 'research/INDEX.md', 'research/STATUS.md',
        'research/logbook/2026-11-12-catalog-actuation.md')
    assert check(ROOT, documents=docs, manifest=None)['status'] == 'passed'
