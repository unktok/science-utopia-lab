"""Effect trace primitives with actual checkpoint/ledger APIs and scripted replies."""
import json
from pathlib import Path

import pytest

from scripts.reports import native_institution_effect_trace_v1 as module
from tests.runtime.test_portable_checkpoint_integration import BINDING,seed,fixed_corpus
from tests.system.test_native_science_kernel import make_sim
from utopia.system.native_kernel import NativeScienceKernel,legacy_world_system
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.utils.data_utils import file_sha256


def test_pre_initial_technical_null_does_not_invent_founders_or_completed_boundaries(tmp_path):
    for status in ('pre-response-journal-failure','technical-failure-before-initial-checkpoint'):
        r=module.trace_world(tmp_path,{'identity':'SCRIPTED-null','role':'search:throughput','seed':42,
            'status':'failed','system':legacy_world_system().to_dict(),'physical_proof':{'status':status}},'SCRIPTED-source')
        assert r['annual']==r['code_calls']==[] and r['code_attempts'] is None
        assert not r['causal_mechanism_effect_identified']


def test_original_native_checkpoint_hash_identity_and_exact_annual_read(tmp_path,fixed_corpus,monkeypatch):
    seed();spec=legacy_world_system();monkeypatch.setitem(BINDING,'cell',spec.fingerprint)
    sim,raw=make_sim(tmp_path/'world',native=NativeScienceKernel(spec));sim.run()
    paths=list((tmp_path/'world').rglob('portable_checkpoint_year_1.json.gz'));assert len(paths)==1
    item={'year':1,'checkpoint_sha256':file_sha256(paths[0])}
    actual=module.checkpoint(tmp_path/'world',item,spec.to_dict());expected=read_portable_checkpoint(paths[0])
    # Decoding recreates runtime objects in unrelated portable agent fields;
    # object identity is not canonical checkpoint equality. Compare the actual
    # native data sections used by the reader and verify the bound file bytes.
    assert actual['native_system']==expected['native_system']
    assert actual['ecosystem_data']==expected['ecosystem_data']
    assert actual['year']==expected['year']==1 and actual['phase']==expected['phase']==5
    item['checkpoint_sha256']='0'*64
    with pytest.raises(ValueError,match='checkpoint required'):module.checkpoint(tmp_path/'world',item,spec.to_dict())


def test_trace_uses_real_ledger_reconciliation_and_distinguishes_received_model_input(tmp_path,monkeypatch):
    from utopia.funding.accounting import ResourceLedger
    from types import SimpleNamespace
    from utopia.system.design_patch import clone
    spec=legacy_world_system();actors={f'actor{i}':SimpleNamespace(id=f'actor{i}',can_author=True,resources=30.,
        is_active=True,get_type=lambda:'SCRIPTED') for i in range(5)}
    ledger=ResourceLedger();ledger.start_year(1,actors);ledger.close_year(1,actors)
    state={'ecosystem_data':{'agents':[{'id':a.id,'can_author':True,'resources':a.resources,'is_active':a.is_active} for a in actors.values()]},
        'resource_ledger':ledger.to_dict(),'native_system':{'events':[]}}
    world={'identity':'SCRIPTED-world','role':'search:throughput','seed':42,'status':'complete','system':spec.to_dict(),
        'physical_proof':{'status':'complete','world_conditions_proof':{'actual_author_resources':{k:30. for k in actors}},
            'annual_checkpoints':[{'year':1,'checkpoint_sha256':'SCRIPTED hash'}],
            'context_input_proof':{'delivered_recipient_messages':2,'messages_observed_in_completed_model_inputs':1}}}
    monkeypatch.setattr(module,'checkpoint',lambda *a:clone(state));r=module.trace_world(tmp_path,world,'SCRIPTED-source')
    assert r['annual'][0]['active_founders']==5 and r['annual'][0]['total_founder_resources']==150.
    assert all(a['residual']==0 for a in r['annual'][0]['all_author_ledger'])
    assert r['legacy_raw_envelope_substring_proof']['delivered_recipient_messages']==2
    assert r['legacy_raw_envelope_substring_proof']['messages_observed_in_completed_model_inputs']==1
    assert r['original_model_facing_context_proof'] is None
    assert r['code_attempts'] is None and not r['causal_mechanism_effect_identified']
    state['ecosystem_data']['agents'][0]['resources']=31.
    with pytest.raises(ValueError,match='residual'):module.trace_world(tmp_path,world,'SCRIPTED-source')


