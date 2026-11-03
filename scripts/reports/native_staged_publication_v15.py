"""Bind audited staged-v15 results, source-scoped tests and owner-reviewed assets.

Read-only verification only: no inference, world, figure/PDF generation or repair.
The caller supplies explicit paper-owner visual-review confirmation; this utility
checks identities/counts/hashes and never pretends to perform visual inspection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _hash(value, size=64):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def asset(path, root=ROOT):
    path = Path(path).resolve()
    _require(path.is_file(), 'missing publication asset: ' + str(path))
    return {'path': str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def _json(path):
    value = json.loads(Path(path).read_text())
    _require(value.get('content_sha256') == digest({k: v for k, v in value.items() if k != 'content_sha256'}),
        'content hash differs: ' + str(path))
    return value


def revision(value, root=ROOT):
    _require(_hash(value, 40), 'exact40-hex source commit required')
    actual = subprocess.check_output(['git', 'rev-parse', '--verify', value + '^{commit}'], cwd=root, text=True).strip()
    _require(actual == value, 'unresolved source commit')
    return actual


def _blob(source, path, root):
    _require(not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts,
        'unsafe repository source path')
    return hashlib.sha256(subprocess.check_output(['git', 'show', source + ':' + path], cwd=root)).hexdigest()


def audited_result(path, *, analysis_source, operational, root=ROOT):
    value = _json(path)
    _require(value.get('schema') == 'scienceutopia.native-staged-search-audit-summary.v15'
        and value.get('classification') == 'actual-local-qwen-staged-native-search-development-v15',
        'actual compact staged-v15 audit required')
    source = revision(value['source_commit'], root)
    _require(value.get('status') in {'complete', 'budget-complete-with-failures'}
        and value.get('budget_terminal') is True and value.get('queue_terminal') is True
        and value.get('planned_native_slots') == value.get('consumed_native_slots') == 4,
        'terminal separately budgeted four-slot evidence required')
    claims = value['claims']
    _require(claims.get('operational_two_generation_native_feedback_arm') is operational,
        'actual operational feedback claim differs')
    _require(all(claims.get(key) is False for key in ('held_out', 'scientific_benefit_established',
        'designer_improvement_established', 'method_superiority_established', 'model_weights_trained',
        'full_world_pathwise_autograd', 'same_society_adoption', 'browser_consent_claimed', 'scripted_HTTP_only')),
        'unsupported scientific/held-out/browser claim')
    if not operational:
        _require(value.get('status') == 'budget-complete-with-failures' and value.get('technical_failures') == 4
            and value.get('physical_native_worlds') == value.get('physical_researcher_responses') == 0,
            'original a1 failures must remain failures with zero executed worlds')
    else:
        _require(claims.get('actual_local_Qwen_automatic_loop') is True
            and value.get('physical_native_worlds', 0) >= 2 and value.get('physical_researcher_responses', 0) > 0,
            'actual original-world two-generation feedback evidence required')
    proof = value['audit']
    _require(proof.get('new_model_calls') == proof.get('new_container_executions') == 0
        and proof.get('exact_raw_tools_draft_source_definition_replayed') is True
        and proof.get('own_history_loss_and_all_ties_replayed') is True
        and value.get('exact_full_audit_reproducible') is True
        and _hash(value.get('exact_full_audit_content_sha256')), 'read-only independent replay proof required')
    _require(proof['analysis_source_sha256'] == _blob(analysis_source,
        'scripts/analyze_native_staged_search_v15.py', root), 'matching analysis source differs')
    source_proof = proof['source_proofs']
    critical = {'utopia/optimization/native_staged_author_v15.py', 'utopia/optimization/native_search_v15.py',
        'utopia/optimization/native_adaptive_search.py', 'utopia/optimization/native_factory.py',
        'utopia/system/native_kernel.py', 'scripts/run_native_staged_search_v15.py'}
    _require(source_proof['status'] == 'verified-exact-staged-runtime-driver-helper-source-blobs'
        and critical <= set(source_proof['files']), 'matching runtime source proof required')
    for name, hashes in source_proof['files'].items():
        _require(_hash(hashes.get('actual_source_sha256'))
            and hashes['actual_source_sha256'] == hashes.get('analysis_source_sha256'), 'runtime source proof differs')
        if name in critical:
            _require(_blob(source, name, root) == _blob(analysis_source, name, root) == hashes['actual_source_sha256'],
                'critical actual/analysis Git blobs differ')
    inventory = proof['raw_input_sha256s']
    _require(isinstance(inventory, dict) and inventory and all(_hash(v) for v in inventory.values())
        and len(inventory) == proof['raw_files_verified_unchanged']
        and digest(inventory) == proof['raw_inventory_sha256'], 'raw inventory identity differs')
    raw = Path(proof['raw_root']).resolve()
    found = {}
    for file in sorted(raw.rglob('*')):
        _require(not file.is_symlink(), 'raw inventory contains a symbolic link')
        if file.is_file():
            found[str(file.relative_to(raw))] = asset(file, root)['sha256']
    _require(found == inventory, 'raw inventory changed after independent audit')
    return {'file': asset(path, root), 'content_sha256': value['content_sha256'], 'source_commit': source,
        'matching_analysis_commit': analysis_source, 'status': value['status'], 'claims': claims,
        'raw_root': str(raw), 'raw_inventory_sha256': proof['raw_inventory_sha256'],
        'raw_files_verified_unchanged': len(inventory),
        'independent_replay_is_not_rerun_by_publication_utility': True}


def recorded_process(directory, name, *, root=ROOT, expected_source=None, junit=False, full_suite=False,
                     expected_exit=0):
    path = directory / (name + '-receipt.json')
    value = json.loads(path.read_text())
    _require(value.get('status') == 'exited' and value.get('exit_code') == expected_exit,
        'process is unfinished/failed, not a pass: ' + name)
    cwd = Path(value['cwd'])
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip()
    revision(source, root)
    _require(expected_source is None or source == expected_source, 'retained process source differs: ' + name)
    result = {'source_commit': source, 'receipt': asset(path, root), 'log': asset(value['log'], root),
        'command': value['command'], 'environment': value.get('environment', {}),
        'started_utc': value['started_utc'], 'ended_utc': value['ended_utc'], 'exit_code': expected_exit,
        'suite_passed': expected_exit == 0 if junit else None,
        'outcome': 'passed' if expected_exit == 0 else 'failed-not-a-pass',
        'source_binding_basis': 'HEAD of retained receipt cwd at verification; supervisor has no start-commit field',
        'scope': 'full tests tree at this named source only' if full_suite else 'exact recorded command at this named source',
        'zero_process_exit_is_not_scientific_success': not junit}
    if junit:
        xml = directory / (name + '.xml')
        tree = ET.parse(xml).getroot()
        suites = [s for s in tree.iter('testsuite') if not list(s.iter('testsuite'))[1:]]
        totals = {key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
        _require(totals['tests'] > 0 and all(v >= 0 for v in totals.values())
            and totals['skipped'] + totals['failures'] + totals['errors'] <= totals['tests'],
            'JUnit is empty/failed/inconsistent: ' + name)
        _require((not totals['failures'] and not totals['errors']) if expected_exit == 0 else
            totals['failures'] + totals['errors'] > 0, 'JUnit does not match process pass/failure: ' + name)
        _require(any(str(arg) in {'--junitxml=' + str(xml), '--junitxml=' + str(xml.resolve())}
            for arg in value['command']), 'JUnit does not match the recorded command')
        if full_suite:
            command = value['command']; position = command.index('pytest')
            args = command[position + 1:]
            _require('tests' in args and not any(arg in {'-k', '-m', '--collect-only', '--lf', '--ff'}
                or arg.startswith(('--ignore', '--deselect')) for arg in args), 'filtered command is not a full suite')
        result.update(junit=asset(xml, root), counts=totals)
        if expected_exit == 0:
            result['passed'] = totals['tests'] - totals['skipped']
        else:
            result['passing_test_cases_within_failed_suite'] = (
                totals['tests'] - totals['skipped'] - totals['failures'] - totals['errors'])
    return result


def page_selection(value, count):
    found = set()
    for group in value.split(','):
        _require(re.fullmatch(r'\d+(?:-\d+)?', group.strip()) is not None, 'invalid enlarged page selection')
        ends = [int(v) for v in group.strip().split('-')]
        first, last = ends[0], ends[-1]
        _require(1 <= first <= last <= count, 'enlarged page selection is out of range')
        found.update(range(first, last + 1))
    return found


def rendered_assets(directory, prefix, expected, root):
    from PIL import Image
    files = sorted(directory.glob(prefix + '-*.png'))
    numbers = []
    for path in files:
        match = re.fullmatch(prefix + r'-(\d+)\.png', path.name)
        _require(match is not None, 'unexpected review render filename')
        numbers.append(int(match[1]))
        with Image.open(path) as image:
            image.verify()
    _require(len(numbers) == len(set(numbers)) and set(numbers) == set(expected),
        'review render/sheet/enlarged pages do not match the declared set')
    return [asset(path, root) for path in files]


def build_verification(args, *, root=ROOT):
    root = root.resolve()
    paper = revision(args.paper_source, root)
    _require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == paper,
        'paper source differs from the reviewed build checkout HEAD')
    _require(args.reviewed_all_pages is True and args.pages > 0, 'explicit complete visual review confirmation required')
    analyses = {'a1': revision(args.a1_analysis_source, root), 'a2': revision(args.a2_analysis_source, root)}
    audits = {name: audited_result(root / 'research/results' / ('native-staged-search-v15-' + name + '.json'),
        analysis_source=source, operational=name == 'a2', root=root) for name, source in analyses.items()}
    _require(audits['a1']['source_commit'] != audits['a2']['source_commit'], 'separate actual revision source pins required')
    v = args.verification_directory
    checks = {}
    for name, source, junit, full in (
        ('a1-job', audits['a1']['source_commit'], False, False),
        ('exact-source-tests', audits['a1']['source_commit'], True, True),
        ('a2-job', audits['a2']['source_commit'], False, False), ('final-focused', paper, True, False)):
        checks[name] = recorded_process(v, name, root=root, expected_source=source, junit=junit, full_suite=full)
    first_full = json.loads((v / 'publication-source-tests-receipt.json').read_text())
    first_failed = first_full.get('status') == 'exited' and first_full.get('exit_code') == 1
    checks['publication-source-tests'] = recorded_process(v, 'publication-source-tests', root=root,
        junit=True, full_suite=True, expected_exit=1 if first_failed else 0)
    latest_full = 'publication-source-tests'
    if first_failed or (v / 'publication-source-tests-r2-receipt.json').exists():
        checks['publication-source-tests-r2'] = recorded_process(v, 'publication-source-tests-r2',
            root=root, junit=True, full_suite=True)
        latest_full = 'publication-source-tests-r2'
    pdf = root / 'output/pdf/science-utopia-lab-working-paper.pdf'
    info = subprocess.check_output(['pdfinfo', str(pdf)], text=True)
    match = re.search(r'^Pages:\s+(\d+)\s*$', info, re.MULTILINE)
    _require(match is not None and int(match[1]) == args.pages, 'final PDF page count differs')
    pages = rendered_assets(args.review_directory / 'pages', 'page', range(1, args.pages + 1), root)
    sheets = rendered_assets(args.review_directory / 'sheets', 'sheet', range(1, (args.pages + 11) // 12 + 1), root)
    enlarged = rendered_assets(args.review_directory / 'enlarged', 'page', page_selection(args.enlarged_pages, args.pages), root)
    artifacts = [asset(pdf, root)]
    manifests = sorted((root / 'paper/figures').glob('native-staged-search-v15*.manifest.json'))
    _require(manifests, 'staged actual figure manifest/quartet required')
    for path in manifests:
        manifest = _json(path)
        _require(manifest.get('schema') == 'scienceutopia.native-staged-search-figure.v15'
            and manifest.get('classification') == 'actual-local-qwen-staged-native-search-development-v15', 'actual figure required')
        for name in ('a1', 'a2'):
            proof = manifest['audits'][name]
            _require(proof['source_commit'] == audits[name]['source_commit']
                and proof['content_sha256'] == audits[name]['content_sha256']
                and proof['file_sha256'] == audits[name]['file']['sha256'], 'figure independent audit binding differs')
        _require({Path(name).suffix for name in manifest['files']} == {'.png', '.svg', '.pdf'}
            and len(manifest['files']) == 3, 'figure must have exactly png/svg/pdf plus its manifest')
        for name, expected in manifest['files'].items():
            _require(Path(name).name == name, 'unsafe figure asset filename')
            found = asset(path.parent / name, root)
            _require(found['sha256'] == expected, 'figure file differs from its manifest')
            artifacts.append(found)
        artifacts.append(asset(path, root))
    screenshot_dirs = sorted(p for p in (root / 'game-ui-v2/screenshots').glob('*staged*actual*qa*') if p.is_dir())
    _require(screenshot_dirs, 'actual staged desktop/mobile screenshot directories required')
    for directory in screenshot_dirs:
        files = sorted(p for p in directory.rglob('*') if p.is_file())
        _require(any(p.suffix.lower() == '.png' for p in files), 'actual screenshot directory has no PNG')
        artifacts.extend(asset(p, root) for p in files)
    result = {'schema': 'scienceutopia.native-staged-publication-verification.v15',
        'status': 'source-scoped-tests-audited-actual-feedback-and-owner-reviewed-artifacts-verified',
        'paper_build_source': paper, 'audits': audits, 'checks': checks, 'artifacts': artifacts,
        'latest_publication_full_suite_check': latest_full,
        'counts_are_not_pooled': True, 'full_suite_results_apply_only_to_their_named_sources': True,
        'current_publication_all_runtime_blobs_equal_actual_experiments_claimed': False,
        'all_non_scale_research_completed_claimed': False,
        'optional_current_protocol_role_capability_and_history_improvements_used_in_a2': False,
        'a1_failures_retained_separately': True,
        'pdf_review': {'pages': args.pages, 'all_pages_visually_inspected': True,
            'confirmation': 'explicit paper-owner --reviewed-all-pages; this utility checks assets, not visual quality',
            'render_binding': 'owner confirmation plus current PDF/page counts and render hashes; no independent rerender',
            'rendered_pages': pages, 'sheets': sheets, 'enlarged_pages': sorted(page_selection(args.enlarged_pages, args.pages)),
            'enlarged': enlarged},
        'prior_pdf': asset(v / 'prior-pdf/science-utopia-lab-v14.pdf', root),
        'new_model_calls': 0, 'new_native_trials': 0, 'no_additional_actual_trials_scheduled_by_this_utility': True}
    result['content_sha256'] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('verification-directory', 'review-directory', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('paper-source', 'a1-analysis-source', 'a2-analysis-source', 'enlarged-pages'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--pages', type=int, required=True)
    parser.add_argument('--reviewed-all-pages', action='store_true', required=True)
    args = parser.parse_args()
    _require(not args.output.exists(), 'verification receipt already exists; never overwrite it')
    result = build_verification(args)
    _require(not args.output.exists(), 'verification receipt appeared concurrently; never overwrite it')
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False, indent=2)
    print(json.dumps({'output': str(args.output), 'content_sha256': result['content_sha256']}))


if __name__ == '__main__':
    main()
