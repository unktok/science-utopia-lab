"""SCRIPTED access/collector/editor checks, not a scientific information effect."""
from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from tests.optimization.test_native_authoring_ir import BINDING, request as editor_request
from tests.optimization.test_native_bounded_author_context_v45 import Model
from tests.optimization.test_native_trajectory_projection_v1 import fixture
from utopia.optimization import native_trajectory_columnar_v1 as codec
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_longitudinal_feedback_v1 import (
    KEY, VIEW, active_view, attach_projection, contract, measurement_adapter, request_view,
)
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator, replay_staged_generation
from utopia.optimization.native_trajectory_projection_v1 import project_checkpoint
from utopia.runtime.checkpointing import write_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest


@pytest.fixture(autouse=True)
def no_network_or_generated_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('longitudinal checks must not execute models or generated code')
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


def inputs(tmp_path):
    state, kw = fixture(tmp_path)
    projection = project_checkpoint(state, **kw)
    policy = clone(state['native_system']['spec'])
    fingerprint = SystemSpec.from_dict(policy).fingerprint
    def pair(name):
        run = {'run_id': name + '-s11', 'seed': 11, 'system_fingerprint': fingerprint,
            'checkpoint_sha256': kw['checkpoint_file_sha256']}
        measurement = {'run_id': run['run_id'], 'system_fingerprint': fingerprint,
            'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': 1}}}
        observation = {'observation_id': 'observation-' + name, 'suggestion_id': name,
            'candidate': clone(policy), 'status': 'complete', 'loss': -1.,
            'metadata': {'world_backend': 'native-research-world', 'technical_failures': [],
                'measurements': [attach_projection(measurement, projection, run=run)], 'runs': [run]}}
        suggestion = {'suggestion_id': name, 'candidate': clone(policy), 'generation': 0,
            'source': 'SCRIPTED'}
        return {'suggestion': suggestion, 'observation': observation}
    reference, own = pair('reference-R7'), pair('own-0')
    body = editor_request()
    body.update(parent_system=policy, observations=[reference, own],
        based_on_observation_id=own['observation']['observation_id'],
        world_binding={'source_commit': kw['source_commit'], 'model_digest': 'SCRIPTED',
            'corpus_sha256': 'SCRIPTED'}, history=[{'observations': [clone(own['observation'])]}])
    return body, state, kw


def access(mode, kw):
    return contract(mode, source_commit=kw['source_commit'], seeds=[11], reference_ids=['reference-R7'])


def project(body, policy):
    return request_view(body, policy, reference_observation_ids=['observation-reference-R7'])


def test_scalar_view_hides_bodies_in_both_observations_and_exact_history_archive(tmp_path):
    body, _, kw = inputs(tmp_path); before = deepcopy(body)
    value = project(body, access('scalar', kw))
    assert body == before
    assert value[VIEW]['active_parent'] == value[VIEW]['archive_items'] == []
    for row in value['observations']:
        assert KEY not in row['observation']['metadata']['measurements'][0]
        assert row['observation']['loss'] == -1.
    assert KEY not in value['history'][0]['observations'][0]['metadata']['measurements'][0]
    from utopia.optimization.native_bounded_author_context_v45 import archive_entries
    archived = archive_entries(value, [])['archive/request.json']['value']
    assert archived == value and 'native-trajectory-projection.v1.columnar' not in json.dumps(archived)
    assert not active_view(value)['active_parent']


def test_trace_keeps_all_allowed_archived_records_but_only_parent_inline(tmp_path):
    body, _, kw = inputs(tmp_path); before = deepcopy(body)
    value = project(body, access('parent-trajectory', kw))
    view = value[VIEW]
    assert len(view['archive_items']) == 2 and len(view['active_parent']) == 1
    assert view['active_parent'][0]['observation_id'] == body['based_on_observation_id']
    assert view['active_parent'][0]['columnar'] == before['observations'][1]['observation']['metadata']['measurements'][0][KEY]
    assert active_view(value)['active_parent'] == view['active_parent']
    assert body == before and not view['context_token_capacity_proved']
    assert not view['causal_advice_or_candidate_policy_supplied']


