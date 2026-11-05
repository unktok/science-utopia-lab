"""Synthetic archive diagnostics only, not a new designer/native experiment."""
import hashlib
import json

import pytest

from scripts import analyze_native_design_stagnation_v20 as diagnostic
from tests.optimization.test_native_authoring_ir import ALPHA, request
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def archive(tmp_path, *, system_role='system', narration=diagnostic.FORBIDDEN, corrupt_wire=False):
    raw = tmp_path / 'raw'
    generation = raw / 'queue/search-SCRIPTED/authoring/generation-SCRIPTED'
    parent = request()['parent_system']
    operation = {'op': 'replace', 'selector': {'mechanism_id': ALPHA},
        'path': '/parameters/code_artifact/source', 'value': parent['mechanisms'][0]['parameters']['code_artifact']['source']}
    action = {'tool': 'edit', 'operations': [operation], 'rationale': 'SCRIPTED illegal envelope'}
    payload = {'messages': [{'role': system_role, 'content': diagnostic.PERMITTED},
        {'role': 'user', 'content': narration}]}
    wire = json.dumps(payload, ensure_ascii=False)
    transport = {'request_wire_utf8': wire, 'request_wire_sha256': 'bad' if corrupt_wire else hashlib.sha256(wire.encode()).hexdigest(),
        'request_payload': payload}
    step = {'model_reply': {'output': action, 'transport': transport}, 'transition': {
        'ok': False, 'document_before_sha256': digest(parent),
        'errors': [{'message': 'unexpected fields for edit: rationale'}]}}
    write_json_atomic(generation / 'request.json', {'request': {'parent_system': parent}}, sort_keys=True)
    write_json_atomic(generation / 'step-00.completed.json', step, sort_keys=True)
    audit = {'source_commit': 'SCRIPTED-original', 'audit': {'raw_input_sha256s': diagnostic._inventory(raw)},
        'designer_costs': {'recorded_POST_attempts': 1}}
    audit['content_sha256'] = digest(audit)
    audit_path = tmp_path / 'audit.json'
    write_json_atomic(audit_path, audit, sort_keys=True)
    return raw, audit_path


def test_reproducible_wire_contradiction_and_noop_operand_diagnosis(tmp_path):
    raw, audit = archive(tmp_path)
    before = diagnostic._inventory(raw)
    result = diagnostic.analyze(raw, audit, source_commit='SCRIPTED-analysis')
    assert diagnostic.analyze(raw, audit, source_commit='SCRIPTED-analysis') == result
    assert diagnostic._inventory(raw) == before
    assert result['all_POSTs_contain_conflicting_invention_instructions']
    assert result['all_edit_operands_equal_parent']
    assert not result['attempted_edit_operands'][0]['actually_applied']
    assert result['tool_error_counts'] == {'unexpected fields for edit: rationale': 1}
    assert result['new_model_POSTs'] == result['new_native_worlds'] == result['source_executions'] == 0
    assert not result['causal_sufficiency_established']


@pytest.mark.parametrize('kwargs', [{'system_role': 'user'}, {'narration': 'No conflicting directive here'}])
def test_role_or_narration_text_alone_does_not_prove_conflicting_authority(tmp_path, kwargs):
    raw, audit = archive(tmp_path, **kwargs)
    assert not diagnostic.analyze(raw, audit, source_commit='SCRIPTED-analysis')[
        'all_POSTs_contain_conflicting_invention_instructions']


def test_wire_hash_is_checked_not_just_the_inventory(tmp_path):
    raw, audit = archive(tmp_path, corrupt_wire=True)
    with pytest.raises(ValueError, match='wire bytes/hash'):
        diagnostic.analyze(raw, audit, source_commit='SCRIPTED-analysis')


def test_changed_raw_evidence_is_rejected(tmp_path):
    raw, audit = archive(tmp_path)
    write_json_atomic(raw / 'extra.json', {'changed': True})
    with pytest.raises(ValueError, match='raw inventory changed'):
        diagnostic.analyze(raw, audit, source_commit='SCRIPTED-analysis')
