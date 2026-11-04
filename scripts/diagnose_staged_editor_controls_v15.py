"""Explicit second diagnosis budget:12 instructed syntax controls, never world design."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import urllib.request

import diagnose_staged_designer_v15 as d
import diagnose_staged_designer_wire_v15 as w

EXPECTED={'tool':'edit','operations':[{'op':'add','path':'/metadata/diagnostic_probe','value':'control'}]}
MINIMAL={'type':'object','required':['tool','operations'],'additionalProperties':False,'properties':{
    'tool':{'const':'edit'},'operations':{'type':'array','minItems':1,'maxItems':1,'items':{
        'type':'object','required':['op','path','value'],'additionalProperties':False,'properties':{
            'op':{'const':'add'},'path':{'type':'string'},'value':{'type':'string'}}}}}}
INSTRUCTION=('This is an isolated JSON editing INTERFACE CONTROL, NOT scientific optimization. '
    'For this response use the document {"metadata": {}}. Add the missing key diagnostic_probe '
    'inside metadata with the string value control. Use tool edit and one op add at the full-document '
    'path /metadata/diagnostic_probe. Do not use replace: the key is absent. '
    'The only allowed outer keys are tool and operations; the operation keys are op, path, value. '
    'Do not include selector, rationale, explanation or any other field. Return the action JSON only. '
    'Nothing will be executed or adopted.')


def prepare(previous,output):
    if d.git('status','--porcelain=v1'):raise ValueError('clean committed source required')
    old=d.read(previous/'plan.json')
    if len(list((previous/'calls').glob('*.completed.json')))!=10:raise ValueError('prior phase must be closed')
    cases=[]
    for ref in [c for c in old['cases'] if c['variant']=='ordered_baseline']:
        base=json.loads(ref['wire_request_utf8'])
        for context in ('isolated','institution'):
            for grammar in ('full','json','minimal'):
                p=deepcopy(base)
                if context=='isolated':p['messages']=[{'role':'system','content':INSTRUCTION},
                    {'role':'user','content':'Document: {"metadata": {}}. Return the requested edit action.'}]
                else:p['messages'][0]['content']+='\n\nAUTHORITATIVE INTERFACE CONTROL\n'+INSTRUCTION
                if grammar=='json':p['format']='json'
                elif grammar=='minimal':p['format']=deepcopy(MINIMAL)
                body=w.wire_bytes(p)
                cases.append({'id':ref['target']+'-'+context+'-'+grammar,'target':ref['target'],
                    'context':context,'grammar':grammar,'wire_request_utf8':body.decode(),'wire_sha256':d.sha(body)})
    output.mkdir(parents=True,exist_ok=False)
    plan={'schema':'scienceutopia.staged-editor-control-plan.v15','source_commit':d.git('rev-parse','HEAD'),
        'created_utc':d.now(),'previous_plan':str(previous/'plan.json'),'previous_plan_sha256':d.sha((previous/'plan.json').read_bytes()),
        'previous_diagnostic_POSTs':30,'maximum_new_POSTs':12,'maximum_combined_POSTs':42,
        'model_digest':old['model_digest'],'native_trials':0,'generated_source_execution':False,
        'production_changes':False,'temperature':.2,'thinking':False,'output_token_bound':2048,
        'request_timeout_seconds':180,'network_retries':0,'cases':cases,'expected_action':EXPECTED,
        'purpose':'Factorial syntax/instruction-following control, not institutional invention or optimization.'}
    plan['content_sha256']=d.sha(d.canonical(plan));d.fresh(output/'plan.json',plan)
    return {'cases':len(cases),'source_commit':plan['source_commit'],'content_sha256':plan['content_sha256']}


def run(output):
    plan=d.read(output/'plan.json')
    if d.git('rev-parse','HEAD')!=plan['source_commit'] or d.git('status','--porcelain=v1'):raise ValueError('exact clean source required')
    actual=next(m['digest'] for m in d.local_get('tags')['models'] if m['name']=='qwen3:8b')
    if actual!=plan['model_digest']:raise ValueError('pinned model differs')
    d.fresh(output/'backend.json',{'version':d.local_get('version'),'model_digest':actual})
    directory=output/'calls';directory.mkdir()
    for case in plan['cases']:
        if len(list(directory.glob('*.started.json')))>=12:raise ValueError('budget exhausted')
        body=case['wire_request_utf8'].encode()
        if d.sha(body)!=case['wire_sha256']:raise ValueError('planned wire body changed')
        start=directory/(case['id']+'.started.json');d.fresh(start,{'created_utc':d.now(),**case,'model_digest':actual})
        begin=time.monotonic();v={k:case[k] for k in ('id','target','context','grammar','wire_sha256')}
        v.update(started_file_sha256=d.sha(start.read_bytes()),new_model_calls=1,native_trials=0)
        try:
            q=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=body,headers={'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(q,timeout=180) as r:raw=r.read().decode();v['http_status']=r.status
            reply=json.loads(raw);v.update(status='reply-known',raw_response=raw,response=reply,
                incomplete=reply.get('done') is not True or reply.get('done_reason')=='length')
            try:v['action']=json.loads(reply['message']['content'])
            except (ValueError,KeyError) as error:v['parse_error']=str(error)
            v['exact_control_pass']=not v['incomplete'] and v.get('action')==EXPECTED
        except Exception as error:v.update(status='transport-failed-or-response-unknown',error=type(error).__name__+': '+str(error),exact_control_pass=False)
        v.update(elapsed_seconds=time.monotonic()-begin,ended_utc=d.now());d.fresh(directory/(case['id']+'.completed.json'),v)
        print(json.dumps({k:v.get(k) for k in ('id','exact_control_pass','action','incomplete','elapsed_seconds')}),flush=True)
    return {'new_diagnostic_POSTs':12,'total_diagnostic_POSTs':42,'native_trials':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run']);p.add_argument('--previous',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(prepare(a.previous.resolve(),a.output.resolve()) if a.mode=='prepare' else run(a.output.resolve())))
