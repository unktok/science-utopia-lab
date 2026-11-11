import json
from pathlib import Path

import pytest

from scripts.reports.native_objective_support_v1 import summarize
from utopia.system.design_patch import digest


def test_actual_retained_screen_reconstructs_exactly_without_native_raw_or_model_calls():
    root=Path(__file__).resolve().parents[2]
    actual=summarize((root/'research/data/pre-scale-search-v1/report.json').read_bytes())
    expected=json.loads((root/'research/results/native-objective-support-screen-v1.json').read_text())
    assert actual==expected
    assert actual['final_active_authors_distribution']=={'5':44}
    assert actual['excluded_noncomplete_worlds']==5 and actual['scope']['new_loss_selected'] is False


@pytest.mark.parametrize('kind',['unavailable','missing-measurement','wrong-schema'])
def test_unavailable_complete_stock_or_wrong_report_is_not_zero_imputed(kind):
    a={'schema':'scienceutopia.pre-scale-search-report.v1','worlds':[{'status':'complete','measurement':{
        'metrics':{'native.final_active_authors':{'status':'unavailable','value':None}}}}]}
    if kind=='wrong-schema':a['schema']='different'
    if kind=='missing-measurement':a['worlds'][0]['measurement']=None
    a['content_sha256']=digest(a)
    with pytest.raises(ValueError):summarize(json.dumps(a).encode())
