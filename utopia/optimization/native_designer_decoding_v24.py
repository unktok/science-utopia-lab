"""Source-owned local designer decoding, shared by sender/calibration/auditor.

Weights and researcher inference are unchanged. The staged institutional
planner requests reasoning; the literal editor does not. One complete final
Hermes envelope becomes a tool action, with strict JSON arguments.
"""
from utopia.system.design_patch import clone, digest

STAGED_MAX_STEPS = 8
STAGED_MAX_TOKENS = 8192
STAGED_PLANNER_TEMPERATURE = .6
STAGED_EDITOR_TEMPERATURE = .2


def decoding_contract(protocol, *, role=None):
    if protocol == 'staged-v15':
        role = role or 'editor'
        if role not in ('planner', 'editor'):
            raise ValueError('unknown source-owned designer role')
        return {'think': role == 'planner', 'backend_format': None, 'response_channel': 'hermes-text-v25',
            'context_policy': {'truncate': False, 'shift': False},
            'max_tokens': STAGED_MAX_TOKENS,
            'temperature': STAGED_PLANNER_TEMPERATURE if role == 'planner' else STAGED_EDITOR_TEMPERATURE,
            'sampling_options': {'num_ctx': 32768, 'top_p': .95, 'top_k': 20, 'min_p': 0.0},
            'token_accounting': 'Backend eval_count is retained as reported; no thinking/final split is imputed.'}
    if protocol == 'one-shot-v14':
        if role not in (None, 'one-shot'):
            raise ValueError('unknown source-owned designer role')
        return {'think': False, 'backend_format': 'json', 'max_tokens': 2048, 'temperature': .2,
            'sampling_options': {'num_ctx': 32768}}
    raise ValueError('unknown designer decoding protocol')


def decoding_contracts(protocol):
    roles = ('planner', 'editor') if protocol == 'staged-v15' else ('one-shot',)
    return {role: decoding_contract(protocol, role=role) for role in roles}


def calibration_role(protocol, case_id):
    if protocol == 'staged-v15':
        return 'planner' if case_id == 'sequence-plan' else 'editor'
    if protocol == 'one-shot-v14':
        return 'one-shot'
    raise ValueError('unknown designer decoding protocol')


def designer_payload(protocol, provider, messages, seed_ctx, *, max_tokens, temperature, role=None):
    contract = decoding_contract(protocol, role=role)
    payload = {'model': provider['model'], 'messages': clone(messages),
        'think': contract['think'], 'stream': False,
        'options': {**clone(contract['sampling_options']), 'temperature': temperature,
            'num_predict': max_tokens, 'seed': int(digest(seed_ctx)[:8], 16) % (2**31)}}
    if contract['backend_format'] is not None:
        payload['format'] = contract['backend_format']
    payload.update(clone(contract.get('context_policy', {})))
    return payload
