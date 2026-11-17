"""Opt-in persistent literal change evidence for native institutional authors.

This is an information intervention, not a candidate selector. No source is
executed, repaired, rejected or required to differ. Historical requests without
the exact prospective declaration retain their original prompt data.
"""
import hashlib
from pathlib import Path

from utopia.system.design_patch import clone, digest
from .native_literal_change_observation_v1 import observe

OPTION = 'literal_design_change_feedback'
SCOPE = 'parent-relative-literal-design-change-v1'
VIEW = 'parent_relative_literal_change_observations'
NOTE = ('DECLARED LITERAL CHANGE OBSERVATIONS: session data compares the current '
    'draft with its exact selected parent on every call, including after reads '
    'and undo. Source text, Python AST, non-code parameters, interfaces, wiring '
    'and schedules are separate observations. Equal AST is not whole-program '
    'equivalence: parameters, interfaces, wiring or runtime can change behavior. '
    'Different AST is not evidence of native behavior change or a better loss. '
    'Unassessed code is not unchanged code. Plan prose is not an implementation. '
    'No change, novelty, fixture pass or improvement is required for submission; '
    'explicit retention remains legal. No source is executed or supplied by '
    'these observations. Minimize only the declared loss.')


def contract():
    observation = Path(__file__).with_name('native_literal_change_observation_v1.py')
    return {'scope': SCOPE, 'maximum_node_rows': 32,
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'observation_source_sha256': hashlib.sha256(observation.read_bytes()).hexdigest(),
        'note_sha256': digest(NOTE), 'veto_on_finish': False, 'changes_loss': False,
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_source_executions': 0}


def declare_request(request):
    """Return an explicitly different prospective request, never mutate one."""
    result = clone(request)
    provenance = result.setdefault('strategy_provenance', {})
    if not isinstance(provenance, dict) or OPTION in provenance:
        raise ValueError('a new unique literal-feedback request declaration is required')
    provenance[OPTION] = contract()
    return result


def enabled(request, *, conversation_profile):
    provenance = request.get('strategy_provenance') or {}
    if not isinstance(provenance, dict) or OPTION not in provenance:
        return False
    from .native_designer_tools_v25 import BOUNDED_AUTHORING
    if conversation_profile != BOUNDED_AUTHORING or provenance[OPTION] != contract():
        raise ValueError('exact source-bound bounded literal-feedback declaration required')
    return True


def view(request, state, *, conversation_profile):
    if not enabled(request, conversation_profile=conversation_profile):
        return None
    result = observe(request['parent_system'], state['document'], maximum_node_rows=32)
    # The passive full report remains a source-bound reusable reader. The
    # active pane omits duplicate source hashes/status bodies, but retains the
    # total count and explicit omission count, including ambiguous drafts.
    rows = result['node_changes']
    return {'schema': 'scienceutopia.literal-design-change-feedback.v1',
        'contract': contract(), 'parent_system_sha256': digest(request['parent_system']),
        'current_system_sha256': digest(state['document']),
        'literal_document_changed': result['literal_document_changed'],
        'node_resolution': result['node_resolution'],
        'node_change_count': result['node_change_count'],
        'omitted_node_rows': result['omitted_node_rows'],
        'node_changes': None if rows is None else [_node_view(row) for row in rows],
        **{key: clone(result[key]) for key in
            ('other_root_fields_changed', 'mechanisms', 'connections', 'schedules')},
        'full_observation_sha256': digest(result),
        'distribution_configuration': {
            key: {'literal_configured': bool(state[key]), 'value_sha256': digest(state[key])}
            for key in ('factors', 'continuous', 'logits')},
        'scope': NOTE,
        'native_behavior_changed': 'not-assessed', 'native_loss': 'not-measured'}


def _node_view(row):
    value = {key: clone(row[key]) for key in ('mechanism_id', 'change')}
    if row['change'] == 'changed':
        value.update({key: clone(row[key]) for key in
            ('node_fields_changed', 'non_code_parameter_fields_changed',
             'code_artifact_fields_except_source_changed', 'standard_python_AST_equal')})
        value['source_text_changed'] = (row['before_source']['source_sha256'] !=
            row['after_source']['source_sha256'])
        value['source_assessment'] = {key: row[key]['status']
            for key in ('before_source', 'after_source')}
    return value
