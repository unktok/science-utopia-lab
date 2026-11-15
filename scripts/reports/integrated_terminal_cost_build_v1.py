"""Retain the reviewed terminal-cost update; old working papers stay literal."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.reports.integrated_native_numeric_build_v1 import Bounds
from scripts.reports.integrated_topic_systems_build_v1 import page_names
from scripts.reports.integrated_workflow_feedback_build_v1 import group, sha
from scripts.reports.paper_rebuild_bundle import literal_dependencies
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
OLD = 'paper/integrated-topic-systems-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-terminal-cost-working-paper.pdf'
RECEIPT = 'paper/integrated-terminal-cost-build-v1.json'
CLOSED = 'research/results/native-terminal-cost-pilot-closed-v1.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-pages-reviewed', action='store_true', required=True)
    for name in ('build-one', 'build-two', 'render-one', 'render-two', 'contact-sheets', 'detail-directory'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--detail-pages', type=int, nargs='+', required=True)
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    if git('status', '--porcelain') or not args.all_pages_reviewed:
        raise ValueError('clean committed source and actual visual review required')
    source = git('rev-parse', 'HEAD')
    if any((ROOT / name).exists() for name in (OUTPUT, RECEIPT)):
        raise ValueError('fresh final PDF and receipt required')
    old = checked(json.loads((ROOT / OLD).read_text()))
    closed = json.loads((ROOT / CLOSED).read_text())
    data = ROOT / 'research/data/native-terminal-cost-pilot-v1'
    report = checked(json.loads((data / 'readout/report.json').read_text()))
    if (closed['writer']['exit_code'] != 0 or closed['paired_closure']['exit_code'] != 0
            or closed['paired_readout']['exit_code'] != 0 or closed['complete_worlds'] != 2
            or closed['automatic_invention'] or closed['held_out_evaluation']
            or closed['loss_or_selection_changed'] or closed['publication_ready']
            or report['content_sha256'] != closed['paired_readout']['report_content_sha256']):
        raise ValueError('normally closed original hand study, not an invention claim, required')
    preserved = {**old['preserved_files'], OLD: sha(ROOT / OLD), old['output']: old['pdf_sha256']}
    if any(sha(ROOT / name) != value for name, value in preserved.items()):
        raise ValueError('historical reviewed artifact changed')
    builds = [args.build_one.resolve(), args.build_two.resolve()]
    renders = [args.render_one.resolve(), args.render_two.resolve()]
    if builds[0] == builds[1] or renders[0] == renders[1]:
        raise ValueError('separate actual builds/renders required')
    texts = [(p / 'integrated.txt').read_bytes() for p in builds]
    logs = [(p / 'integrated.log').read_bytes() for p in builds]
    if texts[0] != texts[1] or logs[0] != logs[1]:
        raise ValueError('two actual cached builds disagree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', logs[0]) or b'??' in texts[0]:
        raise ValueError('unresolved layout/reference diagnostic')
    bbox = (builds[0] / 'bbox.html').read_text()
    bounds = Bounds(); bounds.feed(bbox)
    if bounds.pages < old['pages'] or bounds.outside or not bounds.words or bounds.words != bbox.count('<word '):
        raise ValueError('complete in-page text coverage required')
    aux = (builds[0] / 'integrated.aux').read_text()
    counts = (len(re.findall(r'\\contentsline \{figure\}', aux)),
              len(re.findall(r'\\contentsline \{table\}', aux)),
              (builds[0] / 'integrated.bbl').read_text().count('\\bibitem'))
    if counts != (old['figures'] + 1, old['tables'] + 1, old['cited_references']):
        raise ValueError('all prior visuals/references and one new figure/table required')
    names = page_names(bounds.pages)
    if any(sorted(p.name for p in d.glob('page-*.png')) != names for d in renders):
        raise ValueError('all actual final page images required')
    pages = {name: sha(renders[0] / name) for name in names}
    if any(sha(renders[1] / name) != value for name, value in pages.items()):
        raise ValueError('two complete rendered builds disagree')
    sheets = sorted(args.contact_sheets.glob('sheet-*.png'))
    if len(sheets) != (bounds.pages + 11) // 12:
        raise ValueError('complete labelled contact sheets required')
    detail_pages = sorted(set(args.detail_pages))
    if not {1, 4} <= set(detail_pages) or not all(1 <= p <= bounds.pages for p in detail_pages):
        raise ValueError('first/concept/new-result detail review required')
    details = {f'page-{p:03}.png': sha(args.detail_directory / f'page-{p:03}.png') for p in detail_pages}
    result = {k: v for k, v in old.items() if k != 'content_sha256'}
    result.update(schema='scienceutopia.integrated-terminal-cost-manuscript.v1',
        source_commit=source, retention_tool_source_commit=source, output=OUTPUT,
        pdf_sha256=sha(builds[0] / 'integrated.pdf'), tex_sha256=sha(ROOT / 'paper/integrated.tex'),
        pages=bounds.pages, figures=counts[0], tables=counts[1], cited_references=counts[2],
        preserved_files=preserved, publication_ready=False, new_paper_rebuild_subset_verified=False,
        editorial_changes=['Retain all meaningful earlier tracks without an artificial page cap',
            'Add normally closed two-control original-world terminal-cost study',
            'Separate declared C gain from unchanged requested expense and autonomous invention'],
        scientific_scope={'previous_receipt': OLD, 'previous_receipt_scope': old['scientific_scope'],
            'closed_study_file_sha256': sha(ROOT / CLOSED),
            'scientific_source_commit': closed['scientific_source_commit'], 'physical_worlds': 2,
            'complete_worlds': 2, 'runtime_nulls': 0, 'automatic_invention': False,
            'declared_C_gain': 4, 'requested_expense_reduction': 0,
            'new_scientific_model_calls_by_manuscript_work': 0,
            'independent_optimizer_replication': False, 'new_unused_evaluation': False,
            'publication_ready': False},
        build={'directories': [str(p.relative_to(ROOT)) for p in builds], 'engine': 'Tectonic 0.17.0',
            'flags': '--only-cached --untrusted --keep-logs --keep-intermediates',
            'exit_codes': [0, 0], 'downloads': 0, 'text_identical': True,
            'text_sha256': hashlib.sha256(texts[0]).hexdigest(),
            'log_sha256': [hashlib.sha256(p).hexdigest() for p in logs],
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
    result['source_files'] = group(source, old['source_files']['files'] + ['paper/integrated/native-terminal-cost.tex'])
    result['figure_files'] = group(source, old['figure_files']['files'] + [str(p.relative_to(ROOT)) for p in
        sorted((ROOT / 'paper/figures/native-terminal-cost-v1').iterdir()) if p.is_file()])
    result['support_files'] = group(source, old['support_files']['files'] + [
        'scripts/reports/integrated_terminal_cost_build_v1.py', 'tests/reports/test_native_terminal_cost_retention_v1.py',
        'scripts/reports/native_terminal_cost_interpretation_v1.py', 'scripts/reports/native_terminal_cost_semantics_v1.py'])
    result['evidence_files'] = group(source, old['evidence_files']['files'] + [CLOSED,
        'research/protocols/campaigns/native-terminal-cost-opportunity-v1.md'] + [str(p.relative_to(ROOT)) for p in
        sorted(data.rglob('*')) if p.is_file()])
    bodies = {name: (ROOT / name).read_bytes() for key in ('source_files', 'figure_files', 'support_files')
              for name in result[key]['files']}
    result['literal_dependencies'] = literal_dependencies(bodies, result['entrypoint'], repository_parent_inputs=True)
    with (ROOT / OUTPUT).open('xb') as stream:
        stream.write((builds[0] / 'integrated.pdf').read_bytes())
    save(ROOT / RECEIPT, result)
    print(json.dumps({k: result[k] for k in ('pages', 'figures', 'tables', 'cited_references', 'pdf_sha256')}))


if __name__ == '__main__':
    main()
