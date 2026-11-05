"""SCRIPTED reproduction of actual wall-clock/preview shadowing; no inference."""
from copy import deepcopy

import pytest
from langchain_core.documents import Document

from utopia.agents.conference import create_default_conference_system
from utopia.agents.research_direction import AVAILABLE_DIRECTIONS
from utopia.agents.researcher_agents import UniversityResearcher
from utopia.data.paper_tracker import ArchivedPaper, PaperTracker


def inputs(tmp_path):
    agent = UniversityResearcher('SCRIPTED-researcher', 'SCRIPTED-institution', funding_level=1000,
                                expertise=[AVAILABLE_DIRECTIONS[0]], llm=None)
    tracker = PaperTracker(str(tmp_path))
    paper = ArchivedPaper(id='SCRIPTED-own-paper', title='Own prior research', abstract='Original scientific abstract',
        author_id=agent.id, author_type='university', year=1, conference='SCRIPTED-conference', status='reject',
        review_history=[{'year': 1, 'conference': 'SCRIPTED-conference', 'score': 3., 'decision': 'reject',
                         'reviews': [{'review_time': 1793915165.1100721, 'reviewer_id': 'SCRIPTED-reviewer',
                                      'overall_score': 3, 'justification': 'Original review content'}]}])
    tracker.papers_by_id[paper.id] = paper
    tracker.papers_by_author[agent.id] = [paper]
    direction = {'direction': AVAILABLE_DIRECTIONS[0], 'detailed_focus': 'SCRIPTED research focus'}
    candidates = [Document(page_content='Candidate scientific abstract',
                           metadata={'id': 'SCRIPTED-candidate', 'title': 'Candidate title', 'topics': ['science']})]
    return agent, tracker, paper, direction, candidates


def render(agent, tracker, direction, candidates, **kwargs):
    return agent.get_paper_submission_prompt(candidates, kwargs.pop('year', 2),
        create_default_conference_system().conferences[:1], direction, tracker, **kwargs)


@pytest.mark.parametrize('max_submissions,force_list', [(1, False), (3, False), (1, True)])
def test_year_two_caller_previews_are_not_overwritten_by_private_archived_objects(tmp_path, max_submissions, force_list):
    agent, tracker, paper, direction, candidates = inputs(tmp_path)
    previews = ['EXPLICIT PUBLISHED PREVIEW FROM CALLER']
    raw = deepcopy(paper.to_dict())
    prompt, _ = render(agent, tracker, direction, candidates, previous_papers=previews,
                       max_submissions=max_submissions, force_list=force_list)
    assert previews[0] in prompt
    assert 'ArchivedPaper(' not in prompt
    assert 'Own prior research' in prompt and 'reject with score 3.00' in prompt
    assert '1793915165.1100721' not in prompt
    assert paper.to_dict() == raw and previews == ['EXPLICIT PUBLISHED PREVIEW FROM CALLER']


def test_changing_only_operational_review_clock_cannot_change_submission_input(tmp_path):
    agent, tracker, paper, direction, candidates = inputs(tmp_path)
    first = render(agent, tracker, direction, candidates)
    paper.review_history[0]['reviews'][0]['review_time'] = 1793919693.27541
    second = render(agent, tracker, direction, candidates)
    assert first == second
    assert paper.review_history[0]['reviews'][0]['review_time'] == 1793919693.27541


def test_rendering_sorted_history_does_not_mutate_tracker_order_or_records(tmp_path):
    agent, tracker, paper, direction, candidates = inputs(tmp_path)
    newer = deepcopy(paper)
    newer.id = 'SCRIPTED-newer-paper'
    newer.title = 'Newer own research'
    newer.year = 3
    tracker.papers_by_author[agent.id].append(newer)
    raw = deepcopy(tracker.papers_by_author[agent.id])
    prompt, _ = render(agent, tracker, direction, candidates, year=4)
    assert tracker.papers_by_author[agent.id] == raw
    assert [p.id for p in tracker.papers_by_author[agent.id]] == [paper.id, newer.id]
    assert prompt.index('Newer own research') < prompt.index('Own prior research')


@pytest.mark.parametrize('year', [1, 2])
def test_explicit_scientific_strings_and_candidates_are_not_clock_scrubbed(tmp_path, year):
    agent, tracker, paper, direction, candidates = inputs(tmp_path)
    literal = "Scientific timing claim: review_time=1793915165.1100721; preserve this authored text"
    candidates[0].page_content = literal
    preview = "A published timing study with {'review_time': 1793915165.1100721}"
    prompt, _ = render(agent, tracker, direction, candidates, year=year, previous_papers=[preview])
    assert literal in prompt and preview in prompt
    assert paper.review_history[0]['reviews'][0]['justification'] == 'Original review content'


def test_actual_readiness_binding_includes_the_scientist_prompt_implementation():
    import hashlib
    from pathlib import Path
    import utopia.agents.base_agent as agents
    from utopia.optimization.native_designer_preflight import runtime_binding
    assert runtime_binding()['agents/base_agent.py'] == hashlib.sha256(Path(agents.__file__).read_bytes()).hexdigest()
