"""SCRIPTED score geometry, never extra native-world or optimization evidence."""
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_capacity_preference_geometry_v1 as module
from utopia.system.design_patch import clone,digest


def seal(value):
    value.pop('content_sha256',None);value['content_sha256']=digest(value);return value


def report(pairs=((-10,0),(-4,-4),(0,-10),(0,0))):
    worlds=[{'identity':'SCRIPTED-'+str(i),'seed':61001,'role':'developer-reference',
        'status':'complete','scores':dict(zip(module.OBJECTIVES,p)),
        'system_sha256':str(i)*64} for i,p in enumerate(pairs)]
    worlds.append({'identity':'SCRIPTED-failed','seed':61001,'role':'search:throughput',
        'status':'failed','scores':dict.fromkeys(module.OBJECTIVES),'system_sha256':'f'*64})
    slots=[{'objective':'throughput','generation':0,'status':'failed','physical_job':'SCRIPTED-failed'},
        {'objective':'founder-activity','generation':0,'status':'generation-failure','physical_job':None}]
    return seal({'schema':'scienceutopia.native-capacity-objective-report.v1',
        'score_order':module.OBJECTIVES,'source_commit':'a'*40,'plan_sha256':'b'*64,'audit_sha256':'c'*64,
        'physical_worlds':worlds,'slots':slots,'interpretation':{'held_out_evaluation':False,
            'new_model_calls':0,'new_code_executions':0}})


def test_exact_envelope_pareto_and_unsupported_nondominated_point():
    original=report();before=clone(original);r=module.summarize(original)
    assert original==before
    assert r['geometry']=={'open_intervals':[
        {'left':'0','right':'1/2','winning_curve_indices':[2]},
        {'left':'1/2','right':'1','winning_curve_indices':[0]}],
        'boundaries':[{'weight_T':'0','winning_curve_indices':[2]},
            {'weight_T':'1/2','winning_curve_indices':[0,2]},
            {'weight_T':'1','winning_curve_indices':[0]}]}
    assert [c['observed_pareto_nondominated'] for c in r['curves']]==[True,True,True,False]
    assert [c['minimizes_some_observed_linear_mixture'] for c in r['curves']]==[True,False,True,False]
    assert r['complete_observed_worlds']==4 and r['physical_attempts']==5
    assert r['failed_world_ids']==['SCRIPTED-failed']
    assert len(r['unavailable_own_slots'])==2
    assert not r['candidate_reselection'] and not r['family']['interior_objectives_optimized']


def test_score_ties_never_merge_program_or_physical_identities():
    r=module.summarize(report(((-10,0),(-10,0),(0,-10))))
    assert len(r['curves'])==2 and len(r['curves'][0]['physical_worlds'])==2
    assert len({w['system_sha256'] for w in r['curves'][0]['physical_worlds']})==2
    assert r['complete_observed_worlds']==3


def test_endpoint_only_ties_and_all_coincident_curves_are_retained():
    r=module.summarize(report(((-10,0),(-4,-10),(0,-10))))
    assert r['geometry']['boundaries'][0]=={'weight_T':'0','winning_curve_indices':[1,2]}
    assert not r['curves'][2]['observed_pareto_nondominated']
    assert r['curves'][2]['minimizes_some_observed_linear_mixture']  # zero weight on the other loss
    same=module.summarize(report(((-10,-15),)*3))
    assert same['geometry']['open_intervals']==[{'left':'0','right':'1','winning_curve_indices':[0]}]
    assert len(same['curves'])==1


@pytest.mark.parametrize('change',['schema','seed','duplicate','imputation','bool','positive','fraction','unavailable'])
def test_bad_inputs_do_not_create_new_losses_or_optima(change):
    r=report()
    if change=='schema':r['schema']='scienceutopia.native-objective-instrument-report.v1'
    elif change=='seed':r['physical_worlds'][0]['seed']=1234
    elif change=='duplicate':r['physical_worlds'][0]['identity']=r['physical_worlds'][1]['identity']
    elif change=='imputation':r['physical_worlds'][-1]['scores']['throughput']=0
    elif change=='bool':r['physical_worlds'][0]['scores']['throughput']=True
    elif change=='positive':r['physical_worlds'][0]['scores']['founder-activity']=1
    elif change=='fraction':r['physical_worlds'][0]['scores']['throughput']=-.5
    else:r['physical_worlds']=r['physical_worlds'][-1:]
    seal(r)
    with pytest.raises(ValueError):module.summarize(r)


