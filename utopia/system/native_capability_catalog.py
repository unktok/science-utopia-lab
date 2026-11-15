"""Read-only discoverability of trusted native effect ABIs, not policy recipes.

The index is derived from actual default registration against an empty graph.
No handler, generated source, model, native year or Docker executor is invoked.
Detailed shape schemas are explicitly separated from semantic validator checks.
"""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

from .design_patch import clone, digest

SCHEMA = 'scienceutopia.native-capability-catalog.v15'
CATALOG_IMPLEMENTATIONS = {
    'native.researcher.work.v15': 'Invoke an existing original researcher with arbitrary authored work and response schema.',
    'native.world.resource-transfers.v1': 'Apply conserving institution-authored transfers between actual author balances.',
    'native.domain.commands.v1': 'Apply explicitly granted typed actor/artifact/state/native-effect commands.',
    'native.process.activity.v1': 'Run an explicitly authored registered delegate under bounded data-driven process control.',
    'code.python.v1': 'Run arbitrary authored Python in the pinned isolated no-network executor.',
    'native.world.claim-verification.v1': 'Independently check a completed native count assertion; preserve false claims and corrections.',
    'native.world.review-inputs.v13': 'Expose actual current submissions and original reviewer eligibility without choosing a policy.',
    'native.phase.review.with-routing.v13': 'Execute exactly an institution-authored eligible review-task plan in the original native world.',
    'native.phase.open.v1': 'Run the original native year opening and expose its actual post-opening world observation.',
    'native.world.researcher-context.v1': 'Deliver arbitrary addressed institutional records to original researchers without choosing their actions.',
}


