"""Prospective advice-control orchestration; scripted, not scientific results."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_instruction_timing_support_v1 as module
from scripts.run_pre_scale_completion_chain_v1 import save as plain_chain_save
from tests.reports.test_native_institution_loop_v1 import plan as original_operator
from utopia.optimization.common_content_observer import CommonContentObserver, make_contract, ObserverCompletionUnknown
from utopia.system.design_patch import clone, digest


def operator():
    old=original_operator(); image=old['scientist']['image_id']
    anchor=module.liquidity_control(module.selection_control(module.information_system(image,seed=61001),rule='accept-all'),image)
    backend={**{k:old['scientist'][k] for k in ('model','model_digest')},'ollama_version':'SCRIPTED'}
    return {**{k:clone(old[k]) for k in ('scientist','designer','data_cache','world')},
        'reference_systems':{'reviewed-all-connected':anchor.to_dict()},
        'world':{**clone(old['world']),'world_conditions':{
            'schema':'scienceutopia.native-world-conditions.v1','initial_funding':30,
            'population_resource_profile':'balanced_two_band','log_resource_ledger':True}},
        'losses':{'throughput':module.objective_specs()['throughput'],
            'content-utility':json.loads((module.ROOT/module.CONTENT_LOSS).read_text())},
        'observer_contract':make_contract(source_commit='a'*40,provider={k:old['scientist'][k] for k in ('model','model_digest')},
            backend=backend,maximum_posts=3000,critics=3)}


def prospective_plan():
    op=operator();p=module.build_plan(op,source='b'*40,
        observer_backend=op['observer_contract']['backend'],preceding={'SCRIPTED':'not real preceding evidence'})
    return {**p,'content_sha256':digest(p)}


def preceding(tmp_path,monkeypatch):
    raw,analysis,source=tmp_path/'prior',tmp_path/'prior-analysis',tmp_path/'prior-source'
    for path in (raw,analysis,source):path.mkdir()
    (raw/'writer.lock').touch()
    p=module.save(raw/'plan.json',{**operator(),
        'schema':'scienceutopia.native-objective-fixed-evaluation.v1.plan','source_commit':'a'*40,
        'jobs':[{'SCRIPTED':'one declared prior physical job'}]})
    end=module.save(raw/'terminal.json',{'schema':'scienceutopia.native-objective-fixed-evaluation.v1.terminal',
        'status':'closed','completed_jobs':1})
    audit={'schema':'scienceutopia.native-objective-fixed-evaluation-audit.v1','source_commit':'a'*40,
        'plan_sha256':p['content_sha256'],'closure':{'terminal':end},
        'source_proof':{'status':'verified-exact-source-closure'},'new_model_calls':0,'new_code_executions':0,
        'raw_inventory_sha256':digest(module._inventory(raw))}
    for i in (1,2):module.save(analysis/f'audit-{i}.json',audit)
    for i in (1,2):module.save(analysis/f'costs-{i}.json',{'SCRIPTED':'original separate cost view'})
    plain_chain_save(analysis/'started.json',{'schema':'scienceutopia.native-objective-fixed-evaluation-finish.v1',
        'plan_file_sha256':module.file_sha256(raw/'plan.json'),'scientific_source_commit':'a'*40})
    plain_chain_save(analysis/'ended.json',{'status':'closed',
        'audit_file_sha256':module.file_sha256(analysis/'audit-1.json'),
        'cost_file_sha256':module.file_sha256(analysis/'costs-1.json')})
    monkeypatch.setattr(module,'pinned_revision',lambda path:'a'*40 if Path(path)==source else 'b'*40)
    return raw,analysis,source


def test_exact_same_message_producer_has_only_declared_cut_and_timing_changes():
    p=prospective_plan();cut,early,late=[j['system'] for j in p['jobs']]
    assert cut['mechanisms']==early['mechanisms']==late['mechanisms']
    assert cut['schedules']==early['schedules']
    assert early['connections']==late['connections']
    assert [e for e in early['connections'] if e not in cut['connections']]==[{
        'source_mechanism':'developer-instruction-office','source_port':'messages',
        'target_mechanism':'developer-instruction-receiver','target_port':'messages',
        'channel':'artifact','latency':0}]
    assert [(a,b) for a,b in zip(early['schedules'],late['schedules']) if a!=b]==[({
        'mechanism_id':'developer-instruction-receiver','phase':2,'trigger':'annual'}, {
        'mechanism_id':'developer-instruction-receiver','phase':235,'trigger':'annual'})]
    assert [(j['condition'],j['seed']) for j in p['jobs']]==[('cut',61001),('early',61001),('late',61001)]
    protocol=(module.ROOT/module.PROTOCOL).read_text()
    quoted=' '.join(line.removeprefix('> ') for line in protocol.splitlines() if line.startswith('> '))
    assert quoted==module.MESSAGE==p['instruction'] and '\n' not in p['instruction']
    assert p['budget']['designer_generation_POSTs']==0 and not p['policy_selection']
    assert p['development_seed_reused'] and not p['held_out_evaluation']


def test_real_plain_chain_api_then_actual_plan_save_roundtrip(tmp_path,monkeypatch):
    raw,analysis,source=preceding(tmp_path,monkeypatch)
    assert 'content_sha256' not in json.loads((analysis/'ended.json').read_text())
    op,evidence=module.preceding_evidence(raw,analysis,source)
    root=tmp_path/'new';root.mkdir()
    p=module.build_plan(op,source='b'*40,observer_backend=op['observer_contract']['backend'],preceding=evidence)
    expected=module.save(root/'plan.json',p)
    assert module.require_plan(root)==expected


@pytest.mark.parametrize('change',['message','phase','budget','loss','observer'])
def test_changed_plan_is_not_silently_reconstructed_or_repaired(tmp_path,monkeypatch,change):
    raw,analysis,source=preceding(tmp_path,monkeypatch);op,prior=module.preceding_evidence(raw,analysis,source)
    root=tmp_path/'new';root.mkdir();p=module.build_plan(op,source='b'*40,
        observer_backend=op['observer_contract']['backend'],preceding=prior)
    if change=='message':p['instruction']+=' different'
    elif change=='phase':p['jobs'][2]['system']['schedules'][-1]['phase']=200
    elif change=='budget':p['budget']['world_wall_seconds']+=1
    elif change=='loss':p['losses']['throughput']['per_run']['terms'][0]['coefficient']=-100
    else:p['observer_contract']['rubric']='different';p['observer_contract'].pop('content_sha256');p['observer_contract']['content_sha256']=digest(p['observer_contract'])
    module.save(root/'plan.json',p)
    with pytest.raises(ValueError,match='reconstruction differs'):module.require_plan(root)


@pytest.mark.parametrize('change',['stopped','chain-stopped','different-audits','raw-added','wrong-source'])
def test_previous_study_must_really_be_closed_unchanged_and_source_bound(tmp_path,monkeypatch,change):
    raw,analysis,source=preceding(tmp_path,monkeypatch)
    if change=='stopped':
        end=module.read(raw/'terminal.json');end.pop('content_sha256');end['status']='stopped'
        (raw/'terminal.json').unlink();module.save(raw/'terminal.json',end)
    elif change=='chain-stopped':
        p=analysis/'ended.json';end=json.loads(p.read_text());end['status']='stopped';p.unlink();plain_chain_save(p,end)
    elif change=='different-audits':(analysis/'audit-2.json').write_text('{}')
    elif change=='raw-added':(raw/'unaccounted').write_text('SCRIPTED')
    else:monkeypatch.setattr(module,'pinned_revision',lambda *a:'f'*40)
    with pytest.raises(ValueError):module.preceding_evidence(raw,analysis,source)


@pytest.mark.parametrize('change',['loss','world','reference','judge'])
def test_no_changed_scientific_preferences_or_native_laws(change):
    op=operator();backend=op['observer_contract']['backend']
    if change=='loss':op['losses']['throughput']['per_run']['terms'][0]['coefficient']=-99
    elif change=='world':op['world']['world_conditions']['initial_funding']=999
    elif change=='reference':op['reference_systems']['reviewed-all-connected']['schedules'][0]['phase']=123
    else:backend={**backend,'ollama_version':'different'}
    with pytest.raises(ValueError):module.build_plan(op,source='b'*40,observer_backend=backend,preceding={})


@pytest.mark.parametrize('failure',[None,'control','unknown'])
def test_real_observe_save_and_public_observer_audit_close_without_retries(tmp_path,monkeypatch,failure):
    p=prospective_plan();prior=tmp_path/'previous';prior.mkdir();(prior/'writer.lock').touch()
    p['preceding']={'run':str(prior)};p.pop('content_sha256');p['content_sha256']=digest(p)
    root=tmp_path/'new';root.mkdir()
    monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    monkeypatch.setattr(module,'LocalObserverBackend',lambda **kwargs:None)
    monkeypatch.setattr(module,'factory_for',lambda *args:'SCRIPTED native factory')
    calls=[]
    def evaluate(suggestion,**kwargs):
        calls.append(suggestion.suggestion_id)
        assert kwargs['seeds']==[61001] and kwargs['simulation_factory']=='SCRIPTED native factory'
        if failure=='unknown':raise ObserverCompletionUnknown('SCRIPTED unknown completion')
        m={'run_id':'SCRIPTED','metrics':{
            'native.accepted_decisions':{'status':'measured','value':2},
            'native.common_content_utility_sum':{'status':'measured','value':1}}}
        return SimpleNamespace(to_dict=lambda:{'status':'failed' if failure=='control' else 'complete',
            'metadata':{'measurements':[] if failure=='control' else [m]}})
    monkeypatch.setattr(module,'evaluate_native_suggestion',evaluate)
    if failure:
        with pytest.raises((ValueError,ObserverCompletionUnknown)):module.run(root)
    else:module.run(root)
    assert calls==(['instruction-cut'] if failure else ['instruction-cut','instruction-early','instruction-late'])
    end=module.read(root/'terminal.json')
    assert end['status']==('stopped' if failure else 'closed')
    assert end['completed_jobs']==(0 if failure else 3)
    assert not end['policy_selection']
    if not failure:
        assert module.read(root/'observer-audit.json')==CommonContentObserver(root/'observer',p['observer_contract'],backend=None).audit()
    with pytest.raises(ValueError,match='consumed'):module.run(root)
