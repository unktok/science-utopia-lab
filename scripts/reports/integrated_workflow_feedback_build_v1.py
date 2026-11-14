"""Retain the actually built/reviewed feedback paper, without rerunning science.

The review flag records actual visual inspection, not an automated quality claim.
The earlier reviewed artifacts and failed build attempts are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.reports.integrated_native_numeric_build_v1 import Bounds
from scripts.reports.paper_rebuild_bundle import literal_dependencies
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
OLD = 'paper/integrated-workflow-controls-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-workflow-feedback-working-paper.pdf'
RECEIPT = 'paper/integrated-workflow-feedback-build-v1.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def group(source, names):
    hashes = {}
    for name in sorted(set(names)):
        raw = subprocess.check_output(['git', 'show', source + ':' + name], cwd=ROOT)
        if (ROOT / name).is_symlink() or (ROOT / name).read_bytes() != raw:
            raise ValueError('built paper input changed: ' + name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return {'files': list(hashes), 'manifest_sha256': hashlib.sha256(
        json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--all-pages-reviewed', action='store_true', required=True)
    p.add_argument('--build-one', type=Path, required=True)
    p.add_argument('--build-two', type=Path, required=True)
    p.add_argument('--render-one', type=Path, required=True)
    p.add_argument('--render-two', type=Path, required=True)
    p.add_argument('--contact-sheets', type=Path, required=True)
    a = p.parse_args()
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    if not a.all_pages_reviewed or git('status', '--porcelain'):
        raise ValueError('actual complete visual review and clean committed source required')
    source = git('rev-parse', 'HEAD')
    if any((ROOT / name).exists() for name in (OUTPUT, RECEIPT)):
        raise ValueError('fresh output/receipt required')
    old = checked(json.loads((ROOT / OLD).read_text()))
    preserved = {**old['preserved_files'], OLD: sha(ROOT / OLD), old['output']: old['pdf_sha256']}
    if any(sha(ROOT / name) != expected for name, expected in preserved.items()):
        raise ValueError('historical reviewed artifact changed')
    builds = [a.build_one.resolve(), a.build_two.resolve()]
    if builds[0] == builds[1]:
        raise ValueError('two separate actual builds required')
    texts = [(path / 'integrated.txt').read_bytes() for path in builds]
    logs = [(path / 'integrated.log').read_bytes() for path in builds]
    if texts[0] != texts[1] or logs[0] != logs[1]:
        raise ValueError('two actual cached builds disagree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', logs[0]) or b'??' in texts[0]:
        raise ValueError('unresolved layout/reference diagnostic')
    bbox = (builds[0] / 'bbox.html').read_text()
    bounds = Bounds(); bounds.feed(bbox)
    if bounds.pages < old['pages'] or bounds.outside or not bounds.words or bounds.words != bbox.count('<word '):
        raise ValueError('complete in-page text coverage required')
    aux = (builds[0] / 'integrated.aux').read_text()
    figures = len(re.findall(r'\\contentsline \{figure\}', aux))
    tables = len(re.findall(r'\\contentsline \{table\}', aux))
    refs = (builds[0] / 'integrated.bbl').read_text().count('\\bibitem')
    if figures < old['figures'] + 1 or tables < old['tables'] + 2 or refs < old['cited_references']:
        raise ValueError('new figures/tables or prior research content omitted')
    renders = [a.render_one.resolve(), a.render_two.resolve()]
    if renders[0] == renders[1]:
        raise ValueError('two distinct final render directories required')
    page_names = [f'page-{i:02}.png' for i in range(1, bounds.pages + 1)]
    for path in renders:
        if sorted(p.name for p in path.glob('page-*.png')) != page_names:
            raise ValueError('all final page PNGs required')
    if any(sha(renders[0] / n) != sha(renders[1] / n) for n in page_names):
        raise ValueError('two complete rendered builds differ')
    sheets = sorted(a.contact_sheets.glob('sheet-*.png'))
    if len(sheets) != (bounds.pages + 11) // 12:
        raise ValueError('complete labelled contact sheets required')
    result = {k: v for k, v in old.items() if k != 'content_sha256'}
    result.update(schema='scienceutopia.integrated-workflow-feedback-manuscript.v1',
        source_commit=source, retention_tool_source_commit=source,
        output=OUTPUT, tex_sha256=sha(ROOT / 'paper/integrated.tex'),
        pages=bounds.pages, figures=figures, tables=tables, cited_references=refs,
        pdf_sha256=sha(builds[0] / 'integrated.pdf'), preserved_files=preserved,
        new_paper_rebuild_subset_verified=False, publication_ready=False,
        editorial_changes=['Retain prior meaningful studies without an artificial page cap',
            'Add all six compiler-feedback proposal slots, paths and observed input classes',
            'Add all three physical unused-condition worlds/four frozen labels and corrected critic costs',
            'Separate active SCRIPTED open-institution integration from unexecuted model invention'],
        build={'directories': [str(v.relative_to(ROOT)) for v in builds],
            'engine': 'Tectonic 0.17.0',
            'flags': '--only-cached --untrusted --keep-logs --keep-intermediates',
            'exit_codes': [0, 0], 'downloads': 0, 'text_identical': True,
            'text_sha256': hashlib.sha256(texts[0]).hexdigest(),
            'log_sha256': [hashlib.sha256(v).hexdigest() for v in logs],
            'binary_pdf_identity_claimed': False, 'rendered_page_identity_verified': True,
            'layout_or_undefined_reference_warnings': 0, 'off_page_text_words': 0,
            'bbox_word_tags_accounted': bounds.words, 'unresolved_question_mark_pairs': 0,
            'benign_notices': ['inputenc ignored for UTF8 engine', 'Historical h floats adjusted to ht']},
        visual_review={'all_final_pages_reviewed': True, 'pages_reviewed_for_layout': bounds.pages,
            'pages_reviewed': list(range(1, bounds.pages + 1)), 'render_dpi': 90,
            'contact_sheet_directory': str(a.contact_sheets.resolve().relative_to(ROOT)),
            'clipped_or_overlapping_content_observed': False,
            'page_png_sha256': {name: sha(renders[0] / name) for name in page_names}})
    result['source_files'] = group(source, old['source_files']['files'] + [
        'paper/integrated/native-workflow-feedback.tex'])
    new_figures = [str(p.relative_to(ROOT)) for directory in (
        'native-workflow-compiler-feedback-v2', 'native-workflow-feedback-fixed-v3')
        for p in sorted((ROOT / 'paper/figures' / directory).iterdir()) if p.is_file()]
    result['figure_files'] = group(source, old['figure_files']['files'] + new_figures)
    result['support_files'] = group(source, old['support_files']['files'] + [
        'scripts/reports/integrated_workflow_feedback_build_v1.py',
        'tests/reports/test_integrated_workflow_feedback_paper.py',
        'scripts/reports/pre_scale_costs_v1.py', 'tests/reports/test_pre_scale_costs.py'])
    result['evidence_files'] = group(source, old['evidence_files']['files'] + [
        'research/results/native-workflow-compiler-feedback-closed-v2.json',
        'research/results/native-workflow-feedback-fixed-closed-v3.json',
        'research/results/native-open-workflow-native-software-v1.json'])
    bodies = {name: (ROOT / name).read_bytes() for name in
        result['source_files']['files'] + result['figure_files']['files'] + result['support_files']['files']}
    result['literal_dependencies'] = literal_dependencies(bodies, result['entrypoint'], repository_parent_inputs=True)
    result['scientific_scope'].update(compiler_feedback_own_slots=6,
        compiler_feedback_own_completions=4, compiler_feedback_generation_nulls=2,
        compiler_feedback_development_physical_worlds=6, compiler_feedback_normal_closure=True,
        compiler_feedback_fixed_evaluation_physical_worlds=3,
        compiler_feedback_fixed_evaluation_logical_labels=4,
        compiler_feedback_unused_seeds=[1858637637], compiler_feedback_own_advantage=False,
        compiler_feedback_independent_optimizer_replication=False,
        open_institution_scripted_native_worlds=10, open_institution_real_model_calls=0,
        new_model_calls_by_manuscript_work=0, publication_ready=False)
    (ROOT / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    with (ROOT / OUTPUT).open('xb') as f:
        f.write((builds[0] / 'integrated.pdf').read_bytes())
    save(ROOT / RECEIPT, result)
    print(json.dumps({'pages': bounds.pages, 'figures': figures, 'tables': tables,
        'references': refs, 'pdf_sha256': result['pdf_sha256'], 'publication_ready': False}))


if __name__ == '__main__':
    main()
