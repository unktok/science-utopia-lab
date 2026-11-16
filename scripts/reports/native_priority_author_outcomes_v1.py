"""Join all eight original free-author sessions to frozen native outcomes.

Read-only post-closure analysis: no generation, repair, reselection, native
execution or merit gate. Missing session evidence and null outcomes stay visible.
"""
import argparse
from collections import Counter
import csv
import fcntl
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_author_step_summary_v1 import read_session
from scripts.reports.native_priority_method_readout_v1 import METHODS, OBJECTIVES, SCHEMA as ORIGINAL
from scripts.run_native_priority_fixed_evaluation_v1 import origin_evidence, evidence_files
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-priority-author-outcomes.v1'


def read(path, sealed=True):
    value = decode_json(Path(path).read_text(), strict=True, finite_floats=True)
    return checked(value) if sealed else value


def join(report, authors):
    """Pure diagnostic projection; synthetic inputs are not provenance proof."""
    checked(report)
    slots = [r for r in report['slots'] if r['method'] == METHODS[2]]
    if (report['schema'] != ORIGINAL or len(report['slots']) != 24 or len(slots) != 8
            or len(authors) != 8 or [r['cell_id'] for r in authors] != [r['cell_id'] for r in slots]
            or len({r['cell_id'] for r in slots}) != 8):
        raise ValueError('all eight ordered compound free-author cells required, including nulls')
    traces = {r['identity']: r for r in report['behavior_evidence']['traces']}
    if len(traces) != len(report['behavior_evidence']['traces']):
        raise ValueError('unique observed-path compound identities required')
    references = [('reference/' + r['label'], r['literal_system_sha256']) for r in report['references']]
    rows = []
    for row, author in zip(slots, authors, strict=True):
        session = author['session']; complete = row['status'] == 'complete'
        if (author['submitted_program_sha256'] != row['literal_system_sha256']
                or (session is None and row['status'] != 'generation-null')
                or (row['status'] != 'generation-null' and (not session['terminal_record_present']
                    or session['terminal_status'] != 'generated' or not session['explicit_finish_observed']))):
            raise ValueError('actual submitted program and explicit author finish must agree with outcome')
        previous = references + [(s['cell_id'], s['literal_system_sha256']) for s in report['slots']
            if s['slot_index'] < row['slot_index'] and s['status'] == 'complete']
        parent_ids = [identity for identity, sha in previous if sha == author['parent_program_sha256']]
        parent_paths = [traces[i] for i in parent_ids if i in traces
            and traces[i]['status'] == 'complete' and traces[i]['requests'] is not None]
        own = traces.get(row['cell_id']); available = (complete and own is not None
            and own['status'] == 'complete' and own['requests'] is not None and bool(parent_paths))
        match = None if not available else any(
            own['requests']['ordered_full_request_payload_sha256'] == t['requests']['ordered_full_request_payload_sha256']
            for t in parent_paths)
        path = report['paths']['/'.join((row['method'], str(row['replication']), row['objective']))]
        reference_loss = next(p['reference_loss'] for p in path if p['cell_id'] == row['cell_id'])
        rows.append({**{k: clone(row[k]) for k in ('cell_id', 'slot_index', 'replication', 'objective',
                'generation', 'status', 'suggestion_id', 'loss', 'cross_scores', 'graph_delta')},
            'request_sha256': author['request_sha256'],
            'submitted_program_sha256': author['submitted_program_sha256'],
            'parent_program_sha256': author['parent_program_sha256'],
            'literal_submitted_program_equals_parent': None if row['literal_system_sha256'] is None
                else row['literal_system_sha256'] == author['parent_program_sha256'],
            'parent_observation_id': author['parent_observation_id'], 'measured_parent_loss': author['parent_loss'],
            'own_minus_measured_parent': row['loss'] - author['parent_loss']
                if complete and author['parent_loss'] is not None else None,
            'initial_reference_loss': reference_loss,
            'own_minus_initial_reference': row['loss'] - reference_loss if complete else None,
            'prior_exact_parent_complete_path_ids': [t['identity'] for t in parent_paths],
            'observed_full_inputs_match_a_complete_parent': match,
            'session_evidence_status': 'recorded' if session is not None else 'unavailable-not-zero',
            'session': clone(session)})
    totals = {}
    for objective in OBJECTIVES:
        group = [r for r in rows if r['objective'] == objective]
        known = [r['session'] for r in group if r['session'] is not None]
        totals[objective] = {'declared_cells': len(group), 'recorded_sessions': len(known),
            'session_evidence_unavailable': len(group) - len(known),
            'outcome_statuses': dict(sorted(Counter(r['status'] for r in group).items())),
            'known_session_completed_steps': sum(s['completed_steps'] for s in known),
            'known_session_edit_attempts': sum(s['attempted_edit_steps'] for s in known),
            'known_session_document_changes': sum(s['successful_document_changes'] for s in known),
            'known_session_duplicate_reads': sum(s['duplicate_unchanged_read_observations'] for s in known)}
    return {'schema': SCHEMA, 'scientific_source_commit': report['scientific_source_commit'],
        'original_report_content_sha256': report['content_sha256'], 'rows': rows, 'by_objective': totals,
        'scope': 'All eight free-author cells, no favorable filtering. Action, literal program, '
            'observed native inputs and measured gain are separate layers. Same-input paths are '
            'not semantic equivalence; unknown paths/sessions are not zero. These histories are '
            'not independent scientist populations. No causal model/interface diagnosis or method '
            'superiority, new invention or recursive inventor improvement is inferred. '
            'Step totals exclude separately accounted calibration/probes/role loads.',
        'new_model_calls': 0, 'new_code_executions': 0, 'selection_changed': False, 'publication_ready': False}


