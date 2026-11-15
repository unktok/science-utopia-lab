"""Same-authority developer comparators, never an automatic invention result."""
from copy import deepcopy
from dataclasses import replace

from .native_catalog_planning import SOURCE as CORE_SOURCE, ACTION as CORE_ACTION
from .native_legacy_topic_planning import ACTION
from .validation import validate_system_spec

MEMBERSHIP = """        topics = set(actor['expertise'])
        if context['parameters']['candidate_policy'] == 'core-plus-related':
            for topic in actor['expertise']:
                topics.update(catalog[topic]['related_topics'])
        elif context['parameters']['candidate_policy'] != 'core-only':
            raise ValueError('unknown explicit comparison topic set')
        candidates = [catalog[t] for t in sorted(topics) if t in catalog]"""
SOURCE = CORE_SOURCE.replace("        candidates = [catalog[t] for t in actor['expertise']]", MEMBERSHIP)
SOURCE = SOURCE.replace("action = 'native.catalog-project.v1'", "action = '" + ACTION + "'")


def legacy_topic_control(core_control, *, candidate_policy):
    """Both rules receive identical broad authority; only their topic rule differs.

    This helper replaces a literal developer comparator, not arbitrary authored
    code. Search candidates remain complete editable SystemSpecs, not this menu.
    """
    if candidate_policy not in ('core-only', 'core-plus-related'):
        raise ValueError('explicit core-only/core-plus-related comparison rule required')
    producer = next(n for n in core_control.mechanisms if n.mechanism_id == 'developer-catalog-agenda')
    if producer.parameters['code_artifact']['source'] != CORE_SOURCE or producer.parameters['actuation'] != 'project':
        raise ValueError('literal developer core-project comparator required')
    params = deepcopy(producer.parameters)
    params['candidate_policy'] = candidate_policy
    params['code_artifact']['source'] = SOURCE
    params['code_artifact']['label'] = 'Developer original-topic comparator; not autonomous invention'
    nodes = []
    for node in core_control.mechanisms:
        if node.mechanism_id == producer.mechanism_id:
            node = replace(node, parameters=params)
        elif node.mechanism_id == 'developer-catalog-effects':
            p = deepcopy(node.parameters)
            grants = p['capabilities']
            grants['bootstrap'] = [ACTION if v == CORE_ACTION else v for v in grants['bootstrap']]
            grants['roles'] = {role: [ACTION if v == CORE_ACTION else v for v in values]
                               for role, values in grants['roles'].items()}
            node = replace(node, parameters=p)
        nodes.append(node)
    candidate = replace(core_control, mechanisms=tuple(nodes))
    validate_system_spec(candidate).require_valid()
    return candidate
