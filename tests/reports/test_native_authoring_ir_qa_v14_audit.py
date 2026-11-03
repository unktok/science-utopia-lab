"""SCRIPTED queue/author/protocol contracts only; no model, container or native world."""
from copy import deepcopy
import hashlib
import json

import pytest

from scripts import analyze_native_authoring_ir_qa_v14 as audit
from tests.optimization.test_native_search_v14 import BINDING,FailedFactory,REVISION
from utopia.optimization.native_search_generator_v14 import LLMVocabularyGenerator
from utopia.system.native_open_examples import open_native_system
from utopia.utils.data_utils import write_json_atomic


def save(path,value):
    write_json_atomic(path,value,sort_keys=True,allow_nan=False)


def fixture(root,interrupt=False):
    manifest = audit.build_manifest(source_commit=REVISION,
        initial_system=open_native_system(BINDING['image_id']).to_dict(),
        loss_spec=audit.objective_specs()['native-joint-v5-throughput'],provider_binding=BINDING,
        runtime_seed_binding={'python_hash_seed_environment':'42','python_hash_probe':123},
        protocol_sha256=audit.file_sha256(audit.ROOT/audit.PROTOCOL))
    manifest['classification'] = audit.FIXTURE
    manifest['content_sha256'] = audit.digest(manifest)
    for name,value in [('manifest',manifest),('request',manifest['request']),('operator-config',manifest['operator_config'])]:
        save(root/(name+'.json'),value)
    queue = audit.NativeSearchQueue(root/'queue',provider_binding=BINDING)
    request = manifest['request']
    checked = queue.validate(request,source_commit=REVISION)
    queued = queue.submit(request,confirmed_request_sha256=audit.digest(request),source_commit=REVISION)
    bad = {'operations':[{'op':'replace','selector':{'mechanism_id':'absent-scripted-id'},
        'path':'/parameters/value','value':1.0}],'factors':[],'continuous':[],
        'rationale':'SCRIPTED failure, not scientific evidence'}
    class Model:
        calls = 0
        def generate(self,**kwargs):
            self.calls += 1
            if interrupt and self.calls == 1:
                raise KeyboardInterrupt('SCRIPTED unknown response boundary')
            return bad,[{'role':'assistant','content':json.dumps(bad)}]
    model = Model()
    def builder(directory,request,provider):
        return LLMVocabularyGenerator(model,directory/'authoring',image_id=BINDING['image_id'],
            provider_binding=BINDING,protocol=audit.StableIDAuthoringProtocol())
    if interrupt:
        with pytest.raises(KeyboardInterrupt):
            queue.run_one(lambda *a: FailedFactory(),generator_builder=builder,source_commit=REVISION)
    queue.run_one(lambda *a: FailedFactory(),generator_builder=builder,source_commit=REVISION)
    network=[]
    for path,body,response in [('/native-api/search-validate',request,checked),('/native-api/searches',
            {'request':request,'confirmed_request_sha256':audit.digest(request)},queued)]:
        raw=json.dumps(body); reply=json.dumps(response)
        network.append({'url':'http://127.0.0.1:4594'+path,'method':'POST','request_body_text':raw,
            'request_body_utf8_sha256':hashlib.sha256(raw.encode()).hexdigest(),'http_status':200,
            'response_body_text':reply,'response_body_sha256':hashlib.sha256(reply.encode()).hexdigest()})
    save(root/'operator/actual-ui-submit-receipt.json',{
        'schema':'scienceutopia.native-search-actual-ui-submit.v14','expected_source':REVISION,
        'expected_request_sha256':manifest['request_sha256'],'request_file_sha256':audit.file_sha256(root/'request.json'),
        'provider_file_sha256':audit.file_sha256(root/'operator-config.json'),'search_id':queued['search_id'],
        'status':'queued-once','submission_clicked_once':True,'no_adoption':True,
        'no_worker_or_model_started_by_harness':True,'failures':[],'browser_errors':0,
        'fixture_interception':True,'fixed_loopback_origin':'http://127.0.0.1:4594','network':network,'captures':[]})
    return model,queued


@pytest.mark.parametrize('interrupt',[False,True])
def test_scripted_queue_ir_failures_are_null_repeatable_and_unknown_is_not_replayed(tmp_path,interrupt):
    model,_=fixture(tmp_path,interrupt)
    before=audit._inventory(tmp_path)
    first=audit.analyze(tmp_path,expected_source=REVISION)
    assert first == audit.analyze(tmp_path,expected_source=REVISION)
    assert before == audit._inventory(tmp_path)
    assert first['native']['consumed_native_slots']==2
    assert first['native']['physical_native_worlds']==first['native']['physical_researcher_responses']==0
    assert first['designer']['dispatch_intents']==model.calls==4
    assert first['designer']['known_responses']==4-int(interrupt)
    assert first['designer']['interrupted_response_unknown']==int(interrupt)
    assert not first['claims']['actual_UI_queue_worker_roundtrip']
    assert first['operator']['wire_numeric_JSON_verified']


@pytest.mark.parametrize('mutation',['extra-submit','wire-number','response-hash','prompt','compiler-binding'])
def test_scripted_rehashed_corruption_is_rejected(tmp_path,mutation):
    fixture(tmp_path)
    path=tmp_path/'operator/actual-ui-submit-receipt.json'
    receipt=audit.read(path)
    if mutation=='extra-submit':
        receipt['network'].append(deepcopy(receipt['network'][-1]));save(path,receipt)
    elif mutation=='wire-number':
        row=receipt['network'][0];row['request_body_text']=row['request_body_text'].replace('1.0','1',1)
        row['request_body_utf8_sha256']=hashlib.sha256(row['request_body_text'].encode()).hexdigest();save(path,receipt)
    elif mutation=='response-hash':
        receipt['network'][0]['response_body_text']+=' ';save(path,receipt)
    else:
        cell=next((tmp_path/'queue').glob('search-*/authoring/generation-*'))
        path=cell/('attempt-00.started.json' if mutation=='prompt' else 'request.json')
        record=audit.read(path)
        if mutation=='prompt':record['prompt']+=' repair silently';record['prompt_sha256']=audit.digest(record['prompt'])
        else:
            record['authoring_protocol']['branch_policy']='filter failures'
            record.pop('binding_sha256');record['binding_sha256']=audit.digest(record)
        save(path,record)
    with pytest.raises(ValueError):audit.analyze(tmp_path,expected_source=REVISION)


def test_translation_preserves_authored_operands_without_numeric_normalization():
    raw={'operations':[{'op':'replace','selector':{'mechanism_id':'x'},'path':'/v','value':1.0}],
        'factors':[],'continuous':[],'rationale':'SCRIPTED'}
    translated=deepcopy(raw);translated['operations'][0].pop('selector');translated['operations'][0]['path']='/mechanisms/0/v'
    audit._literal_translation(raw,translated)
    translated['operations'][0]['value']=1
    with pytest.raises(ValueError,match='literal'):audit._literal_translation(raw,translated)
