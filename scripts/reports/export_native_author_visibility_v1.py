"""Postclosure all8 visibility export from the original paired author/outcome chain.

No waiting/retry, inference, native execution, repair, reselection or rendering.
An unfinished/stopped original chain stops before output creation.
"""
import argparse
import csv
import fcntl
from pathlib import Path
import re

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import same_files
from scripts.reports.native_author_visibility_v1 import read_visibility, join_visibility
from scripts.reports.native_priority_method_readout_v1 import cell_id
from scripts.run_native_priority_fixed_evaluation_v1 import origin_evidence, evidence_files
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-author-visibility-export.v1'
PRECEDING = 'scienceutopia.native-priority-author-outcomes-finish.v1'
FILES = {'report.json', 'authors.csv', 'manifest.json'}


def read(path):
    return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def external(out, roots):
    if out.exists() or any(out.is_relative_to(root) for root in roots):
        raise ValueError('fresh output outside reader/all original sources and evidence required')


def export(args):
    raw, author, author_source, science = (getattr(args, k).resolve()
        for k in ('run', 'author_outcomes', 'author_source', 'scientific_source'))
    out = args.output.resolve()
    external(out, (ROOT.resolve(), raw, author, author_source, science))
    reader = pinned_revision(ROOT); author_head = pinned_revision(author_source); scientific = pinned_revision(science)
    inputs = {}

    def bound(path):
        if path.is_symlink(): raise ValueError('literal original evidence file required')
        inputs[str(path)] = file_sha256(path)
        return read(path)

    start, end = bound(author / 'started.json'), bound(author / 'ended.json')
    if set(start['origin']) != {'run', 'source', 'analysis', 'readouts'}:
        raise ValueError('exact original origin paths required')
    origin = {k: str(Path(v).resolve()) for k, v in start['origin'].items()}
    external(out, tuple(Path(v) for v in origin.values()))
    if (start['schema'] != PRECEDING or start['analysis_source_commit'] != author_head
            or start['scientific_source_commit'] != scientific
            or origin['run'] != str(raw) or origin['source'] != str(science)
            or start['new_inference_allowed'] or start['retry_failed_stages']
            or end['status'] != 'closed' or end['new_model_calls'] or end['new_native_worlds']
            or end['steps'] != [{'stage': 'report-1', 'exit_code': 0}, {'stage': 'report-2', 'exit_code': 0}]):
        raise ValueError('normally closed exact original author/outcome continuation required')
    paired = same_files(author / 'report-1', author / 'report-2')
    if set(paired) != FILES or paired != end['report_files']:
        raise ValueError('all three identical original author/outcome export files required')
    for i in (1, 2):
        inputs.update({str(author / f'report-{i}' / name): sha for name, sha in paired.items()})
    report = bound(author / 'report-1/report.json'); manifest = bound(author / 'report-1/manifest.json')
    if (report['analysis_source_commit'] != author_head or report['scientific_source_commit'] != scientific
            or report['new_model_calls'] or report['new_code_executions'] or report['selection_changed']
            or manifest['analysis_source_commit'] != author_head or manifest['scientific_source_commit'] != scientific
            or manifest['new_model_calls'] or manifest['new_code_executions']
            or manifest['files'] != {k: v for k, v in paired.items() if k != 'manifest.json'}):
        raise ValueError('literal original no-new-science author report/manifest required')
    allowed = [Path(p) for p in origin.values()]
    for name, sha in manifest['input_files'].items():
        path = Path(name)
        if (not path.is_absolute() or path.is_symlink() or not path.is_file()
                or not any(path.resolve().is_relative_to(r) for r in allowed)
                or file_sha256(path) != sha):
            raise ValueError('original author report input changed or escaped declared roots')
        inputs[name] = sha
    origin.update(source_commit=scientific,
        input_files={str(p): file_sha256(p) for p in evidence_files(origin)})
    if any(inputs.get(name) != sha for name, sha in origin['input_files'].items()):
        raise ValueError('original joined manifest must bind the complete scientific closure')
    with (raw / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_SH | fcntl.LOCK_NB)
        plan, audit, _ = origin_evidence(origin)
        if (file_sha256(raw / 'plan.json') != start['plan_file_sha256']
                or plan['source_commit'] != scientific
                or report['original_raw_inventory_sha256'] != audit['raw_inventory_sha256']):
            raise ValueError('original plan and complete audited raw inventory required')
        expected = [s for s in plan['schedule'] if s['method'] == 'free-code-graph']
        if (len(expected) != 8 or [r['cell_id'] for r in report['rows']] != [cell_id(s) for s in expected]):
            raise ValueError('all8 exact original scheduled free cells required')
        extras = []
        for row, slot in zip(report['rows'], expected, strict=True):
            value = None
            if row['session'] is not None:
                request = row['request_sha256']
                if not isinstance(request, str) or not re.fullmatch('[0-9a-f]{64}', request):
                    raise ValueError('literal original request identity required')
                directory = raw / 'search/free-code-graph' / ('history-' + str(slot['replication'])) / slot['objective']
                directory = directory / 'authoring' / ('proposal-' + request) / 'editor-session/authoring' / ('generation-' + request)
                if not directory.resolve().is_relative_to(raw): raise ValueError('author journal escaped original raw')
                value = read_visibility(directory); inputs.update(value['file_sha256'])
                request_binding = decode_json((directory / 'request.json').read_text(), strict=True, finite_floats=True)
                if (request_binding['request_sha256'] != request
                        or request_binding['request']['generation'] != slot['generation']
                        or request_binding['request']['loss_spec'] != plan['losses'][slot['objective']]):
                    raise ValueError('visibility request must match its actual scheduled generation/objective')
            extras.append({'cell_id': row['cell_id'], 'visibility': value})
        result = join_visibility(report, extras)
        result.update(analysis_source_commit=reader, original_author_source_commit=author_head,
            original_plan_content_sha256=plan['content_sha256'],
            original_raw_inventory_sha256=audit['raw_inventory_sha256'],
            export_provenance='Original normal paired author exports, full original closure/raw inventory '
                'and all declared input hashes are checked. No new backend transport/native replay '
                'or corrected-author model proof is performed.',
            full_native_or_transport_audit_repeated=False, publication_ready=False)

        def unchanged():
            if (digest(_inventory(raw)) != audit['raw_inventory_sha256']
                    or any(file_sha256(p) != sha for p, sha in inputs.items())
                    or pinned_revision(ROOT) != reader or pinned_revision(author_source) != author_head
                    or pinned_revision(science) != scientific):
                raise ValueError('original data or reader/author/scientific source changed during export')

        unchanged(); out.mkdir(parents=True); save(out / 'report.json', result)
        fields = ['cell_id', 'native_status', 'native_loss', 'row_kind', 'step', 'recorded_phase',
            'expected_phase_using_actual_body', 'whole_document_actually_supplied',
            'inspection_attempts', 'successful_inspections', 'serializer_visibility_phase_mismatch',
            'exact_loss_arithmetic_and_definitions_present', 'response_status', 'attempted_tool']
        with (out / 'steps.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for row in result['rows']:
                value = row['visibility']; base = {'cell_id': row['cell_id'],
                    'native_status': row['status'], 'native_loss': row['loss']}
                steps = [] if value is None else value['rows']
                if not steps:
                    writer.writerow({**base, 'row_kind': 'missing-session' if value is None else 'empty-recorded-session'})
                for step in steps:
                    writer.writerow({**base, 'row_kind': 'recorded-intent',
                        **{k: step[k] for k in fields if k in step}})
        save(out / 'manifest.json', {'schema': SCHEMA, 'analysis_source_commit': reader,
            'scientific_source_commit': scientific, 'original_author_source_commit': author_head,
            'input_files': inputs, 'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
            'new_model_calls': 0, 'new_generated_code_executions': 0, 'scientific_losses_rewritten': False})
        unchanged()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'author-outcomes', 'author-source', 'scientific-source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
