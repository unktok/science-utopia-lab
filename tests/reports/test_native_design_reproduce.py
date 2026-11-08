"""Numerical reconstruction QA; never run a scientist or institutional program."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from scripts.reports import native_design_reproduce as rebuild


@pytest.fixture(scope='module')
def report():
    root = rebuild.ROOT
    manifest = json.loads((root / rebuild.DATA / 'manifest.json').read_text())
    return rebuild.load_report((root / rebuild.DATA / 'closed-report.json.gz').read_bytes(), manifest)


def test_actual_archive_is_the_exact_complete_source_bound_report(report):
    assert len(report['all_candidate_rows']) == 120 and len(report['evaluation']) == 90
    assert report['source_commit'] == 'b6654adefc42223f9ecc7b4e53c043c879230f68'
    assert report['content_sha256'] == '75f64370d673699553f69c480c93b90c07c2babba70b4f924cbc54438ab9d732'


@pytest.mark.parametrize('field', ['archive_sha256', 'uncompressed_sha256', 'report_content_sha256',
    'audit_content_sha256', 'experiment_source_commit', 'classification', 'uncompressed_bytes'])
def test_archive_or_binding_tampering_is_rejected_before_render(field):
    root = rebuild.ROOT
    manifest = json.loads((root / rebuild.DATA / 'manifest.json').read_text())
    manifest[field] = 1 if field == 'uncompressed_bytes' else 'changed'
    with pytest.raises(ValueError):
        rebuild.load_report((root / rebuild.DATA / 'closed-report.json.gz').read_bytes(), manifest)


def test_all_complete_raw_AQR_recompute_without_overwriting_original_scores(report):
    original = deepcopy(report)
    result = rebuild.measurement_arithmetic(report)
    assert result['measured_forwards'] == {'search': 64, 'evaluation': 90}
    assert result['loss_values_recomputed'] == 462
    assert result['maximum_absolute_roundoff'] <= 1e-13
    assert report == original and not result['audited_scores_replaced']
    bad = deepcopy(report); bad['evaluation'][0]['cross_scores']['selective'] += .01
    with pytest.raises(ValueError, match='loss algebra'):
        rebuild.measurement_arithmetic(bad)


def test_resources_retain_unknown_loads_and_nonfinal_proposal_replies():
    evidence = json.loads((rebuild.ROOT / rebuild.INPUTS[5]).read_text())
    rows = {r['stream']: r for r in rebuild.resource_arithmetic(evidence)['rows']}
    assert rows['scientists']['input_tokens'] == 15547758
    assert rows['designer-proposal']['completion_records'] == 1387
    assert rows['designer-proposal']['final_response_reported'] == 1385
    assert rows['role-load-designer']['input_tokens'] is None
    assert rows['role-load-scientist']['output_tokens'] is None
    evidence['scientist_costs']['usage']['total_tokens']['recorded_sum'] += 1
    with pytest.raises(ValueError, match='totals'):
        rebuild.resource_arithmetic(evidence)


def stage_inputs(tmp_path):
    root = tmp_path / 'repo'
    for name in rebuild.INPUTS:
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rebuild.ROOT / name, target)
    return root


def test_rebuild_validates_retained_selection_and_scores_before_render(tmp_path, monkeypatch):
    root = stage_inputs(tmp_path); out = tmp_path / 'rebuilt'; calls = []
    for name in ('plot_search', 'plot_cross_objective', 'plot_evaluation'):
        monkeypatch.setattr(rebuild, name, lambda *a, **kw: calls.append((a, kw)))
    result = rebuild.rebuild(root, out)
    assert len(calls) == 3
    assert calls[1][1] == {'paper': True}
    assert (out / 'search-outcomes.tex').read_bytes() == (root / rebuild.INPUTS[3]).read_bytes()
    assert result['table_and_cross_score_data_match_retained_manuscript']
    assert not result['raw_audit_or_fresh_inference_reproduced']
    assert result['new_model_calls'] == result['new_code_executions'] == 0
    with pytest.raises(ValueError, match='fresh'):
        rebuild.rebuild(root, out)


def test_manuscript_projection_tampering_does_not_create_output(tmp_path):
    root = stage_inputs(tmp_path); p = root / rebuild.INPUTS[2]
    body = json.loads(p.read_text()); body['rows'][0]['all_tied_row_ids'] = []
    p.write_text(json.dumps(body))
    out = tmp_path / 'rebuilt'
    with pytest.raises(ValueError, match='exact ties'):
        rebuild.rebuild(root, out)
    assert not out.exists()
