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
    assert module.checkpoint(tmp_path/'world',item,spec.to_dict())==read_portable_checkpoint(paths[0])
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
    assert r['received_context_proof']['delivered_recipient_messages']==2
    assert r['received_context_proof']['messages_observed_in_completed_model_inputs']==1
    assert r['code_attempts'] is None and not r['causal_mechanism_effect_identified']
    state['ecosystem_data']['agents'][0]['resources']=31.
    with pytest.raises(ValueError,match='residual'):module.trace_world(tmp_path,world,'SCRIPTED-source')
