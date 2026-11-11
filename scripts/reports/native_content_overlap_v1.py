"""Describe audited accepted-record overlap, never causal mediation or reselection."""
import argparse
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import git_binding
from scripts.reports.native_objective_preference_geometry_v1 import analyze as check_audit
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-content-overlap.v1'


def fraction(value):
    return {'numerator':value.numerator,'denominator':value.denominator}


def overlap(left,right):
    """Multisets preserve repeated decision occurrences, not just unique papers."""
    ratings={};pools=[]
    for rows in (left,right):
        pool=Counter()
        for r in rows:
            rating=r['rating'];scores=[a['score'] for a in rating['ratings']]
            if (type(r['year']) is not int or not isinstance(r['paper_id'],str)
                    or rating['status']!='measured' or len(scores)!=3
                    or any(type(s) is not int or not 1<=s<=5 for s in scores)):
                raise ValueError('audited three-position literal ratings required')
            q=Fraction(sum(scores),3);content=rating['content_sha256']
            if float(q)!=rating['mean_score'] or (content in ratings and ratings[content]!=q):
                raise ValueError('same fixed content has inconsistent pooled rating')
            ratings[content]=q;pool[r['year'],r['paper_id'],content]+=1
        pools.append(pool)
    a,b=pools
    def section(counter):
        rows=[{'year':k[0],'paper_id':k[1],'content_sha256':k[2],'multiplicity':n,
            'mean_score':float(ratings[k[2]]),'centered_utility':float(ratings[k[2]]-3)} for k,n in sorted(counter.items())]
        total=sum((ratings[k[2]]*n for k,n in counter.items()),Fraction(0));n=sum(counter.values())
        return {'occurrences':n,'exact_score_sum':fraction(total),'exact_centered_utility_sum':fraction(total-3*n),
            'score_sum':float(total),'centered_utility_sum':float(total-3*n),'records':rows}
    common=section(a&b);only_left=section(a-b);only_right=section(b-a)
    da=sum(a.values())-sum(b.values())
    ds=sum((ratings[k[2]]*n for k,n in a.items()),Fraction(0))-sum((ratings[k[2]]*n for k,n in b.items()),Fraction(0))
    return {'left':section(a),'right':section(b),'common':common,'left_only':only_left,'right_only':only_right,
        'left_minus_right':{'accepted_occurrences':da,'exact_score_sum':fraction(ds),
            'exact_utility_at_declared_center_3':fraction(ds-3*da),
            'count_loss':-da,'utility_loss_at_declared_center_3':float(3*da-ds)},
        'conditional_center_indifference':fraction(ds/da) if da else None,
        'interpretation':'Observed accepted-record overlap and exact arithmetic from fixed three-position opinions. '
            'Left-only/right-only are multiset differences, not causal extra/missing papers or independent samples. '
            'A conditional center indifference holds these realized records fixed; it is not a new optimization, '
            'a changed objective, global optimum, actual adaptation or scientific truth.'}


def analyze(plan,audit,observations,left_label,right_label):
    validation=check_audit(plan,audit)
    if validation['scope'] not in ('stopped-development-reference-diagnostic','closed-development') or left_label==right_label:
        raise ValueError('two distinct actually audited developer references required')
    worlds={w['identity']:w for w in audit['worlds']};records=[]
    for label in (left_label,right_label):
        w=worlds['reference-'+label];o=checked(observations[label]);m,=o['metadata']['measurements']
        if (w['status']!='complete' or o['status']!='complete' or o['suggestion_id']!=w['identity']
                or o['candidate']!=w['system'] or w['system']!=plan['reference_systems'][label]
                or m['measurement_adapter_contract_sha256']!=digest(plan['observer_contract'])):
            raise ValueError('exact audited original reference measurement required')
        rows=m['common_content_observer']['accepted_decisions'];metrics=m['metrics']
        q=math.fsum(r['rating']['mean_score'] for r in rows);u=math.fsum(r['rating']['mean_score']-3 for r in rows)
        if (metrics['native.accepted_decisions']['value']!=len(rows)
                or metrics['native.common_content_score_sum']['value']!=q
                or metrics['native.common_content_utility_sum']['value']!=u
                or w['scores']!={'throughput':-float(len(rows)),'content-utility':-u}):
            raise ValueError('literal original fixed-center measurements and audited scores differ')
        records.append(rows)
    result={'schema':SCHEMA,'scope':validation['scope'],'source_commit':plan['source_commit'],
        'plan_sha256':plan['content_sha256'],'audit_content_sha256':audit['content_sha256'],
        'left_label':left_label,'right_label':right_label,'overlap':overlap(*records),
        'new_model_calls':0,'new_code_executions':0,'loss_changed':False,'selection_changed':False,
        'causal_mediation_claimed':False,'publication_ready':False}
    result['content_sha256']=digest(result);return result


