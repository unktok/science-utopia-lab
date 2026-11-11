"""Finite orchestration checks with no actual models or scientific worlds."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_code_tested_loop_v1 as module
from tests.reports.test_native_institution_loop_v1 import plan as old_plan
from tests.optimization.test_native_post_edit_feedback_v1 import fixture,finish
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.system.design_patch import clone,digest


def plan(tmp_path,monkeypatch):
    gen,model,body,calls=fixture(tmp_path/'fixture',[finish()]);operator=old_plan()
    bank=gen.edit_feedback.bank;image=bank['records'][0]['receipt']['image_id']
    operator['scientist']['image_id']=image;operator['designer']['image_id']=image
    real=module.read
    def read(path):
        if Path(path)==module.ROOT/module.BANK_MANIFEST:
            return {'bank_file_sha256':'SCRIPTED-bank-file','bank_content_sha256':bank['content_sha256']}
        return real(path)
    monkeypatch.setattr(module,'read',read)
    p=module.build_plan(operator=operator,source='c'*40,backend=operator['backend'],
        bank=bank,bank_file_hash='SCRIPTED-bank-file',
        preceding={'directory':'/SCRIPTED-prior-analysis','start_file_sha256':'b'*64,'scientific_source_commit':'a'*40})
    return {**p,'content_sha256':digest(p)}


def setup(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    module.save(tmp_path/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    return p


def test_finite_plan_keeps_original_objectives_authority_and_exact_probe_contract(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch)
    assert [(s['arm'].split(':')[0],s['generation']) for s in p['schedule']]==[
        ('throughput',0),('efficiency',0),('efficiency',1),('throughput',1)]
    assert p['budget']['native_worlds_upper_bound']==7 and not p['budget']['replace_failed_slots']
    assert p['budget']['component_attempts_upper_bound']==32 and p['development_seed_reused']
    assert p['losses']==old_plan()['losses'] and p['evaluation_seeds']==[]
    for arm in p['arm_order']:
        c=module.campaign(tmp_path/'test-campaign',p,'run-00',arm)
        request=c._request([],c._strategy_initial(),1)
        assert request['strategy_provenance'][module.TEST_OPTION]==p['post_edit_contract']
        assert request['loss_spec']==p['losses'][p['assignments'][arm]['objective']]
        assert request['design_space']['world_law_scope']=='fixed-native-production-review-routing-v2'


def test_all_generation_nulls_consume_four_slots_without_native_fallback(tmp_path,monkeypatch):
    p=setup(tmp_path,monkeypatch);events=[];requests=[]
    monkeypatch.setattr(module,'wait_analysis',lambda *a:events.append('preceding-closed') or {'status':'closed'})
    def calibration(root,p,**kwargs):
        events.append('readiness');requests.append(clone(kwargs['request']));return tmp_path/'SCRIPTED-cert'
    monkeypatch.setattr(module,'readiness',calibration)
    monkeypatch.setattr(module,'observe',lambda *a:events.append('reference') or {'status':'complete'})
    monkeypatch.setattr(module,'LocalRoleBoundNativeFactory',lambda *a,**kw:SimpleNamespace(
        model_digest=p['scientist']['model_digest'],corpus_sha256=p['scientist']['corpus_sha256']))
    dispatches=[]
    def generate(*args,**kwargs):
        assert kwargs['seconds']==1800 and kwargs['post_edit_bank']==p['component_bank']
        dispatches.append(kwargs);return {'generation_failure':'SCRIPTED known no-submission'}
    monkeypatch.setattr(module,'execute',generate)
    module.run(tmp_path)
    assert events[:2]==['preceding-closed','readiness']
    assert events.count('readiness')==4 and events.count('reference')==3 and len(dispatches)==4
    assert [len(r['history']) for r in requests]==[0,0,1,1]
    selected=module.read(tmp_path/'selection.json')
    assert all(v['system'] is None and v['loss'] is None for v in selected['selected'].values())
    assert not selected['baseline_fallback'] and module.read(tmp_path/'terminal.json')['status']=='closed'
    with pytest.raises(ValueError,match='no redispatch'):module.run(tmp_path)
    assert len(dispatches)==4


def test_stopped_preceding_analysis_cannot_start_readiness_or_native_world(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    def stopped(*a):raise ValueError('SCRIPTED prior chain stopped')
    monkeypatch.setattr(module,'wait_analysis',stopped)
    monkeypatch.setattr(module,'readiness',lambda *a,**kw:pytest.fail('no inference'))
    monkeypatch.setattr(module,'observe',lambda *a:pytest.fail('no native world'))
    with pytest.raises(ValueError,match='prior chain stopped'):module.run(tmp_path)
    assert module.read(tmp_path/'terminal.json')['status']=='stopped'


def test_unknown_proposal_completion_stops_next_arm_and_preserves_pending_state(tmp_path,monkeypatch):
    p=setup(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(module,'wait_analysis',lambda *a:{'status':'closed'})
    monkeypatch.setattr(module,'readiness',lambda *a,**kw:tmp_path/'SCRIPTED-cert')
    monkeypatch.setattr(module,'observe',lambda *a:{'status':'complete'})
    monkeypatch.setattr(module,'LocalRoleBoundNativeFactory',lambda *a,**kw:SimpleNamespace(
        model_digest=p['scientist']['model_digest'],corpus_sha256=p['scientist']['corpus_sha256']))
    def unknown(*a,**kw):calls.append(kw);raise CompletionUnknown('SCRIPTED unknown generation')
    monkeypatch.setattr(module,'execute',unknown)
    with pytest.raises(CompletionUnknown):module.run(tmp_path)
    assert len(calls)==1 and not (tmp_path/'selection.json').exists()
    c=module.campaign(tmp_path,p,'run-00',p['arm_order'][0])
    assert c.state['pending'] is not None and not c.state['records']
    assert module.read(tmp_path/'terminal.json')['status']=='stopped'


def test_saved_plan_roundtrip_survives_json_sorting_and_rejects_changed_schedule(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch);prior=tmp_path/'prior';prior.mkdir()
    (prior/'started.json').write_text('{"SCRIPTED":true}')
    p['preceding_analysis'].update(directory=str(prior),start_file_sha256=module.file_sha256(prior/'started.json'))
    saved=module.save(tmp_path/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    monkeypatch.setattr(module,'pinned_revision',lambda root:'c'*40)
    assert module.require_plan(tmp_path)==saved
    changed={k:v for k,v in saved.items() if k!='content_sha256'}
    changed['schedule']=changed['schedule'][::-1]
    (tmp_path/'plan.json').unlink();module.save(tmp_path/'plan.json',changed)
    with pytest.raises(ValueError,match='reconstruction'):module.require_plan(tmp_path)


def test_auditor_rejects_nonclosed_loop_before_starting_original_source_worker(tmp_path,monkeypatch):
    from scripts import audit_native_code_tested_loop_v1 as auditor
    module.save(tmp_path/'terminal.json',{'status':'stopped'})
    monkeypatch.setattr('sys.argv',['audit','--run',str(tmp_path),'--frozen-source',str(tmp_path),
        '--output',str(tmp_path/'no-audit.json')])
    monkeypatch.setattr(auditor.subprocess,'run',lambda *a,**kw:pytest.fail('no original worker'))
    with pytest.raises(ValueError,match='closed code-tested loop'):auditor.main()


def test_cost_adapter_recognizes_new_exact_closed_audit_without_relabeling_old_scopes():
    from scripts.reports.pre_scale_costs_v1 import AUDITS
    assert AUDITS[-1]=='scienceutopia.native-code-tested-loop-audit.v1'
    assert AUDITS[3]=='scienceutopia.native-institution-loop-stopped-audit.v1'
    assert AUDITS[4]=='scienceutopia.native-fixed-candidate-evaluation-audit.v1'


def test_failed_fresh_calibration_stops_before_reference_or_proposal(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'wait_analysis',lambda *a:{'status':'closed'})
    def failed(*a,**kw):raise ValueError('SCRIPTED fresh calibration failed')
    monkeypatch.setattr(module,'readiness',failed)
    monkeypatch.setattr(module,'observe',lambda *a:pytest.fail('no reference dispatch'))
    monkeypatch.setattr(module,'execute',lambda *a,**kw:pytest.fail('no proposal dispatch'))
    with pytest.raises(ValueError,match='calibration failed'):module.run(tmp_path)
    assert module.read(tmp_path/'terminal.json')['status']=='stopped'


def test_mismatched_actual_scientist_factory_stops_before_proposal_or_candidate_world(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'wait_analysis',lambda *a:{'status':'closed'})
    monkeypatch.setattr(module,'readiness',lambda *a,**kw:tmp_path/'SCRIPTED-cert')
    monkeypatch.setattr(module,'observe',lambda *a:{'status':'complete'})
    monkeypatch.setattr(module,'LocalRoleBoundNativeFactory',lambda *a,**kw:SimpleNamespace(
        model_digest='WRONG-model',corpus_sha256='WRONG-corpus'))
    monkeypatch.setattr(module,'execute',lambda *a,**kw:pytest.fail('no proposal dispatch'))
    with pytest.raises(ValueError,match='researcher/corpus differs'):module.run(tmp_path)
    assert module.read(tmp_path/'terminal.json')['status']=='stopped'
