"""Closed-audit cost components for native studies, including every model role.

Read-only journals, no inference. Counts are provider-reported usage, not fresh
GPU work or monetary cost. Native/transport aliases and nested times stay apart.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_auxiliary_costs import event,summarize as summarize_auxiliary
from scripts.reports.native_token_costs import cache_usage,summarize as summarize_tokens
from utopia.optimization.native_numeric_designer import checked
from utopia.optimization.native_scientist_load_v38 import replay_load
from utopia.system.design_patch import digest,clone
from utopia.utils.data_utils import decode_json,file_sha256,write_json_atomic

SCHEMA='scienceutopia.pre-scale-cost-components.v1'
AUDITS=('scienceutopia.pre-scale-information-audit.v1','scienceutopia.pre-scale-search-audit.v1',
        'scienceutopia.native-institution-loop-audit.v1',
        'scienceutopia.native-institution-loop-stopped-audit.v1',
        'scienceutopia.native-fixed-candidate-evaluation-audit.v1',
        'scienceutopia.native-code-tested-loop-audit.v1',
        'scienceutopia.native-liquidity-support-audit.v1',
        'scienceutopia.native-objective-instrument-loop-audit.v1',
        'scienceutopia.native-objective-fixed-evaluation-audit.v1',
        'scienceutopia.native-objective-initial-stop-audit.v1',
        'scienceutopia.native-instruction-timing-support-audit.v1',
        'scienceutopia.native-capacity-objective-loop-audit.v1',
        'scienceutopia.native-capacity-fixed-evaluation-audit.v1',
        'scienceutopia.native-catalog-actuation-audit.v1',
        'scienceutopia.native-planning-objective-loop-audit.v1',
        'scienceutopia.native-planning-fixed-evaluation-audit.v1',
        'scienceutopia.native-parent-presentation-loop-audit.v1',
        'scienceutopia.native-parameter-comparator-audit.v1',
        'scienceutopia.native-joint-fixed-evaluation-audit.v1',
        'scienceutopia.native-workflow-objective-loop-audit.v1',
        'scienceutopia.native-workflow-fixed-evaluation-audit.v1',
        'scienceutopia.native-longitudinal-comparison-audit.v1',
        'scienceutopia.native-longitudinal-fixed-evaluation-audit.v1',
        'scienceutopia.native-legacy-choice-pilot-audit.v1',
        'scienceutopia.native-legacy-topic-pilot-audit.v1',
        'scienceutopia.native-terminal-cost-pilot-audit.v1',
        'scienceutopia.native-topic-free-optimization.v1.audit',
        'scienceutopia.native-consumer-source-comparison.v1.audit',
        'scienceutopia.native-priority-method-comparison.v1.audit')


def classify_numeric(relative):
    return 'numeric-readiness' if 'numeric-readiness' in Path(relative).parts else 'numeric-proposal'


def classify_staged(relative):
    return 'editor-readiness' if 'editor-readiness' in Path(relative).parts else 'staged-proposal'


def workflow_event(relative,intent,response,*,model):
    checked(intent)
    if intent['provider']['model']!=model:raise ValueError('workflow cost provider differs')
    if response is not None:
        checked(response)
        if response['intent_sha256']!=intent['content_sha256']:
            raise ValueError('workflow cost response/intent differs')
    transport={} if response is None else clone(response['transport'])
    if 'request_wire_utf8' in transport:
        if transport['request_wire_utf8']!=intent['request_wire']['request_wire_utf8']:
            raise ValueError('workflow cost wire differs from intent')
        transport['request_payload']=clone(intent['payload'])
    kind='workflow-readiness' if Path(relative).parent.name.startswith('calibration-') else 'workflow-proposal'
    return event(kind,relative,transport,model=model,
        status='response-unknown' if response is None else 'error' if response.get('error') else 'http-recorded',
        completion=response is not None,caller_seconds=None if response is None else response.get('elapsed_seconds'))


def numeric_event(relative,intent,response,*,model):
    checked(intent)
    if intent['provider']['model']!=model:raise ValueError('numeric cost provider differs')
    if response is not None:
        checked(response)
        if response['intent_sha256']!=intent['content_sha256']:
            raise ValueError('numeric cost response/intent differs')
    transport={} if response is None else response['transport']
    return event(classify_numeric(relative),relative,transport,model=model,
        status='response-unknown' if response is None else 'error' if response.get('error') else 'http-recorded',
        completion=response is not None,caller_seconds=None if response is None else response.get('elapsed_seconds'))


def staged_event(relative,intent,response,*,model):
    checked(intent)
    payload=decode_json(intent['wire_utf8'],strict=True,finite_floats=True)
    if payload['model']!=model:raise ValueError('staged cost wire model differs')
    transport={}
    if response is not None:
        checked(response)
        if response['intent_sha256']!=intent['content_sha256']:
            raise ValueError('staged cost response/intent differs')
        transport={'request_payload':payload,'elapsed_seconds':response.get('elapsed_seconds')}
        if 'raw_http_response' in response:
            transport.update(raw_http_response=response['raw_http_response'],http_status=response['http_status'])
            try:transport['response_payload']=decode_json(response['raw_http_response'],strict=True,finite_floats=True)
            except (ValueError,TypeError):pass  # Preserve malformed raw text; no fabricated usage.
    return event(classify_staged(relative),relative,transport,model=model,
        status='response-unknown' if response is None else 'error' if response.get('error_type') else 'http-recorded',
        completion=response is not None)


def load_event(relative,intent,response,*,provider):
    proof=replay_load(intent,response,provider=provider,purpose=intent['purpose'],role=intent['role'])
    transport={} if response is None else {k:response[k] for k in
        ('raw_http_response','response_payload','http_status') if k in response}
    if response is not None:transport['request_payload']=intent['request_payload']
    return event('load-'+intent['role'],relative,transport,model=provider['model'],status=proof['status'],
        completion=response is not None,caller_seconds=None if response is None else response.get('elapsed_seconds'))


def analyze(root,plan,audit):
    root=Path(root).resolve();checked(plan);checked(audit)
    if (audit['schema'] not in AUDITS or plan['source_commit']!=audit['source_commit']
            or plan['content_sha256']!=audit['plan_sha256']
            or audit.get('source_proof',{}).get('status')!='verified-exact-source-closure'
            or audit['new_model_calls']!=0 or audit['new_code_executions']!=0):
        raise ValueError('matching closed original-source native study audit required')
    before=_inventory(root)
    if digest(before)!=audit['raw_inventory_sha256'] or len(before)!=audit['raw_files']:
        raise ValueError('raw inventory changed from closed original-source audit')
    stopped = audit['schema'] in (AUDITS[3],AUDITS[9])
    closure_name=('mechanisms-complete.json' if audit['schema']==AUDITS[0]
                  else 'terminal.json' if audit['schema'] in AUDITS[2:] else 'complete.json')
    if closure_name not in before:raise ValueError('normal scientific closure required before cost projection')
    closure=checked(json.loads((root/closure_name).read_text()))
    if audit['schema'] in AUDITS[2:]:
        start=checked(json.loads((root/'started.json').read_text()))
        if (closure.get('status')!=('stopped' if stopped else 'closed') or audit.get('closure',{}).get('terminal')!=closure
                or audit['closure'].get('started')!=start
                or start['plan_sha256']!=plan['content_sha256']):
            raise ValueError('native loop closure differs from exact cold audit')
        if stopped and (audit['closure'].get('scientific_study_closed') is not False
                or audit.get('selection') is not None or audit.get('logical_evaluation') != []):
            raise ValueError('stopped costs cannot imply successful selection or scientific closure')
    elif closure['plan_sha256']!=plan['content_sha256']:raise ValueError('closure plan differs')
    if audit['schema']==AUDITS[0]:
        if closure['slots']!=12 or len(closure['all_observation_file_sha256'])!=12 or len(audit['rows'])!=12:
            raise ValueError('all twelve closed mechanism slots required')
        if any(before.get(name)!=identity for name,identity in closure['all_observation_file_sha256'].items()):
            raise ValueError('closed mechanism observations differ')
    elif audit['schema']==AUDITS[1] and closure['selection_sha256']!=audit['selection']['content_sha256']:
        raise ValueError('closed O/E selection differs')
    def read(relative,hashed=True):
        if relative not in before:raise ValueError('unaudited cost record')
        value=decode_json((root/relative).read_text(),strict=True,finite_floats=True)
        return checked(value) if hashed else value
    events=[];caches=[];usage=[];seen_wire=set();wire_only=[]
    for relative in sorted(before):
        if relative.endswith('/replies/responses.sqlite'):
            values=cache_usage(root/relative,plan);usage.extend(values.pop('values'))
            caches.append({'path':relative,'file_sha256':before[relative],**values})
            seen_wire.add(str(Path(relative).parent.parent/'wire-requests.jsonl'))
        elif Path(relative).name=='call.intent.json':
            intent=read(relative)
            if intent.get('schema')!='scienceutopia.local-workflow-designer.v1.intent':
                raise ValueError('unknown workflow-shaped cost intent')
            response_name=str(Path(relative).with_name('call.http.json'))
            events.append(workflow_event(relative,intent,read(response_name) if response_name in before else None,
                model=plan['designer']['model']))
        elif Path(relative).name.startswith('call-') and relative.endswith('.intent.json'):
            response_name=relative.removesuffix('.intent.json')+'.http.json'
            events.append(numeric_event(relative,read(relative),read(response_name) if response_name in before else None,
                model=plan['designer']['model']))
        elif '/wire/dispatch-' in relative and relative.endswith('.intent.json'):
            response_name=relative.removesuffix('.intent.json')+'.http.json'
            events.append(staged_event(relative,read(relative),read(response_name) if response_name in before else None,
                model=plan['designer']['model']))
        elif relative.endswith('.started.json'):
            intent=read(relative,hashed=False)
            if intent.get('schema')!='scienceutopia.explicit-local-role-load.v38.intent':continue
            if intent['role'] not in ('scientist','designer'):raise ValueError('unknown model load role')
            response_name=relative.removesuffix('.started.json')+'.json'
            events.append(load_event(relative,intent,read(response_name) if response_name in before else None,
                provider=plan[intent['role']]))
    for relative in sorted(before):
        if not relative.endswith('/wire-requests.jsonl') or relative in seen_wire:continue
        rows=[decode_json(line,strict=True,finite_floats=True) for line in (root/relative).read_text().splitlines()]
        if any(r['payload']['model']!=plan['scientist']['model'] for r in rows):
            raise ValueError('wire-only journal has a different scientist model')
        wire_only.append({'path':relative,'wire_inputs':len(rows),'committed_usage':None})
    if not caches:raise ValueError('closed native study requires its original scientist response journals')
    groups=defaultdict(list)
    for item in events:groups[item['kind']].append(item)
    result={'schema':SCHEMA,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'input_audit_content_sha256':audit['content_sha256'],'raw_inventory_sha256':digest(before),
        'scientist':{'physical_response_caches':caches,'completed_responses':sum(r['completed_responses'] for r in caches),
            'wire_inputs_without_committed_reply':sum(r['wire_inputs_without_committed_reply'] for r in caches),
            'wire_only_worlds':wire_only,'provider_usage':summarize_tokens(usage)},
        'auxiliary':{'events':events,'groups':{k:summarize_auxiliary(v) for k,v in sorted(groups.items())}},
        'projection_modules':{p.name:file_sha256(p) for p in [Path(__file__),
            Path(__file__).with_name('native_auxiliary_costs.py'),Path(__file__).with_name('native_token_costs.py')]},
        'unknown_usage_imputed':False,'aliases_or_nested_durations_added':False,
        'fresh_GPU_FLOPs_energy_money_or_total_wall_time_claimed':False,
        'scope':'Provider usage, recorded HTTP/caller timing and empty-prompt load records. Native cached prompt counts are a reported subset, not added input tokens. Transport/native aliases and nested duration fields overlap and are never summed. Retrieval/indexing, sandbox, host and code-agent work remain outside measured call components. An intent is not authenticated server receipt.',
        'new_model_calls':0,'new_code_executions':0}
    if before!=_inventory(root):raise ValueError('raw evidence changed during cost projection')
    if stopped:
        result['scientific_termination']='stopped; no held-out evaluation or successful scientific closure'
    # The original cold audit is authoritative about role presence. A second
    # study-name allowlist silently omitted critics for newer study families.
    # Keep old frozen exports unchanged; new projections include every audited
    # common observer instead of guessing that unlisted study names have none.
    if 'observer' in audit:
        critic=audit['observer']
        result['common_content_observer']={'input_observer_audit_content_sha256':critic['content_sha256'],
            'physical_requests':critic['dispatch_intents'],'known_terminal_attempts':critic['known_terminal_attempts'],
            'usage':clone(critic['usage']),'overlap_with_native_response_caches':False,
            'scope':'Separate fixed-content critic POSTs; repeated content cache hits are not additional physical ratings.'}
    result['content_sha256']=digest(result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','plan','audit','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError('fresh independent cost output required')
    originals={str(path):file_sha256(path) for path in (args.plan,args.audit)}
    result=analyze(args.run,json.loads(args.plan.read_text()),json.loads(args.audit.read_text()))
    if any(file_sha256(path)!=value for path,value in originals.items()):raise ValueError('cost input changed')
    write_json_atomic(args.output,result,sort_keys=True,allow_nan=False)
    print(json.dumps({'output':str(args.output),'content_sha256':result['content_sha256'],
        'scientist_responses':result['scientist']['completed_responses'],'auxiliary_intents':len(result['auxiliary']['events'])}))


if __name__=='__main__':main()
