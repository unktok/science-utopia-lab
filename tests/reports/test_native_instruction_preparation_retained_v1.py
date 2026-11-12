"""Retained preparation evidence is not an instruction effectiveness result."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]


def read(name):return checked(json.loads((ROOT/name).read_text()))


def test_prospective_core_bindings_are_exact_original_frozen_blobs():
    p=read('research/results/native-instruction-timing-preparation-verification-v1.json')
    assert p['source_commit']=='5925d5b7d77bf7f13406730420022986e3fdac1f'
    for name,expected in p['tested_core_files'].items():
        original=subprocess.check_output(['git','show',p['source_commit']+':'+name],cwd=ROOT)
        assert hashlib.sha256(original).hexdigest()==expected
    assert p['test_runs'][0]['exit_code']==4 and p['test_runs'][0]['test_cases']==0
    assert [(r['test_cases'],r['skips']) for r in p['test_runs'][-2:]]==[(62,0),(40,0)]
    assert all(r['source_commit']==p['source_commit'] for r in p['test_runs'][-2:])
    assert p['overlapping_test_scopes_are_not_summed_as_trials']


def test_actual_old_record_compatibility_is_not_a_new_advice_assay():
    v=read('research/results/native-instruction-timing-preparation-verification-v1.json')
    p=read(v['actual_original_record_parser_check']['path'])
    assert file_sha256(ROOT/v['actual_original_record_parser_check']['path'])==v['actual_original_record_parser_check']['file_sha256']
    a=read('research/results/native-objective-instrument-loop-closed-verification-v1.json')
    assert p['original_audit_content_sha256']==a['audit_content_sha256']
    assert p['original_audit_file_sha256']==a['audit_file_sha256']
    assert p['direction_requests']==p['literal_frames']==p['literal_direction_replies']==p['uniquely_memory_matched']==10
    assert p['displayed_candidates']==30 and p['catalog_mismatches']==0
    assert p['wire_requests']==p['committed_responses']==129
    assert p['catalog_bytes_match_original_source']
    assert not p['new_model_calls'] and not p['new_code_executions']
    assert not p['instruction_assay_run'] and not p['effectiveness_claimed']


def test_checkpoint_retains_actual_waiting_state_and_finite_no_designer_budget():
    p=read('research/results/native-instruction-timing-preparation-verification-v1.json')
    assert p['continuation']['stage_at_checkpoint']=='await-original-fixed-evaluation-audits'
    assert not p['continuation']['new_scientific_plan_created']
    assert not p['continuation']['new_control_world_dispatched']
    assert p['budget']['native_worlds']==3 and p['budget']['designer_POSTs']==0
    assert not p['scope']['actual_advice_effectiveness_demonstrated']
    assert not p['scope']['optimizer_comparison'] and not p['scope']['publication_ready']
