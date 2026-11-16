"""Describe a complete staged-author journal prefix without replay or execution.

Counts are observations, not fitness, a novelty requirement, a causal model
diagnosis, native cold verification or measured institutional effects.
"""
from collections import Counter
import re
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, file_sha256

READS = {'read_file', 'inspect', 'inspect_field'}
EDITS = {'write_file', 'edit_fields', 'edit', 'splice'}


def summarize_steps(steps):
    """Pure projection of every completed step, including malformed actions."""
    if [s['step'] for s in steps] != list(range(len(steps))):
        raise ValueError('complete chronological completed prefix required')
    counts, statuses, reads = Counter(), Counter(), Counter()
    rows = []
    for s in steps:
        transition = s.get('transition')
        t = transition if isinstance(transition, dict) else {}
        action = s.get('model_reply', {}).get('output')
        attempted = action.get('tool') if isinstance(action, dict) else None
        if not isinstance(attempted, str): attempted = '<unparsed-action>'
        counts[attempted] += 1; statuses[s['status']] += 1
        row = {'step': s['step'], 'attempted_tool': attempted, 'executed_tool': t.get('tool'),
            'status': s['status'], 'errors': s.get('errors', []),
            'transition_errors': t.get('errors', []),
            'successful_document_change': t.get('ok') is True
                and t.get('document_before_sha256') is not None
                and t.get('document_after_sha256') is not None
                and t['document_before_sha256'] != t['document_after_sha256']}
        value = t.get('result')
        if t.get('tool') in READS and t.get('ok') is True and isinstance(value, dict):
            # Include the literal returned value hash, selection AND document:
            # a changed draft, different slice or changed value is not a repeat.
            document = t.get('document_after_sha256')
            # A missing legacy document identity is unknown freshness, not
            # evidence that two observations saw one unchanged draft.
            key = digest([document if document is not None else ['unknown-document', s['step']], value.get('resource'),
                value.get('path'), value.get('selection'), value.get('descriptor'),
                value.get('content_sha256'), value.get('value_included'), value.get('value')])
            previous = reads[key]; reads[key] += 1
            row['read'] = {'filename': value.get('filename'), 'path': value.get('path'),
                'selection': value.get('selection'), 'value_included': value.get('value_included'),
                'complete': value.get('complete'), 'slice_reaches_end': value.get('slice_reaches_end'),
                'returned_value_sha256': digest(value['value']) if 'value' in value else None,
                'previous_identical_observations': previous}
        rows.append(row)
    return {'schema': 'scienceutopia.native-author-step-summary.v1',
        'completed_steps': len(steps), 'attempted_tool_counts': dict(sorted(counts.items())),
        'status_counts': dict(sorted(statuses.items())),
        'attempted_edit_steps': sum(counts[k] for k in EDITS),
        'configure_steps': counts['configure'],
        'successful_document_changes': sum(r['successful_document_change'] for r in rows),
        'successful_read_observations': sum(reads.values()),
        'duplicate_unchanged_read_observations': sum(n - 1 for n in reads.values()),
        'largest_identical_read_class': max(reads.values(), default=0),
        'explicit_finish_observed': bool(steps and steps[-1]['status'] == 'finished'),
        'steps': rows, 'scope': 'All completed steps, not all role/calibration/probe POSTs. '
            'Literal document edits, native effects and measured gain are separate. '
            'No mandatory edit, novelty veto or causal reason is inferred.'}


