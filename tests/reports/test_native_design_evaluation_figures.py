"""SCRIPTED closed-study figure QA; never an inference experiment."""
from copy import deepcopy
import hashlib
import json

import pytest

from scripts.figures import native_design_evaluation as figures
from scripts.reports.native_design_benchmark import project,descriptive
from tests.reports.test_native_design_benchmark_report import fixture,hashed


def sample():
    p,a=fixture()
    return project(p,a,expected_source=p['source_commit'])


def test_all_references_all_arms_raw_pairs_missingness_and_separate_horizons():
    r=sample();before=deepcopy(r);data=figures.panel_data(r)
    assert r==before and data==figures.panel_data(r)
    assert len(data['panels'])==18 and {p['reference'] for p in data['panels']}==set(r['reference_scores'])
    assert not data['null_losses_imputed'] and not data['horizons_pooled']
    for panel in data['panels']:
        n=5 if panel['years']==2 else 1
        assert len(panel['rows'])==10 and len(panel['seeds'])==n
        assert panel['single_seed_diagnostic']==(n==1)
        for row in panel['rows']:
            assert len(row['pairs'])==n
            assert all(p['physically_shared'] for p in row['pairs'])
            assert all(p['difference'] in (None,0.) for p in row['pairs'])
    t=data['panels'][0]['rows'][0]
    assert t['summary']['available']==4 and t['summary']['missing']==1
    c=next(row for row in data['panels'][0]['rows'] if row['arm']=='selective:parameters')
    assert c['summary']['available']==3 and c['summary']['missing']==2


def test_no_selection_is_not_a_zero_loss_or_an_evaluated_null_candidate():
    r=sample();arm='throughput:parameters'
    r['selection']['selected'][arm]['system']=None;r['paired_vs_all_references'][arm]={};hashed(r)
    data=figures.panel_data(r)
    for panel in data['panels']:
        row=next(row for row in panel['rows'] if row['arm']==arm)
        assert not row['selection_available'] and row['summary'] is None and row['pairs']==[]


@pytest.mark.parametrize('mutate',[
    lambda r:r['paired_vs_all_references']['throughput:parameters']['legacy']['throughput']['2']['pairs'][0].update(difference=3),
    lambda r:r['paired_vs_all_references']['throughput:parameters']['legacy']['throughput']['2']['pairs'][0].update(physically_shared=False),
    lambda r:r['paired_vs_all_references']['throughput:parameters']['legacy']['throughput']['2']['pairs'][0].update(target_job_id='invented-job'),
    lambda r:r['paired_vs_all_references']['throughput:parameters']['legacy']['throughput']['2']['pairs'][0].update(target_loss=999),
    lambda r:r['paired_vs_all_references']['throughput:parameters']['legacy']['throughput']['2']['pairs'].reverse(),
    lambda r:r['paired_vs_all_references']['throughput:parameters']['legacy']['throughput']['2']['summary'].update(mean=-99),
    lambda r:r['evaluation'].append(deepcopy(r['evaluation'][0])),
    lambda r:r['evaluation'][0].update(years=3),
    lambda r:r['reference_scores'].update({'../bad':{}}),
])
def test_even_rehashed_disagreement_cannot_silently_become_a_graph(mutate):
    r=sample();mutate(r);hashed(r)
    with pytest.raises(ValueError):figures.panel_data(r)


def test_nonfinite_or_boolean_physical_loss_is_not_a_plot_point():
    for bad in (True,float('nan'),float('inf')):
        r=sample();r['evaluation'][0]['cross_scores']['throughput']=bad;hashed(r)
        with pytest.raises(ValueError):figures.panel_data(r)


def test_missing_pairs_are_never_imputed_or_summarized_as_zero():
    r=sample()
    for job in r['evaluation']:job['cross_scores']={k:None for k in job['cross_scores']}
    for arm,refs in r['paired_vs_all_references'].items():
        for objectives in refs.values():
            for horizons in objectives.values():
                for block in horizons.values():
                    for pair in block['pairs']:
                        pair.update(target_loss=None,reference_loss=None,difference=None)
                    block['summary']=descriptive(block['pairs'],'difference')
    hashed(r);data=figures.panel_data(r)
    assert all(row['summary']['mean'] is None and row['summary']['available']==0
        for panel in data['panels'] for row in panel['rows'])


def test_renderer_all_reference_files_hashes_watermarks_and_immutable_inputs(tmp_path):
    r=sample();before=deepcopy(r);output=tmp_path/'figures'
    manifest=figures.plot_evaluation(r,output)
    assert r==before and len(manifest['files'])==37  # 9 references x2 horizons x2 formats + plot data
    assert manifest['input_report_content_sha256']==r['content_sha256']
    for name,sha in manifest['files'].items():
        assert hashlib.sha256((output/name).read_bytes()).hexdigest()==sha
    for path in output.glob('*.svg'):
        text=path.read_text()
        assert 'SCRIPTED QA - NOT EXPERIMENTAL RESULTS' in text
        assert 'Missing: outside plot, not a loss' in text
        assert 'Same physical job' in text
    with pytest.raises(ValueError,match='fresh'):figures.plot_evaluation(r,output)


def test_cli_keeps_report_bytes_and_never_executes_model_or_candidate(tmp_path,monkeypatch):
    r=sample();p=tmp_path/'report.json';p.write_text(json.dumps(r));before=p.read_bytes()
    def fake_render(panel,classification,output):
        assert classification.startswith('SCRIPTED')
        # This case tests dispatch and bindings, not image pixels.
    monkeypatch.setattr(figures,'_render',fake_render)
    assert figures.main(['--report',str(p),'--output',str(tmp_path/'figures')])==0
    assert p.read_bytes()==before
    with pytest.raises(ValueError,match='fresh'):
        figures.main(['--report',str(p),'--output',str(tmp_path/'figures')])
