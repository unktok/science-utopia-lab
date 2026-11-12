"""Retained software/source evidence, not a scientific outcome assertion."""
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def test_exact_sources_failed_checks_and_final_native_successes_stay_distinct():
    receipt = checked(json.loads((ROOT / 'research/results/native-catalog-actuation-preparation-v1.json').read_text()))
    source = receipt['scientific_source_commit']
    assert len(source) == 40
    for name in ('scripts/run_native_catalog_actuation_v1.py', 'scripts/audit_native_catalog_actuation_v1.py',
            'utopia/system/native_catalog_planning.py', 'research/protocols/campaigns/native-catalog-actuation-v1.md'):
        original = subprocess.check_output(['git', 'show', source + ':' + name], cwd=ROOT)
        assert original == (ROOT / name).read_bytes()
    reader = subprocess.check_output(['git', 'rev-parse', receipt['reader_source_commit']], cwd=ROOT, text=True).strip()
    assert reader == 'c75d6c481408a3e8b7577ec24cecbace96106f9b'
    rows = {Path(r['path']).stem: r for r in receipt['qa']}
    assert rows['native-catalog-planning-unit-qa-a1']['failures'] == 1
    assert rows['native-catalog-unit-regression-qa-a1']['failures'] == 3
    assert rows['native-catalog-native-integration-qa-a1']['failures'] == 1
    assert rows['native-catalog-production-integration-qa-a1']['tests'] == 0
    for label, count in [('native-catalog-production-integration-qa-a2', 80),
            ('native-catalog-readout-integration-qa-a1', 35)]:
        assert rows[label]['tests'] == count and not rows[label]['failures'] and not rows[label]['errors']
    assert not receipt['SCRIPTED_native_worlds_are_actual_model_results']
    assert not receipt['automatic_invention_demonstrated'] and not receipt['publication_ready']
    assert file_sha256(ROOT / 'research/data/native-information-capability-discovery-v1/catalog.json') == receipt[
        'historical_catalog_file_sha256']


def test_catalog_protocol_component_logbook_and_active_navigation_links_exist():
    docs = ['research/INDEX.md', 'research/STATUS.md', 'research/publication/publication-ready-v3.md',
        'research/protocols/campaigns/native-catalog-actuation-v1.md',
        'research/components/native-catalog-actuation-v1.md', 'research/logbook/2026-11-12-catalog-actuation.md']
    assert check(ROOT, documents=docs, manifest=None)['status'] == 'passed'
