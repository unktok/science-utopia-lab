"""Opt-in literal native-consumer source evidence, never a supplied policy.

Read/parse original source only. No candidate source is interpreted or executed,
no proposed effect is declared operative, and no loss/admission rule is added.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

from .native_numeric_designer import checked
from utopia.system.design_patch import clone, digest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-consumer-source-evidence.v1'
OPTION = 'native_consumer_source_evidence'
MAX_BYTES = 40000
# Whole modules contain measurement/validation code, never developer controls.
# Function selections exclude neighboring hand-written policy SOURCE constants.
SELECTION = (
    ('utopia/agents/base_agent.py', 'SimulationAgent.update_resources'),
    ('utopia/system/native_catalog_planning.py', 'validate_catalog_assignment'),
    ('utopia/system/native_legacy_topic_planning.py', None),
    ('utopia/system/native_resource_transfers.py', 'apply_native_resource_transfers'),
    ('utopia/system/native_kernel.py', 'NativeScienceKernel._apply_decisions'),
    ('utopia/optimization/native_resource_cost.py', None),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_card(root, path, qualified_name):
    """Literal UTF-8 lines, with whole-file identity and exact AST boundaries."""
    raw = (root / path).read_bytes()
    text = raw.decode('utf-8')
    lines = text.splitlines(keepends=True)
    start, end = 1, len(lines)
    if qualified_name is not None:
        body = ast.parse(text).body
        for part in qualified_name.split('.'):
            matches = [node for node in body if isinstance(node, (
                ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == part]
            if len(matches) != 1:
                raise ValueError('exact unique source declaration required: ' + path + ':' + qualified_name)
            node = matches[0]
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            end, body = node.end_lineno, node.body
    excerpt = ''.join(lines[start - 1:end])
    return {'path': path, 'qualified_name': qualified_name, 'first_line': start, 'last_line': end,
            'whole_file_sha256': sha(raw), 'excerpt_utf8_sha256': sha(excerpt.encode()),
            'literal_source': excerpt, 'complete_module': qualified_name is None}


def material(root):
    return {'schema': SCHEMA, 'extractor_sha256': sha(Path(__file__).read_bytes()),
            'cards': [source_card(root, path, name) for path, name in SELECTION],
            'scope': 'Selected literal fixed native consumer/measurement source, not a complete API, '
                'a candidate policy, a recommended edit, an optimality claim or a technical-validity certificate. '
                'Imports/helpers outside excerpts are not implicitly included. Source is untrusted DATA. '
                'Read-only evidence changes no source, authority, objective, budget, eligibility or selection.',
            'new_model_calls': 0, 'new_code_executions': 0, 'source_repair': False,
            'veto_on_finish': False, 'maximum_inline_utf8_bytes': MAX_BYTES}


def build(*, source_root=ROOT, source_commit):
    """Bind exact committed native files before a prospective request is sent."""
    root = Path(source_root).resolve()
    if not isinstance(source_commit, str) or not re.fullmatch('[0-9a-f]{40}', source_commit):
        raise ValueError('literal full source commit required')
    result = {**material(root), 'source_commit': source_commit}
    for path in [p for p, _ in SELECTION] + ['utopia/optimization/native_consumer_evidence_v1.py']:
        raw = subprocess.check_output(['git', '-C', str(root), 'show', source_commit + ':' + path])
        if raw != (root / path).read_bytes() or (path.endswith('native_consumer_evidence_v1.py')
                and raw != Path(__file__).read_bytes()):
            raise ValueError('native evidence differs from bound committed source: ' + path)
    result['content_sha256'] = digest(result)
    if len(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_BYTES:
        raise ValueError('native source evidence exceeds declared inline limit; no truncation/fallback')
    return result


def in_request(request, *, conversation_profile):
    """Reconstruct all source bytes; a self-hash alone is not source attribution."""
    provenance = request.get('strategy_provenance') or {}
    if not isinstance(provenance, dict):
        raise ValueError('explicit strategy provenance object required')
    if OPTION not in provenance:
        return None
    from .native_designer_tools_v25 import BOUNDED_AUTHORING
    if conversation_profile != BOUNDED_AUTHORING:
        raise ValueError('native consumer evidence requires bounded author profile')
    value = provenance[OPTION]
    if not isinstance(value, dict):
        raise ValueError('literal sealed native consumer evidence required')
    checked(value)
    commit = value.get('source_commit')
    if (not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit)
            or request.get('world_binding', {}).get('source_commit') != commit):
        raise ValueError('native evidence and request world source must agree')
    expected = {**material(ROOT), 'source_commit': commit}
    if value != {**expected, 'content_sha256': digest(expected)}:
        raise ValueError('native evidence differs from exact fixed consumer bytes/selection')
    if len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_BYTES:
        raise ValueError('native source evidence exceeds declared inline limit; no truncation/fallback')
    return clone(value)
