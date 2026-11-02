"""Finite orchestration guards; no numerical fixture is scientific evidence."""
import fcntl
from types import SimpleNamespace

import pytest

from scripts.run_native_objective_redesign_v12 import (
    ROOT, advance_arms, summarize, load_preregistered_losses, main)
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending


def campaign(records=None):
    return SimpleNamespace(binding={'strategies': {'design': {}}},
        state={'records': records or [], 'pending': None})


def test_initial_report_does_not_claim_native_results(tmp_path):
    report = summarize(tmp_path, {'world': {'source_commit':'unit-only',
        'classification':'scripted-fixture-not-native-results'}}, {'a':campaign(),'b':campaign()})
    assert report['status']=='in-progress' and report['physical_reply_count']==0
    assert report['planned_native_world_budget']==6
    assert not report['claims']['live_fixed_Qwen_researchers']


def test_six_failed_authoring_slots_are_terminal_not_six_worlds(tmp_path):
    rows=[{'generation_error':{'loss':None},'draws':[],'observations':[]} for _ in range(3)]
    report=summarize(tmp_path,{'world':{'source_commit':'unit-only',
        'classification':'scripted-fixture-not-native-results'}},{'a':campaign(rows),'b':campaign(rows)})
    assert report['budget_terminal'] and report['status']=='budget-complete-with-failures'
    assert report['technical_failures']==6 and report['complete_native_worlds']==0
    assert report['committed_draws']==0


def test_exact_existing_losses_only():
    paths=[ROOT/'research/objectives/losses'/name for name in (
        'native-joint-v5-throughput.json','native-joint-v5-net-reviewed-utility.json')]
    assert [x['id'] for x in load_preregistered_losses(paths)]==[x.stem for x in paths]
    with pytest.raises(ValueError,match='exact preregistered'):
        load_preregistered_losses(paths[::-1])
    with pytest.raises(ValueError,match='exact preregistered'):
        load_preregistered_losses([paths[0],paths[0]])


def test_classification_is_required(tmp_path):
    with pytest.raises(KeyError,match='classification'):
        summarize(tmp_path,{'world':{'source_commit':'unit-only'}},{'a':campaign()})


def test_single_writer_rejected_before_factory(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.argv',['runner','--output',str(tmp_path),'--data-cache','absent',
        '--inference-lock',str(tmp_path/'http.lock'),'--loss','absent1','--loss','absent2'])
    monkeypatch.setattr('scripts.run_native_objective_redesign_v12.subprocess.check_output',lambda *a,**k:b'')
    monkeypatch.setattr('scripts.run_native_objective_redesign_v12.run',
        lambda args:pytest.fail('writer guard must precede factory'))
    with (tmp_path/'pilot-writer.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(RuntimeError,match='another native objective/redesign writer'):
            main()


def test_pending_arm_does_not_block_other_three_generations(tmp_path):
    class Controller:
        def __init__(self,waiting=False):
            self.state={'records':[]}
            self.calls,self.waiting=0,waiting
        def advance(self,**kw):
            self.calls+=1
            assert kw['count']==1 and set(kw['generators'])=={'design'}
            if self.waiting:
                raise ExternalAuthoringPending('exact',tmp_path/'request',tmp_path/'response')
            self.state['records'].append({})
    a,b=Controller(True),Controller()
    snapshots=[]
    waiting=advance_arms(['a','b'],{'a':a,'b':b},{'a':object(),'b':object()},
        simulation_factory=object(),snapshot=lambda:snapshots.append(1))
    assert set(waiting)=={'a'} and a.calls==1 and b.calls==3
    assert len(snapshots)==4


def test_resume_preserves_completed_and_failed_slots_without_reroll():
    class Controller:
        def __init__(self): self.state={'records':[{'generation_error':{'loss':None}}]}
        def advance(self,**kw): self.state['records'].append({})
    c=Controller()
    advance_arms(['a'],{'a':c},{'a':object()},simulation_factory=object(),snapshot=lambda:None)
    assert len(c.state['records'])==3
    assert c.state['records'][0]['generation_error']['loss'] is None


def test_unexpected_infrastructure_error_is_not_a_loss():
    class Controller:
        state={'records':[]}
        def advance(self,**kw): raise RuntimeError('unit-only unexpected infrastructure')
    with pytest.raises(RuntimeError,match='unexpected infrastructure'):
        advance_arms(['a'],{'a':Controller()},{'a':object()},
            simulation_factory=object(),snapshot=lambda:None)
