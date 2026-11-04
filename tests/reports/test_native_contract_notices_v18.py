"""Synthetic offline archive checks, not model inference or native execution."""
from copy import deepcopy

import pytest

from scripts import analyze_native_contract_notices_v18 as offline
from tests.optimization.test_native_contract_notices_v18 import document
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def archive(tmp_path, *, role='system', transport=True):
    root = tmp_path / 'raw'
    system = root / 'queue/search-SCRIPTED/worlds/cell/system.json'
    step = root / 'queue/search-SCRIPTED/authoring/generation-SCRIPTED/step-00.completed.json'
    write_json_atomic(system, document(), sort_keys=True, allow_nan=False)
    content = ('TRUSTED INSTITUTION-AUTHORING PROTOCOL\nSCRIPTED\n'
        'TRUSTED EXECUTION ABI AND DISTRIBUTION CONTRACT\nSCRIPTED\n'
        'Minimize the exact_loss_spec supplied in the session data.')
    value = {'model_reply': {'transport': {'request_payload': {'messages': [{'role': role, 'content': content}]}}
        if transport else {}}}
    write_json_atomic(step, value, sort_keys=True, allow_nan=False)
    index = {'source_commit': 'SCRIPTED-origin', 'audit': {'raw_input_sha256s': offline._inventory(root)},
        'designer_costs': {'recorded_POST_attempts': 1}, 'physical_world_directory_count': 1}
    index['content_sha256'] = digest(index)
    path = tmp_path / 'source-matched-audit.json'
    write_json_atomic(path, index, sort_keys=True, allow_nan=False)
    return root, path, system


def test_offline_notice_and_role_report_is_reproducible_without_source_execution(tmp_path):
    root, index, _ = archive(tmp_path)
    before = offline._inventory(root)
    first = offline.analyze(root, index, source_commit='SCRIPTED-analysis')
    assert offline.analyze(root, index, source_commit='SCRIPTED-analysis') == first
    assert offline._inventory(root) == before
    assert first['all_archived_POSTs_have_trusted_authority_in_SYSTEM']
    assert len(first['systems'][0]['notices']) == 1
    assert first['new_model_POSTs'] == first['new_native_worlds'] == first['source_executions'] == 0
    assert not first['candidate_or_loss_changed'] and not first['warnings_are_vetoes']
    assert not first['operational_goal_achieved']
    assert first['original_actual_source_commit'] == 'SCRIPTED-origin'
    assert first['analysis_source_commit'] == 'SCRIPTED-analysis'


def test_system_looking_text_in_a_user_role_is_not_promoted_to_authority(tmp_path):
    root, index, _ = archive(tmp_path, role='user')
    assert not offline.analyze(root, index, source_commit='SCRIPTED-analysis')[
        'all_archived_POSTs_have_trusted_authority_in_SYSTEM']


def test_missing_post_payload_is_not_a_complete_authority_audit(tmp_path):
    root, index, _ = archive(tmp_path, transport=False)
    with pytest.raises(ValueError, match='all archived designer POSTs'):
        offline.analyze(root, index, source_commit='SCRIPTED-analysis')


def test_changed_raw_document_is_rejected_before_analysis(tmp_path):
    root, index, system = archive(tmp_path)
    write_json_atomic(system, {}, sort_keys=True, allow_nan=False)
    with pytest.raises(ValueError, match='raw inventory differs'):
        offline.analyze(root, index, source_commit='SCRIPTED-analysis')


def test_detects_a_concurrent_writer_during_read_only_analysis(tmp_path, monkeypatch):
    root, index, system = archive(tmp_path)
    notices = offline.contract_notices
    def changed(value):
        write_json_atomic(system, deepcopy(value) | {'concurrent_change': True}, sort_keys=True, allow_nan=False)
        return notices(value)
    monkeypatch.setattr(offline, 'contract_notices', changed)
    with pytest.raises(ValueError, match='changed during read-only'):
        offline.analyze(root, index, source_commit='SCRIPTED-analysis')
