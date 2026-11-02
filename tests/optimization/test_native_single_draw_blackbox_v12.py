"""Opt-in singleton scalar feedback never masquerades as an LR/LOO estimate."""
import pytest
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus

from tests.optimization.test_native_adaptive_search import (
    create, tiny_definition, tiny_parent, loss_spec, synthetic_observation, fail_factory)
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign


def mixed(**kw):
    return GeneratedMixedDesign(tiny_parent(),tiny_definition(),loss_spec=loss_spec(),seed=42,**kw)


def test_singleton_optin_samples_factors_and_latents_without_gradient():
    design=mixed(single_draw_blackbox=True)
    draws=design.draw(1,version_sha256='singleton-software-QA')
    assert len(draws)==1 and draws[0]['assignment'] and len(draws[0]['latent'])==1
    report=design.update(draws,[synthetic_observation(draws[0],-2.)],score=False)
    assert report['status']=='blackbox-observed' and report['gradient'] is None
    assert report['weights_after']==report['weights_before']


def test_no_singleton_score_even_with_blackbox_sampling_optin():
    design=mixed(single_draw_blackbox=True)
    draws=design.draw(1,version_sha256='singleton-software-QA')
    with pytest.raises(ValueError,match='tell batch'):
        design.update(draws,[synthetic_observation(draws[0],-2.)],score=True)


def test_default_still_requires_two_and_preserves_original_draws():
    with pytest.raises(ValueError,match='at least two'):
        mixed().draw(1,version_sha256='singleton-forbidden')
    a,b=mixed(),mixed(single_draw_blackbox=False)
    assert a.draw(2,version_sha256='old-two-draw-path')==b.draw(2,version_sha256='old-two-draw-path')


@pytest.mark.parametrize('mode',['score','hybrid'])
def test_campaign_estimator_modes_reject_singletons_before_author_or_factory(tmp_path,mode):
    campaign=create(tmp_path,mode=mode)
    with pytest.raises(ValueError,match='at least two'):
        campaign.advance(simulation_factory=fail_factory,generators={},count=1)
    assert campaign.state['records']==[] and campaign.state['pending'] is None


def test_singleton_technical_failure_is_null_and_cold_restores(tmp_path):
    campaign=create(tmp_path,mode='blackbox')
    generators={k:lambda req:tiny_definition() for k in campaign.binding['strategies']}
    record=campaign.advance(simulation_factory=fail_factory,generators=generators,count=1)
    assert record['report']['status']=='not-updated-technical-failure'
    assert len(record['draws'])==1 and record['observations'][0]['loss'] is None
    assert create(tmp_path,mode='blackbox').state==campaign.state


def test_original_six_year_single_draw_source_revision_and_cold_restart(tmp_path,fixed_corpus,monkeypatch):
    from tests.optimization.test_native_adaptive_search import evolving_native_generator
    from tests.runtime.test_portable_checkpoint_integration import BINDING,seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
    from utopia.runtime.checkpointing import PortableStop
    from utopia.system.code_mechanisms import DockerCodeExecutor,CodeExecutionError
    from utopia.system.native_kernel import NativeScienceKernel,legacy_world_system
    try:
        executor=DockerCodeExecutor()
    except (OSError,CodeExecutionError):
        pytest.skip('existing isolated local runtime required')
    world={'source_commit':'singleton-native-scripted-QA',
        'model_digest':BINDING['model_revision'],'corpus_sha256':BINDING['corpus_sha256']}
    seen,runs,replies=[],[],[]
    generator=evolving_native_generator(executor.image_id,seen)
    def factory(spec,run_seed,run_id):
        runs.append(run_id)
        if len(runs)==2:
            raise PortableStop('cold stop before second singleton native world')
        monkeypatch.setitem(BINDING,'cell',spec.fingerprint)
        monkeypatch.setitem(BINDING,'science_config',{**BINDING['science_config'],'source_commit':world['source_commit']})
        seed()
        sim,calls=make_sim(tmp_path/'worlds'/run_id,native=NativeScienceKernel(spec))
        replies.append(calls)
        return sim
    def reopen():
        return NativeAdaptiveDesignCampaign(tmp_path/'campaign',initial_system=legacy_world_system(),
            loss_spec=loss_spec(),seeds=[42],world_binding=world,
            strategies={'design':{'fixture':'scripted-not-invention'}},mode='blackbox',seed=42)
    first=reopen().advance(simulation_factory=factory,generators={'design':generator},count=1)
    assert len(first['observations'])==1 and first['observations'][0]['status']=='complete'
    with pytest.raises(PortableStop):
        reopen().advance(simulation_factory=factory,generators={'design':generator},count=1)
    assert len(seen)==2
    second=reopen().advance(simulation_factory=factory,
        generators={'design':lambda req:pytest.fail('saved source must not be regenerated')},count=1)
    assert len(second['observations'])==1 and second['observations'][0]['status']=='complete'
    assert second['report']['mixed']['gradient'] is None
    assert second['version_sha256']!=first['version_sha256']
    assert len(second['definition']['factors'][0]['choices'])==3
    assert len(replies)==2 and all(replies) and runs[1]==runs[2]
    assert len(reopen().state['records'])==2
