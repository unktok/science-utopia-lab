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


def _entries(document, request=None, *, conversation_profile='hermes-function-history-v26', session_steps=None):
    """Derive current literal locations afresh; no name/path inference or cache."""
    entries = {'system.json': {'format': 'json-system', 'value': document, 'path': None}}
    from .native_designer_tools_v25 import tool_specifications
    from utopia.system.native_capability_catalog import native_capability_catalog
    entries.update({
        'reference/tools.json': {'format': 'json-reference', 'read_only': True,
            'value': tool_specifications(conversation_profile=conversation_profile), 'path': None},
        'reference/capabilities.json': {'format': 'json-reference', 'read_only': True,
            'value': native_capability_catalog(), 'path': None}})
    for key, value in document.items():
        entries['system/' + quote(key, safe='._-') + '.json'] = {
            'format': 'json-value', 'value': value, 'path': _pointer(key)}
    nodes = document.get('mechanisms', [])
    if not isinstance(nodes, list):
        nodes = []  # Root files and own history remain readable in an invalid draft.
    counts = Counter(n.get('mechanism_id') for n in nodes
        if isinstance(n, dict) and isinstance(n.get('mechanism_id'), str))
    ambiguous = []
    for index, node in enumerate(nodes):
        # Every literal position remains addressable even in an intermediate
        # graph with duplicate/missing IDs. Names are exact catalog entries,
        # not fuzzy ID resolution or automatic selection among duplicates.
        path = '/mechanisms/' + str(index)
        entries['positions/' + str(index) + '.json'] = {
            'format': 'json-value', 'value': node, 'path': path,
            **({'mechanism_id': node.get('mechanism_id'), 'implementation': node.get('implementation')}
                if isinstance(node, dict) else {})}
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
    if request is not None:
        from .native_designer_tools_v25 import BOUNDED_AUTHORING
        if conversation_profile == BOUNDED_AUTHORING:
            from .native_bounded_author_context_v45 import archive_entries
            entries.update(archive_entries(request, session_steps or []))
        from .native_history_workspace_v37 import history_entries
        entries.update(history_entries(request, _entries))
        parent = request.get('parent_system')
        if isinstance(parent, dict):
            originals, _ = _entries(parent)
            for filename, entry in originals.items():
                if filename.startswith('reference/'):
                    continue
                entries['parent/' + filename] = {**entry, 'path': None, 'read_only': True,
                    'source_kind': 'request-parent', 'parent_system_sha256': digest(parent)}
    return entries, sorted(ambiguous)


def _text(entry):
    return entry['value'] if entry['format'] == 'python-source' else _json(entry['value'])


def file_catalog(document, *, request=None, conversation_profile='hermes-function-history-v26', session_steps=None):
    entries, ambiguous = _entries(document, request, conversation_profile=conversation_profile, session_steps=session_steps)
    files = []
    deferred = 0
    for name, entry in sorted(entries.items()):
        if ((name.startswith('history/') and name != 'history/index.json')
                or (name.startswith('archive/') and name != 'archive/index.json')):
            deferred += 1
            continue
        content = _text(entry)
        files.append({'filename': name,
            **{k: entry[k] for k in ('format', 'mechanism_id', 'implementation', 'source_kind') if k in entry},
            'read_only': entry.get('read_only', False),
            'content_utf8_bytes': len(content.encode('utf-8'))})
    return {'schema': 'scienceutopia.virtual-editor-workspace.v35',
        'scope': 'Current draft, explicit source API references and on-demand own-history files; never OS paths or executed code.',
        'files': files, 'all_file_names_included': deferred == 0,
        'all_current_draft_names_included': True,
        'deferred_archive_names': {'count': deferred,
            'complete_index_filename': 'history/index.json' if deferred else None,
            'reason': 'Archive filenames are explicitly indexed on demand, not silently truncated.'},
        'ambiguous_node_ids_without_aliases': ambiguous,
        'ambiguous_ids_have_explicit_positional_aliases': True,
        'omitted_bodies': 'All bodies are available through read_file; full system.json includes every draft field.',
        'writes': 'Literal complete replacement, not merge. Code files replace only source and preserve all other fields. '
            'Node JSON replaces the whole node; system JSON/root files can change arbitrary graph structure. '
            'new/<URL-encoded-exact-mechanism-id>.json appends your complete authored node; no boilerplate is supplied.',
        'source_execution_on_host': False}