def collect(root, plan, report):
    authors, states, inputs = [], {}, {}
    def bound_read(path, sealed=True):
        if path.is_symlink(): raise ValueError('literal original journal file required')
        inputs[str(path)] = file_sha256(path); return read(path, sealed)
    for row in report['slots']:
        if row['method'] != METHODS[2]: continue
        history = root / 'search' / row['method'] / ('history-' + str(row['replication'])) / row['objective']
        if history not in states:
            state = bound_read(history / 'campaign/native-adaptive-state.json', False)
            if state['pending'] is not None or len(state['records']) != plan['generations']:
                raise ValueError('normally closed original free histories required')
            states[history] = state
        record = states[history]['records'][row['generation']]; request = record['request']
        if (record['request_sha256'] != digest(request) or request['generation'] != row['generation']
                or request['loss_spec'] != plan['losses'][row['objective']]):
            raise ValueError('exact original request, objective and generation required')
        parent_id = request['based_on_observation_id']
        parent = next((r['observation'] for r in request['observations']
            if r['observation']['observation_id'] == parent_id), None)
        if parent is None or parent['candidate'] != request['parent_system'] or parent['status'] != 'complete':
            raise ValueError('actual declared measured parent required, not a convenient matching policy')
        proposal = history / 'authoring' / ('proposal-' + record['request_sha256'])
        session_dir = proposal / 'editor-session/authoring' / ('generation-' + record['request_sha256'])
        session = None
        if (session_dir / 'request.json').exists():
            session = read_session(session_dir); inputs.update(session['file_sha256'])
            binding = bound_read(session_dir / 'request.json', False)
            if binding['request'] != request or session['request_sha256'] != record['request_sha256']:
                raise ValueError('author session belongs to a different original request')
            if (proposal / 'result.json').exists():
                outer = bound_read(proposal / 'result.json')
                inner = bound_read(session_dir / 'response.json')
                if outer['definition'] != inner['definition'] or outer['definition'] != record['definition']:
                    raise ValueError('literal returned/recorded author definition differs')
            elif row['status'] != 'generation-null':
                raise ValueError('submitted native world lacks its actual returned proposal')
        if row['status'] != 'generation-null':
            if len(record['draws']) != 1 or len(record['observations']) != 1:
                raise ValueError('one actual submitted candidate and original observation required')
            submitted = record['draws'][0]['suggestion']['candidate']; observation = record['observations'][0]
            if (submitted != observation['candidate'] or observation['loss'] != row['loss']
                    or observation['status'] != row['status'] or observation['suggestion_id'] != row['suggestion_id']):
                raise ValueError('literal recorded submission/outcome differs')
            submitted_sha = digest(submitted)
        else:
            if record['draws'] or record['observations'] or not row['generation_error']:
                raise ValueError('original generation null must remain absent, not a fallback')
            submitted_sha = None
        authors.append({'cell_id': row['cell_id'], 'request_sha256': record['request_sha256'],
            'parent_program_sha256': digest(request['parent_system']), 'parent_observation_id': parent_id,
            'parent_loss': parent['loss'], 'submitted_program_sha256': submitted_sha, 'session': session})
    if any(file_sha256(p) != h for p, h in inputs.items()): raise ValueError('original author journal changed')
    return authors, inputs


