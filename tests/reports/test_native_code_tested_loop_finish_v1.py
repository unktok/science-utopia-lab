import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_code_tested_loop_v1 as module


def fixture(tmp_path,monkeypatch,*,variant='legacy'):
    science=tmp_path/'science';science.mkdir();root=science/'outputs';root.mkdir()
    workflow=variant=='workflow'
    p={'schema':'scienceutopia.native-workflow-objective-loop.v1.plan' if workflow else
        'scienceutopia.native-code-tested-loop.v1.plan','source_commit':'a'*40,'content_sha256':'b'*64}
    (root/'plan.json').write_text(json.dumps(p))
    (root/'started.json').write_text(json.dumps({'pid':123,'plan_sha256':'b'*64}))
    monkeypatch.setattr(module,'git_binding',lambda directory:'a'*40 if directory==science else 'c'*40)
    monkeypatch.setattr(module,'process_identity',lambda pid:'SCRIPTED scripts.run_native_workflow_objective_loop_v1 run'
        if workflow else 'SCRIPTED scripts.run_native_code_tested_loop_v1 run')
    return SimpleNamespace(run=root,frozen_source=science,output=tmp_path/'analysis',writer_pid=123)


@pytest.mark.parametrize('fail', [None,'closure','audit-1','costs-1'])
@pytest.mark.parametrize('variant', ['legacy','workflow'])
def test_chain_is_read_only_finite_and_never_retries_failed_stage(tmp_path,monkeypatch,fail,variant):
    a=fixture(tmp_path,monkeypatch,variant=variant);calls=[]
    if variant=='workflow':
        from scripts.finish_native_workflow_objective_loop_v1 import run
    else:run=module.run
    def wait(*args):
        if fail=='closure':raise ValueError('SCRIPTED stopped science')
        return {'SCRIPTED':'writer absent and normally closed'}
    monkeypatch.setattr(module,'wait_closed',wait)
    def execute(argv,**kwargs):
        output=Path(argv[argv.index('--output')+1]);calls.append(output.stem)
        assert argv[2]==('scripts.reports.pre_scale_costs_v1' if output.stem.startswith('costs') else
            'scripts.audit_native_workflow_objective_loop_v1' if variant=='workflow' else
            'scripts.audit_native_code_tested_loop_v1')
        assert (a.output/(output.stem+'.started.json')).exists()
        if fail==output.stem:return SimpleNamespace(returncode=2)
        output.write_text('{"SCRIPTED":"matching independent outputs"}')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',execute)
    if fail:
        with pytest.raises(ValueError):run(a)
    else:run(a)
    assert calls==({'closure':[],'audit-1':['audit-1'],'costs-1':['audit-1','audit-2','costs-1']}.get(fail)
                  if fail else ['audit-1','audit-2','costs-1','costs-2'])
    terminal=json.loads((a.output/'ended.json').read_text())
    assert terminal['status']==('stopped' if fail else 'closed')
    if not fail:assert terminal['new_model_calls']==0 and not terminal['publication_ready']
    with pytest.raises(ValueError):run(a)


def test_reused_writer_pid_is_not_treated_as_the_scientific_job(tmp_path,monkeypatch):
    a=fixture(tmp_path,monkeypatch);monkeypatch.setattr(module,'process_identity',lambda pid:'different-process')
    with pytest.raises(ValueError,match='different task'):module.run(a)
    assert not a.output.exists()
