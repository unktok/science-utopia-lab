"""Snapshot projection QA, never live/native inference."""
import json

import pytest

from scripts.export_pre_scale_observatory import project
from utopia.optimization.native_numeric_designer import save
from utopia.replay.campaign_adapter import web_event_stream_hash


def fixture(root):
    p=save(root/'plan.json',{'schema':'scienceutopia.pre-scale-pilot.v1.plan','source_commit':'a'*40,
        'runtime':{'SCRIPTED':'source'},'scientist':{'model':'qwen3:8b'},
        'designer':{'model':'qwen3.6:35b-mlx-64k'},'mechanism_seeds':[41001,41011,41017],
        'losses':{'throughput':{},'efficiency':{},'selective':{}}})
    save(root/'mechanisms/M0-s41001/started.json',{'identity':'M0-s41001','plan_sha256':p['content_sha256']})
    return p


def test_started_journal_never_becomes_a_live_process_or_zero_loss(tmp_path):
    fixture(tmp_path)
    e=project(tmp_path,observed_utc='2026-11-09T01:00:00+00:00');p=e['payload']
    assert len(p['information']['worlds'])==12
    assert p['information']['worlds'][0]['status']=='started-no-terminal-observation'
    assert all(r['scores'] is None for r in p['information']['worlds'])
    assert p['search']['status']=='not-dispatched' and not p['search']['selection_fixed']
    assert 'not-live-heartbeat' in p['observation_kind']
    assert e['web_sha256']==web_event_stream_hash([p])


def test_fake_closure_cannot_hide_missing_mechanism_observations(tmp_path):
    p=fixture(tmp_path)
    save(tmp_path/'mechanisms-complete.json',{'plan_sha256':p['content_sha256'],
        'all_observation_file_sha256':{}})
    with pytest.raises(ValueError,match='does not cover'):project(tmp_path)


def test_cross_source_numeric_certificate_is_rejected(tmp_path):
    p=fixture(tmp_path)
    save(tmp_path/'numeric-readiness/certificate.json',{'provider':p['designer'],
        'runtime':{'SCRIPTED':'different-source'},'cases':[]})
    with pytest.raises(ValueError,match='source/model'):project(tmp_path)
