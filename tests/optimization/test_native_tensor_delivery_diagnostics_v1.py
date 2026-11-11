"""Scripted interfaces and original tensor adapter, not real designer/native results."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from tests.optimization.test_native_authoring_ir import request,edit,IMAGE,BINDING
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_post_edit_feedback_v1 import NativePostEditFeedback
from utopia.optimization.native_tensor_delivery_diagnostics_v1 import diagnose,SCOPE,BANK_OPTION
from utopia.system.code_mechanisms import CodeExecution,sha
from utopia.system.design_patch import digest,clone
from utopia.system.native_open_examples import open_native_system
from utopia.system.tensor_program import tensor_handler


def document():return open_native_system(IMAGE).to_dict()
def node(doc,identity):return next(n for n in doc['mechanisms'] if n['mechanism_id']==identity)
def result(values):return {'outputs':{'features':[{'payload':{'values':values,'records':[]}}]},'state':{}}


def context(doc,values):
    consumer=node(doc,'addressed-selection')
    frame=SimpleNamespace(payload={'values':values,'records':[]},source_mechanism='native-feature-extractor',
        source_port='features',emitted_period=1,actor_ids=(),artifact_ids=())
    return SimpleNamespace(mechanism=SimpleNamespace(parameters=consumer['parameters'],
        outputs=[SimpleNamespace(port_id=p['port_id']) for p in consumer['outputs']]),
        inputs={'features':(frame,)},state={})


@pytest.mark.parametrize('values,expected',[( [],'compatible-recorded-input'),
    ([[4.,3.]],'compatible-recorded-input'),([[4.,3.,1.]],'incompatible-recorded-input')])
def test_observed_shapes_match_actual_native_adapter_including_empty_batches(values,expected):
    doc=document();before=deepcopy(doc);r=diagnose(doc,'native-feature-extractor',result(values));row,=r['rows']
    assert row['status']==expected and row['declared_shape']==[-1,2]
    assert row['observed_shape']==([0,2] if not values else [1,len(values[0])])
    if expected=='incompatible-recorded-input':
        with pytest.raises(ValueError,match='tensor input shape differs: features'):tensor_handler(context(doc,values))
    else:assert tensor_handler(context(doc,values)).events[0].event_type=='native.tensor.executed'
    assert doc==before and not r['changes_validity'] and r['new_tensor_body_executions']==0


def test_diagnostic_does_not_run_body_or_prove_matrix_state_or_world_compatibility(monkeypatch):
    import utopia.system.tensor_program as tensor
    doc=document();consumer=node(doc,'addressed-selection');consumer['parameters']['program']['inputs']['features']=[-1,3]
    # Deliberately keep the two-wide matrix parameters: input compatibility is insufficient.
    def forbidden(*args,**kwargs):raise AssertionError('no tensor body in the diagnostic')
    monkeypatch.setattr(tensor,'execute_tensor_program',forbidden)
    r=diagnose(doc,'native-feature-extractor',result([[4.,3.,1.]]))
    assert r['rows'][0]['status']=='compatible-recorded-input'
    assert r['new_source_executions']==r['new_tensor_body_executions']==0
    with pytest.raises(AssertionError,match='no tensor body'):tensor_handler(context(doc,[[4.,3.,1.]]))


@pytest.mark.parametrize('change',['fan-in','latency','no-frame','two-frames','ambiguous-producer'])
def test_missing_delivery_conditions_never_acquire_a_compatibility_pass(change):
    doc=document();output=result([[4.,3.]])
    edge=next(e for e in doc['connections'] if e['target_mechanism']=='addressed-selection')
    if change=='fan-in':doc['connections'].append({**edge,'source_mechanism':'unobserved-other-producer'})
    elif change=='latency':edge['latency']=1
    elif change=='no-frame':output['outputs']['features']=[]
    elif change=='two-frames':output['outputs']['features']*=2
    else:doc['mechanisms'].append(deepcopy(node(doc,'native-feature-extractor')))
    r=diagnose(doc,'native-feature-extractor',output)
    assert not r['rows'] or all(row['status']=='not-assessed' for row in r['rows'])


def test_literal_renamed_path_shape_and_row_limit_are_respected():
    doc=document();consumer=node(doc,'addressed-selection')
    consumer['parameters']['program']['inputs']={'unusual':[-1,3],'other':[-1,3]}
    consumer['parameters']['input_bindings']={name:{'port':'features','path':'/odd~1key'} for name in ('unusual','other')}
    output=result([]);output['outputs']['features'][0]['payload']={'odd/key':[[1.,2.,3.]]}
    r=diagnose(doc,'native-feature-extractor',output,limit=1)
    assert r['rows'][0]['observed_shape']==[1,3] and r['rows'][0]['status']=='compatible-recorded-input'
    assert r['rows'][0]['literal_binding']['path']=='/odd~1key' and r['omitted_rows']==1


def test_missing_path_and_ragged_input_are_preserved_as_incompatibilities():
    doc=document();output=result([[1.],[2.,3.]])
    assert diagnose(doc,'native-feature-extractor',output)['rows'][0]['status']=='incompatible-recorded-input'
    output['outputs']['features'][0]['payload']={}
    r=diagnose(doc,'native-feature-extractor',output)
    assert r['rows'][0]['status']=='incompatible-recorded-input' and r['rows'][0]['error_type']=='KeyError'


def test_opt_in_shape_failure_survives_reads_and_consumer_changes_are_explicitly_stale(tmp_path):
    from tests.optimization.test_native_bounded_author_context_v45 import Model
    from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator,replay_staged_generation
    doc=document();producer='native-feature-extractor';artifact=node(doc,producer)['parameters']['code_artifact'];records=[];origins=[]
    world={'conferences':{'conferences':[]}}
    for year in range(1,5):
        c={'period':year,'phase':130,'random_seed':42,'parameters':{},'state':{},
            'inputs':{'observations':[{'payload':world}]}}
        original=result([]);original['outputs']['world']=[{'payload':world}]
        r={'schema':'scienceutopia.native-code-input.v1',
            'binding':{'source_commit':'SCRIPTED','system_fingerprint':'SCRIPTED','run_id':'SCRIPTED'},
            'artifact':clone(artifact),'context':c,'result':original,
            'receipt':{'image_id':IMAGE,'artifact_sha256':sha(artifact),'context_sha256':sha(c),'result_sha256':sha(original)}}
        r['bundle_sha256']=sha(r);records.append(r)
        origins.append({'bundle_sha256':r['bundle_sha256'],'node_id':producer,'year':year,'reference':'open-seed'})
    bank={'schema':'scienceutopia.native-component-fixtures.v1','nodes':[producer],'records':records,
        'origins':origins,BANK_OPTION:SCOPE,'scope':'SCRIPTED shaped fixtures, no actual native scientific inputs'}
    bank['content_sha256']=digest(bank);calls=[]
    def execute(a,c):
        calls.append((clone(a),clone(c)));out=result([[4.,3.,1.]]);out['outputs']['world']=[{'payload':world}]
        return CodeExecution(out,{'image_id':IMAGE,'artifact_sha256':sha(a),'context_sha256':sha(c),'result_sha256':sha(out)})
    feedback=NativePostEditFeedback(bank,executor=SimpleNamespace(image_id=IMAGE,timeout=15.,execute=execute),source_commit='c'*40)
    body=request();body['parent_system']=doc;body=feedback.declare_request(body)
    bad=artifact['source'].replace('values.append([score, len(reviews)])','values.append([score, len(reviews), 1.0])')
    assert bad!=artifact['source']
    actions=[{'tool':'plan','objective_reasoning':'SCRIPTED','design_intent':'SCRIPTED'},
        {'tool':'write_file','filename':'code/'+producer+'.py','content':bad},
        {'tool':'read_file','filename':'code/'+producer+'.py'},{'tool':'read_file','filename':'system.json'},
        {'tool':'edit','operations':[edit(identity='addressed-selection',path='/parameters/program/inputs/features',value=[-1,3])]},
        {'tool':'read_file','filename':'system.json'},{'tool':'finish'}]
    model=Model(actions);gen=StagedVocabularyGenerator(model,tmp_path,image_id=IMAGE,provider_binding=BINDING,
        max_steps=16,max_tokens=8192,conversation_profile=BOUNDED_AUTHORING,edit_feedback=feedback)
    definition=gen(body);cell=next(tmp_path.glob('generation-*'))
    for i in (2,3,4):
        row=json.loads(model.calls[i]['prompt'])['persistent_component_diagnostics']['components'][0]
        values=row['current_artifact_observed_suite']['results']
        assert all(v['diagnostic_document_applicability']=='same-current-document' for v in values)
        assert all(v['tensor_delivery_diagnostic']['rows'][0]['status']=='incompatible-recorded-input' for v in values)
        assert 'tensor input shape differs: features' in json.dumps(values)
    for i in (5,6):
        row=json.loads(model.calls[i]['prompt'])['persistent_component_diagnostics']['components'][0]
        assert all(v['diagnostic_document_applicability']=='different-document-not-current-consumer-proof'
            for v in row['current_artifact_observed_suite']['results'])
    assert definition is not None and len(calls)==4 and len(model.calls)==7
    assert replay_staged_generation(cell)==definition and len(calls)==4 and len(model.calls)==7
    assert not feedback.contract['tensor_delivery_diagnostics']['veto_on_finish']


def test_unknown_explicit_scope_rejects_without_implicitly_enabling_or_disabling(tmp_path):
    from tests.optimization.test_native_post_edit_feedback_v1 import fixture,finish
    gen,model,body,calls=fixture(tmp_path,[finish()]);bank=clone(gen.edit_feedback.bank)
    assert 'tensor_delivery_diagnostics' not in gen.edit_feedback.contract
    bank[BANK_OPTION]='unrecognized';bank['content_sha256']=digest({k:v for k,v in bank.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='unknown explicit tensor-delivery'):
        NativePostEditFeedback(bank,executor=gen.edit_feedback.executor,source_commit='c'*40)
    assert not calls and not model.calls