@pytest.mark.parametrize('change', ['seed', 'source', 'policy', 'checkpoint', 'missing',
    'other-channel', 'unknown-reference', 'wrong-parent', 'missing-parent', 'duplicate-measurement'])
def test_missing_unauthorized_or_changed_evidence_is_not_repaired(tmp_path, change):
    body, _, kw = inputs(tmp_path); policy = access('parent-trajectory', kw)
    row = body['observations'][0]['observation']['metadata']['measurements'][0]
    if change in ('seed', 'source', 'policy', 'checkpoint'):
        view = codec.decode(row[KEY])
        field, replacement = {'seed': ('seed', 99), 'source': ('source_commit', 'other'),
            'policy': ('system_fingerprint', 'other'), 'checkpoint': ('checkpoint_file_sha256', 'f'*64)}[change]
        view[field] = replacement; view.pop('content_sha256'); view['content_sha256'] = digest(view)
        row[KEY] = codec.encode(view)
    elif change == 'missing': row.pop(KEY)
    elif change == 'other-channel': body['undeclared_bank'] = {KEY: row[KEY]}
    elif change == 'unknown-reference':
        policy = contract('parent-trajectory', source_commit=kw['source_commit'], seeds=[11], reference_ids=[])
    elif change == 'wrong-parent': body['parent_system']['metadata']['SCRIPTED-change'] = True
    elif change == 'missing-parent': body['based_on_observation_id'] = 'absent'
    else: body['observations'][0]['observation']['metadata']['measurements'].append(clone(row))
    before = deepcopy(body)
    with pytest.raises(ValueError): project(body, policy)
    assert body == before


@pytest.mark.parametrize('change', ['boolean-seed', 'wrong-source-binding', 'unknown-mode', 'truncate', 'extra-field'])
def test_access_contract_changes_are_not_silently_normalized(tmp_path, change):
    _, _, kw = inputs(tmp_path); value = access('scalar', kw)
    from utopia.optimization.native_longitudinal_feedback_v1 import validate_contract
    if change == 'boolean-seed': value['seeds'] = [True]
    elif change == 'wrong-source-binding': value['component_sources']['access'] = '0'*64
    elif change == 'unknown-mode': value['mode'] = 'choose-a-favorable-trace'
    elif change == 'truncate': value['automatic_truncation'] = True
    else: value['candidate_policy'] = 'unrequested'
    value.pop('content_sha256'); value['content_sha256'] = digest(value)
    before = clone(value)
    with pytest.raises(ValueError): validate_contract(value)
    assert value == before


def test_arbitrary_institution_field_names_and_literal_source_are_not_a_new_veto(tmp_path):
    body, _, kw = inputs(tmp_path)
    body['parent_system']['metadata'][KEY] = {'ordinary_authored_value': 'not measurement evidence'}
    for wrapped in body['observations']:
        wrapped['suggestion']['candidate']['metadata'][KEY] = {'ordinary_authored_value': 'not measurement evidence'}
        wrapped['observation']['candidate']['metadata'][KEY] = {'ordinary_authored_value': 'not measurement evidence'}
    # Rebinding a policy invalidates a genuine old projection; test the
    # arbitrary field exemption separately on a no-observation initial draft.
    body['observations'] = []; body['history'] = []; body['based_on_observation_id'] = None
    value = project(body, access('scalar', kw))
    assert value['parent_system'] == body['parent_system']


