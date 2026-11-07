"""Read-only scientist token accounting from CLOSED source-audited journals.

Token counts are reported by the provider, not FLOPs, GPU time, energy or money.
Missing/invalid usage and wire inputs without committed replies are not zeros.
"""
import argparse
import hashlib
from pathlib import Path
import sqlite3

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_design_benchmark import checked
from scripts.reports.native_selection_relaxation import CONTROLS,STUDY
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json,file_sha256,write_json_atomic

SCHEMA='scienceutopia.native-scientist-token-costs.v1'
FIELDS=('prompt_tokens','completion_tokens','total_tokens','cached_prompt_tokens')


def usage_values(response):
    usage=response.get('usage');usage=usage if isinstance(usage,dict) else {}
    details=usage.get('prompt_tokens_details');details=details if isinstance(details,dict) else {}
    return {**{key:usage.get(key) for key in FIELDS[:3]},
        'cached_prompt_tokens':details.get('cached_tokens')}


def summarize(values):
    result={}
    for key in FIELDS:
        known=[v[key] for v in values if type(v[key]) is int and v[key]>=0]
        missing=sum(v[key] is None for v in values)
        result[key]={'recorded_sum':sum(known) if known or not values else None,
            'known_responses':len(known),'missing_responses':missing,
            'invalid_responses':len(values)-len(known)-missing,
            'all_completed_responses_known':len(known)==len(values)}
    return result


def group(relative,schema):
    parts=Path(relative).parts
    if schema==CONTROLS and len(parts)==6 and parts[0]=='controls' and parts[2]=='worlds':
        return 'reference:'+parts[1]
    if schema==STUDY:
        if len(parts)==8 and parts[0]=='search' and parts[2]=='arms' and parts[4]=='worlds':
            return 'search:'+parts[1]+':'+parts[3]
        if len(parts)==6 and parts[0] in ('references','evaluation') and parts[2]=='worlds':
            return parts[0]+':'+parts[1]
    raise ValueError('response journal outside declared physical study layout')


