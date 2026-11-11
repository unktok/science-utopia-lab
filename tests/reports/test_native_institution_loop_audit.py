"""Synthetic audit guards; these are not native-world or LLM results."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from scripts.audit_native_institution_loop_v1 import (
    closed_state, epoch, main, readiness_schedule, request_at, require_age, stopped_state)
from tests.reports.test_native_institution_loop_v1 import plan
from utopia.optimization.native_numeric_designer import save


def test_readiness_schedule_uses_chronological_prefixes_including_other_objectives():
    p = plan(); stages = list(readiness_schedule(p))
    assert len(stages) == 14
    assert sum(s[1] for s in stages) == 5
    assert all(v == 0 for v in stages[0][2].values())
    counts = dict.fromkeys(p['arm_order'], 0)
    for stage, slot in zip(stages[2:], p['schedule']):
        assert stage[2] == counts
        assert stage[3] == slot['arm']
        counts[slot['arm']] += 1
    assert set(counts.values()) == {2}
    # Final T calibration also checks E after E has used both its slots.
    assert stages[-1][3] == 'throughput:parameters'
    assert stages[-1][2]['efficiency:parameters'] == 2
    assert stages[-1][2]['throughput:parameters'] == 1


def test_readiness_rejects_a_schedule_that_rewinds_or_skips_a_generation():
    p = plan(); p['schedule'][3]['generation'] = 1
    with pytest.raises(ValueError, match='chronology'): list(readiness_schedule(p))


def test_request_reconstruction_uses_only_available_prior_feedback():
    records = [{'report':{'strategy_after':{'s':1}}}, {'report':{'strategy_after':{'s':2}}}]
    c = SimpleNamespace(state={'records':records}, _strategy_initial=lambda:{'s':0},
        _request=lambda rows, strategy, count:(deepcopy(rows), strategy, count))
    assert request_at(c, 0) == ([], {'s':0}, 1)
    assert request_at(c, 1) == (records[:1], {'s':1}, 1)
    assert request_at(c, 2) == (records, {'s':2}, 1)
    for count in (-1, 3, True, 1.0):
        with pytest.raises(ValueError, match='prefix'): request_at(c, count)


@pytest.mark.parametrize('value', ['2026-11-11T00:00:00', 'not-time'])
def test_operational_times_must_be_explicit_and_aware(value):
    with pytest.raises(ValueError): epoch(value)


def test_actual_dispatch_age_does_not_get_hidden_by_replaying_at_certificate_time():
    t = epoch('2026-11-11T00:00:00+00:00')
    assert require_age('2026-11-11T00:00:01+00:00', t) == 1
    for time in ('2026-11-10T23:59:59+00:00', '2026-11-12T00:00:01+00:00'):
        with pytest.raises(ValueError, match='stale or future'): require_age(time, t)


def fixture(root):
    p = plan()
    controllers = {arm:SimpleNamespace(state={'pending':None, 'records':[
        {'generation_error':{'message':'SCRIPTED'}, 'observations':[]},
        {'generation_error':None, 'observations':[{'status':'failed','loss':None}]}]})
        for arm in p['arm_order']}
    rows = [{'arm':arm, 'generation':g, 'status':'generation-failure' if g == 0 else 'failed', 'loss':None}
        for arm in p['arm_order'] for g in range(2)]
    save(root/'started.json', {'schema':p['schema'].removesuffix('.plan')+'.start',
        'plan_sha256':p['content_sha256'], 'pid':42, 'started_utc':'2026-11-11T00:00:00+00:00'})
    save(root/'terminal.json', {'schema':p['schema'].removesuffix('.plan')+'.terminal',
        'status':'closed', 'ended_utc':'2026-11-11T01:00:01+00:00'})
    progress = {'schema':p['schema'].removesuffix('.plan')+'.progress', 'stage':'closed', 'active':None,
        'candidate_slots':rows, 'writer_pid':42, 'reference_observations':8, 'evaluation_observations':18,
        'observed_utc':'2026-11-11T01:00:00+00:00'}
    (root/'progress.json').write_text(json.dumps(progress))
    return p, controllers, progress


def test_all_nulls_remain_null_in_a_normally_closed_scientific_record(tmp_path):
    p, cs, progress = fixture(tmp_path)
    proof = closed_state(tmp_path, p, cs, 18)
    assert proof['progress'] == progress
    assert all(r['loss'] is None for r in proof['progress']['candidate_slots'])


@pytest.mark.parametrize('field,value', [('writer_pid',43), ('stage','stopped'),
    ('reference_observations',7), ('evaluation_observations',19), ('candidate_slots',[]),
    ('observed_utc','2026-11-12T01:00:00+00:00')])
def test_closed_display_must_match_actual_slot_and_timing_receipts(tmp_path, field, value):
    p, cs, progress = fixture(tmp_path)
    (tmp_path/'progress.json').write_text(json.dumps({**progress, field:value}))
    with pytest.raises(ValueError, match='progress'): closed_state(tmp_path, p, cs, 18)


def test_closed_display_cannot_cover_a_pending_or_unattempted_candidate(tmp_path):
    p, cs, _ = fixture(tmp_path)
    cs[p['arm_order'][0]].state['pending'] = {'request':'SCRIPTED'}
    with pytest.raises(ValueError, match='incomplete'): closed_state(tmp_path, p, cs, 18)


@pytest.mark.parametrize('status', [None, 'stopped'])
def test_no_audit_dispatch_for_a_running_or_stopped_study(tmp_path, monkeypatch, status):
    if status is not None:
        (tmp_path/'terminal.json').write_text(json.dumps({'status':status}))
    monkeypatch.setattr('sys.argv', ['audit','--run',str(tmp_path),'--output',str(tmp_path/'out.json'),
        '--frozen-source',str(tmp_path)])
    monkeypatch.setattr('subprocess.run',lambda *a,**k:pytest.fail('never start closed audit'))
    with pytest.raises(ValueError): main()


def stopped_fixture(root):
    p, cs, progress = fixture(root)
    final = p['schedule'][-1]
    cs[final['arm']].state['records'].pop()
    progress.update(stage='stopped', active='ValueError', evaluation_observations=0,
        candidate_slots=[r for r in progress['candidate_slots']
            if (r['arm'], r['generation']) != (final['arm'], final['generation'])])
    (root/'progress.json').write_text(json.dumps(progress))
    (root/'terminal.json').unlink()
    save(root/'terminal.json', {'schema':p['schema'].removesuffix('.plan')+'.terminal',
        'status':'stopped', 'error_type':'ValueError',
        'error':'fresh numeric readiness failed; stop without replacement',
        'ended_utc':'2026-11-11T01:00:01+00:00'})
    return p, cs, progress


def test_stopped_prefix_preserves_all_nulls_and_does_not_select_or_close(tmp_path):
    p, cs, progress = stopped_fixture(tmp_path)
    proof = stopped_state(tmp_path, p, cs)
    assert proof['scientific_study_closed'] is False
    assert proof['submitted_slots'] == 11 and proof['unsubmitted_slots'] == 1
    assert proof['next_unsubmitted_slot'] == p['schedule'][-1]
    assert proof['progress'] == progress
    assert all(r['loss'] is None for r in progress['candidate_slots'])
    with pytest.raises(ValueError, match='closure'): closed_state(tmp_path, p, cs, 0)


@pytest.mark.parametrize('name', ['selection.json','evaluation-plan.json','evaluation/unplanned/observation.json'])
def test_stopped_prefix_cannot_hide_poststop_selection_or_evaluation(tmp_path, name):
    p, cs, _ = stopped_fixture(tmp_path)
    target = tmp_path/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('{}')
    with pytest.raises(ValueError, match='unstarted evaluation'): stopped_state(tmp_path, p, cs)


def test_stopped_prefix_rejects_a_pending_dispatch_or_nonprefix(tmp_path):
    p, cs, _ = stopped_fixture(tmp_path)
    cs[p['arm_order'][0]].state['pending'] = {'SCRIPTED':True}
    with pytest.raises(ValueError, match='no pending'): stopped_state(tmp_path, p, cs)
    cs[p['arm_order'][0]].state['pending'] = None
    cs[p['arm_order'][1]].state['records'].pop()
    with pytest.raises(ValueError, match='chronological prefix'): stopped_state(tmp_path, p, cs)


@pytest.mark.parametrize('field,value', [('error','unknown transport'), ('status','closed'),
    ('error_type','CompletionUnknown')])
def test_stopped_prefix_never_accepts_other_failure_classes(tmp_path, field, value):
    p, cs, _ = stopped_fixture(tmp_path)
    end = json.loads((tmp_path/'terminal.json').read_text()); end[field] = value
    end.pop('content_sha256'); (tmp_path/'terminal.json').unlink(); save(tmp_path/'terminal.json', end)
    with pytest.raises(ValueError, match='known numeric-readiness stop'): stopped_state(tmp_path, p, cs)
