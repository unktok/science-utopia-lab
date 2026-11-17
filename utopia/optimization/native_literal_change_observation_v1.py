"""Passive literal design-change observations, not semantic or native validation.

Preparation only: no current author/optimizer imports this module. A future
declared interface may expose these facts without requiring a change or gain.
"""
import ast
from collections import Counter
import hashlib

from utopia.system.design_patch import digest

SCHEMA = 'scienceutopia.literal-institution-change-observation.v1'
MAX_SOURCE_BYTES = 65536


def changed_keys(before, after):
    """Preserve missing/null and int/float/bool distinctions in recorded JSON."""
    return sorted(k for k in set(before) | set(after)
        if (k in before) != (k in after) or k in before and digest(before[k]) != digest(after[k]))


def node_index(document):
    if not isinstance(document, dict) or not isinstance(document.get('mechanisms'), list):
        return None, 'mechanism-list-unavailable'
    nodes = document['mechanisms']; result = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('mechanism_id'), str):
            return None, 'node-without-literal-string-identity'
        key = node['mechanism_id']
        if key in result: return None, 'duplicate-node-identity'
        result[key] = node
    return result, 'unique-literal-identities'


def python_source(node):
    """Only the standard direct Python artifact is assessed by this version.

    Other/nested/generated runtimes remain unrestricted and explicitly
    unassessed here; their literal parameter/root changes still appear.
    """
    params = node.get('parameters') if isinstance(node, dict) else None
    artifact = params.get('code_artifact') if isinstance(params, dict) else None
    if not isinstance(artifact, dict) or not isinstance(artifact.get('source'), str):
        return {'status': 'direct-source-unavailable', 'source_sha256': None, 'AST_sha256': None}
    source = artifact['source']; body = source.encode('utf-8')
    result = {'status': 'not-standard-python-artifact',
        'source_sha256': hashlib.sha256(body).hexdigest(), 'AST_sha256': None}
    if node.get('implementation') != 'code.python.v1' or artifact.get('language') != 'python':
        return result
    if len(body) > MAX_SOURCE_BYTES:
        return {**result, 'status': 'unassessed-source-over-diagnostic-byte-limit'}
    try:
        tree = ast.dump(ast.parse(source), include_attributes=False)
    except (SyntaxError, ValueError, RecursionError) as error:
        return {**result, 'status': 'unassessed-parse-error', 'error_type': type(error).__name__}
    return {**result, 'status': 'parsed-without-execution',
        'AST_sha256': hashlib.sha256(tree.encode('utf-8')).hexdigest()}


def list_change(before, after, key):
    a, b = before.get(key), after.get(key)
    same_presence = (key in before) == (key in after)
    changed = not same_presence or digest(a) != digest(b)
    result = {'literal_changed': changed, 'before_present': key in before, 'after_present': key in after,
        'multiset_changed': None, 'order_only_change': None, 'added_occurrences': None, 'removed_occurrences': None}
    if isinstance(a, list) and isinstance(b, list):
        ca, cb = Counter(map(digest, a)), Counter(map(digest, b))
        result.update(multiset_changed=ca != cb, order_only_change=changed and ca == cb,
            added_occurrences=sum((cb-ca).values()), removed_occurrences=sum((ca-cb).values()))
    return result


def observe(before, after, *, maximum_node_rows=32):
    """Read two UTF8 JSON draft documents, including structurally invalid drafts.

    Never invoke an authored program, compiler, model, tool action or world.
    No validity, usefulness, improvement or plan-fulfillment verdict is issued.
    """
    if type(maximum_node_rows) is not int or not 1 <= maximum_node_rows <= 128:
        raise ValueError('explicit bounded diagnostic node rows required')
    report = {'schema': SCHEMA, 'before_document_sha256': digest(before),
        'after_document_sha256': digest(after), 'literal_document_changed': digest(before) != digest(after),
        'node_resolution': None, 'node_change_count': None, 'node_changes': None, 'omitted_node_rows': None,
        'other_root_fields_changed': None, 'mechanisms': None, 'connections': None, 'schedules': None,
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_source_executions': 0,
        'source_repair': False, 'veto_on_finish': False, 'changes_loss': False, 'grants_world_authority': False,
        'scope': 'Literal JSON/standard direct Python AST facts only. AST equality is not '
            'whole-program/world equivalence; AST difference is not operative behavior or benefit. '
            'Nested/non-Python/new runtimes remain unassessed by the AST diagnostic, not forbidden. '
            'List order/multiplicity, unavailable/ambiguous nodes and invalid source are retained. '
            'No candidate is changed, repaired, rejected, promoted or required to differ. '
            'No plan prose is interpreted or implemented. This report has no measured native loss.'}
    if not isinstance(before, dict) or not isinstance(after, dict):
        report['node_resolution'] = 'non-object-draft-unassessed'
        return report
    reserved = {'mechanisms', 'connections', 'schedules'}
    report['other_root_fields_changed'] = changed_keys(
        {k:v for k,v in before.items() if k not in reserved},
        {k:v for k,v in after.items() if k not in reserved})
    report['connections'] = list_change(before, after, 'connections')
    report['schedules'] = list_change(before, after, 'schedules')
    report['mechanisms'] = list_change(before, after, 'mechanisms')
    a, ra = node_index(before); b, rb = node_index(after)
    if a is None or b is None:
        report['node_resolution'] = {'before': ra, 'after': rb}
        return report
    report['node_resolution'] = 'unique-literal-identities'
    ids = [key for key in sorted(set(a) | set(b))
        if key not in a or key not in b or digest(a[key]) != digest(b[key])]
    report.update(node_change_count=len(ids), node_changes=[], omitted_node_rows=max(0, len(ids)-maximum_node_rows))
    for key in ids[:maximum_node_rows]:
        row = {'mechanism_id': key, 'change': 'added' if key not in a else 'removed' if key not in b else 'changed',
            'before_node_sha256': None if key not in a else digest(a[key]),
            'after_node_sha256': None if key not in b else digest(b[key])}
        if key in a and key in b:
            pa, pb = a[key].get('parameters'), b[key].get('parameters')
            row['node_fields_changed'] = changed_keys(a[key], b[key])
            row['non_code_parameter_fields_changed'] = (changed_keys(
                {k:v for k,v in pa.items() if k != 'code_artifact'},
                {k:v for k,v in pb.items() if k != 'code_artifact'})
                if isinstance(pa, dict) and isinstance(pb, dict) else None)
            ca, cb = python_source(a[key]), python_source(b[key])
            row.update(before_source=ca, after_source=cb,
                standard_python_AST_equal=(ca['AST_sha256'] == cb['AST_sha256']
                    if ca['AST_sha256'] is not None and cb['AST_sha256'] is not None else None))
        report['node_changes'].append(row)
    return report
