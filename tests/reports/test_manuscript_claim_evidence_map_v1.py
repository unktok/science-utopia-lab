"""Evidence transcription/claim scope, not new scientific replication or PDF QA."""
import gzip
import json
from pathlib import Path
import re
import statistics
import subprocess

import pytest

from tests.reports.test_current_manuscript_estimands import bodies
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
SECTION = 'paper/integrated/problem-method.tex'


def retained(name, *, sealed=False):
    raw = (ROOT / name).read_bytes()
    value = json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
    return checked(value) if sealed else value


def overview():
    return bodies()[SECTION].split('\\subsection*{Evidence at a glance:', 1)[1].split(
        '\\section{Problem:', 1)[0]


def test_matched_counts_do_not_merge_slots_policies_worlds_or_independence():
    r = retained('research/results/native-design-freedom-v2-closed-analysis-v1.json')
    counts = r['study_counts']
    assert {k: counts[k] for k in ('search_slots', 'search_complete', 'search_generation_nulls',
        'search_execution_nulls', 'physical_evaluation_jobs', 'exact_evaluated_policies')} == {
        'search_slots': 120, 'search_complete': 64, 'search_generation_nulls': 25,
        'search_execution_nulls': 31, 'physical_evaluation_jobs': 90, 'exact_evaluated_policies': 15}
    text = overview()
    for phrase in ('120 slots: 64 complete, 25 generation nulls, 31 execution nulls',
                   '90 physical evaluations of 15 exact policies',
                   'not 90 independent optimization histories', 'not a pooled estimate',
                   'Technical nulls remain unavailable measurements'):
        assert phrase in text


def test_evaluation_summary_keeps_the_bad_numeric_arm_not_only_code_winners():
    r = retained('research/data/native-design-v2/closed-report.json.gz', sealed=True)
    groups = {}
    for row in r['evaluation']:
        if row['years'] == 2:
            assert row['observation_status'] == 'complete'
            for label in row['labels']:
                groups.setdefault(label, []).append(row)
    for label in ('selected:throughput:code-fixed-graph', 'selected:throughput:code-and-graph',
                  'selected:throughput:technical-only', 'selected:throughput:random',
                  'reference:open-accept-all'):
        assert len(groups[label]) == 5
        assert statistics.mean(-x['cross_scores']['throughput'] for x in groups[label]) == 6.2
    numeric = groups['selected:throughput:parameters']
    assert len(numeric) == 5
    assert statistics.mean(-x['cross_scores']['throughput'] for x in numeric) == 0.2
    for label in ('selected:selective:code-fixed-graph', 'selected:selective:code-and-graph'):
        assert statistics.mean(x['cross_scores']['selective'] for x in groups[label]) == pytest.approx(1.92)
    assert all(x['cross_scores']['selective'] == 0 for x in groups['reference:open-no-review-reject-all'])
    text = overview()
    assert 'throughput code, technical-only and uniform selections average 6.2' in text
    assert 'LLM numeric retains the seed at 0.2' in text
    assert 'Review-cost code selections\naverage loss 1.92' in text
    assert 'worse than reviewer-free reject at 0' in text


def test_same_authority_topic_effect_is_a_hand_contrast_not_automatic_invention():
    r = retained('research/results/native-legacy-topic-pilot-closed-v1.json', sealed=True)
    assert [w['scores']['throughput'] for w in r['rows']] == [-20., -36.]
    assert [w['collected_activity_cost'] for w in r['rows']] == [200., 200.]
    assert r['designer_generation_POSTs'] == 0 and not r['automatic_invention']
    text = overview()
    for phrase in ('Two hand-written rules yield 20 versus 36', 'collected cost 200',
                   'duration-only mediation or a world-level optimum',
                   'Hand\ncontrols establish reachable effects'):
        assert phrase in text


