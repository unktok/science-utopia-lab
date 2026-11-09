from copy import deepcopy
import json
from pathlib import Path
import sys
import time

import pytest

from utopia.optimization import native_numeric_designer as module
from utopia.optimization.native_designer_wire import wire_record
from utopia.optimization.native_numeric_submission import numeric_context
from utopia.runtime.bounded_process import run_bounded
from tests.optimization.test_native_design_space import campaign

IMAGE = 'sha256:'+'a'*64
PROVIDER = {'model': 'qwen3.6:35b-mlx-64k',
    'model_digest': 'f3ddc74319e42fad1cce455555e9f6864372665bcf9f0578b600f554787cbcc8',
    'corpus_sha256': 'c'*64, 'dataset_identity': {'dataset':'Ahren09/SciEvo', 'configuration':'arxiv',
        'revision':'a'*40, 'normalization':'parallel', 'start_year':2016, 'num_years':4,
        'categories':['cs.AI']}, 'corpus_years':4, 'image_id':IMAGE}
BACKEND = {'model':PROVIDER['model'], 'model_digest':PROVIDER['model_digest'], 'ollama_version':'SCRIPTED'}


def fixture(tmp_path, monkeypatch, replies):
    # These are mocked HTTP outcomes, never a model calibration certificate.
    monkeypatch.setattr(module, 'validate_designer_binding', lambda x: None)
    c = campaign(tmp_path/'campaign'); req = c._request([], c._strategy_initial(), 1)
    parent = {x['id']:x['current_value'] for x in numeric_context(req)['coordinates']}
    calls = []
    def fake_run(argv, **kwargs):
        intent_path, response_path = map(Path, argv[-2:]); intent=json.loads(intent_path.read_text())
        calls.append(intent); reply = replies[len(calls)-1](deepcopy(parent))
        body = {'done':True, 'done_reason':'stop', 'model':PROVIDER['model'],
                'message':{'role':'assistant', 'content':json.dumps(reply)}}
        module.save(response_path, {'schema':module.SCHEMA+'.http', 'intent_sha256':intent['content_sha256'],
            'literal_submission':reply, 'transport':{**wire_record(intent['payload'], intent['response_schema']),
                'http_status':200, 'raw_http_response':json.dumps(body), 'response_payload':body},
            'elapsed_seconds':0.})
        return {'timed_out':False, 'returncode':0, 'elapsed_seconds':0., 'redispatched':False}
    monkeypatch.setattr(module, 'run_bounded', fake_run)
    designer=module.NumericDesigner(tmp_path/'author',provider=PROVIDER,backend=BACKEND,calibration=True)
    return designer,req,calls


def valid(values):
    return {'values':values, 'rationale':'SCRIPTED literal submission'}


def test_literal_submission_and_cold_replay_never_redispatch(tmp_path,monkeypatch):
    author,req,calls=fixture(tmp_path,monkeypatch,[valid])
    result=author(req)
    assert result['base_patch'] is None and len(calls)==1
    assert author(req)==result and len(calls)==1
    root=author.directory/('generation-'+module.digest(req))
    assert module.replay_numeric(root)['definition']==result
    assert calls[0]['request_wire']==wire_record(calls[0]['payload'],calls[0]['response_schema'])


def test_invalid_value_repairs_only_through_second_model_response(tmp_path,monkeypatch):
    def bad(v):v['coordinate-2']=99;return valid(v)
    def fixed(v):v['coordinate-2']=.875;return valid(v)
    author,req,calls=fixture(tmp_path,monkeypatch,[bad,fixed])
    result=author(req)
    assert len(calls)==2
    assert result['base_patch']['operations'][0]['value']==.875
    sent=json.loads(calls[1]['payload']['messages'][1]['content'])
    assert sent['previous_literal_submission_feedback']['literal_submission']['values']['coordinate-2']==99
    assert 'outside' in sent['previous_literal_submission_feedback']['error']['message']


def test_two_invalid_proposals_do_not_become_baseline(tmp_path,monkeypatch):
    def bad(v):v['coordinate-2']=99;return valid(v)
    author,req,calls=fixture(tmp_path,monkeypatch,[bad,bad])
    assert author(req) is None and len(calls)==2
    result=module.replay_numeric(author.directory/('generation-'+module.digest(req)))
    assert result['status']=='failed' and result['definition'] is None


def test_incomplete_worker_never_retries_or_fabricates_response(tmp_path,monkeypatch):
    author,req,calls=fixture(tmp_path,monkeypatch,[valid])
    monkeypatch.setattr(module,'run_bounded',lambda *a,**k:{'timed_out':True,'returncode':-15})
    with pytest.raises(module.NumericCompletionUnknown):author(req)
    assert not calls
    root=author.directory/('generation-'+module.digest(req))
    assert len(list(root.glob('*.intent.json')))==1 and not list(root.glob('*.http.json'))
    assert module.replay_numeric(root)['status']=='failed'
    assert module.replay_numeric(root)['completion_unknown']
    with pytest.raises(module.NumericCompletionUnknown):author(req)
    assert not calls


def test_actual_campaign_needs_numeric_certificate(tmp_path,monkeypatch):
    author,req,_=fixture(tmp_path,monkeypatch,[valid]);author.calibration=False
    with pytest.raises(ValueError,match='certificate'):
        author(req)
    assert not author.directory.exists()


def test_raw_response_tampering_rejects_even_after_outer_rehash(tmp_path,monkeypatch):
    author,req,_=fixture(tmp_path,monkeypatch,[valid]);author(req)
    root=author.directory/('generation-'+module.digest(req));path=root/'call-0.http.json'
    raw=json.loads(path.read_text());raw['literal_submission']['values']['coordinate-2']=1.25
    raw['content_sha256']=module.digest({k:v for k,v in raw.items() if k!='content_sha256'})
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError,match='literal'):
        module.replay_numeric(root)


def test_real_owned_process_wall_bound_is_not_just_a_read_timeout():
    result=run_bounded([sys.executable,'-c','import time; time.sleep(10)'],seconds=.1)
    assert result['timed_out'] and result['returncode'] is not None
    assert result['elapsed_seconds']<3.5 and result['server_cancel_confirmed'] is False
    assert not result['redispatched']
