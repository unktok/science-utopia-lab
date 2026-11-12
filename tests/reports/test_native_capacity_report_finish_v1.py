"""Real sealed wait/export journals; scripted subprocesses, no inference."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_code_tested_report_v1 as core
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('kind',['scores','effects','requests'])
@pytest.mark.parametrize('failure',[None,'closure','report-1','report-2','different-bytes'])
def test_exact_capacity_scopes_double_export_or_stop_without_retry(tmp_path,monkeypatch,kind,failure):
    raw=tmp_path/'raw';raw.mkdir();analysis=tmp_path/'analysis';analysis.mkdir()
    save(raw/'plan.json',{'schema':'scienceutopia.native-capacity-objective-loop.v1.plan','source_commit':'a'*40})
    save(analysis/'started.json',{'schema':'scienceutopia.native-capacity-objective-loop-finish.v1',
        'scientific_source_commit':'a'*40,'plan_file_sha256':core.sha(raw/'plan.json')})
    monkeypatch.setattr(core,'git_binding',lambda root:'b'*40)
    def wait(directory):
        if failure=='closure':raise ValueError('SCRIPTED stopped original chain')
        return {'audit_file_sha256':'c'*64,'cost_file_sha256':'d'*64}
    monkeypatch.setattr(core,'wait_analysis',wait);calls=[]
    modules={'scores':'scripts.reports.native_capacity_objective_loop_v1',
        'effects':'scripts.reports.native_institution_effect_trace_v1',
        'requests':'scripts.reports.native_observed_request_classes_v1'}
    def execute(argv,**kwargs):
        assert argv[2]==modules[kind] and kwargs['timeout']==1800
        if kind=='effects':
            assert argv[argv.index('--scope')+1]=='capacity-objective-development'
            assert argv[argv.index('--frozen-source')+1]==str((tmp_path/'source').resolve())
        output=Path(argv[argv.index('--output')+1]);calls.append(output.name)
        if failure==output.name:return SimpleNamespace(returncode=1)
        output.mkdir();save(output/'report.json',{'SCRIPTED':output.name if failure=='different-bytes' else 'identical'})
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(core.subprocess,'run',execute)
    args=SimpleNamespace(run=raw,analysis=analysis,output=tmp_path/'out',
        frozen_source=tmp_path/'source',scope='capacity-objective-development')
    if kind=='effects':from scripts.finish_native_institution_effect_trace_v1 import run
    elif kind=='requests':from scripts.finish_native_capacity_requests_v1 import run
    else:from scripts.finish_native_capacity_objective_report_v1 import run
    if failure:
        with pytest.raises(ValueError):run(args)
    else:run(args)
    assert calls==([] if failure=='closure' else ['report-1'] if failure=='report-1' else ['report-1','report-2'])
    end=json.loads((args.output/'ended.json').read_text())
    assert end['status']==('stopped' if failure else 'closed')
    if not failure:assert end['new_model_calls']==0 and not end['publication_ready']
    with pytest.raises(ValueError):run(args)