def _source(function):
    path = Path(inspect.getsourcefile(function)).resolve()
    package = Path(__file__).resolve().parents[1]
    if not path.is_relative_to(package):
        raise ValueError('capability source is outside the trusted utopia package')
    return {'path': 'utopia/' + str(path.relative_to(package)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'callable': function.__qualname__}


def _registered():
    from .model import SystemSpec
    from .native_kernel import NativeScienceKernel
    # Empty graph is intentional: constructing a candidate's registry could
    # create its Docker executor. Here code registration is listed separately.
    kernel = NativeScienceKernel(SystemSpec('readonly-native-abi-catalog', 1))
    registry = kernel._registry()
    return {key: registry._implementations[key] for key in registry.registered}


def _pointer(identity):
    return '/cards/' + identity.replace('~', '~0').replace('/', '~1')


def native_capability_index():
    registered = _registered()
    from .code_mechanisms import CODE_IMPLEMENTATION, register_code_mechanisms
    implementations = dict(registered)
    implementations[(CODE_IMPLEMENTATION, 1)] = register_code_mechanisms
    entries = []
    for (identity, version), handler in sorted(implementations.items()):
        detailed = identity in CATALOG_IMPLEMENTATIONS
        entries.append({'implementation': identity, 'version': version,
            'registration': 'default-native-registry' if (identity, version) in registered else
                'conditional: explicitly authored direct/wrapped code node and pinned executor',
            'contract_coverage': 'detailed-shape-and-semantic-contract' if detailed else 'implementation-identity-only',
            'description': CATALOG_IMPLEMENTATIONS.get(identity),
            'detail_path': _pointer(identity) if detailed else None})
    return {'schema': SCHEMA + '.index', 'resource': 'capabilities', 'implementations': entries,
        'lookup': {'tool': 'inspect', 'resource': 'capabilities', 'path': '/cards/<exact implementation ID>'},
        'coverage': {'default_registered_implementation_index': 'complete for the source-pinned empty native registry',
            'conditional_code_implementation': 'explicitly listed; constructor/executor not invoked',
            'detailed_contract_implementations': sorted(CATALOG_IMPLEMENTATIONS),
            'identifier_only_implementations': [entry['implementation'] for entry in entries
                if entry['contract_coverage'] == 'implementation-identity-only'],
            'omitted': ['detailed contracts for identifier-only implementations',
                'operator-specific registry_extension plugins',
                'live researcher/actor/artifact identities and world data',
                'institution algorithms, task instructions, default nodes and automatic connections'],
            'silent_size_truncation': False},
        'effects': {'candidate_mutation': False, 'handlers_invoked': False, 'docker_calls': 0,
            'model_calls': 0, 'native_years': 0}}


def _object(properties):
    return {'type': 'object', 'required': list(properties), 'properties': properties, 'additionalProperties': False}


def _work():
    from .native_researcher_work import (
        IMPLEMENTATION, REQUEST, RESPONSE, _REQUEST_KEYS, validate_work_node, validate_work_request,
    )
    identity = {'type': 'string', 'minLength': 1, 'maxLength': 200}
    request = _object({'schema': {'const': REQUEST}, 'request_id': identity, 'actor_id': identity,
        'instruction': {'type': 'string', 'minLength': 1}, 'content': {'type': 'object'},
        'artifact_ids': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'minLength': 1}},
        'response_schema': {'type': 'object', 'required': ['type'], 'properties': {'type': {'const': 'object'}}}})
    if set(request['required']) != _REQUEST_KEYS:
        raise ValueError('researcher-work catalogue differs from actual request envelope keys')
    return {'implementation': IMPLEMENTATION, 'version': 1,
        'ports': {'inputs': [{'port_id': 'tasks', 'channel': 'artifact', 'artifact_type': REQUEST, 'required': False}],
            'outputs': [{'port_id': 'responses', 'channel': 'artifact', 'artifact_type': RESPONSE, 'required': False}],
            'additional_inputs': 'permitted; exact optional tasks input and sole responses output must remain'},
        'parameters_shape_schema': _object({'max_requests_per_invocation': {'type': 'integer', 'minimum': 1, 'maximum': 64}}),
        'request_shape_schema': request,
        'response_envelope_shape_schema': _object({'schema': {'const': RESPONSE},
            'request_id': identity, 'actor_id': identity, 'response': {'type': 'object'},
            'receipt_sha256': {'type': 'string', 'minLength': 64, 'maxLength': 64}}),
        'author_choices': ['arbitrary task instruction', 'arbitrary JSON scientific content',
            'existing recipient actor', 'available artifact references', 'reference-free bounded object response schema'],
        'semantic_constraints': ['instruction must remain nonempty after whitespace stripping',
            'max_requests_per_invocation is a Python int, never bool or float, in1..64',
            'response_schema must pass the existing bounded reference-free/regex-free schema validator',
            'request <=262144 UTF-8 bytes; rendered prompt <=524288 bytes; never truncated',
            'recipient is an existing author-capable original actor using the exact original-world model',
            'value.actor_ids must equal [actor_id] and artifact_ids must exactly match the envelope',
            'artifact references resolve to actually available native/open-domain/graph records',
            'actual causal event lineage and available periods required; duplicate request identities reject',
            'all requests are preflighted before calls; a later failure does not roll back physical inference cost',
            'response must be a finite object satisfying the authored response_schema'],
        'cost': {'scientist_model_calls': 'one per actual request; <=max_requests_per_invocation per invocation',
            'inherited': ['original fixed model identity', 'original scientist token/temperature settings',
                'exact completed-response cache and checkpoint recovery'],
            'process_repetition': 'each explicit process iteration has its own request cap and distinct identity',
            'whole_world_bound': 'not implied by one invocation cap; sum all actual nodes/invocations/iterations'},
        'privilege': {'granted': ['invoke original researcher and emit response data with audit receipt'],
            'not_granted': ['publish a paper', 'invent actual experiment results', 'mint resources',
                'assign native review scores', 'change researcher weights/personas', 'overwrite a native project']},
        'validators': [_source(validate_work_node), _source(validate_work_request)],
        'schema_scope': 'shape schemas plus separately listed semantic checks; actual validators are authoritative'}


