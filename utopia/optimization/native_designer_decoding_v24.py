"""Source-owned local designer decoding, shared by sender/calibration/auditor.

Weights and researcher inference are unchanged. Only the staged institutional
designer requests reasoning; final JSON content alone becomes a tool action.
"""
from utopia.system.design_patch import clone, digest

STAGED_MAX_STEPS = 8
STAGED_MAX_TOKENS = 8192
STAGED_TEMPERATURE = .6


def decoding_contract(protocol):
    if protocol == 'staged-v15':
        return {'think': True, 'backend_format': 'json', 'max_tokens': STAGED_MAX_TOKENS,
            'temperature': STAGED_TEMPERATURE,
            'sampling_options': {'num_ctx': 32768, 'top_p': .95, 'top_k': 20, 'min_p': 0.0},
            'token_accounting': 'Backend eval_count is retained as reported; no thinking/final split is imputed.'}
    if protocol == 'one-shot-v14':
        return {'think': False, 'backend_format': 'json', 'max_tokens': 2048, 'temperature': .2,
            'sampling_options': {'num_ctx': 32768}}
    raise ValueError('unknown designer decoding protocol')


def designer_payload(protocol, provider, messages, seed_ctx, *, max_tokens, temperature):
    contract = decoding_contract(protocol)
    payload = {'model': provider['model'], 'messages': clone(messages),
        'think': contract['think'], 'stream': False,
        'options': {**clone(contract['sampling_options']), 'temperature': temperature,
            'num_predict': max_tokens, 'seed': int(digest(seed_ctx)[:8], 16) % (2**31)}}
    if contract['backend_format'] is not None:
        payload['format'] = contract['backend_format']
    return payload
