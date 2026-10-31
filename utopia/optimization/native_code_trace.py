"""Opt-in exact native code inputs for source design; never host execution.

Raw contexts stay local. Each complete container execution is bound to the
source, graph, run, artifact and actual inputs/outputs independently of labels.
"""
from __future__ import annotations

import json
from pathlib import Path
import threading

from utopia.system.code_mechanisms import sha, validate_code_artifact, validate_code_result, validate_context
from utopia.system.design_patch import clone


class RecordingCodeExecutor:
    def __init__(self, executor, path, *, binding):
        self.executor, self.path = executor, Path(path)
        self.image_id, self.binding = executor.image_id, clone(binding)
        if not self.binding or set(self.binding) != {'source_commit', 'system_fingerprint', 'run_id'}:
            raise ValueError('exact source/system/run recording binding required')
        self.lock = threading.Lock()

    def execute(self, artifact, context):
        execution = self.executor.execute(artifact, context)
        row = {'schema': 'scienceutopia.native-code-input.v1', 'binding': self.binding,
               'artifact': clone(artifact), 'context': clone(context),
               'result': clone(execution.result), 'receipt': clone(execution.receipt)}
        row['bundle_sha256'] = sha(row)
        validate_record(row)
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a') as stream:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
        return execution


def validate_record(row):
    if not isinstance(row, dict) or set(row) != {'schema', 'binding', 'artifact', 'context', 'result', 'receipt', 'bundle_sha256'}:
        raise ValueError('invalid native code-input record')
    if row['schema'] != 'scienceutopia.native-code-input.v1' or sha({k: v for k, v in row.items() if k != 'bundle_sha256'}) != row['bundle_sha256']:
        raise ValueError('native code-input bundle hash mismatch')
    validate_code_artifact(row['artifact'])
    validate_context(row['artifact'], row['context'])
    validate_code_result(row['artifact'], row['result'])
    if any(row['receipt'].get(key + '_sha256') != sha(row[key]) for key in ('artifact', 'context', 'result')):
        raise ValueError('native code-input container receipt mismatch')
    return row


def recorded_contexts(path, *, artifact, binding):
    """Verify ALL records, then select exact artifact and declared execution."""
    values = []
    for line in Path(path).read_text().splitlines():
        row = validate_record(json.loads(line))
        if row['binding'] != binding:
            raise ValueError('native code-input source/system/run binding mismatch')
        if row['artifact'] == artifact:
            values.append(row)
    if not values:
        raise ValueError('no exact actual execution context for requested artifact')
    return values


def parent_context_provider(run_directory, *, source_commit):
    """Bind raw recorded calls to the actual parent checkpoint's node receipts."""
    from utopia.optimization.native_feedback import checked_native_state
    def provide(node_id, parent, history):
        node = next(n for n in parent.mechanisms if n.mechanism_id == node_id)
        actual = []
        for record in history:
            if record['observation']['status'] != 'complete' or record['observation']['metadata']['system_fingerprint'] != parent.fingerprint:
                continue
            for run in record['observation']['metadata']['runs']:
                _, kernel = checked_native_state(record, run)
                rows = recorded_contexts(Path(run_directory) / run['run_id'] / 'code-contexts.jsonl',
                    artifact=node.parameters['code_artifact'], binding={'source_commit': source_commit,
                        'system_fingerprint': parent.fingerprint, 'run_id': run['run_id']})
                for row in rows:
                    if not any(e.event_type == 'generated.code_executed' and e.provenance['mechanism_id'] == node_id
                        and e.year == row['context']['period'] and all(
                            e.payload[k] == row['receipt'][k] for k in ('image_id', 'artifact_sha256', 'context_sha256', 'result_sha256'))
                        for e in kernel.events):
                        raise ValueError('recorded input has no matching actual parent node execution')
                actual.extend(rows)
        if not actual:
            raise ValueError('no completed parent native run with exact recorded node inputs')
        return actual
    return provide
