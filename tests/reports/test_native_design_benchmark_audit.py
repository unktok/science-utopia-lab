"""Observation audit orchestration QA; scripted physical primitive only."""
import json
from pathlib import Path
import pytest

from scripts import analyze_native_design_benchmark as audit
from tests.reports.test_native_design_benchmark_plan import plan
from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
from utopia.system import SystemSpec
from utopia.system.design_patch import digest


def test_observation_identity_loss_and_measurements_are_not_trusted_without_comparison(tmp_path,monkeypatch):
    p=plan();system=p['initial_system'];s=SystemSpec.from_dict(system);identity='SCRIPTED-reference'
    metrics={t['metric_id']:{'status':'measured','value':0} for loss in p['losses'].values() for t in loss['per_run']['terms']}
    measurement={'run_id':identity+'-s42','system_fingerprint':s.fingerprint,'metrics':metrics}
    scores={k:evaluate_loss(v,[measurement]) for k,v in p['losses'].items()}
    o={'candidate':system,'suggestion_id':identity,'observation_id':'observation-'+identity,'status':'complete',
        'loss':scores['throughput']['loss'],'metadata':{'world_backend':'native-research-world',
            'system_fingerprint':s.fingerprint,'loss_spec_sha256':loss_spec_sha256(p['losses']['throughput']),
            'loss_evaluation':scores['throughput'],'measurements':[measurement],
            'technical_failures':[],'runs':[{'SCRIPTED':True}]}}
    def save(name,value):(tmp_path/name).write_text(json.dumps(value))
    save('started.json',{'identity':identity,'seed':42,'years':2,'candidate_sha256':digest(system),'role':'SCRIPTED'})
    save('observation.json',o);save('cross-scores.json',scores)
    cell=tmp_path/'worlds'/(identity+'-s42');cell.mkdir(parents=True)
    monkeypatch.setattr(audit,'loaded',lambda *a,**kw:{'confirmed':True})
    monkeypatch.setattr(audit,'physical_proof',lambda *a,**kw:{'measurement':measurement})
    result=audit.observation_proof(tmp_path,p,identity=identity,system=system,seed=42,years=2,role='SCRIPTED')
    assert result['scores']==scores
    o['loss']=-999.;save('observation.json',o)
    with pytest.raises(ValueError,match='scores differ'):
        audit.observation_proof(tmp_path,p,identity=identity,system=system,seed=42,years=2,role='SCRIPTED')


def test_cli_cannot_overwrite_evidence_or_write_inside_raw_root(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'analyze',lambda *a:pytest.fail('must reject before reading evidence'))
    existing=tmp_path/'existing.json';existing.write_text('original')
    for output in [existing,tmp_path/'raw'/'audit.json']:
        with pytest.raises(SystemExit):audit.main(['--run',str(tmp_path/'raw'),
            '--expected-source','a'*40,'--output',str(output)])
    assert existing.read_text()=='original'
