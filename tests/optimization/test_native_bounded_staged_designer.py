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


def test_component_pending_stops_the_outer_worker_without_becoming_a_semantic_retry(tmp_path,monkeypatch):
    from utopia.optimization.native_component_lab_v1 import ComponentProbePending
    calls=[]
    def run(argv,**kwargs):
        calls.append(argv);intent=module.checked(json.loads((tmp_path/'intent.json').read_text()))
        module.save(tmp_path/'worker-result.json',{'intent_sha256':intent['content_sha256'],
            'error_type':'ComponentProbePending','error':'SCRIPTED component pending',
            'completion_unknown':False,'component_probe_pending':True})
        return {'timed_out':False,'returncode':0}
    monkeypatch.setattr(module,'run_bounded',run)
    for _ in range(2):
        with pytest.raises(ComponentProbePending):
            module.execute(tmp_path,kind='proposal',request={},provider={},source_commit='SCRIPTED')
    assert len(calls)==1


def test_unaccounted_json_journal_is_not_ignored_by_saved_bounded_result(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'run_bounded',lambda *a,**k:{'timed_out':True,'returncode':-15})
    with pytest.raises(module.CompletionUnknown):
        module.execute(tmp_path,kind='proposal',request={},provider={},source_commit='SCRIPTED')
    module.save(tmp_path/'unaccounted-dispatch.json',{'SCRIPTED':'not in terminal inventory'})
    with pytest.raises(ValueError,match='unaccounted JSON'):module.replay(tmp_path)


@pytest.mark.parametrize('extended',[False,True])
def test_worker_component_adapter_is_exactly_bound_and_pending_is_preserved(tmp_path,monkeypatch,extended):
    from tests.optimization.test_native_post_edit_feedback_v1 import fixture,source_action,BAD,finish
    import utopia.optimization.native_jobs as jobs
    import utopia.optimization.native_designer_roles_v38 as roles
    import utopia.optimization.native_scientist_load_v38 as loads
    import utopia.system.code_mechanisms as code
    from utopia.optimization.native_component_lab_v1 import ComponentProbePending
    options={'extended':True,'reference':'resource-30-connected','maximum_probes':64} if extended else {}
    gen,model,body,calls=fixture(tmp_path/'fixture',[source_action(BAD),finish()],**options)
    adapter=gen.edit_feedback;seen=[]
    monkeypatch.setattr(jobs,'pinned_revision',lambda root:'c'*40)
    monkeypatch.setattr(loads,'load_local_role',lambda *a,**kw:None)
    monkeypatch.setattr(code,'DockerCodeExecutor',lambda **kw:adapter.executor)
    class Generator:
        model=SimpleNamespace(session=object())
        def __call__(self,request):raise ComponentProbePending('SCRIPTED worker pending')
    def make(*args,**kwargs):
        seen.append(kwargs['edit_feedback'].contract);return Generator()
    monkeypatch.setattr(roles,'make_local_role_bound_generator',make)
    module.save(tmp_path/'intent.json',{'kind':'proposal','request':body,
        'provider':{'image_id':adapter.executor.image_id},'runtime':module.runtime_binding(),
        'source_commit':'c'*40,'maximum_posts':16,'certificate':'SCRIPTED',
        'post_edit_component_bank':adapter.bank})
    module.worker(tmp_path/'intent.json',tmp_path/'worker-result.json')
    result=module.checked(json.loads((tmp_path/'worker-result.json').read_text()))
    assert seen==[adapter.contract] and result['component_probe_pending']
    assert not result['completion_unknown'] and not calls and not model.calls


def test_declared_component_contract_without_bank_stops_before_model_role_load(tmp_path,monkeypatch):
    import utopia.optimization.native_jobs as jobs
    import utopia.optimization.native_scientist_load_v38 as loads
    monkeypatch.setattr(jobs,'pinned_revision',lambda root:'c'*40)
    def forbidden(*a,**kw):raise AssertionError('no role load before binding check')
    monkeypatch.setattr(loads,'load_local_role',forbidden)
    module.save(tmp_path/'intent.json',{'kind':'proposal',
        'request':{'strategy_provenance':{'post_edit_component_contract':{'SCRIPTED':True}}},
        'provider':{},'runtime':module.runtime_binding(),'source_commit':'c'*40,
        'maximum_posts':16,'certificate':'SCRIPTED'})
    module.worker(tmp_path/'intent.json',tmp_path/'worker-result.json')
    result=module.checked(json.loads((tmp_path/'worker-result.json').read_text()))
    assert result['error_type']=='ValueError' and 'no configured bank' in result['error']
    assert not (tmp_path/'wire').exists()


