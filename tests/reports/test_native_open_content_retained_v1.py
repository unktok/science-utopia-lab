"""Compact retained outcomes, not fresh inference or PDF layout verification."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return checked(json.loads((ROOT / path).read_text()))


def test_fixed_record_utility_disadvantage_is_content_replacement_not_score_overwrite():
    data = read('research/data/native-open-institution-v3/content-delta.json')
    analysis = checked(data['analysis'])
    assert data['raw_files'] == 469 and data['original_bytes_unchanged']
    assert len(analysis['all_slots']) == 6 and len(analysis['all_complete_pairs']) == 3
    worlds = {w['label']: w for w in analysis['worlds']}
    assert worlds['R7-original']['sign_counts'] == {'positive': 13, 'zero': 5, 'negative': 0}
    assert worlds['post-funding-cost']['sign_counts'] == {'positive': 15, 'zero': 5, 'negative': 0}
    assert worlds['U2']['sign_counts'] == {'positive': 12, 'zero': 6, 'negative': 0}
    pair, = [p for p in analysis['all_complete_pairs'] if (p['left_label'], p['right_label']) == ('R7-original', 'U2')]
    overlap = pair['overlap']
    assert overlap['common']['occurrences'] == 13
    assert overlap['common']['exact_centered_utility_sum'] == {'numerator': 28, 'denominator': 3}
    assert overlap['left_only']['occurrences'] == overlap['right_only']['occurrences'] == 5
    assert overlap['left_only']['centered_utility_sum'] == 4.
    assert overlap['right_only']['centered_utility_sum'] == 3.
    assert not analysis['loss_changed'] and not analysis['selection_changed']


def test_trace_preparation_does_not_claim_author_access_or_model_token_fit():
    proof = read('research/results/native-open-content-and-trace-verification-v1.json')
    assert proof['checks']['tests'] == 48 and proof['checks']['exit_code'] == 0
    rows = proof['codec_actual_exports']['rows']
    assert [r['columnar_bytes'] for r in rows] == [13753, 13825, 13753]
    assert all(r['exact_roundtrip'] for r in rows)
    preview = proof['R7_only_frame_preview']
    assert len(preview['rows']) == 6 and preview['prior_mislabeled_hash_field_retained']
    assert all(len(r['request_sha256']) == 64 and r['fits_declared_byte_cap'] for r in preview['rows'])
    assert not preview['full_own_histories_tested'] and not preview['measured_model_token_fit']
    assert not proof['author_or_measurement_connection_implemented']
    assert proof['content_comparison']['two_exports_identical'] and not proof['publication_ready']


def test_complete_unused_comparison_keeps_missing_T_and_unfavorable_U():
    result = read('research/results/native-open-institution-fixed-closed-v1.json')
    assert result['writer']['exit_code'] == 0 and result['terminal']['completed_jobs'] == 3
    assert result['physical_worlds'] == 3 and result['unused_seeds'] == [1516320444]
    rows = {r['label']: r for r in result['logical_rows']}
    assert rows['reference:R7-original']['scores'] == {'throughput': -30., 'content-utility': -25.}
    assert rows['reference:post-funding-cost']['scores'] == {'throughput': -32., 'content-utility': -26.}
    assert rows['selected:content-utility']['scores'] == {'throughput': -28., 'content-utility': -23.}
    assert rows['selected:throughput']['status'] == 'no-completed-submission'
    assert rows['selected:throughput']['physical_job'] is None
    assert all(v is None for v in rows['selected:throughput']['scores'].values())
    assert not result['baseline_fallback'] and result['new_designer_calls'] == 0
    assert not result['own_advantage_over_hand'] and not result['independent_optimizer_replication']
    assert all(v == 0 for v in result['audit']['continuation_exit_codes'].values())
    assert result['scientist_cost']['completed_responses'] == 467
    assert result['common_content_observer_cost']['physical_requests'] == 138
    assert len(result['complete_observed_input_classes']) == 3


def test_local_unused_data_and_figure_bytes_match_both_original_exports():
    result = read('research/results/native-open-institution-fixed-closed-v1.json')
    for name, expected in result['matching_report_files']['report'].items():
        folder = 'paper/figures' if name.endswith(('.png', '.svg')) else 'research/data'
        assert file_sha256(ROOT / folder / 'native-open-institution-fixed-v1' / name) == expected
    source = (ROOT / 'paper/integrated/native-workflow-feedback.tex').read_text()
    for literal in ('R7 reference & $-30$ & $-25$', 'Strong hand & $-32$ & $-26$',
                    'U-selected (U2) & $-28$ & $-23$', '467 complete scientist responses',
                    '138 physical calls', 'there are no new designer calls',
                    'same-year/paper/content', 'No accepted record in'):
        assert literal in source


def test_latest_reviewed_complete_paper_keeps_all_old_artifacts_and_current_results():
    receipt = read('paper/integrated-open-institutions-build-v1.json')
    assert (receipt['pages'], receipt['figures'], receipt['tables'], receipt['cited_references']) == (81, 42, 36, 26)
    assert file_sha256(ROOT / receipt['output']) == receipt['pdf_sha256']
    assert file_sha256(ROOT / 'paper/integrated.tex') == receipt['tex_sha256']
    assert receipt['visual_review']['all_final_pages_reviewed']
    assert receipt['visual_review']['pages_reviewed'] == list(range(1, 82))
    assert len(receipt['visual_review']['page_png_sha256']) == 81
    assert receipt['build']['rendered_page_identity_verified'] and receipt['build']['off_page_text_words'] == 0
    for name, expected in receipt['preserved_files'].items():
        assert file_sha256(ROOT / name) == expected
    scope = receipt['scientific_scope']
    assert scope['open_v3_own_completions'] == 1 and scope['throughput_selection_missing']
    assert scope['open_fixed_physical_worlds'] == 3 and not scope['own_advantage_demonstrated']
    assert not receipt['new_paper_rebuild_subset_verified'] and not receipt['publication_ready']
