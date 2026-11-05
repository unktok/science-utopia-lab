"""Exact field-name addressing, not policy selection or failed-path repair."""
from collections import defaultdict

from utopia.optimization.native_authoring_ir import AuthoringIRDiagnostic, _read, resolve_address
from utopia.system.design_patch import clone

FIELD_RULE = ('field_name matches one exact literal JSON key inside this exact mechanism; '
    'dots and slashes are literal key characters, not path navigation. Missing or ambiguous names reject. '
    'For an explicit document-root JSON pointer, use edit with operations containing op/path/value '
    'and no selector, or inspect with path. Never place that pointer in field_name.')


def _fields(value, prefix=''):
    if isinstance(value, dict):
        for key in sorted(value):
            path = prefix + '/' + key.replace('~', '~0').replace('/', '~1')
            yield key, path
            yield from _fields(value[key], path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _fields(item, prefix + '/' + str(index))


def field_index(node):
    """List all literal field names, not a catalogue of institutional policies."""
    matches = defaultdict(list)
    for name, path in _fields(node):
        matches[name].append(path)
    return {'unique_field_names': sorted(name for name in matches if len(matches[name]) == 1),
        'ambiguous_field_names': {name: len(matches[name]) for name in sorted(matches) if len(matches[name]) > 1}}


def resolve_field(document, mechanism_id, field_name):
    root = resolve_address(document, {'selector': {'mechanism_id': mechanism_id}, 'path': ''},
        stage='staged-field-owner')
    node = _read(document, root, stage='staged-field-owner')
    paths = [path for name, path in _fields(node) if name == field_name]
    if len(paths) != 1:
        raise AuthoringIRDiagnostic('field name is missing or ambiguous; no field was chosen',
            stage='staged-field-name', path=root, actual_owner_id=mechanism_id,
            actual_owner_implementation=node.get('implementation') if isinstance(node, dict) else None,
            field_addressing_rule=FIELD_RULE,
            field_name=field_name, match_count=len(paths),
            matching_field_paths=[root + path for path in paths])
    return {'mechanism_id': mechanism_id, 'field_name': field_name,
        'relative_path': paths[0], 'root_path': root + paths[0],
        'resolution': 'exact unique JSON field name; no fuzzy matching or source repair'}


def field_operations(document, mechanism_id, updates):
    """Resolve all existing fields before applying any literal replacement."""
    resolutions = [resolve_field(document, mechanism_id, update['field_name']) for update in updates]
    operations = [{'op': 'replace', 'path': item['root_path'], 'value': clone(update['value'])}
        for item, update in zip(resolutions, updates)]
    return operations, resolutions