@pytest.mark.parametrize('extended',[False,True])
def test_actual_calibration_worker_declares_feedback_without_executing_components(tmp_path,monkeypatch,extended):
    # Complete scripted transport calibration, not a mocked passed certificate.
    # Calibration describes the production mode but must never run its code.
    from tests.optimization.test_native_post_edit_feedback_v1 import fixture,finish
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession
    import utopia.optimization.native_jobs as jobs
    import utopia.optimization.native_scientist_load_v38 as loads
    from utopia.optimization.native_designer_preflight import require_certificate,EXECUTION_SCOPE
    options={'extended':True,'reference':'resource-30-connected','maximum_probes':64} if extended else {}
    gen,model,body,calls=fixture(tmp_path/'fixture',[finish()],**options)
    monkeypatch.setattr(jobs,'pinned_revision',lambda root:'c'*40)
    monkeypatch.setattr(loads,'load_local_role',lambda *a,**kw:None)
    monkeypatch.setattr('requests.Session',ScriptedSession);ScriptedSession.calls=[]
    module.save(tmp_path/'intent.json',{'kind':'calibration','request':body,
        'provider':gen.provider_binding,'runtime':module.runtime_binding(),'source_commit':'c'*40,
        'maximum_posts':40,'certificate':None})
    module.worker(tmp_path/'intent.json',tmp_path/'worker-result.json')
    result=module.checked(json.loads((tmp_path/'worker-result.json').read_text()))
    assert result.get('passed'),result
    certificate=require_certificate(tmp_path/'calibration/certificate.json',gen.provider_binding,
        protocol='staged-v15',scope=EXECUTION_SCOPE,conversation_profile=module.BOUNDED_AUTHORING)
    retained=module.checked(json.loads((tmp_path/'calibration/certificate.json').read_text()))
    assert retained['plan']['request']==body
    assert certificate['post_edit_component_contract']==gen.edit_feedback.contract
    assert len(ScriptedSession.calls)==certificate['controls']
    assert not calls and not model.calls and not (tmp_path/'component-lab').exists()
    for path in (tmp_path/'wire').glob('dispatch-*.intent.json'):
        assert 'OPTIONAL COMPONENT TESTS ARE DECLARED' in module.checked(json.loads(path.read_text()))['wire_utf8']


@pytest.mark.parametrize('extended',[False,True])
def test_real_role_factory_consumes_real_scripted_certificate_and_repairs_with_feedback(tmp_path,monkeypatch,extended):
    # No mocked certificate summary or model class: actual role/factory/transport
    # implementations, with an explicitly scripted HTTP server and executor.
    from tests.optimization.test_native_post_edit_feedback_v1 import fixture,source_action,BAD,GOOD,finish
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession,Response
    from tests.optimization.test_native_designer_roles_v38 import designer_binding
    from utopia.optimization.native_designer_roles_v38 import make_local_role_bound_generator
    from utopia.optimization.native_designer_preflight import run_calibration,EXECUTION_SCOPE
    from utopia.optimization.native_designer_tools_v25 import function_data
    from utopia.optimization.native_staged_author_v15 import replay_staged_generation
    options={'extended':True,'reference':'resource-30-connected','maximum_probes':64} if extended else {}
    gen,unused,body,probes=fixture(tmp_path/'fixture',[finish()],**options)
    binding=designer_binding();binding['image_id']=gen.image_id
    actions=[{'tool':'plan','objective_reasoning':'SCRIPTED','design_intent':'SCRIPTED'},
        source_action(BAD),source_action(GOOD)]
    if extended:actions.extend([source_action(BAD),source_action(GOOD)])
    actions.append(finish())
    class Session(ScriptedSession):
        calls=[];production=[]
        def get(self,url,**kwargs):
            if url.endswith('/version'):return Response({'version':'SCRIPTED-not-actual'})
            return Response({'models':[{'name':binding['model'],'digest':binding['model_digest']}]})
        def post(self,url,**kwargs):
            payload=json.loads(kwargs['data']);system=payload['messages'][0]['content']
            if 'TRUSTED INTERFACE CALIBRATION TASK' in system:
                result=super().post(url,**kwargs).json();result['model']=binding['model'];return Response(result)
            action=actions[len(self.production)];self.production.append(payload);self.calls.append(payload)
            return Response({'model':binding['model'],'done':True,'done_reason':'stop',
                'prompt_eval_count':120,'eval_count':12,'message':{'role':'assistant',
                    'content':json.dumps(function_data(action)),
                    **({'thinking':'SCRIPTED planner evidence'} if payload['think'] else {})}})
    monkeypatch.setattr('requests.Session',Session)
    run_calibration(tmp_path/'calibration',request=body,provider=binding,scope=EXECUTION_SCOPE,
        conversation_profile=module.BOUNDED_AUTHORING)
    author=make_local_role_bound_generator(tmp_path/'author',image_id=gen.image_id,
        provider_binding=binding,max_steps=16,max_tokens=8192,
        preflight_certificate=tmp_path/'calibration/certificate.json',readiness_scope=EXECUTION_SCOPE,
        conversation_profile=module.BOUNDED_AUTHORING,edit_feedback=gen.edit_feedback)
    result=author(body)
    assert result is not None and 'generation_failure' not in result
    expected_calls,expected_probes=(6,16) if extended else (4,8)
    assert len(Session.production)==expected_calls and len(probes)==expected_probes
    assert 'SCRIPTED-BAD-FLOAT' in json.dumps(Session.production[2])
    assert not unused.calls
    directory=next((tmp_path/'author').glob('generation-*'))
    assert replay_staged_generation(directory)==result
    assert len(Session.production)==expected_calls and len(probes)==expected_probes