def test_resource_gain_is_preserved_without_relabelling_requested_cost_or_science():
    r = retained('research/results/native-terminal-cost-pilot-closed-v1.json')
    a, b = r['rows']
    assert b['C'] - a['C'] == -4
    assert [w['K'] for w in r['rows']] == [200., 160.]
    assert [w['unpaid'] for w in r['rows']] == [0., 40.]
    assert [w['requested'] for w in r['rows']] == [200., 200.]
    assert r['full_scientist_request_sequences_equal']
    assert r['requests_and_literal_choices_per_world'] == 179
    assert r['common_accepted_year_paper_content_records'] == 36
    text = overview()
    for phrase in ('loss by 4', '200$\\to$160', '0$\\to$40', 'requested cost still 200',
                   'The gain is retained, not disqualified', 'better science'):
        assert phrase in text


def test_source_information_summary_retains_null_and_all_four_frozen_ties():
    r = retained('research/results/native-consumer-source-comparison-closed-v1.json')
    assert (r['consumed_own_slots'], r['complete_own_outcomes'], r['runtime_nulls']) == (8, 7, 1)
    assert len(r['own_only_selection']) == len(r['comparisons']) == 4
    assert all(c['own_minus_best_visible'] == 0 for c in r['comparisons'].values())
    assert not r['automatic_useful_institution_invention_demonstrated']
    assert not r['isolated_source_comprehension_causality_identified']
    text = overview()
    assert 'seven completed outcomes and one native null' in text
    assert 'All four\nfrozen own selections tie' in text
    assert 'A general negative effect of source access' in text


def test_complete_terminal_summary_preserves_historical_twenty_slot_receipt():
    r = retained('research/results/native-priority-twentieth-own-outcome-and-prefix-v1.json', sealed=True)
    assert r['prefix_counts_against_visible_reference'] == {'complete': 20, 'tie': 10, 'worse': 10, 'better': 0}
    assert len(r['rows']) == 20 and not r['whole_campaign_closed'] and not r['publication_ready']
    text = overview()
    final = retained('research/results/native-priority-method-terminal-snapshot-v1.json', sealed=True)
    assert final['counts_against_visible_reference'] == {'tie': 12, 'worse': 12, 'better': 0}
    assert final['selected_counts_against_visible_reference'] == {'tie': 8, 'worse': 4, 'better': 0}
    assert final['all24_native_observations_recorded'] and not final['original_paired_cold_cost_readouts_complete']
    assert '14:05 UTC' in text and '14:11 UTC' in text
    assert 'Twelve own\nobservations tie and 12 worsen' in text
    assert '12 frozen own-only selections yield eight ties and four worse losses' in text
    assert 'older dated receipts remain unchanged' in text
    assert 'prospectively\ncorrected software is not an observed corrected search result' in text
    previous = bodies()['paper/integrated/native-priority-method-snapshot.tex']
    assert 'All 24 own native observations' in previous
    assert 'three inspection attempts' in previous and 'counter records\nattempts' in previous


def test_loss_definitions_and_unmet_main_track_goal_are_not_collapsed():
    text = overview()
    for phrase in ('$C=4A-Q+0.1R$', '$L_C=-U+0.1K$', 'native peer scores',
                   'fixed external abstract-content observer', 'different measurements',
                   'Neither objective is retrospectively substituted',
                   'adequate independent evidence remain open',
                   'structural, gradient, nested-design and English game-interface'):
        assert phrase in text


def test_prior_manuscript_inputs_labels_and_evidence_paths_survive_without_pdf_claim():
    current = bodies()
    old = subprocess.check_output(['git', 'show', 'b12acbe9:paper/integrated.tex'], cwd=ROOT, text=True)
    old_inputs = {'paper/' + p + '.tex' for p in re.findall(r'\\input\{([^}]+)\}', old)}
    assert old_inputs <= set(current)
    body = '\n'.join(current.values())
    labels = re.findall(r'\\label\{([^}]+)\}', body)
    assert len(labels) == len(set(labels))
    assert set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}', body)) <= set(labels)
    text = overview()
    for path in re.findall(r'\\path\{([^}]+)\}', text):
        assert (ROOT / path).is_file()
    for p in (SECTION, 'paper/integrated/studies.tex'):
        text = current[p]
        assert text.count('{') == text.count('}')
        stack = []
        for operation, name in re.findall(r'\\(begin|end)\{([^}]+)\}', text):
            if operation == 'begin': stack.append(name)
            else: assert stack and stack.pop() == name
        assert not stack
    assert 'Current111-page revised working paper' in (ROOT / 'paper/README.md').read_text()
