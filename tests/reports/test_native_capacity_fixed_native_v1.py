"""Ten actual native forwards/cold readouts with SCRIPTED model/corpus bindings.

Original development origin and model-load attestations are mocked explicitly.
Execution, policy identity, unused-seed rebinding, P instrument, physical/source
proof, actual score/effect/input exports and cost accounting are not mocked.
This is software QA, never evidence about actual Qwen optimization outcomes.
"""
from pathlib import Path
from types import SimpleNamespace

from scripts import run_native_capacity_fixed_evaluation_v1 as driver
from scripts import audit_native_capacity_fixed_evaluation_v1 as audit
from scripts.reports.native_capacity_fixed_evaluation_v1 import export as score_export
from scripts.reports.native_institution_effect_trace_v1 import export as effect_export
from scripts.reports.native_observed_request_classes_v1 import export as request_export
from scripts.reports.pre_scale_costs_v1 import analyze as cost_projection
from tests.reports.test_native_capacity_fixed_evaluation_v1 import evidence,usage,seal
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.system.design_patch import clone


def test_two_unused_seeds_ten_native_worlds_original_checkpoints_and_all_public_readouts(
        tmp_path,fixed_corpus,monkeypatch):
    seeds=[67101,67107]
    original,origin_audit,_=evidence(tmp_path/'inputs',monkeypatch,seeds=seeds,
        image_override='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833')
    install_scripted_provider(tmp_path/'provider',monkeypatch,2)
    probe=LocalQwenNativeFactory(tmp_path/'probe',tmp_path/'cache',years=4,corpus_years=4,allow_dirty=True)
    for key in ('model','model_digest','corpus_sha256','dataset_identity','runtime_seed_binding','source_commit'):
        original['world'][key]=clone(getattr(probe,key))
        if key in original['scientist']:original['scientist'][key]=clone(getattr(probe,key))
    original['source_commit']=probe.source_commit
    original['world']['classification']='SCRIPTED-capacity-fixed-native-integration'
    original['measurement_contract']['source_commit']=probe.source_commit
    original['world']['measurement_adapter_contract']=clone(original['measurement_contract']);seal(original)
    origin_audit.update(source_commit=original['source_commit'],plan_sha256=original['content_sha256'])
    origin_audit['selection']['plan_sha256']=original['content_sha256'];seal(origin_audit['selection']);seal(origin_audit)
    origin=tmp_path/'SCRIPTED-origin';origin.mkdir();(origin/'writer.lock').touch()
    inventory=tmp_path/'SCRIPTED-unused-root';inventory.mkdir()
    u=usage(seeds);u['root']=str(inventory);seal(u)
    p=seal(driver.build_plan(original,origin_audit,source=probe.source_commit,
        origin={'run':str(origin),'SCRIPTED':'origin attestation not real development'},usages=[u],seeds=seeds))
    root=tmp_path/'evaluation';root.mkdir()
    driver.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    driver.save(root/'seed-usage-00.json',{k:v for k,v in u.items() if k!='content_sha256'})
    monkeypatch.setattr(driver,'origin_evidence',lambda origin:(original,origin_audit))
    monkeypatch.setattr(driver,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'usage_inventory',lambda *a:u)
    def factory(directory,p,root):
        f=LocalQwenNativeFactory(directory,tmp_path/'cache',years=4,corpus_years=4,
            record_wire=True,record_code=True,maximum_http_attempts=1024,
            inference_lock=root/'inference.lock',allow_dirty=True,
            world_conditions=p['world']['world_conditions'],experiment_binding=p['experiment'])
        def make(spec,seed,run_id):
            sim=f(spec,seed,run_id);sim.llm.sim=sim;return sim
        return make
    monkeypatch.setattr(driver,'factory_for',factory)
    driver.run(root)
    assert driver.require_plan(root)==p
    assert driver.read(root/'terminal.json')['status']=='closed'
    assert driver.read(root/'terminal.json')['completed_jobs']==10
    # The LocalQwen factory doesn't make real role-load calls. Keep that
    # limitation explicit while exercising all actual physical/source proofs.
    def loaded(*args,**kwargs):
        return {'confirmed':True,'SCRIPTED':'not an actual-model role attestation',
            'context':str(Path(args[0]).parent/'SCRIPTED-role-context.json')}
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded',loaded)
    paths=[tmp_path/'audit-one.json',tmp_path/'audit-two.json']
    for path in paths:audit.worker(root,path)
    assert paths[0].read_bytes()==paths[1].read_bytes()
    audited=driver.read(paths[0]);assert len(audited['worlds'])==10
    assert audited['source_proof']['status']=='verified-exact-source-closure'
    for w in audited['worlds']:
        assert w['status']=='complete' and len(w['physical_proof']['annual_checkpoints'])==4
        assert w['physical_proof']['world_conditions_proof']['fixed_annual_slot_cap']==1
        m=w['measurements'][0];instrument=m['active_founder_boundary_instrument']
        assert len(instrument['initial_founder_ids'])==5 and len(instrument['annual'])==4
        assert m['metrics']['native.active_founder_boundary_sum']['value']==sum(
            year['active_founders'] for year in instrument['annual'])
    args=SimpleNamespace(run=root,audit_one=paths[0],audit_two=paths[1],output=tmp_path/'scores',
        frozen_source=driver.ROOT,scope='capacity-fixed-evaluation')
    score_export(args);scores=driver.read(args.output/'report.json')
    assert len(scores['physical_worlds'])==10 and len(scores['logical_rows'])==14
    assert len(scores['paired_differences'])==20
    assert len([r for r in scores['logical_rows'] if r['status']=='no-completed-submission'])==2
    assert scores['score_order']==['throughput','founder-activity']
    assert scores['fixed_selection']==p['fixed_selection']
    args.output=tmp_path/'effects';effect_export(args)
    assert len(driver.read(args.output/'report.json')['worlds'])==10
    args.output=tmp_path/'requests';request_export(args)
    assert len(driver.read(args.output/'report.json')['worlds'])==10
    costs=cost_projection(root,p,audited)
    assert len(costs['scientist']['physical_response_caches'])==10
    assert costs['scientist']['completed_responses']>0
    assert 'common_content_observer' not in costs
    assert not audited['new_model_calls'] and not audited['new_code_executions']
