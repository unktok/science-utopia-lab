"""Current-source transcription and retained-identity checks, not PDF layout QA."""
import json
from pathlib import Path
import re
import subprocess

from tests.reports.test_current_manuscript_estimands import bodies
from utopia.optimization.native_numeric_designer import checked


ROOT = Path(__file__).resolve().parents[2]
SECTION = 'paper/integrated/native-priority-method-snapshot.tex'
PREFIX = 'research/results/native-priority-first-three-second-generation-outcomes-v1.json'


def record(name):
    return checked(json.loads((ROOT / name).read_text()))


def test_all_fifteen_complete_rows_cross_scores_and_chronology_match_original_prefix():
    r = record(PREFIX)
    text = (ROOT / SECTION).read_text()
    rows = [line for line in text.splitlines() if re.match(r'^\d+ & [RAF] & ', line)]
    assert len(rows) == len(r['first_15_own_slots']) == 15
    methods = {'uniform-priority': 'R', 'adaptive-priority': 'A', 'free-code-graph': 'F'}
    for original, line in zip(r['first_15_own_slots'], rows, strict=True):
        slot = original['slot']; fields = line.removesuffix('\\\\').split(' & ')
        assert fields[:4] == [str(original['slot_index'] + 1), methods[slot['method']],
            str(slot['replication']) + '/' + str(slot['generation']),
            'U' if slot['objective'] == 'content-utility' else 'C']
        assert fields[4:] == [f"${original['cross_scores'][k]:.2f}$" for k in
            ('content-utility', 'resource-aware-content')] + [f"${original['cross_scores']['throughput']:.0f}$"]
        assert original['status'] == 'complete'
    assert r['counts_against_visible_reference'] == {'tie': 8, 'worse': 7, 'better': 0}
    assert not r['whole_campaign_closed'] and not r['selection_frozen'] and not r['publication_ready']
    for text_boundary in ('10:32 UTC', 'nine planned slots', 'not a selected subset',
                          'No row is marked', 'not failed or zero-valued'):
        assert text_boundary in text


def test_recovery_is_not_promoted_to_best_known_or_adaptive_advantage():
    r = record(PREFIX); text = (ROOT / SECTION).read_text()
    free, adaptive, uniform = r['first_15_own_slots'][12:]
    assert free['assigned_loss_minus_reference'] == 0
    assert abs(adaptive['assigned_loss_minus_reference'] - 1 / 3) < 1e-12
    assert abs(adaptive['assigned_loss_minus_previous_own'] + 8 / 3) < 1e-12
    assert uniform['assigned_loss_minus_reference'] == 0
    assert uniform['assigned_loss_minus_previous_own'] == -3
    for phrase in ('by $8/3$', '$1/3$ worse', 'no adaptive advantage',
                   'not independent policy samples', 'two\nindependent researcher populations'):
        assert phrase in text


def test_inert_edit_claims_match_complete_action_ranking_and_input_evidence():
    e = record(PREFIX)['new_free_C_g1']; text = (ROOT / SECTION).read_text()
    s = e['session_counts']; assert s['completed_steps'] == 14
    assert s['attempted_tool_counts'] == {'finish': 1, 'plan': 1, 'read_file': 11, 'write_file': 1}
    assert s['successful_document_changes'] == 1 and s['duplicate_unchanged_read_observations'] == 7
    assert len(e['authored_topic_priority_bias']) == 9
    assert len(e['actual_agenda_assignments']) == e['actual_assignments_differ_only_in_reason_text'] == 18
    assert all(a['same_direction_as_parent'] and a['actual_logged_topic'] == a['lexical_parent_topic']
               for a in e['actual_agenda_assignments'])
    own, reference = (e['scientist_observed_traces'][k] for k in ('own', 'exact_same_program_reference'))
    for key in ('ordered_full_request_payload_sha256', 'ordered_literal_response_choices_sha256'):
        assert own[key] == reference[key]
    assert own['wire_requests'] == own['completed_responses'] == reference['wire_requests'] == 179
    assert own['ordered_full_provider_body_hashes_sha256'] != reference['ordered_full_provider_body_hashes_sha256']
    assert sum(a['affected_by_visibility_phase_mismatch'] for a in e['phase_rows']) == 9
    for phrase in ('All 18 logged agenda records differ only in reason text',
                   'not whole-record or world byte identity', 'no node, wire or schedule',
                   'not a useful new institution', 'nine further affected calls'):
        assert phrase in text


def test_real_full_document_byte_table_does_not_use_toy_replacements():
    text = (ROOT / SECTION).read_text()
    directory = ROOT / 'tests/fixtures/native_author_context_boundary_v1'
    for name, compact, spaced, label in [
            ('parent-zero.json', 61892, 65479, 'Zero-priority U parent'),
            ('parent-terminal.json', 62755, 66342, 'Terminal C parent'),
            ('after-feature-write.json', 62032, 65619, 'U after feature-source write')]:
        document = json.loads((directory / name).read_text())
        assert len(json.dumps(document, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()) == compact
        assert len(json.dumps(document, ensure_ascii=False, allow_nan=False).encode()) == spaced
        assert f'{label} & {compact:,} & {spaced:,} & ' in text
    for phrase in ('source-owned boolean', 'not native loss corruption',
                   'not a clean isolated comparison', 'do not establish model understanding',
                   'older model certificates', '87 light/scripted', '43 scoped light cases'):
        assert phrase in text


def test_all_prior_tracks_references_and_labels_survive_current_integration():
    current = bodies(); body = '\n'.join(current.values())
    assert SECTION in current
    for name in ('native-consumer-source', 'native-terminal-cost', 'native-topic-system-search',
                 'native-longitudinal-comparison', 'problem-method', 'matched-observatory'):
        assert 'paper/integrated/' + name + '.tex' in current
    labels = re.findall(r'\\label\{([^}]+)\}', body)
    assert len(labels) == len(set(labels))
    assert set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}', body)) <= set(labels)
    section = current[SECTION]
    assert section.count('{') == section.count('}')
    assert sorted(re.findall(r'\\begin\{([^}]+)\}', section)) == sorted(re.findall(r'\\end\{([^}]+)\}', section))
    for path in re.findall(r'\\path\{([^}]+)\}', section):
        assert (ROOT / path).is_file()
    assert 'An important supported main-track claim' in current['paper/integrated.tex']
    assert 'interface can depend on the institution' in current['paper/integrated/discussion.tex']


def test_reviewed_pdf_receipt_is_historical_not_a_new_source_build_claim():
    r = record('paper/integrated-consumer-source-build-v1.json')
    old = subprocess.check_output(['git', 'show', r['source_commit'] + ':paper/integrated.tex'], cwd=ROOT)
    assert b'\\input{integrated/native-priority-method-snapshot}' not in old
    assert r['source_commit'] == '2d19cc966790ff0c2402b6889485ba58f32a49cd'
    assert r['pages'] == 104 and not r['publication_ready']
    note = (ROOT / 'paper/README.md').read_text()
    assert 'amendments have not been built or visually reviewed' in note
    assert 'Source and numeric-transcription checks alone are not PDF QA' in note
