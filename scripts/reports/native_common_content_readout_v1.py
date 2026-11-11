"""Cold fixed-content ratings and original accepted-set sums, never reselection."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_native_common_content_readout_v1 import content_set,INPUT_SHA,SCHEMA as RUN_SCHEMA
from utopia.optimization.common_content_observer import CommonContentObserver,content,request_for
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-common-content-readout-report.v1'


def summarize(inputs,ratings,observer_audit):
    values=content_set(inputs);checked(ratings);checked(observer_audit)
    if set(ratings['ratings'])!=set(values) or ratings['missing_imputed'] or ratings['new_native_worlds']:
        raise ValueError('all exact original contents with no imputation required')
    rows=[]
    for key in values:
        rating=ratings['ratings'][key];answers=rating['ratings']
        if len(answers)!=3 or len(rating['physical_result_sha256'])!=3 or rating['content_sha256']!=key:
            raise ValueError('complete three-position panel accounting required')
        complete=all(answer is not None for answer in answers)
        scores=[a['score'] for a in answers if a is not None]
        if any(type(v) is not int or not 1<=v<=5 for v in scores):raise ValueError('literal1..5 ratings required')
        mean=math.fsum(scores)/3 if complete else None
        if rating['mean_score']!=mean or rating['status']!=('measured' if complete else 'unavailable'):
            raise ValueError('literal critic pooling or availability differs')
        rows.append({'paper_content_sha256':key,'status':rating['status'],'critic_scores':[
            None if a is None else a['score'] for a in answers],'mean_score':mean,
            'within_content_range':max(scores)-min(scores) if complete else None})
    expected=[{k:clone(v) for k,v in row.items() if k!='content'} |
        {'content_sha256':digest(content(row['content']))} for row in inputs['accepted_decisions']]
    if ratings['native_worlds']!=inputs['worlds'] or ratings['accepted_decisions']!=expected:
        raise ValueError('all original accepted decisions and world identities required')
    by_content={r['paper_content_sha256']:r for r in rows};worlds=[];seen=set()
    for world in inputs['worlds']:
        identity=world['identity']
        if identity in seen:raise ValueError('duplicate original world')
        seen.add(identity);decisions=[r for r in expected if r['physical_world']==identity]
        if len(decisions)!=world['accepted_decisions']:raise ValueError('original accepted count differs')
        means=[by_content[r['content_sha256']]['mean_score'] for r in decisions];complete=all(v is not None for v in means)
        worlds.append({'identity':identity,'seed':world['seed'],'accepted_decisions':len(decisions),
            'unique_accepted_contents':len({r['content_sha256'] for r in decisions}),
            'available_decisions':sum(v is not None for v in means),'status':'measured' if complete else 'unavailable',
            'common_score_sum':math.fsum(means) if complete else None,
            'common_centered_utility_sum':math.fsum(v-3 for v in means) if complete else None})
    if len(expected)!=sum(w['accepted_decisions'] for w in worlds):raise ValueError('unaccounted accepted decision')
    result={'schema':SCHEMA,'historical_source_commit':inputs['scientific_source_commit'],
        'ratings_sha256':ratings['content_sha256'],'observer_audit_sha256':observer_audit['content_sha256'],
        'contract_sha256':observer_audit['contract_sha256'],'content_rows':rows,'world_rows':worlds,
        'critic_rating_distribution':{str(k):v for k,v in sorted(Counter(v for r in rows for v in r['critic_scores'] if v is not None).items())},
        'content_panels_available':sum(r['status']=='measured' for r in rows),
        'content_panels_unavailable':sum(r['status']=='unavailable' for r in rows),
        'original_complete_worlds':len(worlds),'original_partial_worlds_excluded':len(inputs['skipped_partial_worlds']),
        'accepted_decision_records':len(expected),'physical_attempts':observer_audit['dispatch_intents'],
        'usage':clone(observer_audit['usage']),
        'interpretation':{'scientific_truth_measured':False,'independent_critic_errors':False,
            'rejected_content_quality_identified':False,'held_out_evaluation':False,
            'new_model_calls':0,'new_native_worlds':0,'policy_reselection':False,'publication_ready':False}}
    result['content_sha256']=digest(result);return result


def export(args):
    root=args.run.resolve();output=args.output.resolve()
    if output.exists() or output.is_relative_to(root):raise ValueError('fresh external readout report required')
    before=_inventory(root)
    read=lambda p:checked(json.loads(Path(p).read_text()))
    terminal=read(root/'terminal.json');plan=read(root/'plan.json');ratings=read(root/'ratings.json')
    if (terminal['schema']!=RUN_SCHEMA+'.terminal' or terminal['status']!='closed' or terminal['stage']!='closed'
            or plan['schema']!=RUN_SCHEMA+'.plan' or plan['source_commit']!=plan['contract']['source_commit']
            or read(root/'started.json')['plan_sha256']!=plan['content_sha256']):
        raise ValueError('normally closed fixed-content readout required')
    path=Path(plan['inputs_path']);input_hash=file_sha256(path);inputs=read(path)
    if input_hash!=INPUT_SHA or input_hash!=plan['inputs_file_sha256'] or ratings['plan_sha256']!=plan['content_sha256']:
        raise ValueError('exact historical inputs and closed plan required')
    order=list(content_set(inputs));initial=read(root/'interface-check.json')
    if (plan['content_order']!=order or plan['initial_interface_check_content_hashes']!=order[:3]
            or initial['contents']!=order[:3] or not initial['all_literal_panels_complete']
            or initial['ratings']!={k:ratings['ratings'][k] for k in order[:3]}
            or any(ratings['ratings'][k]['status']!='measured' for k in order[:3])):
        raise ValueError('original ordered real interface check differs')
    if not (root/'observer/contract.json').is_file():raise ValueError('retained observer contract required before cold reader')
    class Forbidden:
        def __call__(self,*a,**kw):raise AssertionError('cold reader cannot dispatch')
        def lease(self,*a,**kw):raise AssertionError('cold reader cannot acquire inference')
    observer=CommonContentObserver(root/'observer',plan['contract'],backend=Forbidden())
    audit=checked(observer.audit())
    if audit!=read(root/'audit.json') or audit['dispatch_intents']!=228 or audit['known_terminal_attempts']!=228:
        raise ValueError('all228 actual completed critic positions and retained audit required')
    audit_rows={r['key']:r for r in audit['rows']};seen=set()
    for key,value in content_set(inputs).items():
        literal=[];hashes=[]
        for critic in range(3):
            request_key,_,_=request_for(plan['contract'],value,critic);seen.add(request_key)
            record=read(root/'observer/requests'/(request_key+'.result.json'));row=audit_rows[request_key]
            if record['content_sha256']!=row['result_sha256']:raise ValueError('rating differs from reconstructed raw reply')
            literal.append(record['rating']);hashes.append(record['content_sha256'])
        pooled=ratings['ratings'][key]
        if pooled['ratings']!=literal or pooled['physical_result_sha256']!=hashes or pooled['contract_sha256']!=plan['contract']['content_sha256']:
            raise ValueError('pooled values differ from literal critic replies')
    if seen!=set(audit_rows):raise ValueError('unaccounted critic request')
    report=summarize(inputs,ratings,audit)
    if before!=_inventory(root) or input_hash!=file_sha256(path):raise ValueError('readout evidence changed')
    output.mkdir(parents=True);save(output/'report.json',{k:v for k,v in report.items() if k!='content_sha256'})
    for name,rows in (('contents',report['content_rows']),('worlds',report['world_rows'])):
        with (output/(name+'.csv')).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    render(report,output)
    save(output/'manifest.json',{'schema':SCHEMA+'.export','raw_inventory_sha256':digest(before),
        'input_file_sha256':input_hash,'report_content_sha256':report['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},'new_model_calls':0,'new_native_worlds':0})
    print(json.dumps({'report_content_sha256':report['content_sha256'],'contents':76,'physical_replies':228}))


def render(report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':SCHEMA}):
        fig,axes=plt.subplots(1,2,figsize=(8,3))
        counts=Counter(r['mean_score'] for r in report['content_rows'] if r['mean_score'] is not None)
        axes[0].bar(list(counts),list(counts.values()),width=.23,color='#157b80')
        axes[0].set(title='Complete content panels',xlabel='Mean abstract-based rating',ylabel='Distinct contents',xlim=(.8,5.2))
        counts=Counter(r['within_content_range'] for r in report['content_rows'] if r['within_content_range'] is not None)
        axes[1].bar(list(counts),list(counts.values()),width=.6,color='#5366a1')
        axes[1].set(title='Same-model critic disagreement',xlabel='Within-content maximum minus minimum',ylabel='Distinct contents',xticks=[0,1,2,3,4])
        fig.suptitle('Retrospective fixed opinion, not a scientific truth test',fontsize=10)
        fig.tight_layout(rect=(0,0,1,.94))
        for ext in ('png','svg'):fig.savefig(output/('fixed-content-ratings.'+ext),dpi=220,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','output'):parser.add_argument('--'+name,type=Path,required=True)
    export(parser.parse_args())


if __name__=='__main__':main()
