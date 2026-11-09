"""Descriptive projection/print figures from a closed original-source M audit.

All twelve worlds and three paired seed differences remain visible. No new
inference, statistical significance, scientific-value or optimizer claim.
"""
import argparse
import json
import math
from pathlib import Path
import statistics

from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic

CONDITIONS=('M0','M1','M2','M3')
SEEDS=(41001,41011,41017)
METRICS={'A':'native.accepted_decisions','Q':'native.accepted_peer_score_sum',
    'R':'native.review_records','active':'native.final_active_authors',
    'resources':'native.final_author_resources','deliveries':'native.institutional_context_deliveries'}


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('finite nonboolean measured component required')
    return value


def summarize(audit):
    checked(audit)
    if audit['schema']!='scienceutopia.pre-scale-information-audit.v1':
        raise ValueError('closed original-source information audit required')
    rows=[];seen=set()
    for row in audit['rows']:
        condition,seed=row['condition'],row['seed'];key=(condition,seed)
        if condition not in CONDITIONS or seed not in SEEDS or key in seen:
            raise ValueError('unique declared condition/seed required')
        seen.add(key);proof=row['physical_proof']
        if proof['status']!='complete' or proof['seed']!=seed or proof['years']!=4:
            raise ValueError('completed original four-year world proof required')
        raw={}
        for name,metric in METRICS.items():
            value=row['measurement']['metrics'][metric]
            if value['status']!='measured':raise ValueError('missing component cannot become zero')
            raw[name]=number(value['value'])
        a,q,r=(raw[n] for n in ('A','Q','R'))
        computed={'throughput':-a,'efficiency':math.fsum([-q,.5*r]),
            'selective':math.fsum([4*a,-q,.1*r])}
        if any(not math.isclose(number(row['scores'][k]),v,rel_tol=1e-12,abs_tol=1e-12) for k,v in computed.items()):
            raise ValueError('audited cross-score differs from measured components')
        elapsed=[number(y['interval_llm_elapsed_seconds']) for y in proof['annual_checkpoints']]
        if len(elapsed)!=4 or any(t<0 for t in elapsed):raise ValueError('four actual nonnegative call-time intervals required')
        response=proof['response_proof']
        rows.append({'id':row['id'],'condition':condition,'seed':seed,'scores':row['scores'],
            'components':raw,'first_direction_input_year':row['actual_inputs']['first_direction_input_year'],
            'completed_dossier_inputs':len(row['actual_inputs']['completed_dossier_inputs']),
            'consumer_attribution_counts':{label:sum(v['recipient_attribution']==label for v in
                row['actual_inputs']['completed_dossier_inputs']) for label in
                ('unique-rendered-prefix','ambiguous-rendered-prefix','marker-without-matched-complete-prefix')},
            'cost_components':{'scientist_call_seconds':math.fsum(elapsed),
                'recorded_scientist_responses':response['researcher_responses'],
                'wire_requests':response['wire_requests'],
                'code_executions':proof['code_proof']['recorded_executions']}})
    if seen!={(c,s) for s in SEEDS for c in CONDITIONS}:raise ValueError('all twelve declared worlds required')
    rows.sort(key=lambda row:(SEEDS.index(row['seed']),CONDITIONS.index(row['condition'])))
    paired=[]
    for seed in SEEDS:
        subset={r['condition']:r for r in rows if r['seed']==seed}
        for condition in CONDITIONS[1:]:
            paired.append({'seed':seed,'condition':condition,
                'loss_difference_from_disconnected':{k:subset[condition]['scores'][k]-subset['M0']['scores'][k]
                    for k in ('throughput','efficiency','selective')},
                'component_difference_from_disconnected':{k:subset[condition]['components'][k]-subset['M0']['components'][k]
                    for k in METRICS}})
    means={c:{k:statistics.mean(r['scores'][k] for r in rows if r['condition']==c)
        for k in ('throughput','efficiency','selective')} for c in CONDITIONS}
    result={'schema':'scienceutopia.pre-scale-information-report.v1','audit_sha256':audit['content_sha256'],
        'source_commit':audit['source_commit'],'plan_sha256':audit['plan_sha256'],'rows':rows,
        'paired_differences':paired,'condition_loss_means':means,
        'cost_scope':'Observed scientist call intervals, physical request and code counts only. Excludes retrieval/index construction, role loads, designer, readiness and host overhead; not total experiment duration.',
        'interpretation_limits':['Three development seeds, four years; descriptive, not a powered effect claim.',
            'Same initial inputs do not guarantee identical fresh replies or coupling of all future noise.',
            'M2 aggregate is not a token-matched placebo; content/length/recipient specificity are not isolated.',
            'Arrival and next eligible direction invocation differ; first input year is measured, not imposed.',
            'Raw archival reviewer scores/counts are engineering proxies, not scientific truth/welfare.',
            'No designer, optimizer or structural-invention advantage is established by this mechanism study.'],
        'new_model_calls':0,'new_code_executions':0,'scientific_goal_complete':False}
    result['content_sha256']=digest(result)
    return result


