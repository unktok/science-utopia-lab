import copy
import json
from types import SimpleNamespace

import pytest

from utopia.optimization.native_code_trace import RecordingCodeExecutor, recorded_contexts, validate_record
from utopia.system.code_mechanisms import CODE_SCHEMA, CodeExecution, sha


def case(tmp_path):
    artifact = {'schema': CODE_SCHEMA, 'label': 'QA-only recorder fixture',
        'source': "def step(context):\n return {'outputs':{'custom':[]},'state':{}}",
        'inputs': {'arbitrary': {'type': 'object'}}, 'outputs': {'custom': {'type': 'object'}}, 'state_schema': {'type': 'object'}}
    context = {'period': 2, 'phase': 140, 'random_seed': 42, 'parameters': {}, 'state': {},
        'inputs': {'arbitrary': [{'payload': {'actual': 1}}]}}
    result = {'outputs': {'custom': []}, 'state': {}}
    def execute(a, c):
        return CodeExecution(result, {'image_id': 'qa-image', 'artifact_sha256': sha(a), 'context_sha256': sha(c), 'result_sha256': sha(result)})
    binding = {'source_commit': 'qa-source', 'system_fingerprint': 'qa-system', 'run_id': 'qa-run'}
    recorder = RecordingCodeExecutor(SimpleNamespace(image_id='qa-image', execute=execute), tmp_path / 'contexts.jsonl', binding=binding)
    return recorder, artifact, context, binding


def test_exact_arbitrary_ports_are_recorded_without_message_contract(tmp_path):
    recorder, artifact, context, binding = case(tmp_path)
    recorder.execute(artifact, context)
    rows = recorded_contexts(recorder.path, artifact=artifact, binding=binding)
    assert rows[0]['context'] == context and rows[0]['artifact'] == artifact
    assert rows[0]['result']['outputs']['custom'] == []
    assert recorder.image_id == 'qa-image'


def test_receipt_and_binding_drift_rejected_even_with_rehashed_bundle(tmp_path):
    recorder, artifact, context, binding = case(tmp_path)
    recorder.execute(artifact, context)
    row = json.loads(recorder.path.read_text())
    row['context']['period'] += 1
    row['bundle_sha256'] = sha({k: v for k, v in row.items() if k != 'bundle_sha256'})
    with pytest.raises(ValueError, match='receipt mismatch'):
        validate_record(row)
    with pytest.raises(ValueError, match='binding mismatch'):
        recorded_contexts(recorder.path, artifact=artifact, binding={**binding, 'run_id': 'other'})
