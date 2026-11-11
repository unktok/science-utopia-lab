"""Bind manuscript diagnostics to retained observations, not live runs."""
import hashlib
import json
from pathlib import Path
import posixpath
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    return json.loads((ROOT / name).read_text())


def test_all_eight_partial_probe_rows_match_saved_functions_and_frames():
    probe = load('research/data/causal-authoring-assay-v1/fixed-record-probe.json')
    policies = load('research/data/causal-authoring-assay-v1/policies.json')
    assert len(probe['slots']) == len(policies['slots']) == 8
    assert probe['native_worlds'] == probe['model_calls'] == 0
    assert not probe['measured_candidate_losses']
    expected = {
        'throughput-h0-off': ('Source', 'Accepts all 29 addressed papers'),
        'throughput-h0-on': ('Source', 'Accepts all 29 addressed papers'),
        'efficiency-h0-on': ('Source', '\\code{KeyError: world} on all 4 inputs'),
        'efficiency-h0-off': ('Numeric', 'Unchanged selector rejects 29; edited upstream is not executed'),
        'throughput-h1-on': ('Source', 'Empty-cycle output on all 4 nonempty inputs; identity coverage fails'),
        'throughput-h1-off': ('Source', 'Accepts all 29 addressed papers'),
        'efficiency-h1-off': ('Source', 'Accepts one per input, rejects the remaining 25'),
        'efficiency-h1-on': ('Source', 'Accepts all 29 addressed papers'),
    }
    text = (ROOT / 'paper/integrated/design-diagnostics.tex').read_text()
    returned = covered = 0
    by_id = {p['id']: p for p in policies['slots']}
    for slot in probe['slots']:
        identity = slot['id']; policy = by_id[identity]
        assert slot['candidate_sha256'] == policy['candidate_sha256']
        loss, history, access = identity.split('-')
        edit, description = expected[identity]
        row = f"{'T' if loss == 'throughput' else 'E'} & {history.upper()} & {'Yes' if access == 'on' else 'No'} & {edit} & {description}"
        assert row in text
        assert all(not p.startswith('reference/') for p in policy['read_file_counts'])
        frames = slot['frames']; assert len(frames) == 4
        successful = [f for f in frames if f['status'] == 'executed']
        returned += len(successful)
        covered += sum(f['emitted_summary']['exact_identity_coverage'] for f in successful)
        if identity == 'efficiency-h0-on':
            assert not successful and all("KeyError: 'world'" in f['error'] for f in frames)
        elif identity == 'throughput-h1-on':
            assert all(f['emitted_summary']['empty_cycle_marker'] and
                       not f['emitted_summary']['exact_identity_coverage'] for f in frames)
        else:
            accepted = sum(f['emitted_summary']['decision_labels'].get('accept', 0) for f in frames)
            assert accepted == (0 if identity == 'efficiency-h0-off' else
                                4 if identity == 'efficiency-h1-off' else 29)
    assert returned == 28 and covered == 24


def test_diagnostic_costs_keep_readiness_load_and_missing_usage_separate():
    costs = load('research/data/causal-authoring-assay-v1/costs.json')
    assert costs['authoring']['chat_posts'] == 110
    assert costs['authoring']['prompt_tokens']['known_sum'] == 2225666
    assert costs['authoring']['output_tokens']['known_sum'] == 23017
    assert costs['readiness']['chat_posts'] == 58
    assert costs['readiness']['prompt_tokens']['known_sum'] == 618249
    assert costs['readiness']['output_tokens']['known_sum'] == 3574
    loads = costs['explicit_empty_prompt_loads']
    assert loads['confirmed_empty'] == loads['requests'] == 10
    assert loads['unreported_output_token_counts'] == loads['unreported_prompt_token_counts'] == 10
    assert round(costs['observed_start_to_last_chat_response_seconds'], 2) == 1861.22
    assert costs['new_native_worlds'] == costs['new_scientist_inference'] == 0


