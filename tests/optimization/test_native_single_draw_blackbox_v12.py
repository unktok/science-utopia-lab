"""Opt-in singleton scalar feedback never masquerades as an LR/LOO estimate."""
import pytest

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
