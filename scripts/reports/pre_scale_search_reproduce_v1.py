"""Check/rebuild retained CLOSED O/E numerical observations, not a raw audit.

No model, simulator, generated source or network is executed. Exact policies,
null slots, selection ties, independent physical jobs and all raw metric statuses
remain explicit. Passing these checks is not fresh inference or replication.
"""
import argparse
from collections import Counter
import csv
import io
import json
import math
from pathlib import Path

from scripts.native_design_benchmark_plan import policy_identity
from scripts.reports.native_design_benchmark import descriptive,number
from scripts.reports.pre_scale_search_v1 import OBJECTIVES,METHODS,render
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic

SCORES=('throughput','efficiency','selective')
SEEDS=(51001,51011,51017)
REFERENCES=('open-seed','legacy','reviewed-accept-all','no-review-accept-all','no-review-reject-all','information-disconnected')
EVAL_REFERENCES=('open-seed','reviewed-accept-all','no-review-accept-all','no-review-reject-all')
METRICS={'A':'native.accepted_decisions','Q':'native.accepted_peer_score_sum','R':'native.review_records'}
TERMS={'throughput':{'A':-1.},'efficiency':{'Q':-1.,'R':.5},'selective':{'A':4.,'Q':-1.,'R':.1}}


def measurement_scores(world):
    scores=world['scores']
    if set(scores)!=set(SCORES):raise ValueError('all three cross-score statuses required')
    measurement=world['measurement']
    if measurement is None:
        if any(number(v) is not None for v in scores.values()):raise ValueError('score lacks recorded measurement')
        return
    if world['physical_forward_status']!='complete':raise ValueError('measurement without completed physical checkpoint')
    metrics=measurement['metrics'];values={}
    for key,metric in METRICS.items():
        record=metrics.get(metric)
        values[key]=None if record is None or record['status']!='measured' else number(record['value'])
    for key,terms in TERMS.items():
        observed=number(scores[key])
        if observed is None:continue  # Unknown is not recomputed into an assigned success.
        if any(values[term] is None for term in terms):raise ValueError('available loss uses an unavailable raw metric')
        expected=math.fsum(weight*values[term] for term,weight in terms.items())
        if not math.isclose(observed,expected,rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('cross-score differs from retained A/Q/R')


def validate(report):
    checked(report)
    native=report['schema']=='scienceutopia.native-institution-loop-report.v1'
    if native:
        methods=('parameters','code-fixed-graph','code-and-graph');seed=61001
        seeds=(62001,62011,62017)
        references=('open-seed','legacy','reviewed-accept-all','no-review-accept-all',
            'no-review-reject-all','routed-one-accept-all','routed-two-accept-all','routed-one-reject-all')
        eval_references=('legacy','reviewed-accept-all','no-review-accept-all','routed-one-accept-all','routed-two-accept-all')
        if report.get('methods')!=list(methods) or report.get('evaluation_seeds')!=list(seeds):
            raise ValueError('native loop declared methods/seeds differ')
    elif report['schema']=='scienceutopia.pre-scale-search-report.v1':
        methods,seed,seeds,references,eval_references=METHODS,41001,SEEDS,REFERENCES,EVAL_REFERENCES
    else:raise ValueError('closed search report required')
    systems=report['systems_by_sha256']
    if any(digest(v)!=k for k,v in systems.items()):raise ValueError('retained executable system identity differs')
    worlds={w['identity']:w for w in report['worlds']}
    if len(worlds)!=len(report['worlds']):raise ValueError('duplicate physical world')
    for world in worlds.values():
        if world['system_sha256'] not in systems:raise ValueError('physical system omitted from retained source dictionary')
        measurement_scores(world)
        assigned=world['role'].split(':')[1] if world['role'].startswith('search:') else 'throughput'
        if world['status']=='complete' and world['scores'][assigned] is None:raise ValueError('complete assigned result lacks its loss')
    refs={r['row_id']:r for r in report['references']}
    if set(refs)!={'reference:'+r for r in references}:raise ValueError('all declared development references required')
    initial=refs['reference:open-seed'];slots=report['search_slots'];arms=[o+':'+m for m in methods for o in OBJECTIVES]
    order=[(arm,g) for g in range(2) for arm in arms[g:]+arms[:g]]
    if len(slots)!=2*len(arms) or [(r['arm'],r['generation']) for r in slots]!=order:
        raise ValueError('all slots in declared dispatch order required')
    if report['status_counts']!=dict(Counter(r['status'] for r in slots)):
        raise ValueError('all-slot status counts differ')
    rows={**refs,**{r['row_id']:r for r in slots}}
    if len(rows)!=len(references)+2*len(arms) or set(report['development_world_bindings'])!=set(rows):raise ValueError('complete development/physical join required')
    used=[]
    for identity,row in rows.items():
        if type(row['forward_complete']) is not bool or row['status'] not in ('complete','failed','invalid','generation-failure'):
            raise ValueError('explicit terminal status and forward-availability flag required')
        job=report['development_world_bindings'][identity]
        if row['status']=='generation-failure':
            if job is not None or row['forward_complete'] or any(v is not None for v in row['cross_scores'].values()):
                raise ValueError('null proposal acquired physical activity or a score')
            continue
        world=worlds[job];used.append(job)
        system_sha=digest(row['system']) if row['arm'] is None else row['system_sha256']
        role='developer-reference' if row['arm'] is None else 'search:'+row['arm']
        if world['role']!=role or world['seed']!=seed or world['system_sha256']!=system_sha or world['scores']!=row['cross_scores']:
            raise ValueError('retained development world/score differs')
    if len(set(used))!=len(used):raise ValueError('development forwards shared without declaration')
    if set(report['optimization_paths'])!=set(arms):raise ValueError('all declared optimization paths required')
    for arm,path in report['optimization_paths'].items():
        objective=arm.split(':')[0];best=number(initial['cross_scores'][objective]);pool=[initial]
        ordered=[r for r in slots if r['arm']==arm]
        if (path['initial_comparison_loss']!=best or path['initial_exposed_before_first_proposal'] is not False
                or path['candidate_slots']!=ordered):raise ValueError('path does not retain initial/null candidate chronology')
        for g,row in enumerate(ordered):
            if row['row_id']!=f'run-00:{arm}:g{g}' or row['own_loss']!=row['cross_scores'][objective]:
                raise ValueError('wrong candidate identity or assigned objective')
            value=number(row['own_loss'])
            if value is not None:best=value if best is None else min(best,value)
            if best!=row['best_including_initial_for_final_comparison']:raise ValueError('best-so-far path differs')
            pool.append(row)
        eligible=[r for r in pool if r['forward_complete'] and r['cross_scores'][objective] is not None]
        minimum=min((r['cross_scores'][objective] for r in eligible),default=None)
        ties=[r['row_id'] for r in eligible if r['cross_scores'][objective]==minimum]
        selection=path['fixed_selection']
        if (number(selection['loss'])!=minimum or selection['all_tied_row_ids']!=ties
                or selection['selected_row_id']!=(ties[0] if ties else None)):
            raise ValueError('fixed selection or exact ties differ from retained eligible rows')
        chosen=rows[ties[0]] if ties else None
        system=None if chosen is None else chosen['system'] if chosen['arm'] is None else systems[chosen['system_sha256']]
        if selection['system']!=system or selection['policy_sha256']!=(policy_identity(system) if system is not None else None):
            raise ValueError('selected executable policy differs')
        gain=None if minimum is None or path['initial_comparison_loss'] is None else minimum<path['initial_comparison_loss']
        if path['strict_development_gain_over_initial']!=gain:raise ValueError('development gain label differs')
    global_rows=report['references']+slots
    if set(report['selection_pooled'])!=set(OBJECTIVES):raise ValueError('both pooled development comparisons required')
    for objective,selection in report['selection_pooled'].items():
        eligible=[r for r in global_rows if r['forward_complete'] and r['cross_scores'][objective] is not None]
        minimum=min((r['cross_scores'][objective] for r in eligible),default=None)
        tied=[r for r in eligible if r['cross_scores'][objective]==minimum]
        chosen=tied[0] if tied else None
        system=None if chosen is None else chosen['system'] if chosen['arm'] is None else systems[chosen['system_sha256']]
        if (number(selection['loss'])!=minimum or selection['all_tied_row_ids']!=[r['row_id'] for r in tied]
                or selection['selected_row_id']!=(chosen['row_id'] if chosen else None)
                or selection['system']!=system
                or selection['policy_sha256']!=(policy_identity(system) if system is not None else None)):
            raise ValueError('pooled selection/ties differ from global dispatch order')
    evaluation=report['evaluation_rows'];lookup={(r['label'],r['seed']):r for r in evaluation}
    labels={'reference:'+r for r in eval_references}|{'selected:'+arm for arm,path in report['optimization_paths'].items()
        if path['fixed_selection']['system'] is not None}
    if len(lookup)!=len(evaluation) or set(lookup)!={(label,s) for label in labels for s in seeds}:
        raise ValueError('logical labels and three unused seeds differ')
    physical=set()
    for row in evaluation:
        world=worlds[row['physical_job']];physical.add(row['physical_job'])
        system=systems[world['system_sha256']]
        expected=(refs[row['label']]['system'] if row['label'].startswith('reference:') else
            report['optimization_paths'][row['label'].removeprefix('selected:')]['fixed_selection']['system'])
        if (world['role']!='selection-fixed-evaluation' or world['seed']!=row['seed'] or world['status']!=row['status']
                or world['scores']!=row['scores'] or policy_identity(system)!=policy_identity(expected)):
            raise ValueError('logical evaluation changes its physical policy, seed or scores')
    if (report['physical_evaluation_worlds']!=len(physical) or report['logical_evaluation_rows']!=len(evaluation)
            or set(worlds)!=set(used)|physical):raise ValueError('physical or logical evaluation counts differ')
    summaries={label:{k:descriptive([{'value':lookup[label,s]['scores'][k]} for s in seeds],'value') for k in SCORES} for label in sorted(labels)}
    if summaries!=report['evaluation_summary']:raise ValueError('evaluation summaries differ from retained physical observations')
    pairs=[]
    for row in evaluation:
        if not row['label'].startswith('selected:'):continue
        for ref in eval_references:
            other=lookup['reference:'+ref,row['seed']]
            pairs.append({'label':row['label'],'reference':ref,'seed':row['seed'],
                'shared_same_physical_job':row['physical_job']==other['physical_job'],
                'differences':{k:None if row['scores'][k] is None or other['scores'][k] is None else row['scores'][k]-other['scores'][k] for k in SCORES}})
    if pairs!=report['paired_reference_differences']:raise ValueError('paired reference differences differ')
    return report


def world_csv(report):
    validate(report);buffer=io.StringIO(newline='');writer=csv.writer(buffer)
    writer.writerow(['identity','role','seed','assigned_status','physical_forward_status',
        'A','A_status','Q','Q_status','R','R_status',*SCORES])
    for w in report['worlds']:
        metrics=(w['measurement'] or {}).get('metrics',{});values=[]
        for metric in METRICS.values():
            r=metrics.get(metric);values.extend(['' if r is None or r.get('value') is None else r['value'],'not-recorded' if r is None else r['status']])
        writer.writerow([w['identity'],w['role'],w['seed'],w['status'],w['physical_forward_status'],*values,
            *['' if w['scores'][k] is None else w['scores'][k] for k in SCORES]])
    return buffer.getvalue()


def reproduce(report_path,manifest_path,figures,output):
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (report_path.parent,figures)):
        raise ValueError('fresh independent output required')
    report=validate(json.loads(report_path.read_text()));manifest=checked(json.loads(manifest_path.read_text()))
    names=('objective-conditioned-paths.png','objective-conditioned-paths.svg',
        'selection-fixed-common-scores.png','selection-fixed-common-scores.svg')
    if (manifest['schema']!='scienceutopia.pre-scale-search-figures.v1'
            or manifest['report_content_sha256']!=report['content_sha256'] or set(manifest['files'])!={'report.json',*names}):
        raise ValueError('complete closed report/figure manifest required')
    original={report_path:file_sha256(report_path),manifest_path:file_sha256(manifest_path)}
    if file_sha256(report_path)!=manifest['files']['report.json'] or any(file_sha256(figures/n)!=manifest['files'][n] for n in names):
        raise ValueError('retained report/figure bytes differ')
    output.mkdir(parents=True);write_json_atomic(output/'report.json',report,sort_keys=True,allow_nan=False);render(report,output)
    if any(file_sha256(output/n)!=manifest['files'][n] for n in ('report.json',*names)):
        raise ValueError('rebuilt report/figure bytes differ')
    (output/'world-components.csv').write_text(world_csv(report),newline='')
    if any(file_sha256(p)!=sha for p,sha in original.items()):raise ValueError('retained input changed during rebuild')
    result={'schema':'scienceutopia.native-institution-loop-reproduction.v1' if report['schema']=='scienceutopia.native-institution-loop-report.v1' else 'scienceutopia.pre-scale-search-reproduction.v1','input_report_sha256':report['content_sha256'],
        'original_audit_sha256':report['audit_sha256'],'all_slots_selection_ties_and_shared_jobs_rechecked':True,
        'raw_available_cross_scores_recomputed':sum(v is not None for w in report['worlds'] for v in w['scores'].values()),
        'report_and_four_figure_files_byte_identical':True,'raw_audit_repeated':False,
        'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_native_worlds':0,'new_code_executions':0}
    write_json_atomic(output/'reproduction.json',{**result,'content_sha256':digest(result)},sort_keys=True,allow_nan=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('report','manifest','figures','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();r=reproduce(a.report,a.manifest,a.figures,a.output)
    print(json.dumps({'output':str(a.output),'identical':r['report_and_four_figure_files_byte_identical'],'new_model_calls':0}))


if __name__=='__main__':main()
