"""Scripted closure waiting and exporter boundary, with no inference."""
import json
from types import SimpleNamespace

import pytest

from scripts import await_native_objective_fixed_report_v1 as module
from utopia.optimization.native_numeric_designer import save


def test_wait_is_finite_and_stopped_chain_does_not_become_closure(tmp_path):
    now=[0.]
    with pytest.raises(ValueError,match='exhausted'):
        module.wait_chain(tmp_path,clock=lambda:now[0],poll=lambda n:now.__setitem__(0,now[0]+n),seconds=20)
    save(tmp_path/'ended.json',{'status':'stopped'})
    with pytest.raises(ValueError,match='stopped'):module.wait_chain(tmp_path)


@pytest.mark.parametrize('fail',[None,'chain','export','source'])
@pytest.mark.parametrize('trace',[False,True])
def test_future_plan_is_only_read_after_bound_chain_closes(tmp_path,monkeypatch,fail,trace):
    chain=tmp_path/'chain';chain.mkdir();raw=tmp_path/'future-evaluation';frozen=tmp_path/'frozen'
    save(chain/'started.json',{'schema':'scienceutopia.native-objective-evaluation-continuation.v1',
        'source_commit':'a'*40,'evaluation_output':str(raw),'evaluation_source':str(frozen)})
    monkeypatch.setattr(module,'git_binding',lambda p:'a'*40)
    calls=[]
    def wait(path):
        assert not raw.exists()  # A future plan is not fabricated by watcher.
        if fail=='chain':raise ValueError('SCRIPTED stopped chain')
        raw.mkdir();save(raw/'plan.json',{'source_commit':'a'*40})
        end={'status':'closed','evaluation_plan_file_sha256':module.sha(raw/'plan.json')}
        save(chain/'ended.json',end);return json.loads((chain/'ended.json').read_text())
    monkeypatch.setattr(module,'wait_chain',wait)
    def finish(args):
        calls.append(args);assert args.analysis==chain/'audits'
        if trace:assert args.scope=='fixed-evaluation' and args.frozen_source==frozen
        if fail=='export':raise ValueError('SCRIPTED report failed')
        args.output.mkdir();save(args.output/'ended.json',{'status':'closed'})
        if fail=='source':monkeypatch.setattr(module,'git_binding',lambda p:'b'*40)
    monkeypatch.setattr(module,'finish',finish);args=SimpleNamespace(continuation=chain,output=tmp_path/'out')
    if trace:
        from scripts import await_native_institution_effect_trace_v1 as wrapper
        monkeypatch.setattr(wrapper,'finish_trace',finish);run=wrapper.run
    else:run=module.run
    if fail:
        with pytest.raises(ValueError):run(args)
    else:run(args)
    assert len(calls)==(0 if fail=='chain' else 1)
    end=json.loads((args.output/'ended.json').read_text());assert end['status']==('stopped' if fail else 'closed')
    if not fail:assert not end['visual_review_complete'] and not end['publication_ready']
    with pytest.raises(ValueError):run(args)
