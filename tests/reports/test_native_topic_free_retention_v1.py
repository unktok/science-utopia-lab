"""Retain actual SOFTWARE public execution without real-design claims."""
import hashlib
import json
from pathlib import Path
import subprocess
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]


def test_full_public_software_source_and_all_failures_remain_bound():
    r=checked(json.loads((ROOT/'research/results/native-topic-free-public-software-retention-v1.json').read_text()))
    for name,sha in r['retained_files'].items(): assert file_sha256(ROOT/name)==sha
    for name,sha in r['source_sha256s'].items():
        raw=subprocess.check_output(['git','show',r['source_commit']+':'+name],cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest()==sha
    assert r['original_session']==75531 and r['exit_code']==0 and r['all_eight_new_worlds_complete']
    assert r['two_original_cold_audits_identical'] and r['two_original_costs_identical']
    v=r['verification']
    assert v['native_worlds']==8 and v['upstream_software_worlds']==2 and v['own_slots']==6
    assert v['scripted_calibration_POSTs']==199 and v['scripted_proposal_POSTs']==42
    assert v['actual_fixed_scientist_institutional_work_requests']==24
    assert v['scientist_installed_sdk_requests_including_upstream']==1602
    assert v['every_actual_next_feedback_prompt_contains_error']
    assert len(r['preserved_failures'])==5 and all(f['exit_code']==1 for f in r['preserved_failures'])
    assert any('six own software worlds are technical nulls' in f['cause'] for f in r['preserved_failures'])
    assert not r['new_real_model_calls'] and not r['deadline_supervision_tested']
    assert not r['actual_model_capacity_demonstrated'] and not r['automatic_invention_or_improvement_claimed']
    assert not r['publication_ready']
