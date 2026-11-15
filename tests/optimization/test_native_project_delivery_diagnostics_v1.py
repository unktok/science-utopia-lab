"""SCRIPTED commands / real pure validators, not native world or model results."""
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from tests.optimization.test_native_authoring_ir import request,IMAGE,BINDING,edit
from utopia.optimization.native_post_edit_feedback_v1 import NativePostEditFeedback
from utopia.optimization.native_project_delivery_diagnostics_v1 import diagnose,SCOPE,BANK_OPTION
from utopia.system.code_mechanisms import CodeExecution,sha
from utopia.system.design_patch import clone,digest
from utopia.system.native_legacy_topic_controls import legacy_topic_control
from utopia.system.native_legacy_topic_planning import eligible_topics
from utopia.system.native_planning_controls import planning_controls

PRODUCER='developer-catalog-agenda'


def case():
    doc=legacy_topic_control(planning_controls(IMAGE,seed=61001)['assignment-reserve21-no-review-all'],
        candidate_policy='core-plus-related').to_dict()
    producer=next(n for n in doc['mechanisms'] if n['mechanism_id']==PRODUCER)
    actor={'id':'SCRIPTED-native-author','can_author':True,'is_active':True,
        'project_end_year':0,'expertise':['logic_in_cs','mathematical_software','distributed_systems']}
    ctx={'period':1,'phase':1,'random_seed':42,'parameters':clone(producer['parameters']),
        'state':{},'inputs':{'world':[{'payload':{'ecosystem':{'agents':[actor]}}}]}}
    catalog=ctx['parameters']['catalog'];directions={d['topic']:d for d in catalog['directions']}
    assert 'artificial_intelligence' not in eligible_topics(actor,catalog=catalog)
    assignment={'actor_id':actor['id'],'direction':clone(directions['artificial_intelligence']),
        'detailed_focus':'SCRIPTED','reason':'SCRIPTED two-hop invalid topic',
        'project_start_year':1,'project_end_year':directions['artificial_intelligence']['years']}
    command={'schema':'native-domain-command-v1','command_id':'SCRIPTED-project',
        'actor_id':'$mechanism','action':'native.legacy-topic-project.v1','payload':{'assignment':assignment}}
    out={'outputs':{'agenda':[],'commands':[{'payload':command}]},'state':{}}
    return doc,ctx,out


def test_canonical_duration_does_not_make_two_hop_topic_eligible_and_inputs_stay_literal():
    doc,ctx,out=case();before=deepcopy((doc,ctx,out));r=diagnose(doc,PRODUCER,out,ctx);row,=r['rows']
    assert row['status']=='incompatible-recorded-project-fields'
    assert row['error_type']=='GraphRuntimeError' and 'native duration' in row['error_excerpt']
    assert row['field_checks']=={'topic_eligible_for_recorded_actor':False,
        'canonical_catalog_content_equal':True,'native_start_and_duration_equal':True}
    assert r['recorded_context_sha256']==digest(ctx) and r['document_sha256']==digest(doc)
    assert (doc,ctx,out)==before and not r['changes_validity']
    assert r['new_source_executions']==r['new_native_worlds']==r['new_model_calls']==0


def test_eligible_fields_pass_without_claiming_authorization_or_real_native_success():
    doc,ctx,out=case();actor=ctx['inputs']['world'][0]['payload']['ecosystem']['agents'][0]
    topic=eligible_topics(actor,catalog=ctx['parameters']['catalog'])[0]
    direction=next(d for d in ctx['parameters']['catalog']['directions'] if d['topic']==topic)
    command=out['outputs']['commands'][0]['payload'];assignment=command['payload']['assignment']
    assignment['direction']=clone(direction);assignment['project_end_year']=direction['years']
    command['actor_id']='SCRIPTED-not-authorized'  # Intentionally outside this field-only diagnostic.
    r=diagnose(doc,PRODUCER,out,ctx)
    assert r['rows'][0]['status']=='compatible-recorded-project-fields'
    assert 'No command authorization' in r['scope']


@pytest.mark.parametrize('change',['fan-in','delay','unknown-port','missing-context','unknown-action',
    'malformed-action','malformed-frame','ambiguous-producer','missing-frames'])
def test_unassessed_conditions_never_gain_a_fields_pass(change):
    doc,ctx,out=case();edge=next(e for e in doc['connections'] if e['source_mechanism']==PRODUCER and e['source_port']=='commands')
    if change=='fan-in':doc['connections'].append({**edge,'source_mechanism':'SCRIPTED-other'})
    elif change=='delay':edge['latency']=1
    elif change=='unknown-port':edge['target_port']='not-commands'
    elif change=='missing-context':ctx['inputs']={}
    elif change=='unknown-action':out['outputs']['commands'][0]['payload']['action']='new-unassessed-action'
    elif change=='malformed-action':out['outputs']['commands'][0]['payload']['action']=[]
    elif change=='malformed-frame':out['outputs']['commands']=[None]
    elif change=='ambiguous-producer':doc['mechanisms'].append(clone(next(n for n in doc['mechanisms'] if n['mechanism_id']==PRODUCER)))
    else:out['outputs'].pop('commands')
    r=diagnose(doc,PRODUCER,out,ctx)
    assert all(v['status']=='not-assessed' for v in r['rows'])