def test_real_capacity_reader_output_is_consumed_without_relabeled_U(tmp_path,monkeypatch):
    from tests.reports.test_native_capacity_objective_report_v1 import evidence
    from scripts.reports.native_objective_instrument_loop_v1 import summarize
    p,a,records,traces=evidence(tmp_path,monkeypatch)
    raw=summarize(p,a,records,traces,study='capacity-v1');result=module.summarize(raw)
    assert result['complete_observed_worlds']>0
    assert all(c['P']=='-15' for c in result['curves'])
    assert result['original_report_content_sha256']==raw['content_sha256']


def test_two_actual_png_svg_csv_exports_agree_and_keep_source_report(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'pinned_revision',lambda _:'d'*40)
    path=tmp_path/'input/report.json';module.save(path,{k:v for k,v in report().items() if k!='content_sha256'})
    before=path.read_bytes();inventories=[]
    for name in ('one','two'):
        out=tmp_path/name;module.export(SimpleNamespace(report=path,output=out))
        inventories.append({p.name:module.file_sha256(p) for p in out.iterdir()})
        summary=module.checked(json.loads((out/'summary.json').read_text()))
        assert not summary['new_native_worlds'] and not summary['publication_ready']
    assert inventories[0]==inventories[1] and path.read_bytes()==before


def test_raw_adapter_uses_the_actual_sealed_source_report_api(tmp_path,monkeypatch):
    from scripts.reports import native_capacity_objective_loop_v1 as source
    monkeypatch.setattr(module,'pinned_revision',lambda _:'d'*40)
    calls=[]
    def source_export(args):
        calls.append(args)
        module.save(args.output/'report.json',{k:v for k,v in report().items() if k!='content_sha256'})
    monkeypatch.setattr(source,'export',source_export)
    args=SimpleNamespace(run=tmp_path/'raw',audit_one=tmp_path/'audit-one.json',
        audit_two=tmp_path/'audit-two.json',output=tmp_path/'out')
    module.export_from_audits(args)
    assert len(calls)==1 and calls[0].run==args.run
    assert (calls[0].audit_one,calls[0].audit_two)==(args.audit_one,args.audit_two)
    original=module.checked(json.loads((args.output/'source-report/report.json').read_text()))
    projected=module.checked(json.loads((args.output/'geometry/summary.json').read_text()))
    assert projected['original_report_content_sha256']==original['content_sha256']
    with pytest.raises(ValueError,match='fresh'):module.export_from_audits(args)


def test_one_shot_finish_uses_existing_strict_capacity_closure_contract(monkeypatch):
    from scripts import finish_native_capacity_preference_geometry_v1 as finish
    seen=[];monkeypatch.setattr(finish,'finish',lambda args,**kwargs:seen.append((args,kwargs)))
    args=SimpleNamespace(run='SCRIPTED',analysis='SCRIPTED',output='SCRIPTED')
    finish.run(args)
    assert seen==[(args,{'plan_schema':'scienceutopia.native-capacity-objective-loop.v1.plan',
        'preceding_schema':'scienceutopia.native-capacity-objective-loop-finish.v1',
        'continuation_schema':'scienceutopia.native-capacity-preference-geometry-finish.v1',
        'report_module':'scripts.reports.native_capacity_preference_geometry_v1'})]


def test_retained_launch_is_actual_wait_not_a_completed_scientific_geometry():
    root=Path(__file__).resolve().parents[2]
    r=module.checked(json.loads((root/'research/results/native-capacity-geometry-launch-verification-v1.json').read_text()))
    start=module.checked(r['started'])
    assert start['analysis_source_commit']==r['reader_source_commit']=='3fff226536a24d1313725f11594899cffeee088b'
    assert start['scientific_source_commit']==r['scientific_source_commit']=='16cfdcef2151e01365c1fc2bea3f5cc928954220'
    assert hashlib.sha256((json.dumps(start,sort_keys=True,allow_nan=False)+'\n').encode()).hexdigest()==r['started_file_sha256']
    assert start['maximum_wait_seconds']==86400 and not start['new_inference_allowed']
    assert not start['retry_failed_stages']
    assert r['final_tests']['final_exit_code_observed']==0 and r['final_tests']['passed']==45
    assert not r['actual_geometry_created'] and not r['interior_objective_optimization']
    assert not r['candidate_reselection'] and not r['new_native_worlds'] and not r['publication_ready']