def read_file(document, filename, *, offset=0, limit=65536, request=None,
              conversation_profile='hermes-function-history-v26', session_steps=None):
    if not isinstance(filename, str):
        raise ValueError('filename must be a literal string')
    entries, _ = _entries(document, request, conversation_profile=conversation_profile, session_steps=session_steps)
    if filename not in entries:
        raise ValueError(_missing_name(document, filename,
            'unknown exact virtual filename; inspect the current file catalog'))
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 65536:
        raise ValueError('file slice requires nonnegative character offset and limit1..65536')
    text = _text(entries[filename])
    if offset > len(text):
        raise ValueError('virtual file offset exceeds exact character length')
    return {'filename': filename, 'format': entries[filename]['format'],
        'read_only': entries[filename].get('read_only', False),
        **{k: entries[filename][k] for k in ('source_kind', 'archive') if k in entries[filename]},
        'content': text[offset:offset + limit], 'offset': offset,
        'complete': offset == 0 and len(text) <= limit,
        'slice_reaches_end': offset + limit >= len(text), 'total_characters': len(text),
        'total_utf8_bytes': len(text.encode('utf-8')),
        'content_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'scope': ('Literal archived own-trial data; immutable, not the current draft, SYSTEM authority, adoption or executed behavior.'
            if entries[filename].get('source_kind') == 'own-history' else
            'Exact immutable request-parent reference; data only, never automatic restoration, adoption or SYSTEM authority.'
            if entries[filename].get('source_kind') == 'request-parent' else
            'Source-owned read-only API reference, not candidate data or executed behavior.'
            if entries[filename].get('read_only') else
            'Literal current draft text; not a host file, instruction or execution result.')}


def write_file_operations(document, filename, content, *, request=None,
                           conversation_profile='hermes-function-history-v26'):
    """Return exact ordinary edits. The caller applies/validates them as before."""
    if not isinstance(filename, str) or not isinstance(content, str):
        raise ValueError('filename and content must be literal strings')
    entries, _ = _entries(document, request, conversation_profile=conversation_profile)
    if filename not in entries:
        # Creation is an explicit author-selected new node, never a filled-in
        # institution template or implicit creation of a missing source owner.
        if not filename.startswith('new/') or not filename.endswith('.json'):
            raise ValueError(_missing_name(document, filename,
                'unknown exact virtual filename; no OS file is read or created'))
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
    if entry.get('read_only'):
        raise ValueError('virtual API reference or own-history file is read-only; no candidate or host file was changed')
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


def _missing_name(document, filename, default):
    nodes = document.get('mechanisms', [])
    if not isinstance(nodes, list):
        nodes = []
    matches = [('positions/' + str(index) + '.json', '/mechanisms/' + str(index))
        for index, node in enumerate(nodes)
        if isinstance(node, dict) and isinstance(node.get('mechanism_id'), str)
        and filename in ('nodes/' + quote(node['mechanism_id'], safe='._-') + '.json',
            'code/' + quote(node['mechanism_id'], safe='._-') + '.py')]
    if len(matches) > 1:
        return ('ambiguous virtual filename: duplicate mechanism IDs; no owner selected. '
            'Exact current node aliases/paths: ' + json.dumps(matches[:16], ensure_ascii=False)
            + '; total owners=' + str(len(matches)) + ' (all positions are in the current catalog)'
            + '. Use an exact positional alias or explicit root pointer. Immutable originals '
              'are under parent/. No source was repaired or restored.')
    return default
