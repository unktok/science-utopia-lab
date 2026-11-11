"""Instrument QA; scripted scores are never new scientific quality evidence."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.common_content_observer import (
    CommonContentObserver, ObserverCompletionUnknown, content, decode_rating,
    make_contract, request_for,
)

PROVIDER = {'model': 'SCRIPTED-critic', 'model_digest': 'SCRIPTED-weights'}
PAPER = {'id': 'SCRIPTED-paper', 'title': 'A falsifiable test',
    'abstract': 'We describe a measured comparison and its limitations.', 'topics': ['test']}


def contract(*, maximum_posts=12, critics=3):
    return make_contract(source_commit='a' * 40, provider=PROVIDER,
        backend={**PROVIDER, 'ollama_version': 'SCRIPTED-version'},
        maximum_posts=maximum_posts, critics=critics)


def envelope(answer=None, *, done=True, reason='stop', counts=True):
    value = {'model': PROVIDER['model'], 'done': done, 'done_reason': reason,
        'message': {'content': json.dumps(answer if answer is not None else {'score': 4, 'rationale': 'SCRIPTED test'})}}
    if counts:
        value.update(prompt_eval_count=71, eval_count=9)
    return {'http_status': 200, 'raw_http_response': json.dumps(value)}


class Backend:
    def __init__(self, responses=None):
        self.responses = iter(responses) if responses is not None else None
        self.calls = []; self.checks = 0

    def verify(self, spec):
        self.checks += 1

    def __call__(self, wire, timeout):
        self.calls.append((wire, timeout))
        value = next(self.responses) if self.responses is not None else envelope()
        if isinstance(value, BaseException):
            raise value
        return value


def test_same_content_uses_exact_requests_and_cached_responses_across_policy_labels(tmp_path):
    backend = Backend(); observer = CommonContentObserver(tmp_path, contract(), backend=backend)
    a = observer.rate({**PAPER, 'policy': 'all accept', 'decision': 'accept', 'author_id': 'secret'})
    b = observer.rate({**PAPER, 'id': 'other ID', 'policy': 'all reject', 'decision': 'reject', 'author_id': 'other'})
    assert a == b and a['mean_score'] == 4
    assert len(backend.calls) == backend.checks == 3
    for wire, timeout in backend.calls:
        request = json.loads(wire)
        assert timeout == [10, 120] and not request['truncate'] and not request['shift']
        assert json.loads(request['messages'][1]['content']) == content(PAPER)
        assert 'secret' not in wire and 'all accept' not in wire and 'SCRIPTED-paper' not in wire
    cold_backend = Backend()
    cold = CommonContentObserver(tmp_path, contract(), backend=cold_backend).rate(PAPER)
    assert cold == a and not cold_backend.calls


def test_operational_source_budget_and_panel_size_do_not_change_an_existing_critic_input():
    a = contract(maximum_posts=3, critics=1)
    b = make_contract(source_commit='b' * 40, provider=PROVIDER,
        backend={**PROVIDER, 'ollama_version': 'SCRIPTED-version'}, maximum_posts=999, critics=5)
    assert a['content_sha256'] != b['content_sha256']
    assert request_for(a, PAPER, 0) == request_for(b, PAPER, 0)


@pytest.mark.parametrize('answer', [
    {'score': True, 'rationale': 'x'}, {'score': 4.0, 'rationale': 'x'},
    {'score': 6, 'rationale': 'x'}, {'score': 0, 'rationale': 'x'},
    {'score': 4, 'rationale': ''}, {'score': 4, 'rationale': 'x', 'quality': 100},
])
def test_invalid_known_final_scores_are_missing_not_repaired_or_penalized(tmp_path, answer):
    backend = Backend([envelope(answer), envelope(), envelope()])
    observer = CommonContentObserver(tmp_path, contract(), backend=backend)
    result = observer.rate(PAPER)
    assert result['status'] == 'unavailable' and result['mean_score'] is None
    assert result['ratings'][0] is None and len(backend.calls) == 3
    assert observer.rate(PAPER) == result and len(backend.calls) == 3


@pytest.mark.parametrize('response', [
    envelope(done=False), {'http_status': 200, 'raw_http_response': '<not final JSON>'},
    TimeoutError('SCRIPTED timeout'),
])
def test_unknown_completion_stops_the_panel_and_all_later_dispatch(tmp_path, response):
    backend = Backend([response]); observer = CommonContentObserver(tmp_path, contract(), backend=backend)
    with pytest.raises(ObserverCompletionUnknown):
        observer.rate(PAPER)
    assert len(backend.calls) == 1
    with pytest.raises(ObserverCompletionUnknown):
        observer.rate({**PAPER, 'title': 'another content'})
    assert len(backend.calls) == 1


def test_unknown_token_counts_remain_unknown_and_length_is_a_known_failure(tmp_path):
    backend = Backend([envelope(counts=False, reason='length'), envelope(), envelope()])
    observer = CommonContentObserver(tmp_path, contract(), backend=backend)
    assert observer.rate(PAPER)['mean_score'] is None
    records = [json.loads(p.read_text()) for p in (tmp_path / 'requests').glob('*.result.json')]
    failed, = [r for r in records if r['status'] == 'failed']
    assert failed['prompt_tokens'] is failed['output_tokens'] is None
    assert len(backend.calls) == 3  # other critics, never a retry of the failed draw


def test_physical_budget_counts_every_attempt_and_does_not_refill(tmp_path):
    backend = Backend(); observer = CommonContentObserver(tmp_path, contract(maximum_posts=2), backend=backend)
    with pytest.raises(ValueError, match='budget exhausted'):
        observer.rate(PAPER)
    assert len(backend.calls) == 2
    with pytest.raises(ValueError, match='budget exhausted'):
        observer.rate(PAPER)
    assert len(backend.calls) == 2


def test_no_truncation_rubric_changes_cache_reuse_or_implicit_content_defaults(tmp_path):
    with pytest.raises(ValueError, match='no truncation'):
        request_for(contract(), {**PAPER, 'abstract': 'long scientific content ' * 4000}, 0)
    with pytest.raises(KeyError):
        content({'title': 'no abstract'})
    spec = contract(); spec['rubric'] = 'edited'
    from utopia.system.design_patch import digest
    spec['content_sha256'] = digest({k: v for k, v in spec.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='rubric'):
        CommonContentObserver(tmp_path, spec, backend=Backend())


def test_adapter_measures_original_decisions_and_never_mutates_native_state(tmp_path):
    from tests.optimization.test_native_world import loss_spec
    from utopia.optimization.loss import evaluate_loss
    observer = CommonContentObserver(tmp_path, contract(), backend=Backend())
    row = {**PAPER, 'review_history': [{'year': 1, 'decision': 'accept'}, {'year': 2, 'decision': 'accept'}]}
    paper = SimpleNamespace(**row, to_dict=lambda: deepcopy(row))
    sim = SimpleNamespace(num_years=2, native_system=SimpleNamespace(last_year=2,
        spec=SimpleNamespace(fingerprint='SCRIPTED-system')),
        paper_tracker=SimpleNamespace(papers_by_id={paper.id: paper}))
    base = {'run_id': 'SCRIPTED-run', 'system_fingerprint': 'SCRIPTED-system',
        'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': 2},
            'native.review_records': {'status': 'measured', 'value': 77}}}
    before = deepcopy(base); result = observer.measure(sim, base)
    assert base == before and paper.to_dict() == row
    assert result['metrics']['native.common_content_score_sum']['value'] == 8
    assert result['metrics']['native.common_content_utility_sum']['value'] == 2
    assert result['common_content_observer']['unique_contents'] == 1
    loss = evaluate_loss(loss_spec('native.common_content_utility_sum'), [result])
    assert loss['status'] == 'complete' and loss['loss'] == -2


def test_empty_acceptance_is_measured_empty_sum_without_inference(tmp_path):
    backend = Backend(); observer = CommonContentObserver(tmp_path, contract(), backend=backend)
    sim = SimpleNamespace(num_years=2, native_system=SimpleNamespace(last_year=2,
        spec=SimpleNamespace(fingerprint='x')),
        paper_tracker=SimpleNamespace(papers_by_id={}))
    base = {'run_id': 'SCRIPTED-empty', 'system_fingerprint': 'x',
        'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': 0}}}
    result = observer.measure(sim, base)
    assert result['metrics']['native.common_content_utility_sum']['value'] == 0
    assert not backend.calls


def test_observer_audit_counts_physical_costs_not_cached_uses(tmp_path):
    backend = Backend(); observer = CommonContentObserver(tmp_path, contract(), backend=backend)
    observer.rate(PAPER); observer.rate({**PAPER, 'policy': 'another label'})
    audit = observer.audit()
    assert audit['dispatch_intents'] == audit['known_terminal_attempts'] == audit['measured_ratings'] == 3
    assert audit['usage']['prompt_tokens'] == {'known_sum': 213, 'unknown_attempts': 0}
    assert audit['usage']['output_tokens'] == {'known_sum': 27, 'unknown_attempts': 0}
    assert audit['next_inference_allowed'] and audit['new_model_calls'] == 0
    assert len(backend.calls) == 3


def test_audit_retains_unknown_without_filling_or_dispatching(tmp_path):
    backend = Backend([TimeoutError('SCRIPTED timeout')])
    observer = CommonContentObserver(tmp_path, contract(), backend=backend)
    with pytest.raises(ObserverCompletionUnknown):
        observer.rate(PAPER)
    report = observer.audit()
    assert report['dispatch_intents'] == 1 and report['known_terminal_attempts'] == 0
    assert report['usage']['output_tokens']['unknown_attempts'] == 1
    assert not report['next_inference_allowed'] and len(backend.calls) == 1


def test_audit_rejects_orphan_response_omission(tmp_path):
    observer = CommonContentObserver(tmp_path, contract(), backend=Backend())
    observer.rate(PAPER)
    (tmp_path / 'requests' / 'orphan.http.json').write_text('{}')
    with pytest.raises(ValueError, match='orphan'):
        observer.audit()


@pytest.mark.parametrize('field', ['status', 'prompt_tokens', 'rating'])
def test_cold_replay_reconstructs_even_resealed_status_and_cost_from_raw(tmp_path, field):
    from utopia.system.design_patch import digest
    observer = CommonContentObserver(tmp_path, contract(), backend=Backend())
    observer.rate(PAPER)
    path = next((tmp_path / 'requests').glob('*.result.json'))
    result = json.loads(path.read_text())
    if field == 'status':
        result['status'] = 'failed'; result['rating'] = None
    elif field == 'prompt_tokens':
        result['prompt_tokens'] = 999999
    else:
        result['rating']['score'] = 1
    result['content_sha256'] = digest({k: v for k, v in result.items() if k != 'content_sha256'})
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match='status/rating/cost'):
        observer.rate(PAPER)


@pytest.mark.parametrize('post_budget', [12, 72])
def test_actual_original_world_can_optimize_the_optional_criterion(tmp_path, fixed_corpus, post_budget):
    from tests.runtime.test_portable_checkpoint_integration import seed
    from tests.system.test_native_science_kernel import make_sim
    from tests.optimization.test_native_world import loss_spec
    from utopia.optimization.blackbox import Suggestion
    from utopia.optimization.native_world import evaluate_native_suggestion
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    # Four scripted authors x six years x three critics is a finite sufficient
    # fixture ceiling. The smaller case must retain an unavailable criterion.
    backend = Backend(); observer = CommonContentObserver(tmp_path / 'observer', contract(maximum_posts=post_budget), backend=backend)
    def factory(spec, world_seed, run_id):
        seed()
        return make_sim(tmp_path / run_id, native=NativeScienceKernel(spec))[0]
    spec = legacy_world_system()
    result = evaluate_native_suggestion(Suggestion('SCRIPTED-observer-native', spec.to_dict(), 0, 'QA'),
        seeds=[42], simulation_factory=factory, loss_spec=loss_spec('native.common_content_utility_sum'),
        measurement_adapter=observer.measure)
    if post_budget == 12:
        assert result.status == 'failed' and result.loss is None
        assert len(backend.calls) == 12 and len(result.metadata['runs']) == 1
        assert 'budget exhausted' in result.metadata['technical_failures'][0]['error']
        return
    assert result.status == 'complete', result.metadata['technical_failures']
    assert result.loss < 0
    measurement, = result.metadata['measurements']
    count = measurement['metrics']['native.accepted_decisions']['value']
    assert result.loss == -count
    assert measurement['common_content_observer']['new_native_worlds'] == 0
    assert backend.calls and len(backend.calls) % 3 == 0


def test_measurement_extension_cannot_overwrite_native_counts_or_identity(tmp_path, fixed_corpus):
    from tests.runtime.test_portable_checkpoint_integration import seed
    from tests.system.test_native_science_kernel import make_sim
    from tests.optimization.test_native_world import loss_spec
    from utopia.optimization.blackbox import Suggestion
    from utopia.optimization.native_world import evaluate_native_suggestion
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    def factory(spec, world_seed, run_id):
        seed()
        return make_sim(tmp_path / run_id, native=NativeScienceKernel(spec))[0]
    def bad_extension(simulation, measurement):
        measurement['metrics']['native.accepted_decisions']['value'] = 1000000
        return measurement
    result = evaluate_native_suggestion(Suggestion('SCRIPTED-overwrite', legacy_world_system().to_dict(), 0, 'QA'),
        seeds=[42], simulation_factory=factory, loss_spec=loss_spec(), measurement_adapter=bad_extension)
    assert result.status == 'failed' and result.loss is None
    assert not result.metadata['measurements']
    assert len(result.metadata['runs']) == 1  # actual completed native world still retained
    assert 'retain every native measurement' in result.metadata['technical_failures'][0]['error']
