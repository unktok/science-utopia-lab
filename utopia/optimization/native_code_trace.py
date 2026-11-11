"""Opt-in exact native code inputs for source design; never host execution.

Raw contexts stay local. Each complete container execution is bound to the
source, graph, run, artifact and actual inputs/outputs independently of labels.
Prospective attempt journals also preserve exact inputs before delegation;
historical successful-only journals are never retroactively completed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import uuid

from utopia.system.code_mechanisms import sha, validate_code_artifact, validate_code_result, validate_context
from utopia.system.design_patch import clone


class RecordingCodeExecutor:
    def __init__(self, executor, path, *, binding):
        self.executor, self.path = executor, Path(path)
        self.image_id, self.binding = executor.image_id, clone(binding)
        if not self.binding or set(self.binding) != {'source_commit', 'system_fingerprint', 'run_id'}:
            raise ValueError('exact source/system/run recording binding required')
        self.lock = threading.Lock()
        self.attempts_path = self.path.with_name(self.path.name + '.attempts.jsonl')

    def _append(self, path, row):
        # The intent reaches disk before delegated container execution. An I/O
        # error stops dispatch rather than running an unrecorded component.
        with self.lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a') as stream:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())

    def _attempt(self, value):
        row = {'schema': 'scienceutopia.native-code-attempt.v1', **value}
        row['content_sha256'] = sha(row)
        self._append(self.attempts_path, row)
        return row

    def execute(self, artifact, context):
        intent = self._attempt({'kind': 'intent', 'binding': clone(self.binding),
            'nonce': uuid.uuid4().hex, 'artifact': clone(artifact), 'context': clone(context)})
        try:
            execution = self.executor.execute(artifact, context)
            row = {'schema': 'scienceutopia.native-code-input.v1', 'binding': clone(self.binding),
                   'artifact': clone(intent['artifact']), 'context': clone(intent['context']),
                   'result': clone(execution.result), 'receipt': clone(execution.receipt)}
            row['bundle_sha256'] = sha(row)
            validate_record(row)
            self._append(self.path, row)
        except BaseException as error:
            # "raised" describes the executor API, not a claim that a remote
            # timed-out container completed or was cancelled successfully.
            self._attempt({'kind': 'raised', 'intent_sha256': intent['content_sha256'],
                'error_type': type(error).__name__, 'error': str(error),
                'remote_completion_inferred': False})
            raise
        self._attempt({'kind': 'returned', 'intent_sha256': intent['content_sha256'],
            'bundle_sha256': row['bundle_sha256']})
        return execution


def recorded_attempts(path, *, binding):
    """Cold-check inputs including raised/pending calls; never fill a terminal.

    Successful legacy bundles remain unchanged and are joined bijectively to
    returned events. Failed/pending inputs are literal data, not valid contracts
    or proof of execution/cancellation. Historical logs lacking this journal
    cannot be reconstructed by this function.
    """
    path = Path(path); journal = path.with_name(path.name + '.attempts.jsonl')
    intents, terminals = {}, {}
    for line in journal.read_text().splitlines():
        r = json.loads(line)
        if (r.get('schema') != 'scienceutopia.native-code-attempt.v1'
                or r.get('content_sha256') != sha({k:v for k,v in r.items() if k != 'content_sha256'})):
            raise ValueError('native code-attempt journal hash/schema mismatch')
        if r.get('kind') == 'intent':
            if (set(r) != {'schema','kind','binding','nonce','artifact','context','content_sha256'}
                    or r['binding'] != binding or not isinstance(r['nonce'], str) or not r['nonce']
                    or r['content_sha256'] in intents):
                raise ValueError('native code-attempt intent/binding differs')
            intents[r['content_sha256']] = r
        elif r.get('kind') in ('returned','raised'):
            identity = r.get('intent_sha256')
            keys = ({'bundle_sha256'} if r['kind'] == 'returned' else
                    {'error_type','error','remote_completion_inferred'})
            if (set(r) != {'schema','kind','intent_sha256','content_sha256',*keys}
                    or identity not in intents or identity in terminals
                    or (r['kind'] == 'raised' and (r['remote_completion_inferred'] is not False
                        or not isinstance(r['error_type'], str) or not isinstance(r['error'], str)))):
                raise ValueError('native code-attempt terminal/origin differs')
            terminals[identity] = r
        else:
            raise ValueError('unknown native code-attempt event')
    bundles = [validate_record(json.loads(line)) for line in path.read_text().splitlines()] if path.exists() else []
    remaining = list(bundles); result = []
    for identity, intent in intents.items():
        terminal = terminals.get(identity)
        if terminal is not None and terminal['kind'] == 'returned':
            index = next((i for i,b in enumerate(remaining) if b['bundle_sha256'] == terminal['bundle_sha256']
                and b['binding'] == binding and b['artifact'] == intent['artifact'] and b['context'] == intent['context']), None)
            if index is None: raise ValueError('returned code attempt has no exact legacy execution bundle')
            remaining.pop(index)
        result.append({'intent': intent, 'terminal': terminal,
            'status': 'pending' if terminal is None else terminal['kind']})
    if remaining: raise ValueError('legacy execution bundle has no returned code attempt')
    return result


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