def _transfers():
    from .native_resource_transfers import IMPLEMENTATION, _command, apply_native_resource_transfers
    return {'implementation': IMPLEMENTATION, 'version': 1,
        'ports': {'inputs': 'any explicitly declared ports; handler flattens received values', 'outputs': []},
        'parameters': 'no institution policy parameter is read by this effect handler',
        'request_shape_schema': _object({'transaction_id': {'type': 'string', 'minLength': 1, 'maxLength': 200},
            'from_actor': {'type': 'string', 'minLength': 1}, 'to_actor': {'type': 'string', 'minLength': 1},
            'amount': {'type': 'number', 'exclusiveMinimum': 0}}),
        'semantic_constraints': ['finite strictly positive amount, never bool',
            'existing distinct author-capable from/to actors; sufficient actual debit balance',
            'debit and credit must represent the exact amount; nonfinite/rounding-created credit rejects',
            'at most1024 input values; whole batch checked before mutation',
            'actual causal producer lineage and nonfuture emitted period',
            'repeated producer/port/period/transaction_id is idempotent only if the command is exactly unchanged'],
        'cost': {'scientist_model_calls': 0, 'resources': 'conserving debit/credit of existing actual balances'},
        'privilege': {'granted': ['conserving transfers chosen by explicitly connected institution'],
            'not_granted': ['resource minting', 'implicit transfer selection', 'actor creation']},
        'validators': [_source(_command), _source(apply_native_resource_transfers)],
        'schema_scope': 'shape schema plus semantic checks; no allocation algorithm supplied'}


def _information():
    from .native_kernel import NativeScienceKernel, CONTEXT_RECEIVER, legacy_world_system
    # These are the actual existing producer ports, not a new snapshot effect.
    outputs = next(n['outputs'] for n in legacy_world_system().to_dict()['mechanisms']
                   if n['implementation'] == 'native.phase.open.v1')
    observation = _object({'schema': {'const': 'scienceutopia.native-world-observation.v1'},
        'year': {'type': 'integer', 'minimum': 1}, 'ecosystem': {'type': 'object'},
        'papers': {'type': 'object'}, 'conferences': {'type': 'object'},
        'year_results': {'type': 'object'}, 'extension_state': {'type': 'object'}})
    observation['properties'].update({'system_spec': {'type': 'object'},
        'system_fingerprint': {'type': 'string'}, 'open_domain': {'type': 'object'}})
    opening = {'implementation': 'native.phase.open.v1', 'version': 1,
        'ports': {'inputs': 'handler reads no incoming values; declared graph dependencies still apply',
                  'outputs': outputs},
        'parameters': 'no institution policy parameter is read by the original opening handler',
        'response_shape_schema': observation,
        'observation_fields': {'ecosystem.agents': 'actual serialized agents, including id, can_author, is_active, resources, project_start_year, project_end_year and newest_direction',
            'papers': 'actual current paper-tracker serialization',
            'conferences': 'actual conferences, including in-flight submitted_papers',
            'extension_state': 'saved graph mechanism states, not an evaluator or private cache',
            'system_spec': 'only if expose_system_spec metadata explicitly enables self-description',
            'open_domain': 'only if actual open-domain state exists'},
        'semantic_constraints': ['Runs original _setup_year and _start_native_government_year before observation.',
            'The graph must invoke the original opening exactly as its world-law scope permits.',
            'Other native phases also emit their own post-stage world observations; an opening snapshot is not refreshed by waiting.',
            'Author code chooses what to compute, where to route it and when a later consumer runs.',
            'A future model decision cannot be retroactively changed by a later message.'],
        'cost': {'scientist_model_calls': 'original native opening semantics, not a new free model-query endpoint'},
        'privilege': {'granted': ['observe the actual post-opening native world'],
            'not_granted': ['private losses or observer caches', 'new arbitrary snapshots at any time',
                'changing native production/calendar laws', 'automatic messages or wires']},
        'validators': [_source(NativeScienceKernel.observation), _source(NativeScienceKernel)],
        'schema_scope': 'top-level observation shape and literal existing ports; nested domain semantics remain native, not a policy recipe'}
    envelope = _object({'payload': {'type': 'object'},
        'actor_ids': {'type': 'array', 'minItems': 1,
                      'items': {'type': 'string', 'minLength': 1}}})
    envelope['properties']['artifact_ids'] = {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}
    delivery = {'implementation': CONTEXT_RECEIVER, 'version': 1,
        'ports': {'inputs': 'any explicitly declared compatible input ports; all delivered values are consumed',
            'outputs': [], 'optional_unused_output_declarations': 'handler emits no values; required output ports cannot be satisfied'},
        'parameters': 'no policy parameter, instruction template or prescribed payload key is read',
        'producer_code_envelope_shape_schema': envelope,
        'semantic_constraints': ['Payload is an arbitrary finite JSON object; no instruction/topic/policy vocabulary is required.',
            'Nonempty explicit actor_ids must name actual existing author-capable actors.',
            'Graph/runtime supplies causal source, emitted period and lineage; generated code cannot forge these fields.',
            'A delivered record is appended to actual institutional_context and emits native.system.context_delivered.',
            'Repeated message identity raises; no rollback of earlier applied messages in a failed batch is promised.',
            'The original institutional_context_prompt renders stored context for native consumers that call it; not every possible model call is such a consumer.',
            'Schedule and latency are authored graph choices. Late delivery is legal and may only affect later eligible decisions.',
            'Receiver/delivery, prompt presence, chosen action and improved outcome are separate observations.'],
        'persistence': 'stored actor context survives native checkpoint/restart; a one-time producer need not emit every year',
        'cost': {'scientist_model_calls': 0, 'later_input_tokens': 'changed researcher requests retain their actual inference cost'},
        'privilege': {'granted': ['append arbitrary addressed institutional information to original researcher context'],
            'not_granted': ['force obedience', 'overwrite projects', 'fabricate scores or paper acceptance',
                'change weights/personas', 'automatically register a new native action']},
        'validators': [_source(NativeScienceKernel._receive_context)],
        'schema_scope': 'isolated-code output envelope shape plus separately listed native recipient/delivery semantics; no policy algorithm supplied'}
    return [opening, delivery]


