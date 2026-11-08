"""Rebuild actual V2 numerical tables/plots offline from the retained projection.

No simulation, generated institutional code, model endpoint or raw audit runs.
This is numerical reproduction, not an independent validation of raw evidence.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

from scripts.figures.native_design_benchmark import plot_search
from scripts.figures.native_design_cross_objective import cross_objective_data, plot_cross_objective
from scripts.figures.native_design_evaluation import plot_evaluation
from scripts.reports.native_design_benchmark import checked, SCHEMA
from scripts.reports.native_design_tex import summarize, render
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json

ROOT = Path(__file__).resolve().parents[2]
DATA = 'research/data/native-design-v2/'
INPUTS = (DATA + 'manifest.json', DATA + 'closed-report.json.gz',
          'paper/generated/native-design-v2/search-outcomes-data.json',
          'paper/generated/native-design-v2/search-outcomes.tex',
          'paper/generated/native-design-v2/cross-score-data.json',
          'research/results/native-design-freedom-v2-paper-evidence-v1.json')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def load_report(archive, manifest):
    if (manifest['schema'] != 'scienceutopia.native-design-numerical-inputs.v1'
            or manifest['classification'] != 'actual-native-design-freedom-study-v2'
            or len(archive) != manifest['archive_bytes'] or len(archive) > 4 * 1024**2
            or sha(archive) != manifest['archive_sha256']):
        raise ValueError('exact retained numerical archive required')
    with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
        body = stream.read(16 * 1024**2 + 1)
    if (len(body) != manifest['uncompressed_bytes'] or len(body) > 16 * 1024**2
            or sha(body) != manifest['uncompressed_sha256']):
        raise ValueError('exact bounded report bytes required')
    report = decode_json(body.decode(), strict=True, finite_floats=True)
    checked(report, SCHEMA + '.report')
    if (report['content_sha256'] != manifest['report_content_sha256']
            or report['input_audit_content_sha256'] != manifest['audit_content_sha256']
            or report['source_commit'] != manifest['experiment_source_commit']
            or report['classification'] != manifest['classification']):
        raise ValueError('report source/audit/classification differs')
    return report


def measurement_arithmetic(report):
    """Recompute loss algebra separately; never replace audited IEEE values."""
    residuals = []; counts = Counter()
    metrics = [(r['metrics'], r['cross_scores'], 'search') for r in report['all_candidate_rows']
               if r['status'] == 'complete']
    for job in report['evaluation']:
        if job['observation_status'] != 'complete' or len(job['raw_measurements']) != 1:
            raise ValueError('one measured native evaluation per physical job required')
        metrics.append((job['raw_measurements'][0]['metrics'], job['cross_scores'], 'evaluation'))
    for values, scores, scope in metrics:
        keys = ('native.accepted_decisions', 'native.accepted_peer_score_sum', 'native.review_records')
        if any(values[k]['status'] != 'measured' for k in keys):
            raise ValueError('measured A/Q/R required for this retained study')
        a, q, r = [values[k]['value'] for k in keys]
        expected = {'throughput': -a, 'selective': 4*a-q+0.1*r, 'efficiency': -q+0.5*r}
        for key, value in expected.items():
            if not math.isclose(value, scores[key], rel_tol=1e-13, abs_tol=1e-13):
                raise ValueError('raw A/Q/R differs from loss algebra')
            residuals.append(abs(value-scores[key]))
        counts[scope] += 1
    return {'measured_forwards': dict(counts), 'loss_values_recomputed': len(residuals),
            'maximum_absolute_roundoff': max(residuals), 'audited_scores_replaced': False,
            'tolerance_for_independent_arithmetic_only': 1e-13}


def resource_arithmetic(evidence):
    scientist = evidence['scientist_costs']; usage = scientist['usage']
    if (usage['prompt_tokens']['recorded_sum'] + usage['completion_tokens']['recorded_sum']
            != usage['total_tokens']['recorded_sum']
            or usage['cached_prompt_tokens']['recorded_sum'] > usage['prompt_tokens']['recorded_sum']):
        raise ValueError('scientist totals or cache subset differ')
    rows = [{'stream': 'scientists', 'completion_records': scientist['completed_responses'],
        'input_tokens': usage['prompt_tokens']['recorded_sum'],
        'output_tokens': usage['completion_tokens']['recorded_sum'],
        'cached_subset_tokens': usage['cached_prompt_tokens']['recorded_sum']}]
    for name, body in evidence['auxiliary_costs']['groups'].items():
        m = body['measurements']
        rows.append({'stream': name, 'completion_records': body['completion_record_available'],
            'final_response_reported': body['final_response_reported'],
            'input_tokens': m['native_prompt_eval_count']['recorded_sum'],
            'output_tokens': m['native_eval_count']['recorded_sum'],
            'cached_subset_tokens': m['native_prompt_eval_cached_count']['recorded_sum']})
    if (scientist['unknown_usage_imputed'] or evidence['auxiliary_costs']['unknown_usage_imputed']
            or evidence['auxiliary_costs']['cached_prompt_counts_added_to_input_totals']
            or evidence['auxiliary_costs']['token_aliases_or_nested_durations_added']):
        raise ValueError('unknown costs, cache subsets or aliases must not be imputed/added')
    return {'rows': rows, 'writer_wall_seconds': evidence['writer_wall_seconds'],
        'rechecks_retained_aggregates_not_raw_response_usage': True,
        'cached_counts_added_again': False, 'unknowns_imputed': False,
        'overlapping_timing_scopes_added': False, 'full_project_compute_claimed': False}


def rebuild(root, output):
    root = Path(root).resolve(); output = Path(output)
    if output.exists() or output.is_symlink() or root.is_relative_to(output.resolve()):
        raise ValueError('fresh non-source destination required')
    before = {n: (root / n).read_bytes() for n in INPUTS}
    manifest = json.loads(before[DATA + 'manifest.json'])
    report = load_report(before[DATA + 'closed-report.json.gz'], manifest)
    data = summarize(report, expected_source=manifest['experiment_source_commit'])
    cross = cross_objective_data(report)
    if data != json.loads(before[INPUTS[2]]) or render(data).encode() != before[INPUTS[3]]:
        raise ValueError('rebuilt table differs from manuscript data or exact ties')
    if cross != json.loads(before[INPUTS[4]]):
        raise ValueError('rebuilt common scores differ from manuscript raw jobs/labels')
    arithmetic = measurement_arithmetic(report)
    resources = resource_arithmetic(json.loads(before[INPUTS[5]]))
    output.mkdir(parents=True)
    (output / 'search-outcomes.tex').write_text(render(data))
    (output / 'search-outcomes-data.json').write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')
    (output / 'resource-usage.json').write_text(json.dumps(resources, sort_keys=True, indent=2) + '\n')
    plot_search(report, output / 'search-figures')
    plot_cross_objective(report, output / 'cross-objective-figures', paper=True)
    plot_evaluation(report, output / 'paired-figures')
    result = {'schema': 'scienceutopia.native-design-numerical-rebuild.v1',
        'input_hashes': {n: sha(b) for n, b in before.items()},
        'report_content_sha256': report['content_sha256'],
        'audit_content_sha256': report['input_audit_content_sha256'],
        'experiment_source_commit': report['source_commit'],
        'search_counts': data['counts'], 'physical_evaluation_jobs': report['physical_evaluation_jobs'],
        'table_and_cross_score_data_match_retained_manuscript': True,
        'raw_measurement_loss_arithmetic': arithmetic,
        'output_files': {str(p.relative_to(output)): sha(p.read_bytes())
                         for p in sorted(output.rglob('*')) if p.is_file()},
        'null_losses_imputed': False, 'new_model_calls': 0, 'new_code_executions': 0,
        'raw_audit_or_fresh_inference_reproduced': False, 'published_or_uploaded': False}
    if any((root / n).read_bytes() != body for n, body in before.items()):
        raise ValueError('retained inputs changed during rebuilding; preserve incomplete output')
    result['content_sha256'] = digest(result)
    (output / 'numerical-rebuild.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    git = lambda *a: subprocess.check_output(['git', '-C', str(ROOT), *a], text=True).strip()
    commit = git('rev-parse', 'HEAD')
    if git('status', '--porcelain'):
        raise ValueError('commit source and retained data before numerical rebuild')
    for name in INPUTS:
        if subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name]) != (ROOT / name).read_bytes():
            raise ValueError('numerical input differs from committed source: ' + name)
    result = rebuild(ROOT, args.output)
    if git('rev-parse', 'HEAD') != commit or git('status', '--porcelain'):
        raise ValueError('source changed during rebuild')
    print(json.dumps({'analysis_source_commit': commit, 'content_sha256': result['content_sha256'],
                      'output_files': len(result['output_files'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
