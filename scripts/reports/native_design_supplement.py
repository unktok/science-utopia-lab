"""Closed V2 all-trial cross-scores, per-method costs and outside metrics.

Reads exact retained projections only. No model, generated code or world runs.
"""
import argparse
from collections import Counter
from copy import deepcopy
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import subprocess

from scripts.reports.native_design_benchmark import checked, SCHEMA
from scripts.reports.native_design_reproduce import load_report, DATA, ROOT
from scripts.reports.native_design_tex import summarize, METHODS, LABELS, RUNS
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json

LOSSES = ('throughput', 'selective', 'efficiency')
METRICS = ('accepted_decisions', 'accepted_peer_score_sum', 'review_records',
           'final_active_authors', 'final_author_resources', 'accepted_unreviewed_decisions',
           'rejected_decisions', 'institutional_context_deliveries')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def load_inputs(root):
    root = Path(root)
    manifest = json.loads((root / DATA / 'manifest.json').read_text())
    report = load_report((root / DATA / manifest['archive']).read_bytes(), manifest)
    supplements = json.loads((root / DATA / 'supplemental-inputs.json').read_text())
    result = {}
    for key, spec in supplements['inputs'].items():
        archive = (root / DATA / spec['file']).read_bytes()
        if len(archive) > 4*1024**2 or sha(archive) != spec['archive_sha256']:
            raise ValueError('exact bounded supplemental archive required')
        with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
            body = stream.read(16*1024**2+1)
        if len(body) != spec['uncompressed_bytes'] or sha(body) != spec['uncompressed_sha256']:
            raise ValueError('exact bounded cost projection required')
        value = decode_json(body.decode(), strict=True, finite_floats=True)
        checked(value, spec['schema'])
        if (value['content_sha256'] != spec['content_sha256']
                or value['source_commit'] != report['source_commit']
                or value['input_audit_content_sha256'] != report['input_audit_content_sha256']):
            raise ValueError('cost projection source/audit differs')
        result[key] = value
    return report, result['auxiliary'], result['scientist']


def values(metrics):
    return {name: None if not isinstance(metrics, dict)
            or metrics.get('native.'+name, {}).get('status') != 'measured'
            else metrics['native.'+name]['value'] for name in METRICS}