def _domain():
    from .native_catalog_planning import apply_catalog_project, validate_catalog_assignment
    from .native_legacy_topic_planning import apply_legacy_topic_project, validate_legacy_topic_assignment
    from .native_open_domain import (IMPLEMENTATION, STATE_ARTIFACT, COMMAND_SCHEMA,
        default_actions, register_native_domain, apply_domain_commands)
    actions = default_actions()
    return {'implementation': IMPLEMENTATION, 'version': 1,
        'ports': {'inputs': 'commands port; other input names are not consumed',
            'outputs': [{'port_id': 'domain', 'channel': 'artifact', 'artifact_type': STATE_ARTIFACT}],
            'output_optional': 'an entirely empty output declaration is also supported'},
        'parameters': {'capabilities': {'bootstrap': 'explicit unique action grants',
                'roles': 'authored role -> unique action grants'},
            'actor_schemas': 'authored actor type -> bounded JSON schema',
            'artifact_schemas': 'authored artifact type -> bounded JSON schema'},
        'action_payload_schemas': {name: clone(schema) for name, (schema, handler) in actions.actions.items()},
        'request_shape_schema': _object({'schema': {'const': COMMAND_SCHEMA},
            'command_id': {'type': 'string', 'minLength': 1, 'maxLength': 200},
            'actor_id': {'type': 'string'}, 'action': {'type': 'string'}, 'payload': {'type': 'object'}}),
        'action_schema_derivation': 'read directly from actual default_actions().actions, no copy of a policy catalogue',
        'semantic_constraints': ['explicit source principal/role/action grants and actual lineage required',
            'actor/artifact identities/types/revisions/references checked against actual persistent world state',
            'native project/context/transfer actions retain their own original-world semantic constraints',
            'native.catalog-project.v1 requires a legacy active idle author, an actual displayed expertise topic '
            'and its exact original catalog content/duration; filtered exploration candidates are unsupported in v1',
            'native.legacy-topic-project.v1 instead permits core expertise plus directly related original catalog '
            'topics, with exact original content/duration and active idle author requirements; no shortest-topic '
            'or merit rule is imposed. This action still needs an explicit grant and a study domain permitting it',
            'schemas describe data; generated code never becomes a trusted host handler'],
        'cost': {'scientist_model_calls': 0, 'resources': 'only explicitly granted conserving native transfer effect'},
        'privilege': {'granted': ['only the explicitly declared action capability grants'],
            'not_granted': ['register arbitrary host Python', 'silently invent new native privilege', 'bypass schema/identity checks']},
        'validators': [_source(register_native_domain), _source(apply_domain_commands),
            _source(apply_catalog_project), _source(validate_catalog_assignment),
            _source(apply_legacy_topic_project), _source(validate_legacy_topic_assignment)],
        'schema_scope': 'actual registered action payload schemas; command envelope and semantic checks remain explicit'}


