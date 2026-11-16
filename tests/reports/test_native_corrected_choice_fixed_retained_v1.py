"""Literal light-test retention, not real native/certificate/outcome evidence."""
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]


def test_exact_original_light_junits_and_limits_are_retained():
    record = json.loads((ROOT / 'research/results/native-corrected-choice-fixed-preparation-v1.json').read_text())
    assert record['logical_rows'] == 30 and record['seedwise_contrast_rows'] == 120
    assert record['check_invocations_overlap']
    for row in record['checks']:
        raw = (ROOT / row['file']).read_bytes(); assert hashlib.sha256(raw).hexdigest() == row['file_sha256']
        suites = ElementTree.fromstring(raw).findall('testsuite')
        assert len(suites) == 1
        assert int(suites[0].get('tests')) == row['passed']
        assert all(int(suites[0].get(key)) == 0 for key in ('failures', 'errors', 'skipped'))
    assert all(record[key] is False for key in ('unused_seed_attestation_completed',
        'new_scientific_loss_measured', 'existing_development_source_modified', 'public_native_QA_executed',
        'fixed_evaluation_prepared_plan_exists', 'scientific_evaluation_dispatched', 'publication_ready'))
