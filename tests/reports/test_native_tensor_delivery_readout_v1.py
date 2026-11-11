"""Explicit pointer attribution, never a positional or source-hash node guess."""
from scripts.reports.native_tensor_delivery_readout_v1 import probe_owners


def step(tests):return {'transition':{'result':{'component_feedback':{'tests':tests}}}}
def owner_row(node,pointers):return {'node_id':node,'results':[{'exact_step_probe_pointer':p} for p in pointers]}


def test_explicit_reordered_nonconsecutive_ownership_and_ambiguity_are_retained():
    a=step([owner_row('second',['/component_probe_records/3']),owner_row('first',['/component_probe_records/0']),
        owner_row('other',['/component_probe_records/3'])])
    assert probe_owners(a)=={0:['first'],3:['other','second']}


def test_missing_owner_or_invalid_pointer_does_not_get_inferred_from_source():
    assert probe_owners(step([owner_row('first',['/component_probe_records/x','/component_probe_records/1/extra'])]))=={}
    assert probe_owners({})=={}
    assert probe_owners({'transition':None})=={}
    assert probe_owners({'transition':{'result':None}})=={}


def test_two_actual_export_boundaries_accept_null_finish_results_without_rewriting_raw(tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    from scripts.reports import native_tensor_delivery_readout_v1 as module
    from tests.optimization.test_native_tensor_delivery_diagnostics_v1 import document,node,result
    from utopia.system.design_patch import digest
    from scripts.analyze_native_open_v7 import _inventory
    raw=tmp_path/'SCRIPTED-raw';frozen=tmp_path/'SCRIPTED-scientific';out=tmp_path/'out'
    request={'generation':0,'SCRIPTED':'not an original scientific request'};identity=digest(request)
    candidate=document();artifact=node(candidate,'native-feature-extractor')['parameters']['code_artifact']
    definition={'SCRIPTED':'mocked original-source cold proof, not native evidence'}
    record={'request':request,'request_sha256':identity,'definition':definition,'generation_error':None,
        'draws':[{'suggestion':{'candidate':candidate}}]}
    module.save(raw/'plan.json',{'schema':'scienceutopia.native-objective-instrument-loop.v1.plan',
        'source_commit':'a'*40,'objectives':['content-utility']})
    module.save(raw/'search/content-utility/campaign/native-adaptive-state.json',{'records':[record]})
    cell=raw/'search/content-utility/authoring'/('generation-'+identity);inner=cell/'authoring'/('generation-'+identity)
    module.save(cell/'intent.json',{'request':request,'source_commit':'a'*40})
    row={'intent':{'artifact':artifact,'fixture_id':'SCRIPTED-fixture'},'terminal':{'status':'returned','result':result([[4.,3.,1.]])}}
    module.save(inner/'step-00.completed.json',{'step':0,'transition':{'result':{'component_feedback':{'tests':[
        owner_row('native-feature-extractor',['/component_probe_records/0'])]}}},'component_probe_records':[row]})
    module.save(inner/'step-01.completed.json',{'step':1,'transition':{'result':None},'component_probe_records':[]})
    monkeypatch.setattr(module,'git_binding',lambda p:'a'*40 if p==frozen else 'b'*40)
    monkeypatch.setattr(module.subprocess,'check_output',lambda *a,**kw:json.dumps({'definition_sha256':digest(definition)}))
    before=_inventory(raw)
    for name in ('one','two'):
        module.export(SimpleNamespace(run=raw,frozen_source=frozen,output=out/name,
            objective='content-utility',generation=0,producer='native-feature-extractor'))
    assert before==_inventory(raw)
    assert {p.name:p.read_bytes() for p in (out/'one').iterdir()}=={p.name:p.read_bytes() for p in (out/'two').iterdir()}
    report=module.checked(json.loads((out/'one/report.json').read_text()))
    assert report['probes'][0]['diagnostic']['rows'][0]['status']=='incompatible-recorded-input'
    assert not report['presented_to_original_designer'] and not report['is_original_native_world_audit']


def test_retained_actual_readout_keeps_all_probes_but_never_reuses_a_different_artifact():
    import json
    from pathlib import Path
    from utopia.optimization.native_numeric_designer import checked
    from utopia.utils.data_utils import file_sha256
    root=Path(__file__).resolve().parents[2]/'research/data/native-tensor-delivery-diagnostic-v1'
    report=checked(json.loads((root/'report.json').read_text()));manifest=checked(json.loads((root/'manifest.json').read_text()))
    assert file_sha256(root/'report.json')==manifest['report_file_sha256']=='7b45c90fef9a6dcfa5fbd53d728ef2f83794d66acb1a7a355e0e2df28fbafe5e'
    assert report['content_sha256']=='607bcc371f76f58aafbf3fd8b0ffd7c8ea69d3133182aafa39cb81c40b655f02'
    assert len(report['probes'])==report['original_probe_calls']==8 and report['final_artifact_probes']==4
    final=[r for r in report['probes'] if r['final_producer_artifact_match']]
    assert all(r['unambiguous_producer_match'] and r['actual_probe_status']=='returned' for r in final)
    values=[v for r in final for v in r['diagnostic']['rows']]
    assert [v['observed_shape'] for v in values]==[[0,2],[2,3],[3,3],[2,3]]
    assert sum(v['status']=='incompatible-recorded-input' for v in values)==3
    assert all(r['diagnostic'] is None for r in report['probes'] if not r['final_producer_artifact_match'])
    assert not any(report[k] for k in ('presented_to_original_designer','original_feedback_or_verdicts_rewritten',
        'is_original_native_world_audit','loss_changed','publication_ready'))
    assert report['new_model_calls']==report['new_source_executions']==report['new_tensor_body_executions']==0
