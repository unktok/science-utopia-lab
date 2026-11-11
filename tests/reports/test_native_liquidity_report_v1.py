"""Scripted closed resource proof, no claims about real four-world outcomes."""
import pytest

from scripts.reports.native_liquidity_support_v1 import summarize
from scripts import audit_native_liquidity_support_v1 as auditor
from scripts.run_native_liquidity_support_v1 import read
from tests.reports.test_native_liquidity_audit_v1 import fixture


def inputs(tmp_path,monkeypatch):
    fixture(tmp_path/'raw',monkeypatch);auditor.worker(tmp_path/'raw',tmp_path/'audit.json')
    return read(tmp_path/'audit.json'),[{'initial_funding':amount,'SCRIPTED':True} for amount in (30,60)]


def test_retains_all_worlds_80_actor_boundaries_and_zero_differences(tmp_path,monkeypatch):
    audit,contrasts=inputs(tmp_path,monkeypatch);report=summarize(audit,contrasts)
    assert len(report['worlds'])==4 and len(report['actor_boundaries'])==80
    assert all(w['annual_active_founder_boundary_sum']==20 for w in report['worlds'])
    assert all(r['accepted_decisions']==0 for r in report['within_endowment_differences'])
    assert not report['interpretation']['policy_search'] and not report['interpretation']['publication_ready']


@pytest.mark.parametrize('damage',['duplicate','missing-year','bad-ledger','missing-critic-value'])
def test_incomplete_or_changed_actual_proofs_are_not_repaired(tmp_path,monkeypatch,damage):
    audit,contrasts=inputs(tmp_path,monkeypatch);w=audit['worlds'][0]
    if damage=='duplicate':audit['worlds'][1]=w
    if damage=='missing-year':w['annual_resources'].pop()
    if damage=='bad-ledger':w['annual_resources'][0]['ledger_reconciliation'][0]['residual']=1
    if damage=='missing-critic-value':w['physical_proof']['measurement']['metrics']['native.accepted_peer_score_sum']['status']='unavailable'
    with pytest.raises(ValueError):summarize(audit,contrasts)
