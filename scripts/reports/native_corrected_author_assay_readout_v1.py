"""All-three closed technical author outcomes; no model/code/world execution.

Actual original-source cold replay is a separate prerequisite, not replaced by
this reader. Literal edits and measured institutional benefit stay distinct.
"""
import argparse
from collections import Counter
from datetime import datetime
import fcntl
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_author_step_summary_v1 import read_session
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system import SystemSpec
from utopia.system.design_patch import apply_design_patch, clone, digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[2]
ASSAY = 'scienceutopia.native-corrected-author-assay.v1'
SCHEMA = ASSAY + '.readout'
LABELS = ('parent-zero', 'parent-terminal', 'after-feature-write')


def read(path, sealed=True):
    path = Path(path)
    if path.is_symlink(): raise ValueError('literal journal files required')
    value = decode_json(path.read_text(), strict=True, finite_floats=True)
    return checked(value) if sealed else value


def usage(rows):
    """Missing provider counts stay unknown, never zero-token observations."""
    def reply_value(row, key):
        return row[key] if key in row else (row.get('response_payload') or {}).get(key)
    return {'chat_POSTs': len(rows), **{name: {
        'known_sum': sum(r[key] for r in rows if type(r.get(key)) is int),
        'unknown_responses': sum(type(r.get(key)) is not int for r in rows)}
        for name, key in [('prompt_tokens', 'prompt_tokens'), ('output_tokens', 'completion_tokens')]},
        'nonfinal_responses': sum(reply_value(r, 'done') is False for r in rows),
        'completion_signal_unknown': sum(type(reply_value(r, 'done')) is not bool for r in rows),
        'length_terminated_responses': sum(reply_value(r, 'done_reason') == 'length' for r in rows)}


def base_change(parent, definition):
    """Reconstruct the authored BASE, not a sampled factor/continuous policy.

    Validation parses code as data. It never imports/executes its source. Any
    generated factors/coordinates remain uninstantiated, not silently ignored
    when claiming a complete evaluated policy.
    """
    if 'generation_failure' in definition:
        return None
    original = SystemSpec.from_dict(parent)
    patch = definition['base_patch']
    if patch is None:
        authored = original
    else:
        try: authored = apply_design_patch(original, patch)
        except ValueError as error:
            if str(error) != 'design edit is a no-op': raise
            authored = original
    before, after = original.to_dict(), authored.to_dict()
    old = {n['mechanism_id']: n for n in before['mechanisms']}
    new = {n['mechanism_id']: n for n in after['mechanisms']}
    sources = []
    for identity in sorted(old.keys() | new.keys()):
        left = (old.get(identity, {}).get('parameters', {}).get('code_artifact') or {}).get('source')
        right = (new.get(identity, {}).get('parameters', {}).get('code_artifact') or {}).get('source')
        if left != right:
            sources.append({'node_id': identity, 'before_source_value_sha256': digest(left),
                'after_source_value_sha256': digest(right)})
    return {'parent_program_sha256': original.fingerprint, 'authored_base_program_sha256': authored.fingerprint,
        'literal_base_changed': before != after,
        'literal_operation_paths': [] if patch is None else [v['path'] for v in patch['operations']],
        'added_node_ids': sorted(new.keys() - old.keys()), 'removed_node_ids': sorted(old.keys() - new.keys()),
        'changed_source_nodes': sources,
        'connections_changed': before['connections'] != after['connections'],
        'schedules_changed': before['schedules'] != after['schedules'],
        'changed_top_level_fields': sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k)),
        'authored_factor_count': len(definition['factors']),
        'authored_continuous_coordinate_count': len(definition['continuous']),
        'mixed_distribution_instantiated': False, 'new_native_loss': None,
        'scope': 'Literal base-document change only; no behavioral equivalence or native benefit inferred.'}


def project(plan, terminal, rows, cold):
    if (plan['schema'] != ASSAY + '.plan' or terminal['schema'] != ASSAY + '.terminal'
            or terminal['status'] != 'closed' or terminal['completed_cases'] != 3
            or tuple(c['label'] for c in plan['cases']) != LABELS
            or tuple(r['label'] for r in rows) != LABELS
            or cold['schema'] != ASSAY + '.cold' or cold['source_commit'] != plan['source_commit']
            or cold['plan_content_sha256'] != plan['content_sha256']):
        raise ValueError('all three original normally closed cases and matching cold projection required')
    expected_cold = [{k: clone(r[k]) for k in ('label', 'free_submission_available',
        'implementation_phase_calls', 'actual_calibration_records', 'actual_proposal_started_calls')} for r in rows]
    if cold['cases'] != expected_cold:
        raise ValueError('paired original cold cases differ from actual public returns')
    result = []
    for case, row in zip(plan['cases'], rows, strict=True):
        if (row['request_sha256'] != case['request_sha256'] or digest(case['request']) != case['request_sha256']
                or row['new_native_worlds'] != 0 or row['new_scientific_loss'] is not None
                or row['visibility']['any_phase_interpretation_mismatch_calls']
                or row['visibility']['uncommitted_responses']):
            raise ValueError('literal technical request/known completion/no new scientific outcome required')
        definition = row['public_proposal_result']['definition']
        available = 'generation_failure' not in definition
        if row['free_submission_available'] is not available:
            raise ValueError('known no-submission must not be replaced by parent')
        result.append({'label': row['label'], 'request_sha256': row['request_sha256'],
            'free_submission_available': available,
            'actual_calibration_records': row['actual_calibration_records'],
            'actual_proposal_started_calls': row['actual_proposal_started_calls'],
            'implementation_phase_calls': row['implementation_phase_calls'],
            'phase_counts': clone(row['visibility']['phase_counts']),
            'missing_or_different_loss_views': row['visibility']['missing_or_different_loss_views'],
            'literal_base_change': base_change(case['request']['parent_system'], definition),
            'free_transport_usage': usage(row['generation_transport']), 'new_native_loss': None})
    return {'schema': SCHEMA, 'assay_source_commit': plan['source_commit'],
        'plan_content_sha256': plan['content_sha256'], 'cases': result,
        'new_model_calls': 0, 'new_generated_code_executions': 0, 'new_native_worlds': 0,
        'selection_changed': False, 'publication_ready': False,
        'scope': 'Three predeclared technical shapes, not independent scientific populations, '
            'an optimization comparison, useful invention or loss improvement. Directed readiness, '
            'actual free checkpoints, literal edits, fixture feedback and native loss are separate.'}


