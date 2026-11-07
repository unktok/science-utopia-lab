"""Source-owned local designer decoding, shared by sender/calibration/auditor.

Weights and researcher inference are unchanged. Legacy/V40 staged planner
and editor request reasoning; the explicit V43 direct profile does not. One complete final
JSON function object becomes a tool action, with strict literal arguments.
"""
from utopia.system.design_patch import clone, digest
from .native_designer_tools_v25 import LEGACY_HISTORY, DIRECT_PROFILES, RECOVERY_PROFILES, BOUNDED_AUTHORING, check_conversation_profile

STAGED_MAX_STEPS = 8
STAGED_MAX_TOKENS = 8192
STAGED_CONTEXT_TOKENS = 40960
STAGED_PLANNER_TEMPERATURE = .6
STAGED_EDITOR_TEMPERATURE = .6
STAGED_HTTP_TIMEOUT_SECONDS = (10, 900)


def decoding_contract(protocol, *, role=None, conversation_profile=LEGACY_HISTORY):
    check_conversation_profile(conversation_profile)
    if protocol == 'staged-v15':
        role = role or 'editor'
        if role not in ('planner', 'editor'):
            raise ValueError('unknown source-owned designer role')
        result = {'think': conversation_profile not in DIRECT_PROFILES,
            'backend_format': 'json', 'response_channel': 'function-json-v26',
            'http_timeout_seconds': list(STAGED_HTTP_TIMEOUT_SECONDS),
            'context_policy': {'truncate': False, 'shift': False},
            'max_tokens': STAGED_MAX_TOKENS,
            'temperature': STAGED_PLANNER_TEMPERATURE if role == 'planner' else STAGED_EDITOR_TEMPERATURE,
            'sampling_options': {'num_ctx': STAGED_CONTEXT_TOKENS, 'top_p': .95, 'top_k': 20, 'min_p': 0.0},
            'token_accounting': 'Backend eval_count is retained as reported; no thinking/final split is imputed.'}
        if conversation_profile in RECOVERY_PROFILES:
            result['backend_format_policy'] = 'Generic JSON; host-enforced V44 workflow; all finish arguments are archived non-executable notes'
        if conversation_profile == BOUNDED_AUTHORING:
            from .native_bounded_author_context_v45 import context_contract
            result['active_context_contract'] = context_contract()
        return result
    if protocol == 'one-shot-v14':
        if conversation_profile != LEGACY_HISTORY:
            raise ValueError('designer conversation profile requires staged-v15')
        if role not in (None, 'one-shot'):
            raise ValueError('unknown source-owned designer role')
        return {'think': False, 'backend_format': 'json', 'max_tokens': 2048, 'temperature': .2,
            'sampling_options': {'num_ctx': 32768}}
    raise ValueError('unknown designer decoding protocol')


def decoding_contracts(protocol, *, conversation_profile=LEGACY_HISTORY):
    roles = ('planner', 'editor') if protocol == 'staged-v15' else ('one-shot',)
    return {role: decoding_contract(protocol, role=role, conversation_profile=conversation_profile) for role in roles}


def calibration_role(protocol, case_id):
    if protocol == 'staged-v15':
        return 'planner' if case_id == 'sequence-plan' else 'editor'
    if protocol == 'one-shot-v14':
        return 'one-shot'
    raise ValueError('unknown designer decoding protocol')


def designer_payload(protocol, provider, messages, seed_ctx, *, max_tokens, temperature, role=None,
                     conversation_profile=LEGACY_HISTORY):
    contract = decoding_contract(protocol, role=role, conversation_profile=conversation_profile)
    if conversation_profile in DIRECT_PROFILES and (
            type(max_tokens) is not int or max_tokens != contract['max_tokens']
            or temperature != contract['temperature']):
        raise ValueError('direct designer profile requires its exact source-owned decoding budget/temperature')
    payload = {'model': provider['model'], 'messages': clone(messages),
        'think': contract['think'], 'stream': False,
        'options': {**clone(contract['sampling_options']), 'temperature': temperature,
            'num_predict': max_tokens, 'seed': int(digest(seed_ctx)[:8], 16) % (2**31)}}
    if contract['backend_format'] is not None:
        payload['format'] = contract['backend_format']
    if conversation_profile in RECOVERY_PROFILES:
        from .native_authoring_recovery_v44 import backend_format
        payload['format'] = backend_format(messages)
    payload.update(clone(contract.get('context_policy', {})))
    if conversation_profile == BOUNDED_AUTHORING:
        from .native_bounded_author_context_v45 import check_wire_budget
        check_wire_budget(payload)
    return payload
