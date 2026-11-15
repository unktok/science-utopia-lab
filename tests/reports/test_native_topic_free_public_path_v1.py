"""Opt-in clean-source public SOFTWARE path; all providers/corpus are SCRIPTED.

Real native worlds, Docker code, role journals, installed scientist SDK,
calibration/editor/next-feedback calls and outer/inner cold replays remain.
Only bounded child supervision is replaced by its synchronous actual worker;
this test does not certify deadlines or real-model capacity/optimization.
"""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

from openai import OpenAI
import pytest

from scripts import run_native_topic_free_optimization_v1 as driver
from scripts import audit_native_topic_free_optimization_v1 as auditor
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_legacy_choice_pilot_native_v1 import public_operator_path
from tests.reports.test_native_legacy_choice_native_v1 import ScriptedCritic
from tests.reports.test_native_open_workflow_post_edit_v1 import transparent_office
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization import native_bounded_staged_designer as bounded
from utopia.optimization.native_designer_tools_v25 import function_data
from utopia.optimization.native_resource_cost import METRIC
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_TOPIC_FREE_PUBLIC_QA') != '1',
                   reason='explicit clean-source hardware window, no real inference active')
def test_actual_bounded_editor_feedback_native_objectives_and_double_cold(tmp_path,fixed_corpus,monkeypatch):
    sdk_init=OpenAI.__init__
    upstream=public_operator_path(tmp_path/'SCRIPTED-upstream',monkeypatch,topic=True)
    monkeypatch.setattr(OpenAI,'__init__',sdk_init)
    monkeypatch.setattr(driver,'SEED',42)
    monkeypatch.setattr(driver,'LocalObserverBackend',lambda **kw:ScriptedCritic())
    monkeypatch.setattr(driver,'native_sources',lambda old,source:{'original_source':old,
        'SCRIPTED':'historical scientist provenance only; actual runtime source fully cold checked'})
    # All public upstream plan/physical audits are actual software operations;
    # their corpus/HTTP/critic inputs remain SCRIPTED, including source origin.
    old=driver.read(upstream['run']/'plan.json'); provider=old['designer']; scientist=old['scientist']
    current={'request':None,'kind':None}; production=[]; calibration=[]; feedback=[]
    session_counts={}
    class Session(ScriptedSession):
        calls=[]
        def get(self,url,**kw):
            if url.endswith('/version'): return Response({'version':'SCRIPTED'})
            if url.endswith('/ps'):
                return Response({'models':[{'name':p['model'],'digest':p['model_digest'],
                    'context_length':65536 if p is provider else 40960} for p in (provider,scientist)]})
            assert url.endswith('/tags')
            return Response({'models':[{'name':p['model'],'digest':p['model_digest']} for p in (provider,scientist)]})
        def post(self,url,**kw):
            payload=json.loads(kw['data'])
            if url.endswith('/generate'):
                assert payload['prompt']==''
                return Response({'model':payload['model'],'done':True,'done_reason':'load',
                    'response':'','eval_count':0,'prompt_eval_count':0})
            assert url.endswith('/chat')
            if 'TRUSTED INTERFACE CALIBRATION TASK' in payload['messages'][0]['content']:
                calibration.append(payload)
                body=super().post(url,**kw).json(); body['model']=provider['model']
                return Response(body)
            req=current['request']; assert current['kind']=='proposal'
            key=digest(req); i=session_counts.get(key,0); session_counts[key]=i+1
            original=next(n['parameters']['code_artifact']['source'] for n in req['parent_system']['mechanisms']
                          if n['mechanism_id']=='world.selection')
            actions=[{'tool':'plan','objective_reasoning':'SCRIPTED explicit loss arithmetic software test',
                'design_intent':'Exercise actual invalid-code feedback, correction and authored wiring; not discovery'},
                {'tool':'write_file','filename':'code/world.selection.py',
                 'content':"def step(context):\n    return SCRIPTED_undefined_name\n"},
                {'tool':'read_file','filename':'archive/steps/01.json','limit':30000},
                {'tool':'write_file','filename':'code/world.selection.py','content':original},
                transparent_office(req),{'tool':'finish','rationale':'SCRIPTED submitted system, not optimization evidence'}]
            action=actions[i]; production.append(payload)
            if i==2: feedback.append('SCRIPTED_undefined_name' in json.dumps(payload))
            return Response({'model':provider['model'],'done':True,'done_reason':'stop',
                'prompt_eval_count':120,'eval_count':12,
                'message':{'role':'assistant','content':json.dumps(function_data(action)),
                    **({'thinking':'SCRIPTED separate reasoning'} if payload['think'] else {})}})
    monkeypatch.setattr('requests.Session',Session)
    def child(argv,**kw):
        intent=driver.read(Path(argv[-2])); current.update(request=intent['request'],kind=intent['kind'])
        bounded.worker(argv[-2],argv[-1])
        return {'timed_out':False,'returncode':0}
    monkeypatch.setattr(bounded,'run_bounded',child)
    root=tmp_path/'free-study'
    driver.prepare(SimpleNamespace(output=root,origin_run=upstream['run'],origin_source=driver.ROOT,
        audit_one=upstream['audit_one'],audit_two=upstream['audit_two']))
    driver.run(root)
    p=driver.require_plan(root); end=driver.read(root/'terminal.json')
    assert end['status']=='closed' and end['consumed_slots']==6 and end['observations']==8
    assert len(session_counts)==6 and set(session_counts.values())=={6}
    assert feedback==[True]*6 and len(production)==36 and calibration
    assert p['losses']['throughput']==old['losses']['throughput']
    assert p['losses']['content-utility']==old['losses']['content-utility']
    assert set(p['losses'])==set(driver.OBJECTIVES)
    assert p['additional_measurements']['optimization_loss_changed']
    assert p['additional_measurements']['historical_losses_unchanged']
    for objective in p['objectives']:
        c=driver.campaign(root,p,objective,driver.read(root/'developer-reference-context.json'))
        assert len(c.state['records'])==2 and not c.state['pending']
        for r in c.state['records']:
            assert r['request']['design_space']['world_law_scope']==driver.SCOPE
            assert len(r['request']['developer_reference_context']['summary'])==2
            for observation in r['observations']:
                assert observation['status']=='complete'
                assert observation['metadata']['measurements'][0]['metrics'][METRIC]['status']=='measured'
                assert len(observation['candidate']['mechanisms'])>len(r['request']['parent_system']['mechanisms'])
    for client in upstream['clients']: client.close()
    monkeypatch.setattr(OpenAI,'__init__',lambda *a,**kw:pytest.fail('cold reader cannot construct SDK'))
    before=(len(production),len(calibration))
    with tempfile.TemporaryDirectory(prefix='topic-free-software-cold-') as external:
        paths=[Path(external)/f'audit-{i}.json' for i in (1,2)]
        for path in paths: auditor.worker(root,path)
        audits=[driver.read(path) for path in paths]
        assert paths[0].read_bytes()==paths[1].read_bytes()
        pair=[costs(root,p,a) for a in audits]; assert pair[0]==pair[1]
        assert len(audits[0]['worlds'])==8 and all(w['status']=='complete' for w in audits[0]['worlds'])
        assert not audits[0]['held_out_evaluation'] and not audits[0]['publication_ready']
        driver.save(tmp_path/'audit-retained.json',{k:v for k,v in audits[0].items() if k!='content_sha256'})
        driver.save(tmp_path/'cost-retained.json',{k:v for k,v in pair[0].items() if k!='content_sha256'})
    assert before==(len(production),len(calibration))
    with pytest.raises(ValueError,match='no redispatch'): driver.run(root)
    write_json_atomic(tmp_path/'verification.json',{
        'schema':'scienceutopia.native-topic-free-public-software.v1','source_commit':p['source_commit'],
        'classification':'SCRIPTED-HTTP-corpus-critics-and-child-supervision-not-real-model-optimization',
        'public_prepare_run_calibration_execute_replay_and_double_cold':True,
        'native_worlds':8,'upstream_software_worlds':2,'own_slots':6,'objectives':p['objectives'],
        'scripted_proposal_POSTs':len(production),'scripted_calibration_POSTs':len(calibration),
        'every_actual_next_feedback_prompt_contains_error':all(feedback),
        'scientist_installed_sdk_requests_including_upstream':len(upstream['scientist_requests']),
        'audit_content_sha256':audits[0]['content_sha256'],'cost_content_sha256':pair[0]['content_sha256'],
        'new_real_model_calls':0,'deadline_supervision_tested':False,
        'automatic_invention_or_improvement_claimed':False,'publication_ready':False},sort_keys=True)
