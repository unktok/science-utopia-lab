"""Preserved software evidence is not an actual model/evaluation certificate."""
import hashlib
import json
from pathlib import Path
import subprocess

from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest

ROOT=Path(__file__).resolve().parents[2]


def receipt():
    return checked(json.loads((ROOT/'research/results/native-capacity-fixed-evaluation-preparation-v1.json').read_text()))


def test_preparation_retains_sources_exact_qa_scope_and_no_actual_dispatch():
    r=receipt();n=r['native_qa'];f=r['final_integration']
    assert n['source_commit']=='e69af0c32907d84c6f9115be446669c868eb4db6'
    assert (n['passed'],n['failed'],n['native_worlds'],n['years'],n['initial_founders'])==(1,0,10,4,5)
    assert n['final_exit_code_observed']==f['final_exit_code_observed']==0
    assert (f['passed'],f['failed'])==(90,0)
    assert n['SCRIPTED_figures_visually_reviewed'] and not n['real_model_outcome_evidence']
    assert len(n['mocked'])==4
    assert r['prior_native_qa_permission_failure']['failed']==1
    assert not r['prior_native_qa_permission_failure']['scientific_slots_consumed']
    assert not r['prior_native_qa_permission_failure']['production_guard_relaxed']
    assert not r['scientific_followup_dispatched'] and r['evaluation_seeds_chosen'] is None
    assert not r['active_pilot_modified'] and not r['new_source_model_certificate_claimed']
    assert not r['independent_optimizer_replications_established'] and not r['publication_ready']


def test_native_qa_source_closure_reconstructs_from_original_git_not_current_code():
    n=receipt()['native_qa'];hashes={}
    for name in n['source_closure_files']:
        body=subprocess.check_output(['git','show',n['source_commit']+':'+name],cwd=ROOT)
        hashes[name]=hashlib.sha256(body).hexdigest()
    assert len(hashes)==308 and digest(hashes)==n['source_closure_manifest_sha256']
    assert 'utopia/optimization/native_active_founders.py' in hashes
    assert 'scripts/audit_native_capacity_fixed_evaluation_v1.py' in hashes


def test_official_venue_note_keeps_current_dates_and_human_signoff_distinct():
    text=(ROOT/'research/publication/venue-and-ai-readiness-2026-11-12.md').read_text()
    for url in ('https://icml.cc/Conferences/2027/Dates',
                'https://icml.cc/Conferences/2027/AuthorInstructions',
                'https://icml.cc/Conferences/2027/UseOfGenerativeAIByAuthors',
                'https://icml.cc/Conferences/2027/ContributionTypes'):
        assert url in text
    normalized=' '.join(text.split())
    assert 'January14,2027 AoE' in normalized and 'January22,2027 AoE' in normalized
    assert 'Human authors retain responsibility' in normalized
    assert 'Do not paste an example statement claiming' in normalized
    assert 'not a venue selection' in normalized
