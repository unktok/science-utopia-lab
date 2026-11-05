"""Read-only literal editing context, never an invented or repaired institution."""
import json

from utopia.system.design_patch import clone, digest

MAX_LITERAL_BYTES = 65536
MAX_ENTRY_BYTES = 16384


def literal_workbench(state):
    """Index every current node/root field, with exact bounded literal bodies.

    Root addresses are literal JSON pointers, not model-authored free-text plan
    targets. Both bodies and pointers come from the current draft, including
    after intermediate invalid graph edits. Large bodies keep explicit omission
    descriptors and remain available through unrestricted inspect calls.
    """
    document = state['document']
    used = 0

    def entry(path, value):
        nonlocal used
        size = len(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode())
        result = {'address': {'path': path}, 'value_sha256': digest(value), 'literal_utf8_bytes': size}
        if size <= MAX_ENTRY_BYTES and used + size <= MAX_LITERAL_BYTES:
            result.update(value_included=True, value=clone(value))
            used += size
        else:
            result.update(value_included=False,
                omission='Explicit per-entry or aggregate literal byte cap; inspect this exact root address.')
        return result

    nodes = document.get('mechanisms')
    entries = []
    if isinstance(nodes, list):
        for index, node in enumerate(nodes):
            path = '/mechanisms/' + str(index)
            item = entry(path, node)
            if isinstance(node, dict):
                item['mechanism_id'] = clone(node.get('mechanism_id'))
                parameters = node.get('parameters')
                artifact = parameters.get('code_artifact') if isinstance(parameters, dict) else None
                if isinstance(artifact, dict) and isinstance(artifact.get('source'), str):
                    item['source_address'] = {'path': path + '/parameters/code_artifact/source'}
            entries.append(item)
    # Dictionary insertion order may change when exact request JSON is saved
    # with sorted keys. Canonicalize entry order so cold reconstruction is the
    # same prompt, including after capped entries consume the inline budget.
    root_fields = [entry('/' + key.replace('~', '~0').replace('/', '~1'), document[key])
        for key in sorted(document) if key != 'mechanisms']
    if not isinstance(nodes, list) and 'mechanisms' in document:
        root_fields.append(entry('/mechanisms', nodes))
    return {'schema': 'scienceutopia.literal-editor-workbench.v27',
        'scope': 'Observed current draft only, not a supplied candidate or a measured improvement.',
        'document_sha256': digest(document), 'nodes': entries, 'root_fields': root_fields,
        'all_current_nodes_indexed': True, 'all_current_root_fields_indexed': True,
        'literal_bytes_included': used, 'literal_byte_cap': MAX_LITERAL_BYTES,
        'per_entry_byte_cap': MAX_ENTRY_BYTES, 'silent_size_truncation': False,
        'address_rule': 'Each address is one complete document-root form. Do not add a mechanism selector. '
            'Free-text plan targets are not JSON pointers unless verified against these literal values.'}
