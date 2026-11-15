"""Bind actual completed public-path software evidence, not model feasibility."""
import json
from pathlib import Path
import subprocess
import hashlib
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def test_actual_public_path_and_original_source_are_retained():
    r = checked(json.loads((ROOT/'research/results/native-legacy-topic-pilot-software-retention-v1.json').read_text()))
    for name, sha in r['retained_files'].items():
        assert file_sha256(ROOT/name) == sha
    for name, sha in r['source_sha256s'].items():
        raw = subprocess.check_output(['git', 'show', r['source_commit']+':'+name], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == sha
    v = r['verification']
    assert r['original_session'] == 1756 and r['exit_code'] == 0
    assert v['worlds'] == 2 and v['annual_boundaries'] == 8
    assert v['scientist_httpx_requests'] == 300 and v['outside_core_project_effects'] == [0, 16]
    assert v['all_scientist_read_headers'] == ['900'] and v['all_scientist_retry_headers'] == ['0']
    assert not v['scientific_request_body_timeout_fields'] and r['same_initial_society']
    assert v['paired_audit_content_sha256'] == r['audit_content_sha256']
    assert v['paired_cost_content_sha256'] == r['cost_content_sha256']
    assert r['regression_exit_code'] == 0 and r['regression_tests'] == 59
    assert not r['new_real_model_calls'] and not r['scientific_feasibility_claimed']
    assert not r['automatic_invention_claimed'] and not r['publication_ready']
