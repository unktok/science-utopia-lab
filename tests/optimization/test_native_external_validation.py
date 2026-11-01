"""Exact-file authoring regressions; no numeric fixture is native evidence."""
from dataclasses import replace

import pytest

from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.optimization.native_external_validation import validate_saved_generated_response
from utopia.optimization.native_manifest_inbox import SCHEMA
from utopia.system.design_patch import digest, make_patch
from utopia.system import SystemSpec
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import write_json_atomic


def fixture(tmp_path):
    parent=replace(legacy_world_system(),initial_state={'seed':42,'integral_float':1.0})
    definition={'base_patch':make_patch(parent,[{'op':'add','path':'/metadata/authored','value':True}]),
        'factors':[{'id':'free-choice','kind':'bernoulli','choices':[
            {'id':k,'operations':[],'provenance':{'kind':'unit-only'}} for k in ('left','right')]}],
        'continuous':[{'id':'numeric','path':'/initial_state/integral_float',
                       'lower':0.,'upper':2.,'mean':0.,'sigma':.5}],
        'provenance':{'kind':'unit-only-not-native-evidence'}}
    request={'parent_system':parent.to_dict(),'loss_spec':loss_spec(),'rng_seed':12345,
             'count':4,'history':[],'based_on_observation_id':None}
    envelope={'schema':SCHEMA,'request':{'authoring_input':request}}
    identity=digest(envelope)
    request_path=tmp_path/'requests'/f'{identity}.json'
    response_path=tmp_path/'responses'/f'{identity}.json'
    response={'request_sha256':identity,'manifest':definition,
              'authoring':{'kind':'external','identity':'unit-only'}}
    write_json_atomic(request_path,envelope)
    write_json_atomic(response_path,response)
    return parent,request,definition,request_path,response_path,response


def test_saved_floats_stay_floats_and_exact_native_design_draws_match(tmp_path):
    parent,request,definition,rq,rp,response=fixture(tmp_path)
    report=validate_saved_generated_response(rq,rp)
    assert report['status']=='passed' and report['parent_fingerprint']==parent.fingerprint
    assert len(report['reachable_assignments'])==2 and len(report['draws'])==4
    mixed=GeneratedMixedDesign(parent,definition,loss_spec=request['loss_spec'],seed=request['rng_seed'])
    expected=mixed.draw(4,version_sha256=report['version_sha256'])
    assert [d['candidate_fingerprint'] for d in report['draws']]==[
        SystemSpec.from_dict(d['suggestion']['candidate']).fingerprint
        for d in expected]
    assert all(v==0 for v in report['calls'].values())
    assert not report['inbox_consumed'] and not report['parent_rebased']
    assert validate_saved_generated_response(rq,rp)==report


def test_wrong_javascript_normalized_parent_is_rejected_not_rebased(tmp_path):
    parent,request,definition,rq,rp,response=fixture(tmp_path)
    normalized=replace(parent,initial_state={'seed':42,'integral_float':1})
    assert normalized.fingerprint!=parent.fingerprint
    response['manifest']['base_patch']['parent_fingerprint']=normalized.fingerprint
    write_json_atomic(rp,response)
    before=rp.read_bytes()
    with pytest.raises(ValueError,match='parent'):
        validate_saved_generated_response(rq,rp)
    assert rp.read_bytes()==before


def test_validator_reads_fresh_saved_response_not_previously_valid_object(tmp_path):
    parent,request,definition,rq,rp,response=fixture(tmp_path)
    valid=validate_saved_generated_response(rq,rp)
    response['manifest']['base_patch']['parent_fingerprint']='0'*64
    write_json_atomic(rp,response)
    with pytest.raises(ValueError,match='parent'):
        validate_saved_generated_response(rq,rp)
    response['manifest']['base_patch']['parent_fingerprint']=parent.fingerprint
    response['authoring']['extra']='changed after old report'
    write_json_atomic(rp,response)
    assert validate_saved_generated_response(rq,rp)['response_file_sha256']!=valid['response_file_sha256']


def test_conditional_support_uses_only_declared_reachable_assignments(tmp_path):
    parent,request,definition,rq,rp,response=fixture(tmp_path)
    response['manifest']['factors'].append({'id':'conditional','kind':'bernoulli','choices':[
        {'id':k,'operations':[],'provenance':{'kind':'unit-only'}} for k in ('one','two')],
        'support':[{'when':{'free-choice':'left'},'allow':['one']},
                   {'when':{'free-choice':'right'},'allow':['one','two']}]})
    write_json_atomic(rp,response)
    assert len(validate_saved_generated_response(rq,rp)['reachable_assignments'])==3


def test_invalid_continuous_draws_report_null_without_repair_or_replacement(tmp_path):
    parent,request,definition,rq,rp,response=fixture(tmp_path)
    response['manifest']['continuous'][0]['path']='/schedules/0/phase'
    write_json_atomic(rp,response)
    report=validate_saved_generated_response(rq,rp)
    assert report['status']=='invalid-drawn-design' and len(report['draws'])==4
    assert all(d['technical_error'] and d['loss'] is None for d in report['draws'])


def test_duplicate_json_keys_and_changed_request_identity_fail(tmp_path):
    parent,request,definition,rq,rp,response=fixture(tmp_path)
    # Generated-artifact writes in this regression deliberately create malformed
    # JSON, not repository source edits or a live inbox mutation.
    rp.write_text('{"request_sha256":"x","request_sha256":"y"}')
    with pytest.raises(ValueError,match='Duplicate'):
        validate_saved_generated_response(rq,rp)
    write_json_atomic(rp,response)
    request['parent_system']['initial_state']['integral_float']=1
    write_json_atomic(rq,{'schema':SCHEMA,'request':{'authoring_input':request}})
    with pytest.raises(ValueError,match='identity'):
        validate_saved_generated_response(rq,rp)


def test_authored_host_side_effect_source_is_data_never_executed(tmp_path):
    parent,request,definition,rq,rp,response=fixture(tmp_path)
    index=next(i for i,n in enumerate(parent.mechanisms) if n.mechanism_id=='world.selection')
    node=parent.to_dict()['mechanisms'][index]
    source="raise RuntimeError('SOURCE_MUST_REMAIN_DATA')\ndef step(context):\n    raise RuntimeError('NEVER_CALL_AUTHORED_STEP')\n"
    node['implementation']='code.python.v1'
    node['parameters']={'runtime_image_id':'sha256:'+'a'*64,'code_artifact':{
        'schema':'scienceutopia.code-mechanism.v1','label':'unexecuted-source-QA','source':source,
        'inputs':{p['port_id']:{'type':'object'} for p in node['inputs']},
        'outputs':{p['port_id']:{'type':'object'} for p in node['outputs']},'state_schema':{'type':'object'}}}
    response['manifest']['base_patch']['operations'].append({'op':'replace','path':f'/mechanisms/{index}','value':node})
    write_json_atomic(rp,response)
    report=validate_saved_generated_response(rq,rp)
    assert report['status']=='passed' and report['calls']['authored_source']==0
    assert all('world.selection' in row['source_utf8_sha256'] for row in report['reachable_assignments'])
