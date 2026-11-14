"""Retain a newly built and actually reviewed full draft; preserve older PDFs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.reports.integrated_native_numeric_build_v1 import Bounds
from scripts.reports.integrated_workflow_feedback_build_v1 import group, sha
from scripts.reports.paper_rebuild_bundle import literal_dependencies
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
OLD = 'paper/integrated-workflow-feedback-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-open-institutions-working-paper.pdf'
RECEIPT = 'paper/integrated-open-institutions-build-v1.json'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--all-pages-reviewed', action='store_true', required=True)
    for name in ('build-one', 'build-two', 'render-one', 'render-two', 'contact-sheets'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    if not a.all_pages_reviewed or git('status', '--porcelain'):
        raise ValueError('actual complete visual review and clean committed source required')
    source = git('rev-parse', 'HEAD')
    if any((ROOT / name).exists() for name in (OUTPUT, RECEIPT)):
        raise ValueError('fresh PDF/receipt required; historical artifacts are not overwritten')
    read = lambda name: checked(json.loads((ROOT / name).read_text()))
    old = read(OLD)
    dev = read('research/results/native-open-institution-closed-v3.json')
    fixed = read('research/results/native-open-institution-fixed-closed-v1.json')
    delta = read('research/data/native-open-institution-v3/content-delta.json')
    if (fixed['origin_audit_content_sha256'] != dev['audit']['content_sha256']
            or not fixed['audit']['two_original_audits_identical']
            or any(fixed['audit']['continuation_exit_codes'].values())
            or fixed['terminal']['status'] != 'closed' or dev['own_completions'] != 1
            or delta['analysis']['original_audit_content_sha256'] != dev['audit']['content_sha256']):
        raise ValueError('normally closed matching development/evaluation/content evidence required')
    preserved = {**old['preserved_files'], OLD: sha(ROOT / OLD), old['output']: old['pdf_sha256']}
    if any(sha(ROOT / name) != expected for name, expected in preserved.items()):
        raise ValueError('historical reviewed artifact changed')
    builds = [a.build_one.resolve(), a.build_two.resolve()]
    renders = [a.render_one.resolve(), a.render_two.resolve()]
    if builds[0] == builds[1] or renders[0] == renders[1]:
        raise ValueError('distinct actual builds and render directories required')
    texts = [(path / 'integrated.txt').read_bytes() for path in builds]
    logs = [(path / 'integrated.log').read_bytes() for path in builds]
    if texts[0] != texts[1] or logs[0] != logs[1]:
        raise ValueError('two actual cached builds disagree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', logs[0]) or b'??' in texts[0]:
        raise ValueError('unresolved layout/reference diagnostic')
    bounds = Bounds(); bbox = (builds[0] / 'bbox.html').read_text(); bounds.feed(bbox)
    if bounds.pages < old['pages'] or bounds.outside or not bounds.words or bounds.words != bbox.count('<word '):
        raise ValueError('complete in-page Poppler text required')
    aux = (builds[0] / 'integrated.aux').read_text()
    figures = len(re.findall(r'\\contentsline \{figure\}', aux))
    tables = len(re.findall(r'\\contentsline \{table\}', aux))
    references = (builds[0] / 'integrated.bbl').read_text().count('\\bibitem')
    if figures < old['figures'] + 2 or tables < old['tables'] + 3 or references < old['cited_references']:
        raise ValueError('current/prior meaningful figures, tables or references omitted')
    page_names = [f'page-{i:02}.png' for i in range(1, bounds.pages + 1)]
    if any(sorted(p.name for p in directory.glob('page-*.png')) != page_names for directory in renders):
        raise ValueError('complete final renders required')
    if any(sha(renders[0] / name) != sha(renders[1] / name) for name in page_names):
        raise ValueError('two complete rendered builds differ')
    if len(list(a.contact_sheets.glob('sheet-*.png'))) != (bounds.pages + 11) // 12:
        raise ValueError('complete labelled review sheets required')
    result = {k: v for k, v in old.items() if k != 'content_sha256'}
    result.update(schema='scienceutopia.integrated-open-institutions-manuscript.v1',
        source_commit=source, retention_tool_source_commit=source, output=OUTPUT,
        tex_sha256=sha(ROOT / 'paper/integrated.tex'), pdf_sha256=sha(builds[0] / 'integrated.pdf'),
        pages=bounds.pages, figures=figures, tables=tables, cited_references=references,
        preserved_files=preserved, new_paper_rebuild_subset_verified=False, publication_ready=False,
        editorial_changes=['Retain all prior meaningful tracks without an artificial page cap',
            'Add stopped open-code prefix without fabricating normal closure',
            'Add every normally closed v3 slot, null, actual content difference and cost',
            'Add all frozen unused labels, including missing T and unfavorable U, without reselection'],
        scientific_scope={'previous_receipt': OLD, 'previous_receipt_scope': old['scientific_scope'],
            'open_v3_own_slots': 6, 'open_v3_own_completions': 1, 'open_v3_generation_nulls': 3,
            'open_v3_runtime_nulls': 2, 'open_v3_physical_worlds': 5,
            'open_fixed_physical_worlds': 3, 'open_fixed_logical_labels': 4,
            'open_fixed_unused_seeds': fixed['unused_seeds'], 'throughput_selection_missing': True,
            'own_advantage_demonstrated': False, 'new_model_calls_by_manuscript_work': 0,
            'independent_optimizer_replication': False, 'publication_ready': False},
        build={'directories': [str(path.relative_to(ROOT)) for path in builds],
            'engine': 'Tectonic 0.17.0', 'flags': '--only-cached --untrusted --keep-logs --keep-intermediates',
            'exit_codes': [0, 0], 'downloads': 0, 'text_identical': True,
            'text_sha256': hashlib.sha256(texts[0]).hexdigest(),
            'log_sha256': [hashlib.sha256(body).hexdigest() for body in logs],
            'binary_pdf_identity_claimed': False, 'rendered_page_identity_verified': True,
            'layout_or_undefined_reference_warnings': 0, 'off_page_text_words': bounds.outside,
            'bbox_word_tags_accounted': bounds.words, 'unresolved_question_mark_pairs': 0},
        visual_review={'all_final_pages_reviewed': True, 'pages_reviewed_for_layout': bounds.pages,
            'pages_reviewed': list(range(1, bounds.pages + 1)), 'render_dpi': 90,
            'contact_sheet_directory': str(a.contact_sheets.resolve().relative_to(ROOT)),
            'clipped_or_overlapping_content_observed': False,
            'page_png_sha256': {name: sha(renders[0] / name) for name in page_names}})
    result['source_files'] = group(source, old['source_files']['files'])
    added_figures = [str(path.relative_to(ROOT)) for directory in
        ('native-open-institution-v3', 'native-open-institution-fixed-v1')
        for path in sorted((ROOT / 'paper/figures' / directory).iterdir()) if path.is_file()]
    result['figure_files'] = group(source, old['figure_files']['files'] + added_figures)
    result['support_files'] = group(source, old['support_files']['files'] + [
        'scripts/reports/integrated_open_institutions_build_v1.py',
        'scripts/reports/native_workflow_content_delta_v1.py',
        'tests/reports/test_native_open_content_retained_v1.py'])
    evidence = ['research/results/native-open-institution-stopped-prefix-v2.json',
        'research/results/native-open-institution-stopped-physical-readout-v2.json',
        'research/results/native-open-institution-closed-v3.json',
        'research/results/native-open-institution-fixed-closed-v1.json',
        'research/results/native-open-content-and-trace-verification-v1.json',
        'research/data/native-open-institution-v3/content-delta.json']
    result['evidence_files'] = group(source, old['evidence_files']['files'] + evidence)
    bodies = {name: (ROOT / name).read_bytes() for key in ('source_files', 'figure_files', 'support_files')
        for name in result[key]['files']}
    result['literal_dependencies'] = literal_dependencies(bodies, result['entrypoint'], repository_parent_inputs=True)
    (ROOT / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    with (ROOT / OUTPUT).open('xb') as stream:
        stream.write((builds[0] / 'integrated.pdf').read_bytes())
    save(ROOT / RECEIPT, result)
    print(json.dumps({'pages': bounds.pages, 'figures': figures, 'tables': tables,
        'references': references, 'pdf_sha256': result['pdf_sha256'], 'publication_ready': False}))


if __name__ == '__main__': main()
