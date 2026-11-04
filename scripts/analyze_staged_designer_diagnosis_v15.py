"""Cold read-only joins for42 diagnostic replies and five zero-token grammar queries."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from unittest.mock import patch

from jsonschema import Draft202012Validator
import diagnose_staged_designer_v15 as d


def verify_inventory(raw, compact):
    expected=d.read(compact)['audit']['raw_input_sha256s']; actual=d.inventory(raw)
    if expected!=actual:raise ValueError('published historical raw inventory changed')
    return {'root':str(raw),'files':len(actual),'inventory_sha256':d.sha(d.canonical(actual))}


def grammar_rules(grammar):
    return dict(line.split(' ::= ',1) for line in grammar.splitlines() if ' ::= ' in line)


def analyze(base,historical_root):
    sys.path.insert(0,str(historical_root))
    from utopia.optimization import native_staged_author_v15 as historical
    if not Path(historical.__file__).resolve().is_relative_to(historical_root):raise ValueError('wrong historical interpreter')
    if d.git('rev-parse','HEAD',root=historical_root)!=d.ACTUAL:raise ValueError('historical source differs')
    root=d.ROOT; raw_parent=Path(d.read(base/'paired-a1/plan.json')['raw_root']).parent
    historical_before={name:verify_inventory(raw_parent/('native-staged-search-v15-'+name),
        root/('research/results/native-staged-search-v15-'+name+'.json')) for name in ('a1','a2')}
    plans={name:d.read(base/name/'plan.json') for name in ('paired-a1','wire-a2','controls-a3')}
    for name,plan in plans.items():
        if plan['content_sha256']!=d.sha(d.canonical({k:v for k,v in plan.items() if k!='content_sha256'})):
            raise ValueError('planned content changed: '+name)
    binding_by_target={}
    for c in plans['paired-a1']['cases']:
        binding_by_target[c['target']]=d.read(Path(c['historical_generation_directory'])/'request.json')
    rows=[]; artifacts={}; tokens=Counter(); seconds=0.0
    for phase,expected_count in [('paired-a1',20),('wire-a2',10),('controls-a3',12)]:
        folder=base/phase; cases={c.get('id'):c for c in plans[phase]['cases']}
        starts=list((folder/'calls').glob('*.started.json'));completes=list((folder/'calls').glob('*.completed.json'))
        if len(starts)!=expected_count or len(completes)!=expected_count:raise ValueError('incomplete diagnostic phase')
        for path in sorted(completes):
            v=d.read(path);identity=v.get('case_id',v.get('id'));case=cases[identity]
            started=folder/'calls'/(identity+'.started.json')
            if v['started_file_sha256']!=d.sha(started.read_bytes()):raise ValueError('intent/reply binding differs')
            if phase!='paired-a1':
                body=case['wire_request_utf8'];intent=d.read(started)
                if d.sha(body.encode())!=case['wire_sha256'] or intent['wire_request_utf8']!=body:raise ValueError('wire bytes differ')
            else:
                if d.read(started)['payload']!=case['payload']:raise ValueError('payload differs')
            reply=v.get('response',{});action=v.get('action')
            if v.get('raw_response') and json.loads(v['raw_response'])!=reply:raise ValueError('raw response differs')
            complete=reply.get('done') is True and reply.get('done_reason')!='length' and isinstance(action,dict)
            schema_valid=complete and not list(Draft202012Validator(historical.ACTION_SCHEMA).iter_errors(action))
            binding=binding_by_target[case['target']];state=historical.initial_draft(binding['request'])
            receipt=None
            if schema_valid:
                with patch('subprocess.Popen',side_effect=AssertionError('no process in diagnosis analysis')), \
                     patch('socket.socket',side_effect=AssertionError('no tool network in diagnosis analysis')):
                    state,receipt=historical.transition(state,action,binding['request'],
                        binding_sha256=binding['binding_sha256'],provider_binding=binding['provider_binding'])
            r={'id':identity,'phase':phase,'target':case['target'],'variant':case.get('variant'),
                'context':case.get('context'),'grammar':case.get('grammar'),'complete_JSON_object':complete,
                'provider_schema_valid':bool(schema_valid),'historical_tool_valid':bool(receipt and receipt['ok']),
                'action':action,'static_tool_errors':receipt['errors'] if receipt else None,
                'applied_operations':len(state['operations']) if receipt else 0,
                'inspect_empty_object':(receipt['result'].get('value')=={}) if receipt and receipt['tool']=='inspect' and receipt['ok'] else None,
                'exact_control_pass':v.get('exact_control_pass'),
                'prompt_tokens':reply.get('prompt_eval_count'),'completion_tokens':reply.get('eval_count'),
                'elapsed_seconds':v['elapsed_seconds'],'completion_sha256':d.sha(path.read_bytes())}
            rows.append(r);seconds+=v['elapsed_seconds']
            for metric in ('prompt_eval_count','eval_count'):
                if reply.get(metric) is None:tokens[metric+'_unknown_replies']+=1
                else:tokens[metric+'_known_sum']+=reply[metric]
    comparisons=[]
    for target in ('efficiency','throughput'):
        old=next(c for c in plans['paired-a1']['cases'] if c['id']==target+'-baseline')
        new=next(c for c in plans['wire-a2']['cases'] if c['id']==target+'-ordered_baseline')
        if json.loads(new['wire_request_utf8'])!=old['payload']:raise ValueError('schema-order-only comparison changed values')
        expected=d.read(Path(old['historical_step_file']))['model_reply']['output']
        actual=next(r for r in rows if r['id']==new['id'])['action']
        comparisons.append({'target':target,'semantic_payloads_equal':True,
            'schema_key_order_only_changed':True,'ordered_baseline_matches_historical_action':actual==expected})
    grammar={}
    for name in ('empty-value','explicit-string-value','full-author-schema','explicit-anyof','explicit-type-list'):
        p=base/'grammar-metadata'/(name+'.completed.json');v=d.read(p);body=v['response']
        if body['tokens_evaluated']!=0 or body['tokens_predicted']!=0:raise ValueError('metadata query performed inference')
        rules=grammar_rules(body['generation_settings/grammar'])
        grammar[name]={'tokens_evaluated':0,'tokens_predicted':0,'file_sha256':d.sha(p.read_bytes()),
            'critical_rules':{k:v for k,v in rules.items() if k in ('value-','value-kv') or
                k in ('operations-item-0-value','operations-item-1-value','operations-item-3-value','operations-item-4-value')}}
    required=grammar['full-author-schema']['critical_rules']
    if len(required)!=4 or set(required.values())!={'object'}:raise ValueError('unexpected compiled edit-value grammar')
    from diagnose_staged_editor_controls_v15 import EXPECTED
    if list(Draft202012Validator(historical.ACTION_SCHEMA).iter_errors(EXPECTED)):
        raise ValueError('the string-valued control must be valid according to declared schema')
    control_counts={}
    for context in ('isolated','institution'):
        for schema in ('full','json','minimal'):
            subset=[r for r in rows if r['phase']=='controls-a3' and r['context']==context and r['grammar']==schema]
            control_counts[context+'/'+schema]={'passed':sum(r['exact_control_pass'] is True for r in subset),'total':len(subset)}
    for path in sorted(base.rglob('*')):
        if path.is_file() and not path.name.endswith('.log') and 'report-' not in path.name:
            artifacts[str(path.relative_to(base))]=d.sha(path.read_bytes())
    historical_after={name:verify_inventory(Path(v['root']),root/('research/results/native-staged-search-v15-'+name+'.json'))
        for name,v in historical_before.items()}
    if historical_after!=historical_before:raise ValueError('historical evidence changed')
    result={'schema':'scienceutopia.staged-designer-causal-diagnosis.v15','analysis_source_commit':d.git('rev-parse','HEAD'),
        'analysis_script_sha256':d.sha(Path(__file__).read_bytes()),'historical_interpreter_commit':d.ACTUAL,
        'historical_inventories_unchanged':historical_after,'diagnostic_plan_sources':{k:v['source_commit'] for k,v in plans.items()},
        'diagnostic_model_POSTs':42,'known_replies':len(rows),'unknown_intents':0,
        'zero_token_grammar_queries':5,'native_trials':0,'generated_source_executions':0,'production_runtime_changes':False,
        'control_counts':control_counts,'schema_order_comparisons':comparisons,'compiled_grammar':grammar,
        'declared_schema_accepts_string_control_but_compiled_value_rules_object_only':True,
        'loop_detector_is_a_proven_detection_gap_not_sufficient_explanation_of_loop_origin':True,
        'complex_grammar_is_a_locally_demonstrated_edit_obstacle':True,
        'all_arbitrary_institution_edits_impossible_claimed':False,
        'sole_cause_of_historical_inspection_choice_identified':False,
        'eight_billion_parameter_capacity_limit_identified':False,
        'fixed_designer_or_invention_demonstrated':False,
        'recorded_transport_seconds_sum':seconds,'token_accounting':dict(tokens),'rows':rows,
        'raw_artifact_sha256s':artifacts,
        'upstream_reference':'https://github.com/ggml-org/llama.cpp/blob/b10760/common/json-schema-to-grammar.cpp#L1018',
        'upstream_reference_is_not_substituted_for_observed_local_grammar':True}
    result['content_sha256']=d.sha(d.canonical(result));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--historical-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    v=analyze(a.base.resolve(),a.historical_root.resolve());d.fresh(a.output,v)
    print(json.dumps({'output':str(a.output),'content_sha256':v['content_sha256'],'controls':v['control_counts']}))
