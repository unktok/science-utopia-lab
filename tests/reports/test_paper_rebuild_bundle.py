"""Explicit-subset staging QA; dummy document bytes, no PDF creation or inference."""
import json

import pytest

from scripts.reports import paper_rebuild_bundle as bundle


def fixture(tmp_path):
    root = tmp_path / 'source'; root.mkdir()
    bodies = {'LICENSE': b'SCRIPTED upstream notice; retain exact bytes',
        'paper/submission.tex': b'\\documentclass{article}\n\\usepackage{neurips_2025}\n\\input{child}\n\\bibliography{submission-sources}\n',
        'paper/submission-sources.bib': b'SCRIPTED bibliography',
        'paper/child.tex': b'\\includegraphics{figures/result.png}\n',
        'paper/figures/result.png': b'SCRIPTED not an actual bitmap',
        'paper/neurips_2025.sty': b'SCRIPTED upstream template credit',
        'output/pdf/working.pdf': b'SCRIPTED not an actual PDF'}
    receipt = {'schema': 'scienceutopia.working-paper-build.v2',
        'output': 'output/pdf/working.pdf', 'pdf_sha256': bundle.sha(bodies['output/pdf/working.pdf']),
        'tex_sha256': bundle.sha(bodies['paper/submission.tex']),
        'additional_bibliography_sha256': bundle.sha(bodies['paper/submission-sources.bib']),
        'additional_dependencies': {name: bundle.sha(body) for name, body in bodies.items()}}
    bodies['paper/submission-build-v2.json'] = json.dumps(receipt).encode()
    for name, body in bodies.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(body)
    policy = {'schema': 'scienceutopia.paper-rebuild-allowlist.v1',
        'status': 'local-working-draft-not-anonymous-not-release-cleared',
        'scope': 'SCRIPTED staging QA only', 'entrypoint': 'paper/submission.tex',
        'receipt': 'paper/submission-build-v2.json', 'files': sorted(bodies)}
    (root / 'unlisted-private').mkdir(); (root / 'unlisted-private/secret.txt').write_text('never copy')
    return root, bodies, policy


def test_only_explicit_files_are_copied_without_transforming_source_or_credits(tmp_path):
    root, bodies, policy = fixture(tmp_path); output = tmp_path / 'staged'
    r = bundle.stage(root, policy, output, source_commit='SCRIPTED')
    assert r['files'] == {n: bundle.sha(b) for n, b in bodies.items()}
    assert r['literal_tex_dependencies'] == sorted(n for n in bodies if n.startswith('paper/') and not n.endswith('.json'))
    assert not (output / 'unlisted-private').exists() and not (output / '.git').exists()
    assert all((root / n).read_bytes() == (output / n).read_bytes() == b for n, b in bodies.items())
    assert r['original_bytes_transformed'] is False and r['published_or_uploaded'] is False
    assert r['numerical_reproduction_or_clean_machine_build_claimed'] is False
    assert 'NOT an anonymous' in (output / 'REBUILD.md').read_text()
    with pytest.raises(ValueError, match='fresh destination'):
        bundle.stage(root, policy, output, source_commit='SCRIPTED')


@pytest.mark.parametrize('name', ['../secret', '/etc/passwd', '.git/config', 'paper/../x',
    'paper//x', 'paper/./x', 'paper\\x', '', None, 123])
def test_relative_paths_reject_traversal_hidden_and_ambiguous_names(name):
    with pytest.raises(ValueError): bundle.relative(name)


@pytest.mark.parametrize('change', ['tamper', 'missing-dependency', 'no-license', 'unbound', 'duplicate', 'anonymous'])
def test_invalid_or_misleading_subsets_fail_before_destination_creation(tmp_path, change):
    root, bodies, p = fixture(tmp_path); output = tmp_path / 'staged'
    if change == 'tamper': (root / 'paper/child.tex').write_text('changed')
    elif change == 'missing-dependency': p['files'].remove('paper/figures/result.png')
    elif change == 'no-license': p['files'].remove('LICENSE')
    elif change == 'unbound': p['files'] = sorted([*p['files'], 'unlisted-private/secret.txt'])
    elif change == 'duplicate': p['files'].append('LICENSE')
    else: p['status'] = 'anonymous-submission-ready'
    with pytest.raises(ValueError): bundle.stage(root, p, output, source_commit='SCRIPTED')
    assert not output.exists()


