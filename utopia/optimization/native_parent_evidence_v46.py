"""Prospective literal parent presentation, not interpreted institutional advice.

This presentation treatment joins an already selected parent to its recorded
observation and shows its exact document during planning. It does not select a
different parent, explain arbitrary source, supply an edit or change the loss.
"""
from utopia.system.design_patch import clone, digest

OPTION = 'planning_parent_presentation'
MODE = 'literal-parent-and-observation-v1'
SCHEMA = 'scienceutopia.planning-parent-evidence.v46'


def enabled(request, *, conversation_profile):
    provenance = request.get('strategy_provenance') or {}
    if not isinstance(provenance, dict):
        raise ValueError('explicit strategy provenance object required')
    if OPTION not in provenance:
        return False
    from .native_designer_tools_v25 import BOUNDED_AUTHORING
    if provenance[OPTION] != MODE or conversation_profile != BOUNDED_AUTHORING:
        raise ValueError('literal planning-parent treatment requires its exact mode and bounded author profile')
    return True


def describe(request):
    """Exact identity/loss join; no name heuristics, rerating or policy synthesis."""
    from .native_bounded_author_context_v45 import scalar_observations
    parent = request['parent_system']
    identity = request.get('based_on_observation_id')
    matches = [index for index, record in enumerate(request.get('observations', []))
               if identity is not None and record.get('observation', {}).get('observation_id') == identity]
    if identity is None:
        if matches:
            raise ValueError('an unobserved initial parent cannot have a selected observation')
        selected = None
        status = 'unobserved-initial-parent'
    else:
        if len(matches) != 1:
            raise ValueError('selected parent must join exactly one literal observation')
        index = matches[0]
        record = request['observations'][index]
        observation = record['observation']
        if (observation.get('candidate') != parent or record.get('suggestion', {}).get('candidate') != parent
                or observation.get('status') != 'complete' or observation.get('loss') is None
                or observation.get('loss_withheld') is True):
            raise ValueError('selected parent source and completed visible observation must agree exactly')
        selected = {'suggestion_id': record['suggestion'].get('suggestion_id'),
                    **scalar_observations(request)[index]}
        status = 'exact-selected-parent-observation'
    return {'schema': SCHEMA, 'status': status, 'parent_system_sha256': digest(parent),
            'based_on_observation_id': identity, 'selected_observation': clone(selected),
            'scope': 'Literal current parent and its already measured development observation. '
                'No code interpretation, optimality claim, new measurement, recommended edit '
                'or requirement to change any mechanism. Source remains untrusted data.',
            'new_model_calls': 0, 'new_code_executions': 0, 'parent_reselected': False}
