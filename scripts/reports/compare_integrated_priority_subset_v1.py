"""Read-only comparison of already prepared111-page rebuild artifacts.

Matching files do not prove a TeX command ran or a fresh visual review occurred.
No compiler, renderer, model, source program or scientific world is executed.
"""
import argparse
import json
from pathlib import Path
import re

from scripts.reports.integrated_native_numeric_build_v1 import Bounds
from scripts.reports.paper_rebuild_bundle import literal_dependencies, priority_expected, read_file, sha
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = 'paper/integrated-priority-method-build-v1.json'
POLICY = 'research/publication/paper-rebuild-allowlist-integrated-priority-method-v1.json'
SCHEMA = 'scienceutopia.integrated-priority-subset-artifact-comparison.v1'


def compare(subset, build, renders, original, policy, *, text_path=None, bbox_path=None):
    subset, build, renders = map(Path, (subset, build, renders))
    original = checked(original)
    manifest_body = read_file(subset, 'bundle-manifest.json')
    manifest = checked(json.loads(manifest_body))
    if (original['schema'] != 'scienceutopia.integrated-native-priority-method-paper.v1'
            or policy['schema'] != 'scienceutopia.paper-rebuild-allowlist.v1'
            or policy['status'] != 'local-working-draft-not-anonymous-not-release-cleared'
            or policy['files'] != sorted(set(policy['files']))):
        raise ValueError('explicit original111-page working-draft comparison scope required')
    expected = priority_expected(ROOT, original, policy['entrypoint'])
    names = set(expected) | {'LICENSE', RECEIPT}
    if (set(policy['files']) != names or set(manifest['files']) != names
            or manifest['entrypoint'] != original['entrypoint']
            or manifest['original_build_source_commit'] != original['source_commit']
            or manifest['original_build_receipt_schema'] != original['schema']):
        raise ValueError('complete exact original input subset required')
    bodies = {name: read_file(subset, name) for name in sorted(names)}
    if (any(sha(body) != manifest['files'][name] for name, body in bodies.items())
            or any(sha(bodies[name]) != value for name, value in expected.items())
            or checked(json.loads(bodies[RECEIPT])) != original):
        raise ValueError('staged original inputs/receipt differ')
    dependencies = literal_dependencies(bodies, original['entrypoint'], repository_parent_inputs=True)
    if (dependencies != manifest['literal_tex_dependencies']
            or set(dependencies) != set(expected) - {original['pdf']}):
        raise ValueError('complete literal TeX dependencies required')
    locations = {name: build / name for name in
        ('integrated.pdf', 'integrated.txt', 'integrated.log', 'bbox.html')}
    if text_path is not None: locations['integrated.txt'] = Path(text_path)
    if bbox_path is not None: locations['bbox.html'] = Path(bbox_path)
    artifacts = {name: read_file(path.parent, path.name) for name, path in locations.items()}
    if sha(artifacts['integrated.txt']) != original['build']['text_sha256']:
        raise ValueError('prepared artifact text differs from reviewed original')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', artifacts['integrated.log']):
        raise ValueError('prepared artifact has layout/reference diagnostics')
    bbox = artifacts['bbox.html'].decode(); bounds = Bounds(); bounds.feed(bbox)
    if (bounds.pages != original['pages'] or bounds.words != bbox.count('<word ')
            or bounds.words != original['build']['bbox_word_tags_accounted']
            or not bounds.words or bounds.outside):
        raise ValueError('complete original in-page word coverage required')
    pages = {p.name: sha(read_file(renders, p.name)) for p in sorted(renders.glob('page-*.png'))}
    if pages != original['visual_review']['page_sha256'] or len(pages) != original['pages']:
        raise ValueError('every original page image must match')
    if (read_file(subset, 'bundle-manifest.json') != manifest_body
            or any(read_file(subset, name) != body for name, body in bodies.items())
            or any(read_file(locations[name].parent, locations[name].name) != body for name, body in artifacts.items())
            or any(sha(read_file(renders, name)) != value for name, value in pages.items())):
        raise ValueError('comparison inputs changed during reading')
    return {'schema': SCHEMA, 'artifact_comparison_passed': True,
        'original_build_source_commit': original['source_commit'],
        'original_receipt_content_sha256': original['content_sha256'],
        'staging_source_commit': manifest['source_commit'],
        'subset_manifest_content_sha256': manifest['content_sha256'],
        'input_files': len(names), 'literal_dependencies': len(dependencies),
        'pages': bounds.pages, 'word_tags_checked': bounds.words, 'off_page_words': bounds.outside,
        'original_pdf_sha256': original['pdf_sha256'],
        'prepared_pdf_sha256': sha(artifacts['integrated.pdf']),
        'binary_pdf_identical': sha(artifacts['integrated.pdf']) == original['pdf_sha256'],
        'prepared_text_sha256': sha(artifacts['integrated.txt']),
        'prepared_artifact_file_sha256': {k: sha(v) for k, v in artifacts.items()},
        'prepared_artifact_locations': {k: str(v.resolve()) for k, v in locations.items()},
        'matched_reference_dpi': original['visual_review']['dpi'], 'page_sha256': pages,
        'actual_rebuild_execution_verified': False, 'fresh_visual_review_verified': False,
        'prepared_pdf_to_text_render_binding_verified': False,
        'numerical_reproduction_verified': False, 'publication_ready': False,
        'new_model_calls_by_comparison': 0, 'new_PDF_or_page_render_by_comparison': 0,
        'scope': 'Exact staged inputs/text/all page images match the reviewed111-page receipt. '
            'The prepared PDF bytes may differ. Compiler/extraction/render command provenance '
            'and fresh visual inspection require separate evidence; text/images are not '
            'authenticated derivations of that PDF by this comparison. Copying old artifacts alone '
            'can satisfy comparison and must not be called a reconstructed PDF or new science.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('subset', 'build', 'renders', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--text', type=Path)
    parser.add_argument('--bbox', type=Path)
    args = parser.parse_args(); out = args.output.resolve()
    protected = [ROOT, args.subset, args.build, args.renders]
    protected += [p.parent for p in (args.text, args.bbox) if p is not None]
    if out.exists() or any(out.is_relative_to(p.resolve()) for p in protected):
        raise ValueError('fresh comparison output outside reader and input directories required')
    source = pinned_revision(ROOT)
    original_body, policy_body = read_file(ROOT, RECEIPT), read_file(ROOT, POLICY)
    report = compare(args.subset, args.build, args.renders, json.loads(original_body), json.loads(policy_body),
        text_path=args.text, bbox_path=args.bbox)
    if (pinned_revision(ROOT) != source or read_file(ROOT, RECEIPT) != original_body
            or read_file(ROOT, POLICY) != policy_body):
        raise ValueError('comparison reader or original evidence changed')
    report.update(comparison_source_commit=source, receipt_file_sha256=sha(original_body),
        policy_file_sha256=sha(policy_body))
    save(out, report)
    print(json.dumps({k: report[k] for k in ('artifact_comparison_passed',
        'actual_rebuild_execution_verified', 'fresh_visual_review_verified', 'publication_ready')}))


if __name__ == '__main__':
    main()
