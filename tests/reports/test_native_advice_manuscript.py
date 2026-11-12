"""Exact closed control values and editorial inference boundaries, not science runs."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_advice_section_uses_all_closed_conditions_without_claiming_equivalence():
    summary = checked(json.loads((ROOT/'research/data/native-instruction-timing-v1/summary.json').read_text()))
    text = (ROOT/'paper/integrated/native-advice.tex').read_text()
    assert [(w['condition'], w['direction_requests_with_literal_instruction'],
             w['shortest_displayed_selected_attempts'], w['mean_catalog_duration_on_known_attempts'])
            for w in summary['worlds']] == [('cut',0,4,2.6), ('early',10,4,2.6), ('late',5,4,2.6)]
    assert [w['scores'] for w in summary['worlds']] == [
        {'throughput': -7.0, 'content-utility': -4.0}] * 3
    for row in (r'Cut &0/10 &4/10 &2.6', r'Early &10/10 &4/10 &2.6',
                r'Late &5/10 &4/10 &2.6'):
        assert row in text
    for boundary in ('not a newly', 'does not change the displayed catalog',
                     'complete ordered model-input and literal-response sequences differ',
                     'not establish general instruction ineffectiveness',
                     'there are no designer proposals', 'not add an adoption'):
        assert boundary.lower() in ' '.join(text.lower().split())
    assert r'\input{integrated/native-advice}' in (ROOT/'paper/integrated.tex').read_text()


def test_manuscript_costs_join_original_closed_usage_and_timing():
    costs = checked(json.loads((ROOT/'research/data/native-instruction-timing-v1/costs.json').read_text()))
    assert costs['scientist']['completed_responses'] == 389
    assert costs['scientist']['provider_usage']['prompt_tokens']['recorded_sum'] == 360734
    assert costs['scientist']['provider_usage']['completion_tokens']['recorded_sum'] == 38542
    assert costs['common_content_observer']['physical_requests'] == 39
    text = (ROOT/'paper/integrated/native-advice.tex').read_text()
    assert '389 scientist replies with360734 input and38542 output' in text
    assert 'uses39 separate requests' in text
    assert 'Tokenless model-load costs remain unknown' in text


def test_closest_governance_comparison_is_versioned_and_does_not_claim_priority():
    text = (ROOT/'paper/integrated/discussion.tex').read_text()
    assert r'\citep{bracale2026institutional}' in text
    assert 'not new here' in text and 'field-wide' in text
    bib = (ROOT/'paper/submission-sources.bib').read_text()
    assert 'arXiv:2601.11369v1' in bib
    assert 'https://arxiv.org/abs/2601.11369v1' in bib
