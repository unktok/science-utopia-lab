"""SCRIPTED publication-receipt verification fixtures, not scientific evidence."""
from argparse import Namespace
import json
from pathlib import Path

from PIL import Image
import pytest

from scripts.reports import native_staged_publication_v15 as report
from utopia.system.design_patch import digest


def save(path, value, hashed=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if hashed:
        value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    path.write_text(json.dumps(value))


@pytest.fixture
def publication(tmp_path, monkeypatch):
    """Entirely fake temporary assets; mocked Git/PDF metadata, no production writes."""
    root = tmp_path / 'SCRIPTED-publication-fixture'
    root.mkdir()
    sources = {'a1': 'a' * 40, 'a2': 'b' * 40, 'paper': 'c' * 40,
        'analysis1': 'd' * 40, 'analysis2': 'e' * 40, 'full': 'f' * 40}
    monkeypatch.setattr(report, 'revision', lambda value, root: value)
    monkeypatch.setattr(report, '_blob', lambda *args: 'a' * 64)
    cwd_sources = {str(root): sources['paper']}
    def command(args, cwd=None, **kwargs):
        if args[0] == 'pdfinfo':
            return 'Pages: 2\n'
        assert args == ['git', 'rev-parse', 'HEAD']
        return cwd_sources[str(cwd)] + '\n'
    monkeypatch.setattr(report.subprocess, 'check_output', command)
    audits = {}
    for name in ('a1', 'a2'):
        operational = name == 'a2'
        raw = root / 'raw' / name; raw.mkdir(parents=True)
        (raw / 'SCRIPTED-raw.txt').write_text(name)
        inventory = {'SCRIPTED-raw.txt': report.asset(raw / 'SCRIPTED-raw.txt', root)['sha256']}
        claims = {key: False for key in ('held_out', 'scientific_benefit_established',
            'designer_improvement_established', 'method_superiority_established', 'model_weights_trained',
            'full_world_pathwise_autograd', 'same_society_adoption', 'browser_consent_claimed', 'scripted_HTTP_only')}
        claims.update(operational_two_generation_native_feedback_arm=operational,
            actual_local_Qwen_automatic_loop=operational)
        value = {'schema': 'scienceutopia.native-staged-search-audit-summary.v15',
            'classification': 'actual-local-qwen-staged-native-search-development-v15',
            'source_commit': sources[name], 'status': 'complete' if operational else 'budget-complete-with-failures',
            'budget_terminal': True, 'queue_terminal': True, 'planned_native_slots': 4, 'consumed_native_slots': 4,
            'physical_native_worlds': 2 if operational else 0,
            'physical_researcher_responses': 2 if operational else 0, 'technical_failures': 0 if operational else 4,
            'claims': claims, 'exact_full_audit_reproducible': True, 'exact_full_audit_content_sha256': 'b' * 64,
            'audit': {'new_model_calls': 0, 'new_container_executions': 0,
                'exact_raw_tools_draft_source_definition_replayed': True,
                'own_history_loss_and_all_ties_replayed': True, 'analysis_source_sha256': 'a' * 64,
                'source_proofs': {'status': 'verified-exact-staged-runtime-driver-helper-source-blobs',
                    'files': {name: {'actual_source_sha256': 'a' * 64, 'analysis_source_sha256': 'a' * 64}
                        for name in ('utopia/optimization/native_staged_author_v15.py',
                            'utopia/optimization/native_search_v15.py', 'utopia/optimization/native_adaptive_search.py',
                            'utopia/optimization/native_factory.py', 'utopia/system/native_kernel.py',
                            'scripts/run_native_staged_search_v15.py')}},
                'raw_root': str(raw), 'raw_input_sha256s': inventory,
                'raw_files_verified_unchanged': 1, 'raw_inventory_sha256': digest(inventory)}}
        path = root / 'research/results' / ('native-staged-search-v15-' + name + '.json')
        save(path, value, hashed=True); audits[name] = (path, value)
    v = root / 'verification'
    for name, source, junit in (
        ('a1-job', sources['a1'], False), ('exact-source-tests', sources['a1'], True),
        ('a2-job', sources['a2'], False), ('publication-source-tests', sources['full'], True),
        ('final-focused', sources['paper'], True)):
        cwd = root / ('cwd-' + name); cwd.mkdir()
        cwd_sources[str(cwd)] = source
        log = v / (name + '.log'); log.parent.mkdir(exist_ok=True); log.write_text('SCRIPTED verification log')
        xml = v / (name + '.xml')
        command = ['python', '-m', 'pytest', 'tests', '-q', '--junitxml=' + str(xml)] if junit else ['SCRIPTED-driver']
        save(v / (name + '-receipt.json'), {'cwd': str(cwd), 'status': 'exited', 'exit_code': 0,
            'started_utc': 'SCRIPTED-start', 'ended_utc': 'SCRIPTED-end', 'log': str(log), 'command': command})
        if junit:
            xml.write_text('<testsuites><testsuite tests="3" skipped="1" failures="0" errors="0"/></testsuites>')
    paper = root / 'output/pdf/science-utopia-lab-working-paper.pdf'
    paper.parent.mkdir(parents=True); paper.write_bytes(b'SCRIPTED-PDF-not-a-real-document')
    old = v / 'prior-pdf/science-utopia-lab-v14.pdf'; old.parent.mkdir(); old.write_bytes(b'SCRIPTED-old-PDF')
    figure = root / 'paper/figures'; figure.mkdir(parents=True)
    files = {}
    for suffix in ('.png', '.svg', '.pdf'):
        path = figure / ('native-staged-search-v15-SCRIPTED' + suffix); path.write_bytes(suffix.encode())
        files[path.name] = report.asset(path, root)['sha256']
    save(figure / 'native-staged-search-v15-SCRIPTED.manifest.json', {
        'schema': 'scienceutopia.native-staged-search-figure.v15',
        'classification': 'actual-local-qwen-staged-native-search-development-v15', 'files': files,
        'audits': {name: {'source_commit': sources[name], 'content_sha256': value['content_sha256'],
            'file_sha256': report.asset(path, root)['sha256']} for name, (path, value) in audits.items()}}, hashed=True)
    review = root / 'review'
    for directory, names in (('pages', ('page-01.png', 'page-02.png')), ('sheets', ('sheet-01.png',)),
                             ('enlarged', ('page-02.png',))):
        for name in names:
            path = review / directory / name; path.parent.mkdir(parents=True, exist_ok=True)
            Image.new('RGB', (20, 20)).save(path)
    screenshot = root / 'game-ui-v2/screenshots/staged-v15-SCRIPTED-actual-qa/desktop.png'
    screenshot.parent.mkdir(parents=True); Image.new('RGB', (20, 20)).save(screenshot)
    args = Namespace(verification_directory=v, review_directory=review, paper_source=sources['paper'],
        a1_analysis_source=sources['analysis1'], a2_analysis_source=sources['analysis2'], pages=2,
        enlarged_pages='2', reviewed_all_pages=True)
    return root, args, audits


def test_source_scopes_are_not_pooled_or_relabelled_and_no_asset_is_overwritten(publication):
    root, args, audits = publication
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = report.build_verification(args, root=root)
    assert result['checks']['publication-source-tests']['source_commit'] == 'f' * 40
    assert result['paper_build_source'] == 'c' * 40
    assert result['checks']['exact-source-tests']['passed'] == 2
    assert result['counts_are_not_pooled'] and result['a1_failures_retained_separately']
    assert result['optional_current_protocol_role_capability_and_history_improvements_used_in_a2'] is False
    assert result['content_sha256'] == digest({k: v for k, v in result.items() if k != 'content_sha256'})
    assert before == {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('field,value', [('status', 'running'), ('exit_code', 1)])
def test_unfinished_or_failed_full_suite_is_never_a_pass(publication, field, value):
    root, args, _ = publication
    path = args.verification_directory / 'publication-source-tests-receipt.json'
    document = json.loads(path.read_text()); document[field] = value; save(path, document)
    with pytest.raises(ValueError):
        report.build_verification(args, root=root)


def test_failed_first_full_scope_is_retained_separately_and_corrected_second_scope_required(publication):
    root, args, _ = publication
    first = args.verification_directory / 'publication-source-tests-receipt.json'
    original = json.loads(first.read_text())
    failed = dict(original); failed['exit_code'] = 1; save(first, failed)
    xml = args.verification_directory / 'publication-source-tests.xml'
    xml.write_text('<testsuite tests="3" failures="1" errors="0" skipped="1"/>')
    with pytest.raises(FileNotFoundError):
        report.build_verification(args, root=root)
    second = args.verification_directory / 'publication-source-tests-r2-receipt.json'
    second_xml = args.verification_directory / 'publication-source-tests-r2.xml'
    original['command'] = [arg.replace(str(xml), str(second_xml)) for arg in original['command']]
    save(second, original)
    second_xml.write_text('<testsuite tests="3" failures="0" errors="0" skipped="1"/>')
    result = report.build_verification(args, root=root)
    retained = result['checks']['publication-source-tests']
    assert retained['outcome'] == 'failed-not-a-pass' and retained['suite_passed'] is False
    assert 'passed' not in retained and retained['passing_test_cases_within_failed_suite'] == 1
    assert result['checks']['publication-source-tests-r2']['passed'] == 2
    assert result['latest_publication_full_suite_check'] == 'publication-source-tests-r2'
    assert json.loads(first.read_text()) == failed


@pytest.mark.parametrize('kind', ['audit-hash', 'raw-file', 'raw-extra', 'a2-no-feedback', 'a1-false-success'])
def test_audit_raw_identity_and_claim_tampering_rejected(publication, kind):
    root, args, audits = publication
    path, value = audits['a1' if kind == 'a1-false-success' else 'a2']
    if kind == 'raw-file':
        (Path(value['audit']['raw_root']) / 'SCRIPTED-raw.txt').write_text('changed')
    elif kind == 'raw-extra':
        (Path(value['audit']['raw_root']) / 'extra.txt').write_text('unaccounted')
    else:
        if kind == 'a2-no-feedback': value['claims']['operational_two_generation_native_feedback_arm'] = False
        elif kind == 'a1-false-success': value['physical_native_worlds'] = 2
        else: value['status'] = 'tampered'
        save(path, value, hashed=kind != 'audit-hash')
    with pytest.raises(ValueError):
        report.build_verification(args, root=root)


@pytest.mark.parametrize('kind', ['missing-page', 'wrong-enlarged', 'unreviewed', 'changed-figure'])
def test_incomplete_or_unbound_visual_artifacts_rejected(publication, kind):
    root, args, _ = publication
    if kind == 'missing-page': (args.review_directory / 'pages/page-02.png').unlink()
    elif kind == 'wrong-enlarged': args.enlarged_pages = '1'
    elif kind == 'unreviewed': args.reviewed_all_pages = False
    else: next((root / 'paper/figures').glob('*.svg')).write_text('changed')
    with pytest.raises(ValueError):
        report.build_verification(args, root=root)


@pytest.mark.parametrize('selection', ['0', '3', '2-1', '1,,2', 'arbitrary'])
def test_enlarged_page_selection_is_exact_and_bounded(selection):
    with pytest.raises(ValueError):
        report.page_selection(selection, 2)


def test_junit_failures_and_filtered_full_command_are_rejected(publication):
    root, args, _ = publication
    xml = args.verification_directory / 'publication-source-tests.xml'
    xml.write_text('<testsuite tests="3" failures="1" errors="0" skipped="0"/>')
    with pytest.raises(ValueError, match='JUnit'):
        report.build_verification(args, root=root)
    xml.write_text('<testsuite tests="3" failures="0" errors="0" skipped="0"/>')
    path = args.verification_directory / 'publication-source-tests-receipt.json'
    value = json.loads(path.read_text()); value['command'].extend(['-k', 'one']); save(path, value)
    with pytest.raises(ValueError, match='filtered command'):
        report.build_verification(args, root=root)
