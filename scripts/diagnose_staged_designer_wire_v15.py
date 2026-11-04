"""Within the original30-POST diagnosis budget, test schema ordering and edit controls.

Historical journals sort object keys. Preserve source-reconstructed grammar
ordering as a literal HTTP body; semantic dict equality alone loses that order.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

import diagnose_staged_designer_v15 as d


def wire_bytes(payload):
    return json.dumps(payload, sort_keys=False, ensure_ascii=False, allow_nan=False).encode()


def historical_schema(root):
    if d.git('rev-parse', 'HEAD', root=root) != d.ACTUAL or d.git('status', '--porcelain=v1', root=root):
        raise ValueError('clean exact historical source required')
    program = ('import sys,json;sys.path.insert(0,sys.argv[1]);'
        'from utopia.optimization.native_staged_author_v15 import ACTION_SCHEMA;'
        'print(json.dumps(ACTION_SCHEMA,sort_keys=False))')
    return json.loads(subprocess.check_output([sys.executable, '-c', program, str(root)], text=True, cwd=root))


def ordered_payload(original, schema):
    if original['format'] != schema:
        raise ValueError('historical schema semantics differ from stored request')
    result = deepcopy(original); result['format'] = deepcopy(schema)
    if result != original:
        raise ValueError('source-order reconstruction must not change semantic fields')
    return result


def prepare(prior, output, historical):
    if d.git('status', '--porcelain=v1'):
        raise ValueError('clean committed diagnostic source required')
    previous = d.read(prior / 'plan.json')
    completions = list((prior / 'calls').glob('*.completed.json'))
    intents = list((prior / 'calls').glob('*.started.json'))
    if len(completions) != len(intents) or len(intents) != 20 or (prior / 'followups').exists():
        raise ValueError('exact20 terminal first-phase calls and no followups required')
    schema = historical_schema(historical)
    cases = []
    for old in [c for c in previous['cases'] if c['variant'] == 'baseline']:
        generation = Path(old['historical_generation_directory'])
        steps = [d.read(generation / f'step-{i:02d}.completed.json') for i in range(2)]
        base = ordered_payload(old['payload'], schema)
        for name, treatment in [('ordered_baseline', 'baseline'), ('ordered_role', 'trusted_role'),
                ('ordered_combined', 'combined'), ('ordered_control', 'interface_control'),
                ('json_control', 'interface_control')]:
            payload = d.intervene(base, treatment, steps)
            if name == 'json_control':
                payload['format'] = 'json'
            body = wire_bytes(payload)
            cases.append({'id': old['target'] + '-' + name, 'target': old['target'], 'variant': name,
                'wire_request_utf8': body.decode(), 'wire_sha256': d.sha(body),
                'payload_sha256': d.sha(d.canonical(payload)),
                'historical_step_file': old['historical_step_file'],
                'historical_generation_directory': str(generation)})
    output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'scienceutopia.staged-author-wire-diagnosis-plan.v15',
        'source_commit': d.git('rev-parse', 'HEAD'), 'created_utc': d.now(),
        'previous_plan_path': str(prior / 'plan.json'), 'previous_plan_sha256': d.sha((prior / 'plan.json').read_bytes()),
        'previous_calls':20, 'max_new_calls':10, 'max_total_diagnostic_calls':30,
        'first_phase_followups_cancelled_before_any_dispatch': True,
        'historical_source': d.ACTUAL, 'historical_checkout': str(historical),
        'source_schema_order': list(schema['properties']),
        'stored_sorted_schema_order': list(previous['cases'][0]['payload']['format']['properties']),
        'model_digest': previous['model_digest'], 'raw_root': previous['raw_root'],
        'raw_inventory_sha256': previous['raw_inventory_sha256'],
        'native_trials':0, 'production_changes':False, 'generated_source_execution':False,
        'network_retries':0, 'cases':cases,
        'hypothesis': 'Schema property ordering may affect constrained decoding; this is tested, not assumed.',
        'limits': ['Source reconstruction recovers schema insertion order, not unarchived original HTTP bytes.',
            'Current backend version is shared across paired interventions, not proven equal to historical backend.',
            'The specified metadata control is not autonomous invention or a scientific optimization result.']}
    result['content_sha256'] = d.sha(d.canonical(result)); d.fresh(output / 'plan.json', result)
    return {'cases':len(cases), 'source_commit':result['source_commit'], 'content_sha256':result['content_sha256']}


def run(output):
    plan = d.read(output / 'plan.json')
    if d.git('rev-parse', 'HEAD') != plan['source_commit'] or d.git('status', '--porcelain=v1'):
        raise ValueError('clean exact source required')
    actual = next(m['digest'] for m in d.local_get('tags')['models'] if m['name'] == 'qwen3:8b')
    if actual != plan['model_digest']:
        raise ValueError('pinned model differs')
    d.fresh(output / 'backend.json', {'version':d.local_get('version'), 'model_digest':actual})
    directory=output/'calls';directory.mkdir()
    prior=Path(plan['previous_plan_path']).parent
    for case in plan['cases']:
        if (prior/'followups').exists() or len(list((prior/'calls').glob('*.started.json'))) + len(list(directory.glob('*.started.json'))) >= 30:
            raise ValueError('shared30-POST budget exhausted or cancelled followups dispatched')
        body=case['wire_request_utf8'].encode()
        if d.sha(body)!=case['wire_sha256'] or d.sha(d.canonical(json.loads(body)))!=case['payload_sha256']:
            raise ValueError('frozen wire payload changed')
        started=directory/(case['id']+'.started.json')
        d.fresh(started, {'created_utc':d.now(), 'case_id':case['id'], 'wire_sha256':case['wire_sha256'],
            'wire_request_utf8':case['wire_request_utf8'], 'model_digest':actual})
        begin=time.monotonic();result={'case_id':case['id'], 'target':case['target'], 'variant':case['variant'],
            'wire_sha256':case['wire_sha256'], 'started_file_sha256':d.sha(started.read_bytes()),
            'new_model_calls':1, 'native_trials':0}
        try:
            request=urllib.request.Request('http://127.0.0.1:11434/api/chat', data=body,
                headers={'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(request,timeout=180) as response:
                text=response.read().decode();result['http_status']=response.status
            reply=json.loads(text);result.update(status='reply-known',raw_response=text,response=reply,
                truncated=reply.get('done') is not True or reply.get('done_reason')=='length')
            try:result['action']=json.loads(reply['message']['content'])
            except (ValueError,KeyError) as error:result['parse_error']=str(error)
        except Exception as error:
            result.update(status='transport-failed-or-response-unknown',error=type(error).__name__+': '+str(error))
        result.update(elapsed_seconds=time.monotonic()-begin,ended_utc=d.now())
        d.fresh(directory/(case['id']+'.completed.json'),result)
        print(json.dumps({k:result.get(k) for k in ('case_id','status','action','truncated','elapsed_seconds')}),flush=True)
    return {'total_new_calls':10,'shared_diagnosis_calls':30,'native_trials':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run'])
    p.add_argument('--prior',type=Path);p.add_argument('--historical',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    value=prepare(a.prior.resolve(),a.output.resolve(),a.historical.resolve()) if a.mode=='prepare' else run(a.output.resolve())
    print(json.dumps(value))


if __name__=='__main__':main()
