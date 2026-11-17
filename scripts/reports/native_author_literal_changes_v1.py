"""Passive changes in complete original author journals, without replay/execution.

This is an analysis tool, not a production author-feedback mode. A saved next
prompt is evidence of the document then displayed, not universal semantics.
"""
import argparse
from collections import Counter
from pathlib import Path

from scripts.reports.native_author_step_summary_v1 import EDITS, read_session
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_literal_change_observation_v1 import observe
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-author-literal-changes.v1'


def document_view(intent):
    """Only literal full documents are assessed; retrieval pointers are not data."""
    prompt = intent['prompt']
    if isinstance(prompt, str):
        try:
            prompt = decode_json(prompt, strict=True, finite_floats=True)
        except ValueError:
            return None
    if not isinstance(prompt, dict) or prompt.get('literal_current_system') is None:
        return None
    document = prompt['literal_current_system']
    if digest(document) != prompt.get('current_system_sha256'):
        raise ValueError('saved literal document differs from its prompt identity')
    return document


def project(intents, steps):
    """Pure projection; callers establish original journal provenance separately."""
    if ([s['step'] for s in steps] != list(range(len(steps)))
            or [s['step'] for s in intents] != list(range(len(intents)))
            or len(intents) - len(steps) not in (0, 1)):
        raise ValueError('complete chronological intent/completed prefix required')
    rows = []
    for index, step in enumerate(steps):
        transition = step.get('transition')
        transition = transition if isinstance(transition, dict) else {}
        reply = step.get('model_reply')
        action = reply.get('output') if isinstance(reply, dict) else None
        attempted = action.get('tool') if isinstance(action, dict) else None
        attempted = attempted if isinstance(attempted, str) else None
        executed = transition.get('tool')
        executed = executed if isinstance(executed, str) else None
        if attempted not in EDITS and executed not in EDITS:
            continue
        row = {'step': index, 'attempted_tool': attempted, 'executed_tool': executed,
            'original_status': step['status'], 'original_completed_content_sha256': step['content_sha256'],
            'status': 'not-applied-no-change-verdict', 'diagnostic': None}
        if transition.get('ok') is True and executed in EDITS:
            before = document_view(intents[index])
            after = document_view(intents[index + 1]) if index + 1 < len(intents) else None
            row['status'] = 'literal-before-or-next-view-unavailable'
            if before is not None and after is not None:
                if (digest(before) != transition.get('document_before_sha256')
                        or digest(after) != transition.get('document_after_sha256')):
                    raise ValueError('original receipt and saved before/next document differ')
                row.update(status='observed-literal-before-and-next-view', diagnostic=observe(before, after))
        rows.append(row)
    return {'edit_attempts': len(rows), 'status_counts': dict(sorted(Counter(r['status'] for r in rows).items())),
        'edits': rows}


def collect(directory):
    """Validate the complete original chain, then bind all read bytes twice."""
    directory = Path(directory).resolve()
    session = read_session(directory)
    if not session['terminal_record_present'] or session['started_without_committed_receipt']:
        raise ValueError('closed original session with no uncommitted dispatch required')
    files = session['file_sha256']
    def read(path, sealed=False):
        if str(path) not in files or path.is_symlink() or file_sha256(path) != files[str(path)]:
            raise ValueError('original session bytes changed before projection')
        value = decode_json(path.read_text(), strict=True, finite_floats=True)
        return checked(value) if sealed else value
    intents = [read(directory / f'step-{i:02}.started.json') for i in range(session['started_calls'])]
    steps = [read(directory / f'step-{i:02}.completed.json', True) for i in range(session['completed_steps'])]
    result = project(intents, steps)
    if any(file_sha256(p) != h for p, h in files.items()):
        raise ValueError('original journal changed during projection')
    return {'request_sha256': session['request_sha256'], 'session_directory': str(directory),
        'terminal_status': session['terminal_status'], 'terminal_content_sha256': session['terminal_content_sha256'],
        'completed_steps': session['completed_steps'], 'original_file_sha256': files,
        'full_native_cold_replay': False, **result}


def export(args):
    sources = [ROOT.resolve(), args.origin_source.resolve()]
    sessions = [p.resolve() for p in args.session]
    out = args.output.resolve()
    if len(set(sessions)) != len(sessions) or not sessions:
        raise ValueError('explicit nonempty distinct original session directories required')
    if out.exists() or any(out.is_relative_to(p) for p in [*sources, *sessions]):
        raise ValueError('fresh output outside reader/scientific/session roots required')
    commits = [pinned_revision(p) for p in sources]
    rows = [collect(p) for p in sessions]
    if any(file_sha256(p) != h for row in rows for p, h in row['original_file_sha256'].items()):
        raise ValueError('original session changed across the complete export')
    if [pinned_revision(p) for p in sources] != commits:
        raise ValueError('reader/scientific source changed during export')
    return save(out, {'schema': SCHEMA, 'analysis_source_commit': commits[0],
        'scientific_source_commit': commits[1], 'scientific_source_directory': str(sources[1]), 'sessions': rows,
        'source_binding_scope': 'Caller-declared clean scientific checkout; this reader validates original '
            'session chains, not the full original source-bound native cold replay.',
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_probe_attempts': 0,
        'new_authored_source_executions': 0, 'new_author_prompts_exposing_this_diagnostic': 0,
        'source_repair': False, 'veto_on_finish': False, 'changes_loss': False,
        'publication_ready': False,
        'scope': 'Only the explicitly listed closed sessions, not automatically the whole study. '
            'Unknown/missing document views and rejected edits remain visible. Canonical JSON '
            'and standard Python AST facts are not global semantics, native effects, measured '
            'gain, plan fulfillment or a causal feedback result. This analysis never supplies '
            'a diagnostic to an author, changes a candidate or loss, runs code or reselects.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin-source', type=Path, required=True)
    parser.add_argument('--session', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__':
    main()