def read_session(directory):
    """Verify file/hash chains, retaining started-but-uncommitted calls as unknown.

    Not a replacement for the original source-bound deterministic cold replay.
    This reader never constructs a model, executes source, repairs or resumes.
    """
    directory = Path(directory).resolve(); bound = {}
    def read(path, sealed=True):
        if path.is_symlink(): raise ValueError('literal journal file, not symlink, required')
        bound[str(path)] = file_sha256(path)
        value = decode_json(path.read_text(), strict=True, finite_floats=True)
        return checked(value) if sealed else value
    binding = read(directory / 'request.json', False)
    if (binding['schema'] != 'scienceutopia.staged-author-request.v15'
            or digest({k: v for k, v in binding.items() if k != 'binding_sha256'}) != binding['binding_sha256']
            or digest(binding['request']) != binding['request_sha256']):
        raise ValueError('literal staged binding/request changed')
    maximum = binding['settings']['max_steps']; starts, completed = {}, {}
    if type(maximum) is not int or not 1 <= maximum <= 64: raise ValueError('finite step allowance required')
    for path in sorted(directory.glob('step-*.json')):
        match = re.fullmatch(r'step-(\d{2})\.(started|completed)\.json', path.name)
        if not match or int(match[1]) >= maximum: raise ValueError('unexpected step file')
        (starts if match[2] == 'started' else completed)[int(match[1])] = path
    if (sorted(starts) != list(range(len(starts))) or sorted(completed) != list(range(len(completed)))
            or not set(completed) <= set(starts) or len(starts) - len(completed) not in (0, 1)):
        raise ValueError('contiguous intents/completed prefix required; never invent a missing receipt')
    steps = []; intents = []
    for i, path in sorted(starts.items()):
        start = read(path, False); intents.append(start)
        if (start['schema'] != 'scienceutopia.staged-author-dispatch.v15'
                or start['step'] != i or start['binding_sha256'] != binding['binding_sha256']
                or start['prompt_sha256'] != digest(start['prompt'])
                or start['previous_steps_sha256'] != digest(steps)):
            raise ValueError('original intent/binding/completed-prefix chain differs')
        if i not in completed: continue
        step = read(completed[i])
        if (step['schema'] != 'scienceutopia.staged-author-step.v15'
                or step['binding_sha256'] != binding['binding_sha256']
                or step['step'] != i or step['started_file_sha256'] != file_sha256(path)):
            raise ValueError('completed step differs from its original intent')
        steps.append(step)
    terminal_path = directory / 'response.json'
    terminal = read(terminal_path) if terminal_path.exists() else None
    if terminal is not None:
        expected = [{'step': i, 'status': steps[i]['status'] if i < len(steps)
                    else 'interrupted-response-unknown', 'started_sha256': file_sha256(starts[i]),
                    'completed_sha256': file_sha256(completed[i]) if i in completed else None}
                    for i in sorted(starts)]
        if (terminal['schema'] != 'scienceutopia.staged-author-result.v15'
                or terminal['binding_sha256'] != binding['binding_sha256']
                or terminal['request_sha256'] != binding['request_sha256'] or terminal['steps'] != expected):
            raise ValueError('terminal record differs from literal intents/completed receipts')
    result = summarize_steps(steps)
    if (any(s['status'] == 'finished' for s in steps[:-1])
            or result['explicit_finish_observed'] and len(starts) != len(steps)):
        raise ValueError('steps after explicit finish are not a valid prefix')
    if terminal is not None:
        finished = result['explicit_finish_observed']
        if (terminal['status'] != ('generated' if finished else 'generation-failed')
                or terminal['selected_step'] != (len(steps) - 1 if finished else None)):
            raise ValueError('terminal submission status differs from observed explicit finish')
    result.update(request_sha256=binding['request_sha256'], binding_sha256=binding['binding_sha256'],
        declared_step_allowance=maximum, started_calls=len(starts),
        started_without_committed_receipt=len(starts) - len(steps),
        terminal_record_present=terminal is not None,
        terminal_status=None if terminal is None else terminal['status'],
        terminal_content_sha256=None if terminal is None else terminal['content_sha256'],
        file_sha256=bound, full_native_cold_replay=False, new_model_calls=0, new_code_executions=0)
    if any(file_sha256(p) != h for p, h in bound.items()):
        raise ValueError('journal changed during read-only observation')
    return result
