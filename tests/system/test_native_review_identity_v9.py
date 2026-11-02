"""Observational review capture with tiny fake actors, not native/model runs."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from utopia.system.native_review_identity import enable_review_identity_recording, capture_native_review_tasks
from utopia.system.runtime import GraphRuntimeError


class Actor:
    def __init__(self, identity):
        self.id = identity

    def get_review_prompt(self, paper, **kwargs):
        return f'ORIGINAL PROMPT {self.id} {paper["id"]}', {'original': 'schema'}


def observer_fixture():
    actors = [Actor('reviewer-a'), Actor('reviewer-b')]
    calls = []
    def original(prompts, **kwargs):
        calls.append((deepcopy(prompts), deepcopy(kwargs)))
        return [({'overall_score': value, 'justification': 'original response'}, []) for value in (3.75, 4.25)]
    model = SimpleNamespace(generate_batch=original)
    conf = SimpleNamespace(conference_id='conference', reviews={})
    sim = SimpleNamespace(llm=model, native_system=object(),
        ecosystem=SimpleNamespace(agent_population={a.id: a for a in actors}),
        conference_system=SimpleNamespace(conferences=[conf]))
    return sim, actors, conf, calls


def original_phase(sim, actors, conf):
    paper = {'id': 'actual-paper', 'conference': 'conference'}
    prompts = [actor.get_review_prompt(paper)[0] for actor in actors]
    results = sim.llm.generate_batch(prompts, seed_ctx=('phase3_reviews', 1), temperature=.7)
    conf.reviews[paper['id']] = [dict(body, overall_score=int(body['overall_score']), reviewer_id=actor.id,
        arxiv_id=paper['id'], conference_id='conference', year=1) for actor, (body, _) in zip(actors, results)]


def test_observer_retains_exact_original_prompt_batch_results_and_restores_methods():
    sim, actors, conf, calls = observer_fixture()
    original_batch = sim.llm.generate_batch
    enable_review_identity_recording(sim)
    assert sim._record_native_review_identities is True
    with capture_native_review_tasks(sim, 1) as receipt:
        original_phase(sim, actors, conf)
    assert [t['item_index'] for t in receipt['tasks']] == [0, 1]
    assert [t['reviewer_id'] for t in receipt['tasks']] == [a.id for a in actors]
    assert [t['native_score'] for t in receipt['tasks']] == [3, 4]
    assert calls == [(['ORIGINAL PROMPT reviewer-a actual-paper', 'ORIGINAL PROMPT reviewer-b actual-paper'],
        {'seed_ctx': ('phase3_reviews', 1), 'temperature': .7})]
    assert sim.llm.generate_batch is original_batch
    assert all('get_review_prompt' not in vars(a) for a in actors)


@pytest.mark.parametrize('failure', ['original-phase', 'batch-order', 'wrong-context', 'duplicate-task', 'missing-record', 'wrong-record-score'])
def test_observer_fails_closed_and_restores_every_method_on_error(failure):
    sim, actors, conf, calls = observer_fixture()
    original_batch = sim.llm.generate_batch
    with pytest.raises((GraphRuntimeError, RuntimeError)):
        with capture_native_review_tasks(sim, 1):
            if failure == 'original-phase':
                raise RuntimeError('original phase failed')
            if failure in ('batch-order', 'wrong-context'):
                paper = {'id': 'actual-paper', 'conference': 'conference'}
                prompts = [actor.get_review_prompt(paper)[0] for actor in actors]
                sim.llm.generate_batch(list(reversed(prompts)) if failure == 'batch-order' else prompts,
                    seed_ctx=('phase3_reviews', 2 if failure == 'wrong-context' else 1))
            else:
                original_phase(sim, actors if failure != 'duplicate-task' else [actors[0], actors[0]], conf)
                if failure == 'missing-record': conf.reviews.clear()
                if failure == 'wrong-record-score': conf.reviews['actual-paper'][0]['overall_score'] = 10
    assert sim.llm.generate_batch is original_batch
    assert all('get_review_prompt' not in vars(a) for a in actors)


def test_nested_existing_context_prompt_wrapper_and_empty_year_restore_exactly():
    sim, actors, conf, _ = observer_fixture()
    old_instance = lambda paper, **kwargs: ('EXACT EXISTING CONTEXT', {})
    actors[0].get_review_prompt = old_instance
    with capture_native_review_tasks(sim, 1):
        original_phase(sim, actors, conf)
    assert actors[0].get_review_prompt is old_instance
    assert 'get_review_prompt' not in vars(actors[1])
    with capture_native_review_tasks(sim, 2) as receipt:
        pass
    assert receipt['tasks'] == [] and receipt['tasks_sha256']
    sim.native_system = None
    with pytest.raises(ValueError, match='native kernel'):
        enable_review_identity_recording(sim)