def test_real_checkpoint_collector_attaches_only_literal_extra_metadata(tmp_path):
    body, state, kw = inputs(tmp_path)
    directory = tmp_path/'checkpoint'; directory.mkdir()
    path = directory/'portable_checkpoint_year_2.json.gz'; write_portable_checkpoint(path, state)
    sim = SimpleNamespace(output_dir=directory, num_years=2, args=SimpleNamespace(seed=11))
    base = clone(body['observations'][0]['observation']['metadata']['measurements'][0]); base.pop(KEY)
    before = deepcopy(base)
    collect = measurement_adapter(lambda sim, base: base, source_commit=kw['source_commit'], years=2)
    result = collect(sim, base)
    assert {k: v for k, v in result.items() if k != KEY} == before and base == before
    view = codec.decode(result[KEY])
    assert view['annual'][0]['authors'][0]['closing_balance'] == 3.
    assert view['annual'][1]['authors'][0]['closing_balance'] == 5.


@pytest.mark.parametrize('mode', ['scalar', 'parent-trajectory'])
def test_actual_bounded_editor_and_cold_replay_keep_the_selected_access_view(tmp_path, mode):
    body, _, kw = inputs(tmp_path); body = project(body, access(mode, kw))
    images = {node['parameters']['runtime_image_id'] for node in body['parent_system']['mechanisms']
        if node['implementation'] == 'code.python.v1'}
    assert len(images) == 1
    image = next(iter(images)); provider = {**BINDING, 'image_id': image}
    model = Model([{'tool': 'plan', 'objective_reasoning': 'SCRIPTED access check',
        'design_intent': 'Explicitly retain the parent'}, {'tool': 'finish'}])
    generator = StagedVocabularyGenerator(model, tmp_path/'author', image_id=image,
        provider_binding=provider, max_steps=8, max_tokens=8192, conversation_profile=BOUNDED_AUTHORING)
    result = generator(body)
    assert 'generation_failure' not in result, result.get('generation_failure')
    assert len(model.calls) == 2
    for call in model.calls:
        visible = json.loads(call['prompt'])[VIEW]
        assert visible['access_contract']['mode'] == mode
        assert bool(visible['active_parent']) == (mode == 'parent-trajectory')
    cell = next((tmp_path/'author').glob('generation-*'))
    assert replay_staged_generation(cell, expected_provider_binding=provider) == result
    assert len(model.calls) == 2


@pytest.mark.parametrize('mode', ['scalar', 'parent-trajectory'])
def test_campaign_request_assembler_uses_opt_in_view_without_changing_raw_records(tmp_path, mode):
    body, _, kw = inputs(tmp_path)
    # Own-only fixture: source-bound reference-bank authorization is separately
    # handled by the real campaign's existing development-reference validator.
    body['observations'] = body['observations'][1:]
    own = body['observations'][0]
    options = dict(initial_system=SystemSpec.from_dict(body['parent_system']),
        loss_spec=body['loss_spec'], seeds=[11], world_binding=body['world_binding'],
        strategies={'SCRIPTED': {'kind': 'SCRIPTED'}}, mode='blackbox')
    policy = contract(mode, source_commit=kw['source_commit'], seeds=[11], reference_ids=[])
    campaign = NativeAdaptiveDesignCampaign(tmp_path/'access-campaign', **options, longitudinal_access=policy)
    record = {'request_sha256': 'a'*64, 'version_sha256': 'b'*64, 'definition': {},
        'generation_error': None, 'draws': [{'suggestion': own['suggestion']}],
        'observations': [own['observation']], 'report': {}}
    records = [record]; before = deepcopy(records)
    result = campaign._request(records, campaign._strategy_initial(), 1)
    assert records == before and result[VIEW]['access_contract'] == policy
    assert result['parent_system'] == own['suggestion']['candidate']
    assert result['observations'][0]['observation']['loss'] == -1.
    legacy = NativeAdaptiveDesignCampaign(tmp_path/'legacy-campaign', **options)
    original = legacy._request(records, legacy._strategy_initial(), 1)
    assert VIEW not in original and KEY in original['observations'][0]['observation']['metadata']['measurements'][0]
