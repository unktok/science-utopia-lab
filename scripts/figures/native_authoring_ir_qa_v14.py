#!/usr/bin/env python3
"""Small actual-only engineering QA evidence figure; never an outcome benchmark."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from scripts.analyze_native_authoring_ir_qa_v14 import ACTUAL,SCHEMA,read
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic


def render(report,output):
    if report.get('schema') != SCHEMA or report.get('classification') != ACTUAL:
        raise ValueError('this figure requires independently audited actual QA evidence')
    payload={k:v for k,v in report.items() if k!='content_sha256'}
    if digest(payload)!=report['content_sha256']:
        raise ValueError('audited QA result content hash differs')
    native=report['native'];author=report['designer']
    fig=plt.figure(figsize=(5.5,5.7),layout=None)
    fig.patch.set_facecolor('white')
    fig.text(.075,.95,'Separate stable-ID authoring QA',fontsize=13,weight='bold')
    fig.text(.075,.912,'Actual UI → queue → worker · throughput blackbox · budget 2',fontsize=9)
    fig.text(.075,.862,f"Charged slots {native['consumed_native_slots']}/2    "
        f"compiled drafts {author['valid_drafts']}    native worlds {native['physical_native_worlds']}",fontsize=10)
    fig.text(.075,.822,'Loss: n/a — no compiled design or native observation',fontsize=10,color='#7c2828')
    proofs={p['binding']['request_sha256']:p for p in author['proofs']}
    rows=[]
    for generation,record in enumerate(native['records']):
        proof=proofs[record['request_sha256']]
        for attempt,(start,done) in enumerate(zip(proof['started_records'],proof['attempt_records'])):
            if done is None:
                label='Interrupted · response unknown';detail='Consumes attempt; not redispatched'
            elif done['status']=='transport-error':
                label='Reply truncated · no source repair';detail='Known response; incomplete JSON'
            elif done['status']=='invalid':
                label='IR rejected · no source repair'
                error=done['errors'][0];diag=error.get('diagnostics',[{}])[0]
                detail=f"Operation {diag.get('operation_index','?')}: {diag.get('first_missing_segment',error['message'])}"
            else:
                label='Compiled raw IR';detail='Literal operands retained'
            rows.append((f'G{generation} · draft {attempt+1}',label,detail))
    for row,(left,label,detail) in enumerate(rows):
        y=.748-row*.105
        fig.text(.075,y,left,fontsize=9,color='#555555')
        fig.text(.34,y,label,fontsize=9,weight='bold',color='#7c2828' if 'Compiled' not in label else '#246b50')
        fig.text(.34,y-.032,detail,fontsize=8.5,color='#555555')
    costs=author['cost_measurements']; y=.255
    fig.text(.075,y,'Designer cost — known completed records only',fontsize=10,weight='bold')
    fig.text(.075,y-.043,f"{author['dispatch_intents']} attempt intents · {author['known_responses']} known replies · "
        f"{author['interrupted_response_unknown']} response unknown",fontsize=9)
    fig.text(.075,y-.082,f"{costs['prompt_tokens']['recorded_sum']:,.0f} prompt + "
        f"{costs['completion_tokens']['recorded_sum']:,.0f} completion tokens · "
        f"{costs['model_call_seconds']['recorded_sum']/60:.2f} recorded minutes",fontsize=9)
    fig.text(.075,y-.119,'Unknown attempt cost not imputed. Scientist calls/cost: 0.',fontsize=9)
    fig.text(.075,.055,'Engineering diagnostic only; no controlled A1 comparison,\nscientific-value, optimizer or institutional-benefit claim.',fontsize=8,color='#555555')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    outputs={}
    with plt.rc_context({'svg.hashsalt':'native-authoring-ir-qa-v14'}):
        for suffix in ('.png','.svg'):
            path=output.with_suffix(suffix)
            fig.savefig(path,dpi=180,metadata={'Date':None} if suffix=='.svg' else {})
            outputs[path.name]=file_sha256(path)
    plt.close(fig)
    manifest={'schema':'scienceutopia.native-authoring-ir-qa-figure.v14',
        'audit_content_sha256':report['content_sha256'],'width_inches':5.5,'height_inches':5.7,
        'actual_data_only':True,'files':outputs}
    manifest['content_sha256']=digest(manifest)
    write_json_atomic(output.with_suffix('.manifest.json'),manifest,sort_keys=True,allow_nan=False)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();render(read(args.report),args.output)


if __name__=='__main__':main()
