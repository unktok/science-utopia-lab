"""Preserve source-bound reader preparation without claiming a scientific result."""
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT/'research/results/native-planning-content-contributions-preparation-v1.json').read_text()))


def test_exact_committed_reader_and_all_preparation_checks_remain_bound():
    r = receipt(); source = r['analysis_source_commit']
    assert source == '7d6e82f34b59588ebe42ad9388e22c3adb310149'
    for path, expected in r['source_files_sha256'].items():
        body = subprocess.check_output(['git', 'show', source+':'+path], cwd=ROOT)
        assert hashlib.sha256(body).hexdigest() == expected
    assert [(q['tests'], q['failures'], q['errors']) for q in r['qa']] == [(13, 0, 0), (40, 0, 0), (40, 0, 0), (40, 0, 0)]
    assert all(q['final_exit_zero_observed'] for q in r['qa'])


def test_existing_fixture_does_not_become_new_worlds_or_actual_qwen_evidence():
    r = receipt(); f = r['closed_SCRIPTED_fixture']
    assert f['existing_native_worlds'] == 14 and f['new_native_worlds_executed'] == 0
    assert f['accepted_occurrences'] == 106 and f['unique_contents'] == 12
    assert f['original_audits_match'] and f['two_real_CLI_exports_match'] and len(f['files']) == 12
    assert f['communication_corpus_and_origin_attestations_SCRIPTED'] and not f['actual_Qwen_result_claimed']
    assert not any(r[k] for k in ('new_scientific_inference', 'loss_or_selection_changed',
        'actual_scientific_closed_output_claimed', 'causal_mediation_claimed', 'publication_ready'))


def test_actual_frozen_continuation_waits_for_normal_closure_without_retry():
    r = receipt(); launch = r['actual_continuation']; start = checked(launch['start'])
    assert launch['session'] == 64639 and launch['normal_audit_cost_closure_required']
    assert start['analysis_source_commit'] == r['analysis_source_commit']
    assert start['scientific_source_commit'] == '8cd61578b94d86dd0cf2ff3b0e581d9a2698fc0f'
    assert not start['new_inference_allowed'] and not start['retry_failed_stages']


def test_current_entry_and_new_notes_have_resolvable_local_links():
    result = check(ROOT, documents=('research/INDEX.md', 'research/STATUS.md',
        'research/components/native-planning-content-contributions-v1.md',
        'research/logbook/2026-11-13-planning-content-contributions.md'), manifest=None)
    assert result['status'] == 'passed', result['errors']