def project(report, auxiliary, scientist):
    table = summarize(report, expected_source=report['source_commit'])
    checked(auxiliary, 'scienceutopia.native-auxiliary-model-costs.v1')
    checked(scientist, 'scienceutopia.native-scientist-token-costs.v1')
    if any(x['input_audit_content_sha256'] != report['input_audit_content_sha256']
           or x['source_commit'] != report['source_commit'] for x in (auxiliary, scientist)):
        raise ValueError('common exact source/audit required')
    if scientist['wire_only_worlds'] or scientist['wire_inputs_without_committed_reply']:
        raise ValueError('this retained study requires explicit full wire/reply accounting')
    trials = []; method_costs = []
    for run in RUNS:
        for objective in LOSSES[:2]:
            for method in METHODS:
                arm = objective+':'+method
                body = report['search_arms'][run][arm]
                author = auxiliary['proposal_runs'][run][arm]
                if author['author_absent_by_design'] != (method == 'random'):
                    raise ValueError('designer absence differs from assigned method')
                generations = {g['request_sha256']: g for g in author['generations']}
                if len(generations) != (0 if method == 'random' else 4):
                    raise ValueError('exact four designer generations or declared absence required')
                native = body['native_costs']; cumulative = 0.; incumbent = body['initial_loss']; completed_times = []
                for row in body['rows']:
                    if row['physical_forward_completed']:
                        elapsed = row['physical_evidence']['annual_checkpoints'][-1]['llm_call_stats'].get('elapsed_seconds')
                        if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:
                            raise ValueError('explicit completed-world scientist time required, not zero imputation')
                        completed_times.append(elapsed)
                    if method == 'random':
                        charge = 0.; requests = 0; present = False
                    else:
                        g = generations[row['authoring_diagnostics']['request_sha256']]
                        measured = g['measurements']['host_model_call_seconds']
                        charge = measured['recorded_sum'] if measured['all_records_known'] else None
                        requests = g['request_intents']; present = True
                    cumulative = cumulative+charge if cumulative is not None and charge is not None else None
                    if row['own_loss'] is not None:
                        incumbent = min(incumbent, row['own_loss'])
                    if incumbent != row['best_including_initial_so_far']:
                        raise ValueError('best path differs from all observed losses')
                    trials.append({k: deepcopy(row[k]) for k in
                        ('row_id', 'run', 'arm', 'generation', 'status', 'own_loss', 'cross_scores',
                         'system_fingerprint', 'best_including_initial_so_far')} |
                        {'metrics': values(row['metrics']), 'initial_loss': body['initial_loss'],
                         'designer_present_by_design': present, 'designer_request_intents': requests,
                         'designer_host_model_seconds': charge,
                         'cumulative_designer_host_model_seconds': cumulative})
                known = author['measurements']['host_model_call_seconds']
                if known['all_records_known'] and not math.isclose(
                        cumulative, known['recorded_sum'], rel_tol=1e-12, abs_tol=1e-9):
                    raise ValueError('per-generation model seconds differ from method aggregate')
                if not math.isclose(math.fsum(completed_times), native['completed_researcher_model_call_seconds'],
                                    rel_tol=1e-12, abs_tol=1e-9):
                    raise ValueError('completed-only scientist time differs from recorded checkpoints')
                group = scientist['groups'].get('search:'+run+':'+arm.replace(':', '--'))
                if group is None and native['physical_researcher_responses'] != 0:
                    raise ValueError('recorded scientist replies lack usage group')
                if group is not None and any(v['known_responses']+v['missing_responses']+v['invalid_responses']
                                            != native['physical_researcher_responses'] for v in group.values()):
                    raise ValueError('scientist response and usage counts differ')
                method_costs.append({'run': run, 'arm': arm, 'scheduled_slots': 4,
                    'status_counts': dict(Counter(r['status'] for r in body['rows'])),
                    'best_including_initial': body['best_including_initial'],
                    'designer': deepcopy(author), 'native': deepcopy(native),
                    'scientist_usage': deepcopy(group), 'zero_recorded_replies_when_group_absent': group is None,
                    'initial_reference_calibration_load_or_evaluation_costs_included': False})
    jobs = []
    for job in report['evaluation']:
        if len(job['raw_measurements']) != 1:
            raise ValueError('one native measurement per physical evaluation required')
        jobs.append({k: deepcopy(job[k]) for k in
                    ('job_id', 'labels', 'policy_sha256', 'seed', 'years', 'observation_status', 'cross_scores')} |
                    {'metrics': values(job['raw_measurements'][0]['metrics'])})
    summaries = []
    for label in ['reference:'+r for r in ('legacy', 'open-seed', 'open-rank-rate', 'open-accept-all',
                  'open-reject-all', 'open-score-3', 'open-score-4', 'open-no-review-accept-all',
                  'open-no-review-reject-all')] + ['selected:'+o+':'+m for o in LOSSES[:2] for m in METHODS]:
        for years in (2, 4):
            selected = [j for j in jobs if label in j['labels'] and j['years'] == years]
            if len(selected) != (5 if years == 2 else 1):
                raise ValueError('exact unused-condition outside-metric jobs required')
            summary = {'label': label, 'years': years, 'job_ids': [j['job_id'] for j in selected],
                       'policy_sha256': selected[0]['policy_sha256'], 'metrics': {}}
            for metric in METRICS:
                raw = [j['metrics'][metric] for j in selected]; known = [v for v in raw if v is not None]
                summary['metrics'][metric] = {'raw': raw, 'available': len(known), 'missing': len(raw)-len(known),
                    'mean': statistics.mean(known) if known else None,
                    'minimum': min(known) if known else None, 'maximum': max(known) if known else None}
            summaries.append(summary)
    pooled = []
    for arm in (o+':'+m for o in LOSSES[:2] for m in METHODS):
        group = [r for r in method_costs if r['arm']==arm]
        times = [r['designer']['measurements']['host_model_call_seconds'] for r in group]
        pooled.append({'arm':arm, 'scheduled_slots':12,
            'status_counts':dict(sum((Counter(r['status_counts']) for r in group),Counter())),
            'designer_request_intents':sum(r['designer']['request_intents'] for r in group),
            'designer_final_signals':sum(r['designer']['final_response_reported'] for r in group),
            'designer_host_seconds_known_sum':math.fsum(t['recorded_sum'] for t in times if t['recorded_sum'] is not None),
            'designer_host_seconds_all_known':all(t['all_records_known'] for t in times),
            'native_recorded_responses':sum(r['native']['physical_researcher_responses'] for r in group),
            'native_completed_only_model_seconds':math.fsum(r['native']['completed_researcher_model_call_seconds'] for r in group),
            'native_recorded_world_directories':sum(r['native']['physical_world_directory_count'] for r in group),
            'native_recorded_code_executions':sum(r['native']['recorded_code_executions_including_partial'] for r in group)})
    result = {'schema': 'scienceutopia.native-design-supplement.v1',
        'input_report_content_sha256': report['content_sha256'],
        'input_audit_content_sha256': report['input_audit_content_sha256'],
        'auxiliary_content_sha256': auxiliary['content_sha256'], 'scientist_content_sha256': scientist['content_sha256'],
        'trials': trials, 'per_history_method_costs': method_costs, 'pooled_method_costs':pooled, 'evaluation_jobs': jobs,
        'outside_metric_summaries': summaries, 'search_counts': table['counts'],
        'cumulative_cost_axis': 'Recorded host designer model-call seconds ONLY; not scientist time, total compute or wall time.',
        'common_initial_reference_and_calibration_load_costs_excluded_from_search_paths': True,
        'unknown_scientist_usage_imputed_when_group_absent': False,
        'horizons_or_shared_jobs_counted_as_extra_replication': False,
        'null_losses_imputed': False, 'new_model_calls': 0, 'new_code_executions': 0}
    result['content_sha256'] = digest(result)
    return result


