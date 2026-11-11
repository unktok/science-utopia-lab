"""Scripted closure-chain stages; no LLM or original-source audit claim."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_fixed_candidate_evaluation_v1 as finish


def setup(tmp_path,monkeypatch):
    root=tmp_path/'raw';root.mkdir();frozen=tmp_path/'source';frozen.mkdir()
    (root/'plan.json').write_text(json.dumps({'schema':'scienceutopia.native-fixed-candidate-evaluation.v1.plan',
        'source_commit':'a'*40,'content_sha256':'b'*64}))
    (root/'started.json').write_text(json.dumps({'pid':123,'plan_sha256':'b'*64}))
    monkeypatch.setattr(finish,'git_binding',lambda root:'a'*40)
    monkeypatch.setattr(finish,'process_identity',lambda pid:'SCRIPTED scripts.run_native_fixed_candidate_evaluation_v1 run')
    monkeypatch.setattr(finish,'wait_closed',lambda *a:{'SCRIPTED':'writer absent'})
    return SimpleNamespace(run=root,frozen_source=frozen,output=tmp_path/'analysis',writer_pid=123)


@pytest.mark.parametrize('failure',[None,'audit-1','costs-1'])
def test_only_fixed_readonly_stages_run_once_and_failure_stops_next(tmp_path,monkeypatch,failure):
    args=setup(tmp_path,monkeypatch);calls=[]
    def execute(command,**kwargs):
        name=Path(command[-1]).stem;calls.append(name)
        if failure==name:return SimpleNamespace(returncode=1)
        Path(command[-1]).write_text('SAME AUDIT' if name.startswith('audit') else 'SAME COST')
        assert command[2] in ('scripts.audit_native_fixed_candidate_evaluation_v1','scripts.reports.pre_scale_costs_v1')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(finish.subprocess,'run',execute)
    if failure:
        with pytest.raises(ValueError,match='no retry'):finish.run(args)
    else:finish.run(args)
    end=json.loads((args.output/'ended.json').read_text())
    assert end['status']==('stopped' if failure else 'closed')
    assert calls==(['audit-1'] if failure=='audit-1' else ['audit-1','audit-2','costs-1']
        if failure=='costs-1' else ['audit-1','audit-2','costs-1','costs-2'])
    if not failure:assert not end['publication_ready'] and end['new_model_calls']==0
    with pytest.raises(ValueError,match='fresh analysis'):finish.run(args)


def test_stopped_scientific_writer_is_not_restarted_or_followed_by_audit(tmp_path,monkeypatch):
    args=setup(tmp_path,monkeypatch)
    def stopped(*args):raise ValueError('SCRIPTED science stopped')
    monkeypatch.setattr(finish,'wait_closed',stopped)
    monkeypatch.setattr(finish.subprocess,'run',lambda *a,**k:pytest.fail('no next stage'))
    with pytest.raises(ValueError,match='science stopped'):finish.run(args)
    assert json.loads((args.output/'ended.json').read_text())['stage']=='await-scientific-closure'


def test_pid_or_source_mismatch_stops_before_creating_analysis_output(tmp_path,monkeypatch):
    args=setup(tmp_path,monkeypatch);args.writer_pid=124
    with pytest.raises(ValueError,match='source/plan/writer'):finish.run(args)
    assert not args.output.exists()
