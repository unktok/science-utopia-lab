"""JSON-only12-path joins: no scientist, designer, Docker or actual cold replay."""
import json
from types import SimpleNamespace

import pytest

from scripts import run_native_longitudinal_comparison_v1 as driver
from scripts.reports import native_workflow_construction_trace_v1 as module
from tests.reports.test_native_longitudinal_reports_v1 import development_fixture
from tests.reports.test_native_workflow_construction_trace_v1 import seal
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone, digest


def evidence(tmp_path,monkeypatch):
    p,a,records=development_fixture(tmp_path,monkeypatch)
    p['designer_mode']=module.MODE;seal(p)
    a['plan_sha256']=p['content_sha256'];a['selection']['plan_sha256']=p['content_sha256']
    seal(a['selection']);seal(a);sessions={}
    for key,record in records.items():
        record['definition']={'SCRIPTED-distinct-history':list(key[0]),'generation':key[1]}
        response=seal({'request_sha256':record['request_sha256'],'status':'generated',
            'definition':clone(record['definition']),'component_testing':{
                'probe_attempts':0,'returned':0,'raised':0,'veto_on_finish':False,
                'new_native_worlds':0,'new_model_calls_from_tests':0}})
        sessions[key]={'request_sha256':record['request_sha256'],'definition':clone(record['definition']),
            'response':response,'steps':[]}
    return p,a,records,sessions


def test_same_objective_generation_in_two_arms_is_not_one_construction_path(tmp_path,monkeypatch):
    p,a,records,sessions=evidence(tmp_path,monkeypatch)
    report=module.summarize(p,a,records,sessions)
    assert report['schema']=='scienceutopia.native-longitudinal-construction-trace.v1'
    assert len(report['slots'])==12 and len({(r['arm'],r['objective'],r['generation']) for r in report['slots']})==12
    assert report['selection']==a['selection']
    assert not report['interpretation']['staged_method_superiority_claimed']
    assert report['construction_counts']['recorded_model_steps']==0
    sessions[('scalar','throughput'),0]=clone(sessions[('parent-trajectory','throughput'),0])
    with pytest.raises(ValueError,match='request/definition'):module.summarize(p,a,records,sessions)


def test_generation_null_keeps_its_original_arm_and_unknown_probe_summary(tmp_path,monkeypatch):
    p,a,records,sessions=evidence(tmp_path,monkeypatch);key=('parent-trajectory','content-utility'),1
    identity='parent-trajectory::content-utility-1';record=records[key]
    record.update(generation_error={'SCRIPTED':'known original null'},draws=[],observations=[],
        definition={'generation_failure':{'SCRIPTED':'original'}})
    sessions[key].update(definition=clone(record['definition']),response=None)
    a['worlds']=[w for w in a['worlds'] if w['identity']!=identity]
    selected=a['selection']['selected']['parent-trajectory::content-utility']
    selected['completed_submissions']-=1;selected['all_tied_ids'].remove(identity)
    seal(a['selection']);seal(a)
    report=module.summarize(p,a,records,sessions)
    row=next(r for r in report['slots'] if (r['arm'],r['objective'],r['generation'])==(*key[0],key[1]))
    assert row['status']=='generation-null' and row['loss'] is None
    assert row['construction_trace']['terminal_response_missing']
    assert row['construction_trace']['component_testing'] is None
    assert report['construction_counts']['sessions_missing_component_summary']==1
    assert len(report['slots'])==12


def test_public_export_reads_all_four_histories_and_is_byte_repeatable(tmp_path,monkeypatch):
    p,a,records,sessions=evidence(tmp_path,monkeypatch);raw=tmp_path/'raw';raw.mkdir()
    save(raw/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    a['closure']['terminal']=save(raw/'terminal.json',{'status':'closed','consumed_slots':12})
    for history in driver.history_keys(p):
        directory=driver.history_directory(raw,history)
        save(directory/'campaign/native-adaptive-state.json',{'pending':None,
            'records':[records[history,g] for g in range(3)]})
        for g in range(3):
            record=records[history,g];d=directory/'authoring'/('proposal-'+record['request_sha256'])
            binding=save(d/'binding.json',{'request':record['request']})
            save(d/'result.json',{'binding_sha256':binding['content_sha256'],'definition':record['definition']})
            response=sessions[history,g]['response']
            save(d/'editor-session/authoring'/('generation-'+record['request_sha256'])/'response.json',
                {k:v for k,v in response.items() if k!='content_sha256'})
    a.update(raw_inventory_sha256=digest(module._inventory(raw)),raw_files=len(module._inventory(raw)));seal(a)
    audits=[tmp_path/'audit-one.json',tmp_path/'audit-two.json']
    for audit in audits:save(audit,{k:v for k,v in a.items() if k!='content_sha256'})
    args=SimpleNamespace(run=raw,audit_one=audits[0],audit_two=audits[1],output=tmp_path/'one')
    before=module._inventory(raw);one=module.export(args);args.output=tmp_path/'two';two=module.export(args)
    assert one==two and before==module._inventory(raw)
    for name in ('report.json','manifest.json','slots.csv'):
        assert (tmp_path/'one'/name).read_bytes()==(tmp_path/'two'/name).read_bytes()
    csv=(tmp_path/'one/slots.csv').read_text().splitlines()
    assert len(csv)==13 and 'arm' in csv[0].split(',')


@pytest.mark.parametrize('kind',['scores','choices','effects','requests','construction'])
def test_continuation_routes_new_study_without_old_six_slot_labels(tmp_path,monkeypatch,kind):
    from scripts import finish_native_longitudinal_readouts_v1 as m
    seen={};monkeypatch.setattr(m,'finish',lambda args,**kw:seen.update(kw))
    m.run(SimpleNamespace(kind=kind,frozen_source=tmp_path))
    assert seen['plan_schema']==driver.SCHEMA+'.plan'
    assert seen['preceding_schema']=='scienceutopia.native-longitudinal-comparison-finish.v1'
    if kind=='choices':assert seen['report_extra_arguments'][-2:]==('--study','longitudinal-development')
    elif kind=='effects':assert seen['report_extra_arguments'][-2:]==('--scope','longitudinal-objective-development')
    else:assert seen['report_extra_arguments']==()


def test_read_only_waiter_binds_original_writer_and_auditor(monkeypatch):
    from scripts import finish_native_longitudinal_comparison_v1 as m
    seen={};monkeypatch.setattr(m,'finish',lambda args,**kw:seen.update(kw));m.run(SimpleNamespace())
    assert seen['plan_schema']==driver.SCHEMA+'.plan'
    assert seen['audit_module']=='scripts.audit_native_longitudinal_comparison_v1'
    assert seen['writer_command']=='scripts.run_native_longitudinal_comparison_v1 run'
