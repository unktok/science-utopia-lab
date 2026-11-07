"""Pure driver/real archived-bank QA; no inference, code or native-world call.

Set SCIENCE_UTOPIA_V45_HISTORICAL_AUDIT to the read-only V44 full audit. Tests
explicitly skip when that untracked local artifact is unavailable elsewhere.
"""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

driver = pytest.importorskip('scripts.run_native_warmstart_v45')
from scripts.analyze_native_autonomous_search_v14 import replay_campaign
from scripts.analyze_native_warmstart_v45 import _writer_and_progress
from utopia.optimization.native_initial_evidence import build_initial_evidence
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system
from utopia.utils.data_utils import file_sha256, write_json_atomic


@pytest.fixture(scope='module')
def historical_inputs():
    path = os.environ.get('SCIENCE_UTOPIA_V45_HISTORICAL_AUDIT')
    if not path or not Path(path).is_file():
        pytest.skip('untracked original V44 audit not available; no synthetic research substitute')
    path = Path(path).resolve()
    before = file_sha256(path)
    raw = json.loads(path.read_text())
    bank = build_initial_evidence(raw, expected_audit_content_sha256=driver.HISTORICAL_AUDIT,
        expected_source_commit=driver.HISTORICAL_SOURCE)
    roles = raw['role_bindings']
    result = {'source_commit': 'a' * 40, 'provider_binding': roles['scientist'],
        'designer_provider_binding': roles['designer'],
        'runtime_seed_binding': {'python_hash_seed_environment': '42',
            'python_hash_probe': hash('scienceutopia.native-world.v1')},
        'initial_system': open_native_system(roles['scientist']['image_id']).to_dict(),
        'bank': bank, 'historical_audit_manifest': {'path': str(path), 'file_sha256': before}}
    yield result
    assert file_sha256(path) == before


def test_real_archived_bank_builds_both_exact_loss_bound_empty_campaigns(tmp_path, historical_inputs):
    plan = driver.build_plan(**deepcopy(historical_inputs))
    assert plan['content_sha256'] == digest({k: v for k, v in plan.items() if k != 'content_sha256'})
    assert plan['initial_evidence_sha256'] == driver.INITIAL_BANK
    assert len(historical_inputs['bank']['entries']) == 8
    assert plan['budget']['maximum_new_native_slots'] == 2
    assert plan['budget']['maximum_authoring_POSTs'] == 32
    assert plan['budget']['replacement_policy'] == 'none'
    assert plan['designer']['conversation_profile'] == plan['conversation_profile']
    assert 'loss_spec' not in plan['experiment']
    campaigns = driver.make_campaigns(tmp_path, plan)
    requests = {}
    for name, campaign in campaigns.items():
        assert campaign.binding == plan['campaign_bindings'][name]
        assert campaign.state['records'] == [] and campaign.state['pending'] is None
        reader = replay_campaign(tmp_path / 'arms' / name / 'campaign', 'blackbox')
        assert reader.binding == campaign.binding and reader.state == campaign.state
        request = campaign._request([], campaign._strategy_initial(), 1)
        requests[name] = request
        assert request['history'] == [] and request['count'] == 1
        assert request['world_binding']['source_commit'] == historical_inputs['source_commit']
        assert request['initial_evidence']['source_audit']['source_commit'] == driver.HISTORICAL_SOURCE
        assert not request['initial_evidence']['physical_cache_reuse_allowed']
        assert len(request['observations']) == 7
        assert len(request['initial_evidence']['unobserved_slots']) == 1
        assert request['initial_evidence']['initial_selection']['tied_observation_ids']
    assert requests['efficiency']['selection']['loss'] == pytest.approx(-11.833333333333336)
    assert requests['throughput']['selection']['loss'] == -7.
    assert requests['efficiency']['parent_system'] == requests['throughput']['parent_system']
    assert requests['efficiency']['loss_spec'] != requests['throughput']['loss_spec']
    assert requests['efficiency']['world_binding'] == requests['throughput']['world_binding']


def test_failed_first_arm_does_not_change_other_arm_initial_data_or_refill(tmp_path, historical_inputs):
    plan = driver.build_plan(**deepcopy(historical_inputs))
    campaigns = driver.make_campaigns(tmp_path, plan)
    first, second = campaigns['efficiency'], campaigns['throughput']
    before = second._request([], second._strategy_initial(), 1)
    calls = []
    def generator(request):
        calls.append(request['generation'])
        return {'generation_failure': {'kind': 'SCRIPTED driver accounting; no model dispatch'}}
    def forbidden_world(*args):
        raise AssertionError('driver QA must never construct a native world')
    for name in driver.ARMS:
        campaigns[name].advance(simulation_factory=forbidden_world,
            generators={'local-bounded-author': generator}, count=1)
        if name == 'efficiency':
            assert second._request([], second._strategy_initial(), 1) == before
    assert calls == [0, 0]
    progress = driver.progress(tmp_path, plan, campaigns)
    assert progress['status'] == 'budget-complete-with-failures'
    assert progress['consumed_native_slots'] == 2
    assert progress['counts'] == {'complete': 0, 'technical-failure': 0, 'generation-failure': 2}
    assert all(row['loss'] is None for row in progress['arms'].values())
    restored = driver.make_campaigns(tmp_path, plan)
    assert driver.progress(tmp_path, plan, restored) == progress
    started = {'schema': driver.SCHEMA + '.writer', 'source_commit': plan['source_commit'],
        'action': 'run', 'pid': 123, 'argv': ['SCRIPTED'], 'status': 'started',
        'started_utc': '2000-01-01T00:00:00+00:00', 'environment': {'PYTHONHASHSEED': '42'}}
    write_json_atomic(tmp_path / 'writer.started.json', started)
    write_json_atomic(tmp_path / 'writer.ended.json', {**started, 'status': 'exited',
        'exit_code': 0, 'ended_utc': '2000-01-01T00:00:01+00:00'})
    runs = {name: {'observations': [{'status': 'generation-failure', 'loss': None}]} for name in driver.ARMS}
    assert _writer_and_progress(tmp_path, plan, runs)['progress'] == progress


def test_actual_bank_rehashed_mutation_cannot_enter_this_finite_protocol(historical_inputs):
    args = deepcopy(historical_inputs)
    args['bank']['source_audit']['source_commit'] = 'forged-source'
    args['bank']['content_sha256'] = digest({k: v for k, v in args['bank'].items() if k != 'content_sha256'})
    with pytest.raises(ValueError):
        driver.build_plan(**args)


def test_main_never_reruns_a_previously_dispatched_action(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: 'a' * 40)
    calls = []
    monkeypatch.setattr(driver, 'execute', lambda args: calls.append(args.action) or 0)
    argv = ['run', '--execute-authorized', '--output', str(tmp_path), '--data-cache', str(tmp_path / 'unused'),
        '--designer-provider-config', str(tmp_path / 'unused-config.json'),
        '--historical-audit', str(tmp_path / 'unused-historical.json')]
    assert driver.main(argv) == 0
    before = (tmp_path / 'writer.started.json').read_bytes()
    with pytest.raises(ValueError, match='no hidden retry'):
        driver.main(argv)
    assert calls == ['run']
    assert (tmp_path / 'writer.started.json').read_bytes() == before
