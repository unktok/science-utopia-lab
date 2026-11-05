"""Stable-ID addressing for arbitrary authored native edits, never a design menu.

Compilation only translates explicit addresses into the existing atomic patch.
It never repairs literals, invents wires/source, filters support or executes code.
The legacy generated-vocabulary representation remains the execution boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

from utopia.optimization.native_adaptive_search import _apply_or_identity
from utopia.optimization.native_factorized_gradient import NativeFactorizedDesignSearch
from utopia.system import SystemSpec
from utopia.system.design_patch import _edit, clone, digest, make_patch, pointer

PROTOCOL = 'scienceutopia.native-stable-id-authoring.v1'
TRACE = 'scienceutopia.native-stable-id-compile-trace.v1'
SELECTOR = {'type': 'object', 'required': ['mechanism_id'], 'additionalProperties': False,
    'properties': {'mechanism_id': {'type': 'string', 'minLength': 1}}}
# An empty schema is ANY JSON according to JSON Schema, but the deployed
# llama.cpp converter compiled it as object-only. Spell out the equivalent
# union; never silently narrow the institution author's legal operand types.
ANY_JSON = {'type': ['object', 'array', 'string', 'number', 'boolean', 'null']}


def _operation_schema(action, selected):
    properties = {'op': {'const': action}, 'path': {'type': 'string',
        'pattern': r'^(?:/.*)?$' if selected else r'^/.+', 'maxLength': 4096}}
    required = ['op', 'path']
    if selected:
        properties['selector'] = SELECTOR
        required.append('selector')
    if action != 'remove':
        properties['value'] = ANY_JSON
        required.append('value')
    return {'type': 'object', 'required': required, 'properties': properties, 'additionalProperties': False}


OPERATION = {'oneOf': [_operation_schema(action, selected)
    for selected in (False, True) for action in ('add', 'replace', 'remove')]}
CHOICE = {'type': 'object', 'required': ['id', 'operations', 'provenance'], 'additionalProperties': False,
    'properties': {'id': {'type': 'string', 'minLength': 1},
        'operations': {'type': 'array', 'maxItems': 80, 'items': OPERATION},
        'provenance': {'type': 'object', 'minProperties': 1}}}
FACTOR = {'type': 'object', 'required': ['id', 'kind', 'choices'], 'additionalProperties': False,
    'properties': {'id': {'type': 'string', 'minLength': 1},
        'kind': {'enum': ['categorical', 'bernoulli']},
        'choices': {'type': 'array', 'minItems': 2, 'items': CHOICE},
        'support': {'type': 'array', 'minItems': 1, 'items': {
            'type': 'object', 'required': ['when', 'allow'], 'additionalProperties': False,
            'properties': {'when': {'type': 'object', 'additionalProperties': {'type': 'string'}},
                'allow': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'type': 'string'}}}}}}}
COORDINATE = {'type': 'object', 'required': ['id', 'path', 'lower', 'upper', 'mean', 'sigma'],
    'additionalProperties': False, 'properties': {
        'id': {'type': 'string', 'minLength': 1}, 'path': {'type': 'string', 'pattern': r'^/.+', 'maxLength': 4096},
        'selector': SELECTOR, **{key: {'type': 'number'} for key in ('lower', 'upper', 'mean', 'sigma')}}}
OUTPUT_SCHEMA = {'type': 'object', 'required': ['operations', 'factors', 'continuous', 'rationale'],
    'additionalProperties': False, 'properties': {
        'operations': {'type': 'array', 'maxItems': 80, 'items': OPERATION},
        'factors': {'type': 'array', 'maxItems': 12, 'items': FACTOR},
        'continuous': {'type': 'array', 'maxItems': 12, 'items': COORDINATE},
        'logits': {'type': 'object', 'additionalProperties': {'type': 'array', 'items': {'type': 'number'}}},
        'rationale': {'type': 'string', 'minLength': 1, 'maxLength': 4096}}}

INSTRUCTIONS = """Stable-ID authoring protocol v1 address contract:
An edit is {op:'add'|'replace'|'remove', selector:{mechanism_id:<EXACT authored ID>},
path:<JSON pointer LOCAL to that mechanism>, value:<literal JSON when not remove>}.
For replacing/removing an entire mechanism, selector plus path:'' is allowed.
Resolve IDs after preceding explicitly authored edits, never by guessed index.
Alternatively omit selector and use an unrestricted full-document JSON pointer.
That escape supports explicit new mechanisms, removals, ports, wires, protocol
types, schedules, process delegates and metadata. It does not fill missing edits.
Adding a new mechanism uses full-document add, such as path:'/mechanisms/-',
and a complete authored node value. New IDs and source are chosen by you.
Schema containers are literal JSON objects, never JSON-encoded strings.
Python source is a literal UTF-8 string of 1..65536 bytes, never a coordinate.
Continuous entries may include selector plus LOCAL numeric path, or omit it
and name a full-document numeric path. Every reachable structure must already
contain that finite numeric field; booleans, source text and schema strings are
not numeric fields. An explicitly authored parameter still needs your code to
read it; the host never creates that relationship. [] remains legal.
Factor choice edits are resolved after the authored base and all earlier chosen
edits. If one choice or coordinate resolves to different array pointers across
reachable branches, compilation rejects it: explicitly express those different
conditional edits or use full-document paths. No support is silently removed.
The path catalogue describes the actual parent and its JSON types, not a menu
of allowed institutions. All literal source/schema values remain your output.
"""


def json_type(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, dict):
        return 'object'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, str):
        return 'string'
    return 'number' if type(value) in (int, float) else type(value).__name__


def _escape(segment):
    return str(segment).replace('~', '~0').replace('/', '~1')


def _path(parts):
    return '/' + '/'.join(_escape(p) for p in parts) if parts else ''


class AuthoringIRDiagnostic(ValueError):
    def __init__(self, message, **diagnostic):
        super().__init__(message)
        self.diagnostics = [{'message': message, 'operation_index': None, 'path': None,
            'deepest_existing_prefix': None, 'first_missing_segment': None, 'available_keys': None,
            'actual_owner_id': None, 'actual_owner_implementation': None, **clone(diagnostic)}]


def _owner(document, parts):
    if len(parts) > 1 and parts[0] == 'mechanisms' and str(parts[1]).isdecimal():
        nodes = document.get('mechanisms', [])
        index = int(parts[1])
        if isinstance(nodes, list) and index < len(nodes) and isinstance(nodes[index], dict):
            return {'actual_owner_id': nodes[index].get('mechanism_id'),
                'actual_owner_implementation': nodes[index].get('implementation')}
    return {}


def _read(document, path, *, operation_index=None, stage=None, allow_add=False):
    try:
        parts = pointer(path)
    except ValueError as error:
        raise AuthoringIRDiagnostic(str(error), operation_index=operation_index, path=path, stage=stage) from error
    current, traversed = document, []
    for index, segment in enumerate(parts):
        leaf = index == len(parts) - 1
        available = sorted(current) if isinstance(current, dict) else None
        if isinstance(current, dict):
            exists = segment in current
            if leaf and allow_add and not exists:
                return None
        elif isinstance(current, list):
            canonical = segment.isdecimal() and (segment == '0' or not segment.startswith('0'))
            exists = canonical and int(segment) < len(current)
            if leaf and allow_add and (segment == '-' or canonical and int(segment) == len(current)):
                return None
        else:
            exists = False
        if not exists:
            raise AuthoringIRDiagnostic('authored path does not exist' if json_type(current) in ('object', 'array')
                else 'authored path traverses a scalar', operation_index=operation_index, path=path,
                stage=stage, deepest_existing_prefix=_path(traversed), first_missing_segment=segment,
                available_keys=available, actual_type=json_type(current), **_owner(document, parts))
        current = current[int(segment)] if isinstance(current, list) else current[segment]
        traversed.append(segment)
    return current


def resolve_address(document, address, *, operation_index=None, stage=None):
    """Resolve one exact selector, without changing the authored transaction."""
    local = address['path']
    if 'selector' not in address:
        return local
    identity = address['selector']['mechanism_id']
    matches = [i for i, node in enumerate(document.get('mechanisms', []))
        if isinstance(node, dict) and node.get('mechanism_id') == identity]
    if len(matches) != 1:
        raise AuthoringIRDiagnostic('stable mechanism ID is missing or ambiguous', operation_index=operation_index,
            path=local, stage=stage, selector=address['selector'], deepest_existing_prefix='/mechanisms',
            first_missing_segment=identity, available_keys=[node.get('mechanism_id')
                for node in document.get('mechanisms', []) if isinstance(node, dict)], match_count=len(matches))
    # The local root means this exact node, never the whole system document.
    if local:
        try:
            pointer(local)
        except ValueError as error:
            raise AuthoringIRDiagnostic(str(error), operation_index=operation_index, path=local, stage=stage) from error
    return '/mechanisms/' + str(matches[0]) + local


def translate_operations(document, operations, *, stage):
    """Apply only explicit edits to an isolated JSON shadow, with precise errors."""
    current, translated, trace = clone(document), [], []
    for index, operation in enumerate(operations):
        path = resolve_address(current, operation, operation_index=index, stage=stage)
        if operation.get('selector') and operation['path'] == '' and operation['op'] == 'add':
            raise AuthoringIRDiagnostic('adding a whole mechanism requires an explicit full-document add',
                operation_index=index, path=path, stage=stage, **_owner(current, pointer(path)))
        _read(current, path, operation_index=index, stage=stage, allow_add=operation['op'] == 'add')
        edit = {k: clone(v) for k, v in operation.items() if k != 'selector'}
        edit['path'] = path
        trace.append({'operation_index': index, 'authored_path': operation['path'],
            'selector': clone(operation.get('selector')), 'translated_path': path, **_owner(current, pointer(path))})
        try:
            _edit(current, edit)
        except ValueError as error:
            raise AuthoringIRDiagnostic(str(error), operation_index=index, path=path, stage=stage,
                **_owner(current, pointer(path))) from error
        translated.append(edit)
    return current, translated, trace


def _operation_index(operations, path, identity):
    for index in reversed(range(len(operations))):
        operation = operations[index]
        value = operation.get('value')
        if (path == operation['path'] or path.startswith(operation['path'] + '/')
                or operation['path'].startswith(path + '/')):
            return index
        if (operation['path'].startswith('/mechanisms/') and isinstance(value, dict)
                and value.get('mechanism_id') == identity):
            return index
    return None


def _collection_failure(document, operations, *, stage):
    """Explain a previously rejected typed conversion; never add a new veto.

    Called only after the existing compiler fails. It reports existing model
    container contracts without repairing a value or executing any source.
    """
    def issue(value, path, expected):
        return AuthoringIRDiagnostic('system collection has the wrong JSON shape',
            operation_index=_operation_index(operations, path, None), path=path, stage=stage,
            expected_type=expected, actual_type=json_type(value),
            **_owner(document, pointer(path)))

    def objects(value, path):
        if not isinstance(value, list):
            return issue(value, path, 'array of objects')
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                return issue(item, path + '/' + str(index), 'object')
        return None

    for key in ('agent_types', 'artifact_types', 'mechanisms', 'connections', 'schedules'):
        if key in document:
            failure = objects(document[key], '/' + key)
            if failure is not None:
                return failure
    for index, node in enumerate(document.get('mechanisms', [])):
        for direction in ('inputs', 'outputs'):
            if direction in node:
                failure = objects(node[direction], '/mechanisms/' + str(index) + '/' + direction)
                if failure is not None:
                    return failure
    return None


def _tensor_attribute_failure(document, operations, *, stage):
    """Explain this exact existing rejection; never change validity or repair."""
    from utopia.system.tensor_program import ATTRS, IMPLEMENTATION, validate_tensor_program
    for index, owner in enumerate(document.get('mechanisms', [])):
        if not isinstance(owner, dict) or owner.get('implementation') != IMPLEMENTATION:
            continue
        parameters = owner.get('parameters')
        program = parameters.get('program') if isinstance(parameters, dict) else None
        try:
            validate_tensor_program(program)
        except ValueError as error:
            if str(error) != 'invalid tensor operation attributes':
                continue  # Preserve all other errors and their existing precedence.
        else:
            continue
        for node_index, node in enumerate(program['nodes']):
            attrs, op = node['attrs'], node['op']
            allowed = ATTRS.get(op, set())
            if not isinstance(attrs, dict) or not set(attrs) <= allowed:
                path = f'/mechanisms/{index}/parameters/program/nodes/{node_index}/attrs'
                return AuthoringIRDiagnostic('invalid tensor operation attributes',
                    stage=stage, path=path,
                    operation_index=_operation_index(operations, path, owner.get('mechanism_id')),
                    actual_owner_id=owner.get('mechanism_id'),
                    actual_owner_implementation=owner.get('implementation'),
                    tensor_node_id=node['id'], tensor_operation=op,
                    expected_type='object containing only the listed operation attributes',
                    actual_type=json_type(attrs), allowed_attribute_keys=sorted(allowed),
                    actual_attribute_keys=sorted(attrs) if isinstance(attrs, dict) else None)
    return None


def _literal_fields(document, operations, *, stage, image_id):
    """Check known code/schema ABI field types without changing any value."""
    from utopia.system.code_mechanisms import validate_code_artifact
    for index, outer in enumerate(document.get('mechanisms', [])):
        if not isinstance(outer, dict):
            continue
        node, prefix = outer, f'/mechanisms/{index}'
        if outer.get('implementation') == 'native.process.activity.v1':
            parameters = outer.get('parameters')
            node = parameters.get('delegate') if isinstance(parameters, dict) else None
            prefix += '/parameters/delegate'
        if not isinstance(node, dict) or node.get('implementation') != 'code.python.v1':
            continue
        owner = {**_owner(document, ['mechanisms', str(index)]),
            'executed_owner_id': node.get('mechanism_id'), 'executed_owner_implementation': node.get('implementation')}
        parameters = node.get('parameters', {})
        if not isinstance(parameters, dict):
            raise AuthoringIRDiagnostic('code mechanism parameters must be a literal JSON object',
                stage=stage, path=prefix + '/parameters', expected_type='object', actual_type=json_type(parameters), **owner)
        if parameters.get('runtime_image_id') != image_id:
            path = prefix + '/parameters/runtime_image_id'
            raise AuthoringIRDiagnostic('authored code runtime image differs from pinned operator sandbox',
                stage=stage, path=path, operation_index=_operation_index(operations, path, outer.get('mechanism_id')),
                expected_type='exact operator image identity', actual_type=json_type(parameters.get('runtime_image_id')),
                **owner)
        artifact = parameters.get('code_artifact')
        if not isinstance(artifact, dict):
            raise AuthoringIRDiagnostic('code artifact must be a literal JSON object',
                stage=stage, path=prefix + '/parameters/code_artifact', expected_type='object',
                actual_type=json_type(artifact), **owner)
        fields = [(field, artifact[field]) for field in ('source', 'inputs', 'outputs', 'state_schema') if field in artifact]
        for direction in ('inputs', 'outputs'):
            if isinstance(artifact.get(direction), dict):
                fields.extend((direction + '/' + _escape(port), artifact[direction][port])
                    for port in sorted(artifact[direction]))
        for field, value in fields:
            path = prefix + '/parameters/code_artifact/' + field
            expected = 'string' if field == 'source' else 'object'
            size = len(value.encode()) if isinstance(value, str) else None
            if json_type(value) != expected or field == 'source' and not 1 <= size <= 65_536:
                raise AuthoringIRDiagnostic('literal Python source must have 1..65536 UTF-8 bytes' if field == 'source'
                    else 'literal contract schema container must be a JSON object, not encoded text',
                    operation_index=_operation_index(operations, path, outer.get('mechanism_id')),
                    path=path, stage=stage, expected_type=expected,
                    actual_type=json_type(value), source_utf8_bytes=size if field == 'source' else None,
                    deepest_existing_prefix=path, **owner)
        try:
            validate_code_artifact(artifact)  # Parses AST/schema only; no generated code execution.
        except Exception as error:
            source_error = isinstance(error, SyntaxError) or str(error).startswith(('source ', 'step '))
            path = prefix + '/parameters/code_artifact' + ('/source' if source_error else '')
            raise AuthoringIRDiagnostic(str(error)[:2000], stage=stage, path=path,
                operation_index=_operation_index(operations, path, outer.get('mechanism_id')),
                source_line=getattr(error, 'lineno', None), source_column=getattr(error, 'offset', None),
                expected_type='valid literal Python source/step ABI' if source_error else 'valid literal code/schema artifact',
                actual_type=json_type(artifact.get('source')) if source_error else 'object',
                deepest_existing_prefix=path, **owner) from error


def path_catalog(document):
    """Declared structural/parameter summary; full parent remains in the prompt."""
    result = []
    def visit(value, parts, identity=None, implementation=None, local=None):
        item = {'path': _path(parts), 'type': json_type(value),
            'numeric_coordinate_eligible': type(value) in (int, float) and math.isfinite(value)}
        if identity is not None:
            item.update(mechanism_id=identity, implementation=implementation, local_path=_path(local or []))
        if isinstance(value, str):
            item['utf8_bytes'] = len(value.encode())
            item['role'] = 'literal-python-source' if parts[-2:] == ['code_artifact', 'source'] else 'text'
        if isinstance(value, dict):
            item['available_keys'] = sorted(value)
        elif isinstance(value, list):
            item['length'] = len(value)
        result.append(item)
        # These structures have their exact full bodies in parent_system. The
        # catalogue explicitly describes their container/type boundary instead
        # of duplicating every port, connection and schema-key address.
        structural_array = len(parts) == 1 and parts[0] not in ('initial_state', 'metadata')
        node_ports = identity is not None and parts[-1] in ('inputs', 'outputs') and isinstance(value, list)
        contract_schema = len(parts) >= 2 and parts[-2] == 'code_artifact' and parts[-1] in ('inputs', 'outputs', 'state_schema')
        if structural_array or node_ports or contract_schema:
            if isinstance(value, (dict, list)):
                item['children_in_full_parent_only'] = True
            return
        if isinstance(value, (dict, list)):
            for key, child in (((key, value[key]) for key in sorted(value))
                    if isinstance(value, dict) else enumerate(value)):
                visit(child, parts + [str(key)], identity, implementation,
                    (local + [str(key)]) if local is not None else None)
    for key in sorted(document):
        if key != 'mechanisms':
            visit(document[key], [key])
    for index, node in enumerate(document.get('mechanisms', [])):
        visit(node, ['mechanisms', str(index)], node.get('mechanism_id'), node.get('implementation'), [])
    def descriptor(item):
        if item.get('role') == 'literal-python-source':
            return {'type': 'string', 'role': 'literal-python-source', 'utf8_bytes': item['utf8_bytes'],
                'numeric_coordinate_eligible': False}
        return item['type']
    mechanisms = [{'mechanism_id': node['mechanism_id'], 'implementation': node['implementation'],
        'document_path': '/mechanisms/' + str(index),
        'fields': {item['local_path']: descriptor(item) for item in result
            if item.get('mechanism_id') == node['mechanism_id']}}
        for index, node in enumerate(document.get('mechanisms', []))]
    return {'schema': PROTOCOL + '.path-catalog', 'parent_sha256': digest(document),
        'mechanisms': mechanisms,
        'document_fields': {item['path']: descriptor(item) for item in result if 'mechanism_id' not in item},
        'encoding': 'mechanism fields map LOCAL pointer to JSON type or source descriptor; document_fields map FULL pointer to type',
        'coordinate_rule': 'finite numeric current field in every reachable structure; never source/text/boolean',
        'enumeration_policy': 'all mechanisms and their parameter fields; recursive initial_state/metadata; structural arrays, node ports and code-contract schemas summarized as exact typed containers',
        'nonexpanded_children': ['global structural arrays', 'node input/output port declarations', 'code-artifact input/output/state schema internals'],
        'full_parent_retained': True, 'size_based_truncation': False,
        'scope': 'describes current parent; no institution whitelist'}


def _failed_ir_receipt(item):
    raw = item.get('raw_ir')
    operations = []
    if isinstance(raw, dict):
        groups = [('base', raw.get('operations', []))]
        for factor in raw.get('factors', []) if isinstance(raw.get('factors'), list) else []:
            if isinstance(factor, dict):
                for choice in factor.get('choices', []) if isinstance(factor.get('choices'), list) else []:
                    if isinstance(choice, dict):
                        groups.append(('factor:' + str(factor.get('id')) + '/choice:' + str(choice.get('id')),
                            choice.get('operations', [])))
        for stage, edits in groups:
            for index, operation in enumerate(edits if isinstance(edits, list) else []):
                if not isinstance(operation, dict):
                    operations.append({'stage': stage, 'operation_index': index,
                        'raw_operation_sha256': digest(operation), 'actual_type': json_type(operation)})
                    continue
                receipt = {'stage': stage, 'operation_index': index, 'raw_operation_sha256': digest(operation),
                    **{key: clone(operation[key]) for key in ('op', 'path', 'selector') if key in operation}}
                if 'value' in operation:
                    value = operation['value']
                    receipt['literal_operand'] = {'type': json_type(value), 'sha256': digest(value),
                        'json_utf8_bytes': len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode())}
                operations.append(receipt)
    return {**{key: clone(item.get(key)) for key in ('attempt', 'status', 'started_sha256', 'completed_sha256')},
        'raw_ir_available': raw is not None,
        'raw_ir_sha256': digest(raw) if raw is not None else item.get('raw_ir_sha256'),
        'operation_receipts': operations,
        'continuous': clone(raw.get('continuous')) if isinstance(raw, dict) else None,
        'technical_errors': clone(item.get('technical_errors', []))}


def detailed_failure_history(request):
    """Own archived failures only; exact operand bodies stay in the raw archive."""
    failures = []
    for index, record in enumerate(request.get('history', [])):
        definition = record.get('definition')
        failure = definition.get('generation_failure') if isinstance(definition, dict) else None
        if not isinstance(failure, dict):
            continue
        failures.append({'history_index': index, 'stage': record.get('stage'),
            'campaign_generation_error': clone(record.get('generation_error')),
            'request_sha256': failure.get('request_sha256'),
            'technical_errors': clone(failure.get('technical_errors', [])),
            'failed_ir_receipts': [_failed_ir_receipt(item) for item in failure.get('attempt_evidence', [])]})
    return failures


class StableIDAuthoringProtocol:
    """Optional trusted protocol for LLMVocabularyGenerator; legacy stays usable."""
    output_schema = OUTPUT_SCHEMA

    def instructions(self):
        from .native_search_generator_v14 import INSTRUCTIONS as legacy
        old = ('operations is one atomic add/remove/replace JSON-pointer transaction on the full\n'
            'parent SystemSpec below. Values and Python source must be complete, literal JSON.\n'
            'Array indices refer to the document after preceding edits. An empty operations\n'
            'array means explicit retention.')
        new = ('operations is one atomic add/remove/replace transaction. Prefer exact mechanism_id\n'
            'selectors with mechanism-local JSON pointers. Alternatively omit selector and use\n'
            'full-document JSON pointers. Both resolve after preceding explicit edits.\n'
            'Values/source are complete literal JSON; [] means explicit retention.')
        if old not in legacy:
            raise ValueError('legacy authoring address instructions changed; stable protocol needs explicit revision')
        return legacy.replace(old, new, 1) + '\n' + INSTRUCTIONS

    def binding(self):
        from . import native_search_generator_v14 as legacy
        return {'schema': PROTOCOL, 'version': 1, 'compiler': 'exact-stable-id-to-atomic-json-patch',
            'compiler_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'legacy_adapter_source_sha256': hashlib.sha256(Path(legacy.__file__).read_bytes()).hexdigest(),
            'output_schema_sha256': digest(self.output_schema),
            'instructions_sha256': digest(self.instructions()),
            'branch_policy': 'reject branch-dependent translated pointers; never guess semantic transport'}

    def build_prompt(self, request, *, image_id, errors):
        from .native_search_generator_v14 import build_prompt
        prompt = json.loads(build_prompt(request, image_id=image_id, errors=errors))
        prompt.update(instructions=self.instructions(),
            response_schema=clone(self.output_schema), authoring_protocol=self.binding(),
            parent_path_catalog=path_catalog(request['parent_system']))
        prompt['own_history']['generation_authoring_failures'] = detailed_failure_history(request)
        prompt['prompt_view_metadata'] = {'schema': PROTOCOL + '.prompt-view',
            'included': ['full current parent', 'all own scalar observations/null failures/updates',
                'all own archived generation technical errors', 'available exact failed-IR and operation receipt hashes'],
            'omitted_fields': [
                {'field': 'previous observed candidate bodies', 'representation': 'fingerprints; exact bodies in archived request'},
                {'field': 'previous failed-IR fields other than operation addresses and coordinate declarations, including literal operands and rationales',
                    'representation': 'exact operand/operation/IR hashes and byte/type descriptors; exact bodies in archived generation failure and author journal'},
                {'field': 'previous raw provider messages and transport bodies', 'representation': 'committed receipt hashes; exact bodies in author journal'}],
            'catalogue_nonexpanded_fields': ['global structural arrays', 'node input/output port declarations',
                'code-artifact input/output/state schema internals; exact children remain in full parent_system'],
            'other_arm_data_included': False, 'silent_truncation': False}
        return json.dumps(prompt, ensure_ascii=False, sort_keys=True, allow_nan=False)

    def compile(self, request, output, *, binding_sha256, provider_binding):
        from .native_search_generator_v14 import compile_authored_output
        errors = list(Draft202012Validator(self.output_schema).iter_errors(output))
        if errors:
            error = errors[0]
            raise AuthoringIRDiagnostic('authoring IR schema: ' + error.message[:2000],
                stage='output-schema', path=error.json_path, expected_type='strict authoring IR object',
                actual_type=json_type(error.instance))
        try:
            digest(output)  # Reject nonfinite values before any compiler provenance.
        except (ValueError, TypeError, OverflowError) as error:
            raise AuthoringIRDiagnostic('authoring IR must be finite strict JSON', stage='output-schema') from error
        for index, coordinate in enumerate(output['continuous']):
            try:
                finite = all(math.isfinite(coordinate[k]) for k in ('lower', 'upper', 'mean', 'sigma'))
                valid = finite and coordinate['lower'] < coordinate['upper'] and coordinate['sigma'] > 0
            except OverflowError:
                valid = False
            if not valid:
                raise AuthoringIRDiagnostic('continuous settings require finite lower<upper, finite mean and positive finite sigma',
                    operation_index=index, path=coordinate['path'], stage='continuous-settings',
                    coordinate_id=coordinate['id'], expected_type='finite ordered bounds/mean and positive finite sigma')
        parent = SystemSpec.from_dict(request['parent_system'])
        base_document, base_operations, base_trace = translate_operations(parent.to_dict(), output['operations'], stage='base')
        try:
            _literal_fields(base_document, base_operations, stage='base', image_id=provider_binding['image_id'])
            base = _apply_or_identity(parent, make_patch(parent, base_operations, rationale=output['rationale'])
                if base_operations else None)
        except AuthoringIRDiagnostic:
            raise  # Preserve more specific source/ABI/literal diagnostics.
        except Exception as error:
            failure = _collection_failure(base_document, base_operations, stage='base-final-transaction')
            if failure is None and str(error) == 'invalid tensor operation attributes':
                failure = _tensor_attribute_failure(base_document, base_operations, stage='base-final-transaction')
            if failure is not None:
                raise failure from error
            raise AuthoringIRDiagnostic(str(error), stage='base-final-transaction') from error
        translated = clone(output)
        translated['operations'] = base_operations
        factors = clone(output['factors'])
        skeleton = clone(factors)
        for factor in skeleton:
            for choice in factor['choices']:
                choice['operations'] = []
        try:
            assignments = (NativeFactorizedDesignSearch(base, skeleton, loss_spec=request['loss_spec'],
                design_provenance={'kind': 'stable-ID-address-preflight'}, seed=request.get('rng_seed', 42),
                logits=output.get('logits')).assignments if skeleton else [{}])
        except Exception as error:
            raise AuthoringIRDiagnostic(str(error), stage='declared-factor-support',
                **getattr(error, 'details', {})) from error
        choice_edits, factor_trace, coordinate_paths, coordinate_trace = {}, {}, {}, {}
        for assignment in assignments:
            document, assignment_edits = clone(base_document), []
            for factor in factors:
                choice = next(c for c in factor['choices'] if c['id'] == assignment[factor['id']])
                key = (factor['id'], choice['id'])
                document, edits, trace = translate_operations(document, choice['operations'],
                    stage='factor:' + factor['id'] + '/choice:' + choice['id'])
                if key in choice_edits and choice_edits[key] != edits:
                    changed = next(i for i, (before, after) in enumerate(zip(choice_edits[key], edits))
                        if before != after)
                    raise AuthoringIRDiagnostic('branch-dependent pointer for one factor choice is unsupported; author explicit conditional edits',
                        stage='factor-address-stability', factor_id=factor['id'], choice_id=choice['id'],
                        operation_index=changed, path=edits[changed]['path'],
                        assignment=assignment, previous_paths=[o['path'] for o in choice_edits[key]],
                        translated_paths=[o['path'] for o in edits])
                choice_edits[key], factor_trace[key] = edits, trace
                assignment_edits.extend(edits)
            _literal_fields(document, assignment_edits, stage='factor-assignment', image_id=provider_binding['image_id'])
            for index, coordinate in enumerate(output['continuous']):
                path = resolve_address(document, coordinate, operation_index=index, stage='continuous')
                value = _read(document, path, operation_index=index, stage='continuous')
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise AuthoringIRDiagnostic('continuous coordinate requires an existing finite numeric field, never source/text/boolean',
                        operation_index=index, path=path, stage='continuous', coordinate_id=coordinate['id'],
                        expected_type='finite number', actual_type=json_type(value), deepest_existing_prefix=path,
                        **_owner(document, pointer(path)))
                if index in coordinate_paths and coordinate_paths[index] != path:
                    raise AuthoringIRDiagnostic('branch-dependent pointer for a continuous coordinate is unsupported; no implicit transport',
                        operation_index=index, path=path, stage='continuous-address-stability',
                        coordinate_id=coordinate['id'], previous_path=coordinate_paths[index], assignment=assignment,
                        **_owner(document, pointer(path)))
                coordinate_paths[index] = path
                coordinate_trace[index] = {'coordinate_index': index, 'authored_path': coordinate['path'],
                    'selector': clone(coordinate.get('selector')), 'translated_path': path, 'actual_type': json_type(value)}
        # Explicitly unreachable choices remain declared. Their addresses must
        # still have a literal base translation; no new reachable support is made.
        for factor in factors:
            for choice in factor['choices']:
                key = (factor['id'], choice['id'])
                if key not in choice_edits:
                    _, choice_edits[key], factor_trace[key] = translate_operations(base_document,
                        choice['operations'], stage='unreachable-choice:' + factor['id'] + '/' + choice['id'])
                choice['operations'] = choice_edits[key]
        translated['factors'] = factors
        translated['continuous'] = [{**{k: clone(v) for k, v in coordinate.items() if k != 'selector'},
            'path': coordinate_paths[index]} for index, coordinate in enumerate(output['continuous'])]
        try:
            definition = compile_authored_output(request, translated, binding_sha256=binding_sha256,
                provider_binding=provider_binding)
        except Exception as error:
            raise AuthoringIRDiagnostic(str(error), stage='legacy-final-vocabulary-validation') from error
        definition['provenance']['authoring_compiler'] = {'schema': TRACE, 'protocol': self.binding(),
            'raw_ir': clone(output), 'raw_ir_sha256': digest(output),
            'translated_output': clone(translated), 'translated_output_sha256': digest(translated),
            'base_operation_map': base_trace,
            'factor_operation_map': [{'factor_id': k[0], 'choice_id': k[1], 'operations': v}
                for k, v in factor_trace.items()],
            'continuous_map': list(coordinate_trace.values()), 'reachable_assignments_checked': len(assignments),
            'source_execution_on_host': False, 'implicit_source_or_wire_repairs': False,
            'support_filtering': False}
        return definition