def cache_usage(path,plan):
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        bindings=db.execute('SELECT binding FROM metadata').fetchall()
        rows=db.execute('SELECT identity,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    if len(bindings)!=1:raise ValueError('one original response binding required')
    binding=decode_json(bindings[0][0],strict=True,finite_floats=True)
    if (binding['model']!=plan['scientist']['model'] or binding['model_revision']!=plan['scientist']['model_digest']
            or binding['corpus_sha256']!=plan['scientist']['corpus_sha256']
            or binding['science_config']['source_commit']!=plan['source_commit']):
        raise ValueError('response journal role/model/corpus/source differs')
    wire=path.parent.parent/'wire-requests.jsonl'
    wires=[decode_json(line,strict=True,finite_floats=True) for line in wire.read_text().splitlines()] if wire.exists() else []
    values=[];offset=0;matched=[];mismatches=0
    for identity,payload_sha,outcome,data,data_sha in rows:
        if outcome!='response' or hashlib.sha256(data.encode()).hexdigest()!=data_sha:
            raise ValueError('committed response body/outcome differs')
        response=decode_json(data,strict=True,finite_floats=True)
        if response.get('model')!=binding['model']:raise ValueError('response model differs')
        while offset<len(wires) and wires[offset]['payload_sha256']!=payload_sha:offset+=1
        if offset==len(wires):raise ValueError('committed reply lacks its ordered wire input')
        matched.append(offset);offset+=1
        value=usage_values(response);values.append(value)
        if all(type(value[k]) is int and value[k]>=0 for k in FIELDS[:3]):
            mismatches+=value['total_tokens']!=value['prompt_tokens']+value['completion_tokens']
    return {'completed_responses':len(rows),'wire_inputs':len(wires),
        'wire_inputs_without_committed_reply':len(wires)-len(rows),
        'provider_total_component_disagreements':mismatches,'usage':summarize(values),
        'values':values,'matched_wire_indices_sha256':digest(matched)}


def analyze(root,plan,audit,*,expected_source):
    root=Path(root).resolve();schema=plan.get('schema')
    if schema not in (CONTROLS,STUDY):raise ValueError('supported closed protocol required')
    checked(plan,schema);checked(audit,schema+'.audit')
    if (plan['source_commit']!=expected_source or audit['source_commit']!=expected_source
            or audit['plan_sha256']!=plan['content_sha256']
            or audit['source_proofs']['status']!='verified-exact-source-closure'
            or audit['writer']['ended']['status']!='exited' or audit['writer']['ended']['exit_code']!=0
            or audit['new_model_calls']!=0 or audit['new_code_executions']!=0):
        raise ValueError('closed original-source audit required; never summarize a live writer')
    before=_inventory(root)
    if before!=audit['input_inventory']:raise ValueError('raw inventory differs from exact audit')
    try:
        caches=[];all_values=[];groups={};seen_wires=set()
        for relative in sorted(before):
            if not relative.endswith('/replies/responses.sqlite'):continue
            identity=group(relative,schema);path=root/relative
            data=cache_usage(path,plan);values=data.pop('values');all_values.extend(values)
            groups.setdefault(identity,[]).extend(values)
            caches.append({'relative_path':relative,'group':identity,'sql_sha256':before[relative],**data})
            seen_wires.add(str(Path(relative).parent.parent/'wire-requests.jsonl'))
        wire_only=[]
        for relative in sorted(before):
            if not relative.endswith('/wire-requests.jsonl') or relative in seen_wires:continue
            identity=group(str(Path(relative).parent/'replies/responses.sqlite'),schema)
            lines=(root/relative).read_text().splitlines()
            for line in lines:decode_json(line,strict=True,finite_floats=True)
            wire_only.append({'relative_path':relative,'group':identity,'sha256':before[relative],
                'wire_inputs':len(lines),'response_usage':'unknown-no-response-journal'})
        result={'schema':SCHEMA,'classification':plan['classification'],
            'source_commit':expected_source,'plan_sha256':plan['content_sha256'],
            'input_audit_content_sha256':audit['content_sha256'],'input_inventory_sha256':digest(before),
            'projection_source_sha256':file_sha256(Path(__file__)),
            'physical_response_journals':len(caches),'completed_responses':len(all_values),
            'wire_inputs':sum(c['wire_inputs'] for c in caches)+sum(w['wire_inputs'] for w in wire_only),
            'wire_inputs_without_committed_reply':sum(c['wire_inputs_without_committed_reply'] for c in caches)
                +sum(w['wire_inputs'] for w in wire_only),
            'provider_total_component_disagreements':sum(c['provider_total_component_disagreements'] for c in caches),
            'usage':summarize(all_values),'groups':{key:summarize(value) for key,value in groups.items()},
            'caches':caches,'wire_only_worlds':wire_only,
            'raw_inventory_unchanged':True,'new_model_calls':0,'new_code_executions':0,
            'full_experiment_compute_cost_claimed':False,
            'unknown_usage_imputed':False,'is_new_original_source_audit':False,
            'scope':'Scientist committed response usage only, including partial native worlds. Every distinct audited physical journal counts once; identical reply content is not deduplicated across worlds. Failed/pre-journal worlds, uncommitted wire responses, designers, calibration, role loads, model-server caching, retrieval, container/host work, earlier exploration and coding-agent costs are not converted into zero token/FLOP/energy/time/money costs. Prompt counts include provider-reported cached tokens; they are not a count of fresh GPU operations.'}
        result['content_sha256']=digest(result);return result
    finally:
        if _inventory(root)!=before:raise ValueError('raw evidence changed during token projection')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--audit',type=Path,required=True);p.add_argument('--expected-source',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    if a.output.exists() or a.output.resolve().is_relative_to(a.run.resolve()):
        p.error('fresh token projection outside raw root required')
    original={path:path.read_bytes() for path in (a.plan,a.audit)}
    data={path:decode_json(body.decode(),strict=True,finite_floats=True) for path,body in original.items()}
    result=analyze(a.run,data[a.plan],data[a.audit],expected_source=a.expected_source)
    if any(path.read_bytes()!=body for path,body in original.items()):raise ValueError('input audit/plan changed')
    write_json_atomic(a.output,result,sort_keys=True,allow_nan=False,indent=2)
    print({'content_sha256':result['content_sha256'],'completed_scientist_responses':result['completed_responses']})
    return 0


if __name__=='__main__':raise SystemExit(main())
