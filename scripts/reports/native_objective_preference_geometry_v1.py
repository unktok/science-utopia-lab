"""Finite observed preference sets, not new selection or global policy optima."""
import argparse
from itertools import combinations
import json
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-objective-preference-geometry.v1'
AUDITS={
    'scienceutopia.native-objective-initial-stop-audit.v1':'stopped-development-reference-diagnostic',
    'scienceutopia.native-objective-instrument-loop-audit.v1':'closed-development',
    'scienceutopia.native-objective-fixed-evaluation-audit.v1':'frozen-policy-evaluation'}


def geometry(worlds,objectives):
    if len(objectives)<2 or len(set(objectives))!=len(objectives):raise ValueError('at least two explicit unique objectives required')
    identities=set();seeds={}
    for w in worlds:
        if w['identity'] in identities or type(w['seed']) is not int:raise ValueError('unique physical identities and literal world seeds required')
        identities.add(w['identity'])
        if set(w['scores'])!=set(objectives):raise ValueError('exact declared cross-criteria required')
        for value in w['scores'].values():
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
                raise ValueError('finite observed losses or explicit missing values required')
        seeds.setdefault(w['seed'],[]).append(clone(w))
    results=[]
    for seed,rows in sorted(seeds.items()):
        rows.sort(key=lambda r:r['identity'])
        known=[r for r in rows if r['status']=='complete' and all(r['scores'][o] is not None for o in objectives)]
        best={}
        for objective in objectives:
            minimum=min((r['scores'][objective] for r in known),default=None)
            best[objective]={'loss':minimum,'all_tied_physical_ids':[r['identity'] for r in known if r['scores'][objective]==minimum]}
        comparisons=[]
        for a,b in combinations(objectives,2):
            pairs=[];counts={k:0 for k in ('joint-tie','same-strict-preference','strict-conflict','tie-only-first','tie-only-second')}
            for left,right in combinations(known,2):
                signs=[(left['scores'][o]>right['scores'][o])-(left['scores'][o]<right['scores'][o]) for o in (a,b)]
                kind=('joint-tie' if signs==[0,0] else 'tie-only-first' if signs[0]==0 else
                    'tie-only-second' if signs[1]==0 else 'same-strict-preference' if signs[0]==signs[1] else 'strict-conflict')
                counts[kind]+=1;pairs.append({'left':left['identity'],'right':right['identity'],
                    'loss_comparison_signs':signs,'relation':kind})
            first=set(best[a]['all_tied_physical_ids']);second=set(best[b]['all_tied_physical_ids'])
            comparisons.append({'first_objective':a,'second_objective':b,'pair_counts':counts,'pairs':pairs,
                'observed_minimum_set_intersection':sorted(first&second),
                'observed_minimum_sets_equal':first==second if known else None})
        nondominated=[r['identity'] for r in known if not any(
            all(other['scores'][o]<=r['scores'][o] for o in objectives)
            and any(other['scores'][o]<r['scores'][o] for o in objectives) for other in known)]
        results.append({'seed':seed,'physical_rows':len(rows),'common_completed_rows':len(known),
            'common_completed_ids':[r['identity'] for r in known],
            'excluded_from_common_geometry':[{'identity':r['identity'],'status':r['status'],'scores':r['scores']}
                for r in rows if r not in known],'observed_minima':best,'objective_pairs':comparisons,
            'observed_nondominated_physical_ids':nondominated})
    return {'objectives':list(objectives),'by_world_seed':results,
        'scope':'Exact lower-loss preferences on the common completed observed physical pool, separately by world seed. '
            'Missing or technically failed rows are retained but excluded from this descriptive geometry. '
            'Ties use literal recorded values; no tolerance, imputation, new preference or adoption veto is introduced. '
            'An observed minimum is not a global optimum; pair counts are not independent replications.'}


def analyze(plan,audit):
    checked(plan);checked(audit)
    scope=AUDITS.get(audit['schema'])
    if (scope is None or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or audit['source_proof']['status']!='verified-exact-source-closure' or audit['new_model_calls'] or audit['new_code_executions']):
        raise ValueError('matching independently audited original source and plan required')
    expected='stopped' if scope=='stopped-development-reference-diagnostic' else 'closed'
    if audit['closure']['terminal']['status']!=expected:raise ValueError('declared scientific boundary differs')
    if expected=='stopped' and (audit['selection'] is not None or audit['candidate_native_worlds']!=0):
        raise ValueError('stopped reference diagnostic cannot become an optimization result')
    result={'schema':SCHEMA,'scope':scope,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'audit_content_sha256':audit['content_sha256'],'geometry':geometry(audit['worlds'],plan['objectives']),
        'frozen_selection_changed':False,'loss_changed':False,'new_model_calls':0,'new_code_executions':0,
        'scientific_truth_or_global_optimum_claimed':False,'publication_ready':False}
    result['content_sha256']=digest(result);return result


def export(args):
    root=args.run.resolve();out=args.output.resolve();source=pinned_revision(ROOT)
    if out.exists() or out.is_relative_to(root):raise ValueError('fresh geometry output outside scientific raw required')
    paths=[args.audit_one,args.audit_two,root/'plan.json'];hashes={str(p):file_sha256(p) for p in paths}
    if args.audit_one.read_bytes()!=args.audit_two.read_bytes():raise ValueError('two matching original-source audits required')
    before=_inventory(root);audit=checked(json.loads(args.audit_one.read_text()));plan=checked(json.loads((root/'plan.json').read_text()))
    if audit['raw_inventory_sha256']!=digest(before):raise ValueError('raw state differs from original cold audit')
    report=analyze(plan,audit)
    if (before!=_inventory(root) or hashes!={str(p):file_sha256(p) for p in paths} or pinned_revision(ROOT)!=source):
        raise ValueError('geometry inputs or reader source changed')
    out.mkdir(parents=True);save(out/'report.json',{k:v for k,v in report.items() if k!='content_sha256'})
    save(out/'manifest.json',{'schema':SCHEMA+'.export','analysis_source_commit':source,'inputs':hashes,
        'report_content_sha256':report['content_sha256'],'report_file_sha256':file_sha256(out/'report.json'),
        'raw_inventory_sha256':digest(before),'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'scope':report['scope'],'seed_groups':len(report['geometry']['by_world_seed']),
        'content_sha256':report['content_sha256']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    export(p.parse_args())


if __name__=='__main__':main()