def _process():
    from .native_process import IMPLEMENTATION, CONTROL, DONE, _validate_parameters, controlled_activity
    return {'implementation': IMPLEMENTATION, 'version': 1,
        'ports': {'inputs': 'delegate inputs plus optional explicit process-control signal',
            'outputs': 'delegate outputs made optional plus process-completion signal of type ' + CONTROL,
            'reserved': {'control_input': 'process-control', 'completion_output': DONE}},
        'parameter_fields': {'delegate': 'complete authored registered mechanism, no recursive process delegate',
            'count': 'integer0..limit', 'limit': 'integer1..1024', 'control': 'boolean',
            'guard_path': 'null or nonempty string-key list; requires control',
            'count_path': 'null or nonempty string-key list; requires control',
            'until_path': 'null or nonempty string-key list', 'initial_delegate_state': 'explicit JSON object',
            'missing_control': 'wait|error'},
        'semantic_constraints': ['all parameter fields explicit; reserved ports may not collide',
            'delegates resolve in actual native registry before execution',
            'native.phase/native.activity legacy routines cannot repeat more than once per annual identity',
            'data-driven guard/count/stop values remain bounded and typed; no expressions evaluated on the host'],
        'cost': {'scientist_model_calls': 'delegate-dependent; multiplied only by explicit actual bounded iterations'},
        'privilege': {'granted': ['compose/reorder/guard/repeat actually registered activities'],
            'not_granted': ['new underlying native privilege', 'unbounded hidden loops', 'automatic institutional design']},
        'validators': [_source(_validate_parameters), _source(controlled_activity)],
        'schema_scope': 'parameter/port ABI summary; actual process validator authoritative'}


def _code():
    from .code_mechanisms import CODE_IMPLEMENTATION, CODE_SCHEMA, validate_code_artifact, register_code_mechanisms
    return {'implementation': CODE_IMPLEMENTATION, 'version': 1,
        'ports': {'inputs': 'arbitrary explicitly declared ports matching code_artifact.inputs',
            'outputs': 'arbitrary explicitly declared ports matching code_artifact.outputs'},
        'parameter_fields': {'runtime_image_id': 'must equal supplied pinned operator image',
            'code_artifact': {'schema': CODE_SCHEMA, 'label': 'string1..120 characters',
                'source': 'literal arbitrary Python1..65536 UTF-8 bytes defining one top-level step(context)',
                'inputs': 'port -> bounded JSON schema, <=32 ports',
                'outputs': 'port -> bounded JSON schema, <=32 ports', 'state_schema': 'bounded JSON schema'},
            'other_authored_fields': 'ordinary data accessible as context.parameters'},
        'execution_ABI': {'context_keys': ['period', 'phase', 'random_seed', 'parameters', 'state', 'inputs'],
            'inputs': 'port -> list of complete delivered message envelopes; body in payload',
            'return': 'outputs:{port:[message envelopes...]}, state:JSON object'},
        'cost': {'scientist_model_calls': 0, 'runtime': 'pinned isolated executor with explicit resource limits'},
        'privilege': {'granted': ['arbitrary source computation and typed graph output'],
            'not_granted': ['host execution/import', 'network', 'world mutation without separately connected native effect capability']},
        'validators': [_source(validate_code_artifact), _source(register_code_mechanisms)],
        'schema_scope': 'literal artifact/port/source ABI; no source template or algorithm supplied'}


