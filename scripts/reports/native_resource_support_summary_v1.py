"""Portable numeric vectors from source-bound resource readouts, no raw prompts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import digest


def compact(raw):
    r=checked(json.loads(raw))
    if r['schema']!='scienceutopia.native-year-end-resource-support.v1':raise ValueError('exact resource readout required')
    worlds=[];snapshots=[]
    for w in r['worlds']:
        annual=w['annual'];ids=[a['actor_id_sha256'] for a in annual[0]['actors']]
        if len(ids)!=len(set(ids)) or [a['year'] for a in annual]!=[1,2,3,4]:raise ValueError('ordered four-year actor vectors required')
        years=[]
        for row in annual:
            actors=row['actors']
            if [a['actor_id_sha256'] for a in actors]!=ids:raise ValueError('actor-vector identities differ')
            years.append({'year':row['year'],'checkpoint_sha256':row['checkpoint_sha256'],
                **{key:[a[key] for a in actors] for key in
                   ('resources','is_active','initial_funding','project_start_year','project_end_year')}})
            snapshots.append(row)
        worlds.append({**{k:w[k] for k in ('identity','role','seed')},'actor_id_sha256s':ids,'annual':years})
    per_year=[]
    for year in (1,2,3,4):
        rows=[s for s in snapshots if s['year']==year];actors=[a for s in rows for a in s['actors']]
        if not rows:raise ValueError('every declared year required')
        per_year.append({'year':year,'world_boundaries':len(rows),'actor_boundaries':len(actors),
            'active_actor_boundaries':sum(a['is_active'] for a in actors),
            'minimum_actor_resources':min(a['resources'] for a in actors),
            'maximum_actor_resources':max(a['resources'] for a in actors)})
    all_actors=[a for row in snapshots for a in row['actors']]
    rebuilt={'complete_worlds':len(worlds),'skipped_worlds':len(r['skipped_worlds']),
        'annual_boundaries':len(snapshots),'actor_boundaries':len(all_actors),
        'active_actor_boundaries':sum(a['is_active'] for a in all_actors),
        'minimum_observed_year_end_actor_resources':min(a['resources'] for a in all_actors),
        'maximum_observed_year_end_actor_resources':max(a['resources'] for a in all_actors),
        'year_end_active_author_distribution':dict(Counter(str(row['year_end_active_authors']) for row in snapshots)),
        'recorded_initial_funding_distribution':dict(Counter(str(a['initial_funding']) for a in all_actors))}
    if rebuilt!=r['summary']:raise ValueError('resource aggregate differs from literal actor vectors')
    d={'schema':'scienceutopia.native-year-end-resource-summary.v1',
        'scientific_source_commit':r['source_commit'],'input_full_audit_content_sha256':r['input_full_audit_content_sha256'],
        'input_full_audit_file_sha256':r['input_full_audit_file_sha256'],
        'raw_readout_content_sha256':r['content_sha256'],'raw_readout_file_sha256':hashlib.sha256(raw).hexdigest(),
        'reader_source_sha256':r['analysis_adapter_sha256'],'summary':r['summary'],
        'per_year':per_year,'worlds':worlds,'skipped_worlds':r['skipped_worlds'],'scope':r['scope'],
        'repeated_initial_funding_fields_are_not_distinct_allocation_events':True}
    d['content_sha256']=digest(d);return d


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--readout',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('fresh compact output required')
    raw=a.readout.read_bytes();d=compact(raw)
    save(a.output,{k:v for k,v in d.items() if k!='content_sha256'})
    if raw!=a.readout.read_bytes():raise ValueError('resource readout changed')
    print(json.dumps({'content_sha256':d['content_sha256'],'summary':d['summary']}))


if __name__=='__main__':main()
