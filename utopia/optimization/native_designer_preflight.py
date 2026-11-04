"""Fail-closed, source/backend-bound interface calibration; NOT research merit.

No generated source is executed, no scientific world is dispatched, and no
failed/unknown call is retried. Certificates are operator-owned local evidence,
not cryptographic remote attestation and never accepted from browser requests.
"""
import hashlib
import json
from pathlib import Path
import time

from jsonschema import Draft202012Validator

from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic

SCHEMA = 'scienceutopia.designer-interface-certificate.v16'
TTL_SECONDS = 86400
VALUES = [17, -2.75, True, None, ['x', 3, False], {'nested': {'items': [None, 1]}},
    '研究者\n"quoted" \\ source: def step(context):\n    return {}\n', 9007199254740993]


def runtime_binding():
    # Include compiler, graph/ABI validators, discovery, JSON interpreter and
    # transport, not just the sender. Tests/docs don't invalidate a certificate.
    root = Path(__file__).resolve().parents[1]
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*.py'))}


def backend_binding(provider, session=None):
    if session is None:
        import requests
        session = requests.Session()
        session.trust_env = False
    def get(resource):
        response = session.get('http://127.0.0.1:11434/api/' + resource, timeout=10)
        response.raise_for_status()
        return response.json()
    version, tags = get('version'), get('tags')
    actual = next(item['digest'] for item in tags['models'] if item['name'] == provider['model'])
    if actual != provider['model_digest']:
        raise ValueError('preflight model digest differs from pinned provider')
    if not isinstance(version.get('version'), str) or not version['version']:
        raise ValueError('backend version missing')
    return {'model': provider['model'], 'model_digest': actual, 'ollama_version': version['version']}


def _schema(protocol):
    if protocol == 'staged-v15':
        from .native_staged_author_v15 import ACTION_SCHEMA
        return ACTION_SCHEMA
    if protocol == 'one-shot-v14':
        from .native_authoring_ir import OUTPUT_SCHEMA
        return OUTPUT_SCHEMA
    raise ValueError('unknown designer preflight protocol')


def _output(protocol, operation):
    if protocol == 'staged-v15':
        return {'tool': 'edit', 'operations': [operation]}
    return {'operations': [operation], 'factors': [], 'continuous': [],
        'rationale': 'Interface calibration only; not institutional invention'}


def cases(protocol):
    return [{'id': 'typed-' + str(index), 'expected': _output(protocol,
        {'op': 'add', 'path': '/metadata/interface_calibration', 'value': clone(value)})}
        for index, value in enumerate(VALUES)]


def _prompt(request, state, steps, provider, expected, protocol):
    from .native_staged_author_v15 import build_prompt, SYSTEM_PROMPT
    prompt = build_prompt(request, state, steps, image_id=provider['image_id'], binding_sha256=digest(request),
        settings={'max_steps': 16})
    system = SYSTEM_PROMPT + ('\n\nTRUSTED INTERFACE CALIBRATION TASK\n'
        'This call tests literal JSON editing, not autonomous invention or optimization. '
        'Return exactly the following action, with exact JSON types and values and no extra fields. '
        'This is a prospective compatibility control; nothing is executed or adopted.\n'
        + json.dumps(expected, ensure_ascii=False, allow_nan=False))
    if protocol == 'one-shot-v14':
        system += '\nUse the one-shot operations/factors/continuous/rationale envelope, not a tool envelope.'
    return prompt, system


def sequence(state):
    """Literal multi-turn code editing control, NOT an autonomous design success."""
    for index, node in enumerate(state['document'].get('mechanisms', [])):
        source = node.get('parameters', {}).get('code_artifact', {}).get('source')
        if isinstance(source, str):
            path = f'/mechanisms/{index}/parameters/code_artifact/source'
            return [{'id': 'sequence-inspect', 'expected': {'tool': 'inspect', 'path': path}},
                {'id': 'sequence-splice', 'expected': {'tool': 'splice', 'path': path,
                    'offset': len(source), 'delete': 0, 'text': '\n# interface calibration; no behavioral change\n'}},
                {'id': 'sequence-reinspect', 'expected': {'tool': 'inspect', 'path': path}},
                {'id': 'sequence-validate', 'expected': {'tool': 'validate'}},
                {'id': 'sequence-finish', 'expected': {'tool': 'finish',
                    'rationale': 'Interface calibration only; no behavioral improvement claimed'}}]
    raise ValueError('staged calibration requires a real code-bearing parent, not an empty toy document')


