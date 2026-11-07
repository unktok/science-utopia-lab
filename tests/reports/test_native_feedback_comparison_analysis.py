"""Pure analysis controls; all toy costs below are explicitly software QA."""
from copy import deepcopy
import json

import pytest

from scripts import analyze_native_feedback_comparison as audit
from tests.reports.test_native_feedback_comparison_driver import plan
from utopia.system.design_patch import digest


def fixtures():
    p = plan(); runs = {}
    for i, arm in enumerate(p['arm_order']):
        runs[arm] = {'observations': [{'generation': g, 'status': 'complete',
            'loss': -1., 'system_fingerprint': 'SCRIPTED-only', 'checkpoint_sha256': None,
            'metrics': {}, 'lineage': {}, 'cross_scores': {loss['id']: -(i+1.) for loss in p['losses'].values()}}
            for g in range(2)], 'designer': {'proofs': ['not repeated'], 'dispatch_intents': 4},
            **{k: 0 for k in ('physical_native_worlds','physical_world_directory_count',
                'physical_researcher_responses','physical_wire_requests',
                'recorded_code_executions_including_partial','completed_researcher_model_call_seconds')}}
    baseline = {'cross_scores': {'throughput': -10., 'efficiency': 0.},
        'physical_proof': {'not': 'repeated'}, 'row': {'row_id': 'shared-baseline',
        'status': 'complete', 'cross_scores': {'throughput': -10., 'efficiency': 0.}}}
    return p, runs, baseline


def test_all_ties_failures_paths_cross_objective_selection_and_baseline_retained():
    p, runs, baseline = fixtures()
    bad = runs['throughput-loss']['observations'][0]
    bad.update(status='technical-failure', loss=None,
        cross_scores={loss['id']: None for loss in p['losses'].values()})
    before = deepcopy(runs)
    result = audit.summarize(p, runs, baseline)
    assert result['content_sha256'] == digest({k:v for k,v in result.items() if k!='content_sha256'})
    assert len(result['candidate_rows']) == 8 and runs == before
    assert result['candidate_rows'][0]['loss'] is None
    assert result['arms']['throughput-loss']['best_so_far'] == [None, -1.]
    assert result['pooled_loss_only_best']['throughput'] == {
        'loss': -10., 'all_tied_row_ids': ['shared-baseline']}
    # A throughput-generating candidate remains eligible for efficiency loss.
    for r in runs['throughput-technical-only']['observations']:
        r['cross_scores'][p['losses']['efficiency']['id']] = -99.
    result = audit.summarize(p, runs, baseline)
    assert result['pooled_loss_only_best']['efficiency']['all_tied_row_ids'] == [
        'throughput-technical-only:g0', 'throughput-technical-only:g1']
    assert 'physical_proof' not in result['baseline']
    assert result['arm_label_is_selection_veto'] is False


def test_no_complete_observation_cannot_get_an_invented_numeric_best():
    rows = [{'row_id':'a','status':'technical-failure','cross_scores':{'loss':None}}]
    assert audit.best(rows, 'loss') == {'loss':None,'all_tied_row_ids':[]}


def test_terminal_writer_and_saved_progress_reconstructed_from_all_slots(tmp_path):
    p, runs, _ = fixtures()
    started = {'schema': audit.driver.SCHEMA+'.writer','source_commit':p['source_commit'],
        'action':'run','status':'started','pid':17,'argv':['SCRIPTED'],
        'environment':{'PYTHONHASHSEED':'42'},'started_utc':'2026-11-07T00:00:00+00:00'}
    ended = {**started,'status':'exited','exit_code':0,'ended_utc':'2026-11-07T00:00:01+00:00'}
    progress = {'schema':audit.driver.SCHEMA+'.progress','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'], 'arms':{arm:{'slots':[
            {k:r[k] for k in ('generation','status','loss')} for r in run['observations']],
            'pending':False} for arm,run in runs.items()},'consumed_candidate_slots':8,
        'terminal':True,'status':'complete'}
    progress['content_sha256'] = digest(progress)
    for name, value in [('writer.started.json',started),('writer.ended.json',ended),('progress.json',progress)]:
        (tmp_path/name).write_text(json.dumps(value))
    assert audit._terminal(tmp_path,p,runs)['progress']==progress
    progress['arms']['throughput-loss']['slots'][0]['loss']=-123.
    (tmp_path/'progress.json').write_text(json.dumps(progress))
    with pytest.raises(ValueError,match='every actual attempt'):
        audit._terminal(tmp_path,p,runs)


def test_source_proof_fails_on_invalid_source_and_local_byte_changes(tmp_path, monkeypatch):
    with pytest.raises(ValueError,match='exact comparison source'):
        audit.source_proofs('not a commit')
    names = ['utopia/example.py','scripts/run_native_feedback_comparison.py',
        'scripts/analyze_native_feedback_comparison.py',audit.driver.PROTOCOL,
        *['research/objectives/losses/'+identity+'.json' for identity in audit.driver.LOSSES.values()]]
    bodies = {name:b'# SCRIPTED source proof fixture\n' for name in names}
    for name, body in bodies.items():
        path = tmp_path/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(body)
    def git(args, **kwargs):
        if args[1]=='ls-tree':
            return 'utopia/example.py\n'
        return bodies[args[-1].split(':',1)[1]]
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    monkeypatch.setattr(audit.subprocess,'check_output',git)
    assert len(audit.source_proofs('a'*40)['files'])==len(names)
    (tmp_path/'utopia/example.py').write_bytes(b'# changed runtime\n')
    with pytest.raises(ValueError,match='replay-critical source differs'):
        audit.source_proofs('a'*40)


def test_cli_rejects_existing_or_inside_raw_outputs_before_analysis(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'analyze',lambda *a,**kw:pytest.fail('must reject before reading/dispatch'))
    existing=tmp_path/'saved.json';existing.write_text('original')
    for output in (existing,tmp_path/'raw'/'result.json'):
        with pytest.raises(SystemExit):
            audit.main(['--run',str(tmp_path/'raw'),'--expected-source','a'*40,'--output',str(output)])
    assert existing.read_text()=='original'
