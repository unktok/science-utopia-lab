"""Finite comparison plan/replay QA, no model or native scientific result."""
from copy import deepcopy

import pytest

from scripts import run_native_feedback_comparison as driver
from tests.optimization.test_native_designer_roles_v38 import BINDING, designer_binding
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system


def plan():
    return driver.build_plan(source_commit='a'*40, provider_binding=BINDING,
        designer_provider_binding=designer_binding(), runtime_seed_binding={
            'python_hash_seed_environment': '42', 'python_hash_probe': 123},
        initial_system=open_native_system(BINDING['image_id']).to_dict())


def test_exact_four_arm_common_world_budget_and_initial_information(tmp_path):
    p = plan()
    assert p['content_sha256'] == digest({k: v for k, v in p.items() if k != 'content_sha256'})
    assert p['budget']['maximum_native_worlds'] == 9
    assert p['budget']['maximum_candidate_slots'] == 8
    assert p['budget']['maximum_authoring_POSTs'] == 128
    assert p['designer']['conversation_profile'] == p['conversation_profile']
    assert p['designer']['decoding']['editor']['http_timeout_seconds'] == [10, 900]
    campaigns = driver.make_campaigns(tmp_path, p)
    first = {}
    for name, c in campaigns.items():
        assert c.binding == p['campaign_bindings'][name]
        assert c.binding['world'] == p['world_binding']
        assert 'initial_evidence' not in c.binding
        r = c._request([], c._strategy_initial(), 1)
        first[name] = r
        assert r['parent_system'] == p['initial_system']
        assert r['history'] == r['observations'] == []
        assert r['based_on_observation_id'] is None
        assert 'objective' not in r['world_binding']['experiment']
        assert 'arm' not in r['world_binding']['experiment']
    assert first['throughput-loss']['loss_spec'] == first['throughput-technical-only']['loss_spec']
    assert first['efficiency-loss']['loss_spec'] == first['efficiency-technical-only']['loss_spec']
    assert first['throughput-loss']['loss_spec'] != first['efficiency-loss']['loss_spec']


def test_failure_consumes_each_slot_without_world_fallback_and_replays(tmp_path):
    p = plan(); campaigns = driver.make_campaigns(tmp_path, p)
    calls = []
    def author(request):
        calls.append((request['generation'], request['loss_spec']['id']))
        return {'generation_failure': {'kind': 'SCRIPTED author failure'}}
    def forbidden_world(*args):
        pytest.fail('a malformed definition must not start a native world')
    for _ in range(2):
        for c in campaigns.values():
            c.advance(simulation_factory=forbidden_world, generators={'local-bounded-author': author}, count=1)
    result = driver.progress(tmp_path, p, campaigns)
    assert len(calls) == result['consumed_candidate_slots'] == 8
    assert result['terminal'] and result['status'] == 'budget-complete-with-failures'
    assert all(r['loss'] is None and r['status']=='generation-failure'
        for arm in result['arms'].values() for r in arm['slots'])
    reloaded = driver.make_campaigns(tmp_path, p)
    assert driver.progress(tmp_path, p, reloaded) == result
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    for name, c in campaigns.items():
        assert replay_campaign(tmp_path/'arms'/name/'campaign', 'blackbox').state == c.state
    one = next(iter(campaigns.values()))
    one.advance(simulation_factory=forbidden_world, generators={'local-bounded-author': author}, count=1)
    with pytest.raises(ValueError, match='budget exceeded'):
        driver.progress(tmp_path, p, campaigns)


def test_proposal_policy_cannot_change_on_reopen(tmp_path):
    p = plan(); driver.make_campaigns(tmp_path, p)
    changed = deepcopy(p)
    changed['campaign_bindings']['throughput-technical-only'].pop('proposal_feedback')
    with pytest.raises(ValueError, match='binding changed'):
        driver.make_campaigns(tmp_path, changed)


def test_main_action_cannot_rerun_or_refresh_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: 'a'*40)
    calls = []
    monkeypatch.setattr(driver, 'execute', lambda args: calls.append(args.action) or 0)
    argv = ['run', '--execute-authorized', '--output', str(tmp_path),
        '--data-cache', str(tmp_path/'unused-cache'),
        '--designer-provider-config', str(tmp_path/'unused-config')]
    assert driver.main(argv) == 0
    before = (tmp_path/'writer.started.json').read_bytes()
    with pytest.raises(ValueError, match='no hidden retry'):
        driver.main(argv)
    assert calls == ['run'] and (tmp_path/'writer.started.json').read_bytes() == before
