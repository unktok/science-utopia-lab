"""Retain the already built/reviewed numeric working paper, not new science.

The review flag records a human/agent observation; it does not automate visual
judgment. No TeX, model, world, or scientific analysis is executed by this tool.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
SOURCE = '3d8e10541b8b1bbce07b4250289643097d354de4'
OLD = 'paper/integrated-planning-search-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-native-numeric-working-paper.pdf'
RECEIPT = 'paper/integrated-native-numeric-build-v1.json'


def sha(body):
    return hashlib.sha256(body).hexdigest()


class Bounds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pages = self.words = self.outside = 0
        self.size = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'page':
            self.pages += 1
            self.size = tuple(float(attrs[k]) for k in ('width', 'height'))
        elif tag == 'word':
            if self.size is None:
                raise ValueError('word outside a Poppler page')
            self.words += 1
            x0, y0, x1, y1 = (float(attrs[k]) for k in ('xmin', 'ymin', 'xmax', 'ymax'))
            if not (0 <= x0 <= x1 <= self.size[0] and 0 <= y0 <= y1 <= self.size[1]):
                self.outside += 1

    def handle_endtag(self, tag):
        if tag == 'page':
            self.size = None


def group(names):
    names = sorted(set(names))
    hashes = {}
    for name in names:
        blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', SOURCE + ':' + name])
        if (ROOT / name).read_bytes() != blob:
            raise ValueError('manuscript input changed since actual build: ' + name)
        hashes[name] = sha(blob)
    return {'files': names, 'manifest_sha256': sha(json.dumps(
        hashes, sort_keys=True, separators=(',', ':')).encode())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-pages-reviewed', action='store_true', required=True)
    args = parser.parse_args()
    if not args.all_pages_reviewed:
        parser.error('complete actual visual inspection first')
    git = lambda *a: subprocess.check_output(['git', '-C', str(ROOT), *a], text=True).strip()
    if git('status', '--porcelain'):
        raise ValueError('commit retention tool before generating artifacts')
    retention_source = git('rev-parse', 'HEAD')
    if any((ROOT / name).exists() for name in (OUTPUT, RECEIPT)):
        raise ValueError('fresh artifact/receipt required; preserve old bytes')
    old = checked(json.loads((ROOT / OLD).read_text()))
    preserved = dict(old['preserved_files'])
    preserved.update({OLD: sha((ROOT / OLD).read_bytes()), old['output']: old['pdf_sha256']})
    if any(sha((ROOT / name).read_bytes()) != value for name, value in preserved.items()):
        raise ValueError('historical artifact changed')
    dirs = ['tmp/pdfs/integrated-native-numeric-a3', 'tmp/pdfs/integrated-native-numeric-a4']
    builds = [ROOT / name for name in dirs]
    texts = [(p / 'integrated.txt').read_bytes() for p in builds]
    logs = [(p / 'integrated.log').read_bytes() for p in builds]
    if texts[0] != texts[1] or logs[0] != logs[1]:
        raise ValueError('two actual cached builds do not agree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference', logs[0]) or b'??' in texts[0]:
        raise ValueError('unresolved manuscript layout/reference diagnostic')
    bounds = Bounds()
    bbox = (builds[0] / 'bbox.html').read_text()
    bounds.feed(bbox)
    if bounds.pages != 73 or bounds.words != bbox.count('<word ') or not bounds.words or bounds.outside:
        raise ValueError('incomplete or off-page Poppler text bounds')
    aux = (builds[0] / 'integrated.aux').read_text()
    figures = len(re.findall(r'\\contentsline \{figure\}', aux))
    tables = len(re.findall(r'\\contentsline \{table\}', aux))
    refs = (builds[0] / 'integrated.bbl').read_text().count('\\bibitem')
    if (figures, tables, refs) != (38, 30, 26):
        raise ValueError('actual figure/table/reference inventory differs')
    render = ROOT / 'tmp/pdfs/integrated-native-numeric-render-a3'
    pages = sorted(render.glob('page-*.png'))
    if [p.name for p in pages] != [f'page-{i:02}.png' for i in range(1, 74)]:
        raise ValueError('complete original page render required')
    details = ROOT / 'tmp/pdfs/integrated-native-numeric-detail-a3'
    detail_pages = [1, 2, 3, 6, 51, 52, 53, 54]
    if any(not (details / f'page-{i}-{i:02}.png').is_file() for i in detail_pages):
        raise ValueError('fresh detail renders missing')
    result = {k: v for k, v in old.items() if k != 'content_sha256'}
    result.update(source_commit=SOURCE, retention_tool_source_commit=retention_source,
        output=OUTPUT, pages=73, figures=figures, tables=tables, cited_references=refs,
        pdf_sha256=sha((builds[0] / 'integrated.pdf').read_bytes()), preserved_files=preserved,
        new_paper_rebuild_subset_verified=False, publication_ready=False,
        editorial_changes=[
            'Retain every meaningful earlier scientific track without an artificial page cap',
            'Add conditional 240-call reserve analysis and original realized ledger, not counterfactual worlds',
            'Add all six normally closed numeric worlds and distinct own/incumbent paths, with no incumbent gain',
            'Use two print-scale graphics and distinguish SCRIPTED workflow proof from model evidence'],
        build={'directories': dirs, 'engine': 'Tectonic 0.17.0',
            'flags': '--only-cached --untrusted --keep-logs --keep-intermediates',
            'exit_codes': [0, 0], 'downloads': 0, 'text_identical': True,
            'text_sha256': sha(texts[0]), 'log_sha256': [sha(b) for b in logs],
            'binary_pdf_identity_claimed': False, 'layout_or_undefined_reference_warnings': 0,
            'off_page_text_words': bounds.outside, 'bbox_word_tags_accounted': bounds.words,
            'bbox_parser': 'HTMLParser; all Poppler word tags counted',
            'unresolved_question_mark_pairs': 0,
            'benign_notices': ['inputenc ignored for UTF8 engine', 'Two historical h floats adjusted to ht']},
        visual_review={'all_final_pages_reviewed': True, 'pages_reviewed_for_layout': 73,
            'pages_reviewed': list(range(1, 74)), 'render_dpi': 90,
            'contact_sheet_directory': 'tmp/pdfs/integrated-native-numeric-sheets-a3',
            'fresh_150dpi_detail_pages': detail_pages, 'clipped_or_overlapping_content_observed': False,
            'page_png_sha256': {p.name: sha(p.read_bytes()) for p in pages}})
    result['source_files'] = group(old['source_files']['files'] + [
        'paper/integrated/native-reserve-response.tex', 'paper/integrated/native-numeric-comparator.tex'])
    new_figures = [str(p.relative_to(ROOT)) for name in ('native-reserve-paper-v1', 'native-numeric-paper-v1')
                   for p in (ROOT / 'paper/figures' / name).iterdir() if p.is_file()]
    result['figure_files'] = group(old['figure_files']['files'] + new_figures)
    result['support_files'] = group(old['support_files']['files'] + [
        'scripts/reports/native_reserve_paper_v1.py',
        'tests/reports/test_integrated_reserve_response_paper.py',
        'tests/reports/test_integrated_numeric_comparator_paper.py'])
    additions = [str(p.relative_to(ROOT)) for name in (
        'native-reserve-command-response-v1', 'native-parameter-comparator-v1')
        for p in (ROOT / 'research/data' / name).rglob('*') if p.is_file()]
    additions += ['research/results/native-parameter-comparator-closed-v1.json',
                  'research/results/native-workflow-v2-preparation-v1.json']
    result['evidence_files'] = group(old['evidence_files']['files'] + additions)
    result['scientific_scope'].update(numeric_physical_worlds=6, numeric_world_seed=61001,
        numeric_technical_nulls=0, numeric_observed_input_classes=4,
        numeric_incumbent_improvement=False, numeric_independent_optimizer_replication=False,
        numeric_unused_evaluation_dispatched=False, reserve_fixed_input_component_calls=240,
        reserve_alternative_worlds=0, workflow_model_worlds_at_manuscript_snapshot=0,
        new_model_calls_by_manuscript_work=0, publication_ready=False)
    with (ROOT / OUTPUT).open('xb') as handle:
        handle.write((builds[0] / 'integrated.pdf').read_bytes())
    save(ROOT / RECEIPT, result)
    print(json.dumps({'pages': 73, 'figures': figures, 'tables': tables, 'references': refs,
        'words': bounds.words, 'off_page_words': bounds.outside, 'pdf_sha256': result['pdf_sha256'],
        'source_commit': SOURCE, 'preserved_artifacts': len(preserved)}))


if __name__ == '__main__':
    main()
