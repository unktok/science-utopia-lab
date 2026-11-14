"""Synthetic JSON-only search allocation; no model/native execution evidence."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from scripts.reports import native_longitudinal_search_allocation_v1 as m
from scripts.reports import native_workflow_construction_trace_v1 as construction
from scripts import run_native_longitudinal_comparison_v1 as driver
from tests.reports.test_native_longitudinal_construction_trace_v1 import evidence,seal
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def step(index=0,tool='read_file',status='applied',output=None):
    return seal({'step':index,'status':status,'model_reply':{'output':output or {
        'tool':tool,'filename':'code/world.selection.py'}},'errors':[],
        'transition':{'tool':tool,'ok':status=='applied','draft_before_sha256':'old',
            'draft_after_sha256':'new' if tool=='write_file' else 'old',
            'result':{'literal_document_changed':tool=='write_file','operation_map':[
                {'actual_owner_id':'world.selection','translated_path':'/mechanisms/6/parameters/code_artifact/source'}]
                if tool=='write_file' else []},'errors':[]}})


def projected(tmp_path,monkeypatch):
    p,a,records,sessions=evidence(tmp_path,monkeypatch)
    for session in sessions.values():session['steps']=[step(),step(1,'write_file')]
    c=seal(construction.summarize(p,a,records,sessions))
    steps={(*key[0],key[1]):v['steps'] for key,v in sessions.items()}
    return p,c,steps,a,records,sessions


@pytest.mark.parametrize('output',[None,'unparsed',[],{'filename':{'bad':'object'}},
    {'filename':['not','a','path']},{'operations':'bad'},
    {'operations':[None,[],{'path':{}},{'path':'/recorded-only'}]}])
def test_rejected_model_json_remains_untrusted_data(output):
    s=step(status='rejected');s['model_reply']['output']=output;seal(s)
    before=deepcopy(s);view=m.step_summary(s)
    assert view['untrusted_model_output_type']==type(output).__name__
    assert not view['applied_host_edit_targets'] and not view['document_changed']
    assert not view['native_effect_inferred'] and s==before
    if isinstance(output,dict) and isinstance(output.get('filename'),(dict,list)):
        assert view['untrusted_proposed_filename'] is None
        assert view['untrusted_target_field_types']['filename'] in ('dict','list')


def test_rejected_untrusted_tool_shape_does_not_crash_or_become_an_executed_tool():
    s=step(status='rejected');s['transition']['tool']=['malformed'];seal(s)
    v=m.step_summary(s)
    assert v['tool'] is None and v['tool_field_type']=='list'


def test_actual_host_target_and_proposed_target_are_not_conflated():
    s=step(tool='write_file',output={'tool':'write_file','filename':'new/imagined.json'})
    v=m.step_summary(s)
    assert v['untrusted_proposed_filename']=='new/imagined.json'
    assert v['applied_host_edit_targets'][0]['owner_id']=='world.selection'
    assert v['document_changed'] and not v['native_effect_inferred']


def test_corrupt_applied_host_metadata_is_not_silently_ignored():
    s=step(tool='write_file');s['transition']['result']['operation_map']={};seal(s)
    with pytest.raises(ValueError,match='host operation map'):m.step_summary(s)


def test_long_error_excerpt_preserves_hash_and_marks_truncation():
    s=step(status='rejected');message='SCRIPTED error '*100
    s['transition']['errors']=[{'type':'ValueError','message':message}];seal(s)
    v=m.step_summary(s)['rejection_diagnostics'][0]
    assert v['message_is_excerpt'] and len(v['message_excerpt'])==400
    assert v['full_message_value_digest']==digest(message)


def test_transport_and_action_errors_keep_separate_original_locations():
    s=step(status='rejected');s['errors']=[{'type':'TransportError','message':'SCRIPTED transport'}]
    s['transition']['errors']=[{'type':'ValueError','message':'SCRIPTED action'}];seal(s)
    v=m.step_summary(s)['rejection_diagnostics']
    assert [(e['location'],e['type']) for e in v]==[('step','TransportError'),('transition','ValueError')]


def test_four_histories_and_all_twelve_slots_remain_separate(tmp_path,monkeypatch):
    p,c,steps,*_=projected(tmp_path,monkeypatch);v=m.summarize(p,c,steps)
    assert len(v['slots'])==12 and len(v['histories'])==4
    for history in v['histories'].values():
        assert history['slots']==3 and history['recorded_complete_steps']==6
        assert history['changed_document_host_owner_operations']=={'world.selection':3}
    assert not v['loss_or_selection_changed'] and not v['causal_search_bias_or_repair_proved']
    steps.pop(next(iter(steps)))
    with pytest.raises(ValueError,match='twelve'):m.summarize(p,c,steps)


def test_missing_terminal_keeps_unknown_final_total_and_observed_prefix(tmp_path,monkeypatch):
    p,c,steps,*_=projected(tmp_path,monkeypatch);row=c['slots'][0]
    row.update(status='generation-null',loss=None)
    row['construction_trace']['terminal_response_missing']=True;seal(c)
    v=m.summarize(p,c,steps)['slots'][0]
    assert v['loss'] is None and v['recorded_complete_step_prefix']==2
    assert not v['final_call_total_known']


def test_changed_complete_journal_rejected(tmp_path,monkeypatch):
    p,c,steps,*_=projected(tmp_path,monkeypatch);key=next(iter(steps))
    steps[key][0]['status']='rejected';seal(steps[key][0])
    with pytest.raises(ValueError,match='raw complete steps differ'):m.summarize(p,c,steps)


def upstream_exports(tmp_path,monkeypatch):
    p,c,steps,a,records,sessions=projected(tmp_path,monkeypatch);raw=tmp_path/'raw';raw.mkdir()
    save(raw/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    a['closure']['terminal']=save(raw/'terminal.json',{'status':'closed','consumed_slots':12})
    for history in driver.history_keys(p):
        h=driver.history_directory(raw,history)
        save(h/'campaign/native-adaptive-state.json',{'pending':None,'records':[records[history,g] for g in range(3)]})
        for g in range(3):
            rec=records[history,g];d=h/'authoring'/('proposal-'+rec['request_sha256'])
            binding=save(d/'binding.json',{'request':rec['request']})
            save(d/'result.json',{'binding_sha256':binding['content_sha256'],'definition':rec['definition']})
            inner=d/'editor-session/authoring'/('generation-'+rec['request_sha256'])
            response=sessions[history,g]['response']
            save(inner/'response.json',{k:v for k,v in response.items() if k!='content_sha256'})
            for s in sessions[history,g]['steps']:save(inner/f'step-{s["step"]:02d}.completed.json',{k:v for k,v in s.items() if k!='content_sha256'})
    a.update(raw_inventory_sha256=digest(m._inventory(raw)),raw_files=len(m._inventory(raw)));seal(a)
    audits=[tmp_path/'audit-one.json',tmp_path/'audit-two.json']
    for path in audits:save(path,{k:v for k,v in a.items() if k!='content_sha256'})
    one=tmp_path/'construction-one';two=tmp_path/'construction-two'
    for out in (one,two):construction.export(SimpleNamespace(run=raw,audit_one=audits[0],audit_two=audits[1],output=out))
    monkeypatch.setattr(m,'pinned_revision',lambda root:'SCRIPTED-reader-source')
    return SimpleNamespace(run=raw,audit_one=audits[0],audit_two=audits[1],construction_one=one,
        construction_two=two,output=tmp_path/'allocation-one')


def test_public_export_double_bytes_and_original_raw_unchanged(tmp_path,monkeypatch):
    args=upstream_exports(tmp_path,monkeypatch);before=m._inventory(args.run)
    one=m.export(args);args.output=tmp_path/'allocation-two';two=m.export(args)
    assert one==two and before==m._inventory(args.run)
    for name in ('report.json','slots.csv','manifest.json'):
        assert (tmp_path/'allocation-one'/name).read_bytes()==(args.output/name).read_bytes()
    assert len((args.output/'slots.csv').read_text().splitlines())==13


def test_changed_upstream_files_reject_before_output(tmp_path,monkeypatch):
    args=upstream_exports(tmp_path,monkeypatch)
    (args.construction_two/'slots.csv').write_text('SCRIPTED changed\n')
    with pytest.raises(ValueError,match='outputs differ'):m.export(args)
    assert not args.output.exists()