def planned_cases(request, protocol):
    from .native_staged_author_v15 import initial_draft
    return cases(protocol) + (sequence(initial_draft(request)) if protocol == 'staged-v15' else [])


def _apply(state, action, request, provider):
    from .native_staged_author_v15 import transition
    return transition(state, action, request, binding_sha256=digest(request), provider_binding=provider)


def run_calibration(directory, *, request, provider, protocol='staged-v15', source_commit='SCRIPTED-unpinned-test'):
    from .native_staged_author_v15 import initial_draft, LocalStagedQwenDesignerModel
    from .native_search_generator_v14 import LocalQwenDesignerModel
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    plan = {'schema': SCHEMA + '.plan', 'protocol': protocol, 'source_commit': source_commit, 'request': clone(request),
        'provider': clone(provider), 'runtime': runtime_binding(), 'backend': backend_binding(provider),
        'cases': planned_cases(request, protocol), 'max_POSTs': len(planned_cases(request, protocol)),
        'native_worlds': 0, 'source_executions': 0, 'network_retries': 0,
        'max_tokens': 2048, 'temperature': .2, 'created_epoch': time.time()}
    write_json_atomic(directory / 'plan.json', plan, sort_keys=True, allow_nan=False)
    model = (LocalStagedQwenDesignerModel if protocol == 'staged-v15' else LocalQwenDesignerModel)(provider,
        inference_lock=directory.parent / 'interface-calibration.lock')
    state, steps, records = initial_draft(request), [], []
    for case in plan['cases']:
        # Typed controls are independent. The five-step sequence is continuous.
        if case['id'].startswith('typed-') or case['id'] == 'sequence-inspect':
            state, steps = initial_draft(request), []
        prompt, system = _prompt(request, state, steps, provider, case['expected'], protocol)
        intent = {'id': case['id'], 'prompt': prompt, 'system_prompt': system,
            'seed_ctx': ['designer-contract-v16', protocol, case['id']], 'expected': case['expected']}
        write_json_atomic(directory / (case['id'] + '.started.json'), intent, sort_keys=True, allow_nan=False)
        record = {'intent': intent, 'ok': False}
        begin = time.monotonic()
        try:
            output, _ = model.generate(prompt=prompt, system_prompt=system, seed_ctx=intent['seed_ctx'],
                max_tokens=2048, temperature=.2, response_format={'json_object': {'schema': _schema(protocol)}})
            # Python bool==1 and large numeric rounding are NOT exact JSON equality.
            if digest(output) != digest(case['expected']):
                raise ValueError('literal output differs from exact typed control')
            Draft202012Validator(_schema(protocol)).validate(output)
            action = output if protocol == 'staged-v15' else {'tool': 'edit', 'operations': output['operations']}
            state, receipt = _apply(state, action, request, provider)
            if not receipt['ok']:
                raise ValueError('control rejected by actual interpreter: ' + str(receipt['errors']))
            if case['id'] in ('sequence-validate', 'sequence-finish') and not receipt['result']['valid']:
                raise ValueError('continuous code edit failed static compilation')
            record.update(ok=True, output=output, receipt=receipt)
            steps.append({'step': len(steps), 'status': 'applied', 'model_reply': {'output': output},
                'transition': receipt})
        except Exception as error:
            record['error'] = type(error).__name__ + ': ' + str(error)
        record.update(transport=clone(model.last_transport), elapsed_seconds=time.monotonic() - begin)
        records.append(record)
        write_json_atomic(directory / (case['id'] + '.completed.json'), record, sort_keys=True, allow_nan=False)
        print(json.dumps({'case': case['id'], 'ok': record['ok'], 'elapsed_seconds': record['elapsed_seconds'],
            'error': record.get('error')}), flush=True)
        if not record['ok']:
            break  # Failed/unknown replies are charged, never automatically replaced.
    certificate = {'schema': SCHEMA, 'plan': plan, 'records': records, 'completed_epoch': time.time(),
        'maximum_age_seconds': TTL_SECONDS, 'all_controls_passed': len(records) == len(plan['cases'])
            and all(record['ok'] for record in records)}
    certificate['content_sha256'] = digest(certificate)
    write_json_atomic(directory / 'certificate.json', certificate, sort_keys=True, allow_nan=False)
    return certificate


