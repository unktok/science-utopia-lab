"""Non-veto diagnostics for the existing object-payload code ABI.

No schema satisfiability solver, source evaluation, candidate repair or native
probe. Empty record lists remain legal even if a port schema excludes objects.
Only explicit root types and literal local context-key reads are diagnosed.
"""
import ast
from utopia.system.design_patch import clone

JSON_TYPES = frozenset({'null', 'boolean', 'object', 'array', 'number', 'integer', 'string'})
SCOPE = ('Explicit code-schema root types, original adapter consumption and literal local context-key reads only; '
    'no general dataflow/reachability proof, schema satisfiability, factor enumeration or native execution.')
STAGE_PARAMETER_RULE = (
    'Original native.phase.*.v1 stages and native.activity.*.v1 '
    'resubmissions/research/collaboration/submission/funding adapters do not read '
    'mechanism.parameters. Adding keys does not change their routines. Explicitly '
    'author a consuming code/process/wiring and use the actual native effect ABI. '
    'Keys remain legal data; this notice supplies no implementation and makes no '
    'claim about other mechanisms reading deliberately exposed data.')


def _original_stage_adapter(implementation):
    from utopia.system.native_kernel import STAGES
    return isinstance(implementation, str) and implementation in ({'native.phase.' + stage + '.v1' for stage, _ in STAGES}
        | {'native.activity.' + stage + '.v1' for stage in
           ('resubmissions', 'research', 'collaboration', 'submission', 'funding')})


def _excludes_object(schema):
    if not isinstance(schema, dict):
        return False
    declared = schema.get('type')
    if isinstance(declared, str):
        return declared in JSON_TYPES and declared != 'object'
    if (isinstance(declared, list) and 0 < len(declared) <= len(JSON_TYPES)
            and all(isinstance(item, str) and item in JSON_TYPES for item in declared)
            and len(set(declared)) == len(declared)):
        return 'object' not in declared
    return False  # Invalid/implicit/composed schemas belong to other checks.


def _escape(value):
    return value.replace('~', '~0').replace('/', '~1')


def _missing_literal_reads(artifact, parameters):
    """Syntactic potential mismatches, not branch/dataflow/exception analysis."""
    source = artifact.get('source')
    if not isinstance(source, str):
        return []
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, TypeError, RecursionError, MemoryError):
        return []  # Existing source validation diagnoses unparseable artifacts.
    missing = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str) and isinstance(node.value, ast.Subscript)):
            continue
        parent = node.value
        if not (isinstance(parent.value, ast.Name) and parent.value.id == 'context'
                and isinstance(parent.slice, ast.Constant) and parent.slice.value in ('parameters', 'inputs')):
            continue
        namespace, key = parent.slice.value, node.slice.value
        available = parameters if namespace == 'parameters' else artifact.get('inputs')
        if isinstance(available, dict) and key not in available:
            missing.add((namespace, key))
    return sorted(missing)


