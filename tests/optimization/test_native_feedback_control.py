"""Proposal noninterference/software QA; synthetic numbers are not research."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_adaptive_search import (
    create, fail_factory, tiny_parent, PROVENANCE, loss_spec, STRATEGIES,
)
from tests.optimization.test_native_bounded_author_context_v45 import frame
from utopia.optimization.native_bounded_author_context_v45 import archive_entries
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_feedback_control import technical_history
from utopia.optimization.native_file_workspace_v35 import file_catalog
from utopia.optimization.native_staged_author_v15 import initial_draft, transition
from utopia.system.design_patch import digest, make_patch
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


def definition(value):
    return {'base_patch': make_patch(tiny_parent(), [{'op': 'replace',
        'path': '/initial_state/coordinate', 'value': value}]),
        'factors': [], 'continuous': [], 'provenance': PROVENANCE}


def synthetic_record(campaign, *, previous=(), value=1., cost=-2.):
    request = campaign._request(list(previous), campaign._strategy_initial(), 1)
    authored = definition(value)
    record = {'request': request, 'request_sha256': digest(request),
        'version_sha256': digest({'request': digest(request), 'definition': authored}),
        'definition': authored, 'generation_error': None}
    _, draws = campaign._compile(record)
    record.update(draws=draws, observations=[{'observation_id': 'raw-measured-id',
        'status': 'complete', 'loss': cost, 'metadata': {'measurements': [{'cost': cost}],
            'runs': [{'raw': 'loss-derived-output'}], 'technical_failures': []}}],
        report={'strategy_after': {'logits': [cost, -cost]}, 'loss': cost})
    return record


def campaign(path, **kwargs):
    return create(path, mode='blackbox', proposal_feedback='technical-only', **kwargs)


def test_default_constructor_preserves_exact_legacy_bindings_and_requests(tmp_path):
    default = create(tmp_path/'default', mode='blackbox')
    explicit = create(tmp_path/'explicit', mode='blackbox', proposal_feedback='loss')
    assert 'proposal_feedback' not in default.binding
    assert default.binding == explicit.binding
    assert default._request([], default._strategy_initial(), 1) == explicit._request(
        [], explicit._strategy_initial(), 1)


@pytest.mark.parametrize('kwargs', [dict(mode='score'), dict(mode='hybrid'),
    dict(initial_evidence={}), dict(expectation_estimator={}), dict(proposal_feedback='unknown')])
def test_rejects_unimplemented_or_ambiguous_control_combinations(tmp_path, kwargs):
    args = dict(mode='blackbox', proposal_feedback='technical-only')
    args.update(kwargs)
    with pytest.raises(ValueError, match='technical-only'):
        create(tmp_path, **args)
    assert not (tmp_path/'native-adaptive-state.json').exists()


def test_measured_values_raw_ids_reports_and_error_text_cannot_change_request(tmp_path):
    c = campaign(tmp_path)
    records = [synthetic_record(c, value=1., cost=-2.), synthetic_record(c, value=2., cost=9.)]
    records[1]['observations'][0].update(status='failed', loss=None)
    records[1]['observations'][0]['metadata']['technical_failures'] = [
        {'error_type': 'ValueError', 'error': 'raw secret quality=9', 'loss': None}]
    before = deepcopy(records)
    expected = c._request(records, c._strategy_initial(), 1)
    changed = deepcopy(records)
    for r in changed:
        r['request_sha256'] = 'secret-dependent-request-hash'
        r['version_sha256'] = 'secret-dependent-version-hash'
        r['report'] = {'strategy_after': {'logits': [1000., -1000.]}, 'best': 99.}
        o = r['observations'][0]
        o['observation_id'] = 'a-different-measured-world'
        if o['status'] == 'complete':
            o['loss'] = 1234567.
        o['metadata'].update(measurements=[{'cost': 1234567.}], runs=['secret output'])
        for error in o['metadata']['technical_failures']:
            error['error'] = 'another secret quality=1234567'
    # All displayed strategy state, selection and digest fields must obey the
    # same noninterference contract, not merely a list of stripped loss keys.
    altered_strategy = {'logits': [100., -100.], 'statistics': {'secret': 1234567.}}
    assert c._request(changed, altered_strategy, 1) == expected
    assert records == before
    assert expected['parent_system'] == c.initial.to_dict()
    assert expected['based_on_observation_id'] is None and 'selection' not in expected
    assert expected['strategy_probabilities'] == [.5, .5]
    assert [w['observation']['status'] for w in expected['observations']] == ['complete', 'failed']
    assert '1234567' not in json.dumps(expected)
    assert 'raw secret' not in json.dumps(expected)
    assert expected['history'][0]['identities_are_projected_not_raw_evidence']


def test_loss_feedback_parent_really_changes_while_control_parent_is_fixed(tmp_path):
    full = create(tmp_path/'full', mode='blackbox', proposal_feedback='matched-loss')
    blind = campaign(tmp_path/'blind')
    records = [synthetic_record(full, value=1., cost=-2.), synthetic_record(full, value=2., cost=9.)]
    before = full._request(records, full._strategy_initial(), 1)
    changed = deepcopy(records)
    changed[1]['observations'][0]['loss'] = -10.
    after = full._request(changed, full._strategy_initial(), 1)
    assert before['parent_system'] != after['parent_system']
    assert blind._request(records, blind._strategy_initial(), 1) == blind._request(
        changed, blind._strategy_initial(), 1)


def test_matched_loss_arm_uses_same_technical_error_channel_but_preserves_losses(tmp_path):
    full = create(tmp_path/'full', mode='blackbox', proposal_feedback='matched-loss')
    blind = campaign(tmp_path/'blind')
    record = synthetic_record(full)
    record['observations'][0]['metadata']['technical_failures'] = [
        {'error_type':'ValueError','error':'private native output','loss':None}]
    record['generation_error'] = {'type':'SyntaxError','message':'private compiler output','loss':None}
    before = deepcopy(record)
    a = full._request([record], full._strategy_initial(), 1)
    b = blind._request([record], blind._strategy_initial(), 1)
    assert a['observations'][0]['observation']['loss'] == -2.
    assert 'loss' not in b['observations'][0]['observation']
    assert a['observations'][0]['observation']['metadata']['technical_failures'] == b[
        'observations'][0]['observation']['metadata']['technical_failures']
    assert a['history'][0]['generation_error'] == b['history'][0]['generation_error']
    assert 'private native output' not in json.dumps(a)
    assert 'private compiler output' not in json.dumps(a)
    assert record == before


def test_actual_prompt_and_all_virtual_archives_expose_only_control_view(tmp_path):
    c = campaign(tmp_path)
    original = synthetic_record(c)
    modified = deepcopy(original)
    modified['observations'][0]['loss'] = -987654321.
    modified['observations'][0]['metadata']['measurements'] = ['PRIVATE-MEASURED-OUTPUT']
    a = c._request([original], c._strategy_initial(), 1)
    b = c._request([modified], c._strategy_initial(), 1)
    state = initial_draft(a)
    assert frame(a, state, []) == frame(b, initial_draft(b), [])
    assert archive_entries(a, []) == archive_entries(b, [])
    assert file_catalog(state['document'], request=a, conversation_profile=BOUNDED_AUTHORING) == file_catalog(
        state['document'], request=b, conversation_profile=BOUNDED_AUTHORING)
    chunks = []
    rendered = json.dumps(a, ensure_ascii=False, sort_keys=True, indent=2)
    for offset in range(0, len(rendered), 30000):
        _, receipt = transition(state, {'tool': 'read_file', 'filename': 'archive/request.json',
            'offset': offset, 'limit': 30000}, a,
            binding_sha256='d'*64, provider_binding={'image_id': 'sha256:'+'a'*64},
            conversation_profile=BOUNDED_AUTHORING)
        assert receipt['ok'] and 'PRIVATE-MEASURED-OUTPUT' not in json.dumps(receipt)
        chunks.append(receipt['result']['value'])
    assert json.loads(''.join(chunks)) == a
    active = json.loads(frame(a, state, [])[0])
    assert active['proposal_feedback_policy']['name'] == 'technical-only'
    assert active['own_observations'][0]['loss_withheld'] is True
    assert 'loss' not in active['own_observations'][0]


def test_internal_losses_stay_literal_but_strategy_never_updates(tmp_path):
    c = campaign(tmp_path)
    record = synthetic_record(c)
    report = c._finish(record, c._strategy_initial())
    assert report['mixed']['losses'] == [-2.]
    assert report['strategy_before'] == report['strategy_after'] == c._strategy_initial()
    assert report['mixed']['gradient'] is None
    assert record['observations'][0]['loss'] == -2.


def test_generation_failure_projection_and_ordinal_candidate_order(tmp_path):
    c = campaign(tmp_path)
    bad = {'definition': {'generation_failure': {'kind': 'SCRIPTED author QA'}},
        'generation_error': {'type': 'ValueError', 'message': 'hidden full error', 'loss': None},
        'draws': [], 'observations': []}
    records = [bad, synthetic_record(c, previous=[bad], value=1.),
        synthetic_record(c, previous=[bad], value=2.)]
    history, observations = technical_history(records)
    assert history[0]['generation_error'] == {'type': 'ValueError',
        'message_withheld': True, 'loss_withheld': True}
    assert [r['suggestion']['candidate']['initial_state']['coordinate'] for r in observations] == [1., 2.]
    assert [r['suggestion']['proposal_index'] for r in observations] == [0, 1]
    assert 'hidden full error' not in json.dumps(history)


def test_failed_native_attempts_reopen_and_read_only_replay_without_refilling(tmp_path):
    c = campaign(tmp_path)
    seen = []
    def author(request):
        seen.append(deepcopy(request))
        return definition(1.)
    generators = {key: author for key in c.binding['strategies']}
    for _ in range(2):
        c.advance(simulation_factory=fail_factory, generators=generators, count=1)
        c = campaign(tmp_path)
    assert len(c.state['records']) == 2 and len(seen) == 2
    assert all(r['observations'][0]['loss'] is None for r in c.state['records'])
    assert len(seen[1]['history']) == 1
    assert seen[1]['history'][0]['observations'][0]['loss_withheld']
    assert all('loss' not in r for r in seen[1]['history'][0]['observations'])
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    assert replay_campaign(tmp_path, 'blackbox').state == c.state
    with pytest.raises(ValueError, match='binding changed'):
        create(tmp_path, mode='blackbox')


def test_successful_original_native_world_keeps_true_losses_private_across_generations(
        tmp_path, fixed_corpus, monkeypatch):
    # Full original six-year phases/checkpoints, with only corpus and scholar
    # HTTP scripted by the existing fixture. This is NOT a model experiment.
    from tests.runtime import test_portable_checkpoint_integration as fixture
    from tests.system.test_native_science_kernel import make_sim
    from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
    from utopia.system.native_kernel import NativeScienceKernel
    world = {'source_commit':'SCRIPTED-control-native-QA',
        'model_digest':fixture.BINDING['model_revision'],
        'corpus_sha256':fixture.BINDING['corpus_sha256']}
    def reopen():
        return NativeAdaptiveDesignCampaign(tmp_path/'campaign',initial_system=tiny_parent(),
            loss_spec=loss_spec(),seeds=[42],world_binding=world,strategies=STRATEGIES,
            mode='blackbox',proposal_feedback='technical-only')
    physical,seen=[],[]
    def factory(spec,seed,run_id):
        fixture.seed();physical.append(run_id)
        monkeypatch.setitem(fixture.BINDING,'cell',spec.fingerprint)
        monkeypatch.setitem(fixture.BINDING,'science_config',{
            **fixture.BINDING['science_config'],'source_commit':world['source_commit']})
        sim,_=make_sim(tmp_path/'runs'/run_id,native=NativeScienceKernel(spec))
        return sim
    def author(request):
        seen.append(deepcopy(request))
        return definition(request['generation']+1.)
    for _ in range(2):
        c=reopen()
        r=c.advance(simulation_factory=factory,generators={key:author for key in STRATEGIES},count=1)
        assert r['observations'][0]['status']=='complete'
        assert isinstance(r['observations'][0]['loss'],float)
        assert r['observations'][0]['metadata']['measurements']
    assert len(physical)==len(set(physical))==len(seen)==2
    assert seen[1]['parent_system']==tiny_parent().to_dict()
    assert seen[1]['history'][0]['observations'][0]['loss_withheld']
    assert 'loss' not in seen[1]['observations'][0]['observation']
    assert reopen().state==c.state
