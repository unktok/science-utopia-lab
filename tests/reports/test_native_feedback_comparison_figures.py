"""Render explicitly SCRIPTED cost fixtures, never claim native evidence."""
import json

import pytest

from scripts.analyze_native_feedback_comparison import summarize
from scripts.figures.native_feedback_comparison import render
from tests.reports.test_native_feedback_comparison_analysis import fixtures
from utopia.system.design_patch import digest


def test_render_nulls_and_ties_without_modifying_input_or_overwriting(tmp_path):
    p,runs,baseline=fixtures()
    row=runs['throughput-loss']['observations'][0]
    row.update(status='technical-failure',loss=None,cross_scores={loss['id']:None for loss in p['losses'].values()})
    value=summarize(p,runs,baseline)
    source=tmp_path/'SCRIPTED-summary.json'; source.write_text(json.dumps(value))
    before=source.read_bytes()
    result=render(source,tmp_path/'SCRIPTED-figures')
    assert source.read_bytes()==before
    assert set(result['files'])=={'feedback-comparison.png','feedback-comparison.svg'}
    assert result['nulls_imputed'] is False and result['independent_objective_color_scales']
    assert result['new_model_calls']==result['new_worlds']==0
    svg=(tmp_path/'SCRIPTED-figures/feedback-comparison.svg').read_text()
    assert 'G0: null' in svg and 'Shared baseline' in svg
    with pytest.raises(ValueError,match='fresh'):
        render(source,tmp_path/'SCRIPTED-figures')
    value['arms']['throughput-loss']['best_so_far']=[-999.,-999.]
    source.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='content identity'):
        render(source,tmp_path/'not-created')
    assert not (tmp_path/'not-created').exists()


def test_all_null_curves_render_as_missing_not_zero(tmp_path):
    p,runs,baseline=fixtures()
    for arm in runs.values():
        for row in arm['observations']:
            row.update(status='generation-failure',loss=None,
                cross_scores={loss['id']:None for loss in p['losses'].values()})
    baseline.update(cross_scores={'throughput':None,'efficiency':None},row={
        'row_id':'shared-baseline','status':'technical-failure','cross_scores':{'throughput':None,'efficiency':None}})
    value=summarize(p,runs,baseline)
    source=tmp_path/'SCRIPTED-null-summary.json';source.write_text(json.dumps(value))
    assert render(source,tmp_path/'SCRIPTED-null-figures')['nulls_imputed'] is False
