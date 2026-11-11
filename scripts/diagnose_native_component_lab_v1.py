"""Three predeclared component-only calls: baseline and two retained failures.

No LLM requests, new institutions, scientific worlds, source repair or fixture
replacement. A baseline failure stops the diagnostic; all raw records remain.
"""
import argparse
import json
from pathlib import Path
import time

from utopia.optimization.native_component_lab_v1 import NativeComponentLab
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.code_mechanisms import DockerCodeExecutor,sha
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[1]
CASES=(('baseline',None),
    ('retained-float-input-failure','native-adaptive-426a089543652483089f7e39'),
    ('retained-record-envelope-failure','native-adaptive-97df5e66ef462728cea78a54'))


def inputs(bank,audit):
    checked(bank);checked(audit)
    if (bank['schema']!='scienceutopia.native-component-fixtures.v1'
            or bank['historical_audit_content_sha256']!=audit['content_sha256']
            or audit['schema']!='scienceutopia.native-institution-loop-stopped-audit.v1'):
        raise ValueError('matching real developer fixture bank and stopped audit required')
    origins=[r for r in bank['origins'] if r['reference']=='open-seed'
        and r['node_id']=='world.selection' and r['year']==1 and r['seed']==61001]
    if len(origins)!=1:raise ValueError('one predeclared open-seed year1 selector input required')
    rows=[r for r in bank['records'] if r['bundle_sha256']==origins[0]['bundle_sha256']]
    if len(rows)!=1:raise ValueError('one exact component bundle required')
    row=rows[0];cases=[]
    for label,identity in CASES:
        if identity is None:artifact=row['artifact']
        else:
            worlds=[w for w in audit['worlds'] if w['identity']==identity and w['status']=='failed']
            if len(worlds)!=1:raise ValueError('exact retained failed scientific submission required')
            nodes=[n for n in worlds[0]['system']['mechanisms'] if n['mechanism_id']=='world.selection']
            if len(nodes)!=1:raise ValueError('retained failure has ambiguous selector')
            artifact=nodes[0]['parameters']['code_artifact']
        cases.append({'label':label,'origin_submission':identity,'artifact':clone(artifact)})
    return 'fixture-'+row['bundle_sha256'],cases,row


def run(args):
    source=pinned_revision(ROOT)
    if args.output.exists():raise ValueError('fresh diagnostic output required')
    bank=checked(json.loads(args.bank.read_text()));audit=checked(json.loads(args.audit.read_text()))
    if file_sha256(args.audit)!=bank['historical_audit_file_sha256']:
        raise ValueError('original physical-audit bytes differ from fixture provenance')
    key,cases,row=inputs(bank,audit)
    image=row['receipt']['image_id'];executor=DockerCodeExecutor(image=image,timeout=15.)
    if executor.image_id!=image:raise ValueError('pinned existing component image differs')
    args.output.mkdir(parents=True)
    provenance={'bank_file_sha256':file_sha256(args.bank),'bank_content_sha256':bank['content_sha256'],
        'historical_audit_content_sha256':audit['content_sha256'],'scope':'developer component-only diagnostic'}
    save(args.output/'plan.json',{'source_commit':source,'cases':cases,'fixture_id':key,
        'fixture_provenance':provenance,'maximum_probes':3,'image_id':image,'timeout_seconds':15,
        'new_model_calls':0,'new_native_worlds':0,'refill':False})
    lab=NativeComponentLab(args.output/'lab',records=bank['records'],provenance=provenance,
        executor=executor,source_commit=source,maximum_probes=3)
    observations=[]
    for i,case in enumerate(cases):
        start=time.monotonic();reply=lab.probe(case['artifact'],key)
        observations.append({'label':case['label'],'status':reply['status'],
            'artifact_sha256':sha(case['artifact']),'result_content_sha256':reply['content_sha256'],
            'error_type':reply.get('error_type'),'error':reply.get('error'),
            'caller_elapsed_seconds':time.monotonic()-start,
            'baseline_output_matches_original':(sha(reply['result'])==sha(row['result']))
                if i==0 and reply['status']=='returned' else None})
        if i==0 and reply['status']!='returned':break
    replay=lab.replay()
    if len(replay)!=len(observations) or any(r['terminal'] is None for r in replay):
        raise ValueError('component diagnostic has pending/unaccounted calls')
    if (pinned_revision(ROOT)!=source or file_sha256(args.bank)!=provenance['bank_file_sha256']
            or file_sha256(args.audit)!=bank['historical_audit_file_sha256']):
        raise ValueError('diagnostic source/input changed')
    save(args.output/'summary.json',{'source_commit':source,'observations':observations,
        'fixture_provenance':provenance,'calls':len(observations),'new_model_calls':0,'new_native_worlds':0,
        'new_component_executions':len(observations),'whole_native_failure_reproduced':False,
        'model_self_debug_demonstrated':False,'cold_replay_sha256':sha(replay)})
    print(json.dumps({'calls':len(observations),'statuses':[o['status'] for o in observations],
        'new_model_calls':0,'new_native_worlds':0}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bank','audit','output'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