@pytest.mark.parametrize('copies',[1,2])
def test_wrapped_code_delegate_is_resolved_and_ambiguous_copies_are_not_greedily_attributed(tmp_path,monkeypatch,copies):
    from dataclasses import replace
    from types import SimpleNamespace
    from tests.optimization.test_native_authoring_ir import parent,ALPHA
    from utopia.system import ScheduleSpec
    from utopia.system.native_process import controlled_activity
    from utopia.system.design_patch import clone,digest
    from utopia.funding.accounting import ResourceLedger
    original=parent();delegate=original.mechanisms[0];wrapper=controlled_activity(delegate)
    spec=replace(original,mechanisms=(wrapper,),schedules=(ScheduleSpec(ALPHA,130),))
    actors={f'a{i}':SimpleNamespace(id=f'a{i}',can_author=True,resources=30.,is_active=True,get_type=lambda:'SCRIPTED') for i in range(5)}
    ledger=ResourceLedger();ledger.start_year(1,actors);ledger.close_year(1,actors)
    context={'period':1,'phase':130,'random_seed':42,'parameters':{'gain':.5},'state':{},'inputs':{}}
    artifact=clone(delegate.parameters['code_artifact']);result={'outputs':{},'state':{}}
    receipt={'image_id':delegate.parameters['runtime_image_id'],'artifact_sha256':digest(artifact),
        'context_sha256':digest(context),'result_sha256':digest(result)}
    row={'schema':'scienceutopia.native-code-input.v1',
        'binding':{'source_commit':'SCRIPTED-source','system_fingerprint':spec.fingerprint,'run_id':tmp_path.name},
        'artifact':artifact,'context':context,'result':result,'receipt':receipt};row['bundle_sha256']=digest(row)
    (tmp_path/'code-contexts.jsonl').write_text((json.dumps(row)+'\n')*copies)
    event={'event_id':'SCRIPTED-code-event','event_type':'generated.code_executed','year':1,'phase':130,
        'provenance':{'mechanism_id':ALPHA},'payload':receipt}
    state={'ecosystem_data':{'agents':[{'id':a.id,'can_author':True,'resources':a.resources,'is_active':a.is_active} for a in actors.values()]},
        'resource_ledger':ledger.to_dict(),'native_system':{'events':[event]}}
    proof={'status':'complete','world_conditions_proof':{'actual_author_resources':{k:30. for k in actors}},
        'annual_checkpoints':[{'year':1,'checkpoint_sha256':'SCRIPTED hash'}],
        'code_proof':{'recorded_executions':copies,'physical_records':[{'index':i,'year':1,
            'bundle_sha256':row['bundle_sha256'],'matching_event_ids':['SCRIPTED-code-event'],
            'attribution':'unique-event-match' if copies==1 else 'ambiguous-physical-attempt'} for i in range(copies)]}}
    world={'identity':'SCRIPTED-world','role':'search:throughput','seed':42,'status':'complete','system':spec.to_dict(),'physical_proof':proof}
    monkeypatch.setattr(module,'checkpoint',lambda *a:clone(state));r=module.trace_world(tmp_path,world,'SCRIPTED-source')
    assert len(r['code_calls'])==copies and r['code_nodes'][0]['declared_wrapper_implementation']=='native.process.activity.v1'
    assert r['code_nodes'][0]['committed_code_events']==1
    assert r['code_nodes'][0]['uniquely_attributed_physical_calls']==(1 if copies==1 else 0)
    assert all(c['committed_node_ids']==[ALPHA] for c in r['code_calls'])
    proof['code_proof']['physical_records'][0]['matching_event_ids']=[]
    with pytest.raises(ValueError,match='attribution differ'):module.trace_world(tmp_path,world,'SCRIPTED-source')


def test_literal_original_formatter_recovers_alpha_aliased_inputs_without_rewriting_raw_or_claiming_actor_identity(tmp_path):
    import sqlite3
    from types import SimpleNamespace
    from utopia.system.native_kernel import institutional_context_prompt
    from utopia.system.design_patch import digest,clone
    messages=[{'message_id':'opaque-source-reference-'+str(i),'source':'SCRIPTED-office','received_year':i+1,
        'emitted_year':i+1,'input_event_ids':['opaque-event-'+str(i)],'payload':{'scientific_value':100+i}} for i in range(2)]
    state={'ecosystem_data':{'agents':[{'id':'SCRIPTED-actor','institutional_context':clone(messages)}]},
        'native_system':{'events':[{'event_type':'native.system.context_delivered','actor_ids':['SCRIPTED-actor'],
            'payload':{'message':clone(m)}} for m in messages]}}
    (tmp_path/'replies').mkdir()
    known={'messages':[{'role':'user','content':'SCRIPTED personality'+institutional_context_prompt(SimpleNamespace(institutional_context=messages[:1]))}]}
    unknown={'messages':[{'role':'user','content':institutional_context_prompt(SimpleNamespace(institutional_context=messages))}]}
    with sqlite3.connect(tmp_path/'replies/responses.sqlite') as db:
        db.execute('CREATE TABLE replies (payload_sha TEXT, outcome TEXT)')
        db.execute('INSERT INTO replies VALUES (?, ?)',(digest(known),'response'))
    (tmp_path/'wire-requests.jsonl').write_text('\n'.join(json.dumps({'year':i+2,'payload':v,'payload_sha256':digest(v)}) for i,v in enumerate((known,unknown))))
    before=clone(state);r=module.rendered_context_proof(tmp_path,state)
    assert r['delivered_recipient_messages']==2 and r['delivered_messages_with_rendered_content_in_completed_inputs']==1
    assert [v['rendered_content_present_in_completed_request'] for v in r['all_stored_messages']]==[True,False]
    assert json.dumps(messages[0],sort_keys=True) not in known['messages'][0]['content']
    assert r['unique_matching_completed_payloads']==1 and state==before
    assert 'not unique actor attribution' in r['scope'] and 'proof of absence when unmatched' in r['scope']


def test_zero_response_partial_world_may_lack_wire_log_but_known_reply_may_not(tmp_path):
    import sqlite3
    (tmp_path/'replies').mkdir()
    with sqlite3.connect(tmp_path/'replies/responses.sqlite') as db:
        db.execute('CREATE TABLE replies (payload_sha TEXT, outcome TEXT)')
    state={'ecosystem_data':{'agents':[]},'native_system':{'events':[]}}
    proof=module.rendered_context_proof(tmp_path,state)
    assert proof['unique_matching_completed_payloads']==0 and proof['all_stored_messages']==[]
    with sqlite3.connect(tmp_path/'replies/responses.sqlite') as db:db.execute("INSERT INTO replies VALUES ('SCRIPTED', 'response')")
    with pytest.raises(ValueError,match='without original wire'):module.rendered_context_proof(tmp_path,state)
