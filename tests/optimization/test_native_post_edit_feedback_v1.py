"""Scripted backend/executor repair loop; NOT actual LLM or native outcomes."""
import json
from types import SimpleNamespace

import pytest

from tests.optimization.test_native_authoring_ir import request,ALPHA,edit
from tests.optimization.test_native_search_generator_v14 import Model,IMAGE,BINDING
from utopia.optimization.native_component_lab_v1 import ComponentProbePending
from utopia.optimization.native_post_edit_feedback_v1 import NativePostEditFeedback
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator,replay_staged_generation
from utopia.system.code_mechanisms import CodeExecution,sha
from utopia.system.design_patch import clone,digest

BAD="def step(context):\n    raise TypeError('SCRIPTED-BAD-FLOAT')\n"
GOOD="def step(context):\n    return {'outputs': {}, 'state': {'fixed': True}}\n"


def fixture(tmp_path,actions,*,interrupt=False,model_class=Model,profile='hermes-function-history-v26',large=False):
    body=request();artifact=body['parent_system']['mechanisms'][0]['parameters']['code_artifact']
    records=[];origins=[]
    for year in range(1,5):
        context={'period':year,'phase':130,'random_seed':42,'parameters':{},'state':{},'inputs':{}}
        result={'outputs':{},'state':{}}
        row={'schema':'scienceutopia.native-code-input.v1',
            'binding':{'source_commit':'SCRIPTED','system_fingerprint':'SCRIPTED','run_id':'SCRIPTED'},
            'artifact':clone(artifact),'context':context,'result':result,
            'receipt':{'image_id':IMAGE,'artifact_sha256':sha(artifact),'context_sha256':sha(context),'result_sha256':sha(result)}}
        row['bundle_sha256']=sha(row);records.append(row)
        origins.append({'bundle_sha256':row['bundle_sha256'],'node_id':ALPHA,'year':year,'reference':'open-seed'})
    bank={'schema':'scienceutopia.native-component-fixtures.v1','nodes':[ALPHA],'records':records,
        'origins':origins,'scope':'SCRIPTED; no real native input, model, or container execution'}
    bank['content_sha256']=digest(bank);calls=[]
    def execute(a,c):
        calls.append((clone(a),clone(c)))
        if interrupt:raise KeyboardInterrupt('SCRIPTED interrupted component')
        if 'SCRIPTED-BAD-FLOAT' in a['source']:raise TypeError('SCRIPTED-BAD-FLOAT')
        result={'outputs':{},'state':{'fixed':True,**({'large':'研究者\\n\n' * 12000} if large else {})}}
        return CodeExecution(result,{'image_id':IMAGE,'artifact_sha256':sha(a),'context_sha256':sha(c),'result_sha256':sha(result)})
    feedback=NativePostEditFeedback(bank,executor=SimpleNamespace(image_id=IMAGE,timeout=15.,execute=execute),source_commit='c'*40)
    body=feedback.declare_request(body)
    model=model_class(actions)
    generator=StagedVocabularyGenerator(model,tmp_path,image_id=IMAGE,provider_binding=BINDING,
        max_steps=max(8,len(actions)) if profile!='hermes-function-history-v26' else len(actions),
        max_tokens=8192 if profile!='hermes-function-history-v26' else 2048,
        conversation_profile=profile,edit_feedback=feedback)
    return generator,model,body,calls


def source_action(source):return {'tool':'edit','operations':[edit(path='/parameters/code_artifact/source',value=source)]}
def finish():return {'tool':'finish','rationale':'SCRIPTED explicit submission'}
def directory(root):return next(root.glob('generation-*'))


@pytest.mark.parametrize('declared',[None,{'SCRIPTED':'different contract'},'exact'])
def test_role_factory_requires_exact_readiness_contract_before_constructing_model(tmp_path,monkeypatch,declared):
    from utopia.optimization import native_designer_roles_v38 as roles
    from utopia.optimization import native_designer_preflight as preflight
    gen,model,body,calls=fixture(tmp_path,[finish()])
    declaration=gen.edit_feedback.contract if declared=='exact' else declared
    certificate={'plan':{'request':{'strategy_provenance':{'post_edit_component_contract':declaration}}}}
    seen=[]
    monkeypatch.setattr(roles,'validate_designer_binding',lambda x:None)
    monkeypatch.setattr(preflight,'require_certificate',lambda *a,**kw:certificate)
    monkeypatch.setattr(roles,'LocalRoleBoundDesignerModel',lambda *a,**kw:seen.append(kw) or model)
    kwargs=dict(image_id=IMAGE,provider_binding=BINDING,max_steps=2,max_tokens=2048,
        preflight_certificate='SCRIPTED',edit_feedback=gen.edit_feedback)
    if declared=='exact':
        author=roles.make_local_role_bound_generator(tmp_path/'factory',**kwargs)
        assert len(seen)==1 and author.edit_feedback is gen.edit_feedback
    else:
        with pytest.raises(ValueError,match='readiness request'):
            roles.make_local_role_bound_generator(tmp_path/'factory',**kwargs)
        assert not seen
    assert not calls and not model.calls


def test_component_error_reaches_next_model_call_before_literal_repair_and_cold_replay(tmp_path):
    gen,model,body,calls=fixture(tmp_path,[source_action(BAD),source_action(GOOD),finish()])
    result=gen(body)
    assert len(model.calls)==3 and len(calls)==8
    assert 'ComponentTestDiagnostic' in model.calls[1]['prompt'] and 'SCRIPTED-BAD-FLOAT' in model.calls[1]['prompt']
    assert result['base_patch']['operations'][0]['value']==BAD
    assert result['base_patch']['operations'][1]['value']==GOOD
    assert body['parent_system']==request()['parent_system']
    assert replay_staged_generation(directory(tmp_path))==result
    assert len(model.calls)==3 and len(calls)==8


