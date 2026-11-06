"""Exact field-name addressing, not policy selection or failed-path repair."""
from collections import defaultdict
import json

from utopia.optimization.native_authoring_ir import AuthoringIRDiagnostic, _read, resolve_address
from utopia.system.design_patch import clone

FIELD_RULE = ('field_name matches one exact literal JSON key inside this exact mechanism; '
    'dots and slashes are literal key characters, not path navigation. Missing or ambiguous names reject. '
    'For an explicit document-root JSON pointer, use edit with operations containing op/path/value '
    'and no selector, or inspect with path. Never place that pointer in field_name.')
MAX_FEEDBACK_NAMES = 64
MAX_FEEDBACK_NAME_BYTES = 2048


def _bounded_names(names, *, limit=MAX_FEEDBACK_NAMES, byte_limit=MAX_FEEDBACK_NAME_BYTES):
    """Whole literal names only; never turn a truncated name into an address."""
    included, used = [], 0
    for name in names:
        size = len(json.dumps(name, ensure_ascii=False).encode('utf-8'))
        if len(included) < limit and used + size <= byte_limit:
            included.append(name)
            used += size
    return included


def field_failure_catalog(node):
    """Observed names, not guessed corrections, replacement values or a policy menu."""
    index = field_index(node)
    all_names = sorted([*index['unique_field_names'], *index['ambiguous_field_names']])
    names = _bounded_names(all_names)
    selected = set(names)
    omitted = len(all_names) - len(names)
    return {'scope': 'Actual literal keys inside this exact current node; no field/value was chosen or repaired.',
        'usage': 'Copy one exact literal name; any dots/slashes in it are literal characters, not navigation.',
        'unique_field_names': [name for name in index['unique_field_names'] if name in selected],
        'ambiguous_field_names': {name: count for name, count in index['ambiguous_field_names'].items()
            if name in selected},
        'total_name_count': len(all_names), 'included_name_count': len(names),
        'omitted_name_count': omitted, 'complete': omitted == 0,
        'limits': {'names': MAX_FEEDBACK_NAMES, 'encoded_name_utf8_bytes': MAX_FEEDBACK_NAME_BYTES},
        'omission': ('Whole literal names exceeding explicit count/byte caps are omitted; '
            'inspect the current node for its full keys. Omitted fields remain addressable.' if omitted else None)}


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
            observed_field_name_catalog=field_failure_catalog(node),
            field_name=field_name, match_count=len(paths),
            matching_field_paths=[root + path for path in paths])
    return {'mechanism_id': mechanism_id, 'field_name': field_name,
        'relative_path': paths[0], 'root_path': root + paths[0],
        'resolution': 'exact unique JSON field name; no fuzzy matching or source repair'}


def field_operations(document, mechanism_id, updates):
    """Resolve all existing fields before applying any literal replacement."""
    resolutions = []
    for index, update in enumerate(updates):
        try:
            resolutions.append(resolve_field(document, mechanism_id, update['field_name']))
        except AuthoringIRDiagnostic as error:
            prior = [item['field_name'] for item in resolutions]
            included = _bounded_names(prior, limit=8, byte_limit=512)
            for diagnostic in error.diagnostics:
                diagnostic.update(failed_field_update_index=index, field_updates_applied=0,
                    field_update_transaction='atomic; no supplied update was applied',
                    successfully_resolved_prior_update_count=len(resolutions),
                    resolved_prior_field_names=included,
                    omitted_prior_field_name_count=len(prior) - len(included))
            raise
    operations = [{'op': 'replace', 'path': item['root_path'], 'value': clone(update['value'])}
        for item, update in zip(resolutions, updates)]
    return operations, resolutions