def test_bounded_return_reports_omitted_commands_not_sample_as_complete():
    doc,ctx,out=case();out['outputs']['commands']*=20;r=diagnose(doc,PRODUCER,out,ctx,limit=2)
    assert len(r['rows'])==2 and r['omitted_rows']==18


@pytest.mark.parametrize('assignment',[None,[],{}, {'actor_id':[]},
    {'actor_id':'SCRIPTED-native-author','direction':None}])
def test_malformed_untrusted_assignment_is_diagnostic_not_a_prompt_build_exception(assignment):
    doc,ctx,out=case();out['outputs']['commands'][0]['payload']['payload']['assignment']=assignment
    row,=diagnose(doc,PRODUCER,out,ctx)['rows']
    assert row['status']=='incompatible-recorded-project-fields'


def test_optional_feedback_survives_reads_finish_and_cold_replay_without_repair(tmp_path):
    from tests.optimization.test_native_bounded_author_context_v45 import Model
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator,replay_staged_generation
    doc,ctx,out=case();artifact=next(n for n in doc['mechanisms'] if n['mechanism_id']==PRODUCER)['parameters']['code_artifact']
    row={'schema':'scienceutopia.native-code-input.v1','binding':{'source_commit':'SCRIPTED',
        'system_fingerprint':'SCRIPTED','run_id':'SCRIPTED'},'artifact':clone(artifact),'context':ctx,
        'result':out,'receipt':{'image_id':IMAGE,'artifact_sha256':sha(artifact),
        'context_sha256':sha(ctx),'result_sha256':sha(out)}}
    row['bundle_sha256']=sha(row)
    bank={'schema':'scienceutopia.native-component-fixtures.v1','nodes':[PRODUCER],
        'records':[row],'origins':[{'bundle_sha256':row['bundle_sha256'],'node_id':PRODUCER,
            'year':1,'reference':'open-seed'}],BANK_OPTION:SCOPE,'scope':'SCRIPTED; no actual model or world'}
    bank['content_sha256']=digest(bank);calls=[]
    def execute(a,c):
        calls.append((clone(a),clone(c)))
        return CodeExecution(clone(out),{'image_id':IMAGE,'artifact_sha256':sha(a),
            'context_sha256':sha(c),'result_sha256':sha(out)})
    feedback=NativePostEditFeedback(bank,executor=SimpleNamespace(image_id=IMAGE,timeout=15.,execute=execute),source_commit='c'*40)
    body=request();body['parent_system']=doc;body=feedback.declare_request(body)
    source=artifact['source']+'\n# SCRIPTED literal edit; never executed by test\n'
    model=Model([{'tool':'plan','objective_reasoning':'SCRIPTED','design_intent':'SCRIPTED'},
        {'tool':'write_file','filename':'code/'+PRODUCER+'.py','content':source},
        {'tool':'read_file','filename':'system.json'},
        {'tool':'edit','operations':[edit(identity='world.selection',path='/parameters/control_rule',value='accept-all')]},
        {'tool':'finish'}])
    gen=StagedVocabularyGenerator(model,tmp_path,image_id=IMAGE,provider_binding=BINDING,
        max_steps=16,max_tokens=8192,conversation_profile=BOUNDED_AUTHORING,edit_feedback=feedback)
    definition=gen(body)
    for i in (2,3,4):
        obs=json.loads(model.calls[i]['prompt'])['persistent_component_diagnostics']['components'][0]['current_artifact_observed_suite']['results'][0]
        assert obs['status']=='returned'
        assert obs['project_delivery_diagnostic']['rows'][0]['status']=='incompatible-recorded-project-fields'
        assert obs['project_diagnostic_document_applicability']=='same-current-document'
    assert definition is not None and len(calls)==1
    assert replay_staged_generation(next(tmp_path.glob('generation-*')))==definition and len(calls)==1
    assert not feedback.contract['project_delivery_diagnostics']['veto_on_finish']


def test_unknown_opt_in_scope_is_rejected_not_implicitly_enabled(tmp_path):
    from tests.optimization.test_native_post_edit_feedback_v1 import fixture,finish
    gen,model,body,calls=fixture(tmp_path,[finish()]);bank=clone(gen.edit_feedback.bank)
    assert 'project_delivery_diagnostics' not in gen.edit_feedback.contract
    bank[BANK_OPTION]='unrecognized';bank['content_sha256']=digest({k:v for k,v in bank.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='unknown explicit project-delivery'):
        NativePostEditFeedback(bank,executor=gen.edit_feedback.executor,source_commit='c'*40)
    assert not calls and not model.calls
