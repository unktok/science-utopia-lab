"""Scripted source/input/receipt guards, not actual native observations."""
import json
from types import SimpleNamespace

import pytest

from scripts.reports.stage_native_component_fixtures_v1 import (stage,REFERENCES,NODES,
    LIQUIDITY_SCOPE,LIQUIDITY_REFERENCES,LIQUIDITY_NODES,
    WORKFLOW_SCOPE,WORKFLOW_REFERENCES,WORKFLOW_NODES)
from scripts.analyze_native_open_v7 import _inventory
from tests.optimization.test_native_code_trace import case
from utopia.optimization.native_numeric_designer import save,checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


def inputs(tmp,monkeypatch,*,liquidity=False,workflow=False,years=(1,2,3,4)):
    root=tmp/'raw';root.mkdir();source='a'*40
    references=WORKFLOW_REFERENCES if workflow else LIQUIDITY_REFERENCES if liquidity else REFERENCES
    requested=WORKFLOW_NODES if workflow else LIQUIDITY_NODES if liquidity else NODES
    plan={'source_commit':source}
    if liquidity:plan['jobs']=[{'identity':ref} for ref in references]
    if workflow:
        from scripts.run_native_workflow_objective_loop_v1 import SCHEMA,OPEN_PROTOCOL,OPEN_SCOPE,OPEN_IR_MODE
        plan.update(schema=SCHEMA+'.plan',designer_mode=OPEN_IR_MODE,protocol=OPEN_PROTOCOL,
            authoring_scope=OPEN_SCOPE,optimizer_reference_labels=list(WORKFLOW_REFERENCES))
    p=save(root/'plan.json',plan);worlds=[];specs={}
    for ref in references:
        identity=('workflow-reference-'+ref.lower() if workflow else ref if liquidity else 'reference-'+ref)
        cell=root/('worlds-by-job' if liquidity else 'references')/ref/'worlds'/(identity+'-s61001')
        recorder,artifact,context,binding=case(cell)
        recorder.path=cell/'code-contexts.jsonl';recorder.attempts_path=cell/'code-contexts.jsonl.attempts.jsonl'
        recorder.binding={'source_commit':source,'system_fingerprint':'SCRIPTED-'+ref,'run_id':cell.name}
        mechanisms=[]
        for i,node in enumerate((*requested,'SCRIPTED intrinsic native handler')):
            a={**artifact,'label':'SCRIPTED-'+node}
            for year in years if liquidity or workflow else [i+1]:
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
    a={'schema':('scienceutopia.native-workflow-objective-loop-audit.v1' if workflow else
        'scienceutopia.native-liquidity-support-audit.v1' if liquidity else 'scienceutopia.native-institution-loop-stopped-audit.v1'),'source_commit':source,
        'plan_sha256':p['content_sha256'],'raw_inventory_sha256':digest(_inventory(root)),
        'closure':{'terminal':({'status':'closed'} if workflow else
            {'status':'closed','complete_worlds':4} if liquidity else {'status':'stopped'})},
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


def test_open_workflow_bank_selects_only_twenty_original_r7_inputs(tmp_path,monkeypatch):
    root,audit=inputs(tmp_path,monkeypatch,workflow=True);out=tmp_path/'bank.json'
    stage(root,audit,out,scope=WORKFLOW_SCOPE);bank=checked(json.loads(out.read_text()))
    assert bank['references']==['R7-original'] and bank['nodes']==list(WORKFLOW_NODES)
    assert len(bank['records'])==len(bank['origins'])==20
    assert bank['post_edit_reference']=='R7-original'
    assert bank['post_edit_probe_scope']=='declared-sixtyfour-v2'
    for node in WORKFLOW_NODES:
        assert sorted(o['year'] for o in bank['origins'] if o['node_id']==node)==[1,2,3,4]
    assert bank['new_model_calls']==bank['new_code_executions']==0


def test_open_workflow_requires_four_real_years_without_filling_missing_inputs(tmp_path,monkeypatch):
    root,audit=inputs(tmp_path,monkeypatch,workflow=True,years=(1,2,3))
    with pytest.raises(ValueError,match='four exact yearly developer contexts'):
        stage(root,audit,tmp_path/'no.json',scope=WORKFLOW_SCOPE)
    assert not (tmp_path/'no.json').exists()


def test_open_workflow_does_not_import_other_comparison_worlds_into_bank(tmp_path,monkeypatch):
    root,audit=inputs(tmp_path,monkeypatch,workflow=True)
    a=json.loads(audit.read_text());a.pop('content_sha256')
    a['worlds'].append({'identity':'workflow-reference-post-funding-cost','role':'developer-reference',
        'status':'complete','system':{'SCRIPTED forbidden comparison':'must not be read'}})
    audit.unlink();save(audit,a)
    stage(root,audit,tmp_path/'bank.json',scope=WORKFLOW_SCOPE)
    bank=checked(json.loads((tmp_path/'bank.json').read_text()))
    assert bank['references']==['R7-original'] and len(bank['records'])==20
    assert all(o['reference']=='R7-original' for o in bank['origins'])


@pytest.mark.parametrize('field,value',[
    ('optimizer_reference_labels',['R7-original','post-funding-cost']),
    ('authoring_scope','SCRIPTED-wrong-scope'),('designer_mode','SCRIPTED-wrong-mode'),
    ('schema','SCRIPTED-wrong-plan-schema'),('protocol','SCRIPTED-wrong-protocol')])
def test_open_workflow_scope_cannot_expose_comparison_control_or_other_study(tmp_path,monkeypatch,field,value):
    root,audit=inputs(tmp_path,monkeypatch,workflow=True)
    plan=json.loads((root/'plan.json').read_text());plan.pop('content_sha256');plan[field]=value
    (root/'plan.json').unlink()  # Deliberately mutate this SCRIPTED temporary fixture only.
    p=save(root/'plan.json',plan)
    a=json.loads(audit.read_text());a.pop('content_sha256')
    a.update(plan_sha256=p['content_sha256'],raw_inventory_sha256=digest(_inventory(root)))
    audit.unlink();save(audit,a)
    with pytest.raises(ValueError,match='explicit open'):
        stage(root,audit,tmp_path/'no.json',scope=WORKFLOW_SCOPE)
    assert not (tmp_path/'no.json').exists()


@pytest.mark.parametrize('scope',[None,LIQUIDITY_SCOPE,WORKFLOW_SCOPE])
def test_staging_rejects_unattributed_code_records_instead_of_guessing_a_node(tmp_path,monkeypatch,scope):
    root,audit=inputs(tmp_path,monkeypatch,liquidity=scope==LIQUIDITY_SCOPE,workflow=scope==WORKFLOW_SCOPE)
    a=checked(json.loads(audit.read_text()));a['worlds'][0]['physical_proof']['code_proof']['physical_records'][0]['matching_event_ids']=[]
    audit.unlink();save(audit,{k:v for k,v in a.items() if k!='content_sha256'})
    options={'scope':scope} if scope else {}
    with pytest.raises(ValueError,match='uniquely attributed'):stage(root,audit,tmp_path/'no.json',**options)
    assert not (tmp_path/'no.json').exists()


def test_staging_rejects_any_raw_inventory_change_before_projection(tmp_path,monkeypatch):
    root,audit=inputs(tmp_path,monkeypatch);(root/'unaccounted.json').write_text('{}')
    with pytest.raises(ValueError,match='exact audited historical'):stage(root,audit,tmp_path/'no.json')
