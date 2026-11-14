"""Retain a reviewed real-staged development/fixed paper, preserving old PDFs."""
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
OLD = 'paper/integrated-staged-construction-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-staged-actual-working-paper.pdf'
RECEIPT = 'paper/integrated-staged-actual-build-v1.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-pages-reviewed', action='store_true', required=True)
    for name in ('build-one', 'build-two', 'render-one', 'render-two', 'contact-sheets'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    if not args.all_pages_reviewed or git('status', '--porcelain'):
        raise ValueError('clean committed source and actual full visual review required')
    source = git('rev-parse', 'HEAD')
    if any((ROOT / name).exists() for name in (OUTPUT, RECEIPT)):
        raise ValueError('fresh PDF/receipt required, not a historical overwrite')
    read = lambda name: checked(json.loads((ROOT / name).read_text()))
    old = read(OLD)
    dev_name = 'research/results/native-open-staged-institution-closed-v1.json'
    fixed_name = 'research/results/native-open-staged-fixed-closed-v1.json'
    dev, fixed = read(dev_name), read(fixed_name)
    if (dev['terminal']['status'] != 'closed' or dev['terminal']['consumed_slots'] != 6
            or dev['terminal']['observations'] != 8 or fixed['terminal']['status'] != 'closed'
            or fixed['physical_worlds'] != 3 or fixed['logical_labels'] != 4
            or fixed['origin_audit_content_sha256'] != dev['audit']['content_sha256']
            or any(fixed['audit']['continuation_exit_codes'].values())
            or not fixed['audit']['two_original_audits_identical']
            or not fixed['audit']['two_cost_exports_identical']):
        raise ValueError('normally closed, matching actual development/fixed evidence required')
    preserved = {**old['preserved_files'], OLD: sha(ROOT / OLD), old['output']: old['pdf_sha256']}
    if any(sha(ROOT / name) != value for name, value in preserved.items()):
        raise ValueError('historical reviewed artifact changed')
    builds = [args.build_one.resolve(), args.build_two.resolve()]
    renders = [args.render_one.resolve(), args.render_two.resolve()]
    if builds[0] == builds[1] or renders[0] == renders[1]:
        raise ValueError('distinct actual builds and renders required')
    texts = [(d / 'integrated.txt').read_bytes() for d in builds]
    logs = [(d / 'integrated.log').read_bytes() for d in builds]
    if texts[0] != texts[1] or logs[0] != logs[1]:
        raise ValueError('two actual cached builds disagree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', logs[0]) or b'??' in texts[0]:
        raise ValueError('unresolved layout/reference diagnostics remain')
    bounds = Bounds(); bbox = (builds[0] / 'bbox.html').read_text(); bounds.feed(bbox)
    if bounds.pages < old['pages'] or bounds.outside or not bounds.words or bounds.words != bbox.count('<word '):
        raise ValueError('complete in-page Poppler text required')
    aux = (builds[0] / 'integrated.aux').read_text()
    bbl = (builds[0] / 'integrated.bbl').read_text()
    figures = len(re.findall(r'\\contentsline \{figure\}', aux))
    tables = len(re.findall(r'\\contentsline \{table\}', aux))
    refs = bbl.count('\\bibitem')
    if figures != old['figures'] + 2 or tables != old['tables'] + 2 or refs != old['cited_references'] + 1:
        raise ValueError('all prior visuals and declared two figures/tables plus one reference required')
    if bbl.count('{el2025inefficiencies}') != 1:
        raise ValueError('one behavioral-redundancy precedent required')
    names = [f'page-{i:02}.png' for i in range(1, bounds.pages + 1)]
    if any(sorted(p.name for p in d.glob('page-*.png')) != names for d in renders):
        raise ValueError('complete final renders required')
    pages = {name: sha(renders[0] / name) for name in names}
    if any(sha(renders[1] / name) != value for name, value in pages.items()):
        raise ValueError('two complete rendered builds differ')
    if len(list(args.contact_sheets.glob('sheet-*.png'))) != (bounds.pages + 11) // 12:
        raise ValueError('complete labelled contact sheets required')
    result = {k: v for k, v in old.items() if k != 'content_sha256'}
    result.update(schema='scienceutopia.integrated-staged-actual-manuscript.v1', source_commit=source,
        retention_tool_source_commit=source, output=OUTPUT, pdf_sha256=sha(builds[0] / 'integrated.pdf'),
        tex_sha256=sha(ROOT / 'paper/integrated.tex'), pages=bounds.pages, figures=figures, tables=tables,
        cited_references=refs, preserved_files=preserved, new_paper_rebuild_subset_verified=False,
        publication_ready=False, editorial_changes=[
            'Retain all meaningful earlier tracks and unfavorable actual staged development/fixed outcomes',
            'Add full candidate paths, literal sharing, full scientist-input classes and complete costs',
            'Distinguish core-only duration envelope from original related-topic support relaxation',
            'Credit prior behavioral-redundancy and design-cost analysis without a priority claim'],
        scientific_scope={'previous_receipt': OLD, 'previous_receipt_scope': old['scientific_scope'],
            'development_evidence_content_sha256': dev['content_sha256'],
            'fixed_evidence_content_sha256': fixed['content_sha256'],
            'own_slots': 6, 'development_worlds': 8, 'fixed_worlds': 3, 'fixed_logical_labels': 4,
            'unused_seeds': fixed['unused_seeds'], 'own_advantage_demonstrated': False,
            'new_scientific_model_calls_by_manuscript_work': 0,
            'independent_optimizer_replication': False, 'publication_ready': False},
        build={'directories': [str(d.relative_to(ROOT)) for d in builds], 'engine': 'Tectonic 0.17.0',
            'flags': '--only-cached --untrusted --keep-logs --keep-intermediates', 'exit_codes': [0, 0],
            'downloads': 0, 'text_identical': True, 'text_sha256': hashlib.sha256(texts[0]).hexdigest(),
            'log_sha256': [hashlib.sha256(log).hexdigest() for log in logs],
            'binary_pdf_identical': (builds[0] / 'integrated.pdf').read_bytes() == (builds[1] / 'integrated.pdf').read_bytes(),
            'rendered_page_identity_verified': True, 'layout_or_undefined_reference_warnings': 0,
            'off_page_text_words': bounds.outside, 'bbox_word_tags_accounted': bounds.words,
            'unresolved_question_mark_pairs': 0},
        visual_review={'all_final_pages_reviewed': True, 'pages_reviewed_for_layout': bounds.pages,
            'pages_reviewed': list(range(1, bounds.pages + 1)), 'render_dpi': 90,
            'contact_sheet_directory': str(args.contact_sheets.resolve().relative_to(ROOT)),
            'clipped_or_overlapping_content_observed': False, 'page_png_sha256': pages})
    result['source_files'] = group(source, old['source_files']['files'] + ['paper/integrated/native-staged-construction.tex'])
    added = [str(p.relative_to(ROOT)) for name in ('native-staged-construction-v1', 'native-staged-fixed-v1')
        for p in sorted((ROOT / 'paper/figures' / name).iterdir()) if p.is_file()]
    result['figure_files'] = group(source, old['figure_files']['files'] + added)
    result['support_files'] = group(source, old['support_files']['files'] + [
        'scripts/reports/integrated_staged_actual_build_v1.py', 'tests/reports/test_native_staged_closed_retained_v1.py'])
    result['evidence_files'] = group(source, old['evidence_files']['files'] + [dev_name, fixed_name,
        'research/results/native-open-staged-first-operative-agenda-v1.json',
        'research/data/native-direction-support-v1/report.json',
        'research/publication/native-staged-next-evidence-decision-v1.md'])
    bodies = {name: (ROOT / name).read_bytes() for key in ('source_files', 'figure_files', 'support_files')
        for name in result[key]['files']}
    result['literal_dependencies'] = literal_dependencies(bodies, result['entrypoint'], repository_parent_inputs=True)
    with (ROOT / OUTPUT).open('xb') as stream:
        stream.write((builds[0] / 'integrated.pdf').read_bytes())
    save(ROOT / RECEIPT, result)
    print(json.dumps({k: result[k] for k in ('pages', 'figures', 'tables', 'cited_references', 'pdf_sha256')}))


if __name__ == '__main__':
    main()
