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


def test_read_only_audit_accounts_all_controls_and_rejects_cross_score_tamper(tmp_path,monkeypatch):
    # Explicitly scripted physical proof primitives: test the new orchestration
    # and exact raw comparisons, not the already-tested real domain auditor.
    from scripts import analyze_native_benchmark_controls as audit
    from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
    p=plan();root=tmp_path/'raw';root.mkdir()
    def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
    save(root/'plan.json',p)
    start={'schema':driver.SCHEMA+'.writer','source_commit':'a'*40,'action':'run',
        'status':'started','started_utc':'2026-11-07T00:00:00+00:00'}
    save(root/'writer.started.json',start)
    save(root/'writer.ended.json',{**start,'status':'exited','exit_code':0,'ended_utc':'2026-11-07T00:00:01+00:00'})
    rows=[]
    for index,name in enumerate(p['order']):
        directory=root/'controls'/name
        suggestion={'candidate':p['systems'][name],'suggestion_id':'control-'+name}
        from utopia.system import SystemSpec
        fingerprint=SystemSpec.from_dict(suggestion['candidate']).fingerprint
        metrics={term['metric_id']:{'status':'measured','value':0} for loss in p['losses'].values()
            for term in loss['per_run']['terms']}
        measurement=[{'run_id':'control-'+name+'-s42','system_fingerprint':fingerprint,'metrics':metrics}]
        scores={k:evaluate_loss(v,measurement) for k,v in p['losses'].items()}
        o={**suggestion,'observation_id':'observation-control-'+name,'status':'complete',
            'loss':scores['throughput']['loss'],'metadata':{'world_backend':'native-research-world',
            'system_fingerprint':fingerprint,'measurements':measurement,'runs':[{'SCRIPTED':True}],
            'technical_failures':[],'loss_evaluation':scores['throughput'],
            'loss_spec_sha256':loss_spec_sha256(p['losses']['throughput'])}}
        save(directory/'started.json',{'slot':index,'name':name,'candidate_sha256':digest(suggestion['candidate'])})
        save(directory/'observation.json',o);save(directory/'cross-scores.json',scores)
        for file in ['role-load-000.started.json','role-load-000.json','loaded-role-context-000.json']:
            save(directory/'worlds'/('control-'+name+'-s42')/file,{'SCRIPTED':True})
        rows.append({'name':name,'slot':index,'status':'complete','cross_scores':{k:v['loss'] for k,v in scores.items()}})
    progress={'schema':driver.SCHEMA+'.progress','plan_sha256':p['content_sha256'],
        'rows':rows,'consumed_slots':8,'terminal':True};progress['content_sha256']=digest(progress)
    save(root/'progress.json',progress)
    monkeypatch.setattr(audit,'source_proofs',lambda *a,**kw:{'SCRIPTED':True})
    monkeypatch.setattr(audit,'replay_load',lambda *a,**kw:{'empty_prompt_load_confirmed':True})
    monkeypatch.setattr(audit,'replay_loaded_context',lambda *a,**kw:True)
    monkeypatch.setattr(audit,'audit_native_run_v14',lambda directory,draw,o,*a,**kw:{'measurement':o['metadata']['measurements'][0]})
    before=audit._inventory(root)
    result=audit.analyze(root,'a'*40)
    assert len(result['rows'])==len(result['proofs'])==8 and audit._inventory(root)==before
    assert result['best']['throughput']['all_tied_names']==p['order']
    loc=root/'controls'/'legacy'/'cross-scores.json';data=json.loads(loc.read_text());data['throughput']['loss']=-999.
    save(loc,data)
    with pytest.raises(ValueError,match='score differs'):audit.analyze(root,'a'*40)
