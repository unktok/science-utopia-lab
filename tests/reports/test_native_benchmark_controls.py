"""Finite control-driver and evidence QA; no live scholar inference."""
from copy import deepcopy
import json
import pytest
from scripts import run_native_benchmark_controls as driver
from tests.optimization.test_native_designer_roles_v38 import BINDING,designer_binding
from utopia.system.design_patch import digest


def plan():
    return driver.build_plan(source='a'*40,scientist=BINDING,designer=designer_binding(),
        runtime_seed={'python_hash_seed_environment':'42','python_hash_probe':123})


def test_common_forward_world_explicit_no_designer_budget_and_fixed_tradeoff():
    p=plan()
    assert p['maximum_worlds']==len(p['order'])==8 and p['designer_calls']==0
    assert p['seed']==42 and p['years']==2 and p['refill'] is False
    assert p['content_sha256']==digest({k:v for k,v in p.items() if k!='content_sha256'})
    assert set(p['losses'])=={'throughput','efficiency','selective'}
    assert 'loss' not in p['experiment'] and 'arm' not in p['experiment']


def test_runtime_failures_consume_every_slot_no_refill_and_no_fake_scores(tmp_path):
    p=plan();calls=[]
    def make_factory(root):
        def fail(spec,seed,run_id):
            calls.append((spec.fingerprint,seed,run_id));raise RuntimeError('SCRIPTED native failure')
        return fail
    assert driver.run_slots(tmp_path,p,make_factory)==0
    assert len(calls)==8
    progress=json.loads((tmp_path/'progress.json').read_text())
    assert progress['terminal'] and progress['consumed_slots']==8
    assert all(r['status']=='failed' and set(r['cross_scores'].values())=={None} for r in progress['rows'])
    with pytest.raises(ValueError,match='immutable'):driver.run_slots(tmp_path,p,make_factory)
    assert len(calls)==8


def test_writer_will_not_redispatch_aborted_or_completed_action(tmp_path,monkeypatch):
    monkeypatch.setattr(driver,'pinned_revision',lambda root:'a'*40)
    calls=[];monkeypatch.setattr(driver,'execute',lambda args:calls.append(args.action) or 0)
    argv=['run','--execute-authorized','--output',str(tmp_path),'--data-cache',str(tmp_path/'cache'),
        '--designer-provider-config',str(tmp_path/'config')]
    assert driver.main(argv)==0
    with pytest.raises(ValueError,match='immutable'):driver.main(argv)
    assert calls==['run']


def test_audit_cli_rejects_output_overwrite_or_raw_mutation_before_analysis(tmp_path,monkeypatch):
    from scripts import analyze_native_benchmark_controls as audit
    monkeypatch.setattr(audit,'analyze',lambda *a:pytest.fail('must not analyze'))
    existing=tmp_path/'existing.json';existing.write_text('original')
    for output in [existing,tmp_path/'raw'/'audit.json']:
        with pytest.raises(SystemExit):audit.main(['--run',str(tmp_path/'raw'),
            '--expected-source','a'*40,'--output',str(output)])
    assert existing.read_text()=='original'
