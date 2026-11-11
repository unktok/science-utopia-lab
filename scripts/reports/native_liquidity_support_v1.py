"""All four resource controls and annual actors, after independent cold closure."""
import argparse
import csv
import json
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-liquidity-support-report.v1'


def read(path):return checked(json.loads(Path(path).read_text()))


def summarize(audit,contrasts):
    if audit['schema']!='scienceutopia.native-liquidity-support-audit.v1' or audit['closure']['terminal']['status']!='closed':
        raise ValueError('normal original resource audit required')
    expected={(amount,label) for amount in (30,60) for label in ('connected','disconnected')}
    worlds=[];actors=[];seen=set()
    for world in audit['worlds']:
        key=(world['initial_funding'],world['condition'])
        if key not in expected or key in seen or world['status']!='complete':raise ValueError('exact four native controls required')
        seen.add(key);annual=world['annual_resources'];metrics=world['physical_proof']['measurement']['metrics']
        if [y['year'] for y in annual]!=[1,2,3,4]:raise ValueError('four actual annual boundaries required')
        states=[]
        for year in annual:
            founders=year['authors']
            if len(founders)!=5 or len({a['id'] for a in founders})!=5:raise ValueError('five original founder states required')
            ledger=year['ledger_reconciliation']
            if len(ledger)!=5 or any(row['residual']!=0 for row in ledger):raise ValueError('all founder ledger legs must reconcile')
            for actor in founders:
                if type(actor['is_active']) is not bool or not math.isfinite(actor['resources']):raise ValueError('literal finite native actor state required')
                actors.append({'world':world['identity'],'initial_funding':key[0],'condition':key[1],
                    'year':year['year'],'actor_id':actor['id'],'resources':actor['resources'],'is_active':actor['is_active']})
            transfers=year['transfer_events']
            if key[1]=='disconnected' and transfers:raise ValueError('disconnected receiver unexpectedly transferred resources')
            for event in transfers:
                p=event['payload']
                if (event['event_type']!='native.system.resource_transferred' or event['year']!=year['year']
                        or p['actual_debit']!=p['actual_credit'] or p['actual_debit']<=0
                        or math.fsum(p['balances_before'].values())!=math.fsum(p['balances_after'].values())):
                    raise ValueError('literal conserving transfer proof differs')
            states.append({'year':year['year'],'active_founders':sum(a['is_active'] for a in founders),
                'total_resources':math.fsum(a['resources'] for a in founders),
                'minimum_resources':min(a['resources'] for a in founders),'transfer_events':len(transfers),
                'transferred_units':math.fsum(e['payload']['actual_debit'] for e in transfers)})
        def value(name):
            m=metrics[name]
            if m['status']!='measured' or not math.isfinite(m['value']):raise ValueError('original native metric unavailable')
            return m['value']
        worlds.append({'identity':world['identity'],'initial_funding':key[0],'condition':key[1],
            'accepted_decisions':value('native.accepted_decisions'),
            'accepted_peer_score_sum':value('native.accepted_peer_score_sum'),
            'review_records':value('native.review_records'),'scores':world['scores'],
            'final_active_founders':states[-1]['active_founders'],
            'annual_active_founder_boundary_sum':sum(y['active_founders'] for y in states),
            'final_resources':states[-1]['total_resources'],'annual':states})
    if seen!=expected or len(contrasts)!=2 or {r['initial_funding'] for r in contrasts}!={30,60}:
        raise ValueError('both endowment contrasts required')
    deltas=[]
    for amount in (30,60):
        by={w['condition']:w for w in worlds if w['initial_funding']==amount}
        deltas.append({'initial_funding':amount,'difference':'connected-minus-disconnected',**{
            k:by['connected'][k]-by['disconnected'][k] for k in ('accepted_decisions','accepted_peer_score_sum',
            'review_records','final_active_founders','annual_active_founder_boundary_sum','final_resources')}})
    result={'schema':SCHEMA,'scientific_source_commit':audit['source_commit'],'audit_content_sha256':audit['content_sha256'],
        'worlds':worlds,'actor_boundaries':actors,'within_endowment_differences':deltas,'request_contrasts':contrasts,
        'raw_inventory_sha256':audit['raw_inventory_sha256'],
        'interpretation':{'developer_controls':True,'development_seed_reused':True,'policy_search':False,
            'held_out_evaluation':False,'independent_optimizer_histories':0,'scientific_truth_measured':False,
            'new_model_calls':0,'new_native_worlds':0,'publication_ready':False}}
    result['content_sha256']=digest(result);return result


