"""Pure prospective pipeline QA. No live models or scientific observations."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from scripts import run_pre_scale_search_v1 as driver
from tests.optimization.test_native_numeric_designer import PROVIDER,BACKEND
from utopia.system.design_patch import digest


def plan():
    scientist={**deepcopy(PROVIDER),'model':'qwen3:8b',
        'model_digest':'500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41'}
    p=driver.build_plan(source='a'*40,scientist=scientist,designer=PROVIDER,backend=BACKEND,
        data_cache='/SCRIPTED/no-data',seed_usage=[{'valid':True,'errors':[],
            'prior_matching_runs':[],'content_sha256':'b'*64}])
    p['content_sha256']=digest(p)
    return p


def references(root,p):
    for name,system in p['reference_systems'].items():
        metrics={k:{'status':'measured','value':0} for k in ('native.accepted_decisions',
            'native.accepted_peer_score_sum','native.review_records')}
        o={'status':'complete','candidate':system,'metadata':{'technical_failures':[],
            'runs':[{'run_id':'SCRIPTED'}],'measurements':[{'run_id':'SCRIPTED','metrics':metrics}]}}
        path=root/'references'/name/'observation.json';path.parent.mkdir(parents=True)
        path.write_text(json.dumps(o))


def test_prospective_plan_has_finite_objectives_world_laws_and_no_merit_gate():
    p=plan()
    assert p['objectives']==['throughput','efficiency'] and len(p['schedule'])==16
    assert set(p['losses'])=={'throughput','efficiency','selective'}
    assert len(p['reference_systems'])==6 and len(p['evaluation']['reference_labels'])==4
    assert p['budget']['total_native_worlds_upper_bound']==58
    assert all(b['design_space']['world_law_scope']=='fixed-native-production-v1'
               for b in p['campaign_bindings']['run-00'].values())
    assert [(s['generation'],s['arm']) for s in p['schedule']][:8]!=[(s['generation'],s['arm']) for s in p['schedule']][8:]
    assert not p['claims']['method_superiority'] and not p['claims']['scientific_truth']


def test_selection_keeps_all_16_nulls_initial_ties_and_physical_sharing(tmp_path):
    p=plan();references(tmp_path,p)
    with pytest.raises(ValueError,match='every declared'):
        driver.selection_payload(tmp_path,p,frozen_utc='SCRIPTED',campaign_loader=driver.campaign)
    def forbidden(*a):pytest.fail('invalid definition cannot dispatch a native world')
    for arm in p['assignments']:
        c=driver.campaign(tmp_path,p,'run-00',arm)
        for _ in range(2):
            c.advance(simulation_factory=forbidden,
                generators={p['assignments'][arm]['strategy']:lambda request:None},count=1)
    selection=driver.selection_payload(tmp_path,p,frozen_utc='SCRIPTED',campaign_loader=driver.campaign)
    assert len(selection['all_rows'])==22
    assert sum(r['status']=='generation-failure' for r in selection['all_rows'])==16
    assert all(v['selected_row_id']=='reference:open-seed' for v in selection['selected'].values())
    assert len(selection['pooled']['throughput']['all_tied_row_ids'])==6
    jobs=driver.evaluation_jobs(p,selection)
    assert len(jobs)==12 # four exact policies * three unused seeds
    assert all(j['seed'] in driver.EVALUATION_SEEDS for j in jobs)
    assert any(len(j['labels'])==9 for j in jobs) # eight initial selections + reference
    changed=deepcopy(selection);changed['selected']['throughput:parameters']['loss']=-999
    with pytest.raises(ValueError,match='changed'):driver.evaluation_jobs(p,changed)


def test_evaluation_requires_frozen_selection_and_writes_plan_before_any_world(tmp_path,monkeypatch):
    p=plan();p['_output']=str(tmp_path)
    with pytest.raises(FileNotFoundError):driver.evaluate(tmp_path,p)
    selection={'plan_sha256':p['content_sha256'],'selected':{}}
    driver.save(tmp_path/'selection.json',selection)
    seen=[]
    def observe(*args):
        assert (tmp_path/'selection.json').exists() and (tmp_path/'evaluation-plan.json').exists()
        seen.append(args)
    monkeypatch.setattr(driver,'observe',observe)
    monkeypatch.setattr(driver,'progress',lambda *a,**kw:None)
    driver.evaluate(tmp_path,p)
    assert len(seen)==12 and (tmp_path/'complete.json').exists()
    with pytest.raises(ValueError,match='immutable'):driver.evaluate(tmp_path,p)


def test_pooled_exact_ties_follow_dispatch_schedule_not_sorted_json_or_arm_group_order(tmp_path):
    p=plan();references(tmp_path,p)
    def loader(root,p,run,arm):
        records=[]
        for g in range(2):
            if (arm,g) in [('efficiency:parameters',0),('throughput:parameters',1)]:
                metrics={k:{'status':'measured','value':v} for k,v in [
                    ('native.accepted_decisions',5),('native.accepted_peer_score_sum',10),('native.review_records',3)]}
                o={'candidate':p['reference_systems']['open-seed'],'status':'complete','metadata':{
                    'technical_failures':[],'runs':[{'run_id':'SCRIPTED'}],
                    'measurements':[{'run_id':'SCRIPTED','metrics':metrics}]}}
            else:o=None
            records.append({'generation_error':None if o else {'SCRIPTED':True},'observations':[o] if o else []})
        return SimpleNamespace(state={'pending':None,'records':records})
    first=driver.selection_payload(tmp_path,p,frozen_utc='SCRIPTED',campaign_loader=loader)
    serialized=json.loads(json.dumps(p,sort_keys=True))
    second=driver.selection_payload(tmp_path,serialized,frozen_utc='SCRIPTED',campaign_loader=loader)
    assert first==second
    assert first['pooled']['throughput']['all_tied_row_ids']==[
        'run-00:efficiency:parameters:g0','run-00:throughput:parameters:g1']
    assert first['pooled']['throughput']['selected_row_id']=='run-00:efficiency:parameters:g0'


def test_technical_unknowns_are_not_fresh_world_retries(tmp_path):
    p=plan();p['_output']=str(tmp_path)
    driver.save(tmp_path/'started.json',{'SCRIPTED':'unknown previous dispatch'})
    with pytest.raises(ValueError,match='already consumed'):
        driver.observe(tmp_path,p,'x',p['reference_systems']['open-seed'],41001,'SCRIPTED')


def test_environment_is_checked_before_expensive_author_or_world_dispatch(monkeypatch):
    for k,v in driver.ENVIRONMENT.items():monkeypatch.setenv(k,v)
    driver.require_environment()
    monkeypatch.delenv('HF_HUB_OFFLINE')
    with pytest.raises(ValueError,match='before any dispatch'):driver.require_environment()