def require_certificate(path, provider, *, protocol, session=None, now=None):
    """Cold replay literal controls + live metadata; a pass flag alone is insufficient."""
    if path is None:
        raise ValueError('actual-backend designer preflight certificate required before production search')
    from .native_search_generator_v14 import _strict_json
    from .native_staged_author_v15 import initial_draft, build_conversation
    from .native_designer_wire import wire_record
    path = Path(path)
    if path.is_symlink():
        raise ValueError('operator certificate cannot be a symbolic link')
    certificate = _strict_json(path.read_text())
    if certificate.get('schema') != SCHEMA or certificate.get('content_sha256') != digest(
            {key: value for key, value in certificate.items() if key != 'content_sha256'}):
        raise ValueError('designer preflight certificate hash/schema differs')
    plan, records = certificate['plan'], certificate['records']
    age = (time.time() if now is None else now) - certificate['completed_epoch']
    if not 0 <= age <= TTL_SECONDS or certificate['maximum_age_seconds'] != TTL_SECONDS:
        raise ValueError('designer preflight is stale or future-dated; recalibrate explicitly')
    if (plan['protocol'] != protocol or plan['runtime'] != runtime_binding()
            or plan['backend'] != backend_binding(provider, session)):
        raise ValueError('designer preflight protocol/runtime/backend binding changed')
    expected_cases = planned_cases(plan['request'], protocol)
    if (plan['cases'] != expected_cases or len(records) != len(expected_cases)
            or not certificate['all_controls_passed'] or plan['max_POSTs'] != len(expected_cases)
            or plan['max_tokens'] != 2048 or plan['temperature'] != .2):
        raise ValueError('designer preflight controls incomplete or plan changed')
    if any(plan['provider'].get(key) != provider.get(key) for key in ('model', 'model_digest', 'image_id')):
        raise ValueError('designer preflight provider/image binding differs')
    state, steps = initial_draft(plan['request']), []
    for case, record in zip(expected_cases, records):
        if case['id'].startswith('typed-') or case['id'] == 'sequence-inspect':
            state, steps = initial_draft(plan['request']), []
        prompt, system = _prompt(plan['request'], state, steps, provider, case['expected'], protocol)
        intent = {'id': case['id'], 'prompt': prompt, 'system_prompt': system,
            'seed_ctx': ['designer-contract-v16', protocol, case['id']], 'expected': case['expected']}
        transport = record['transport']
        messages = (build_conversation(prompt, system) if protocol == 'staged-v15' else
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}])
        payload = {'model': provider['model'], 'messages': messages, 'format': 'json', 'think': False,
            'stream': False, 'options': {'temperature': .2, 'num_predict': 2048, 'num_ctx': 32768,
                'seed': int(digest(intent['seed_ctx'])[:8], 16) % (2**31)}}
        wire = wire_record(payload, _schema(protocol))
        if (record['intent'] != intent or record['ok'] is not True or transport['request_payload'] != payload
                or any(transport.get(key) != value for key, value in wire.items())
                or transport.get('model_digest') != provider['model_digest']
                or transport.get('endpoint') != 'http://127.0.0.1:11434/api/chat'
                or transport.get('network_retries') != 0 or transport.get('http_status') != 200):
            raise ValueError('preflight original control intent/POST differs')
        body = _strict_json(transport['raw_http_response'])
        if (body != transport['response_payload'] or body.get('done') is not True
                or body.get('done_reason') == 'length' or body.get('model') != provider['model']):
            raise ValueError('preflight incomplete/foreign original response')
        action_output = _strict_json(body['message']['content'])
        Draft202012Validator(_schema(protocol)).validate(action_output)
        if digest(action_output) != digest(case['expected']) or digest(record['output']) != digest(action_output):
            raise ValueError('preflight typed output differs from original response')
        action = action_output if protocol == 'staged-v15' else {'tool': 'edit', 'operations': action_output['operations']}
        state, receipt = _apply(state, action, plan['request'], provider)
        if not receipt['ok'] or record['receipt'] != receipt:
            raise ValueError('preflight interpreter replay differs')
        if case['id'] in ('sequence-validate', 'sequence-finish') and not receipt['result']['valid']:
            raise ValueError('preflight continuous compilation invalid')
        steps.append({'step': len(steps), 'status': 'applied', 'model_reply': {'output': action_output},
            'transition': receipt})
    return {'certificate_sha256': certificate['content_sha256'], 'controls': len(records),
        'age_seconds': age, 'protocol': protocol, 'backend': clone(plan['backend']),
        'runtime_sha256': digest(plan['runtime'])}
