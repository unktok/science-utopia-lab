"""Combined original-world integration, scripted HTTP/retrieval, real Docker.

This is engineering QA; it is not Qwen or institutional-benefit evidence.
"""
from copy import deepcopy

from tests.runtime.test_portable_checkpoint_integration import BINDING, fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_hybrid import boundary_coverage, conditional_backward, project_continuous
from utopia.optimization.native_relaxation import native_tensor_trace
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.design_patch import make_patch
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.native_open_examples import SOURCE, joint_engineering_loss, open_native_system


def test_same_native_world_connects_domain_process_evolving_mixed_search_and_backward(tmp_path, fixed_corpus, monkeypatch):
    executor = DockerCodeExecutor(timeout=60.)
    initial = open_native_system(executor.image_id)
    calls, requests = [], []
    def factory(spec, run_seed, run_id):
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit':binding['source_commit']})
        seed()
        sim, payloads = make_sim(tmp_path / run_id, native=NativeScienceKernel(spec, code_executor=executor))
        calls.append(payloads)
        return sim
    binding = {'source_commit':'joint-v7-scripted-QA', 'model_digest':BINDING['model_revision'],
        'corpus_sha256':BINDING['corpus_sha256']}
    provenance = {'kind':'developer-software-QA-not-LLM-discovery', 'identity':'joint-v7-test'}
    def campaign():
        return NativeAdaptiveDesignCampaign(tmp_path/'campaign',initial_system=initial,
            loss_spec=joint_engineering_loss(), seeds=[42], world_binding=binding,
            strategies={'invent':provenance,'revise':provenance},mode='hybrid')
    def generate(request):
        requests.append(deepcopy(request))
        parent=SystemSpec.from_dict(request['parent_system'])
        index=next(i for i,n in enumerate(parent.mechanisms) if n.mechanism_id=='open-source')
        bias=next(i for i,n in enumerate(parent.mechanisms) if n.mechanism_id=='addressed-selection')
        patch=None
        if request['generation']:
            assert all(o['observation']['status']=='complete' for o in request['observations'])
            source=SOURCE.replace("{'actor_ids':[authors[index % len(authors)]],", "{'actor_ids':authors,")
            patch=make_patch(parent,[{'op':'replace',
                'path':f'/mechanisms/{index}/parameters/delegate/parameters/code_artifact/source','value':source}])
        return {'base_patch':patch,'factors':[{'id':'activity-repetition','kind':'bernoulli',
            'choices':[{'id':str(count),'operations':[{'op':'replace',
                'path':f'/mechanisms/{index}/parameters/count','value':count}], 'provenance':provenance} for count in (1,2)]}],
            'continuous':[{'id':'selection-bias','path':f'/mechanisms/{bias}/parameters/program/parameters/bias',
                'lower':-1.,'upper':1.,'mean':0.,'sigma':.5}], 'provenance':provenance}
    first=campaign().advance(simulation_factory=factory,generators={'invent':generate,'revise':generate},count=2)
    second=campaign().advance(simulation_factory=factory,generators={'invent':generate,'revise':generate},count=2)
    assert len(calls)==4 and len(requests)==2 and requests[1]['history']
    assert first['version_sha256']!=second['version_sha256']
    for record in (first,second):
        assert record['report']['status']=='score-updated'
        for draw, observation in zip(record['draws'],record['observations']):
            assert observation['status']=='complete',observation
            assert observation['loss'] is not None
            checkpoint=read_portable_checkpoint(observation['metadata']['runs'][0]['checkpoint_path'])
            native=checkpoint['native_system']
            assert native['last_year']==6
            repeats=draw['assignment']['activity-repetition']
            assert native['open_domain']['actors']['cooperative']['state']['rounds']==6*int(repeats)
            assert len(native['open_domain']['artifacts'])==6*int(repeats)
            assert native['graph_checkpoint']['mechanism_states']['open-source']['total_invocations']==6*int(repeats)
            system=SystemSpec.from_dict(draw['suggestion']['candidate'])
            coverage=boundary_coverage(system,native['events'])
            assert coverage['represented_numeric_edge_count']>=1
            assert not coverage['full_native_world_autograd']
            programs={n.mechanism_id:n.parameters['program'] for n in system.mechanisms if n.implementation=='program.tensor.v1'}
            backward=conditional_backward(native_tensor_trace(native['events']),programs,
                trainable={'addressed-selection':['bias']},terms=[{'mechanism':'open-memory-router','output':'actions','coefficient':-1.}])
            assert all(c['status']=='passed' for c in backward['numerical_checks'])
            candidate, projection=project_continuous(system,[{'id':'bias','mechanism':'addressed-selection',
                'path':'/program/parameters/bias','lower':-1.,'upper':1.,'quantum':None}],{'bias':0.})
            assert projection['candidate_fingerprint']==candidate.fingerprint
    assert campaign().state['records']==[first,second]
