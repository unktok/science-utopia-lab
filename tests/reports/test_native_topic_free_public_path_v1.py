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
from tests.reports.native_topic_work_fixture_v1 import work_edit
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization import native_bounded_staged_designer as bounded
from utopia.optimization.native_designer_tools_v25 import function_data
from utopia.optimization.native_resource_cost import METRIC
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_TOPIC_FREE_PUBLIC_QA') != '1',
                   reason='explicit clean-source hardware window, no real inference active')
def test_actual_bounded_editor_feedback_native_objectives_and_double_cold(tmp_path,fixed_corpus,monkeypatch,matched=False):
    sdk_init=OpenAI.__init__
    upstream=public_operator_path(tmp_path/'SCRIPTED-upstream',monkeypatch,topic=True)
    from scripts.reports import native_legacy_topic_pilot_v1 as readout
    with tempfile.TemporaryDirectory(prefix='topic-control-software-readout-') as external:
        outputs=[Path(external)/f'readout-{i}' for i in (1,2)]
        for output in outputs:
            readout.export(SimpleNamespace(run=upstream['run'],frozen_source=driver.ROOT,
                audit_one=upstream['audit_one'],audit_two=upstream['audit_two'],output=output))
        assert (outputs[0]/'report.json').read_bytes()==(outputs[1]/'report.json').read_bytes()
        summary=driver.read(outputs[0]/'report.json')
        assert [w['outside_core_assignments'] for w in summary['worlds']]==[0,16]
        assert summary['new_model_calls']==0 and not summary['automatic_invention']
    monkeypatch.setattr(OpenAI,'__init__',sdk_init)
    from utopia.models import models
    from openai.types.chat import ChatCompletion
    old_model=models.VLLMServerModel; work_payloads=[]
    def model(name,**kw):
        value=old_model(name,**kw); old_reply=value.reply
        def reply(**payload):
            if payload.get('response_format',{}).get('json_schema',{}).get('name')!='native_researcher_work_v15':
                return old_reply(**payload)
            work_payloads.append(payload)
            value.context=value.contexts.get(payload['seed'],getattr(value,'context',None))
            value.requests.append((value.context,payload))
            return ChatCompletion.model_validate({'id':'SCRIPTED-work','object':'chat.completion','created':0,
                'model':name,'choices':[{'index':0,'message':{'role':'assistant',
                'content':json.dumps({'note':'SCRIPTED fixed-scientist institutional response'})},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':5,'completion_tokens':3,'total_tokens':8}})
        value.reply=reply
        return value
    monkeypatch.setattr(models,'VLLMServerModel',model)
    monkeypatch.setattr(driver,'SEED',42)
    if matched:
        monkeypatch.setattr(driver.free,'SEED',42)
    monkeypatch.setattr(driver,'LocalObserverBackend',lambda **kw:ScriptedCritic())
    monkeypatch.setattr(driver,'native_sources',lambda old,source:{'original_source':old,
        'SCRIPTED':'historical scientist provenance only; actual runtime source fully cold checked'})
    # All public upstream plan/physical audits are actual software operations;
    # their corpus/HTTP/critic inputs remain SCRIPTED, including source origin.
    old=driver.read(upstream['run']/'plan.json'); provider=old['designer']; scientist=old['scientist']
    current={'request':None,'kind':None}; production=[]; calibration=[]; feedback=[]
    session_counts={}; submitted_requests={}
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
            if current['kind']=='calibration':
                calibration.append(payload)
                # Bounded planning controls place their exact target after
                # planning data in the USER message, not in the system header.
                marker='nothing is executed or adopted.\n'
                text=next(m['content'] for m in reversed(payload['messages']) if marker in m['content'])
                target=text.rsplit(marker,1)[1]
                from utopia.optimization.native_designer_preflight import CONTROL_JSON_BEGIN,CONTROL_JSON_END
                if target.startswith(CONTROL_JSON_BEGIN):
                    target=target.removeprefix(CONTROL_JSON_BEGIN).split(CONTROL_JSON_END,1)[0]
                action,_=json.JSONDecoder().raw_decode(target.lstrip())
                if set(action)=={'name','arguments'}:
                    action={'tool':action['name'],**action['arguments']}
                return Response({'model':provider['model'],'done':True,'done_reason':'stop',
                    'prompt_eval_count':120,'eval_count':12,
                    'message':{'role':'assistant','content':json.dumps(function_data(action)),
                        **({'thinking':'SCRIPTED calibration reasoning'} if payload['think'] else {})}})
            req=current['request']; assert current['kind']=='proposal'
            key=digest(req); i=session_counts.get(key,0); session_counts[key]=i+1
            submitted_requests[key]=clone(req)
            if matched:
                from utopia.optimization.native_consumer_evidence_v1 import OPTION
                data,_=json.JSONDecoder().raw_decode(payload['messages'][1]['content'].split('BOUNDED ACTIVE SESSION DATA\n',1)[1])
                has_source=OPTION in req['strategy_provenance']
                assert ('literal_native_consumer_source_evidence' in data)==has_source
                if has_source:
                    assert data['literal_native_consumer_source_evidence']==req['strategy_provenance'][OPTION]
                assert [v['reference'] for v in req['developer_reference_context']['summary']]==[
                    'workflow-reference-core-only','workflow-reference-core-plus-related']
                assert 'terminal-consolidation' not in json.dumps(req)
            original=next(n['parameters']['code_artifact']['source'] for n in req['parent_system']['mechanisms']
                          if n['mechanism_id']=='world.selection')
            actions=[{'tool':'plan','objective_reasoning':'SCRIPTED explicit loss arithmetic software test',
                'design_intent':'Exercise actual invalid-code feedback, correction and authored wiring; not discovery'},
                {'tool':'write_file','filename':'code/world.selection.py',
                 'content':"def step(context):\n    return SCRIPTED_undefined_name\n"},
                {'tool':'read_file','filename':'archive/steps/01.json','limit':30000},
                {'tool':'write_file','filename':'code/world.selection.py','content':original},
                transparent_office(req,identity='scripted-feedback-office-'+str(req['generation'])),
                work_edit(req),
                {'tool':'finish','rationale':'SCRIPTED submitted system, not optimization evidence'}]
            if matched and req['generation']==0:
                actions=actions[:4]+actions[-1:]
            action=actions[i]; production.append(payload)
            if i==2:
                # The bad name also occurs in literal source. Require the actual
                # error type, not merely an echo of that source string.
                feedback.append('NameError' in json.dumps(payload))
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
    own,worlds=(8,11) if matched else (6,8)
    assert end['status']=='closed' and end['consumed_slots']==own and end['observations']==worlds
    assert len(session_counts)==own and set(session_counts.values())==({5,7} if matched else {7})
    assert feedback==[True]*own and len(production)==(48 if matched else 42) and calibration
    assert len(work_payloads)>=(16 if matched else 24)
    assert p['losses']['throughput']==old['losses']['throughput']
    assert p['losses']['content-utility']==old['losses']['content-utility']
    assert set(p['losses'])==set(driver.free.OBJECTIVES if matched else driver.OBJECTIVES)
    assert p['additional_measurements']['optimization_loss_changed']
    assert p['additional_measurements']['historical_losses_unchanged']
    sequences=[]
    for key in driver.history_keys(p):
        c=driver.campaign(root,p,key,driver.read(root/'developer-reference-context.json'))
        assert len(c.state['records'])==2 and not c.state['pending']
        for r in c.state['records']:
            assert r['request']['design_space']['world_law_scope']=='fixed-native-effects-institution-workflow-v6'
            assert len(r['request']['developer_reference_context']['summary'])==2
            for observation in r['observations']:
                assert observation['status']=='complete'
                assert observation['metadata']['measurements'][0]['metrics'][METRIC]['status']=='measured'
                work=observation['metadata']['measurements'][0]['native_workflow_interval']['institutional_work_events']
                if matched and r['request']['generation']==0:
                    assert work==0 and len(observation['candidate']['mechanisms'])==len(r['request']['parent_system']['mechanisms'])
                    cell=driver.history_directory(root,key)/'worlds'/(observation['suggestion_id']+'-s42')
                    sequences.append([json.loads(line)['payload'] for line in (cell/'wire-requests.jsonl').read_text().splitlines()])
                else:
                    assert work>=4
                    assert len(observation['candidate']['mechanisms'])>len(r['request']['parent_system']['mechanisms'])
    if matched:
        assert len(sequences)==4 and all(seq==sequences[0] for seq in sequences)
        assert sum('native_consumer_source_evidence' in req['strategy_provenance'] for req in submitted_requests.values())==4
    for client in upstream['clients']: client.close()
    monkeypatch.setattr(OpenAI,'__init__',lambda *a,**kw:pytest.fail('cold reader cannot construct SDK'))
    before=(len(production),len(calibration))
    with tempfile.TemporaryDirectory(prefix='topic-free-software-cold-') as external:
        paths=[Path(external)/f'audit-{i}.json' for i in (1,2)]
        for path in paths: auditor.worker(root,path)
        audits=[driver.read(path) for path in paths]
        assert paths[0].read_bytes()==paths[1].read_bytes()
        pair=[costs(root,p,a) for a in audits]; assert pair[0]==pair[1]
        assert len(audits[0]['worlds'])==worlds and all(w['status']=='complete' for w in audits[0]['worlds'])
        assert not audits[0]['held_out_evaluation'] and not audits[0]['publication_ready']
        driver.save(tmp_path/'audit-retained.json',{k:v for k,v in audits[0].items() if k!='content_sha256'})
        driver.save(tmp_path/'cost-retained.json',{k:v for k,v in pair[0].items() if k!='content_sha256'})
    assert before==(len(production),len(calibration))
    with pytest.raises(ValueError,match='no redispatch'): driver.run(root)
    write_json_atomic(tmp_path/'verification.json',{
        'schema':('scienceutopia.native-consumer-source-public-software.v1' if matched else 'scienceutopia.native-topic-free-public-software.v1'),'source_commit':p['source_commit'],
        'classification':'SCRIPTED-HTTP-corpus-critics-and-child-supervision-not-real-model-optimization',
        'public_prepare_run_calibration_execute_replay_and_double_cold':True,
        'native_worlds':worlds,'upstream_software_worlds':2,'own_slots':own,'objectives':p['objectives'],
        'scripted_proposal_POSTs':len(production),'scripted_calibration_POSTs':len(calibration),
        'every_actual_next_feedback_prompt_contains_error':all(feedback),
        'actual_fixed_scientist_institutional_work_requests':len(work_payloads),
        'scientist_installed_sdk_requests_including_upstream':len(upstream['scientist_requests']),
        'audit_content_sha256':audits[0]['content_sha256'],'cost_content_sha256':pair[0]['content_sha256'],
        'new_real_model_calls':0,'deadline_supervision_tested':False,
        'automatic_invention_or_improvement_claimed':False,'publication_ready':False},sort_keys=True)