def render(report,out):
    import textwrap
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data=report['overlap'];labels=[report['left_label'],report['right_label']]
    with plt.rc_context({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':SCHEMA}):
        fig,axes=plt.subplots(1,2,figsize=(8,3.9))
        for ax,metric,title in zip(axes,['occurrences','centered_utility_sum'],['Accepted decision occurrences','Fixed content utility (score minus 3)']):
            shared=data['common'][metric];unique=[data['left_only'][metric],data['right_only'][metric]]
            ax.bar([0,1],[shared,shared],color='#c6cdd5',label='Shared record occurrences',width=.55)
            ax.bar([0,1],unique,bottom=shared,color=['#087f8c','#b47835'],width=.55)
            totals=[shared+v for v in unique];low=min(0,shared,*totals);high=max(0,shared,*totals)
            margin=max(.2,.18*(high-low))
            for i,v in enumerate(unique):
                ax.text(i,shared+v+margin*.18,f'{shared+v:g}',ha='center',va='bottom')
                if shared:ax.text(i,shared/2,f'{shared:g}',ha='center',va='center',fontsize=7)
                if v:ax.text(i,shared+v/2,f'{v:g}',ha='center',va='center',color='white',fontsize=7)
            ax.set(title=title,xticks=[0,1],xticklabels=[textwrap.fill(s.replace('reviewed-all-',''),23) for s in labels],
                ylim=(0 if metric=='occurrences' else low-margin,high+margin))
            if metric=='occurrences':
                from matplotlib.ticker import MaxNLocator
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            else:ax.axhline(0,color='#9aa3ad',lw=.7)
            ax.grid(axis='y',color='#eeeeee');ax.set_axisbelow(True)
        axes[0].legend(fontsize=6,loc='upper left')
        fig.suptitle('Different record sets can have equal objective value',fontsize=11)
        fig.text(.5,.02,'Grey = same year, paper and content; colored = side-only multiset. Descriptive overlap, not causal mediation.',
            ha='center',fontsize=6.5)
        fig.tight_layout(rect=(0,.06,1,.92))
        for ext in ('png','svg'):fig.savefig(out/('content-overlap.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args):
    root=args.run.resolve();out=args.output.resolve();source=git_binding(ROOT)
    if out.exists() or out.is_relative_to(root):raise ValueError('fresh external analysis output required')
    if args.audit_one.read_bytes()!=args.audit_two.read_bytes():raise ValueError('two matching original-source audits required')
    before=_inventory(root);plan=checked(json.loads((root/'plan.json').read_text()));audit=checked(json.loads(args.audit_one.read_text()))
    if digest(before)!=audit['raw_inventory_sha256']:raise ValueError('raw state differs from cold audit')
    paths=[root/'plan.json',args.audit_one,args.audit_two]
    observations={}
    for label in (args.left,args.right):
        if label not in plan['reference_order']:raise ValueError('declared original reference required')
        path=root/'references'/label/'observation.json';paths.append(path);observations[label]=json.loads(path.read_text())
    hashes={str(p):file_sha256(p) for p in paths};report=analyze(plan,audit,observations,args.left,args.right)
    if before!=_inventory(root) or hashes!={str(p):file_sha256(p) for p in paths} or git_binding(ROOT)!=source:
        raise ValueError('scientific inputs or analysis source changed')
    out.mkdir(parents=True);save(out/'report.json',{k:v for k,v in report.items() if k!='content_sha256'});render(report,out)
    save(out/'manifest.json',{'schema':SCHEMA+'.export','analysis_source_commit':source,'inputs':hashes,
        'raw_inventory_sha256':digest(before),'report_content_sha256':report['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(out.iterdir())},'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'scope':report['scope'],'content_sha256':report['content_sha256'],
        'delta':report['overlap']['left_minus_right']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--left',default='reviewed-all-connected');p.add_argument('--right',default='reviewed-all-disconnected')
    export(p.parse_args())


if __name__=='__main__':main()
