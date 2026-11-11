"""Finite read-only continuation; scripted process boundary, no real inference."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_code_tested_report_v1 as module
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('fail',[None,'closure','report-1','report-2','different-bytes'])
def test_exact_analysis_chain_two_exports_or_stop_without_retry(tmp_path,monkeypatch,fail):
    raw=tmp_path/'raw';raw.mkdir();analysis=tmp_path/'analysis';analysis.mkdir()
    save(raw/'plan.json',{'schema':'scienceutopia.native-code-tested-loop.v1.plan','source_commit':'a'*40})
    save(analysis/'started.json',{'schema':'scienceutopia.code-tested-loop-finish.v1',
        'scientific_source_commit':'a'*40,'plan_file_sha256':module.sha(raw/'plan.json')})
    (analysis/'ended.json').write_text('SCRIPTED closed')
    monkeypatch.setattr(module,'git_binding',lambda root:'b'*40)
    calls=[]
    def wait(directory):
        if fail=='closure':raise ValueError('SCRIPTED stopped audit')
        return {'audit_file_sha256':'c'*64,'cost_file_sha256':'d'*64}
    monkeypatch.setattr(module,'wait_analysis',wait)
    def execute(argv,**kwargs):
        d=Path(argv[argv.index('--output')+1]);calls.append(d.name)
        assert (d.parent/(d.name+'.started.json')).exists()
        if fail==d.name:return SimpleNamespace(returncode=2)
        d.mkdir();(d/'SCRIPTED.json').write_text(d.name if fail=='different-bytes' else 'matching')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',execute)
    args=SimpleNamespace(run=raw,analysis=analysis,output=tmp_path/'out')
    if fail:
        with pytest.raises(ValueError):module.run(args)
    else:module.run(args)
    assert calls==([] if fail=='closure' else ['report-1'] if fail=='report-1' else ['report-1','report-2'])
    end=json.loads((args.output/'ended.json').read_text())
    assert end['status']==('stopped' if fail else 'closed')
    if not fail:assert not end['publication_ready'] and not end['visual_review_complete'] and end['new_model_calls']==0
    with pytest.raises(ValueError):module.run(args)
