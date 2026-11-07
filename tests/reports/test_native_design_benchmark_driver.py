"""Pure pipeline ordering/selection QA, not scientific data."""
import json
from copy import deepcopy
from types import SimpleNamespace
import pytest

from scripts import run_native_design_benchmark as driver
from tests.reports.test_native_design_benchmark_plan import plan
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest


def test_selection_requires_all_slots_and_keeps_nulls_ties_and_raw_definitions(tmp_path):
    p=plan()
    for name,system in p['reference_systems'].items():
        metrics={'native.accepted_decisions':{'status':'measured','value':0},
            'native.accepted_peer_score_sum':{'status':'measured','value':0},
            'native.review_records':{'status':'measured','value':0}}
        o={'status':'complete','candidate':system,'metadata':{'measurements':[{'run_id':'SCRIPTED','metrics':metrics}]}}
        path=tmp_path/'references'/name/'observation.json';path.parent.mkdir(parents=True);path.write_text(json.dumps(o))
    # Every real controller owns an explicit failed definition, not a host fallback.
    calls=[]
    def author(request):calls.append(request);return {'generation_failure':{'kind':'SCRIPTED author failure'}}
    def forbidden_world(*a):pytest.fail('generation failure must not execute a world')
    with pytest.raises(ValueError,match='every declared search slot'):driver.freeze_selection(tmp_path,p)
    for run,bindings in p['campaign_bindings'].items():
        for arm in bindings:
            c=driver.campaign(tmp_path,p,run,arm)
            for _ in range(4):c.advance(simulation_factory=forbidden_world,
                generators={p['assignments'][arm]['strategy']:author},count=1)
    s=driver.freeze_selection(tmp_path,p)
    assert len(calls)==120 and len(s['all_rows'])==129
    assert all(v['selected_row_id']=='reference:open-seed' for v in s['selected'].values())
    assert len(s['pooled']['throughput']['all_tied_row_ids'])==9
    assert all(r['status']=='generation-failure' and set(r['cross_scores'].values())=={None}
        for r in s['all_rows'] if r['arm'] is not None)
    jobs=driver.evaluation_jobs(p,s)
    assert len(jobs)<=114
    assert all(driver.spec.policy_identity(j['system'])==j['policy_sha256'] for j in jobs)
    assert any('selected:throughput:parameters' in j['labels'] and 'reference:open-seed' in j['labels'] for j in jobs)
    with pytest.raises(ValueError,match='immutable'):driver.freeze_selection(tmp_path,p)
    changed=deepcopy(s);changed['selected']['throughput:parameters']['loss']=-999.
    with pytest.raises(ValueError,match='exact frozen selection'):driver.evaluation_jobs(p,changed)


def test_pipeline_freezes_selection_and_evaluation_plan_before_any_evaluation(tmp_path,monkeypatch):
    p=plan();events=[]
    monkeypatch.setattr(driver,'prepare',lambda args:p)
    monkeypatch.setattr(driver,'evaluate',lambda root,plan,**kw:events.append(kw['role']))
    monkeypatch.setattr(driver,'progress',lambda *a,**kw:None)
    monkeypatch.setattr(driver,'calibration',lambda *a:events.append('calibrate') or 'SCRIPTED certificate')
    monkeypatch.setattr(driver,'search_run',lambda *a,**kw:events.append('search'))
    def freeze(*a):events.append('freeze');return {'content_sha256':'SCRIPTED'}
    monkeypatch.setattr(driver,'freeze_selection',freeze)
    monkeypatch.setattr(driver,'evaluation_jobs',lambda *a:[{'job_id':'evaluation-0000','system':p['initial_system'],
        'seed':31001,'years':2}])
    args=SimpleNamespace(output=tmp_path,data_cache=tmp_path/'cache',action='all')
    assert driver.execute(args)==0
    assert events==['developer-reference']*9+['calibrate','search']*3+['freeze','selection-fixed-evaluation']
    assert (tmp_path/'evaluation-plan.json').exists()


def test_writer_preserves_abort_and_does_not_redispatch(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,'pinned_revision',lambda root:'a'*40)
    calls=[]
    def stop(args):calls.append(args.action);raise RuntimeError('SCRIPTED bounded abort')
    monkeypatch.setattr(driver,'execute',stop)
    argv=['all','--execute-authorized','--output',str(tmp_path),'--data-cache',str(tmp_path/'cache'),
        '--designer-provider-config',str(tmp_path/'operator')]
    with pytest.raises(RuntimeError):driver.main(argv)
    end=json.loads((tmp_path/'writer.ended.json').read_text());assert end['status']=='aborted'
    with pytest.raises(ValueError,match='immutable'):driver.main(argv)
    assert calls==['all']
