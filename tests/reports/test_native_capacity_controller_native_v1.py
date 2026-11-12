"""Complete nine-world controller with SCRIPTED HTTP, corpus and designer.

Native Simulation, institutional containers, journals, measurement, real
reference context, loss feedback and cold physical proofs are not mocked.
This is software integration, not evidence about actual Qwen policy design.
"""
from pathlib import Path

from scripts import run_native_capacity_objective_loop_v1 as driver
from scripts.native_benchmark_physical import physical_proof
from tests.reports.test_native_capacity_objective_loop_v1 import plan
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_active_founders import measure_from_checkpoints
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest


def test_real_references_two_objective_histories_feedback_selection_and_nine_cold_worlds(tmp_path,fixed_corpus,monkeypatch):
    p=plan(tmp_path/'inputs',monkeypatch,
        image_override='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833')
    install_scripted_provider(tmp_path/'provider',monkeypatch,2)
    # The declared scientific binding in this software fixture is explicitly
    # its real scripted transport/corpus binding, not the installed Qwen digest.
    def factory(directory,p,root):
        f=LocalQwenNativeFactory(directory,tmp_path/'cache',years=4,corpus_years=4,
            record_wire=True,record_code=True,maximum_http_attempts=1024,
            inference_lock=root/'inference.lock',allow_dirty=True,
            world_conditions=p['world']['world_conditions'],experiment_binding=p['experiment'])
        def make(spec,seed,run_id):
            sim=f(spec,seed,run_id);sim.llm.sim=sim;return sim
        return make
    probe=LocalQwenNativeFactory(tmp_path/'probe',tmp_path/'cache',years=4,corpus_years=4,allow_dirty=True)
    for key in ('model','model_digest','corpus_sha256','dataset_identity','runtime_seed_binding','source_commit'):
        p['world'][key]=clone(getattr(probe,key))
    p['world']['classification']='SCRIPTED-nine-world-controller-native-integration'
    p['source_commit']=probe.source_commit
    p['measurement_contract']['source_commit']=probe.source_commit
    p={k:v for k,v in p.items() if k!='content_sha256'};p['content_sha256']=digest(p)
    monkeypatch.setattr(driver,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr(driver,'factory_for',factory)
    requests=[];gates=[]
    monkeypatch.setattr(driver,'readiness',lambda root,p,**kw:gates.append(clone(kw['request'])) or tmp_path/'SCRIPTED-cert')
    def generate(*a,**kw):
        requests.append(clone(kw['request']))
        return {'base_patch':None,'factors':[],'continuous':[],
            'provenance':{'kind':'SCRIPTED-explicit-identity-not-LLM-invention'}}
    monkeypatch.setattr(driver,'execute',generate)
    root=tmp_path/'study';root.mkdir();driver.run(root)
    assert driver.read(root/'terminal.json')['status']=='closed'
    assert len(gates)==5 and len(requests)==4
    assert [len(r['history']) for r in requests]==[0,0,1,1]
    assert [len(r['observations']) for r in requests]==[5,5,6,6]
    selected=driver.read(root/'selection.json')
    assert not selected['baseline_fallback']
    assert all(v['completed_submissions']==2 and v['system'] is not None for v in selected['selected'].values())
    for request in requests:
        assert request['loss_spec'] in p['losses'].values()
        assert request['world_binding']['measurement_adapter_contract']==p['measurement_contract']
        assert all(driver.METRIC in r['observation']['metadata']['measurements'][0]['metrics']
                   for r in request['observations'])
    observations=[driver.read(path) for path in (root/'references').glob('*/observation.json')]
    for objective in p['objectives']:
        c=driver.campaign(root,p,objective,driver.read(root/'developer-reference-context.json'))
        observations.extend(o for r in c.state['records'] for o in r['observations'])
    assert len(observations)==9
    for observation in observations:
        m=observation['metadata'];assert observation['status']=='complete' and len(m['runs'])==1
        evidence=m['runs'][0];checkpoint=Path(evidence['checkpoint_path']);cell=checkpoint.parent
        # Resolve by actual cache location, never guessed layout depth.
        while not (cell/'replies/responses.sqlite').is_file():
            assert cell.is_relative_to(root)
            cell=cell.parent
        spec=SystemSpec.from_dict(observation['candidate'])
        proof=physical_proof(cell,spec,world=p['world'],seed=driver.SEED,years=4,evidence=evidence)
        measured={**measure_from_checkpoints(proof['measurement'],
            [checkpoint.parent/f'portable_checkpoint_year_{y}.json.gz' for y in range(5)]),
            'measurement_adapter_contract_sha256':digest(p['measurement_contract'])}
        assert m['measurements']==[measured]
