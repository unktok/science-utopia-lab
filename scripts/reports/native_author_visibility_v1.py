"""Inspect recorded V45 body/phase evidence without author or native execution.

This is not a source-bound cold replay, backend transport audit or successful
correction. Missing pending responses remain unknown; losses are never rewritten.
"""
from collections import Counter
import json
from pathlib import Path

from scripts.reports.native_author_step_summary_v1 import read_session
from utopia.optimization.native_numeric_designer import checked
from utopia.optimization.native_objective_view import loss_arithmetic
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json, file_sha256


SCHEMA = 'scienceutopia.native-author-visibility.v1'
REVISIONS = {'matched-bounded-author-64k-v1', 'matched-bounded-author-64k-v2-literal-visibility'}


def prompt_projection(prompt, *, index, maximum, previous_status, expected_loss):
    """Version-specific V44 checkpoint interpretation on the actual V45 body.

    The historical source triggers implementation after three inspection
    attempts, not three successes. This diagnostic states that convention;
    it does not impose another budget/validation rule on any experiment.
    """
    view = decode_json(prompt, strict=True, finite_floats=True)
    contract = view['active_context_contract']
    flow = view['000_current_turn']['authoring_workflow']
    if (contract['schema'] != 'scienceutopia.bounded-author-context.v45'
            or contract['prospective_context_revision'] not in REVISIONS
            or flow['schema'] != 'scienceutopia.authoring-workflow.v44'):
        raise ValueError('explicit supported recorded V45/V44 profile required')
    if ('literal_current_system' not in view
            or type(index) is not int or type(maximum) is not int or not 0 <= index < maximum):
        raise ValueError('actual body presence and finite original step identity required')
    body = view['literal_current_system']; supplied = body is not None
    if supplied and not isinstance(body, dict): raise ValueError('literal native document object required')
    attempts = flow['inspection_attempts_since_last_draft_change']
    successful = flow['successful_inspections_since_last_document_change']
    remaining = flow['remaining_calls_including_this_one']
    reserve = flow['submission_reserve']; cap = flow['literal_current_system_byte_cap']
    if (any(type(v) is not int for v in (attempts, successful, remaining, reserve, cap))
            or not 0 <= successful <= attempts <= index or remaining != maximum - index
            or reserve < 1 or cap < 1 or type(flow['literal_current_system_included']) is not bool):
        raise ValueError('literal recorded workflow counts/caps must match its original step')
    phase = flow['phase']
    if phase not in {'planning', 'general', 'implementation', 'submit', 'recovery'}:
        raise ValueError('known recorded workflow phase required')
    compact = None if not supplied else len(json.dumps(body, ensure_ascii=False,
        sort_keys=True, allow_nan=False, separators=(',', ':')).encode())
    spaced = None if not supplied else len(json.dumps(body, ensure_ascii=False, allow_nan=False).encode())
    if index == 0: expected = 'planning'
    elif remaining in (1, reserve): expected = 'submit'
    elif remaining == 2 and previous_status != 'finished': expected = 'recovery'
    elif supplied and attempts >= 3: expected = 'implementation'
    else: expected = 'general'
    return {'step': index, 'recorded_context_revision': contract['prospective_context_revision'],
        'recorded_phase': phase, 'expected_phase_using_actual_body': expected,
        'whole_document_actually_supplied': supplied,
        'displayed_visibility_matches_body_presence': flow['literal_current_system_included'] is supplied,
        'supplied_body_matches_declared_document_hash': None if not supplied else digest(body) == view['current_system_sha256'],
        'compact_document_utf8_bytes': compact, 'legacy_spaced_document_utf8_bytes': spaced,
        'declared_literal_byte_cap': cap, 'remaining_calls': remaining, 'submission_reserve': reserve,
        'inspection_attempts': attempts, 'successful_inspections': successful,
        'phase_differs_from_actual_body_interpretation': phase != expected,
        'serializer_visibility_phase_mismatch': supplied and compact <= cap < spaced
            and phase == 'general' and expected == 'implementation',
        'exact_loss_arithmetic_and_definitions_present': view['loss_arithmetic'] == expected_loss,
        'scope': 'Saved author request journal; actual backend-wire/capacity/native proofs are separate.'}


