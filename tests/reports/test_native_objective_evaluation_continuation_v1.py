"""Mocked process boundaries, never an automatic real scientific dispatch."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import continue_native_objective_evaluation_v1 as module
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('fail',[None,'closure','prepare','evaluation','cold-proof','source-change'])
def test_fixed_continuation_exact_stage_order_or_stop_without_retry(tmp_path,monkeypatch,fail):
    raw=tmp_path/'original';raw.mkdir();analysis=tmp_path/'original-analysis';analysis.mkdir()
    save(raw/'plan.json',{'schema':'scienceutopia.native-objective-instrument-loop.v1.plan','source_commit':'a'*40})
    save(analysis/'started.json',{'schema':'scienceutopia.native-objective-instrument-loop-finish.v1',
        'scientific_source_commit':'a'*40,'plan_file_sha256':module.sha(raw/'plan.json')})
    (analysis/'ended.json').write_text('SCRIPTED analysis terminal')
    original_source=tmp_path/'old-source';frozen=tmp_path/'evaluation-source';frozen.mkdir();calls=[]
    def binding(path):
        if Path(path)==original_source:return 'a'*40
        if fail=='source-change' and calls:return 'c'*40
        return 'b'*40
    monkeypatch.setattr(module,'git_binding',binding);monkeypatch.setattr(module,'require_environment',lambda:None)
    def wait(path):
        if fail=='closure':raise ValueError('SCRIPTED stopped development audit')
        return {'audit_file_sha256':'d'*64,'cost_file_sha256':'e'*64}
    monkeypatch.setattr(module,'wait_analysis',wait)
    evaluation=frozen/'outputs/evaluation'
    def execute(argv,**kwargs):
        label='prepare' if 'prepare' in argv else 'evaluation' if 'run' in argv else 'cold-proof';calls.append(label)
        assert kwargs['timeout'] in (1800,86400,9000)
        if label=='prepare':evaluation.mkdir(parents=True);save(evaluation/'plan.json',{'SCRIPTED':'mocked plan'})
        if label=='evaluation':save(evaluation/'started.json',{'pid':123456})
        return SimpleNamespace(returncode=2 if fail==label else 0)
    monkeypatch.setattr(module.subprocess,'run',execute)
    args=SimpleNamespace(origin_run=raw,origin_source=original_source,origin_analysis=analysis,
        evaluation_source=frozen,evaluation_output=evaluation,output=tmp_path/'chain',seed_usage_root=[tmp_path/'seed-root'])
    if fail:
        with pytest.raises(ValueError):module.run(args)
    else:module.run(args)
    assert calls==([] if fail=='closure' else ['prepare'] if fail in ('prepare','source-change') else
        ['prepare','evaluation'] if fail=='evaluation' else ['prepare','evaluation','cold-proof'])
    end=json.loads((args.output/'ended.json').read_text());assert end['status']==('stopped' if fail else 'closed')
    if not fail:assert not end['candidate_reselection'] and not end['publication_ready']
    with pytest.raises(ValueError):module.run(args)
