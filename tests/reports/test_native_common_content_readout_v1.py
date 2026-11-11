"""Finite retrospective observation runner, fake model only."""
from collections import Counter
import json
from types import SimpleNamespace

import pytest

from scripts import run_native_common_content_readout_v1 as module
from utopia.optimization.common_content_observer import ObserverCompletionUnknown
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def inputs():
    rows=[{'physical_world':'SCRIPTED-world-'+str(i%44),'paper_id':'SCRIPTED-paper-'+str(i),
        'year':1,'decision_index':0,'content':{'title':'SCRIPTED title '+str(i%76),
            'abstract':'SCRIPTED abstract','topics':['SCRIPTED-topic']}} for i in range(263)]
    body={'scientific_source_commit':'62388a74d071a3a4fdc8cc309c2807422f96223f',
        'worlds':[{'identity':'SCRIPTED-world-'+str(i)} for i in range(44)],
        'skipped_partial_worlds':[{'SCRIPTED':i} for i in range(5)],'accepted_decisions':rows}
    return {**body,'content_sha256':digest(body)}


def test_content_order_is_exact_full_set_not_decision_order_or_policy_metadata():
    body=inputs();values=module.content_set(body)
    body['accepted_decisions'].reverse();body.pop('content_sha256');body['content_sha256']=digest(body)
    assert values==module.content_set(body) and list(values)==sorted(values) and len(values)==76
    assert all(set(row)=={'title','abstract','topics'} for row in values.values())


@pytest.mark.parametrize('failure',[None,'preceding','initial-known','later-known','unknown'])
def test_readout_has_finite_interface_check_no_refill_and_stops_unknown(tmp_path,monkeypatch,failure):
    body=inputs();save(tmp_path/'inputs.json',{k:v for k,v in body.items() if k!='content_sha256'})
    p={'content_sha256':'SCRIPTED-plan','preceding_report':str(tmp_path/'prior'),
        'inputs_path':str(tmp_path/'inputs.json'),'inference_lock':str(tmp_path/'inference.lock'),'contract':{}}
    monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    def wait(directory):
        if failure=='preceding':raise ValueError('SCRIPTED stopped preceding report')
        return {'status':'closed','content_sha256':'SCRIPTED closed'}
    monkeypatch.setattr(module,'wait_report',wait)
    monkeypatch.setattr(module,'LocalObserverBackend',lambda **kwargs:object())
    calls=[]
    class Observer:
        def __init__(self,*args,**kwargs):pass
        def rate(self,value):
            calls.append(digest(value))
            if failure=='unknown' and len(calls)==5:raise ObserverCompletionUnknown('SCRIPTED unknown POST')
            return {'status':'unavailable' if (failure=='initial-known' and len(calls)==2) or
                (failure=='later-known' and len(calls)==4) else 'measured','mean_score':3}
        def audit(self):
            value={'SCRIPTED':'cold audit'};return {**value,'content_sha256':digest(value)}
    monkeypatch.setattr(module,'CommonContentObserver',Observer)
    root=tmp_path/'run';root.mkdir()
    if failure in ('preceding','initial-known','unknown'):
        with pytest.raises((ValueError,ObserverCompletionUnknown)):module.run(root)
    else:module.run(root)
    assert len(calls)=={'preceding':0,'initial-known':2,'unknown':5}.get(failure,76)
    assert len(calls)==len(set(calls))
    end=module.read(root/'terminal.json')
    assert end['status']==('stopped' if failure in ('preceding','initial-known','unknown') else 'closed')
    if failure in ('preceding','initial-known','unknown'):assert 'error_type' in end
    else:
        ratings=module.read(root/'ratings.json')
        assert len(ratings['ratings'])==76 and len(ratings['accepted_decisions'])==263
        assert not ratings['missing_imputed'] and ratings['new_native_worlds']==0
        assert module.read(root/'interface-check.json')['all_literal_panels_complete']
        assert Counter(calls)==Counter(module.content_set(body).keys())
    with pytest.raises(ValueError,match='consumed'):module.run(root)


def test_stopped_preceding_report_never_looks_at_output_tables(tmp_path):
    save(tmp_path/'ended.json',{'status':'stopped'})
    with pytest.raises(ValueError,match='preceding report stopped'):module.wait_report(tmp_path)


def test_finite_wait_never_dispatches(tmp_path):
    times=iter([0,86401])
    with pytest.raises(ValueError,match='finite preceding-report wait'):
        module.wait_report(tmp_path,clock=lambda:next(times),poll=lambda s:None)


def test_runner_real_observer_journals_all228_literal_scripted_replies_and_cold_replays(tmp_path,monkeypatch):
    from tests.optimization.test_common_content_observer import Backend,PROVIDER
    from utopia.optimization.common_content_observer import make_contract,CommonContentObserver
    body=inputs();save(tmp_path/'inputs.json',{k:v for k,v in body.items() if k!='content_sha256'})
    contract=make_contract(source_commit='a'*40,provider=PROVIDER,
        backend={**PROVIDER,'ollama_version':'SCRIPTED-version'},maximum_posts=228,critics=3)
    p={'content_sha256':'SCRIPTED-plan','preceding_report':str(tmp_path/'prior'),
        'inputs_path':str(tmp_path/'inputs.json'),'inference_lock':str(tmp_path/'lock'),'contract':contract}
    monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    monkeypatch.setattr(module,'wait_report',lambda directory:{'status':'closed'})
    backend=Backend();monkeypatch.setattr(module,'LocalObserverBackend',lambda **kwargs:backend)
    root=tmp_path/'run';root.mkdir();module.run(root)
    assert len(backend.calls)==228 and len(set(wire for wire,timeout in backend.calls))==228
    for wire,timeout in backend.calls:
        value=json.loads(wire)
        assert set(json.loads(value['messages'][1]['content']))=={'title','abstract','topics'}
        assert 'SCRIPTED-world-' not in wire and 'SCRIPTED-paper-' not in wire
    first=module.read(root/'audit.json');cold_backend=Backend()
    observer=CommonContentObserver(root/'observer',contract,backend=cold_backend)
    assert observer.audit()==first
    for key in module.content_set(body):
        assert module.read(root/'ratings'/(key+'.json'))['paper_content_sha256']==key
    before=len(backend.calls)
    for value in module.content_set(body).values():observer.rate(value)
    assert not cold_backend.calls and len(backend.calls)==before


def test_saved_plan_roundtrip_reconstructs_full_content_order_and_protocol_binding(tmp_path,monkeypatch):
    from tests.optimization.test_common_content_observer import PROVIDER
    body=inputs();path=tmp_path/'inputs.json';save(path,{k:v for k,v in body.items() if k!='content_sha256'})
    monkeypatch.setattr(module,'INPUT_SHA',module.sha(path));monkeypatch.setattr(module,'git_binding',lambda root:'a'*40)
    prior=tmp_path/'prior';prior.mkdir()
    save(prior/'started.json',{'schema':'scienceutopia.code-tested-report-finish.v1',
        'scientific_source_commit':'93076b477b023a6bcb78cac5568fcbe795fa9a52'})
    p=module.build_plan(source='a'*40,inputs_path=path,preceding_report=prior,
        inference_lock=tmp_path/'lock',provider=PROVIDER,backend={**PROVIDER,'ollama_version':'SCRIPTED-version'})
    saved=save(tmp_path/'plan.json',p)
    assert module.require_plan(tmp_path)==saved
    assert p['maximum_posts']==228 and len(p['content_order'])==76
    assert p['initial_interface_check_content_hashes']==p['content_order'][:3]