def test_source_symlinks_cannot_pull_unlisted_or_external_content_into_bundle(tmp_path):
    root, bodies, p = fixture(tmp_path)
    original = root / 'paper/child.tex'; moved = root / 'kept-child.tex'; original.rename(moved)
    original.symlink_to(moved)
    with pytest.raises(ValueError, match='linked'):
        bundle.stage(root, p, tmp_path / 'staged', source_commit='SCRIPTED')


def test_source_change_during_staging_is_detected_without_silently_repairing_or_removing_evidence(tmp_path, monkeypatch):
    root, bodies, p = fixture(tmp_path); original = bundle.read_file; counts = {}
    def changing(base, name):
        counts[name] = counts.get(name, 0) + 1
        if name == 'LICENSE' and counts[name] == 2: (root / name).write_text('changed mid-stage')
        return original(base, name)
    monkeypatch.setattr(bundle, 'read_file', changing)
    output = tmp_path / 'staged'
    with pytest.raises(ValueError, match='source evidence changed'):
        bundle.stage(root, p, output, source_commit='SCRIPTED')
    assert (output / 'LICENSE').read_bytes() == bodies['LICENSE']
    assert not (output / 'bundle-manifest.json').exists()


def test_literal_dependency_parser_rejects_unsupported_macro_or_outside_paths():
    for content in [b'\\input{../outside}', b'\\input{\\dynamicfile}']:
        with pytest.raises(ValueError): bundle.literal_dependencies({'paper/main.tex': content}, 'paper/main.tex')


def test_local_path_findings_are_reported_without_rewriting_historical_source(tmp_path):
    root, bodies, p = fixture(tmp_path)
    text = bodies['paper/child.tex'] + b'% recorded locator /Users/SCRIPTED/private\n'
    (root / 'paper/child.tex').write_bytes(text)
    receipt_path = root / p['receipt']; receipt = json.loads(receipt_path.read_text())
    receipt['additional_dependencies']['paper/child.tex'] = bundle.sha(text)
    receipt_path.write_text(json.dumps(receipt))
    output = tmp_path / 'staged'; r = bundle.stage(root, p, output, source_commit='SCRIPTED')
    assert r['limited_text_scan_findings'] == [{'file': 'paper/child.tex', 'line': 2, 'kind': 'possible-home-path'}]
    assert (output / 'paper/child.tex').read_bytes() == text


def test_current_real_allowlist_covers_literal_manuscript_inputs_without_staging():
    root = bundle.ROOT; p = json.loads((root / 'research/publication/paper-rebuild-allowlist-v1.json').read_text())
    bodies = {n: bundle.read_file(root, n) for n in p['files']}
    dependencies = bundle.literal_dependencies(bodies, p['entrypoint'])
    assert 'paper/neurips_2025.sty' in dependencies and len(dependencies) == 9
    assert all(not n.startswith(('outputs/', 'data/', 'game-ui-v2/', 'research/results/')) for n in p['files'])
    assert len(p['files']) == 12


def test_v3_receipt_uses_its_actual_entrypoint_without_changing_old_contract(tmp_path):
    root, bodies, p = fixture(tmp_path)
    old = root / 'paper/submission.tex'; new = root / 'paper/submission-v2.tex'
    old.rename(new); p['entrypoint'] = 'paper/submission-v2.tex'
    p['files'] = sorted('paper/submission-v2.tex' if n == 'paper/submission.tex' else n for n in p['files'])
    receipt_path = root / p['receipt']; receipt = json.loads(receipt_path.read_text())
    receipt['schema'] = 'scienceutopia.working-paper-build.v3'
    receipt['entrypoint'] = p['entrypoint']; receipt_path.write_text(json.dumps(receipt))
    out = tmp_path / 'staged'
    bundle.stage(root, p, out, source_commit='SCRIPTED')
    assert 'submission-v2.tex' in (out / 'REBUILD.md').read_text()
    assert 'rebuild submission.tex' not in (out / 'REBUILD.md').read_text()
    assert new.read_bytes() == (out / p['entrypoint']).read_bytes()


