"""Scripted closed resource proof, no claims about real four-world outcomes."""
import json
from types import SimpleNamespace

import pytest

from scripts.reports.native_liquidity_support_v1 import summarize,export
from scripts import audit_native_liquidity_support_v1 as auditor
from scripts.run_native_liquidity_support_v1 import read
from tests.reports.test_native_liquidity_audit_v1 import fixture
from scripts.run_native_liquidity_support_v1 import save
from scripts.analyze_native_open_v7 import _inventory
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


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


def test_actual_cold_export_reads_sealed_audit_retains_payload_contrasts_and_matches_twice(tmp_path,monkeypatch):
    root=tmp_path/'raw';p,_=fixture(root,monkeypatch);save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    for job in p['jobs']:
        identity=job['identity'];cell=root/'worlds-by-job'/identity/'worlds'/(identity+'-s61001')
        payloads=[{'SCRIPTED_initial_direction':i} for i in range(5)]+[{'SCRIPTED_after':job['condition']}]
        rows=[{'year':1,'payload':v,'payload_sha256':digest(v)} for v in payloads]
        (cell/'wire-requests.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    analysis=tmp_path/'analysis';analysis.mkdir()
    auditor.worker(root,analysis/'audit-1.json');auditor.worker(root,analysis/'audit-2.json')
    for i in (1,2):save(analysis/f'costs-{i}.json',{'SCRIPTED':'cost projection'})
    (analysis/'ended.json').write_text(json.dumps({'status':'closed','audit_file_sha256':file_sha256(analysis/'audit-1.json'),
        'cost_file_sha256':file_sha256(analysis/'costs-1.json')}))
    before=_inventory(root);analysis_before=_inventory(analysis)
    for label in ('first','second'):export(SimpleNamespace(run=root,analysis=analysis,output=tmp_path/label))
    assert before==_inventory(root) and analysis_before==_inventory(analysis)
    first=tmp_path/'first';second=tmp_path/'second'
    assert {p.name:p.read_bytes() for p in first.iterdir()}=={p.name:p.read_bytes() for p in second.iterdir()}
    report=read(first/'report.json')
    assert all(r['initial_five_full_payloads_equal'] and r['equal_full_payload_prefix_count']==5
        and not r['entire_payload_sequences_equal'] for r in report['request_contrasts'])
