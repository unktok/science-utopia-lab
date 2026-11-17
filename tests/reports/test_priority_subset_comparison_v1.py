"""SCRIPTED bytes only: no PDF/PNG creation, TeX, Poppler, model or science."""
import json
from pathlib import Path

import pytest

from scripts.reports import compare_integrated_priority_subset_v1 as module
from utopia.system.design_patch import digest
from utopia.optimization.native_numeric_designer import checked


def seal(value):
    value = dict(value); value.pop('content_sha256', None)
    return {**value, 'content_sha256': digest(value)}


def fixture(tmp_path, monkeypatch):
    subset, build, renders = [tmp_path / p for p in ('subset', 'build', 'renders')]
    for p in (subset, build, renders): p.mkdir()
    text = b'SCRIPTED original text; no actual document is rendered'
    page_body = b'SCRIPTED not a PNG'
    names = [f'page-{i:03}.png' for i in range(1, 112)]
    original = seal({'schema': 'scienceutopia.integrated-native-priority-method-paper.v1',
        'source_commit': 'a' * 40, 'entrypoint': 'paper/integrated.tex',
        'pdf': 'output/pdf/original.pdf', 'pdf_sha256': module.sha(b'SCRIPTED not a PDF'),
        'pages': 111, 'build': {'text_sha256': module.sha(text), 'bbox_word_tags_accounted': 111},
        'visual_review': {'dpi': 90, 'all111_layouts_reviewed': True,
            'page_sha256': {n: module.sha(page_body) for n in names}}})
    bodies = {'LICENSE': b'SCRIPTED notice', 'paper/integrated.tex': b'\\usepackage{neurips_2025}',
        'paper/neurips_2025.sty': b'SCRIPTED style', original['pdf']: b'SCRIPTED not a PDF',
        module.RECEIPT: json.dumps(original).encode()}
    for name, body in bodies.items():
        p = subset / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(body)
    expected = {k: module.sha(v) for k, v in bodies.items() if k not in ('LICENSE', module.RECEIPT)}
    monkeypatch.setattr(module, 'priority_expected', lambda *a: expected)
    policy = {'schema': 'scienceutopia.paper-rebuild-allowlist.v1',
        'status': 'local-working-draft-not-anonymous-not-release-cleared',
        'entrypoint': original['entrypoint'], 'files': sorted(bodies)}
    manifest = seal({'source_commit': 'b' * 40, 'original_build_source_commit': original['source_commit'],
        'original_build_receipt_schema': original['schema'], 'entrypoint': original['entrypoint'],
        'files': {k: module.sha(v) for k, v in bodies.items()},
        'literal_tex_dependencies': ['paper/integrated.tex', 'paper/neurips_2025.sty']})
    (subset / 'bundle-manifest.json').write_text(json.dumps(manifest))
    bbox = '<html>' + '<page width="100" height="100"><word xmin="1" ymin="1" xmax="2" ymax="2">x</word></page>' * 111 + '</html>'
    for name, body in {'integrated.pdf': b'SCRIPTED not a PDF', 'integrated.txt': text,
        'integrated.log': b'SCRIPTED no compiler ran', 'bbox.html': bbox.encode()}.items():
        (build / name).write_bytes(body)
    for name in names: (renders / name).write_bytes(page_body)
    return subset, build, renders, original, policy


def test_matching_prepared_bytes_are_not_compiler_or_render_execution_evidence(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); r = module.compare(*args)
    assert r['artifact_comparison_passed'] and r['pages'] == r['word_tags_checked'] == 111
    assert r['input_files'] == 5 and r['literal_dependencies'] == 2
    assert r['binary_pdf_identical'] and len(r['page_sha256']) == 111
    assert not any(r[k] for k in ('actual_rebuild_execution_verified', 'fresh_visual_review_verified',
        'prepared_pdf_to_text_render_binding_verified', 'numerical_reproduction_verified', 'publication_ready'))
    # The comparison intentionally cannot authenticate precomputed text/images
    # as derivations of these different PDF bytes. Do not promote this result.
    (args[1] / 'integrated.pdf').write_bytes(b'SCRIPTED different supposed PDF')
    changed = module.compare(*args)
    assert changed['artifact_comparison_passed'] and not changed['binary_pdf_identical']
    assert not changed['prepared_pdf_to_text_render_binding_verified']


@pytest.mark.parametrize('change', ['input', 'text', 'log', 'bbox-pages', 'bbox-words',
    'bbox-outside', 'page-bytes', 'missing-page', 'extra-page', 'manifest', 'dependencies', 'policy'])
