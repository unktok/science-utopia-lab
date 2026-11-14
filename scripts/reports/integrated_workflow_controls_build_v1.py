"""Retain the built and visually reviewed workflow working paper; no builds."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.reports.integrated_native_numeric_build_v1 import Bounds
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
SOURCE = '173d2e342db911ad3b685fe6967c829bb93a2a73'
OLD = 'paper/integrated-native-numeric-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-workflow-controls-working-paper.pdf'
RECEIPT = 'paper/integrated-workflow-controls-build-v1.json'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def group(names):
    hashes = {}
    for name in sorted(set(names)):
        raw = subprocess.check_output(['git', 'show', SOURCE + ':' + name], cwd=ROOT)
        if (ROOT / name).read_bytes() != raw: raise ValueError('built paper input changed: ' + name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return {'files': list(hashes), 'manifest_sha256': hashlib.sha256(json.dumps(
        hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-pages-reviewed', action='store_true', required=True)
    args = parser.parse_args()
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    if not args.all_pages_reviewed or git('status', '--porcelain'):
        raise ValueError('actual complete visual review and clean retention source required')
    retention_source = git('rev-parse', 'HEAD')
    if (ROOT / OUTPUT).exists() or (ROOT / RECEIPT).exists(): raise ValueError('preserve existing PDF/receipt')
    old = checked(json.loads((ROOT / OLD).read_text()))
    preserved = {**old['preserved_files'], OLD: sha(ROOT / OLD), old['output']: old['pdf_sha256']}
    if any(sha(ROOT / name) != expected for name, expected in preserved.items()):
        raise ValueError('historical manuscript artifact changed')
    builds = [ROOT / ('tmp/pdfs/integrated-workflow-controls-a' + str(i)) for i in (7, 8)]
    texts = [(p / 'integrated.txt').read_bytes() for p in builds]
    logs = [(p / 'integrated.log').read_bytes() for p in builds]
    if texts[0] != texts[1] or logs[0] != logs[1]: raise ValueError('actual cached builds disagree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', logs[0]) or b'??' in texts[0]:
        raise ValueError('unresolved text/layout/reference diagnostic')
    bbox = (builds[0] / 'bbox.html').read_text(); bounds = Bounds(); bounds.feed(bbox)
    if bounds.pages != 75 or bounds.outside or bounds.words != bbox.count('<word '):
        raise ValueError('complete in-page Poppler text coverage required')
    aux = (builds[0] / 'integrated.aux').read_text()
    figures = len(re.findall(r'\\contentsline \{figure\}', aux))
    tables = len(re.findall(r'\\contentsline \{table\}', aux))
    refs = (builds[0] / 'integrated.bbl').read_text().count('\\bibitem')
    if (figures, tables, refs) != (39, 31, 26): raise ValueError('final observed object inventory differs')
    render = ROOT / 'tmp/pdfs/integrated-workflow-controls-render-a7'
    pages = sorted(render.glob('page-*.png'))
    if [p.name for p in pages] != [f'page-{i:02}.png' for i in range(1, 76)]:
        raise ValueError('all final page renders required')
    prior = ROOT / 'tmp/pdfs/integrated-workflow-controls-render-a3'
    if any(sha(render / f'page-{i:02}.png') != sha(prior / f'page-{i:02}.png') for i in range(1, 55)):
        raise ValueError('previously reviewed unchanged prefix differs')
    details = ROOT / 'tmp/pdfs/integrated-workflow-controls-detail-a7'
    if any(not (details / f'{prefix}-{i:02}.png').is_file()
            for prefix, indexes in (('first', range(1, 4)), ('new', range(54, 58))) for i in indexes):
        raise ValueError('fresh final detail images required')
    result = {k: v for k, v in old.items() if k != 'content_sha256'}
    result.update(schema='scienceutopia.integrated-workflow-controls-manuscript.v1',
        source_commit=SOURCE, retention_tool_source_commit=retention_source,
        output=OUTPUT, pages=75, figures=figures, tables=tables, cited_references=refs,
        pdf_sha256=sha(builds[0] / 'integrated.pdf'), preserved_files=preserved,
        new_paper_rebuild_subset_verified=False, publication_ready=False,
        editorial_changes=['Keep all prior meaningful research tracks without an artificial page cap',
            'Add both original-source cold-verified completed workflow controls and actual annual figure',
            'Separate joint timing/routing hand effect from invention and isolated causal identification',
            'Retain actual four-call output-mode and one-call capacity failures without repair or scientific losses'],
        build={'directories': [str(p.relative_to(ROOT)) for p in builds], 'engine': 'Tectonic 0.17.0',
            'flags': '--only-cached --untrusted --keep-logs --keep-intermediates', 'exit_codes': [0, 0],
            'downloads': 0, 'text_identical': True, 'text_sha256': hashlib.sha256(texts[0]).hexdigest(),
            'log_sha256': [hashlib.sha256(v).hexdigest() for v in logs], 'binary_pdf_identity_claimed': False,
            'layout_or_undefined_reference_warnings': 0, 'off_page_text_words': 0,
            'bbox_word_tags_accounted': bounds.words, 'bbox_parser': 'HTMLParser; all Poppler word tags counted',
            'unresolved_question_mark_pairs': 0,
            'benign_notices': ['inputenc ignored for UTF8 engine', 'Two historical h floats adjusted to ht'],
            'earlier_prebuild_failure': 'Wrong caller cwd caused Git pathspec and absent output-directory errors before TeX; no science or existing PDF changed.',
            'earlier_visual_revisions': ['a3/a4 preserve the first reviewed long section tail',
                'a5/a6 preserve the shorter but still split final paragraph',
                'a7/a8 final text keeps the workflow section entirely before Discussion']},
        visual_review={'all_final_pages_reviewed': True, 'pages_reviewed_for_layout': 75,
            'pages_reviewed': list(range(1, 76)), 'render_dpi': 90,
            'reviewed_prefix_by_byte_identity_to_a3': list(range(1, 55)),
            'fresh_final_contact_sheets': 'tmp/pdfs/integrated-workflow-controls-sheets-a7',
            'fresh_150dpi_detail_pages': [1, 2, 3, 54, 55, 56, 57],
            'clipped_or_overlapping_content_observed': False,
            'page_png_sha256': {p.name: sha(p) for p in pages}})
    result['source_files'] = group(old['source_files']['files'] + ['paper/integrated/native-workflow-controls.tex'])
    result['figure_files'] = group(old['figure_files']['files'] + [str(p.relative_to(ROOT))
        for p in sorted((ROOT / 'paper/figures/native-workflow-controls-paper-v1').iterdir()) if p.is_file()])
    result['support_files'] = group(old['support_files']['files'] + [
        'scripts/figures/native_workflow_controls_paper_v1.py', 'tests/reports/test_native_workflow_controls_paper_v1.py'])
    result['evidence_files'] = group(old['evidence_files']['files'] + [
        'research/results/native-workflow-v3-stop-and-control-contrast-v1.json',
        'research/results/native-workflow-v3-stopped-controls-cold-proof-v1.json',
        'research/results/native-workflow-output-mode-assay-v1.json',
        'research/results/native-workflow-thinking-capacity-probe-v1.json'])
    result['scientific_scope'].update(workflow_complete_control_worlds=2, workflow_own_native_worlds=0,
        workflow_normal_study_closure=False, workflow_final_selection=None,
        workflow_developer_joint_timing_routing_contrast=True, workflow_isolated_cost_order_effect=False,
        workflow_actual_output_mode_calls=4, workflow_actual_capacity_calls=1,
        workflow_new_scientific_losses_from_interface_probes=0, workflow_invention_improvement=False)
    # The visual flag records the preceding actual inspection, not an automated
    # claim that text extraction can prove typography or scientific merit.
    (ROOT / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    with (ROOT / OUTPUT).open('xb') as f: f.write((builds[0] / 'integrated.pdf').read_bytes())
    save(ROOT / RECEIPT, result)
    print(json.dumps({'pages': 75, 'figures': figures, 'tables': tables,
        'pdf_sha256': result['pdf_sha256'], 'publication_ready': False}))


if __name__ == '__main__': main()
