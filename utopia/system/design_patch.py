"""Atomic source/protocol/wiring edits to a SystemSpec, not a mechanism menu."""
from __future__ import annotations

import hashlib
import json

from .model import SystemSpec
from .validation import validate_system_spec

PATCH_SCHEMA = 'scienceutopia.system-design-patch.v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def clone(value):
    return json.loads(json.dumps(value, allow_nan=False))


def pointer(path):
    if not isinstance(path, str) or not path.startswith('/') or path == '/':
        raise ValueError('patch path must be a non-root JSON pointer')
    parts = path[1:].split('/')
    for part in parts:
        # Accept only RFC-style escapes; never silently reinterpret a typo.
        remainder = part.replace('~1', '').replace('~0', '')
        if '~' in remainder:
            raise ValueError('invalid JSON pointer escape')
    return [p.replace('~1', '/').replace('~0', '~') for p in parts]


def _index(value, key, *, append=False):
    if isinstance(value, list):
        if key == '-' and append:
            return len(value)
        if not key.isdecimal() or (len(key) > 1 and key.startswith('0')):
            raise ValueError('array path requires a canonical nonnegative index')
        index = int(key)
        if not 0 <= index < len(value) + int(append):
            raise ValueError('array path index out of range')
        return index
    if not isinstance(value, dict):
        raise ValueError('patch path traverses a scalar')
    return key


def read_pointer(value, path):
    for part in pointer(path):
        value = value[_index(value, part)]
    return value


def _edit(document, operation):
    if not isinstance(operation, dict) or operation.get('op') not in {'add', 'remove', 'replace'}:
        raise ValueError('unsupported design edit')
    action = operation['op']
    if set(operation) != ({'op', 'path'} if action == 'remove' else {'op', 'path', 'value'}):
        raise ValueError('invalid design edit fields')
    parts = pointer(operation['path'])
    owner = document
    try:
        for part in parts[:-1]:
            owner = owner[_index(owner, part)]
        key = _index(owner, parts[-1], append=action == 'add')
        if action == 'remove':
            del owner[key]
        elif isinstance(owner, list) and action == 'add':
            owner.insert(key, clone(operation['value']))
        else:
            if isinstance(owner, dict) and action == 'replace' and key not in owner:
                raise ValueError('replace path does not exist')
            owner[key] = clone(operation['value'])
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError('design patch path does not exist') from error


def make_patch(parent, operations, *, rationale=''):
    return {'schema': PATCH_SCHEMA, 'parent_fingerprint': parent.fingerprint,
            'operations': clone(operations), 'rationale': rationale}


def apply_design_patch(parent: SystemSpec, patch: dict):
    """Validate only the finished edit transaction: protocols may change jointly.

    The parent is immutable. Structural validity is not scientific usefulness;
    unimplemented host capabilities still fail at execution, not via a catalog.
    """
    if (not isinstance(patch, dict) or set(patch) != {
            'schema', 'parent_fingerprint', 'operations', 'rationale'}
            or patch['schema'] != PATCH_SCHEMA or patch['parent_fingerprint'] != parent.fingerprint
            or not isinstance(patch['operations'], list) or not 1 <= len(patch['operations']) <= 256
            or not isinstance(patch['rationale'], str)):
        raise ValueError('design patch schema/parent/operations mismatch')
    if len(json.dumps(patch, allow_nan=False).encode()) > 2_097_152:
        raise ValueError('design patch exceeds size limit')
    document = clone(parent.to_dict())
    for operation in patch['operations']:
        _edit(document, operation)
    candidate = SystemSpec.from_dict(document)
    if candidate.to_dict() != document:
        raise ValueError('design edit has unknown or noncanonical SystemSpec fields')
    validate_system_spec(candidate).require_valid()
    from .code_mechanisms import CODE_IMPLEMENTATION, validate_code_artifact
    for node in candidate.mechanisms:
        if node.implementation == CODE_IMPLEMENTATION:
            artifact = node.parameters.get('code_artifact')
            validate_code_artifact(artifact)
            if (set(artifact['inputs']) != {p.port_id for p in node.inputs}
                    or set(artifact['outputs']) != {p.port_id for p in node.outputs}):
                raise ValueError('code artifact and edited graph ports differ')
    if candidate.fingerprint == parent.fingerprint:
        raise ValueError('design edit is a no-op')
    return candidate


def design_difference(parent, candidate):
    before = {n['mechanism_id']: n for n in parent.to_dict()['mechanisms']}
    after = {n['mechanism_id']: n for n in candidate.to_dict()['mechanisms']}
    return {'parent_fingerprint': parent.fingerprint, 'candidate_fingerprint': candidate.fingerprint,
            'nodes_added': sorted(after.keys() - before.keys()),
            'nodes_removed': sorted(before.keys() - after.keys()),
            'nodes_changed': sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
            'connections_before': parent.to_dict()['connections'],
            'connections_after': candidate.to_dict()['connections'],
            'schedules_before': parent.to_dict()['schedules'],
            'schedules_after': candidate.to_dict()['schedules']}