def export(args):
    origin = {k: str(getattr(args, 'origin_' + k).resolve()) for k in ('run', 'source', 'analysis', 'readouts')}
    out = args.output.resolve()
    if out.exists() or any(out.is_relative_to(p) for p in [ROOT.resolve(), *map(Path, origin.values())]):
        raise ValueError('fresh output outside reader/all original source and evidence roots required')
    reader = pinned_revision(ROOT); raw = Path(origin['run'])
    origin['source_commit'] = read(raw / 'plan.json')['source_commit']
    origin['input_files'] = {str(p): file_sha256(p) for p in evidence_files(origin)}
    with (raw / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_SH | fcntl.LOCK_NB)
        plan, _, _ = origin_evidence(origin); before = _inventory(raw)
        report = read(Path(origin['readouts']) / 'report-1/report.json')
        authors, inputs = collect(raw, plan, report); result = join(report, authors)
        inputs.update(origin['input_files'])
        if before != _inventory(raw) or any(file_sha256(p) != h for p, h in inputs.items()):
            raise ValueError('original records changed during joined analysis')
        costs = read(Path(origin['analysis']) / 'costs-1.json')
        result.update(analysis_source_commit=reader, original_raw_inventory_sha256=digest(before),
            original_cost_content_sha256=costs['content_sha256'],
            original_campaign_cost_summary={k: clone(costs.get(k)) for k in
                ('scientist', 'common_content_observer', 'auxiliary', 'scope')})
        out.mkdir(parents=True); save(out / 'report.json', result)
        fields = ['cell_id', 'objective', 'replication', 'generation', 'status', 'loss',
            'own_minus_measured_parent', 'own_minus_initial_reference',
            'literal_submitted_program_equals_parent', 'observed_full_inputs_match_a_complete_parent',
            'session_evidence_status', 'completed_steps', 'attempted_edit_steps',
            'successful_document_changes', 'duplicate_unchanged_read_observations']
        with (out / 'authors.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for row in result['rows']:
                session = row['session'] or {}
                writer.writerow({k: row[k] if k in row else session.get(k) for k in fields})
        save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'analysis_source_commit': reader,
            'scientific_source_commit': plan['source_commit'], 'input_files': inputs,
            'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
            'new_model_calls': 0, 'new_code_executions': 0})
        if (before != _inventory(raw) or any(file_sha256(p) != h for p, h in inputs.items())
                or pinned_revision(ROOT) != reader or pinned_revision(Path(origin['source'])) != plan['source_commit']):
            raise ValueError('reader/scientific source or original records changed during export')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'source', 'analysis', 'readouts'):
        parser.add_argument('--origin-' + key, type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); export(parser.parse_args())


if __name__ == '__main__': main()
