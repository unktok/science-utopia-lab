"""SCRIPTED explicit local loads, never an actual provider request."""
import json

import pytest

from tests.optimization.test_native_designer_contract_v16 import Response
from tests.optimization.test_native_loaded_roles_v38 import bindings
from utopia.optimization.native_scientist_load_v38 import load_scientist, load_local_role, replay_load
from utopia.system.design_patch import digest


class Session:
    def __init__(self, body=None, error=None):
        self.body = body if body is not None else {'model':'qwen3:8b','done':True,'done_reason':'load'}
        self.error, self.calls = error, []
    def post(self, url, **kwargs):
        self.calls.append((url,kwargs))
        assert url == 'http://127.0.0.1:11434/api/generate'
        assert kwargs['timeout'] == (10,120)
        payload = json.loads(kwargs['data'])
        assert payload['prompt'] == '' and payload['model']=='qwen3:8b'
        assert payload['options']=={'num_ctx':40960} and payload['stream'] is False
        if self.error:
            raise self.error
        return Response(self.body)


def read(path):
    return json.loads(path.read_text())


def test_one_empty_load_records_intent_wire_body_and_replays_without_calls(tmp_path):
    session=Session();path=tmp_path/'load.json';provider=bindings()['scientist']
    record=load_scientist(path,provider=provider,purpose='SCRIPTED',session=session)
    intent=read(path.with_suffix('.started.json'))
    assert len(session.calls)==1 and record['valid_empty_prompt_load']
    assert 'eval_count' not in record['response_payload']
    assert 'prompt_eval_count' not in record['response_payload']
    assert replay_load(intent,record,provider=provider,purpose='SCRIPTED')['empty_prompt_load_confirmed']
    before=path.read_bytes()
    with pytest.raises(ValueError,match='no overwrite or hidden retry'):
        load_scientist(path,provider=provider,purpose='SCRIPTED',session=session)
    assert path.read_bytes()==before and len(session.calls)==1


@pytest.mark.parametrize('body',[
    {'model':'qwen3:8b','done':False},
    {'model':'qwen3:8b','done':True,'done_reason':'stop'},
    {'model':'another-model','done':True,'done_reason':'load'},
    {'model':'qwen3:8b','done':True,'done_reason':'load','response':'unexpected generation'},
    {'model':'qwen3:8b','done':True,'done_reason':'load','eval_count':3},
    {'model':'qwen3:8b','done':True,'done_reason':'load','eval_count':False},
])
def test_unknown_nonload_or_generated_response_stops_without_retry(tmp_path,body):
    session=Session(body);provider=bindings()['scientist'];path=tmp_path/'bad.json'
    with pytest.raises(ValueError,match='failed/unknown'):
        load_scientist(path,provider=provider,purpose='SCRIPTED',session=session)
    record=read(path)
    assert record['response_payload']==body and not record['valid_empty_prompt_load']
    assert not replay_load(read(path.with_suffix('.started.json')),record,
        provider=provider,purpose='SCRIPTED')['empty_prompt_load_confirmed']
    assert len(session.calls)==1


def test_timeout_preserves_known_intent_and_unknown_response(tmp_path):
    session=Session(error=TimeoutError('SCRIPTED'));provider=bindings()['scientist'];path=tmp_path/'failed.json'
    with pytest.raises(ValueError):
        load_scientist(path,provider=provider,purpose='SCRIPTED',session=session)
    record=read(path)
    assert record['error'].startswith('TimeoutError') and 'response_payload' not in record
    assert record['elapsed_seconds']>=0 and len(session.calls)==1
    assert replay_load(read(path.with_suffix('.started.json')),record,
        provider=provider,purpose='SCRIPTED')['status']=='failed-or-unknown-load'


def test_interruption_keeps_pre_dispatch_intent_without_fabricated_completion(tmp_path):
    session=Session(error=KeyboardInterrupt('SCRIPTED'));provider=bindings()['scientist'];path=tmp_path/'unknown.json'
    with pytest.raises(KeyboardInterrupt):
        load_scientist(path,provider=provider,purpose='SCRIPTED',session=session)
    assert not path.exists() and len(session.calls)==1
    assert replay_load(read(path.with_suffix('.started.json')),None,
        provider=provider,purpose='SCRIPTED')['status']=='dispatched-response-unknown'
    with pytest.raises(ValueError,match='already dispatched'):
        load_scientist(path,provider=provider,purpose='SCRIPTED',session=session)
    assert len(session.calls)==1


def test_rehashed_nonempty_prompt_or_raw_response_change_is_rejected(tmp_path):
    provider=bindings()['scientist'];path=tmp_path/'load.json'
    record=load_scientist(path,provider=provider,purpose='SCRIPTED',session=Session())
    intent=read(path.with_suffix('.started.json'))
    intent['request_payload']['prompt']='unauthorized scientific prompt'
    intent['content_sha256']=digest({k:v for k,v in intent.items() if k!='content_sha256'})
    with pytest.raises(ValueError):
        replay_load(intent,record,provider=provider,purpose='SCRIPTED')
    intent=read(path.with_suffix('.started.json'))
    record['response_payload']['done']=False
    record['content_sha256']=digest({k:v for k,v in record.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='raw response'):
        replay_load(intent,record,provider=provider,purpose='SCRIPTED')


def test_changed_scientist_weights_are_rejected_before_dispatch(tmp_path):
    provider={**bindings()['scientist'],'model_digest':'0'*64};session=Session()
    with pytest.raises(ValueError,match='original researcher weights'):
        load_scientist(tmp_path/'never.json',provider=provider,purpose='SCRIPTED',session=session)
    assert session.calls==[] and not list(tmp_path.iterdir())


def test_explicit_designer_load_cannot_be_mislabeled_as_a_scientist_load(tmp_path):
    designer=bindings()['designer'];path=tmp_path/'designer.json'
    class DesignerSession:
        calls=[]
        def post(self,url,**kwargs):
            self.calls.append(kwargs)
            payload=json.loads(kwargs['data'])
            assert payload['model']==designer['model'] and payload['prompt']==''
            assert payload['options']=={'num_ctx':40960}
            return Response({'model':designer['model'],'done':True,'done_reason':'load'})
    session=DesignerSession()
    record=load_local_role(path,provider=designer,purpose='SCRIPTED-designer',role='designer',session=session)
    intent=read(path.with_suffix('.started.json'))
    assert intent['role']==record['role']=='designer' and len(session.calls)==1
    assert replay_load(intent,record,provider=designer,purpose='SCRIPTED-designer',role='designer')['empty_prompt_load_confirmed']
    with pytest.raises(ValueError):
        replay_load(intent,record,provider=designer,purpose='SCRIPTED-designer',role='scientist')
    with pytest.raises(ValueError):
        load_scientist(tmp_path/'not-science.json',provider=designer,purpose='SCRIPTED',session=session)
    assert len(session.calls)==1
