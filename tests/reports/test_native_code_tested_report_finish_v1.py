"""Finite read-only continuation; scripted process boundary, no real inference."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_code_tested_report_v1 as module
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('fail',[None,'closure','report-1','report-2','different-bytes'])
@pytest.mark.parametrize('variant',['legacy','objective','fixed-objective'])
def test_exact_analysis_chain_two_exports_or_stop_without_retry(tmp_path,monkeypatch,fail,variant):
    objective=variant=='objective'
    fixed=variant=='fixed-objective'
    plan_schema=('scienceutopia.native-objective-fixed-evaluation.v1.plan' if fixed else
        'scienceutopia.native-objective-instrument-loop.v1.plan' if objective else 'scienceutopia.native-code-tested-loop.v1.plan')
    preceding_schema=('scienceutopia.native-objective-fixed-evaluation-finish.v1' if fixed else
        'scienceutopia.native-objective-instrument-loop-finish.v1' if objective else 'scienceutopia.code-tested-loop-finish.v1')
    raw=tmp_path/'raw';raw.mkdir();analysis=tmp_path/'analysis';analysis.mkdir()
    save(raw/'plan.json',{'schema':plan_schema,'source_commit':'a'*40})
    save(analysis/'started.json',{'schema':preceding_schema,
        'scientific_source_commit':'a'*40,'plan_file_sha256':module.sha(raw/'plan.json')})
    (analysis/'ended.json').write_text('SCRIPTED closed')
    monkeypatch.setattr(module,'git_binding',lambda root:'b'*40)
    calls=[]
    def wait(directory):
        if fail=='closure':raise ValueError('SCRIPTED stopped audit')
        return {'audit_file_sha256':'c'*64,'cost_file_sha256':'d'*64}
    monkeypatch.setattr(module,'wait_analysis',wait)
    def execute(argv,**kwargs):
        assert argv[2]==('scripts.reports.native_objective_fixed_evaluation_v1' if fixed else
            'scripts.reports.native_objective_instrument_loop_v1' if objective else 'scripts.reports.native_code_tested_loop_v1')
        d=Path(argv[argv.index('--output')+1]);calls.append(d.name)
        assert (d.parent/(d.name+'.started.json')).exists()
        if fail==d.name:return SimpleNamespace(returncode=2)
        d.mkdir();(d/'SCRIPTED.json').write_text(d.name if fail=='different-bytes' else 'matching')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',execute)
    args=SimpleNamespace(run=raw,analysis=analysis,output=tmp_path/'out')
    if fixed:
        from scripts.finish_native_objective_fixed_report_v1 import run
    elif objective:
        from scripts.finish_native_objective_instrument_report_v1 import run
    else:run=module.run
    if fail:
        with pytest.raises(ValueError):run(args)
    else:run(args)
    assert calls==([] if fail=='closure' else ['report-1'] if fail=='report-1' else ['report-1','report-2'])
    end=json.loads((args.output/'ended.json').read_text())
    assert end['status']==('stopped' if fail else 'closed')
    if not fail:assert not end['publication_ready'] and not end['visual_review_complete'] and end['new_model_calls']==0
    with pytest.raises(ValueError):run(args)
