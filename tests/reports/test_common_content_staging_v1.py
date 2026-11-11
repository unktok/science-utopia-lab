from copy import deepcopy

from scripts.reports.stage_common_content_observer_v1 import project
from tests.optimization.test_common_content_observer import PAPER, contract
from utopia.system.design_patch import digest


def inputs(contents):
    value = {'scientific_source_commit': 'SCRIPTED-original', 'historical_full_audit_content_sha256': 'SCRIPTED-audit',
        'worlds': [{'identity': 'SCRIPTED-world'}], 'skipped_partial_worlds': [{'identity': 'SCRIPTED-partial'}],
        'accepted_decisions': [{'content': row} for row in contents]}
    return {**value, 'content_sha256': digest(value)}


def test_staging_deduplicates_only_content_and_retains_missing_inputs():
    source = inputs([PAPER, {**PAPER, 'id': 'another label'}, {**PAPER, 'abstract': None}]); before = deepcopy(source)
    result = project(source, contract())
    assert source == before and result['accepted_decision_records'] == 3
    assert result['unique_contents'] == 2 and result['eligible_unique_contents'] == 1
    assert result['unavailable_unique_contents'] == 1 and result['partial_worlds_skipped'] == 1
    assert result['all_eligible_panel_posts_upper_bound'] == 3 and result['new_model_calls'] == 0
    assert not result['scores_observed']


def test_oversized_scientific_content_is_unavailable_not_shortened():
    result = project(inputs([{**PAPER, 'abstract': 'full content ' * 10000}]), contract())
    assert result['eligible_unique_contents'] == 0 and result['unavailable_unique_contents'] == 1
    assert result['maximum_prompt_utf8_bytes'] is None
