"""One-shot stage wiring with fake subprocesses; never real experiment evidence."""
from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

from scripts import continue_native_instruction_timing_v1 as module
from utopia.optimization.native_numeric_designer import save, checked


def setup(tmp_path,monkeypatch,failure=None):
    previous=tmp_path/'previous-source';previous.mkdir()
    science=tmp_path/'assay-source';science.mkdir()
    analysis_source=tmp_path/'analysis-source';analysis_source.mkdir()
    raw=previous/'outputs/original';raw.mkdir(parents=True)
    prior=tmp_path/'previous-audits';prior.mkdir();(prior/'ended.json').write_text('{"SCRIPTED":"plain chain"}')
    save(raw/'plan.json',{'schema':'scienceutopia.native-objective-fixed-evaluation.v1.plan','source_commit':'a'*40})
    args=SimpleNamespace(preceding_run=raw,preceding_analysis=prior,preceding_source=previous,
        assay_source=science,assay_output=science/'outputs/assay',output=analysis_source/'outputs/continuation')
    monkeypatch.setattr(module,'ROOT',analysis_source)
    monkeypatch.setattr(module,'require_environment',lambda:None)
    changed=[]
    monkeypatch.setattr(module,'git_binding',lambda p:'f'*40 if changed else 'a'*40 if p==previous else 'b'*40)
    events=[];closed={'audit_file_sha256':'SCRIPTED audit hash','cost_file_sha256':'SCRIPTED cost hash'}
    def wait(path):
        events.append('wait-prior' if path==prior else 'wait-own-audits')
        if failure=='wait':raise ValueError('SCRIPTED previous chain stopped')
        return closed
    monkeypatch.setattr(module,'wait_analysis',wait)
    def execute(argv,**kwargs):
        if 'prepare' in argv:stage='prepare'
        elif 'run' in argv:stage='controls'
        elif 'scripts.finish_native_instruction_timing_v1' in argv:stage='cold-proof'
        else:stage=Path(argv[argv.index('--output')+1]).name
        events.append(stage)
        if failure==stage:return SimpleNamespace(returncode=1)
        if failure=='timeout' and stage=='controls':raise subprocess.TimeoutExpired('SCRIPTED',kwargs['timeout'])
        assert kwargs['env']['HF_HUB_OFFLINE']=='1' and kwargs['env']['PYTHONHASHSEED']=='42'
        if stage=='prepare':
            assert argv[argv.index('--preceding-source')+1]==str(previous)
            assert kwargs['cwd']==science
            args.assay_output.mkdir(parents=True);save(args.assay_output/'plan.json',{'SCRIPTED':'not an actual scientific plan'})
            if failure=='source-change':changed.append(True)
        elif stage=='controls':
            assert kwargs['timeout']==28800 and kwargs['cwd']==science
            save(args.assay_output/'started.json',{'pid':123})
        elif stage!='cold-proof':
            destination=Path(argv[argv.index('--output')+1]);destination.mkdir()
            save(destination/'report.json',{'SCRIPTED':stage.rsplit('-',1)[0]})
            if stage.startswith('effects'):
                assert argv[argv.index('--scope')+1]=='instruction-timing-controls'
                assert argv[argv.index('--frozen-source')+1]==str(science)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',execute)
    return args,events


def test_exact_gated_stages_and_double_exports_do_not_add_designer_or_reselection(tmp_path,monkeypatch):
    args,events=setup(tmp_path,monkeypatch);module.run(args)
    assert events==['wait-prior','prepare','controls','cold-proof','wait-own-audits',
        'choices-1','choices-2','effects-1','effects-2','requests-1','requests-2','wait-prior']
    end=checked(__import__('json').loads((args.output/'ended.json').read_text()))
    assert end['status']=='closed' and len(end['steps'])==9
    assert not end['policy_selection'] and not end['scientific_improvement_claimed']
    assert end['designer_POSTs']==0 and not end['publication_ready']
    with pytest.raises(ValueError,match='fresh separate'):module.run(args)


@pytest.mark.parametrize('failure',['wait','prepare','controls','cold-proof','choices-1','timeout','source-change'])
def test_failures_stop_at_the_actual_stage_without_retry_or_world_refill(tmp_path,monkeypatch,failure):
    args,events=setup(tmp_path,monkeypatch,failure)
    with pytest.raises((ValueError,subprocess.TimeoutExpired)):module.run(args)
    end=checked(__import__('json').loads((args.output/'ended.json').read_text()))
    assert end['status']=='stopped' and not end['science_restarted'] and not end['unknown_completions_refilled']
    assert events.count('prepare')<2 and events.count('controls')<2
    if failure=='wait':assert events==['wait-prior'] and not args.assay_output.exists()
    if failure=='prepare' or failure=='source-change':assert 'controls' not in events
    if failure in ('controls','timeout'):assert 'cold-proof' not in events
    if failure=='cold-proof':assert 'choices-1' not in events
    if failure=='choices-1':assert 'choices-2' not in events
