"""Opt-in observational identities for original native review batch tasks.

The original prompts, model request seeds, parser, review records and RNG are
untouched. Identities are captured where actual prompt construction and batch
submission meet, rather than guessed from paper titles or response scores.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib

from .design_patch import digest
from .runtime import GraphRuntimeError

SCHEMA = 'scienceutopia.native-review-task-identities.v9'
EVENT = 'native.system.review_tasks_bound'


def enable_review_identity_recording(simulation):
    """Enable before each fresh/resumed run; no model calls or file writes."""
    if getattr(simulation, 'native_system', None) is None:
        raise ValueError('review identity recording requires the original native kernel')
    simulation._record_native_review_identities = True


@contextmanager
def capture_native_review_tasks(simulation, year):
    """Capture actual collection order and successful native review records.

    Only the original batched phase3 path is supported. Observers restore all
    methods even on failure; they neither repair nor replace any model result.
    """
    model = simulation.llm
    if not hasattr(model, 'generate_batch'):
        raise GraphRuntimeError('review identity recording requires original batched phase3 requests')
    originals, tasks, results = [], [], []
    receipt = {'schema': SCHEMA, 'year': year, 'tasks': tasks}
    had_batch = 'generate_batch' in vars(model)
    old_batch = vars(model).get('generate_batch')
    original_batch = model.generate_batch
    calls = 0
    try:
        for actor in simulation.ecosystem.agent_population.values():
            if not hasattr(actor, 'get_review_prompt'):
                continue
            original = actor.get_review_prompt
            had_instance = 'get_review_prompt' in vars(actor)
            originals.append((actor, had_instance, vars(actor).get('get_review_prompt')))
            def prompt(*args, _original=original, _actor=actor, **kwargs):
                paper = args[0] if args else kwargs['paper']
                text, response_format = _original(*args, **kwargs)
                if not isinstance(text, str):
                    raise GraphRuntimeError('actual native review prompt is not text')
                tasks.append({'item_index': len(tasks), 'year': year, 'reviewer_id': _actor.id,
                    'paper_id': paper['id'], 'conference_id': paper['conference'],
                    'prompt_sha256': hashlib.sha256(text.encode()).hexdigest()})
                return text, response_format
            actor.get_review_prompt = prompt

        def batch(prompts, *args, **kwargs):
            nonlocal calls
            calls += 1
            if (calls != 1 or kwargs.get('seed_ctx') != ('phase3_reviews', year)
                    or len(prompts) != len(tasks)
                    or [hashlib.sha256(p.encode()).hexdigest() for p in prompts]
                    != [t['prompt_sha256'] for t in tasks]):
                raise GraphRuntimeError('native review task collection differs from submitted original batch')
            returned = original_batch(prompts, *args, **kwargs)
            if len(returned) != len(tasks):
                raise GraphRuntimeError('original review batch result count differs from actual tasks')
            results.extend(deepcopy(body) for body, _ in returned)
            return returned
        model.generate_batch = batch
        yield receipt
        if (tasks and calls != 1) or (not tasks and calls != 0):
            raise GraphRuntimeError('native review task batch was absent or unexpectedly repeated')
        seen = set()
        conferences = {c.conference_id: c for c in simulation.conference_system.conferences}
        for task, body in zip(tasks, results):
            key = (task['conference_id'], task['paper_id'], task['reviewer_id'])
            if key in seen:
                raise GraphRuntimeError('duplicate actual paper/conference/reviewer review task')
            seen.add(key)
            rows = [r for r in conferences[task['conference_id']].reviews.get(task['paper_id'], [])
                if r.get('reviewer_id') == task['reviewer_id']]
            if not isinstance(body, dict) or 'overall_score' not in body or len(rows) != 1:
                raise GraphRuntimeError('successful original review result lacks one unique actual native record')
            row = rows[0]
            if (row.get('arxiv_id') != task['paper_id'] or row.get('conference_id') != task['conference_id']
                    or row.get('year') != year
                    or row.get('overall_score') != int(body['overall_score'])):
                raise GraphRuntimeError('actual native review identity or original integer parse differs')
            task.update(parsed_response_sha256=digest(body), native_score=row['overall_score'],
                native_review_sha256=digest(row))
        receipt['tasks_sha256'] = digest(tasks)
    finally:
        if had_batch:
            model.generate_batch = old_batch
        else:
            vars(model).pop('generate_batch', None)
        for actor, had_instance, old_instance in originals:
            if had_instance:
                actor.get_review_prompt = old_instance
            else:
                vars(actor).pop('get_review_prompt', None)
