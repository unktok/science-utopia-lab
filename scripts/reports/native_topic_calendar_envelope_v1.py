"""Conditional original-calendar headroom, not another simulated researcher world.

Reads the retained closed two-control pilot and original catalog. The calendar
relaxation is explicitly conditional, not a global bound on arbitrary systems,
content utility, resource cost or the general Science Utopia engine.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import digest
from utopia.system.native_catalog_planning import catalog_contract
from utopia.system.native_legacy_topic_planning import eligible_topics
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-topic-calendar-envelope.v1'
PRIMITIVES=('utopia/agents/research_direction.py','utopia/simulation.py',
    'utopia/arguments.py','utopia/optimization/native_factory.py',
    'utopia/system/native_kernel.py','utopia/system/native_open_domain.py',
    'utopia/system/native_catalog_planning.py','utopia/system/native_legacy_topic_planning.py')


def capacity(authors,catalog,*,years,papers_per_project,related):
    """Optimistic completion slots conditional on an unchanged sequential calendar."""
    if (type(years) is not int or years<1 or type(papers_per_project) is not int
            or papers_per_project<1 or type(related) is not bool):
        raise ValueError('explicit positive integer calendar/production allowance required')
    directions={d['topic']:d for d in catalog['directions']}
    if len(directions)!=len(catalog['directions']): raise ValueError('unique literal catalog topics required')
    rows=[]; known=set()
    for actor in authors:
        if actor['id'] in known: raise ValueError('unique original author identities required')
        known.add(actor['id'])
        union=eligible_topics(actor,catalog=catalog)
        topics=union if related else sorted(set(actor['expertise']))
        durations=[directions[t]['years'] for t in topics]
        if not durations or any(type(d) is not int or d<1 for d in durations):
            raise ValueError('literal positive integer original durations required')
        shortest=min(durations); completions=years//shortest
        rows.append({'actor_id':actor['id'],'core_expertise':actor['expertise'],
            'eligible_topics':topics,'minimum_original_duration':shortest,
            'all_minimum_duration_topics':[t for t in topics if directions[t]['years']==shortest],
            'conditional_completed_project_slots':completions,
            'conditional_new_paper_slots':papers_per_project*completions})
    return {'authors':rows,'conditional_completed_project_slots':sum(r['conditional_completed_project_slots'] for r in rows),
        'conditional_new_paper_slots':sum(r['conditional_new_paper_slots'] for r in rows)}


def analyze(report,plan,catalog):
    worlds=report['worlds']; years=plan['world']['years']
    papers=plan['world']['world_conditions']['papers_per_project']
    if [w['condition'] for w in worlds]!=['core-only','core-plus-related']:
        raise ValueError('literal ordered closed developer contrast required')
    result=[]; initial=None
    for world in worlds:
        if (world['status']!='complete' or [a['year'] for a in world['annual']]!=list(range(1,years+1))):
            raise ValueError('actual complete original annual authors required')
        authors=world['annual'][0]['authors']
        identity=sorted((a['id'],a['expertise']) for a in authors)
        if len(authors)!=5 or any(sorted((a['id'],a['expertise']) for a in s['authors'])!=identity
                                 for s in world['annual']):
            raise ValueError('this diagnostic requires the retained unchanged five-author calendar')
        if initial is not None and identity!=initial: raise ValueError('same literal author/topic support required')
        initial=identity
        envelope=capacity(authors,catalog,years=years,papers_per_project=papers,
                          related=world['condition']=='core-plus-related')
        accepted=len(world['accepted_content'])
        if world['scores']['throughput']!=-accepted: raise ValueError('literal original throughput differs')
        projects=Counter()
        for a in world['assignments']:
            if a['catalog_sha256']!=catalog['directions_sha256']:
                raise ValueError('actual project original catalog differs from retained analysis catalog')
            projects[a['actor_id']]+=1
        if not set(projects)<=set(a['id'] for a in authors): raise ValueError('actual assignment actor absent')
        for row in envelope['authors']:
            row['observed_assignment_effects']=projects[row['actor_id']]
        unique=len({r['paper_id'] for r in world['accepted_content']})
        result.append({'condition':world['condition'],'observed_accepted_decisions':accepted,
            'observed_unique_accepted_papers':unique,'observed_project_assignments':len(world['assignments']),
            'observed_content_utility_loss':world['scores']['content-utility'],
            'observed_collected_resource_cost':world['resource_cost'],**envelope,
            'observed_acceptance_equals_conditional_paper_slots':accepted==envelope['conditional_new_paper_slots'],
            'observed_acceptance_exceeds_conditional_paper_slots':accepted>envelope['conditional_new_paper_slots']})
    return {'schema':SCHEMA,'scientific_source_commit':report['scientific_source_commit'],
        'original_report_content_sha256':report['content_sha256'],'original_plan_content_sha256':plan['content_sha256'],
        'original_catalog_sha256':catalog['directions_sha256'],'years':years,'papers_per_project':papers,
        'formula':'papers_per_project * sum_a floor(years / min_original_eligible_duration_a)',
        'conditional_assumptions':[
            'Same original author set and fixed core/related catalog throughout; no new native authors or altered expertise.',
            'Authors begin idle before year1, have at most one nonoverlapping native project, and original positive durations do not change.',
            'New native papers arise only at a mature project, at most papers_per_project per completion; no extra production effect.',
            'No initially existing output or repeated acceptance of the same paper increases the accepted-decision metric.',
            'Ignore funding, inactivity, collaboration, paper availability and inference failures: this is optimistic calendar capacity, not a feasible policy solver.'
        ],
        'rows':result,
        'interpretation':'Both hand rules are compared to their explicit candidate-set calendar relaxation. '
            'Core-only is a source-chosen rule, not the shared permission limit. Equality describes these '
            'observed trajectories and this conditional calendar model, not certified optimality of arbitrary '
            'v6 programs or of the general engine. It does not bound U, K or C, prove a causal duration '
            'effect, implement optimization or add an activity/novelty/merit requirement. Native original '
            'worlds remain the scientific evaluation; this arithmetic never replaces them.',
        'full_design_domain_optimality_proved':False,'new_model_calls':0,'new_code_executions':0,
        'new_native_worlds':0,'historical_loss_or_selection_changed':False,'publication_ready':False}


def export(args):
    source=pinned_revision(ROOT); out=args.output.resolve(); plan_path=args.plan.resolve()
    paths=[ROOT/'research/results/native-legacy-topic-pilot-closed-v1.json',
           ROOT/'research/data/native-legacy-topic-pilot-v1/report.json',plan_path]
    if out.exists() or out.is_relative_to(ROOT) or out.is_relative_to(plan_path.parent):
        raise ValueError('fresh external output outside reader and original run required')
    hashes={str(p):file_sha256(p) for p in paths}
    receipt,report,plan=[checked(json.loads(p.read_text())) for p in paths]
    if (receipt['scientific_source_commit']!=report['scientific_source_commit']
            or receipt['scientific_source_commit']!=plan['source_commit']
            or receipt['plan_file_sha256']!=hashes[str(plan_path)]
            or report['plan_sha256']!=plan['content_sha256']
            or receipt['retained_files']['research/data/native-legacy-topic-pilot-v1/report.json']!=hashes[str(paths[1])]
            or not receipt['two_original_source_audits_identical'] or not receipt['same_cold_initial_physical_society']):
        raise ValueError('original retained report/plan/closed reconstruction binding required')
    primitive_hashes={}
    for name in PRIMITIVES:
        blob=subprocess.check_output(['git','show',plan['source_commit']+':'+name],cwd=ROOT)
        if (ROOT/name).read_bytes()!=blob: raise ValueError('original primitive source changed: '+name)
        primitive_hashes[name]=file_sha256(ROOT/name)
    result=analyze(report,plan,catalog_contract())
    result.update(analysis_source_commit=source,original_primitive_files_sha256=primitive_hashes,
                  original_cold_audits_reexecuted=False)
    out.mkdir(parents=True); save(out/'report.json',result)
    fields=('condition','observed_accepted_decisions','conditional_new_paper_slots',
            'observed_project_assignments','conditional_completed_project_slots',
            'observed_content_utility_loss','observed_collected_resource_cost')
    with (out/'calendar-envelope.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
        writer.writerows({k:row[k] for k in fields} for row in result['rows'])
    save(out/'manifest.json',{'schema':SCHEMA+'.export','inputs':hashes,'analysis_source_commit':source,
        'files':{p.name:file_sha256(p) for p in sorted(out.iterdir())},'new_model_calls':0,
        'new_native_worlds':0,'original_cold_audits_reexecuted':False})
    if (pinned_revision(ROOT)!=source or hashes!={str(p):file_sha256(p) for p in paths}
            or primitive_hashes!={p:file_sha256(ROOT/p) for p in PRIMITIVES}):
        raise ValueError('original retained inputs or bound reader/primitive source changed')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('plan','output'): parser.add_argument('--'+key,type=Path,required=True)
    r=export(parser.parse_args())
    print(json.dumps({'conditional_paper_slots':[w['conditional_new_paper_slots'] for w in r['rows']],
                      'new_model_calls':0,'new_native_worlds':0,'global_optimality_proved':False}))


if __name__=='__main__': main()
