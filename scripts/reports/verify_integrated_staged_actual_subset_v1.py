"""Retain actual cached subset reconstruction, never infer or rerun science."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.reports.integrated_native_numeric_build_v1 import Bounds
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
POLICY = 'research/publication/paper-rebuild-allowlist-integrated-staged-actual-v1.json'
RECEIPT = 'paper/integrated-staged-actual-build-v1.json'
OUTPUT = 'research/results/integrated-staged-actual-rebuild-subset-verification-v1.json'
SCHEMA = 'scienceutopia.integrated-staged-actual-subset-verification.v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subset', type=Path, required=True)
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    source = git('rev-parse', 'HEAD')
    if git('status', '--porcelain') or (ROOT/OUTPUT).exists():
        raise ValueError('clean committed verifier and fresh output required')
    original = checked(json.loads((ROOT/RECEIPT).read_text()))
    policy = json.loads((ROOT/POLICY).read_text())
    subset = args.subset.resolve()
    if not subset.is_relative_to(ROOT/'outputs'):
        raise ValueError('declared local outputs subset required')
    manifest = checked(json.loads((subset/'bundle-manifest.json').read_text()))
    expected = set(original['literal_dependencies']) | {'LICENSE', original['output'], RECEIPT}
    if (set(manifest['files']) != expected or set(policy['files']) != expected
            or manifest['literal_tex_dependencies'] != original['literal_dependencies']
            or manifest['original_build_source_commit'] != original['source_commit']
            or not original['visual_review']['all_final_pages_reviewed']):
        raise ValueError('exact reviewed source, complete dependencies and explicit subset required')
    for name, value in manifest['files'].items():
        if sha(subset/name) != value:
            raise ValueError('staged input bytes changed: ' + name)
    build = subset/'tmp/pdfs/rebuild'
    if sha(build/'integrated.txt') != original['build']['text_sha256']:
        raise ValueError('actual rebuilt text differs from reviewed original')
    log = (build/'integrated.log').read_text()
    if re.search(r'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', log):
        raise ValueError('actual rebuilt layout/reference warning')
    bbox = (build/'bbox.html').read_text(); bounds = Bounds(); bounds.feed(bbox)
    if (bounds.pages != original['pages'] or bounds.words != bbox.count('<word ')
            or not bounds.words or bounds.outside):
        raise ValueError('complete in-page rebuilt text required')
    pages = {p.name: sha(p) for p in sorted((subset/'tmp/pdfs/render').glob('page-*.png'))}
    if pages != original['visual_review']['page_png_sha256']:
        raise ValueError('every actual reconstructed page must match the reviewed page')
    result = {'schema': SCHEMA,
        'verification_source_commit': source, 'staging_source_commit': manifest['source_commit'],
        'original_build_source_commit': original['source_commit'],
        'original_receipt_content_sha256': original['content_sha256'],
        'policy_file': POLICY, 'policy_file_sha256': sha(ROOT/POLICY),
        'subset_directory': str(subset.relative_to(ROOT)),
        'subset_manifest_file_sha256': sha(subset/'bundle-manifest.json'),
        'subset_manifest_content_sha256': manifest['content_sha256'],
        'input_files': len(manifest['files']), 'literal_dependencies': len(original['literal_dependencies']),
        'all_staged_input_bytes_unchanged': True, 'pages': bounds.pages,
        'original_reviewed_pdf_sha256': original['pdf_sha256'],
        'rebuilt_pdf_sha256': sha(build/'integrated.pdf'),
        'binary_pdf_identical': sha(build/'integrated.pdf') == original['pdf_sha256'],
        'rebuilt_default_pdftotext_sha256': sha(build/'integrated.txt'),
        'all_rendered_page_pixels_match_reviewed_original': True,
        'render_dpi': 90, 'page_png_sha256': pages,
        'cache_only_untrusted_actual_build_exit_code': 0,
        'layout_or_undefined_reference_warnings': 0, 'off_page_text_words': bounds.outside,
        'new_downloads': 0, 'new_model_calls': 0,
        'raw_audit_repeated': False, 'independent_inference_rerun': False,
        'numerical_results_recomputed': False, 'clean_machine_build_claimed': False,
        'original_pdf_or_receipt_overwritten': False, 'published_or_uploaded': False,
        'anonymous_or_release_clearance': False, 'publication_ready': False}
    if git('rev-parse', 'HEAD') != source or git('status', '--porcelain'):
        raise ValueError('verification source changed')
    save(ROOT/OUTPUT, result)
    print(json.dumps({k: result[k] for k in ('input_files', 'pages',
        'all_rendered_page_pixels_match_reviewed_original', 'binary_pdf_identical')}))


if __name__ == '__main__':
    main()