def test_panel_counts_are_decision_records_and_fixed_readouts_not_new_worlds():
    report = load('research/data/native-panel-sensitivity-v1/report.json')
    assert report['summary'] == {
        'complete_physical_worlds': 44, 'incomplete_physical_worlds': 5,
        'complete_worlds_with_nonzero_readout_range': 24,
        'reviewed_accepted_decision_records': 217,
        'unreviewed_accepted_decision_records': 46,
    }
    assert report['new_model_calls'] == report['new_native_worlds'] == 0
    assert report['new_authored_code_executions'] == 0
    assert not report['cost_of_omitted_reviews_removed']
    assert not report['independent_samples_inferred_from_subsets']
    text = (ROOT / 'paper/integrated/design-diagnostics.tex').read_text()
    for boundary in ('not six valid whole institutions', 'not confidence',
                     'not actual reading', 'not counted here as a',
                     'adds no new loss', 'actually performed'):
        assert boundary in text


def test_new_build_binds_its_own_source_assets_and_evidence_without_rewriting_history():
    receipt = load('paper/integrated-diagnostics-build-v1.json')
    assert receipt['schema'] == 'scienceutopia.integrated-diagnostics-paper-build.v1'
    assert not receipt['artificial_page_cap']
    original = {}
    for group in ('source_files', 'figure_files', 'support_files', 'evidence_files'):
        files = receipt[group]['files']
        assert len(files) == len(set(files))
        hashes = {}
        for name in files:
            assert name == posixpath.normpath(name) and not name.startswith(('/', '../'))
            data = subprocess.check_output(['git', 'show', receipt['source_commit'] + ':' + name], cwd=ROOT)
            hashes[name] = hashlib.sha256(data).hexdigest()
            if group == 'source_files':
                original[name] = data.decode()
        observed = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert observed == receipt[group]['manifest_sha256'], group
    visited = set(); pending = [receipt['entrypoint']]
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        pending.extend(posixpath.normpath('paper/' + path + ('' if path.endswith('.tex') else '.tex'))
                       for path in re.findall(r'\\input\{([^}]+)\}', original[name]))
    assert visited == set(original)
    body = '\n'.join(original.values())
    figures = re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', body)
    assert len(figures) == receipt['figures'] == 20
    assert {posixpath.normpath('paper/' + name) for name in figures} == set(receipt['figure_files']['files'])
    assert body.count('\\begin{table}') == receipt['tables'] == 18
    labels = re.findall(r'\\label\{([^}]+)\}', body)
    assert len(labels) == len(set(labels))
    assert set(re.findall(r'\\ref\{([^}]+)\}', body)) <= set(labels)
    assert '\\label{sec:design-diagnostics}' in body
    assert receipt['build']['text_identical'] and receipt['build']['exit_codes'] == [0, 0]
    assert receipt['build']['downloads'] == receipt['build']['off_page_text_words'] == 0
    for name, expected in receipt['preserved_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert not receipt['scientific_scope']['ongoing671436a_comparison_counted_as_completed']


def test_reviewed_new_pdf_is_the_exact_separate_artifact():
    receipt = load('paper/integrated-diagnostics-build-v1.json')
    pdf = ROOT / receipt['output']
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == receipt['pdf_sha256']
    assert receipt['visual_review']['all_final_pages_reviewed']
    assert receipt['visual_review']['pages_reviewed'] == receipt['pages'] == 47
    if shutil.which('pdfinfo'):
        info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
        assert re.search(r'^Pages:\s+47$', info, re.M)
    if shutil.which('pdftotext'):
        data = subprocess.check_output(['pdftotext', str(pdf), '-'])
        assert hashlib.sha256(data).hexdigest() == receipt['build']['text_sha256']
        assert b'??' not in data and b'ZZPROTECTED' not in data
        assert b'Authority, authoring and measurement diagnostics' in data