def test_corrupted_or_incomplete_artifacts_fail_without_generating_a_pdf(tmp_path, monkeypatch, change):
    args = fixture(tmp_path, monkeypatch); subset, build, renders, original, policy = args
    if change == 'input': (subset / 'paper/integrated.tex').write_text('SCRIPTED changed')
    elif change == 'text': (build / 'integrated.txt').write_text('SCRIPTED changed')
    elif change == 'log': (build / 'integrated.log').write_text('Overfull SCRIPTED diagnostic')
    elif change.startswith('bbox-'):
        p = build / 'bbox.html'; text = p.read_text()
        if change == 'bbox-pages': text = text.replace('<page ', '<div ', 1).replace('</page>', '</div>', 1)
        elif change == 'bbox-words': text = text.replace('<word ', '<span ', 1).replace('</word>', '</span>', 1)
        else: text = text.replace('xmax="2"', 'xmax="200"', 1)
        p.write_text(text)
    elif change == 'page-bytes': (renders / 'page-001.png').write_bytes(b'SCRIPTED wrong pixels')
    elif change == 'missing-page': (renders / 'page-111.png').unlink()
    elif change == 'extra-page': (renders / 'page-112.png').write_bytes(b'SCRIPTED extra')
    elif change == 'policy': policy['files'].append(policy['files'][-1])
    else:
        p = subset / 'bundle-manifest.json'; m = json.loads(p.read_text())
        if change == 'manifest': m['files']['paper/integrated.tex'] = '0' * 64
        else: m['literal_tex_dependencies'].pop()
        p.write_text(json.dumps(seal(m)))
    with pytest.raises(ValueError): module.compare(*args)


def test_public_export_does_not_call_pdf_tools_or_relabel_comparison_as_rebuild(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); root = tmp_path / 'reader'; root.mkdir()
    original, policy = args[-2:]
    for name, value in ((module.RECEIPT, original), (module.POLICY, policy)):
        p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(value))
    monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(module, 'pinned_revision', lambda root: 'c' * 40)
    def forbidden(*a, **kw): pytest.fail('comparison must not invoke a compiler/renderer/process')
    monkeypatch.setattr('subprocess.run', forbidden)
    monkeypatch.setattr('subprocess.check_output', forbidden)
    output = tmp_path / 'comparison.json'
    monkeypatch.setattr('sys.argv', ['compare', '--subset', str(args[0]), '--build', str(args[1]),
        '--renders', str(args[2]), '--output', str(output)])
    module.main(); report = checked(json.loads(output.read_text()))
    assert report['artifact_comparison_passed'] and report['comparison_source_commit'] == 'c' * 40
    assert not report['actual_rebuild_execution_verified'] and not report['fresh_visual_review_verified']
    with pytest.raises(ValueError, match='fresh comparison'): module.main()


@pytest.mark.parametrize('target', ['reader', 'subset', 'build', 'renders'])
def test_output_path_guard_precedes_source_or_artifact_reads(tmp_path, monkeypatch, target):
    roots = {k: tmp_path / k for k in ('reader', 'subset', 'build', 'renders')}
    monkeypatch.setattr(module, 'ROOT', roots['reader'])
    def forbidden(*a, **kw): pytest.fail('path guard must precede source/artifact checks')
    monkeypatch.setattr(module, 'pinned_revision', forbidden)
    output = roots[target] / 'out.json'
    monkeypatch.setattr('sys.argv', ['compare', '--subset', str(roots['subset']),
        '--build', str(roots['build']), '--renders', str(roots['renders']), '--output', str(output)])
    with pytest.raises(ValueError, match='fresh comparison'): module.main()
    assert not output.exists()


def test_artifact_change_during_read_is_not_a_successful_comparison(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); original_read = module.read_file
    changed = False
    def changing(root, name):
        nonlocal changed
        body = original_read(root, name)
        if Path(root) == args[1] and name == 'bbox.html' and not changed:
            changed = True
            (args[1] / 'integrated.txt').write_bytes(b'SCRIPTED concurrent mutation')
        return body
    monkeypatch.setattr(module, 'read_file', changing)
    with pytest.raises(ValueError, match='changed during reading'): module.compare(*args)


def test_existing_separate_extraction_paths_are_read_without_copying_or_rendering(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); extracted = tmp_path / 'prior-extraction'; extracted.mkdir()
    text = extracted / 'text.txt'; bbox = extracted / 'bbox.html'
    (args[1] / 'integrated.txt').rename(text)
    (args[1] / 'bbox.html').rename(bbox)
    r = module.compare(*args, text_path=text, bbox_path=bbox)
    assert r['artifact_comparison_passed']
    assert r['prepared_artifact_locations']['integrated.txt'] == str(text.resolve())
    assert r['prepared_artifact_locations']['bbox.html'] == str(bbox.resolve())
    assert not r['actual_rebuild_execution_verified'] and not r['prepared_pdf_to_text_render_binding_verified']