def export(args):
    root, source, output = args.run.resolve(), args.assay_source.resolve(), args.output.resolve()
    if output.exists() or any(output.is_relative_to(p) for p in (ROOT.resolve(), root, source)):
        raise ValueError('fresh output outside reader/assay source and raw evidence required')
    reader = pinned_revision(ROOT)
    with (root / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_SH | fcntl.LOCK_NB)
        before = _inventory(root); plan = read(root / 'plan.json'); terminal = read(root / 'terminal.json')
        if pinned_revision(source) != plan['source_commit']:
            raise ValueError('exact unchanged original assay source required')
        if args.cold_one.read_bytes() != args.cold_two.read_bytes():
            raise ValueError('paired original cold outputs differ')
        cold = read(args.cold_one, False)
        rows = [read(root / (label + '.result.json')) for label in LABELS]
        report = project(plan, terminal, rows, cold)
        calibration, proposal, loads = [], [], []
        for case, original, row in zip(plan['cases'], rows, report['cases'], strict=True):
            directory = root / case['label']; identity = case['request_sha256']
            certificate = read(original['certificate'])
            if file_sha256(original['certificate']) != original['certificate_file_sha256']:
                raise ValueError('original certificate changed')
            records = certificate['records']
            if (len(records) != original['actual_calibration_records'] or not certificate['all_controls_passed']
                    or not all(r['ok'] for r in records)):
                raise ValueError('actual directed calibration differs')
            row['calibration_copy_diagnostics'] = dict(sorted(Counter(
                'exact' if r['copy_diagnostic']['exact_match'] else 'noncopy' for r in records).items()))
            observed = [r['transport'] for r in records]
            calibration.extend(observed); row['calibration_transport_usage'] = usage(observed)
            gen = directory / ('proposal-' + identity) / 'editor-session/authoring' / ('generation-' + identity)
            session = read_session(gen)
            if (digest(session) != original['visibility']['session_summary_sha256']
                    or session['started_calls'] != original['actual_proposal_started_calls']
                    or len(original['generation_transport']) != session['completed_steps']):
                raise ValueError('author action summary differs from original visibility')
            row['session'] = {k: clone(session[k]) for k in ('completed_steps', 'attempted_tool_counts',
                'status_counts', 'attempted_edit_steps', 'successful_document_changes',
                'duplicate_unchanged_read_observations', 'explicit_finish_observed', 'terminal_status')}
            probes = 0; probe_status = Counter()
            for path in sorted(gen.glob('step-*.completed.json')):
                step = read(path); feedback = ((step.get('transition') or {}).get('result') or {}).get('component_feedback')
                if feedback is None: continue
                if feedback['probe_offset'] != probes: raise ValueError('component probe prefix changed')
                probes += feedback['probe_attempts']
                for test in feedback['tests']:
                    for value in test['results']: probe_status[value['status']] += 1
            row['recorded_component_probe_attempts'] = probes
            row['component_fixture_status_counts'] = dict(sorted(probe_status.items()))
            proposal.extend(original['generation_transport'])
            for purpose, inner in [('calibration', 'editor-readiness'), ('proposal', 'editor-session')]:
                load = read(directory / (purpose + '-' + identity) / inner / 'designer-load.json')
                loads.append(load)
        started = read(root / 'started.json')
        report.update(calibration_transport_usage=usage(calibration), free_transport_usage=usage(proposal),
            separate_role_load_POSTs=len(loads),
            role_load_token_counts={key: {'known_sum': sum(l['response_payload'][key] for l in loads
                if type(l['response_payload'].get(key)) is int),
                'unknown_responses': sum(type(l['response_payload'].get(key)) is not int for l in loads)}
                for key in ('prompt_eval_count', 'eval_count')},
            shared_host_elapsed_seconds=(datetime.fromisoformat(terminal['ended_utc'])
                - datetime.fromisoformat(started['started_utc'])).total_seconds(),
            dedicated_throughput_benchmark=False, raw_inventory_sha256=digest(before),
            paired_original_cold_file_sha256=file_sha256(args.cold_one))
        if before != _inventory(root) or pinned_revision(ROOT) != reader or pinned_revision(source) != plan['source_commit']:
            raise ValueError('original evidence or reader/source changed during export')
        output.mkdir(parents=True)
        save(output / 'report.json', report)
        save(output / 'manifest.json', {'schema': SCHEMA + '.export', 'reader_source_commit': reader,
            'assay_source_commit': plan['source_commit'], 'raw_inventory_sha256': digest(before),
            'paired_original_cold_file_sha256': file_sha256(args.cold_one),
            'files': {'report.json': file_sha256(output / 'report.json')}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'assay-source', 'cold-one', 'cold-two', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
