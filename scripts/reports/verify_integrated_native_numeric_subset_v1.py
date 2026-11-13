"""Verify an actual cached rebuild against the reviewed 73-page working paper.

Only compare retained bytes. No model, native world, TeX or renderer is run.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
POLICY = 'research/publication/paper-rebuild-allowlist-integrated-native-numeric-v1.json'
OUTPUT = 'research/results/integrated-native-numeric-rebuild-subset-verification-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    git = lambda *a: subprocess.check_output(['git', '-C', str(ROOT), *a], text=True).strip()
    if git('status', '--porcelain'):
        raise ValueError('commit verification tool before retaining a source-bound result')
    source = git('rev-parse', 'HEAD')
    original = checked(json.loads((ROOT / 'paper/integrated-native-numeric-build-v1.json').read_text()))
    subset = ROOT / 'outputs/integrated-native-numeric-rebuild-subset-v1-a1'
    manifest = checked(json.loads((subset / 'bundle-manifest.json').read_text()))
    policy = json.loads((ROOT / POLICY).read_text())
    if (set(manifest['files']) != set(policy['files']) or len(manifest['files']) != 62
            or manifest['original_build_source_commit'] != original['source_commit']):
        raise ValueError('actual explicit staging manifest differs')
    for name, value in manifest['files'].items():
        if sha(subset / name) != value:
            raise ValueError('staged artifact changed: ' + name)
    build = subset / 'tmp/pdfs/rebuild'
    # Match the original plain pdftotext invocation. Preserve the independent
    # layout-mode extraction rather than overwriting it to satisfy this check.
    plain_text = build / 'integrated-plain.txt'
    if sha(plain_text) != original['build']['text_sha256']:
        raise ValueError('actual rebuilt text differs')
    log = (build / 'integrated.log').read_text()
    if re.search(r'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', log):
        raise ValueError('actual rebuilt layout/reference warning')
    pages = {p.name: sha(p) for p in sorted((subset / 'tmp/pdfs/rebuilt-render').glob('page-*.png'))}
    if pages != original['visual_review']['page_png_sha256']:
        raise ValueError('actual rendered page bytes differ from reviewed originals')
    result = {'schema': 'scienceutopia.integrated-native-numeric-rebuild-subset-verification.v1',
        'verification_source_commit': source, 'staging_source_commit': manifest['source_commit'],
        'original_build_source_commit': original['source_commit'], 'pages': 73, 'render_dpi': 90,
        'policy_file': POLICY, 'policy_file_sha256': sha(ROOT / POLICY), 'subset_manifest': manifest,
        'original_reviewed_pdf_sha256': original['pdf_sha256'],
        'rebuilt_pdf_sha256': sha(build / 'integrated.pdf'),
        'binary_pdf_identical': sha(build / 'integrated.pdf') == original['pdf_sha256'],
        'rebuilt_text_sha256': sha(plain_text),
        'text_extraction_mode': 'pdftotext default, matching the original build',
        'earlier_verification_attempt': {'status': 'failed-before-receipt',
            'source_commit': 'fb546bb5', 'error': 'actual rebuilt text differs',
            'cause': 'layout-mode extraction compared with original default-mode text',
            'original_layout_text_preserved': True, 'actual_page_images_already_match': 73},
        'all_73_rendered_PNGs_byte_identical_to_reviewed': True, 'page_png_sha256': pages,
        'layout_or_undefined_reference_warnings': 0, 'cache_only_untrusted_build_exit_code': 0,
        'new_downloads': 0, 'new_model_calls': 0, 'raw_audit_repeated': False,
        'independent_inference_rerun': False, 'numerical_results_recomputed': False,
        'clean_machine_build_claimed': False, 'published_or_uploaded': False,
        'anonymous_or_release_clearance': False, 'publication_ready': False}
    if git('rev-parse', 'HEAD') != source or git('status', '--porcelain'):
        raise ValueError('verification source changed')
    save(ROOT / OUTPUT, result)
    print(json.dumps({k: result[k] for k in ('pages', 'all_73_rendered_PNGs_byte_identical_to_reviewed',
        'binary_pdf_identical', 'new_model_calls', 'publication_ready')}))


if __name__ == '__main__':
    main()