def contract_notices(document):
    """Read-only notices; none changes the accepted design or its validity."""
    if not isinstance(document, dict) or not isinstance(document.get('mechanisms'), list):
        return []
    pending = [(node, '/mechanisms/' + str(index), node.get('mechanism_id') if isinstance(node, dict) else None, frozenset())
        for index, node in reversed(list(enumerate(document['mechanisms'])))]
    notices = []
    while pending:
        node, prefix, owner, ancestors = pending.pop()
        if not isinstance(node, dict) or id(node) in ancestors:
            continue
        parameters = node.get('parameters')
        if not isinstance(parameters, dict) or node.get('version', 1) != 1:
            continue
        if node.get('implementation') == 'native.process.activity.v1':
            pending.append((parameters.get('delegate'), prefix + '/parameters/delegate', owner, ancestors | {id(node)}))
            continue
        if parameters and _original_stage_adapter(node.get('implementation')):
            notices.append({'code': 'original-stage-adapter-does-not-read-parameters',
                'mechanism_id': owner, 'executed_mechanism_id': node.get('mechanism_id'),
                'implementation': node.get('implementation'), 'path': prefix + '/parameters',
                'parameter_names': sorted(key for key in parameters if isinstance(key, str)),
                'message': STAGE_PARAMETER_RULE,
                'scope': 'This implementation handler only, not general whole-system effect analysis.',
                'changes_validity': False, 'authored_value_changed_by_host': False,
                'native_execution_performed': False})
            continue
        if node.get('implementation') != 'code.python.v1':
            continue  # No assumptions about another implementation's data contract.
        artifact = parameters.get('code_artifact')
        if not isinstance(artifact, dict) or artifact.get('schema') != 'scienceutopia.code-mechanism.v1':
            continue
        base = prefix + '/parameters/code_artifact'
        # Match register_code_mechanisms.handler's actual request, not the
        # editor configuration map (which also holds sandbox/artifact metadata).
        local_parameters = {k: v for k, v in parameters.items() if k not in {'code_artifact', 'runtime_image_id'}}
        for namespace, key in _missing_literal_reads(artifact, local_parameters):
            available = local_parameters if namespace == 'parameters' else artifact['inputs']
            from .native_field_addressing_v28 import (
                _bounded_names, MAX_FEEDBACK_NAMES, MAX_FEEDBACK_NAME_BYTES)
            names = sorted(name for name in available if isinstance(name, str))
            included = _bounded_names(names)
            notices.append({'code': 'literal-local-context-key-not-present',
                'mechanism_id': owner, 'executed_mechanism_id': node.get('mechanism_id'),
                'path': base + '/source', 'namespace': namespace, 'literal_key': key,
                'observed_local_keys': included,
                'observed_local_key_count': len(names),
                'observed_local_keys_omitted_count': len(names) - len(included),
                'observed_local_keys_complete': len(names) == len(included),
                'observed_local_key_limits': {'names': MAX_FEEDBACK_NAMES,
                    'encoded_name_utf8_bytes': MAX_FEEDBACK_NAME_BYTES},
                'message': 'A literal context key read is absent from this executing node. '
                    'context parameters/inputs are local to this node; another node having the key '
                    'does not bind it here. code_artifact/runtime_image_id are excluded from runtime user parameters. '
                    'No value, owner, source or wire was supplied or changed.',
                'scope': 'Potential syntactic read only; no reachability, context rebinding or exception-handling proof.',
                'changes_validity': False, 'authored_value_changed_by_host': False,
                'native_execution_performed': False})
        schemas = []
        for direction in ('inputs', 'outputs'):
            ports = artifact.get(direction)
            if isinstance(ports, dict):
                schemas.extend((direction, base + '/' + direction + '/' + _escape(port), ports[port])
                    for port in sorted(key for key in ports if isinstance(key, str)))
        schemas.append(('state_schema', base + '/state_schema', artifact.get('state_schema')))
        for direction, path, schema in schemas:
            if not _excludes_object(schema):
                continue
            is_state = direction == 'state_schema'
            notices.append({'code': 'code-abi-explicit-type-excludes-object',
                'mechanism_id': owner, 'executed_mechanism_id': node.get('mechanism_id'),
                'path': path, 'declared_type': clone(schema['type']),
                'runtime_object': 'returned state' if is_state else 'one record payload',
                'condition': ('When this mechanism executes and returns state.' if is_state else
                    'When a record is delivered/emitted on this port; an empty record list remains legal.'),
                'message': ('The code ABI requires object state, including returned empty state.' if is_state else
                    'Each record payload is an object. This schema does not describe the outer list of records. '
                    'Array-valued data may be fields inside a payload object.'),
                'changes_validity': False, 'authored_value_changed_by_host': False,
                'native_execution_performed': False})
    return notices


def notice_summary(document, *, limit=8):
    """Bound prompt overhead without silently dropping the total notice count."""
    if type(limit) is not int or limit < 1:
        raise ValueError('notice limit must be a positive integer')
    notices = contract_notices(document)
    return {'scope': SCOPE, 'notices': notices[:limit], 'total_count': len(notices),
        'included_count': min(limit, len(notices)), 'omitted_count': max(0, len(notices) - limit),
        'complete': len(notices) <= limit, 'limit': limit,
        'omission': 'Revalidate after edits to inspect remaining notices.' if len(notices) > limit else None,
        'warning_is_not_a_veto': True}
