"""Bind the empirical V2 draft to retained actual evidence, not old pilot data."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from scripts.reports.historical_paper_sources import historical_source

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((ROOT / name).read_text())


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def test_v2_reviewed_source_pdf_and_dependencies_match():
    receipt = read('paper/submission-build-v3.json')
    assert receipt['schema'] == 'scienceutopia.working-paper-build.v3'
    assert receipt['status'] == 'working-draft-not-submission-ready'
    assert receipt['pages'] == 12
    assert receipt['visual_qa']['pages'] == list(range(1, 13))
    assert receipt['visual_qa']['all_pages_inspected'] is True
    assert len(receipt['visual_qa']['final_page_png_sha256']) == 12
    assert not receipt['layout_or_undefined_reference_warnings']
    expected = {receipt['entrypoint']: receipt['tex_sha256'],
                receipt['output']: receipt['pdf_sha256'],
                'paper/submission-sources.bib': receipt['additional_bibliography_sha256'],
                **receipt['additional_dependencies'], **receipt['analysis_projection_sources']}
    for name, digest in expected.items():
        assert (ROOT / name).resolve().is_relative_to(ROOT)
        observed = sha(name) if name == receipt['output'] else hashlib.sha256(
            historical_source('paper/submission-build-v3.json',name)).hexdigest()
        assert observed == digest, name
    old = receipt['previous_draft_preserved']
    assert sha(old['output']) == old['pdf_sha256']
    info = shutil.which('pdfinfo')
    if info:
        result = subprocess.check_output([info, str(ROOT / receipt['output'])], text=True)
        assert re.search(r'^Pages:\s+12$', result, re.M)


def test_v2_literal_dependencies_and_citations_are_bound():
    receipt = read('paper/submission-build-v3.json')
    pending = [receipt['entrypoint']]; visited = set(); bodies = []
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name); body = historical_source('paper/submission-build-v3.json',name).decode(); bodies.append(body)
        if name != receipt['entrypoint']:
            assert name in receipt['additional_dependencies']
        pending += ['paper/' + p + ('' if p.endswith('.tex') else '.tex')
                    for p in re.findall(r'\\input\{([^}]+)\}', body)]
    tex = '\n'.join(bodies)
    bib = ''.join(historical_source('paper/submission-build-v3.json',p).decode()
        for p in ('paper/references.bib','paper/submission-sources.bib'))
    available = set(re.findall(r'@\w+\s*\{\s*([^,\s]+)', bib))
    used = {k.strip() for g in re.findall(r'\\cite\w*\{([^}]+)\}', tex) for k in g.split(',')}
    assert used and used <= available
    figures = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', tex)
    assert len(figures) == 5
    assert all('paper/' + p in receipt['additional_dependencies'] for p in figures)
    assert 'SCRIPTED' not in tex and '/Users/' not in tex


def test_v2_attempt_counts_failures_selection_and_shared_evaluation():
    table = read('paper/generated/native-design-v2/search-outcomes-data.json')
    scores = read('paper/generated/native-design-v2/cross-score-data.json')
    assert table['classification'] == scores['classification'] == 'actual-native-design-freedom-study-v2'
    assert table['counts'] == {'complete': 64, 'generation-failure': 25, 'technical-failure': 31}
    assert len(table['rows']) == 10 and sum(r['scheduled'] for r in table['rows']) == 120
    assert sum(r['selected_initial'] for r in table['rows']) == 4
    for row in table['rows']:
        assert row['scheduled'] == sum(row['status_counts'].values()) == 12
        assert row['selected_row_id'] in row['all_tied_row_ids']
    assert scores['physical_policies'] == 15 and scores['physical_evaluation_jobs'] == 90
    assert scores['logical_evaluation_labels'] == 19
    assert not scores['shared_labels_count_as_new_replication']
    jobs = set()
    for panel in scores['panels']:
        assert len(panel['rows']) == 19
        assert panel['seeds'] == ([31001, 31013, 31019, 31033, 31039] if panel['years'] == 2 else [31001])
        for row in panel['rows']:
            for cell in row['cells'].values():
                assert all(p['observation_status'] == 'complete' for p in cell['points'])
                jobs.update(p['job_id'] for p in cell['points'])
    assert len(jobs) == 90


def test_v2_abstract_means_recompute_from_retained_raw_scores():
    scores = read('paper/generated/native-design-v2/cross-score-data.json')
    rows = {r['label']: r for r in scores['panels'][0]['rows']}
    def mean(label, objective):
        values = [p['value'] for p in rows[label]['cells'][objective]['points']]
        assert len(values) == 5
        return sum(values) / len(values)
    assert mean('reference:open-seed', 'selective') == pytest.approx(2.58)
    assert mean('selected:selective:code-and-graph', 'selective') == pytest.approx(1.92)
    assert mean('selected:selective:code-fixed-graph', 'selective') == pytest.approx(1.92)
    assert mean('reference:open-no-review-reject-all', 'selective') == 0
    assert mean('selected:throughput:code-and-graph', 'throughput') == pytest.approx(-6.2)
    assert mean('reference:open-accept-all', 'throughput') == pytest.approx(-6.2)


def test_v2_spec_inspection_and_runtime_categories_do_not_claim_causality():
    evidence = read('research/results/native-design-freedom-v2-paper-evidence-v1.json')
    inspection = evidence['spec_inspection']
    assert sha(inspection['script']) == inspection['script_sha256']
    assert inspection['complete_specs_rejoined'] == 64
    assert inspection['all_trial_status_and_own_loss_rows_rejoined'] == 120
    assert not inspection['outside_mechanisms'] and not inspection['nonparameter_node_fields']
    assert not inspection['node_id_change_rows'] and not inspection['node_order_change_rows']
    assert inspection['selected_representatives_rejoined'] == 10
    assert inspection['all_exact_tied_ids_rejoined']
    assert sum(inspection['runtime_failure_counts'].values()) == 31
    assert evidence['new_model_calls'] == evidence['new_code_executions'] == 0


def test_v2_measured_costs_keep_cache_missingness_and_overlapping_times():
    evidence = read('research/results/native-design-freedom-v2-paper-evidence-v1.json')
    scientist = evidence['scientist_costs']; groups = evidence['auxiliary_costs']['groups']
    assert scientist['completed_responses'] == scientist['wire_inputs'] == 16043
    assert scientist['physical_response_journals'] == 194
    assert scientist['wire_inputs_without_committed_reply'] == scientist['provider_total_component_disagreements'] == 0
    usage = scientist['usage']
    assert usage['total_tokens']['recorded_sum'] == sum(usage[k]['recorded_sum'] for k in ('prompt_tokens', 'completion_tokens'))
    assert usage['cached_prompt_tokens']['recorded_sum'] <= usage['prompt_tokens']['recorded_sum']
    tex = (ROOT / 'paper/submission-v2.tex').read_text()
    for label, count, input_count, output_count in (
        ('Scientists (including partial worlds)', 16043, 15547758, 1473665),
        ('Designer proposals', 1387, 25969867, 267057),
        ('Designer calibration', 84, 808832, 3819)):
        assert label + '&' + '&'.join(format(v, ',') for v in (count, input_count, output_count)) + r'\\' in tex
    assert groups['designer-proposal']['completion_record_available'] == 1387
    assert groups['designer-proposal']['final_response_reported'] == 1385
    assert sum(v['request_intents'] for v in groups.values()) == 1764
    for key in ('role-load-designer', 'role-load-scientist'):
        assert groups[key]['measurements']['native_prompt_eval_count']['recorded_sum'] is None
        assert not groups[key]['unknown_usage_imputed']
    assert not evidence['auxiliary_costs']['cached_prompt_counts_added_to_input_totals']
    assert evidence['proposal_and_load_times_are_overlapping_scopes']
    assert evidence['not_total_project_compute']
