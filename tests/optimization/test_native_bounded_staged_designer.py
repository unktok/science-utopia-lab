import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from utopia.optimization import native_bounded_staged_designer as module


def test_literal_wire_is_durable_before_the_single_actual_dispatch(tmp_path):
    calls=[]
    class Session:
        def post(self,endpoint,**kwargs):
            intent=json.loads((tmp_path/'dispatch-000.intent.json').read_text())
            assert intent['wire_utf8'].encode()==kwargs['data']
            calls.append(endpoint)
            return SimpleNamespace(status_code=200,text='{"done":true}')
    session=module.DurableSession(Session(),tmp_path,maximum_posts=1)
    session.post('http://127.0.0.1:11434/api/chat',data=b'{"x":1}',timeout=(10,900))
    assert len(calls)==1
    assert (tmp_path/'dispatch-000.http.json').exists()
    with pytest.raises(ValueError,match='budget'):
        session.post('http://127.0.0.1:11434/api/chat',data=b'{}',timeout=(10,900))
    assert len(calls)==1


@pytest.mark.parametrize('kind',['timeout','nonfinal'])
def test_unknown_completion_cannot_be_caught_as_an_editor_semantic_error(tmp_path,kind):
    class Session:
        def post(self,*args,**kwargs):
            if kind=='timeout':raise requests.ReadTimeout('SCRIPTED uncertain completion')
            return SimpleNamespace(status_code=200,text='{"done":false}')
    session=module.DurableSession(Session(),tmp_path,maximum_posts=16)
    with pytest.raises(module.CompletionUnknown):
        session.post('http://127.0.0.1:11434/api/chat',data=b'{}',timeout=(10,900))
    assert (tmp_path/'dispatch-000.intent.json').exists() and (tmp_path/'dispatch-000.http.json').exists()
    assert not issubclass(module.CompletionUnknown,Exception)


def test_whole_session_timeout_preserves_intent_and_never_restarts(tmp_path,monkeypatch):
    calls=[]
    def run(*args,**kwargs):
        calls.append(args);assert (tmp_path/'intent.json').exists()
        return {'timed_out':True,'returncode':-15,'elapsed_seconds':1.,'server_cancel_confirmed':False}
    monkeypatch.setattr(module,'run_bounded',run)
    for _ in range(2):
        with pytest.raises(module.CompletionUnknown):
            module.execute(tmp_path,kind='proposal',request={},provider={},source_commit='scripted',
                           certificate=tmp_path/'cert.json',seconds=1)
    assert len(calls)==1 and not (tmp_path/'worker-result.json').exists()
    receipt=json.loads((tmp_path/'result.json').read_text())
    assert not receipt['redispatch_allowed']


def test_worker_terminal_error_is_not_silently_replaced_with_the_initial_system(tmp_path,monkeypatch):
    def run(argv,**kwargs):
        intent=module.checked(json.loads((tmp_path/'intent.json').read_text()))
        module.save(tmp_path/'worker-result.json',{'intent_sha256':intent['content_sha256'],
            'error_type':'ValueError','error':'SCRIPTED invalid actual editor source','completion_unknown':False})
        return {'timed_out':False,'returncode':0}
    monkeypatch.setattr(module,'run_bounded',run)
    with pytest.raises(ValueError,match='invalid actual editor'):
        module.execute(tmp_path,kind='proposal',request={},provider={},source_commit='scripted',seconds=1)
    assert json.loads((tmp_path/'result.json').read_text())['worker_result_exists']


@pytest.mark.parametrize('unknown',[False,True])
def test_real_worker_wiring_records_post_before_dispatch_and_stops_unknown(tmp_path,monkeypatch,unknown):
    # Trusted orchestration unit: mocked role/model/certificate, not readiness.
    import utopia.optimization.native_jobs as jobs
    import utopia.optimization.native_designer_roles_v38 as roles
    import utopia.optimization.native_scientist_load_v38 as loads
    monkeypatch.setattr(jobs,'pinned_revision',lambda root:'a'*40)
    monkeypatch.setattr(loads,'load_local_role',lambda *a,**kw:None)
    calls=[]
    class Session:
        def post(self,endpoint,**kwargs):
            assert (tmp_path/'wire/dispatch-000.intent.json').exists()
            calls.append(endpoint)
            if unknown:raise requests.ReadTimeout('SCRIPTED unknown')
            return SimpleNamespace(status_code=200,text='{"done":true}')
    class Generator:
        model=SimpleNamespace(session=Session())
        def __call__(self,request):
            self.model.session.post('http://127.0.0.1:11434/api/chat',data=b'{}',timeout=(10,900))
            return {'SCRIPTED':'literal definition'}
    monkeypatch.setattr(roles,'make_local_role_bound_generator',lambda *a,**kw:Generator())
    module.save(tmp_path/'intent.json',{'kind':'proposal','request':{},'provider':{'image_id':'SCRIPTED'},
        'runtime':module.runtime_binding(),'source_commit':'a'*40,'maximum_posts':16,'certificate':'SCRIPTED'})
    module.worker(tmp_path/'intent.json',tmp_path/'worker-result.json')
    result=module.checked(json.loads((tmp_path/'worker-result.json').read_text()))
    assert len(calls)==1 and (tmp_path/'wire/dispatch-000.http.json').exists()
    if unknown:
        assert result['completion_unknown'] and result['error_type']=='CompletionUnknown'
        assert 'definition' not in result
    else:assert result['submitted'] and result['definition']=={'SCRIPTED':'literal definition'}
