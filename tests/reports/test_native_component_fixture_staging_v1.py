"""Scripted source/input/receipt guards, not actual native observations."""
import json
from types import SimpleNamespace

import pytest

from scripts.reports.stage_native_component_fixtures_v1 import (stage,REFERENCES,NODES,
    LIQUIDITY_SCOPE,LIQUIDITY_REFERENCES,LIQUIDITY_NODES)
from scripts.analyze_native_open_v7 import _inventory
from tests.optimization.test_native_code_trace import case
from utopia.optimization.native_numeric_designer import save,checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


def inputs(tmp,monkeypatch,*,liquidity=False):
    root=tmp/'raw';root.mkdir();source='a'*40
    references=LIQUIDITY_REFERENCES if liquidity else REFERENCES
    requested=LIQUIDITY_NODES if liquidity else NODES
    plan={'source_commit':source}
    if liquidity:plan['jobs']=[{'identity':ref} for ref in references]
    p=save(root/'plan.json',plan);worlds=[];specs={}
    for ref in references:
        identity=ref if liquidity else 'reference-'+ref
        cell=root/('worlds-by-job' if liquidity else 'references')/ref/'worlds'/(identity+'-s61001')
        recorder,artifact,context,binding=case(cell)
        recorder.path=cell/'code-contexts.jsonl';recorder.attempts_path=cell/'code-contexts.jsonl.attempts.jsonl'
        recorder.binding={'source_commit':source,'system_fingerprint':'SCRIPTED-'+ref,'run_id':cell.name}
        mechanisms=[]
        for i,node in enumerate((*requested,'SCRIPTED intrinsic native handler')):
            a={**artifact,'label':'SCRIPTED-'+node}
            for year in range(1,5) if liquidity else [i+1]:
                recorder.execute(a,{**context,'period':year})
            if node in requested:
                mechanisms.append(SimpleNamespace(mechanism_id=node,parameters={'code_artifact':a}))
        rows=[json.loads(line) for line in recorder.path.read_text().splitlines()]
        physical=[{'index':i,'bundle_sha256':r['bundle_sha256'],'year':r['context']['period'],
            'attribution':'unique-event-match','matching_event_ids':['SCRIPTED-'+str(i)]} for i,r in enumerate(rows)]
        specs[ref]=SimpleNamespace(mechanisms=mechanisms,fingerprint='SCRIPTED-'+ref)
        worlds.append({'identity':identity,'role':'developer-liquidity-control' if liquidity else 'developer-reference','status':'complete','seed':61001,
            'system':{'SCRIPTED':ref},'physical_proof':{'code_proof':{
                'one_to_one_physical_execution_proven':True,'code_contexts_sha256':file_sha256(recorder.path),
                'physical_records':physical,'recorded_executions':len(rows)}}})
    a={'schema':'scienceutopia.native-liquidity-support-audit.v1' if liquidity else 'scienceutopia.native-institution-loop-stopped-audit.v1','source_commit':source,
        'plan_sha256':p['content_sha256'],'raw_inventory_sha256':digest(_inventory(root)),
        'closure':{'terminal':{'status':'closed','complete_worlds':4} if liquidity else {'status':'stopped'}},
        'source_proof':{'status':'verified-exact-source-closure'},'worlds':worlds}
    audit=tmp/'audit.json';save(audit,a)
    monkeypatch.setattr('utopia.optimization.native_jobs.pinned_revision',lambda path:source)
    monkeypatch.setattr('utopia.system.SystemSpec.from_dict',lambda d:specs[d['SCRIPTED']])
    return root,audit


def test_staging_preserves_each_literal_bundle_and_its_unique_native_attribution(tmp_path,monkeypatch):
    root,audit=inputs(tmp_path,monkeypatch);out=tmp_path/'bank.json';stage(root,audit,out)
    bank=checked(json.loads(out.read_text()))
    assert bank['references']==list(REFERENCES) and bank['nodes']==list(NODES)
    assert len(bank['records'])==len(bank['origins'])==6
    assert bank['new_model_calls']==bank['new_code_executions']==0
    assert all(r['seed']==61001 for r in bank['origins'])
    assert {r['bundle_sha256'] for r in bank['records']}=={r['bundle_sha256'] for r in bank['origins']}


def test_new_resource_bank_retains_four_real_labels_and_explicit_reference_scope(tmp_path,monkeypatch):
    root,audit=inputs(tmp_path,monkeypatch,liquidity=True);out=tmp_path/'bank.json'
    stage(root,audit,out,scope=LIQUIDITY_SCOPE);bank=checked(json.loads(out.read_text()))
    assert len(bank['records'])==len(bank['origins'])==48
    assert bank['references']==list(LIQUIDITY_REFERENCES) and bank['nodes']==list(LIQUIDITY_NODES)
    assert bank['post_edit_reference']=='resource-30-connected'
    assert bank['post_edit_probe_scope']=='declared-sixtyfour-v2'
    assert 'open-seed' not in {o['reference'] for o in bank['origins']}
    assert bank['new_model_calls']==bank['new_code_executions']==0


@pytest.mark.parametrize('liquidity',[False,True])
def test_staging_rejects_unattributed_code_records_instead_of_guessing_a_node(tmp_path,monkeypatch,liquidity):
    root,audit=inputs(tmp_path,monkeypatch,liquidity=liquidity)
    a=checked(json.loads(audit.read_text()));a['worlds'][0]['physical_proof']['code_proof']['physical_records'][0]['matching_event_ids']=[]
    audit.unlink();save(audit,{k:v for k,v in a.items() if k!='content_sha256'})
    options={'scope':LIQUIDITY_SCOPE} if liquidity else {}
    with pytest.raises(ValueError,match='uniquely attributed'):stage(root,audit,tmp_path/'no.json',**options)
    assert not (tmp_path/'no.json').exists()


def test_staging_rejects_any_raw_inventory_change_before_projection(tmp_path,monkeypatch):
    root,audit=inputs(tmp_path,monkeypatch);(root/'unaccounted.json').write_text('{}')
    with pytest.raises(ValueError,match='exact audited historical'):stage(root,audit,tmp_path/'no.json')
