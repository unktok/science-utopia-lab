"""End-stock support in the already retained closed O/E report; no new losses."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def summarize(raw):
    a=checked(json.loads(raw));rows=[];worlds=a['worlds']
    if a['schema']!='scienceutopia.pre-scale-search-report.v1':raise ValueError('exact retained closed O/E report required')
    for w in worlds:
        if w['status']!='complete':continue
        if w.get('measurement') is None:raise ValueError('complete world lacks measurement')
        metrics=w['measurement']['metrics'];values={}
        for key in ('final_active_authors','final_author_resources'):
            record=metrics['native.'+key]
            if record['status']!='measured' or record['value'] is None:raise ValueError('required end stock unavailable')
            values[key]=record['value']
        rows.append({**{k:w[k] for k in ('identity','role','seed','status')},**values})
    if not rows:raise ValueError('completed measured worlds required')
    d={'schema':'scienceutopia.native-objective-support-screen.v1',
        'input_report':'research/data/pre-scale-search-v1/report.json',
        'input_file_sha256':hashlib.sha256(raw).hexdigest(),'input_content_sha256':a['content_sha256'],
        'original_source_commit':a['source_commit'],'original_audit_content_sha256':a['audit_sha256'],
        'physical_worlds':len(worlds),'completed_worlds':len(rows),'excluded_noncomplete_worlds':len(worlds)-len(rows),
        'final_active_authors_distribution':dict(Counter(str(r['final_active_authors']) for r in rows)),
        'total_final_author_resources_range':[min(r['final_author_resources'] for r in rows),max(r['final_author_resources'] for r in rows)],
        'rows':rows,'scope':{'new_model_calls':0,'new_worlds':0,'new_independent_audit':False,
            'new_loss_selected':False,'conditioned_on_completed_worlds':True,'independent_optimizer_replicates_claimed':False,
            'transient_dropout_and_individual_resource_floors_not_identified':True}}
    d['content_sha256']=digest(d);return d


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('fresh support-screen output required')
    raw=a.report.read_bytes();result=summarize(raw)
    write_json_atomic(a.output,result,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)
    if a.report.read_bytes()!=raw:raise ValueError('input report changed')
    print(json.dumps({'content_sha256':result['content_sha256'],'completed_worlds':result['completed_worlds']}))


if __name__=='__main__':main()