def export(args):
    root=args.run.resolve();analysis=args.analysis.resolve();out=args.output.resolve()
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(analysis):raise ValueError('fresh separate report required')
    before=_inventory(root);analysis_before=_inventory(analysis);end=json.loads((analysis/'ended.json').read_text())
    if (end['status']!='closed' or end['audit_file_sha256']!=file_sha256(analysis/'audit-1.json')
            or end['cost_file_sha256']!=file_sha256(analysis/'costs-1.json')
            or (analysis/'audit-1.json').read_bytes()!=(analysis/'audit-2.json').read_bytes()
            or (analysis/'costs-1.json').read_bytes()!=(analysis/'costs-2.json').read_bytes()):
        raise ValueError('two identical independent audits/costs required')
    audit=read(analysis/'audit-1.json')
    if digest(before)!=audit['raw_inventory_sha256']:raise ValueError('original audited raw inventory differs')
    plan=read(root/'plan.json');terminal=read(root/'terminal.json');start=read(root/'started.json')
    if (audit['plan_sha256']!=plan['content_sha256'] or audit['closure']!={'started':start,'terminal':terminal}
            or plan['source_commit']!=audit['source_commit']):raise ValueError('original plan and closure differ')
    contrasts=[]
    for amount in (30,60):
        streams={}
        for condition in ('connected','disconnected'):
            identity=f'resource-{amount}-{condition}'
            p=root/'worlds-by-job'/identity/'worlds'/(identity+'-s61001')/'wire-requests.jsonl'
            rows=[json.loads(line) for line in p.read_text().splitlines()]
            if len(rows)<5 or any(r['year']!=1 for r in rows[:5]):raise ValueError('five initial researcher requests required')
            if any(digest(r['payload'])!=r['payload_sha256'] for r in rows):raise ValueError('full HTTP payload hash differs')
            streams[condition]=[r['payload'] for r in rows]
        on,off=streams['connected'],streams['disconnected'];prefix=0
        for a,b in zip(on,off):
            if a!=b:break
            prefix+=1
        contrasts.append({'initial_funding':amount,'initial_five_full_payloads_equal':on[:5]==off[:5],
            'equal_full_payload_prefix_count':prefix,'connected_requests':len(on),'disconnected_requests':len(off),
            'entire_payload_sequences_equal':on==off,'connected_payload_sequence_sha256':digest(on),
            'disconnected_payload_sequence_sha256':digest(off),
            'scope':'First five initial direction requests; prefix is descriptive, not every pre-transfer request or mediation identification.'})
    report=summarize(audit,contrasts)
    if before!=_inventory(root) or analysis_before!=_inventory(analysis):raise ValueError('evidence changed during read-only report')
    out.mkdir(parents=True);save(out/'report.json',{k:v for k,v in report.items() if k!='content_sha256'})
    for name,rows in (('worlds',[{k:v for k,v in w.items() if k not in ('scores','annual')} for w in report['worlds']]),
            ('actors',report['actor_boundaries']),('differences',report['within_endowment_differences'])):
        with (out/(name+'.csv')).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    render(report,out)
    save(out/'manifest.json',{'schema':SCHEMA+'.export','report_content_sha256':report['content_sha256'],
        'raw_inventory_sha256':digest(before),'analysis_inventory_sha256':digest(analysis_before),
        'files':{p.name:file_sha256(p) for p in sorted(out.iterdir())},'new_model_calls':0,'new_native_worlds':0})
    print(json.dumps({'worlds':4,'actor_boundaries':80,'report_content_sha256':report['content_sha256']}))


def render(report,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':SCHEMA}):
        fig,axes=plt.subplots(1,3,figsize=(10,3.1))
        for amount,color in ((30,'#a74c43'),(60,'#146c80')):
            for condition,style in (('connected','-'),('disconnected','--')):
                w=next(w for w in report['worlds'] if w['initial_funding']==amount and w['condition']==condition)
                label=f'{amount} / {condition}'
                axes[0].plot([y['year'] for y in w['annual']],[y['active_founders'] for y in w['annual']],
                    style,marker='o',color=color,label=label)
                axes[1].plot([y['year'] for y in w['annual']],[y['total_resources'] for y in w['annual']],style,marker='o',color=color)
        axes[0].set(title='Actual year-end activity',xlabel='Native year',ylabel='Active original founders',xticks=[1,2,3,4],ylim=(-.2,5.4))
        axes[1].set(title='Actual year-end resources',xlabel='Native year',ylabel='Founder resources',xticks=[1,2,3,4])
        worlds=report['worlds'];axes[2].bar(range(4),[w['accepted_decisions'] for w in worlds],color=[
            '#a74c43' if w['initial_funding']==30 else '#146c80' for w in worlds])
        axes[2].set(title='Publication decisions',ylabel='Accepted decisions',xticks=range(4),
            xticklabels=[str(w['initial_funding'])+' / '+('on' if w['condition']=='connected' else 'off') for w in worlds])
        fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=4,fontsize=8)
        fig.suptitle('Four developer controls, one reused seed — not policy optimization',fontsize=10)
        fig.tight_layout(rect=(0,.09,1,.94))
        for ext in ('png','svg'):fig.savefig(out/('resource-controls.'+ext),dpi=220,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','output'):p.add_argument('--'+key,type=Path,required=True)
    export(p.parse_args())


if __name__=='__main__':main()
