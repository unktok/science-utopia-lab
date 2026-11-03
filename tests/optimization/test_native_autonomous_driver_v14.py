"""Prospective exact pilot-plan tests; no model/native executions."""
from copy import deepcopy

import pytest

from scripts.run_native_autonomous_search_v14 import build_plan
from utopia.system.native_open_examples import open_native_system

SOURCE = 'a' * 40
IMAGE = 'sha256:' + 'b' * 64
PROVIDER = {'model': 'qwen3:8b', 'model_digest': 'c' * 64, 'corpus_sha256': 'd' * 64,
    'corpus_years': 4, 'dataset_identity': {'fixture': 'plan-only-no-worlds'}, 'image_id': IMAGE}


def plan():
    return build_plan(source_commit=SOURCE, initial_system=open_native_system(IMAGE).to_dict(),
        provider_binding=PROVIDER, runtime_seed_binding={'python_hash_seed_environment': '42', 'python_hash_probe': 123})


def test_exact_eight_slot_six_generation_and_twelve_generation_POST_bound():
    value = plan()
    assert value['population'] == {'authors': 5, 'conference_setting': 1}
    assert [r['request']['native_budget'] for r in value['runs']] == [2, 2, 4]
    assert [r['request']['method'] for r in value['runs']] == ['blackbox', 'blackbox', 'nested-lr']
    assert value['designer_budget']['generations'] == 6
    assert value['designer_budget']['max_http_attempts'] == 12
    assert 'POST' in value['designer_budget']['http_budget_means']
    assert all(r['request']['seed'] == 42 and r['request']['years'] == 2 for r in value['runs'])
    assert len({r['directory'] for r in value['runs']}) == 3


def test_exact_existing_loss_specs_no_hidden_veto_or_retrospective_changes():
    value = plan()
    requests = [r['request'] for r in value['runs']]
    assert requests[0]['loss_spec']['id'] == 'native-joint-v5-throughput'
    assert requests[1]['loss_spec'] == requests[2]['loss_spec']
    assert requests[1]['loss_spec']['id'] == 'native-reviewed-production-efficiency-v13'
    assert not value['completion_requires_useful_invention']
    assert all(r['initial_system'] == value['initial_system'] for r in requests)


def test_source_binding_is_not_an_unpinned_short_alias():
    with pytest.raises(ValueError, match='source'):
        build_plan(source_commit='main', initial_system=open_native_system(IMAGE).to_dict(),
            provider_binding=PROVIDER, runtime_seed_binding={})
