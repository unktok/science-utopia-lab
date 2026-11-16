"""Current-source transcription and retained-identity checks, not PDF layout QA."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

from tests.reports.test_current_manuscript_estimands import bodies
from utopia.optimization.native_numeric_designer import checked


ROOT = Path(__file__).resolve().parents[2]
SECTION = 'paper/integrated/native-priority-method-snapshot.tex'
PREFIX = 'research/results/native-priority-first-three-second-generation-outcomes-v1.json'
TERMINAL = 'research/results/native-priority-method-terminal-snapshot-v1.json'


def record(name):
    return checked(json.loads((ROOT / name).read_text()))


def test_all_twenty_four_rows_match_terminal_without_changing_earlier_prefix():
    r = record(TERMINAL)
    text = (ROOT / SECTION).read_text()
    rows = [line for line in text.splitlines() if re.match(r'^\d+ & [RAF] & ', line)]
    assert len(rows) == len(r['rows']) == 24
    methods = {'uniform-priority': 'R', 'adaptive-priority': 'A', 'free-code-graph': 'F'}
    for original, line in zip(r['rows'], rows, strict=True):
        slot = original['slot']; fields = line.removesuffix('\\\\').split(' & ')
        assert fields[:4] == [str(original['slot_index'] + 1), methods[slot['method']],
            str(slot['replication']) + '/' + str(slot['generation']),
            'U' if slot['objective'] == 'content-utility' else 'C']
        assert fields[4:] == [f"${original['cross_scores'][k]:.2f}$" for k in
            ('content-utility', 'resource-aware-content')] + [f"${original['cross_scores']['throughput']:.0f}$"]
        assert original['status'] == 'complete'
    old = record(PREFIX)
    for earlier, final in zip(old['first_15_own_slots'], r['rows'][:15], strict=True):
        assert earlier['slot'] == final['slot']
        assert earlier['cross_scores'] == final['cross_scores']
        assert earlier['assigned_loss_minus_reference'] == final['assigned_loss_minus_reference']
    assert old['counts_against_visible_reference'] == {'tie': 8, 'worse': 7, 'better': 0}
    assert not old['whole_campaign_closed'] and not old['selection_frozen']
    assert r['counts_against_visible_reference'] == {'tie': 12, 'worse': 12, 'better': 0}
    assert r['selection_frozen_and_checked'] and not r['publication_ready']
    assert not r['original_paired_cold_cost_readouts_complete']
    for text_boundary in ('14:05 UTC', '14:11 UTC', 'not a selected subset',
                          '12 tie and 12 worsen', 'this terminal snapshot is not that audit'):
        assert text_boundary in text


def test_terminal_and_own_only_selection_do_not_become_method_or_cold_proof():
    r = record(TERMINAL); text = (ROOT / SECTION).read_text()
    assert r['normal_original_handle'] == 82425 and r['normal_original_exit_code'] == 0
    assert checked(r['terminal'])['consumed_slots'] == 24
    assert r['terminal']['observations'] == 27 and r['terminal']['no_retry']
    assert checked(r['writer_exit'])['exit_code'] == 0
    assert r['selected_counts_against_visible_reference'] == {'tie': 8, 'worse': 4, 'better': 0}
    assert len(r['selected']) == 12
    for chosen in r['selected']:
        pool = [row for row in r['rows'] if row['slot']['method'] == chosen['method']
                and row['slot']['replication'] == chosen['replication']
                and row['slot']['objective'] == chosen['objective']]
        best = min(row['cross_scores'][chosen['objective']] for row in pool)
        ties = [row for row in pool if row['cross_scores'][chosen['objective']] == best]
        assert chosen['completed_submissions'] == len(pool) == 2
        assert chosen['loss'] == best and chosen['selected_id'] == ties[0]['suggestion_id']
        assert chosen['all_tied_ids'] == [row['suggestion_id'] for row in ties]
        assert chosen['own_minus_reference'] == best - chosen['reference_loss']
        assert chosen['literal_program_sha256'] == ties[0]['literal_program_sha256']
    assert not r['held_out_evaluation'] and not r['raw_scientific_records_modified']
    assert r['new_model_calls'] == r['new_code_executions'] == 0
    assert not r['all8_author_outcome_and_visibility_exports_complete']
    for phrase in ('eight tie and four', 'without falling back',
                   'not independent populations', '45 instances', '102 committed proposal steps',
                   '179 full researcher inputs', 'corrected-model\nproof'):
        assert phrase in text


def test_final_paired_reports_are_retained_exactly_without_resealing_or_new_science():
    closed = record('research/results/native-priority-method-comparison-closed-v1.json')
    directory = ROOT / 'research/data/native-priority-method-closed-v1'
    for kind, paired in [('method', 'readouts'), ('author', 'author'), ('visibility', 'visibility')]:
        for name, expected in closed['paired_matching_files'][paired].items():
            path = directory / kind / (name + '.gz' if name == 'report.json' else name)
            raw = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == expected
            if name == 'report.json': checked(json.loads(raw))
    costs = gzip.decompress((directory / 'closure/costs.json.gz').read_bytes())
    assert hashlib.sha256(costs).hexdigest() == closed['paired_matching_files']['costs']
    assert checked(json.loads(costs))['content_sha256'] == closed['cost_content_sha256']
    assert all(code == 0 for code in closed['actual_exit_codes'].values())
    assert closed['coverage']['physical_worlds'] == 27
    assert closed['counts_against_visible_reference'] == record(TERMINAL)['counts_against_visible_reference']
    assert closed['author_totals'] == {'completed_steps': 102, 'attempted_edit_steps': 5,
        'successful_document_changes': 5, 'duplicate_unchanged_read_observations': 52,
        'serializer_mismatch_calls': 45, 'missing_or_different_loss_views': 0, 'uncommitted_responses': 0}
    assert closed['unchanged_parent_submissions'] == 4
    assert closed['observed_parent_matching_input_paths'] == 8
    assert len(closed['complete_observed_input_classes']) == 9
    assert not closed['corrected_author_model_readiness_proven'] and not closed['method_superiority_claimed']
    assert not closed['held_out_evaluation'] and not closed['publication_ready']
    text = (ROOT / SECTION).read_text()
    for phrase in ('14:21 UTC', '52 duplicate unchanged reads', 'five actual source writes',
                   '4,888 complete researcher responses', '7,392,125 prompt tokens',
                   '442,516 output tokens', '256 readiness and 102 proposal POSTs',
                   '35,144.9 seconds on a shared host'):
        assert phrase in text


def test_corrected_public_native_qa_is_not_corrected_real_model_or_scientific_gain():
    r = record('research/results/native-priority-corrected-public-native-qa-v1.json')
    assert r['source_commit'] == 'adfd6b947aa6cb5f151faf144d2e708bdb27dea6'
    assert r['actual_exit_code'] == 0 and r['passed'] == 1 and r['failures'] == r['errors'] == r['skipped'] == 0
    assert r['verification']['software_seed_override'] == [43003, 43011]
    assert r['verification']['evaluation_native_worlds'] == 18
    assert r['verification']['logical_rows'] == 30 and r['verification']['paired_rows'] == 108
    assert not r['corrected_real_model_readiness_proven'] and not r['new_scientific_optimization_run']
    assert not r['scientific_reserved_seeds_consumed'] and r['new_real_model_calls'] == 0
    directory = ROOT / 'research/data/native-priority-corrected-public-native-qa-v1'
    for name, expected in [('verification.json', r['verification_file_sha256']), ('junit.xml', r['JUnit_file_sha256'])]:
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
    text = (ROOT / SECTION).read_text()
    for phrase in ('1,245.16 shared-host seconds', '27 development', '18 fixed-evaluation native worlds',
                   'explicitly scripted', 'not\nreal-model readiness'):
        assert phrase in text


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


def test_earlier_closed_study_diagnostic_does_not_expand_the_new_confounds_scope():
    r = record('research/results/native-consumer-source-visibility-diagnostic-v1.json')
    assert r['totals'] == {'requests': 101, 'mismatches': 0, 'supplied_whole_document': 101, 'sessions': 8}
    assert [s['slot_index'] for s in r['sessions']] == list(range(8))
    assert sum(s['completed_steps'] for s in r['sessions']) == 101
    assert sum(len(s['steps']) for s in r['sessions']) == 101
    assert all(not s['mismatch_steps'] and s['terminal_status'] == 'generated' for s in r['sessions'])
    sizes = [pair for session in r['sessions'] for pair in session['full_document_size_pairs']]
    assert (min(a for a, b in sizes), max(a for a, b in sizes)) == (60210, 60885)
    assert (min(b for a, b in sizes), max(b for a, b in sizes)) == (63690, 64365)
    assert r['all_observed_documents_fit_both_serializers']
    assert not r['whole_native_cold_audit_repeated'] and not r['scientific_losses_or_selection_changed']
    assert r['new_model_calls'] == r['new_code_executions'] == 0
    text = (ROOT / SECTION).read_text()
    for phrase in ('not be projected onto every earlier study', '101 original',
                   '60,210 to 60,885', '63,690 to 64,365', 'No instance of this',
                   'does not extend to uninspected studies'):
        assert phrase in text


def test_reviewed_pdf_receipt_is_historical_not_a_new_source_build_claim():
    r = record('paper/integrated-consumer-source-build-v1.json')
    old = subprocess.check_output(['git', 'show', r['source_commit'] + ':paper/integrated.tex'], cwd=ROOT)
    assert b'\\input{integrated/native-priority-method-snapshot}' not in old
    assert r['source_commit'] == '2d19cc966790ff0c2402b6889485ba58f32a49cd'
    assert r['pages'] == 104 and not r['publication_ready']
    note = (ROOT / 'paper/README.md').read_text()
    assert 'amendments have not been built or visually reviewed' in note
    assert 'Source and numeric-transcription checks alone are not PDF QA' in note
