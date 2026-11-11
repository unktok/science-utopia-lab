"""New resource binding through the actual shared finite finish engine."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_liquidity_support_v1 as module
from scripts import finish_native_code_tested_loop_v1 as engine
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('failure',[None,'closure','audit-1','costs-1'])
@pytest.mark.parametrize('study',['liquidity-support','objective-instrument-loop'])
def test_resource_schema_uses_actual_existing_engine_without_retry_or_scientific_restart(tmp_path,monkeypatch,failure,study):
    from scripts import finish_native_objective_instrument_loop_v1 as instrument
    target=module if study=='liquidity-support' else instrument
    name=study.replace('-','_')
    science=tmp_path/'science';science.mkdir();raw=science/'raw';raw.mkdir()
    p=save(raw/'plan.json',{'schema':'scienceutopia.native-'+study+'.v1.plan','source_commit':'a'*40})
    save(raw/'started.json',{'pid':123,'plan_sha256':p['content_sha256']})
    monkeypatch.setattr(engine,'git_binding',lambda path:'a'*40 if path==science else 'b'*40)
    monkeypatch.setattr(engine,'process_identity',lambda pid:'SCRIPTED scripts.run_native_'+name+'_v1 run')
    def wait(*args):
        if failure=='closure':raise ValueError('SCRIPTED science stopped')
        return {'status':'closed'}
    monkeypatch.setattr(engine,'wait_closed',wait);calls=[]
    def execute(argv,**kwargs):
        path=Path(argv[argv.index('--output')+1]);calls.append(path.stem)
        if path.stem.startswith('audit'):assert argv[argv.index('-m')+1]=='scripts.audit_native_'+name+'_v1'
        if failure==path.stem:return SimpleNamespace(returncode=2)
        path.write_text('SCRIPTED matching outputs');return SimpleNamespace(returncode=0)
    monkeypatch.setattr(engine.subprocess,'run',execute)
    args=SimpleNamespace(run=raw,frozen_source=science,output=tmp_path/'analysis',writer_pid=123)
    if failure:
        with pytest.raises(ValueError):target.run(args)
    else:target.run(args)
    assert calls=={'closure':[],'audit-1':['audit-1'],'costs-1':['audit-1','audit-2','costs-1']}.get(failure,['audit-1','audit-2','costs-1','costs-2'])
    started=json.loads((args.output/'started.json').read_text())
    assert started['schema']=='scienceutopia.native-'+study+'-finish.v1'
    ended=json.loads((args.output/'ended.json').read_text())
    assert ended['status']==('stopped' if failure else 'closed')
    with pytest.raises(ValueError):target.run(args)
