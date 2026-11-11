"""Diagnostic input selection only; not a real container or native failure."""
from copy import deepcopy
import json

import pytest

from scripts.diagnose_native_component_lab_v1 import inputs,CASES
from tests.optimization.test_native_code_trace import case
from utopia.system.design_patch import digest


def data(tmp_path):
    r,a,c,b=case(tmp_path);r.execute(a,c);row=json.loads(r.path.read_text())
    worlds=[]
    for label,identity in CASES[1:]:
        bad={**a,'source':"def step(context):\n raise TypeError('SCRIPTED bad artifact')"}
        worlds.append({'identity':identity,'status':'failed','system':{'mechanisms':[
            {'mechanism_id':'world.selection','parameters':{'code_artifact':bad}}]}})
    audit={'schema':'scienceutopia.native-institution-loop-stopped-audit.v1','worlds':worlds}
    audit['content_sha256']=digest(audit)
    bank={'schema':'scienceutopia.native-component-fixtures.v1',
        'historical_audit_content_sha256':audit['content_sha256'],'records':[row],
        'origins':[{'reference':'open-seed','node_id':'world.selection','year':1,'seed':61001,
            'bundle_sha256':row['bundle_sha256']}]}
    bank['content_sha256']=digest(bank)
    return bank,audit


def test_only_predeclared_retained_code_and_single_developer_input_are_selected(tmp_path):
    bank,audit=data(tmp_path);key,cases,row=inputs(bank,audit)
    assert key=='fixture-'+row['bundle_sha256']
    assert [c['label'] for c in cases]==[c[0] for c in CASES]
    assert cases[0]['artifact']==row['artifact']
    assert cases[1]['artifact']==audit['worlds'][0]['system']['mechanisms'][0]['parameters']['code_artifact']


def test_missing_old_failure_is_not_replaced_by_another_code_candidate(tmp_path):
    bank,audit=data(tmp_path);audit['worlds'].pop()
    audit.pop('content_sha256');audit['content_sha256']=digest(audit)
    bank['historical_audit_content_sha256']=audit['content_sha256']
    bank.pop('content_sha256');bank['content_sha256']=digest(bank)
    with pytest.raises(ValueError,match='exact retained failed'):inputs(bank,audit)


def test_wrong_or_ambiguous_fixture_does_not_trigger_a_search_for_an_alternative(tmp_path):
    bank,audit=data(tmp_path);bank['origins'].append(deepcopy(bank['origins'][0]))
    bank.pop('content_sha256');bank['content_sha256']=digest(bank)
    with pytest.raises(ValueError,match='one predeclared'):inputs(bank,audit)
