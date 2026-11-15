"""Retain two actual reviewed builds of the closed topic-system working paper.

This does not rerun inference or turn a visual-review flag into scientific evidence.
All older reviewed PDFs and receipts are preserved byte for byte.
"""
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
OLD = 'paper/integrated-choice-resource-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-topic-systems-working-paper.pdf'
RECEIPT = 'paper/integrated-topic-systems-build-v1.json'
CLOSED = 'research/results/native-topic-free-optimization-closed-v1.json'


def page_names(pages):
    """Poppler pads page indices to the digit count of the complete PDF."""
    width = len(str(pages))
    return [f'page-{i:0{width}}.png' for i in range(1, pages + 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-pages-reviewed', action='store_true', required=True)
    for name in ('build-one', 'build-two', 'render-one', 'render-two', 'contact-sheets', 'detail-directory'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--detail-pages', type=int, nargs='+', required=True)
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    if not args.all_pages_reviewed or git('status', '--porcelain'):
        raise ValueError('clean committed source and actual complete visual review required')
    source = git('rev-parse', 'HEAD')
    if any((ROOT / name).exists() for name in (OUTPUT, RECEIPT)):
        raise ValueError('fresh PDF and receipt required')
    old = checked(json.loads((ROOT / OLD).read_text()))
    closed = json.loads((ROOT / CLOSED).read_text())
    closure, readout = closed['paired_closure'], closed['paired_readout']
    if ((closed['consumed_own_slots'], closed['complete_own_worlds'], closed['runtime_nulls']) != (6, 5, 1)
            or closed['writer']['exit_code'] != 0 or closure['exit_code'] != 0
            or closure['audit_exit_codes'] != [0, 0] or closure['cost_exit_codes'] != [0, 0]
            or not closure['audits_identical'] or not closure['costs_identical']
            or readout['exit_code'] != 0 or readout['exit_codes'] != [0, 0]
            or not readout['all_seven_files_identical'] or closed['baseline_fallback']
            or closed['held_out_evaluation'] or closed['publication_ready']):
        raise ValueError('normally closed original study with matching paired records required')
    preserved = {**old['preserved_files'], OLD: sha(ROOT / OLD), old['output']: old['pdf_sha256']}
    if any(sha(ROOT / name) != value for name, value in preserved.items()):
        raise ValueError('historical reviewed artifact changed')
    builds = [args.build_one.resolve(), args.build_two.resolve()]
    renders = [args.render_one.resolve(), args.render_two.resolve()]
    if builds[0] == builds[1] or renders[0] == renders[1]:
        raise ValueError('separate actual builds and renders required')
    texts = [(d / 'integrated.txt').read_bytes() for d in builds]
    logs = [(d / 'integrated.log').read_bytes() for d in builds]
    if texts[0] != texts[1] or logs[0] != logs[1]:
        raise ValueError('two actual cached builds disagree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', logs[0]) or b'??' in texts[0]:
        raise ValueError('unresolved layout or reference diagnostic')
    bbox = (builds[0] / 'bbox.html').read_text()
    bounds = Bounds(); bounds.feed(bbox)
    if bounds.pages < old['pages'] or bounds.outside or not bounds.words or bounds.words != bbox.count('<word '):
        raise ValueError('complete in-page text coverage required')
    aux = (builds[0] / 'integrated.aux').read_text()
    counts = (len(re.findall(r'\\contentsline \{figure\}', aux)),
              len(re.findall(r'\\contentsline \{table\}', aux)),
              (builds[0] / 'integrated.bbl').read_text().count('\\bibitem'))
    if counts != (old['figures'] + 2, old['tables'] + 3, old['cited_references']):
        raise ValueError('all prior visuals/references and two new figures/three tables required')
    names = page_names(bounds.pages)
    if any(sorted(p.name for p in d.glob('page-*.png')) != names for d in renders):
        raise ValueError('every final page PNG required')
    pages = {name: sha(renders[0] / name) for name in names}
    if any(sha(renders[1] / name) != value for name, value in pages.items()):
        raise ValueError('complete rendered builds disagree')
    sheets = sorted(args.contact_sheets.glob('sheet-*.png'))
    if len(sheets) != (bounds.pages + 11) // 12:
        raise ValueError('all labelled contact sheets required')
    detail_pages = sorted(set(args.detail_pages))
    if not {1, 4} <= set(detail_pages) or not all(1 <= p <= bounds.pages for p in detail_pages):
        raise ValueError('actual first/concept and updated-section detail review required')
    details = {f'page-{p:03}.png': sha(args.detail_directory / f'page-{p:03}.png') for p in detail_pages}
    result = {k: v for k, v in old.items() if k != 'content_sha256'}
    result.update(schema='scienceutopia.integrated-topic-systems-manuscript.v1',
        source_commit=source, retention_tool_source_commit=source, output=OUTPUT,
        pdf_sha256=sha(builds[0] / 'integrated.pdf'), tex_sha256=sha(ROOT / 'paper/integrated.tex'),
        pages=bounds.pages, figures=counts[0], tables=counts[1], cited_references=counts[2],
        preserved_files=preserved, publication_ready=False, new_paper_rebuild_subset_verified=False,
        editorial_changes=[
            'Retain all meaningful previous research tracks without an artificial page cap',
            'Add same-authority original-topic controls and conditional calendar/content diagnostics',
            'Add all six closed free-system slots, frozen selection, effects and full per-role costs',
            'Keep failure, unchanged parent, conditional consumer incompatibility and no-reference-gain findings',
            'Separate prospective diagnostics and terminal-cost forecast from observed scientific gains'],
        scientific_scope={'previous_receipt': OLD, 'previous_receipt_scope': old['scientific_scope'],
            'closed_study_file_sha256': sha(ROOT / CLOSED),
            'scientific_source_commit': closed['scientific_source_commit'],
            'own_slots': 6, 'complete_own_worlds': 5, 'runtime_nulls': 1,
            'physical_attempts': 8, 'own_advantage_demonstrated': False,
            'new_scientific_model_calls_by_manuscript_work': 0,
            'independent_optimizer_replication': False, 'new_unused_evaluation': False,
            'publication_ready': False},
        build={'directories': [str(d.relative_to(ROOT)) for d in builds], 'engine': 'Tectonic 0.17.0',
            'flags': '--only-cached --untrusted --keep-logs --keep-intermediates',
            'exit_codes': [0, 0], 'downloads': 0, 'text_identical': True,
            'text_sha256': hashlib.sha256(texts[0]).hexdigest(),
            'log_sha256': [hashlib.sha256(log).hexdigest() for log in logs],
            'binary_pdf_identical': (builds[0] / 'integrated.pdf').read_bytes() == (builds[1] / 'integrated.pdf').read_bytes(),
            'rendered_page_identity_verified': True, 'overfull_underfull_or_undefined_diagnostics': 0,
            'off_page_text_words': bounds.outside, 'bbox_word_tags_accounted': bounds.words,
            'unresolved_question_mark_pairs': 0},
        visual_review={'all_final_pages_reviewed': True, 'pages_reviewed_for_layout': bounds.pages,
            'pages_reviewed': list(range(1, bounds.pages + 1)), 'render_dpi': 90,
            'contact_sheet_directory': str(args.contact_sheets.resolve().relative_to(ROOT)),
            'contact_sheet_sha256': {p.name: sha(p) for p in sheets},
            'detail_pages_reviewed': detail_pages, 'detail_render_dpi': 150,
            'detail_directory': str(args.detail_directory.resolve().relative_to(ROOT)),
            'detail_png_sha256': details, 'clipped_or_overlapping_content_observed': False,
            'page_png_sha256': pages})
    result['source_files'] = group(source, old['source_files']['files'] + [
        'paper/integrated/native-topic-system-search.tex'])
    added_figures = [str(p.relative_to(ROOT)) for p in sorted(
        (ROOT / 'paper/figures/native-topic-free-v1').iterdir()) if p.is_file()]
    result['figure_files'] = group(source, old['figure_files']['files'] + added_figures)
    result['support_files'] = group(source, old['support_files']['files'] + [
        'scripts/reports/integrated_topic_systems_build_v1.py',
        'tests/reports/test_topic_system_manuscript_v1.py'])
    evidence = [CLOSED, 'research/results/native-legacy-topic-pilot-closed-v1.json',
        'research/results/native-topic-free-first-resource-outcomes-v1.json',
        'research/results/native-topic-free-throughput-g1-submission-v1.json',
        'research/results/native-topic-fixed-record-support-v1.json',
        'research/results/native-terminal-cost-opportunity-preparation-v1.json',
        'research/results/native-project-delivery-feedback-preparation-v1.json',
        'research/results/native-project-feedback-outer-v1.json',
        'research/results/native-topic-effect-map-retention-v1.json',
        'research/protocols/campaigns/native-topic-free-optimization-v1.md']
    evidence += [str(p.relative_to(ROOT)) for p in
        sorted((ROOT / 'research/data/native-topic-free-optimization-v1').rglob('*')) if p.is_file()]
    result['evidence_files'] = group(source, old['evidence_files']['files'] + evidence)
    bodies = {name: (ROOT / name).read_bytes() for key in ('source_files', 'figure_files', 'support_files')
        for name in result[key]['files']}
    result['literal_dependencies'] = literal_dependencies(bodies, result['entrypoint'], repository_parent_inputs=True)
    with (ROOT / OUTPUT).open('xb') as stream:
        stream.write((builds[0] / 'integrated.pdf').read_bytes())
    save(ROOT / RECEIPT, result)
    print(json.dumps({k: result[k] for k in ('pages', 'figures', 'tables', 'cited_references', 'pdf_sha256')}))


if __name__ == '__main__':
    main()
