"""Retain reviewed staged-construction/priority update; never rerun science."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import json

from scripts.reports.integrated_native_numeric_build_v1 import Bounds
from scripts.reports.integrated_workflow_feedback_build_v1 import group, sha
from scripts.reports.paper_rebuild_bundle import literal_dependencies
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[2]
OLD = 'paper/integrated-open-institutions-build-v1.json'
OUTPUT = 'output/pdf/science-utopia-lab-integrated-staged-construction-working-paper.pdf'
RECEIPT = 'paper/integrated-staged-construction-build-v1.json'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--all-pages-reviewed', action='store_true', required=True)
    for name in ('build-one','build-two','render-one','render-two','contact-sheets'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    git = lambda *args: subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    if not a.all_pages_reviewed or git('status','--porcelain'):
        raise ValueError('clean committed source and actual full visual review required')
    source = git('rev-parse','HEAD')
    if any((ROOT/name).exists() for name in (OUTPUT,RECEIPT)):
        raise ValueError('fresh paper/receipt required; no historical artifact overwrite')
    read = lambda name: checked(json.loads((ROOT/name).read_text()))
    old = read(OLD)
    proof = read('research/results/native-open-workflow-staged-native-software-v1.json')
    prepared = read('research/results/native-open-staged-institution-prepared-v1.json')
    if (proof['exit_code']!=0 or proof['native_software_worlds']!=10
            or proof['annual_checkpoints']!=40 or proof['actual_model_calls']!=0
            or proof['real_backend_calibration_passed'] or proof['actual_scientific_gain_claimed']
            or prepared['real_writer_started'] or prepared['actual_model_POSTs']!=0):
        raise ValueError('exact software/pre-dispatch evidence required, not invented model outcomes')
    preserved = {**old['preserved_files'], OLD:sha(ROOT/OLD), old['output']:old['pdf_sha256']}
    if any(sha(ROOT/name)!=value for name,value in preserved.items()):
        raise ValueError('historical reviewed artifact changed')
    builds = [a.build_one.resolve(),a.build_two.resolve()]
    renders = [a.render_one.resolve(),a.render_two.resolve()]
    if builds[0]==builds[1] or renders[0]==renders[1]:
        raise ValueError('distinct actual builds/renders required')
    texts = [(d/'integrated.txt').read_bytes() for d in builds]
    logs = [(d/'integrated.log').read_bytes() for d in builds]
    if texts[0]!=texts[1] or logs[0]!=logs[1]:
        raise ValueError('two actual cached builds disagree')
    if re.search(rb'Overfull|Underfull|undefined|LaTeX Warning:.*Reference',logs[0]) or b'??' in texts[0]:
        raise ValueError('layout/reference diagnostics remain')
    bounds = Bounds(); bbox = (builds[0]/'bbox.html').read_text(); bounds.feed(bbox)
    if bounds.pages<old['pages'] or bounds.outside or not bounds.words or bounds.words!=bbox.count('<word '):
        raise ValueError('complete in-page Poppler text required')
    aux = (builds[0]/'integrated.aux').read_text(); bbl = (builds[0]/'integrated.bbl').read_text()
    figures = len(re.findall(r'\\contentsline \{figure\}',aux))
    tables = len(re.findall(r'\\contentsline \{table\}',aux))
    references = bbl.count('\\bibitem')
    if (figures!=old['figures'] or tables!=old['tables'] or references!=old['cited_references']+1
            or bbl.count('{liu2025mechanism}')!=1 or bbl.count('{narayanaswami2022programmatic}')!=1):
        raise ValueError('all existing visuals and exactly one new reference required; AMD-LLM is already cited')
    names = [f'page-{i:02}.png' for i in range(1,bounds.pages+1)]
    if any(sorted(p.name for p in d.glob('page-*.png'))!=names for d in renders):
        raise ValueError('complete final renders required')
    pages = {name:sha(renders[0]/name) for name in names}
    if any(sha(renders[1]/name)!=value for name,value in pages.items()):
        raise ValueError('rendered pages differ between actual builds')
    if len(list(a.contact_sheets.glob('sheet-*.png')))!=(bounds.pages+11)//12:
        raise ValueError('complete labelled contact sheets required')
    result = {k:v for k,v in old.items() if k!='content_sha256'}
    result.update(schema='scienceutopia.integrated-staged-construction-manuscript.v1',source_commit=source,
        retention_tool_source_commit=source,output=OUTPUT,pdf_sha256=sha(builds[0]/'integrated.pdf'),
        tex_sha256=sha(ROOT/'paper/integrated.tex'),pages=bounds.pages,figures=figures,tables=tables,
        cited_references=references,preserved_files=preserved,new_paper_rebuild_subset_verified=False,
        publication_ready=False,editorial_changes=[
            'Add ALA2022 programmatic mechanism-design precedent without duplicating existing AMD-LLM',
            'Separate application-specific formulation from priority for programs or mixed structural/numeric search',
            'Add full staged construction software boundary without claiming model repair or new scientific outcomes'],
        scientific_scope={'previous_receipt':OLD,'previous_receipt_scope':old['scientific_scope'],
            'staged_software_evidence_content_sha256':proof['content_sha256'],
            'prepared_real_study_content_sha256':prepared['content_sha256'],
            'new_scientific_model_calls':0,'new_scientific_optimizer_results':0,
            'autonomous_repair_or_gain_claimed':False,'independent_optimizer_replication':False,
            'real_staged_campaign_started_at_manuscript_snapshot':False,'publication_ready':False},
        build={'directories':[str(d.relative_to(ROOT)) for d in builds],
            'engine':'Tectonic 0.17.0','flags':'--only-cached --untrusted --keep-logs --keep-intermediates',
            'exit_codes':[0,0],'downloads':0,'text_identical':True,
            'text_sha256':hashlib.sha256(texts[0]).hexdigest(),
            'log_sha256':[hashlib.sha256(value).hexdigest() for value in logs],
            'binary_pdf_identity_claimed':False,'rendered_page_identity_verified':True,
            'layout_or_undefined_reference_warnings':0,'off_page_text_words':bounds.outside,
            'bbox_word_tags_accounted':bounds.words,'unresolved_question_mark_pairs':0},
        visual_review={'all_final_pages_reviewed':True,'pages_reviewed_for_layout':bounds.pages,
            'pages_reviewed':list(range(1,bounds.pages+1)),'render_dpi':90,
            'contact_sheet_directory':str(a.contact_sheets.resolve().relative_to(ROOT)),
            'clipped_or_overlapping_content_observed':False,'page_png_sha256':pages})
    result['source_files'] = group(source,old['source_files']['files'])
    result['figure_files'] = group(source,old['figure_files']['files'])
    result['support_files'] = group(source,old['support_files']['files']+[
        'scripts/reports/integrated_staged_construction_build_v1.py',
        'tests/reports/test_staged_manuscript_sources_v1.py'])
    result['evidence_files'] = group(source,old['evidence_files']['files']+[
        'research/results/native-open-workflow-staged-native-software-v1.json',
        'research/results/native-open-staged-institution-prepared-v1.json',
        'research/publication/novelty-addendum-programmatic-institutions-v1.md'])
    bodies = {name:(ROOT/name).read_bytes() for key in ('source_files','figure_files','support_files')
        for name in result[key]['files']}
    result['literal_dependencies'] = literal_dependencies(bodies,result['entrypoint'],repository_parent_inputs=True)
    with (ROOT/OUTPUT).open('xb') as stream: stream.write((builds[0]/'integrated.pdf').read_bytes())
    save(ROOT/RECEIPT,result)
    print(json.dumps({k:result[k] for k in ('pages','figures','tables','cited_references','pdf_sha256','publication_ready')}))


if __name__=='__main__':main()
