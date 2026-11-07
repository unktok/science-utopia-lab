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
