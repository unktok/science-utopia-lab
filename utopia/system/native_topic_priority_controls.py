"""Named restricted developer family, not free-system invention or a new law.

Priorities break ties only among the shortest eligible original directions.
The general institution editor remains free to replace this entire algorithm,
its mechanisms and its wiring; this family is a prospective comparison control.
"""
from copy import deepcopy
from dataclasses import replace
import math

from .native_legacy_topic_controls import SOURCE as LEGACY_SOURCE
from .validation import validate_system_spec

_CHOICE = "        direction = min(candidates, key=lambda d: (d['years'], d['topic']))"
_APPEND = '        assignments.append(assignment)'
if LEGACY_SOURCE.count(_CHOICE) != 1 or LEGACY_SOURCE.count(_APPEND) != 1:
    raise RuntimeError('literal developer comparator source changed')
SOURCE = LEGACY_SOURCE.replace(_CHOICE, """        lexical_direction = min(candidates, key=lambda d: (d['years'], d['topic']))
        direction = min(candidates, key=lambda d: (d['years'],
            -context['parameters']['topic_priorities'].get(d['topic'], 0), d['topic']))""")
SOURCE = SOURCE.replace(_APPEND, """        if direction['topic'] != lexical_direction['topic']:
            assignment['reason'] = 'Developer catalog agenda: shortest displayed duration, then declared topic priority.'
        assignments.append(assignment)""")


def topic_priority_control(related_control, *, priorities):
    """Replace only a literal same-authority hand comparator, without repair.

    Missing displayed-topic weights mean zero. Unknown topics, booleans,
    nonnumeric and nonfinite values are rejected rather than clipped/coerced.
    This is a restricted policy-family constructor, not a candidate-space veto.
    """
    producer = next(n for n in related_control.mechanisms
                    if n.mechanism_id == 'developer-catalog-agenda')
    if (producer.parameters['code_artifact']['source'] != LEGACY_SOURCE
            or producer.parameters['candidate_policy'] != 'core-plus-related'
            or producer.parameters['actuation'] != 'project'):
        raise ValueError('literal developer core-plus-related project comparator required')
    topics = {d['topic'] for d in producer.parameters['catalog']['directions']}
    if (not isinstance(priorities, dict) or any(not isinstance(k, str) or k not in topics for k in priorities)
            or any(type(v) not in (int, float) or (type(v) is float and not math.isfinite(v))
                   for v in priorities.values())):
        raise ValueError('displayed topics with finite numeric priorities required')
    parameters = deepcopy(producer.parameters)
    parameters['topic_priorities'] = deepcopy(priorities)
    parameters['code_artifact']['source'] = SOURCE
    parameters['code_artifact']['label'] = 'Developer shortest-duration priority family; not autonomous invention'
    nodes = tuple(replace(n, parameters=parameters) if n.mechanism_id == producer.mechanism_id else n
                  for n in related_control.mechanisms)
    candidate = replace(related_control, mechanisms=nodes)
    validate_system_spec(candidate).require_valid()
    return candidate