def csv_file(path, columns, rows):
    with path.open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader()
        writer.writerows(rows)


def write_tables(data, output):
    output = Path(output)
    csv_file(output/'all-search-observations.csv',
        ['row_id', 'status', *LOSSES, *METRICS, 'designer_request_intents', 'designer_host_model_seconds',
         'cumulative_designer_host_model_seconds'],
        [dict(row_id=r['row_id'], status=r['status'], **r['cross_scores'], **r['metrics'],
              **{k:r[k] for k in ('designer_request_intents', 'designer_host_model_seconds',
                                'cumulative_designer_host_model_seconds')}) for r in data['trials']])
    csv_file(output/'evaluation-physical-observations.csv',
        ['job_id', 'labels', 'policy_sha256', 'seed', 'years', *LOSSES, *METRICS],
        [dict(job_id=r['job_id'], labels=json.dumps(r['labels']), policy_sha256=r['policy_sha256'],
              seed=r['seed'], years=r['years'], **r['cross_scores'], **r['metrics'])
         for r in data['evaluation_jobs']])
    rows = []
    for r in data['per_history_method_costs']:
        author = r['designer']; m = author['measurements']; native = r['native']
        rows.append({'run':r['run'], 'arm':r['arm'], 'complete':r['status_counts'].get('complete', 0),
            'designer_intents':author['request_intents'], 'designer_final_signals':author['final_response_reported'],
            'designer_input_tokens':m['native_prompt_eval_count']['recorded_sum'],
            'designer_output_tokens':m['native_eval_count']['recorded_sum'],
            'designer_cached_subset_tokens':m['native_prompt_eval_cached_count']['recorded_sum'],
            'designer_host_seconds':m['host_model_call_seconds']['recorded_sum'],
            'native_recorded_responses':native['physical_researcher_responses'],
            'native_recorded_world_directories':native['physical_world_directory_count'],
            'native_recorded_code_executions':native['recorded_code_executions_including_partial'],
            'native_completed_only_model_seconds':native['completed_researcher_model_call_seconds'],
            **{'scientist_'+name:None if r['scientist_usage'] is None
               else r['scientist_usage'][name]['recorded_sum']
               for name in ('prompt_tokens','completion_tokens','cached_prompt_tokens')}})
    csv_file(output/'per-history-method-costs.csv', list(rows[0]), rows)
    columns = [k for k in data['pooled_method_costs'][0] if k!='status_counts']
    csv_file(output/'pooled-method-costs.csv', columns,
             [{k:r[k] for k in columns} for r in data['pooled_method_costs']])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error('fresh output directory required')
    git = lambda *a: subprocess.check_output(['git', '-C', str(ROOT), *a], text=True).strip()
    source = git('rev-parse', 'HEAD')
    if git('status', '--porcelain'):
        raise ValueError('commit source and exact inputs before supplement reconstruction')
    names = [DATA+n for n in ('manifest.json', 'closed-report.json.gz', 'supplemental-inputs.json',
                              'auxiliary-costs.json.gz', 'scientist-token-costs.json.gz')]
    before = {n:(ROOT/n).read_bytes() for n in names}
    for name, body in before.items():
        if subprocess.check_output(['git', '-C', str(ROOT), 'show', source+':'+name]) != body:
            raise ValueError('retained numerical inputs differ from HEAD')
    report, auxiliary, scientist = load_inputs(ROOT)
    data = project(report, auxiliary, scientist)
    args.output.mkdir(parents=True); write_tables(data, args.output)
    from scripts.figures.native_design_supplement import plot
    plot(data, args.output)
    (args.output/'supplement.json').write_text(json.dumps(data, sort_keys=True, indent=2)+'\n')
    manifest = {'schema':'scienceutopia.native-design-supplement-files.v1',
        'analysis_source_commit':source, 'input_file_sha256':{n:sha(b) for n,b in before.items()},
        'input_report_content_sha256':report['content_sha256'], 'supplement_content_sha256':data['content_sha256'],
        'files':{p.name:sha(p.read_bytes()) for p in sorted(args.output.iterdir()) if p.is_file()},
        'new_model_calls':0, 'new_code_executions':0}
    if (git('rev-parse', 'HEAD') != source or git('status', '--porcelain')
            or any((ROOT/n).read_bytes() != body for n,body in before.items())):
        raise ValueError('source or input changed during reconstruction; preserve incomplete output')
    manifest['content_sha256'] = digest(manifest)
    (args.output/'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
    print(json.dumps({'content_sha256':manifest['content_sha256'], 'files':len(manifest['files'])}))
    return 0


if __name__ == '__main__': raise SystemExit(main())
