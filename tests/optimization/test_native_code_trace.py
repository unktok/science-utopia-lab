import copy
import json
from types import SimpleNamespace

import pytest

from utopia.optimization.native_code_trace import RecordingCodeExecutor, recorded_contexts, validate_record, recorded_attempts
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


def test_attempt_input_is_on_disk_before_delegate_and_legacy_success_is_unchanged(tmp_path):
    recorder, artifact, context, binding = case(tmp_path)
    delegate = recorder.executor.execute
    def execute(a,c):
        rows = recorded_attempts(recorder.path,binding=binding)
        assert len(rows)==1 and rows[0]['status']=='pending'
        assert rows[0]['intent']['artifact']==a and rows[0]['intent']['context']==c
        return delegate(a,c)
    recorder.executor.execute=execute
    recorder.execute(artifact,context)
    rows=recorded_attempts(recorder.path,binding=binding)
    assert rows[0]['status']=='returned'
    legacy=recorded_contexts(recorder.path,artifact=artifact,binding=binding)
    assert rows[0]['terminal']['bundle_sha256']==legacy[0]['bundle_sha256']


@pytest.mark.parametrize('exception',[TypeError("'float' object is not subscriptable"),KeyboardInterrupt('SCRIPTED')])
def test_failed_or_interrupted_executor_keeps_exact_input_without_inventing_completion(tmp_path,exception):
    recorder,artifact,context,binding=case(tmp_path)
    def execute(a,c):raise exception
    recorder.executor.execute=execute
    with pytest.raises(type(exception)):recorder.execute(artifact,context)
    assert not recorder.path.exists()
    rows=recorded_attempts(recorder.path,binding=binding)
    assert rows[0]['status']=='raised' and rows[0]['intent']['context']==context
    assert rows[0]['terminal']['error']==str(exception)
    assert rows[0]['terminal']['remote_completion_inferred'] is False


def test_recording_io_failure_stops_before_delegate(tmp_path,monkeypatch):
    recorder,artifact,context,_=case(tmp_path)
    def failed_fsync(*args):raise OSError('SCRIPTED disk error')
    monkeypatch.setattr('os.fsync',failed_fsync)
    recorder.executor.execute=lambda *a:pytest.fail('no unrecorded execution')
    with pytest.raises(OSError,match='disk error'):recorder.execute(artifact,context)


def test_duplicate_equal_calls_have_distinct_intents_without_global_random_changes(tmp_path):
    import random
    recorder,artifact,context,binding=case(tmp_path)
    random.seed(888);before=random.getstate()
    recorder.execute(artifact,context);recorder.execute(artifact,context)
    assert random.getstate()==before
    rows=recorded_attempts(recorder.path,binding=binding)
    assert len(rows)==2 and len({r['intent']['content_sha256'] for r in rows})==2
    assert all(r['status']=='returned' for r in rows)


def test_missing_terminal_is_not_reconstructed_from_successful_legacy_bundle(tmp_path):
    recorder,artifact,context,binding=case(tmp_path)
    recorder.execute(artifact,context)
    lines=recorder.attempts_path.read_text().splitlines()
    recorder.attempts_path.write_text(lines[0]+'\n')
    with pytest.raises(ValueError,match='no returned code attempt'):recorded_attempts(recorder.path,binding=binding)


def test_terminal_hash_and_binding_must_match_literal_input_journal(tmp_path):
    recorder,artifact,context,binding=case(tmp_path)
    recorder.execute(artifact,context)
    with pytest.raises(ValueError,match='binding'):recorded_attempts(recorder.path,binding={**binding,'run_id':'other'})
    rows=[json.loads(line) for line in recorder.attempts_path.read_text().splitlines()]
    rows[1]['intent_sha256']='x'
    rows[1]['content_sha256']=sha({k:v for k,v in rows[1].items() if k!='content_sha256'})
    recorder.attempts_path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError,match='terminal/origin'):recorded_attempts(recorder.path,binding=binding)


def test_physical_projection_does_not_make_up_historical_attempt_counts(tmp_path):
    from scripts.native_benchmark_physical import code_attempt_proof
    recorder,artifact,context,binding=case(tmp_path)
    spec=SimpleNamespace(fingerprint=binding['system_fingerprint'])
    assert code_attempt_proof(tmp_path,spec,binding) is None
    recorder.path=tmp_path/'code-contexts.jsonl'
    recorder.attempts_path=recorder.path.with_name(recorder.path.name+'.attempts.jsonl')
    recorder.binding['run_id']=tmp_path.name
    recorder.execute(artifact,context)
    proof=code_attempt_proof(tmp_path,spec,binding)
    assert proof['counts']=={'returned':1,'raised':0,'pending':0}
    assert not proof['unreturned_intents']