def test_failed_component_tests_do_not_veto_finish_or_restore_baseline_source(tmp_path):
    gen,model,body,calls=fixture(tmp_path,[source_action(BAD),finish()])
    result=gen(body)
    assert result['base_patch']['operations'][0]['value']==BAD and len(calls)==4
    assert replay_staged_generation(directory(tmp_path))==result


def test_fixed_probe_budget_never_refills_and_later_edits_still_remain_literal(tmp_path):
    last=BAD+'# last literal change\n'
    gen,model,body,calls=fixture(tmp_path,[source_action(BAD),source_action(GOOD),source_action(last),finish()])
    result=gen(body)
    assert len(calls)==8 and result['base_patch']['operations'][-1]['value']==last
    step=json.loads((directory(tmp_path)/'step-02.completed.json').read_text())
    feedback=step['transition']['result']['component_feedback']
    assert feedback['probe_attempts']==0 and feedback['tests'][0]['status']=='not-run-budget-exhausted'
    assert not feedback['veto_on_test_failure']
    assert replay_staged_generation(directory(tmp_path))==result


def test_pending_component_stops_before_any_next_model_call_or_fabricated_terminal(tmp_path):
    gen,model,body,calls=fixture(tmp_path,[source_action(BAD),finish()],interrupt=True)
    with pytest.raises(ComponentProbePending):gen(body)
    assert len(model.calls)==len(calls)==1
    with pytest.raises(ComponentProbePending):gen(body)
    assert len(model.calls)==len(calls)==1
    assert not (directory(tmp_path)/'response.json').exists()
    assert not (directory(tmp_path)/'step-00.completed.json').exists()


def test_rehashed_component_error_cannot_change_saved_next_prompt_or_tool_receipt(tmp_path):
    gen,model,body,calls=fixture(tmp_path,[source_action(BAD),finish()]);gen(body)
    p=directory(tmp_path)/'component-lab/probe-000.result.json';r=json.loads(p.read_text())
    r['error']='CHANGED ERROR';r['content_sha256']=digest({k:v for k,v in r.items() if k!='content_sha256'})
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='changed|differs'):replay_staged_generation(directory(tmp_path))
    assert len(model.calls)==2 and len(calls)==4


def test_malformed_intermediate_node_can_be_repaired_without_crashing_feedback_or_next_prompt(tmp_path):
    bad={'tool':'edit','operations':[{'op':'replace','path':'/mechanisms/0','value':'SCRIPTED malformed node'}]}
    repaired=clone(request()['parent_system']['mechanisms'][0]);repaired['parameters']['code_artifact']['source']=GOOD
    repair={'tool':'edit','operations':[{'op':'replace','path':'/mechanisms/0','value':repaired}]}
    gen,model,body,calls=fixture(tmp_path,[bad,repair,finish()]);result=gen(body)
    assert len(model.calls)==3 and len(calls)==4
    assert result['base_patch']['operations'][0]['value']=='SCRIPTED malformed node'
    assert result['base_patch']['operations'][1]['value']==repaired
    assert replay_staged_generation(directory(tmp_path))==result


def test_real_bounded_wire_shape_keeps_large_probe_bodies_in_exact_step_archives(tmp_path):
    from tests.optimization.test_native_bounded_author_context_v45 import Model as BoundedModel
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    actions=[{'tool':'plan','objective_reasoning':'SCRIPTED','design_intent':'SCRIPTED'},
        source_action(BAD),source_action(GOOD),{'tool':'finish'}]
    gen,model,body,calls=fixture(tmp_path,actions,model_class=BoundedModel,profile=BOUNDED_AUTHORING,large=True)
    result=gen(body)
    assert len(model.calls)==4 and len(calls)==8
    assert 'SCRIPTED-BAD-FLOAT' in model.calls[2]['prompt']
    step=json.loads((directory(tmp_path)/'step-02.completed.json').read_text())
    assert len(json.dumps(step['transition']['result'],ensure_ascii=False).encode())<96000
    assert len(step['component_probe_records'][0]['terminal']['result']['state']['large'])>50000
    assert '研究者' not in model.calls[3]['prompt']
    assert replay_staged_generation(directory(tmp_path))==result
    assert len(model.calls)==4 and len(calls)==8


def test_diagnostic_provenance_is_not_inserted_into_the_sampled_scientific_system(tmp_path):
    from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
    from utopia.system import SystemSpec
    gen,model,body,calls=fixture(tmp_path,[source_action(BAD),source_action(GOOD),finish()]);result=gen(body)
    changed=clone(result)
    changed['provenance']['staged_author']['observed_session']['steps'][0]['errors']=[{'unrelated_audit_id':'CHANGED'}]
    candidates=[]
    for definition in (result,changed):
        mixed=GeneratedMixedDesign(SystemSpec.from_dict(body['parent_system']),definition,
            loss_spec=body['loss_spec'],seed=42,single_draw_blackbox=True)
        candidates.append(mixed.draw(1,version_sha256=digest(definition))[0]['suggestion']['candidate'])
    assert candidates[0]==candidates[1]
    assert 'CHANGED' not in json.dumps(candidates[0])
