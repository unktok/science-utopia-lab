from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

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


def test_retained_actual_stage_binds_original_audit_and_exact_frozen_instrument():
    from utopia.optimization.native_numeric_designer import checked
    root = Path(__file__).resolve().parents[2]
    directory = root / 'research/data/common-content-observer-v1'
    report = checked(json.loads((directory / 'staging.json').read_text()))
    saved = checked(json.loads((directory / 'contract.json').read_text()))
    assert hashlib.sha256((directory / 'staging.json').read_bytes()).hexdigest() == 'd6640c4671833bc45bd1876d2059f976be23edcef2b5c086a5c1927ca4d631b2'
    assert report['contract_sha256'] == saved['content_sha256']
    assert saved['source_commit'] == 'af294b70ccfcac9b13d2bcdee3b3111785a34f31'
    original = subprocess.check_output(['git', 'show', saved['source_commit'] + ':utopia/optimization/common_content_observer.py'], cwd=root)
    assert hashlib.sha256(original).hexdigest() == saved['adapter_source_sha256']
    assert report['complete_physical_worlds'] == 44 and report['partial_worlds_skipped'] == 5
    assert report['accepted_decision_records'] == 263 and report['unique_contents'] == 76
    assert report['eligible_unique_contents'] == 76 and report['unavailable_unique_contents'] == 0
    assert report['all_eligible_panel_posts_upper_bound'] == 228
    assert report['maximum_prompt_utf8_bytes'] == 3232 and report['minimum_prompt_utf8_bytes'] == 1449
    assert report['new_model_calls'] == report['new_native_worlds'] == 0 and not report['scores_observed']
    assert report['historical_full_audit_content_sha256'] == '85d4698ff09dd6cfbfe8b83790f8ae28dbf27072de9853184adc1db4334b92d1'
    for row in report['contents'].values():
        assert row['status'] == 'eligible' and [p['critic'] for p in row['prompts']] == [0, 1, 2]
        assert all(p['request_utf8_bytes'] <= saved['maximum_request_utf8_bytes'] for p in row['prompts'])
