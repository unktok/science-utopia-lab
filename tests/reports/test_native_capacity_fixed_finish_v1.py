"""One-shot normal-closure/export continuations with scripted subprocesses only."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_code_tested_loop_v1 as cold_core
from scripts import finish_native_code_tested_report_v1 as report_core
from scripts import finish_native_capacity_fixed_evaluation_v1 as cold
from scripts import finish_native_capacity_fixed_report_v1 as reports
from tests.reports.test_native_code_tested_loop_finish_v1 import fixture
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('failure',[None,'closure','audit-1','costs-1','different-bytes'])
def test_exact_fixed_capacity_cold_chain_or_stop_no_retries(tmp_path,monkeypatch,failure):
    args=fixture(tmp_path,monkeypatch);p=json.loads((args.run/'plan.json').read_text())
    p['schema']='scienceutopia.native-capacity-fixed-evaluation.v1.plan';(args.run/'plan.json').write_text(json.dumps(p))
    monkeypatch.setattr(cold_core,'process_identity',lambda pid:'SCRIPTED scripts.run_native_capacity_fixed_evaluation_v1 run')
    def wait(*a):
        if failure=='closure':raise ValueError('SCRIPTED stopped native world')
        return {'SCRIPTED':'normally closed'}
    monkeypatch.setattr(cold_core,'wait_closed',wait);calls=[]
    def execute(argv,**kwargs):
        output=Path(argv[argv.index('--output')+1]);calls.append(output.stem)
        assert kwargs['timeout']==1800
        if output.stem==failure:return SimpleNamespace(returncode=2)
        output.write_text(json.dumps({'SCRIPTED':output.stem if failure=='different-bytes' else 'same'}))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(cold_core.subprocess,'run',execute)
    if failure:
        with pytest.raises(ValueError):cold.run(args)
    else:cold.run(args)
    expected=[] if failure=='closure' else ['audit-1'] if failure=='audit-1' else ['audit-1','audit-2'] if failure=='different-bytes' else ['audit-1','audit-2','costs-1'] if failure=='costs-1' else ['audit-1','audit-2','costs-1','costs-2']
    assert calls==expected
    end=json.loads((args.output/'ended.json').read_text());assert end['status']==('stopped' if failure else 'closed')
    with pytest.raises(ValueError):cold.run(args)


@pytest.mark.parametrize('failure',[None,'closure','report-1','report-2','different-bytes'])
def test_exact_fixed_capacity_score_exports_or_stop_no_retries(tmp_path,monkeypatch,failure):
    raw=tmp_path/'raw';raw.mkdir();analysis=tmp_path/'analysis';analysis.mkdir()
    save(raw/'plan.json',{'schema':'scienceutopia.native-capacity-fixed-evaluation.v1.plan','source_commit':'a'*40})
    save(analysis/'started.json',{'schema':'scienceutopia.native-capacity-fixed-evaluation-finish.v1',
        'scientific_source_commit':'a'*40,'plan_file_sha256':report_core.sha(raw/'plan.json')})
    (analysis/'ended.json').write_text('SCRIPTED matching closure')
    monkeypatch.setattr(report_core,'git_binding',lambda root:'b'*40)
    def wait(*a):
        if failure=='closure':raise ValueError('SCRIPTED no normal cold closure')
        return {'audit_file_sha256':'c'*64,'cost_file_sha256':'d'*64}
    monkeypatch.setattr(report_core,'wait_analysis',wait);calls=[]
    def execute(argv,**kwargs):
        assert argv[2]=='scripts.reports.native_capacity_fixed_evaluation_v1'
        output=Path(argv[argv.index('--output')+1]);calls.append(output.name)
        if output.name==failure:return SimpleNamespace(returncode=1)
        output.mkdir();save(output/'report.json',{'SCRIPTED':output.name if failure=='different-bytes' else 'same'})
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(report_core.subprocess,'run',execute)
    args=SimpleNamespace(run=raw,analysis=analysis,output=tmp_path/'out')
    if failure:
        with pytest.raises(ValueError):reports.run(args)
    else:reports.run(args)
    assert calls==([] if failure=='closure' else ['report-1'] if failure=='report-1' else ['report-1','report-2'])
    assert json.loads((args.output/'ended.json').read_text())['status']==('stopped' if failure else 'closed')
    with pytest.raises(ValueError):reports.run(args)
