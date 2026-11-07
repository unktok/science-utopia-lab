"""Synthetic raw-cache projection QA, no model, container or science execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.reports import native_token_costs as costs
from utopia.system.design_patch import digest


def hashed(v):v['content_sha256']=digest({k:x for k,x in v.items() if k!='content_sha256'});return v


def make(tmp_path,schema=costs.CONTROLS):
    root=tmp_path/'raw';root.mkdir()
    p=hashed({'schema':schema,'source_commit':'a'*40,'classification':'SCRIPTED-token-QA-only',
        'scientist':{'model':'SCRIPTED','model_digest':'b'*64,'corpus_sha256':'c'*64}})
    return root,p


def cache(root,p,relative,usages,*,unmatched=0):
    path=root/relative;path.parent.mkdir(parents=True)
    binding={'model':'SCRIPTED','model_revision':'b'*64,'corpus_sha256':'c'*64,
        'science_config':{'source_commit':p['source_commit']}}
    wires=[]
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE metadata (binding TEXT)');db.execute('INSERT INTO metadata VALUES (?)',(json.dumps(binding),))
        db.execute('CREATE TABLE replies (identity TEXT,payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        for i,usage in enumerate(usages):
            body=json.dumps({'model':'SCRIPTED','usage':usage});sha=hashlib.sha256(body.encode()).hexdigest()
            db.execute('INSERT INTO replies VALUES (?,?,?,?,?)',(str(i),'payload-'+str(i),'response',body,sha))
            wires.append({'payload_sha256':'payload-'+str(i)})
        db.commit()
    wires += [{'payload_sha256':'unknown-'+str(i)} for i in range(unmatched)]
    if wires:(path.parent.parent/'wire-requests.jsonl').write_text('\n'.join(json.dumps(w) for w in wires)+'\n')
    return path


def audit(root,p):
    return hashed({'schema':p['schema']+'.audit','source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],
        'source_proofs':{'status':'verified-exact-source-closure','files':{'SCRIPTED':'not-a-real-source-proof'}},
        'writer':{'ended':{'status':'exited','exit_code':0}},'new_model_calls':0,'new_code_executions':0,
        'input_inventory':costs._inventory(root)})


def test_missing_invalid_and_reported_zero_stay_distinct_and_totals_are_not_repaired():
    values=[costs.usage_values(v) for v in [
        {'usage':{'prompt_tokens':0,'completion_tokens':2,'total_tokens':99,
            'prompt_tokens_details':{'cached_tokens':0}}},
        {},{'usage':None},{'usage':{'prompt_tokens':True,'completion_tokens':-1,'total_tokens':'1'}},
        {'usage':[]},{'usage':{'prompt_tokens':3,'completion_tokens':4,'total_tokens':7}}]]
    r=costs.summarize(values)
    assert r['prompt_tokens']=={'recorded_sum':3,'known_responses':2,'missing_responses':3,
        'invalid_responses':1,'all_completed_responses_known':False}
    assert r['cached_prompt_tokens']['known_responses']==1 and r['cached_prompt_tokens']['recorded_sum']==0
    assert r['total_tokens']['recorded_sum']==106  # Preserve reported99, not repaired2.
    assert costs.summarize([costs.usage_values({})])['prompt_tokens']['recorded_sum'] is None
    assert costs.summarize([])['prompt_tokens']['recorded_sum']==0  # Empty observed set, not unknown response.


def test_closed_s1_partial_wire_and_duplicate_content_are_counted_as_physical_journals(tmp_path):
    root,p=make(tmp_path);usage={'prompt_tokens':3,'completion_tokens':4,'total_tokens':7}
    for name in ['one','two']:
        cache(root,p,f'controls/{name}/worlds/SCRIPTED/replies/responses.sqlite',[usage,None],unmatched=1)
    a=audit(root,p);before=deepcopy(a);r=costs.analyze(root,p,a,expected_source=p['source_commit'])
    assert a==before and costs._inventory(root)==a['input_inventory']
    assert r['completed_responses']==4 and r['physical_response_journals']==2
    assert r['wire_inputs']==6 and r['wire_inputs_without_committed_reply']==2
    assert r['usage']['prompt_tokens']['recorded_sum']==6 and r['usage']['prompt_tokens']['missing_responses']==2
    assert r['usage']['cached_prompt_tokens']['recorded_sum'] is None
    assert not r['full_experiment_compute_cost_claimed'] and not r['unknown_usage_imputed']
    assert r==costs.analyze(root,p,a,expected_source=p['source_commit'])


def test_empty_cache_and_wire_only_world_are_not_hidden_or_fabricated_responses(tmp_path):
    root,p=make(tmp_path)
    cache(root,p,'controls/empty/worlds/SCRIPTED/replies/responses.sqlite',[])
    wire=root/'controls/no-cache/worlds/SCRIPTED/wire-requests.jsonl';wire.parent.mkdir(parents=True)
    wire.write_text('{"payload_sha256":"unknown"}\n')
    r=costs.analyze(root,p,audit(root,p),expected_source=p['source_commit'])
    assert r['completed_responses']==0 and r['wire_inputs']==1
    assert r['wire_inputs_without_committed_reply']==1
    assert r['wire_only_worlds'][0]['response_usage']=='unknown-no-response-journal'


@pytest.mark.parametrize('relative',[
    'search/run-00/arms/throughput--parameters/worlds/SCRIPTED/replies/responses.sqlite',
    'references/legacy/worlds/SCRIPTED/replies/responses.sqlite',
    'evaluation/SCRIPTED-job/worlds/SCRIPTED/replies/responses.sqlite'])
def test_v2_stages_include_search_and_selected_shared_physical_jobs_once(tmp_path,relative):
    root,p=make(tmp_path,costs.STUDY);cache(root,p,relative,[{'prompt_tokens':8,'completion_tokens':2,'total_tokens':10}])
    r=costs.analyze(root,p,audit(root,p),expected_source=p['source_commit'])
    assert r['physical_response_journals']==1 and r['completed_responses']==1
    assert r['usage']['prompt_tokens']['recorded_sum']==8


def test_unknown_layout_or_changed_inventory_or_reply_cannot_be_cost_evidence(tmp_path):
    root,p=make(tmp_path);path=cache(root,p,'controls/one/worlds/SCRIPTED/replies/responses.sqlite',[None]);a=audit(root,p)
    with sqlite3.connect(path) as db:db.execute("UPDATE replies SET data='changed'");db.commit()
    with pytest.raises(ValueError,match='inventory'):costs.analyze(root,p,a,expected_source=p['source_commit'])
    a=audit(root,p)  # Even an incorrectly rehashed synthetic inventory cannot bypass reply hashes.
    with pytest.raises(ValueError,match='body/outcome'):costs.analyze(root,p,a,expected_source=p['source_commit'])
    with pytest.raises(ValueError,match='layout'):costs.group('outside/replies/responses.sqlite',costs.STUDY)


def test_live_writer_wrong_source_and_cli_overwrite_are_refused(tmp_path):
    root,p=make(tmp_path);cache(root,p,'controls/empty/worlds/SCRIPTED/replies/responses.sqlite',[]);a=audit(root,p)
    live=deepcopy(a);live['writer']['ended']['status']='running';hashed(live)
    with pytest.raises(ValueError,match='closed'):costs.analyze(root,p,live,expected_source=p['source_commit'])
    with pytest.raises(ValueError,match='closed'):costs.analyze(root,p,a,expected_source='d'*40)
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(p));proof=tmp_path/'audit.json';proof.write_text(json.dumps(a))
    out=tmp_path/'result.json';args=['--run',str(root),'--plan',str(plan),'--audit',str(proof),
        '--expected-source',p['source_commit'],'--output',str(out)]
    assert costs.main(args)==0;original=out.read_bytes()
    with pytest.raises(SystemExit):costs.main(args)
    assert out.read_bytes()==original
    with pytest.raises(SystemExit):costs.main(args[:-1]+[str(root/'new.json')])
