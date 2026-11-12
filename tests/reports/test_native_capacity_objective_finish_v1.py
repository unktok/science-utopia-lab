import json
from pathlib import Path
from types import SimpleNamespace

from scripts import finish_native_capacity_objective_loop_v1 as module
from scripts import finish_native_code_tested_loop_v1 as core
from tests.reports.test_native_code_tested_loop_finish_v1 import fixture
from tests.reports.test_pre_scale_costs import hashed


def test_exact_wrapper_runs_two_original_audits_and_two_costs_without_inference(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    p=json.loads((args.run/'plan.json').read_text());p['schema']='scienceutopia.native-capacity-objective-loop.v1.plan'
    (args.run/'plan.json').write_text(json.dumps(p))
    monkeypatch.setattr(core,'process_identity',lambda pid:'SCRIPTED scripts.run_native_capacity_objective_loop_v1 run')
    monkeypatch.setattr(core,'wait_closed',lambda *a:{'SCRIPTED':'normally closed'})
    calls=[]
    def execute(argv,**kwargs):
        calls.append(argv);output=Path(argv[argv.index('--output')+1]);output.write_text('{"SCRIPTED":"same output"}')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(core.subprocess,'run',execute);module.run(args)
    assert len(calls)==4 and all('scripts.audit_native_capacity_objective_loop_v1' in a for a in calls[:2])
    assert all('scripts.reports.pre_scale_costs_v1' in a for a in calls[2:])
    terminal=json.loads((args.output/'ended.json').read_text())
    assert terminal['status']=='closed' and terminal['new_model_calls']==0


def test_capacity_cost_projection_has_native_usage_and_no_implicit_critic_scope(tmp_path):
    from tests.reports.test_native_token_costs import cache
    from scripts.reports.pre_scale_costs_v1 import analyze
    from scripts.analyze_native_open_v7 import _inventory
    from utopia.optimization.native_numeric_designer import save
    from utopia.system.design_patch import digest
    p=hashed({'source_commit':'a'*40,'scientist':{'model':'SCRIPTED','model_digest':'b'*64,'corpus_sha256':'c'*64},
        'designer':{'model':'SCRIPTED-designer'}})
    cache(tmp_path,p,'references/test/worlds/test/replies/responses.sqlite',[
        {'prompt_tokens':3,'completion_tokens':4,'total_tokens':7},None])
    start=save(tmp_path/'started.json',{'plan_sha256':p['content_sha256']})
    end=save(tmp_path/'terminal.json',{'status':'closed'});inventory=_inventory(tmp_path)
    audit=hashed({'schema':'scienceutopia.native-capacity-objective-loop-audit.v1','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'source_proof':{'status':'verified-exact-source-closure'},
        'new_model_calls':0,'new_code_executions':0,'closure':{'started':start,'terminal':end},
        'raw_inventory_sha256':digest(inventory),'raw_files':len(inventory)})
    result=analyze(tmp_path,p,audit)
    assert result['scientist']['completed_responses']==2
    assert result['scientist']['provider_usage']['prompt_tokens']['recorded_sum']==3
    assert result['scientist']['provider_usage']['prompt_tokens']['missing_responses']==1
    assert 'common_content_observer' not in result and _inventory(tmp_path)==inventory