@pytest.mark.parametrize('change', ['unsupported-schema', 'different-entrypoint'])
def test_v3_does_not_accept_unrecognized_or_mismatched_receipts(tmp_path, change):
    root, bodies, p = fixture(tmp_path)
    path = root / p['receipt']; receipt = json.loads(path.read_text())
    receipt['schema'] = 'unknown' if change == 'unsupported-schema' else 'scienceutopia.working-paper-build.v3'
    receipt['entrypoint'] = 'paper/different.tex'; path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        bundle.stage(root, p, tmp_path / 'staged', source_commit='SCRIPTED')
    assert not (tmp_path / 'staged').exists()


def test_v2_empirical_allowlist_has_all_actual_literal_inputs():
    root = bundle.ROOT
    policy = json.loads((root / 'research/publication/paper-rebuild-allowlist-v2.json').read_text())
    bodies = {n: bundle.read_file(root, n) for n in policy['files']}
    assert len(bundle.literal_dependencies(bodies, policy['entrypoint'])) == 10
    assert len(policy['files']) == 13
    assert all(not n.startswith(('outputs/', 'data/', 'game-ui-v2/', 'research/')) for n in policy['files'])


def historical_integrated_root(tmp_path, *, source='ef104f33f14b408fc48201757cff794a3db3c3b9',
                               policy_path='research/publication/paper-rebuild-allowlist-integrated-capacity-v1.json'):
    """Materialize only the earlier allowlist; never amend its frozen receipt.

    A shared local clone permits the real source-manifest git-show checks. No
    network, historical code, TeX or scientific runtime is executed here.
    """
    import subprocess
    root = tmp_path / 'historical-source'
    subprocess.run(['git', 'clone', '--shared', '--no-checkout', '--quiet', str(bundle.ROOT), str(root)], check=True)
    policy = json.loads(subprocess.check_output(['git', 'show', source + ':' + policy_path], cwd=bundle.ROOT))
    for name in [*policy['files'], policy_path]:
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(subprocess.check_output(['git', 'show', source + ':' + name], cwd=bundle.ROOT))
    return root


def test_integrated_policy_stages_only_reviewed_manuscript_dependencies(tmp_path):
    root = historical_integrated_root(tmp_path)
    p = json.loads((root / 'research/publication/paper-rebuild-allowlist-integrated-capacity-v1.json').read_text())
    r = bundle.stage(root, p, tmp_path / 'subset', source_commit='SCRIPTED-staging-source')
    assert len(r['files']) == 51 and len(r['literal_tex_dependencies']) == 48
    assert r['original_build_source_commit'] == '9063d6f06d5993cf23e8e8fca2aa2c845184b811'
    assert 'research/data/pre-scale-information-v1/table-tabular.tex' in r['literal_tex_dependencies']
    assert sum(n.endswith('.png') for n in r['files']) == 28
    assert not any(n.startswith(('outputs/', 'data/cache/')) for n in r['files'])
    instructions = (tmp_path / 'subset/REBUILD.md').read_text()
    assert 'integrated.tex' in instructions and 'UI screenshot' in instructions
    assert 'unlisted game assets' in instructions and not r['published_or_uploaded']


