"""Explain literal compiler failures; never repair or add an admission rule."""
from jsonschema import Draft202012Validator

from utopia.optimization.native_workflow_submission_v1 import (
    compile_submission, workflow_context, submission_schema)
from utopia.system.design_patch import clone, digest


def diagnose(request, submission):
    before = digest([request, submission])
    error = None
    try:
        compile_submission(request, submission)
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    context = workflow_context(request)
    schema_errors = [{'instance_path': list(e.absolute_path), 'message': e.message}
        for e in Draft202012Validator(submission_schema(context)).iter_errors(submission)]
    witnesses = []
    if not schema_errors:
        # JSON Schema accepts integral floats. The original compiler requires
        # literal ints; do not coerce them merely to create a friendlier report.
        ints = [*submission['phase_updates'].values(), *submission['remove_connections'],
            *[e['latency'] for e in submission['add_connections']]]
        if all(type(value) is int for value in ints):
            phases = {s['mechanism_id']: s['phase'] for s in context['parent_schedules']}
            phases.update(submission['phase_updates'])
            removed = set(submission['remove_connections'])
            edges = [{'origin_parent_index': e['index'], **{k: v for k, v in e.items() if k != 'index'}}
                for e in context['parent_connections'] if e['index'] not in removed]
            edges += [{'origin_added_index': i, **clone(e)} for i, e in enumerate(submission['add_connections'])]
            for index, edge in enumerate(edges):
                source, target = edge['source_mechanism'], edge['target_mechanism']
                if (edge['latency'] == 0 and source in phases and target in phases
                        and phases[source] >= phases[target]):
                    witnesses.append({'candidate_connection_index': index, 'connection': edge,
                        'source_phase': phases[source], 'target_phase': phases[target],
                        'violated_existing_rule': 'zero-latency producer phase must precede consumer phase'})
    if before != digest([request, submission]): raise AssertionError('diagnostic mutated original inputs')
    return {'schema': 'scienceutopia.native-workflow-submission-feedback.v1',
        'valid_under_original_compiler': error is None, 'original_compiler_error': error,
        'schema_errors': schema_errors, 'causal_order_witnesses': witnesses,
        'scope': 'Explanatory witnesses only; the unchanged original compiler decides validity. This list is not a complete second graph validator.',
        'request_sha256': digest(request), 'literal_submission_sha256': digest(submission),
        'graph_repaired': False, 'new_admission_rule': False,
        'new_model_calls': 0, 'new_native_worlds': 0}
