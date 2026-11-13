"""18 native worlds/72 checkpoints, three cold readers and double exports.

All HTTP/data, original-study attestations and unused-root receipts are named
SCRIPTED fixtures. Production role loads/factory, seed rebinding, original
native execution, checkpoints, Docker consumers, observer reconstruction,
literal policy sharing, reports and costs are actual software paths. This
does not dispatch real-Qwen scientific evaluation or certify upstream studies.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from scripts import run_native_joint_fixed_evaluation_v1 as driver
from scripts import audit_native_joint_fixed_evaluation_v1 as audit
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from scripts.reports.native_joint_fixed_evaluation_v1 import export
from tests.reports.test_native_joint_fixed_evaluation_v1 import evidence,audited,usage,seal
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory,SCIENTIST_DIGEST
from utopia.system.design_patch import clone

IMAGE='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_eighteen_original_worlds_fixed_sixteen_labels_real_roles_and_complete_cold_readouts(tmp_path,fixed_corpus,monkeypatch):
    values,_=evidence(tmp_path/'inputs',monkeypatch,image_override=IMAGE)
    install_scripted_provider(tmp_path/'provider',monkeypatch,2)
    monkeypatch.setattr('requests.get',lambda *a,**k:SimpleNamespace(raise_for_status=lambda:None,
        json=lambda:{'models':[{'name':'qwen3:8b','digest':SCIENTIST_DIGEST}]}))
    class Response:
        status_code=200
        def __init__(self,body):self.text=json.dumps(body)
        def raise_for_status(self):pass
    class LoadSession:
        def get(self,url,**kw):
            assert url.endswith('/api/ps')
            return Response({'models':[{'name':'qwen3:8b','digest':SCIENTIST_DIGEST,'context_length':40960}]})
        def post(self,url,**kw):
            body=json.loads(kw['data']);assert url.endswith('/api/generate') and body['prompt']==''
            return Response({'model':'qwen3:8b','done':True,'done_reason':'load','response':'','eval_count':0,'prompt_eval_count':0})
    monkeypatch.setattr('requests.Session',LoadSession)
    probe=LocalQwenNativeFactory(tmp_path/'probe',tmp_path/'cache',years=4,corpus_years=4)
    for kind,(p,_) in values.items():
        for key in ('model','model_digest','corpus_sha256','dataset_identity','runtime_seed_binding','source_commit'):
            p['world'][key]=clone(getattr(probe,key))
            if key in p['scientist']:p['scientist'][key]=clone(getattr(probe,key))
            if key in ('corpus_sha256','dataset_identity'):p['designer'][key]=clone(getattr(probe,key))
        p['source_commit']=probe.source_commit;p['data_cache']=str(tmp_path/'cache')
        p['world']['classification']='SCRIPTED-joint-origin-'+kind
        p['observer_contract']=make_contract(source_commit=probe.source_commit,
            provider={k:p['scientist'][k] for k in ('model','model_digest')},
            backend={**{k:p['scientist'][k] for k in ('model','model_digest')},'ollama_version':'SCRIPTED'},
            maximum_posts=3000 if kind=='presentation' else 1500,critics=3)
        p['world']['measurement_adapter_contract']=clone(p['observer_contract']);seal(p)
    old=values['planning'][0];prior=audited(old,'planning')
    numeric=values['numeric'][0];numeric['origin_audit_content_sha256']=prior['content_sha256']
    numeric['reference_context_sha256']=prior['developer_references']['content_sha256'];seal(numeric)
    values={'planning':(old,prior),'presentation':(values['presentation'][0],audited(values['presentation'][0],'presentation')),
        'numeric':(numeric,audited(numeric,'numeric',missing=('content-utility',)))}
    origins={k:{'run':str(tmp_path/('SCRIPTED-origin-'+k)),'SCRIPTED':True} for k in driver.STUDIES}
    for v in origins.values():
        path=Path(v['run']);path.mkdir();(path/'writer.lock').touch()
    seed_root=tmp_path/'SCRIPTED-unused-root';seed_root.mkdir();seeds=[81701,81707]
    u=usage(seeds);u['root']=str(seed_root);seal(u)
    from scripts.run_native_parameter_comparator_v1 import unchanged_native_sources
    p=driver.build_plan(values,source=probe.source_commit,origins=origins,usages=[u],seeds=seeds,
        observer_backend=old['observer_contract']['backend'],native_sources=unchanged_native_sources(old['source_commit']))
    root=tmp_path/'evaluation';root.mkdir();driver.save(root/'plan.json',p)
    driver.save(root/'seed-usage-00.json',{k:v for k,v in u.items() if k!='content_sha256'})
    monkeypatch.setattr(driver,'origin_evidence',lambda origin,kind:values[kind])
    monkeypatch.setattr(driver,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'usage_inventory',lambda *a:u)
    real_make=LocalRoleBoundNativeFactory.__call__
    def make(self,*a,**kw):
        sim=real_make(self,*a,**kw);sim.llm.sim=sim;return sim
    monkeypatch.setattr(LocalRoleBoundNativeFactory,'__call__',make)
    class Critic:
        @contextmanager
        def lease(self,contract):yield self
        def __call__(self,wire,timeout):
            body={'model':json.loads(wire)['model'],'done':True,'done_reason':'stop','prompt_eval_count':71,'eval_count':9,
                'message':{'content':json.dumps({'score':4,'rationale':'SCRIPTED complete observer reply'})}}
            return {'http_status':200,'raw_http_response':json.dumps(body)}
    monkeypatch.setattr(driver,'LocalObserverBackend',lambda **kw:Critic())
    # Do not mock require_plan, production factory/role receipts, native forward,
    # measurement, source proof, physical/critic audit, report, or costs.
    p=driver.require_plan(root);driver.run(root)
    assert driver.read(root/'terminal.json')['status']=='closed' and len(p['jobs'])==18
    paths=[tmp_path/'audit-1.json',tmp_path/'audit-2.json']
    for path in paths:audit.worker(root,path)
    assert paths[0].read_bytes()==paths[1].read_bytes()
    proof=driver.read(paths[0]);assert len(proof['worlds'])==18
    assert all(w['loaded']['confirmed'] and len(w['physical_proof']['annual_checkpoints'])==4 for w in proof['worlds'])
    from scripts.analyze_native_open_v7 import _inventory
    before=_inventory(root);outs=[tmp_path/'scores-1',tmp_path/'scores-2']
    for out in outs:export(SimpleNamespace(run=root,audit_one=paths[0],audit_two=paths[1],output=out))
    assert {f.name:f.read_bytes() for f in outs[0].iterdir()}=={f.name:f.read_bytes() for f in outs[1].iterdir()}
    report=driver.read(outs[0]/'report.json')
    assert len(report['logical_rows'])==32 and len(report['paired_differences'])==128
    assert len(report['fixed_policy_contrasts'])==16
    assert sum(r['status']=='no-completed-submission' for r in report['logical_rows'])==2
    for name,extra in (
            ('native_planning_choice_trace_v1',('--frozen-source',str(driver.ROOT),'--study','joint-fixed-evaluation')),
            ('native_institution_effect_trace_v1',('--frozen-source',str(driver.ROOT),'--scope','joint-fixed-evaluation')),
            ('native_observed_request_classes_v1',())):
        copies=[tmp_path/(name+'-one'),tmp_path/(name+'-two')]
        for out in copies:
            subprocess.run([sys.executable,'-m','scripts.reports.'+name,'--run',str(root),
                '--audit-one',str(paths[0]),'--audit-two',str(paths[1]),'--output',str(out),*extra],
                cwd=driver.ROOT,check=True,capture_output=True,text=True,timeout=1800)
        assert {f.name:f.read_bytes() for f in copies[0].iterdir()}=={f.name:f.read_bytes() for f in copies[1].iterdir()}
        assert len(driver.read(copies[0]/'report.json')['worlds'])==18
    projections=[costs(root,p,proof),costs(root,p,proof)]
    assert projections[0]==projections[1] and len(projections[0]['scientist']['physical_response_caches'])==18
    assert len(list(root.rglob('role-load-000.json')))==18 and not list(root.rglob('dispatch-*.intent.json'))
    assert _inventory(root)==before
