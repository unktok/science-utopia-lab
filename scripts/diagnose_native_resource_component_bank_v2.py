"""Twelve fixed original resource components, isolated execution then cold replay."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from utopia.optimization.native_component_lab_v1 import NativeComponentLab,EXTENDED_PROBE_SCOPE
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.code_mechanisms import DockerCodeExecutor,sha
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-resource-component-diagnostic.v2'
NODES=('world.selection','native-feature-extractor','developer-liquidity-director')


def read(path):return checked(json.loads(Path(path).read_text()))


def inputs(bank,audit):
    checked(bank);checked(audit)
    if (bank['schema']!='scienceutopia.native-component-fixtures.v1'
            or audit['schema']!='scienceutopia.native-liquidity-support-audit.v1'
            or audit['closure']['terminal']['status']!='closed'
            or bank['historical_audit_content_sha256']!=audit['content_sha256']
            or bank['source_commit']!=audit['source_commit']
            or bank['post_edit_reference']!='resource-30-connected'
            or bank['post_edit_probe_scope']!=EXTENDED_PROBE_SCOPE or bank['nodes']!=list(NODES)):
        raise ValueError('exact audited resource developer bank and explicit reference required')
    origins=sorted((o for o in bank['origins'] if o['reference']==bank['post_edit_reference']),
        key=lambda o:(NODES.index(o['node_id']),o['year']))
    if [(o['node_id'],o['year']) for o in origins]!=[(n,y) for n in NODES for y in range(1,5)]:
        raise ValueError('all twelve predeclared original component contexts required')
    by={r['bundle_sha256']:r for r in bank['records']}
    return [(o,by[o['bundle_sha256']]) for o in origins]


def replay(root):
    root=Path(root);p=read(root/'plan.json');summary=read(root/'summary.json')
    bank=read(Path(p['bank_path']));audit=read(Path(p['audit_path']));cases=inputs(bank,audit)
    if (p['source_commit']!=pinned_revision(ROOT) or file_sha256(Path(p['bank_path']))!=p['bank_file_sha256']
            or file_sha256(Path(p['audit_path']))!=p['audit_file_sha256']
            or summary['plan_sha256']!=p['content_sha256']):raise ValueError('diagnostic source or input differs')
    if not (root/'lab/contract.json').is_file():raise ValueError('cold replay requires original component contract')
    def forbidden(*a):raise AssertionError('cold diagnostic cannot execute source')
    lab=NativeComponentLab(root/'lab',records=bank['records'],provenance=p['fixture_provenance'],
        executor=SimpleNamespace(image_id=p['image_id'],timeout=15.,execute=forbidden),source_commit=p['source_commit'],
        maximum_probes=12,budget_scope=EXTENDED_PROBE_SCOPE)
    rows=lab.replay();observations=[]
    for (origin,record),row in zip(cases,rows):
        reply=row['terminal']
        if (row['intent']['fixture_id']!='fixture-'+record['bundle_sha256']
                or row['intent']['artifact']!=record['artifact'] or reply is None):
            raise ValueError('exact fixed original diagnostic call required')
        observations.append({'node_id':origin['node_id'],'year':origin['year'],'status':reply['status'],
            'original_result_matches':reply['status']=='returned' and sha(reply['result'])==sha(record['result']),
            'reply_content_sha256':reply['content_sha256']})
    if (len(rows)>12 or len(observations)!=len(rows) or summary['observations']!=observations
            or summary['status']!=('closed' if len(rows)==12 and all(o['original_result_matches'] for o in observations) else 'stopped')
            or any(not o['original_result_matches'] for o in observations[:-1])):
        raise ValueError('diagnostic closure or stopped prefix differs')
    return {'schema':SCHEMA+'.cold','source_commit':p['source_commit'],'summary_sha256':summary['content_sha256'],
        'calls':len(rows),'status':summary['status'],'new_model_calls':0,'new_code_executions':0}


def run(args):
    source=pinned_revision(ROOT);root=args.output.resolve()
    if root.exists():raise ValueError('fresh component diagnostic required')
    bank=read(args.bank);audit=read(args.audit);cases=inputs(bank,audit)
    if file_sha256(args.audit)!=bank['historical_audit_file_sha256']:raise ValueError('original audit bytes differ')
    images={r['receipt']['image_id'] for _,r in cases}
    if len(images)!=1:raise ValueError('one original pinned component image required')
    image=next(iter(images));executor=DockerCodeExecutor(image=image,timeout=15.)
    if executor.image_id!=image:raise ValueError('component executor image differs')
    root.mkdir(parents=True)
    provenance={'bank_content_sha256':bank['content_sha256'],'scope':'twelve developer baseline components, not candidate loss'}
    p=save(root/'plan.json',{'schema':SCHEMA+'.plan','source_commit':source,'bank_path':str(args.bank.resolve()),
        'audit_path':str(args.audit.resolve()),'bank_file_sha256':file_sha256(args.bank),'audit_file_sha256':file_sha256(args.audit),
        'fixture_provenance':provenance,'image_id':image,'maximum_probes':12,'budget_scope':EXTENDED_PROBE_SCOPE,
        'new_model_calls':0,'new_native_worlds':0,'replace_failed_calls':False})
    lab=NativeComponentLab(root/'lab',records=bank['records'],provenance=provenance,executor=executor,
        source_commit=source,maximum_probes=12,budget_scope=EXTENDED_PROBE_SCOPE)
    observations=[]
    for origin,row in cases:
        reply=lab.probe(row['artifact'],'fixture-'+row['bundle_sha256'])
        match=reply['status']=='returned' and sha(reply['result'])==sha(row['result'])
        observations.append({'node_id':origin['node_id'],'year':origin['year'],'status':reply['status'],
            'original_result_matches':match,'reply_content_sha256':reply['content_sha256']})
        if not match:break
    save(root/'summary.json',{'schema':SCHEMA+'.summary','plan_sha256':p['content_sha256'],
        'status':'closed' if len(observations)==12 and all(o['original_result_matches'] for o in observations) else 'stopped',
        'observations':observations,'new_model_calls':0,'new_native_worlds':0,
        'scientific_improvement_claimed':False,'actual_model_self_repair_claimed':False})
    print(json.dumps(replay(root)),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bank',type=Path);p.add_argument('--audit',type=Path);p.add_argument('--cold',action='store_true')
    args=p.parse_args()
    if args.cold:print(json.dumps(replay(args.output)));return
    if args.bank is None or args.audit is None:p.error('explicit bank and audit required')
    run(args)


if __name__=='__main__':main()
