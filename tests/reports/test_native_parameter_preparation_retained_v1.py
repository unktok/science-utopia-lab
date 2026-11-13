"""Literal prior numeric consumer QA, not scientific optimization evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_numeric_preparation_retains_committed_source_and_actual_isolated_execution_scope():
    receipt = checked(json.loads((ROOT / 'research/results/native-parameter-space-preparation-verification-v1.json').read_text()))
    assert receipt['source_commit'] == '9031064a0ded9f06d7f00bef0fa3260a75db35a8'
    for name, expected in receipt['source_files'].items():
        raw = subprocess.check_output(['git', 'show', receipt['source_commit'] + ':' + name], cwd=ROOT)
        assert hashlib.sha256(raw).hexdigest() == expected
    qa = receipt['isolated_consumer_qa']
    assert qa['tests'] == 7 and qa['actual_sandbox_executions'] == 4 and qa['observed_exit_code'] == 0
    assert qa['no_model_calls'] and qa['synthetic_input_frame_not_a_scientific_world']
    assert qa['observed_numeric_commands'] == {'20': {'amount': 2, 'to_actor': 'soon'}, '21': {'amount': 1, 'to_actor': 'near'}}
    assert not any(receipt[k] for k in ('fixture_bounds_are_scientific_study_bounds',
        'full_native_numeric_campaign_implemented', 'new_numeric_study_dispatched',
        'scientific_gain_demonstrated', 'publication_ready', 'new_scientific_worlds', 'new_model_calls'))