def _claims():
    from .native_claim_verification import (IMPLEMENTATION,CLAIM,VERDICT,METRICS,
        evaluate_claim,verify_claims,validated_records,MAX_CLAIMS_PER_INVOCATION,MAX_RETAINED_CLAIMS)
    identity={'type':'string','minLength':1,'maxLength':200}
    return {'implementation':IMPLEMENTATION,'version':1,
        'ports':{'inputs':[{'port_id':'claims','channel':'artifact','artifact_type':CLAIM,'required':False}],
            'outputs':[{'port_id':'verifications','channel':'artifact','artifact_type':VERDICT,'required':False}]},
        'parameters':'No policy parameters read; source-defined metric counts and actual native evidence are authoritative.',
        'request_shape_schema':_object({'schema':{'const':CLAIM},'claim_id':identity,
            'metric':{'enum':list(METRICS)},'after_year':{'type':'integer','minimum':0},
            'through_year':{'type':'integer','minimum':1},'asserted_value':{'type':'integer','minimum':0},
            'supersedes':{'anyOf':[{'type':'null'},identity]}}),
        'semantic_constraints':['Counts/years must be Python ints, never bool or float.',
            'after_year < through_year <= actual completed native publication year; future/partial intervals reject.',
            'actual causal input lineage required; supplied recipients must be actual researchers; duplicate batch identities reject.',
            'Only actual native paper/review histories determine the computed count; no authored world or truth flag.',
            'Corrections name a retained predecessor for the same metric/interval; old records and hashes persist.',
            'Every retained verdict is recomputed against native evidence; all validation precedes returned state commit.'],
        'author_choices':['arbitrary claim identity','one explicit count metric and completed interval',
            'literal nonnegative asserted value','optional predecessor','arbitrary producer and delivery graph'],
        'cost':{'scientist_model_calls':0,'native_record_scan':'completed interval records per assertion',
            'max_claims_per_invocation':MAX_CLAIMS_PER_INVOCATION,'max_retained_claims':MAX_RETAINED_CLAIMS,
            'overflow':'technical error; no partial commit or silent history discard'},
        'privilege':{'granted':['emit independent count-consistency verdict data and preserved correction history'],
            'not_granted':['scientific truth of a paper','publish knowledge','assign a loss or promotion policy',
                'alter native evidence','execute authored host code']},
        'validators':[_source(evaluate_claim),_source(verify_claims),_source(validated_records)],
        'schema_scope':'shape plus actual publication/identity/state semantic checks, not an external science oracle'}


