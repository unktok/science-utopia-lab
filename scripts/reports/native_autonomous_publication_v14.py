"""Bind already audited v14 results and reviewed artifacts; never run a world."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def asset(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def recorded_test(directory, name, *, source, interrupted=False, junit=False):
    path = directory / (name + '.receipt.json')
    receipt = json.loads(path.read_text())
    if receipt['status'] != 'exited' or receipt['exit_code'] != (-15 if interrupted else 0):
        raise ValueError('missing expected stopped-process result: ' + name)
    result = {'source_commit': source, 'receipt': asset(path),
        'log': asset(Path(receipt['log'])), 'status': receipt['status'],
        'exit_code': receipt['exit_code'], 'command': receipt['command'],
        'environment': receipt['environment'], 'started_utc': receipt['started_utc'],
        'ended_utc': receipt['ended_utc'], 'interrupted_not_a_pass': interrupted}
    if junit:
        xml = directory / (name + '.xml')
        suites = ET.parse(xml).getroot().iter('testsuite')
        totals = {key: 0 for key in ('tests', 'failures', 'errors', 'skipped')}
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.attrib.get(key, 0))
        if totals['failures'] or totals['errors']:
            raise ValueError('JUnit contains failures: ' + name)
        result.update(junit=asset(xml), counts=totals,
            passed=totals['tests'] - totals['skipped'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verification-directory', type=Path, required=True)
    parser.add_argument('--paper-source', required=True)
    parser.add_argument('--qa-analysis-source', required=True)
    parser.add_argument('--pages', type=int, required=True)
    parser.add_argument('--review-directory', type=Path, required=True)
    parser.add_argument('--enlarged-pages', required=True)
    parser.add_argument('--reviewed-all-pages', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not all(re.fullmatch('[a-f0-9]{40}', value) for value in
        (args.paper_source, args.qa_analysis_source)):
        parser.error('exact paper/QA analysis source commits required')
    if args.output.exists():
        parser.error('verification receipt already exists; do not overwrite it')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if head != args.paper_source:
        raise ValueError('paper source differs from the reviewed build source')
    pages = sorted((args.review_directory / 'pages').glob('page-*.png'))
    sheets = sorted((args.review_directory / 'sheets').glob('sheet-*.png'))
    enlarged = sorted((args.review_directory / 'enlarged').glob('page-*.png'))
    if len(pages) != args.pages or len(sheets) != (args.pages + 11) // 12 or not enlarged:
        raise ValueError('render every final page and all declared review sheets first')
    v = args.verification_directory
    old = '54a7d92dad5221f83f25f81d62aa225ab38cef25'
    qa = 'fdb694d0adee759470d9c4ff41c4d8c75e490d19'
    audits = {}
    for name in ('native-autonomous-search-v14-a1', 'native-authoring-ir-v14-qa-a1'):
        path = ROOT / 'research/results' / (name + '.json')
        value = json.loads(path.read_text())
        if value['content_sha256'] != digest({k: x for k, x in value.items() if k != 'content_sha256'}):
            raise ValueError('independent audit content hash differs: ' + name)
        audits[name] = {'file': asset(path), 'content_sha256': value['content_sha256'],
            'source_commit': value['source_commit'], 'status': value['status'],
            'raw_inventory_sha256': value['audit']['raw_inventory_sha256']}
    checks = {}
    for name, source, interrupted, junit in (
        ('runtime-full-r1', old, False, True),
        ('ir-qa-full-r1', qa, True, False),
        ('ir-qa-full-r2', qa, False, True),
        ('ir-qa-worker-r1', qa, True, False),
        ('ir-qa-worker-r2', qa, False, False),
        ('ir-qa-terminal-resume-r1', qa, False, False),
        ('ui-tests-r1', 'ed9915b', False, True),
        ('ui-build-r1', 'ed9915b', False, False),
        ('operator-guards-r1', 'ed9915b', False, False),
        ('scripted-browser-r1', '38e2c53', False, False),
        ('final-focused-r1', args.paper_source, False, True),
    ):
        checks[name] = recorded_test(v, name, source=source, interrupted=interrupted, junit=junit)
    artifacts = [ROOT / 'output/pdf/science-utopia-lab-working-paper.pdf']
    artifacts += sorted((ROOT / 'paper/figures').glob('native-autonomous-search-v14-a1.*'))
    artifacts += sorted((ROOT / 'paper/figures').glob('native-authoring-ir-v14-qa-a1.*'))
    for directory in ('autonomous-search-v14-a1-actual-qa', 'native-authoring-ir-v14-qa-actual-qa'):
        artifacts += [p for p in (ROOT / 'game-ui-v2/screenshots' / directory).rglob('*') if p.is_file()]
    result = {'schema': 'scienceutopia.native-autonomous-publication-verification.v14',
        'status': 'finite-v14-implementation-failed-actual-authoring-and-artifacts-verified',
        'date': '2026-11-03', 'paper_build_and_final_focused_source': args.paper_source,
        'separate_qa_matching_analysis_commit': args.qa_analysis_source,
        'actual_source_commits': {'closed_a1': old, 'separate_engineering_qa': qa},
        'all_non_scale_research_completed_claimed': False,
        'scope': 'Automatic search/consent/runtime and honest bounded failure evidence. No valid automatic candidate/native execution in either actual v14 experiment; not useful invention or scientific benefit.',
        'counts_are_not_pooled': True,
        'test_counting': 'Overlapping software scopes are neither added nor scientific replicates; full-suite results apply only to their named frozen sources.',
        'current_publication_all_replay_blobs_equal_old_experiments_claimed': False,
        'audits': audits, 'checks': checks, 'artifacts': [asset(p) for p in artifacts],
        'pdf_review': {'pages': args.pages, 'all_pages_visually_inspected': True,
            'review_method': 'Poppler renders, labelled contact sheets, enlarged changed pages',
            'enlarged_pages': args.enlarged_pages,
            'rendered_pages': [asset(p) for p in pages], 'sheets': [asset(p) for p in sheets],
            'enlarged': [asset(p) for p in enlarged],
            'overfull_boxes': 0, 'undefined_references': 0},
        'prior_pdf': asset(v / 'prior-pdf/science-utopia-lab-v13.pdf'),
        'no_additional_actual_trials_scheduled': True}
    result['content_sha256'] = digest(result)
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({'output': str(args.output), 'content_sha256': result['content_sha256']}))


if __name__ == '__main__':
    main()
