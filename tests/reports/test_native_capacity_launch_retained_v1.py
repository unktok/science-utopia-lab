import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[2]


def test_frozen_launch_is_actual_readiness_not_a_completed_or_winning_study():
    r=checked(json.loads((ROOT/'research/results/native-capacity-objective-launch-verification-v1.json').read_text()))
    assert r['scientific_source_commit']=='16cfdcef2151e01365c1fc2bea3f5cc928954220'
    assert r['started']['plan_sha256']==r['plan_content_sha256']
    assert r['started']['pid']==84531 and r['scientific_session']==10035
    assert r['source_bound_final_tests']['passed']==128 and r['source_bound_final_tests']['final_exit_code_observed']==0
    assert r['native_worlds_upper_bound']==9 and r['scientific_world_completed_at_receipt']==0
    assert not r['actual_designer_readiness_claimed_passed'] and not r['publication_ready']
    assert not r['repeat_failed_slots'] and not r['preceding_studies']['losses_reused_as_development_observations']
    for path in ('scripts/run_native_capacity_objective_loop_v1.py','scripts/audit_native_capacity_objective_loop_v1.py',
                 'utopia/optimization/native_active_founders.py','research/protocols/campaigns/native-capacity-objective-loop-v1.md'):
        assert subprocess.check_output(['git','show',r['scientific_source_commit']+':'+path],cwd=ROOT)==(ROOT/path).read_bytes()
