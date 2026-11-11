"""Bind the reviewed working paper to sources/assets; no TeX build or inference."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from scripts.reports.historical_paper_sources import historical_source

ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reviewed_pdf_and_complete_source_dependencies_match_receipt():
    receipt=json.loads((ROOT/'paper/submission-build-v2.json').read_text())
    assert receipt['status'] in ('working-draft-not-submission-ready','submission-ready-pending-user-approval')
    assert receipt['visual_qa']['all_pages_inspected'] is True
    assert receipt['visual_qa']['pages']==list(range(1,receipt['pages']+1))
    assets={receipt['output']:receipt['pdf_sha256'],'paper/submission.tex':receipt['tex_sha256'],
        'paper/submission-sources.bib':receipt['additional_bibliography_sha256'],
        'paper/figures/native-controls-v2-a1-print/manifest.json':receipt['strong_control_print_figure_manifest_sha256'],
        **receipt['additional_dependencies']}
    for relative,expected in assets.items():
        target=(ROOT/relative).resolve()
        assert target.is_relative_to(ROOT) and target.is_file()
        observed = sha(target) if relative == receipt['output'] else hashlib.sha256(
            historical_source('paper/submission-build-v2.json',relative)).hexdigest()
        assert observed==expected,relative
    info=shutil.which('pdfinfo')
    if info:
        text=subprocess.check_output([info,str(ROOT/receipt['output'])],text=True)
        assert int(re.search(r'^Pages:\s+(\d+)',text,re.M).group(1))==receipt['pages']


def test_manuscript_citations_and_included_figures_have_bound_local_inputs():
    receipt=json.loads((ROOT/'paper/submission-build-v2.json').read_text())
    pending=['paper/submission.tex'];visited=set();bodies=[]
    while pending:
        path=pending.pop()
        if path in visited:continue
        visited.add(path);text=historical_source('paper/submission-build-v2.json',path).decode();bodies.append(text)
        if path!='paper/submission.tex':assert path in receipt['additional_dependencies'],path
        for relative in re.findall(r'\\input\{([^}]+)\}',text):
            pending.append('paper/'+relative+('' if relative.endswith('.tex') else '.tex'))
    tex='\n'.join(bodies)
    bib=''.join(historical_source('paper/submission-build-v2.json',p).decode()
        for p in ('paper/references.bib','paper/submission-sources.bib'))
    available=set(re.findall(r'@\w+\s*\{\s*([^,\s]+)',bib))
    used={key.strip() for group in re.findall(r'\\cite\w*\{([^}]+)\}',tex) for key in group.split(',')}
    assert used and used<=available
    for relative in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex):
        assert 'paper/'+relative in receipt['additional_dependencies']


def test_resource_table_uses_tracked_observed_usage_without_imputing_or_adding_cache():
    tokens=json.loads((ROOT/'research/results/native-controls-token-costs-v1.json').read_text())
    controls=json.loads((ROOT/'research/results/native-benchmark-controls-v2-a1.json').read_text())
    tex=(ROOT/'paper/submission.tex').read_text()
    quantities={
        'Physical two-year worlds':controls['physical_world_slots'],
        'Committed scientist responses':tokens['completed_responses'],
        'Prompt tokens (including cache)':tokens['usage']['prompt_tokens']['recorded_sum'],
        'Cached prompt tokens (subset)':tokens['usage']['cached_prompt_tokens']['recorded_sum'],
        'Completion tokens':tokens['usage']['completion_tokens']['recorded_sum'],
        'Provider-reported total tokens':tokens['usage']['total_tokens']['recorded_sum'],
        'Recorded institution-code executions':controls['costs']['code_executions']['known_sum']}
    for label,value in quantities.items():assert label+' & '+format(value,',')+r'\\' in tex
    assert tokens['completed_responses']==controls['costs']['scientist_responses']['known_sum']
    assert tokens['wire_inputs_without_committed_reply']==0
    assert tokens['provider_total_component_disagreements']==0
    assert all(v['all_completed_responses_known'] and not v['invalid_responses'] for v in tokens['usage'].values())
    assert tokens['usage']['cached_prompt_tokens']['recorded_sum']<=tokens['usage']['prompt_tokens']['recorded_sum']
    assert tokens['usage']['total_tokens']['recorded_sum']==sum(tokens['usage'][k]['recorded_sum']
        for k in ('prompt_tokens','completion_tokens'))  # Never add the cached subset again.
    hardware=json.loads((ROOT/'research/results/submission-hardware-observed-v2.json').read_text())
    assert hardware['physical_memory_bytes']==hardware['physical_memory_gib']*1024**3
    assert hardware['cpu_brand_string'] in tex and f"{hardware['reported_logical_cpus']} logical CPUs" in tex
    assert not hardware['startup_environment_attested'] and not hardware['gpu_utilization_or_energy_measured']
