"""A virtual editor view of the actual SystemSpec; never host filesystem access.

File names identify literal draft locations, not programs to run. Python source
is passed through verbatim. JSON files are parsed strictly and translated into
ordinary explicit atomic design edits; there are no authored policies here.
"""
import hashlib
import json
from collections import Counter
from urllib.parse import quote

from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json


def _pointer(key):
    return '/' + key.replace('~', '~0').replace('/', '~1')


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)


def _entries(document):
    """Derive current literal locations afresh; no name/path inference or cache."""
    entries = {'system.json': {'format': 'json-system', 'value': document, 'path': None}}
    for key, value in document.items():
        entries['system/' + quote(key, safe='._-') + '.json'] = {
            'format': 'json-value', 'value': value, 'path': _pointer(key)}
    nodes = document.get('mechanisms', [])
    if not isinstance(nodes, list):
        return entries, []
    counts = Counter(n.get('mechanism_id') for n in nodes
        if isinstance(n, dict) and isinstance(n.get('mechanism_id'), str))
    ambiguous = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or not isinstance(node.get('mechanism_id'), str):
            continue  # The full system/root array file still exposes malformed nodes.
        identity = node['mechanism_id']
        if counts[identity] != 1:
            if identity not in ambiguous:
                ambiguous.append(identity)
            continue
        token = quote(identity, safe='._-')
        path = '/mechanisms/' + str(index)
        meta = {'mechanism_id': identity, 'implementation': node.get('implementation')}
        entries['nodes/' + token + '.json'] = {
            **meta, 'format': 'json-value', 'value': node, 'path': path}
        parameters = node.get('parameters')
        artifact = parameters.get('code_artifact') if isinstance(parameters, dict) else None
        if isinstance(artifact, dict) and isinstance(artifact.get('source'), str):
            entries['code/' + token + '.py'] = {
                **meta, 'format': 'python-source', 'value': artifact['source'],
                'path': path + '/parameters/code_artifact/source'}
    return entries, sorted(ambiguous)


def _text(entry):
    return entry['value'] if entry['format'] == 'python-source' else _json(entry['value'])


def file_catalog(document):
    entries, ambiguous = _entries(document)
    files = []
    for name, entry in sorted(entries.items()):
        content = _text(entry)
        files.append({'filename': name,
            **{k: entry[k] for k in ('format', 'mechanism_id', 'implementation') if k in entry},
            'content_utf8_bytes': len(content.encode('utf-8'))})
    return {'schema': 'scienceutopia.virtual-editor-workspace.v35',
        'scope': 'Current actual draft only; virtual files, never OS paths or executed code.',
        'files': files, 'all_file_names_included': True,
        'ambiguous_node_ids_without_aliases': ambiguous,
        'omitted_bodies': 'All bodies are available through read_file; full system.json includes every draft field.',
        'writes': 'Literal complete replacement, not merge. Code files replace only source and preserve all other fields. '
            'Node JSON replaces the whole node; system JSON/root files can change arbitrary graph structure. '
            'new/<URL-encoded-exact-mechanism-id>.json appends your complete authored node; no boilerplate is supplied.',
        'source_execution_on_host': False}


def read_file(document, filename, *, offset=0, limit=65536):
    if not isinstance(filename, str):
        raise ValueError('filename must be a literal string')
    entries, _ = _entries(document)
    if filename not in entries:
        raise ValueError('unknown exact virtual filename; inspect the current file catalog')
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 65536:
        raise ValueError('file slice requires nonnegative character offset and limit1..65536')
    text = _text(entries[filename])
    if offset > len(text):
        raise ValueError('virtual file offset exceeds exact character length')
    return {'filename': filename, 'format': entries[filename]['format'],
        'content': text[offset:offset + limit], 'offset': offset,
        'complete': offset == 0 and len(text) <= limit,
        'slice_reaches_end': offset + limit >= len(text), 'total_characters': len(text),
        'total_utf8_bytes': len(text.encode('utf-8')),
        'content_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'scope': 'Literal current draft text; not a host file, instruction or execution result.'}


def write_file_operations(document, filename, content):
    """Return exact ordinary edits. The caller applies/validates them as before."""
    if not isinstance(filename, str) or not isinstance(content, str):
        raise ValueError('filename and content must be literal strings')
    entries, _ = _entries(document)
    if filename not in entries:
        # Creation is an explicit author-selected new node, never a filled-in
        # institution template or implicit creation of a missing source owner.
        if not filename.startswith('new/') or not filename.endswith('.json'):
            raise ValueError('unknown exact virtual filename; no OS file is read or created')
        node = decode_json(content, strict=True, finite_floats=True)
        if not isinstance(node, dict) or not isinstance(node.get('mechanism_id'), str):
            raise ValueError('new node JSON must contain its authored mechanism_id')
        if filename != 'new/' + quote(node['mechanism_id'], safe='._-') + '.json':
            raise ValueError('new filename must exactly encode its authored mechanism_id')
        nodes = document.get('mechanisms')
        if not isinstance(nodes, list) or any(isinstance(n, dict) and n.get('mechanism_id') == node['mechanism_id'] for n in nodes):
            raise ValueError('new node ID already exists or mechanisms is not an array')
        return [{'op': 'add', 'path': '/mechanisms/-', 'value': node}]
    entry = entries[filename]
    value = content if entry['format'] == 'python-source' else decode_json(content, strict=True, finite_floats=True)
    if entry['format'] != 'json-system':
        return [{'op': 'replace', 'path': entry['path'], 'value': value}]
    if not isinstance(value, dict):
        raise ValueError('system.json must be a complete authored JSON object')
    # Existing editor uses non-root JSON pointers. Enumerate all root changes
    # explicitly, without retaining omitted fields or merging nested values.
    return ([{'op': 'remove', 'path': _pointer(k)} for k in sorted(set(document) - set(value))]
        + [{'op': 'replace' if k in document else 'add', 'path': _pointer(k), 'value': clone(value[k])}
           for k in sorted(value) if k not in document or digest(value[k]) != digest(document[k])])