def read_visibility(directory):
    """Read the same verified prefix as read_session, including one pending intent."""
    directory = Path(directory).resolve(); summary = read_session(directory)
    inputs = clone(summary['file_sha256'])
    binding = decode_json((directory / 'request.json').read_text(), strict=True, finite_floats=True)
    expected_loss = loss_arithmetic(binding['request']['loss_spec'])
    rows = []
    for index in range(summary['started_calls']):
        path = directory / f'step-{index:02}.started.json'
        if str(path) not in inputs: raise ValueError('intent outside verified original prefix')
        intent = decode_json(path.read_text(), strict=True, finite_floats=True)
        row = prompt_projection(intent['prompt'], index=index, maximum=summary['declared_step_allowance'],
            previous_status=None if not index else summary['steps'][index - 1]['status'],
            expected_loss=expected_loss)
        completed = summary['steps'][index] if index < summary['completed_steps'] else None
        row.update(receipt_status=None if completed is None else completed['status'],
            attempted_tool=None if completed is None else completed['attempted_tool'],
            response_status='uncommitted-unknown' if completed is None else 'committed-receipt',
            observed_successful_document_change=None if completed is None else completed['successful_document_change'])
        rows.append(row)
    if any(file_sha256(path) != sha for path, sha in inputs.items()):
        raise ValueError('original request/receipt journal changed during visibility analysis')
    return {'schema': SCHEMA, 'request_sha256': summary['request_sha256'],
        'binding_sha256': summary['binding_sha256'], 'session_summary_sha256': digest(summary),
        'started_calls': summary['started_calls'], 'completed_steps': summary['completed_steps'],
        'uncommitted_responses': summary['started_without_committed_receipt'],
        'terminal_record_present': summary['terminal_record_present'], 'terminal_status': summary['terminal_status'],
        'phase_counts': dict(sorted(Counter(r['recorded_phase'] for r in rows).items())),
        'serializer_mismatch_calls': sum(r['serializer_visibility_phase_mismatch'] for r in rows),
        'any_phase_interpretation_mismatch_calls': sum(r['phase_differs_from_actual_body_interpretation'] for r in rows),
        'missing_or_different_loss_views': sum(not r['exact_loss_arithmetic_and_definitions_present'] for r in rows),
        'rows': rows, 'file_sha256': inputs, 'new_model_calls': 0, 'new_generated_code_executions': 0,
        'full_native_or_transport_audit': False,
        'scope': 'Entire verified chronological journal prefix, not only a recent tail. '
            'Pending intent responses are unknown, not failures/zero costs. No causal model '
            'diagnosis, source repair, new objective/veto or altered native loss is inferred.'}


def join_visibility(author_report, visibility, *, profile='priority-v1'):
    """Pure all8 final-cell join; caller must establish original export provenance."""
    checked(author_report)
    if profile == 'priority-v1':
        author_schema, schema = 'scienceutopia.native-priority-author-outcomes.v1', SCHEMA + '.all8-join'
    elif profile == 'corrected-choice-v1':
        author_schema = 'scienceutopia.native-corrected-choice-author-outcomes.v1'
        schema = 'scienceutopia.native-corrected-choice-author-visibility.v1.all8-join'
    else: raise ValueError('explicit legacy or corrected four-step author visibility profile required')
    if (author_report['schema'] != author_schema
            or len(author_report['rows']) != 8 or len(visibility) != 8
            or len({r['cell_id'] for r in author_report['rows']}) != 8
            or [r['cell_id'] for r in visibility] != [r['cell_id'] for r in author_report['rows']]):
        raise ValueError('all8 exact ordered original author/outcome cells required')
    rows = []
    for original, extra in zip(author_report['rows'], visibility, strict=True):
        session = original['session']; actual = extra['visibility']
        if (session is None) != (actual is None): raise ValueError('missing session is unknown, not zero')
        if session is None and original['status'] != 'generation-null':
            raise ValueError('only an actual generation-null may lack its author session')
        if actual is not None:
            if (actual['schema'] != SCHEMA or actual['request_sha256'] != original['request_sha256']
                    or actual['completed_steps'] != session['completed_steps']
                    or actual['terminal_status'] != session['terminal_status']
                    or actual['terminal_record_present'] != session['terminal_record_present']
                    or actual['file_sha256'] != session['file_sha256']):
                raise ValueError('visibility journal differs from its original all8 author/outcome evidence')
        rows.append({'cell_id': original['cell_id'], 'status': original['status'],
            'loss': original['loss'], 'original_author_row_sha256': digest(original),
            'visibility_evidence_status': 'unavailable-not-zero' if actual is None else 'recorded',
            'visibility': clone(actual)})
    return {'schema': schema,
        'original_author_report_content_sha256': author_report['content_sha256'],
        'scientific_source_commit': author_report['scientific_source_commit'], 'rows': rows,
        'recorded_sessions': sum(r['visibility'] is not None for r in rows),
        'new_model_calls': 0, 'new_generated_code_executions': 0, 'scientific_losses_rewritten': False,
        'scope': 'Pure join only, not original closure/export provenance or all-stage cold proof. '
            'Every original loss/null stays literal; visibility diagnoses are not scientific vetoes.'}