@pytest.mark.parametrize('change', ['source', 'manifest', 'entrypoint', 'changed-input', 'missing-parent-input'])
def test_integrated_original_receipt_and_literal_parent_inputs_cannot_be_weakened(tmp_path, change, monkeypatch):
    from copy import deepcopy
    from utopia.system.design_patch import digest
    root = historical_integrated_root(tmp_path)
    p = json.loads((root / 'research/publication/paper-rebuild-allowlist-integrated-capacity-v1.json').read_text())
    read = bundle.read_file
    def modified(base, name):
        body = read(base, name)
        if name == p['receipt']:
            r = deepcopy(json.loads(body))
            if change == 'source': r['source_commit'] = 'bad'
            elif change == 'manifest': r['figure_files']['manifest_sha256'] = '0' * 64
            elif change == 'entrypoint': r['entrypoint'] = 'paper/wrong.tex'
            r.pop('content_sha256'); r['content_sha256'] = digest(r)
            return json.dumps(r).encode()
        if change == 'changed-input' and name == 'paper/integrated.tex': return body + b'\nSCRIPTED changed input'
        return body
    monkeypatch.setattr(bundle, 'read_file', modified)
    if change == 'missing-parent-input': p['files'].remove('research/data/pre-scale-information-v1/table-tabular.tex')
    with pytest.raises(ValueError): bundle.stage(root, p, tmp_path / 'subset', source_commit='SCRIPTED')
    assert not (tmp_path / 'subset').exists()


def test_repository_parent_inputs_are_explicit_and_cannot_escape_root():
    bodies = {'paper/main.tex': b'\\input{../research/table}', 'research/table.tex': b'SCRIPTED table'}
    with pytest.raises(ValueError): bundle.literal_dependencies(bodies, 'paper/main.tex')
    assert bundle.literal_dependencies(bodies, 'paper/main.tex', repository_parent_inputs=True) == sorted(bodies)
    for content in (b'\\input{../../outside}', b'\\input{/private/outside}'):
        with pytest.raises(ValueError):
            bundle.literal_dependencies({'paper/main.tex': content}, 'paper/main.tex', repository_parent_inputs=True)


def test_catalog_policy_stages_all_66_page_literal_inputs_without_old_pdf_substitution(tmp_path):
    root = historical_integrated_root(tmp_path,
        source='e4bd2c767b13b0eb0342fc75d37de39331d0bfbb',
        policy_path='research/publication/paper-rebuild-allowlist-integrated-catalog-v1.json')
    policy = json.loads((root / 'research/publication/paper-rebuild-allowlist-integrated-catalog-v1.json').read_text())
    report = bundle.stage(root, policy, tmp_path / 'catalog-subset', source_commit='SCRIPTED-staging-source')
    assert len(report['files']) == 54 and len(report['literal_tex_dependencies']) == 51
    assert report['original_build_source_commit'] == '5c7d3de618aa4c9aa04739a6ef70161b94239fef'
    assert report['original_build_receipt_schema'] == 'scienceutopia.integrated-catalog-planning-build.v1'
    assert 'paper/integrated/native-catalog.tex' in report['literal_tex_dependencies']
    assert 'output/pdf/science-utopia-lab-integrated-catalog-planning-working-paper.pdf' in report['files']
    assert 'output/pdf/science-utopia-lab-integrated-capacity-authority-working-paper.pdf' not in report['files']
    assert sum(n.endswith('.png') for n in report['files']) == 30
    assert not report['published_or_uploaded'] and not report['raw_or_model_data_included']


def test_planning_search_policy_stages_current_69_page_inputs_not_older_pdf(tmp_path):
    root = bundle.ROOT
    policy = json.loads((root / 'research/publication/paper-rebuild-allowlist-integrated-planning-search-v1.json').read_text())
    report = bundle.stage(root, policy, tmp_path/'planning-subset', source_commit='SCRIPTED-staging-source')
    assert len(report['files']) == 58 and len(report['literal_tex_dependencies']) == 55
    assert report['original_build_source_commit'] == '78e469a50694943f4f191b81a4158fc53749501b'
    assert 'paper/integrated/native-planning-search.tex' in report['literal_tex_dependencies']
    assert sum(n.endswith('.png') for n in report['files']) == 33
    assert 'output/pdf/science-utopia-lab-integrated-planning-search-working-paper.pdf' in report['files']
    assert 'output/pdf/science-utopia-lab-integrated-catalog-planning-working-paper.pdf' not in report['files']
    assert not report['published_or_uploaded'] and not report['raw_or_model_data_included']
