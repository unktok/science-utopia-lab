"""Scripted baseline executor; not actual original-input container evidence."""
from types import SimpleNamespace

from scripts import diagnose_native_resource_component_bank_v2 as diagnostic
from scripts.reports.stage_native_component_fixtures_v1 import stage,LIQUIDITY_SCOPE
from tests.reports.test_native_component_fixture_staging_v1 import inputs
from utopia.system.code_mechanisms import CodeExecution,sha


def setup(tmp_path,monkeypatch,fail_at=None):
    raw,audit=inputs(tmp_path,monkeypatch,liquidity=True);bank=tmp_path/'bank.json'
    stage(raw,audit,bank,scope=LIQUIDITY_SCOPE);value=diagnostic.read(bank);calls=[]
    lookup={(sha(r['artifact']),sha(r['context'])):r for r in value['records']}
    image=value['records'][0]['receipt']['image_id']
    class Executor:
        image_id=image;timeout=15.
        def execute(self,artifact,context):
            calls.append((sha(artifact),sha(context)))
            if len(calls)==fail_at:raise TypeError('SCRIPTED fixed baseline failure')
            r=lookup[calls[-1]];result=r['result']
            return CodeExecution(result,{'image_id':image,'artifact_sha256':sha(artifact),
                'context_sha256':sha(context),'result_sha256':sha(result)})
    monkeypatch.setattr(diagnostic,'DockerCodeExecutor',lambda **kw:Executor())
    monkeypatch.setattr(diagnostic,'pinned_revision',lambda root:'c'*40)
    return SimpleNamespace(bank=bank,audit=audit,output=tmp_path/'diagnostic'),calls


def test_exact_twelve_fixed_calls_and_fresh_cold_reader_do_not_dispatch_again(tmp_path,monkeypatch):
    args,calls=setup(tmp_path,monkeypatch);diagnostic.run(args)
    assert len(calls)==12
    assert diagnostic.replay(args.output)['status']=='closed' and len(calls)==12
    assert all(o['original_result_matches'] for o in diagnostic.read(args.output/'summary.json')['observations'])


def test_failed_baseline_stops_without_replacement_and_cold_reader_keeps_prefix(tmp_path,monkeypatch):
    args,calls=setup(tmp_path,monkeypatch,fail_at=3);diagnostic.run(args)
    summary=diagnostic.read(args.output/'summary.json')
    assert len(calls)==len(summary['observations'])==3 and summary['status']=='stopped'
    assert not summary['observations'][-1]['original_result_matches']
    assert diagnostic.replay(args.output)['calls']==3 and len(calls)==3