def _review_routing():
    from .native_review_routing import (BATCH, PLAN, SNAPSHOT, REVIEW, STATE,
        review_input_batch, validate_routing_plan, validate_routing_state, register_review_routing)
    identity = {'type': 'string', 'minLength': 1}
    plan = _object({'schema': {'const': PLAN}, 'year': {'type': 'integer'},
        'batch_sha256': {'type': 'string'}, 'tasks': {'type': 'array', 'items': _object({
            'conference_id': identity, 'paper_id': identity, 'reviewer_id': identity})}})
    batch = _object({'schema': {'const': BATCH}, 'year': {'type': 'integer'},
        'papers': {'type': 'array', 'items': _object({'conference_id': identity,
            'paper_id': identity, 'paper': {'type': 'object'},
            'eligible_reviewer_ids': {'type': 'array', 'items': identity}})}})
    shared = {'version': 1, 'parameters': 'No policy parameters are consumed by these handlers.',
        'integration': 'Author every node, artifact type, port, connection and schedule explicitly. '
            'Read the current graph: snapshot and arbitrary producer must precede the original review. '
            'Do not copy numeric phases from another graph; no automatic wiring or policy is supplied.',
        'schema_scope': 'Shape descriptions plus separately stated runtime identity/lineage checks; '
            'actual validators are authoritative. No routing algorithm or example policy provided.'}
    snapshot = {**shared, 'implementation': SNAPSHOT,
        'ports': {'inputs': 'Explicit world dependency from the current native costs stage.',
            'outputs': [{'port_id': 'batch', 'channel': 'artifact', 'artifact_type': BATCH, 'required': True}]},
        'response_shape_schema': batch,
        'semantic_constraints': ['Exact actual conference/paper/year identities with globally unique paper IDs.',
            'Eligibility is original can_review with paper-author and conflict-of-interest exclusions.',
            'No model calls, RNG, decisions or review scores are produced.'],
        'cost': {'scientist_model_calls': 0},
        'privilege': {'granted': ['read current actual submissions and eligible reviewer identities'],
            'not_granted': ['create papers or reviewers', 'alter projects', 'assign review scores']},
        'validators': [_source(review_input_batch), _source(register_review_routing)]}
    review = {**shared, 'implementation': REVIEW,
        'ports': {'inputs': [
            {'port_id': 'batch', 'channel': 'artifact', 'artifact_type': BATCH, 'required': True},
            {'port_id': 'routing', 'channel': 'artifact', 'artifact_type': PLAN, 'required': True}],
            'inherited': 'Retain the original review phase completion dependency and next/world outputs.'},
        'request_shape_schema': plan,
        'batch_shape_schema': batch,
        'batch_hash_encoding': 'SHA256 of exact batch encoded as UTF-8 JSON with sort_keys=True, '
            'separators=(comma,colon), ensure_ascii=False, allow_nan=False.',
        'semantic_constraints': ['Exactly one batch and one routing value with causal lineage in the current period.',
            'Batch must equal the actual current native submissions and original eligibility in full.',
            'year must be Python int (not bool/float) and equal current native year; batch_sha256 must match.',
            'Every task names an actual conference/paper and eligible reviewer; duplicate triples reject.',
            'Empty tasks and papers without reviews are legal; no raw review is fabricated.',
            'Legacy selection may reject missing reviews; choose a compatible explicit selection if needed.',
            'Cannot repeat or rewind an already committed review year; persistent state is receipt-bound.'],
        'state_contract': {'schema': STATE, 'fields': ['schema', 'last_period', 'receipt_sha256']},
        'author_choices': ['arbitrary task set and order within actual eligibility',
            'arbitrary producer code, information paths and institutional schedules within declared design space'],
        'cost': {'scientist_model_calls': 'actual original review tasks; record physical batch requests and tokens separately'},
        'privilege': {'granted': ['change actual native review assignment and work'],
            'not_granted': ['fabricate scores', 'accept papers automatically', 'overwrite projects',
                'override the experiment design-space or native world accounting']},
        'validators': [_source(validate_routing_plan), _source(validate_routing_state), _source(register_review_routing)]}
    return [snapshot, review]


def native_capability_catalog():
    cards = [_work(), _transfers(), _domain(), _process(), _code(), _claims(), *_review_routing(), *_information()]
    registered = _registered()
    registry_sources = {_source(handler)['path']: _source(handler)
        for handler in registered.values()}
    result = {'schema': SCHEMA, 'index': native_capability_index(),
        'cards': {card['implementation']: card for card in cards},
        'catalog_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'registry_sources': [registry_sources[key] for key in sorted(registry_sources)],
        'interpretation': 'native effect ABI discovery, not a finite institution/scientific-activity policy catalogue'}
    result['content_sha256'] = digest(result)
    return result