def render(report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=('#888888','#198d91','#7861a5','#bc8037')
    with plt.rc_context({'font.size':8.5,'axes.spines.top':False,'axes.spines.right':False,
            'svg.hashsalt':'pre-scale-information-v1'}):
        fig,axes=plt.subplots(1,3,figsize=(6.7,2.8))
        for ax,key,title in zip(axes[:2],('throughput','efficiency'),('Throughput loss: −A','Efficiency loss: −Q + 0.5R')):
            for seed in SEEDS:
                subset={r['condition']:r for r in report['rows'] if r['seed']==seed}
                ax.plot(range(4),[subset[c]['scores'][key] for c in CONDITIONS],color='#aaaaaa',lw=.7,alpha=.65,zorder=1)
            for i,c in enumerate(CONDITIONS):
                values=[r['scores'][key] for r in report['rows'] if r['condition']==c]
                ax.scatter([i-.06,i,i+.06],values,s=19,color=colors[i],zorder=3)
                ax.plot([i-.16,i+.16],[statistics.mean(values)]*2,color=colors[i],lw=2,zorder=4)
            ax.set(title=title,xticks=range(4),xticklabels=CONDITIONS,xlabel='Lower loss is better')
        ax=axes[2]
        for i,c in enumerate(CONDITIONS):
            for j,seed in enumerate(SEEDS):
                row=next(r for r in report['rows'] if r['condition']==c and r['seed']==seed)
                y=row['first_direction_input_year']
                if y is None:ax.text(i+(j-1)*.14,.25,'×',ha='center',color=colors[i],fontsize=9)
                else:ax.scatter([i+(j-1)*.14],[y],s=19,color=colors[i])
        ax.set(title='First dossier in direction input',xticks=range(4),xticklabels=CONDITIONS,
            yticks=range(1,5),ylim=(0,4.5),xlabel='×: none observed in four years',ylabel='Actual native year')
        fig.subplots_adjust(left=.07,right=.99,bottom=.23,top=.84,wspace=.42)
        for ext in ('png','svg'):
            fig.savefig(output/('information-comparison.'+ext),dpi=240,
                metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('fresh report destination required')
    original=file_sha256(args.audit);report=summarize(json.loads(args.audit.read_text()))
    args.output.mkdir(parents=True);write_json_atomic(args.output/'report.json',report,sort_keys=True,allow_nan=False)
    render(report,args.output)
    if file_sha256(args.audit)!=original:raise ValueError('audit changed during projection')
    manifest={'schema':'scienceutopia.pre-scale-information-figures.v1','input_file_sha256':original,
        'report_content_sha256':report['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()},
        'new_model_calls':0,'new_native_worlds':0}
    write_json_atomic(args.output/'manifest.json',{**manifest,'content_sha256':digest(manifest)},sort_keys=True,allow_nan=False)
    print(json.dumps({'output':str(args.output),'report':report['content_sha256'],'new_model_calls':0}))


if __name__=='__main__':main()
