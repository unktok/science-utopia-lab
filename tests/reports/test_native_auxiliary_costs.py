"""SCRIPTED closed-audit/raw auxiliary-cost projection QA; no model calls."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.reports import native_auxiliary_costs as costs
from utopia.system.design_patch import digest


def hashed(value):
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))


def transport(prompt=10, completion=2):
    body = {'model': 'SCRIPTED-designer', 'done': True, 'done_reason': 'stop',
        'prompt_eval_count': prompt, 'eval_count': completion, 'total_duration': 100,
        'load_duration': 10, 'prompt_eval_duration': 40, 'eval_duration': 50}
    return {'request_payload': {'SCRIPTED': True}, 'http_status': 200,
        'response_payload': body, 'raw_http_response': json.dumps(body),
        'prompt_tokens': prompt, 'completion_tokens': completion, 'elapsed_seconds': .1}


def fixture(tmp_path):
    root = tmp_path / 'raw'; root.mkdir()
    p = hashed({'schema': costs.STUDY, 'source_commit': 'a' * 40,
        'classification': 'SCRIPTED-auxiliary-cost-QA-only', 'generations': 1,
        'designer': {'model': 'SCRIPTED-designer', 'model_digest': 'b' * 64},
        'scientist': {'model': 'SCRIPTED-scientist', 'model_digest': 'c' * 64},
        'campaign_bindings': {'run-00': {'throughput:parameters': {}, 'throughput:random': {}}},
        'assignments': {'throughput:parameters': {'method': 'parameters'}, 'throughput:random': {'method': 'random'}}})
    steps = [{'status': 'rejected', 'model_reply': {'transport': transport()}, 'model_call_seconds': .2}, None]
    proof = {'request_sha256': 'd' * 64, 'started_records': [{'step': 0}, {'step': 1}],
        'completed_records': steps, 'counts': {'dispatch_intents': 2, 'recorded_POST_attempts': 1, 'known_HTTP_responses': 1}}
    cell = root / ('search/run-00/arms/throughput--parameters/authoring/generation-' + proof['request_sha256'])
    for start, step in zip(proof['started_records'], steps):
        save(cell / f"step-{start['step']:02d}.started.json", start)
        if step is not None: save(cell / f"step-{start['step']:02d}.completed.json", step)
    cert = hashed({'schema': 'scienceutopia.designer-interface-certificate.v16',
        'plan': {'source_commit': p['source_commit'], 'provider': p['designer']},
        'records': [{'intent': {'id': 'SCRIPTED-control-' + str(i)}, 'ok': True,
                     'elapsed_seconds': .3, 'transport': transport()} for i in range(2)]})
    save(root / 'search/run-00/preflight/certificate.json', cert)
    loads = []
    for role in ('designer', 'scientist'):
        path = root / ('SCRIPTED-' + role + '-load.json')
        intent = hashed({'schema': 'scienceutopia.explicit-local-role-load.v38.intent',
            'provider': p[role], 'role': role, 'request_payload': {'prompt': '', 'SCRIPTED': True}})
        save(path.with_suffix('.started.json'), intent)
        body = {'model': p[role]['model'], 'done': True, 'done_reason': 'load'}
        record = hashed({'schema': 'scienceutopia.explicit-local-role-load.v38', 'intent_sha256': intent['content_sha256'],
            'provider': p[role], 'role': role, 'http_status': 200, 'raw_http_response': json.dumps(body),
            'response_payload': body, 'elapsed_seconds': 2., 'valid_empty_prompt_load': True})
        save(path, record); loads.append({'load': str(path), 'proof': {'status': 'completed-load'}})
    a = hashed({'schema': costs.STUDY + '.audit', 'source_commit': p['source_commit'],
        'plan_sha256': p['content_sha256'], 'source_proofs': {'status': 'verified-exact-source-closure',
            'files': {'SCRIPTED': 'not-real-source-proof'}},
        'input_inventory': costs._inventory(root), 'raw_inventory_unchanged': True,
        'writer': {'ended': {'status': 'exited', 'exit_code': 0}}, 'new_model_calls': 0, 'new_code_executions': 0,
        'runs': {'run-00': {'throughput:parameters': {'designer': {'proofs': [proof]}}, 'throughput:random': {}}},
        'certificates': {'run-00': {'certificate_sha256': cert['content_sha256'], 'controls': 2}},
        'designer_loads': loads})
    return root, p, a


def analyze(root, p, a): return costs.analyze(root, p, a, expected_source=p['source_commit'])


def test_all_intents_failures_calibration_and_loads_count_once_with_explicit_unknowns(tmp_path):
    root, p, a = fixture(tmp_path); before = deepcopy(a); inventory = costs._inventory(root)
    r = analyze(root, p, a)
    assert a == before and costs._inventory(root) == inventory and r == analyze(root, p, a)
    assert len(r['events']) == 6  # two proposal intents, two controls, two empty-prompt loads.
    proposal = r['groups']['designer-proposal']; calibration = r['groups']['designer-calibration']
    assert proposal['request_intents'] == 2 and proposal['recorded_POST_attempt'] == 1
    assert proposal['status_counts'] == {'rejected': 1, 'interrupted-response-unknown': 1}
    m = proposal['measurements']['native_prompt_eval_count']
    assert m['recorded_sum'] == 10 and m['known_records'] == 1 and m['missing_records'] == 1
    assert calibration['measurements']['native_prompt_eval_count']['recorded_sum'] == 20
    for role in ('scientist', 'designer'):
        group = r['groups']['role-load-' + role]
        assert group['measurements']['native_prompt_eval_count']['recorded_sum'] is None
        assert group['measurements']['caller_elapsed_seconds']['recorded_sum'] == 2.
        assert group['measurements']['transport_seconds']['recorded_sum'] is None  # Not separately measured.
    random = r['proposal_runs']['run-00']['throughput:random']
    assert random['author_absent_by_design'] and random['request_intents'] == 0
    assert random['measurements']['native_prompt_eval_count']['recorded_sum'] == 0
    assert not r['unknown_usage_imputed'] and not r['token_aliases_or_nested_durations_added']


def test_reported_alias_disagreement_and_large_integer_nanoseconds_are_preserved_not_repaired():
    t = transport(); t['prompt_tokens'] = 99
    t['response_payload']['total_duration'] = 9007199254740993
    t['raw_http_response'] = json.dumps(t['response_payload'])
    event = costs.event('SCRIPTED', 'one', t, model='SCRIPTED-designer', status='invalid-response')
    r = costs.summarize([event])['measurements']
    assert r['native_prompt_eval_count']['recorded_sum'] == 10
    assert r['transport_prompt_tokens']['recorded_sum'] == 99
    assert r['provider_total_duration_ns']['recorded_sum'] == 9007199254740993


@pytest.mark.parametrize('bad', [True, -1, 1.5, '4', []])
def test_invalid_counts_are_not_zero_or_silently_coerced(bad):
    t = transport(prompt=bad)
    event = costs.event('SCRIPTED', 'one', t, model='SCRIPTED-designer', status='invalid-response')
    m = costs.summarize([event])['measurements']['native_prompt_eval_count']
    assert m['recorded_sum'] is None and m['invalid_records'] == 1 and m['missing_records'] == 0


def test_returned_invalid_json_count_cannot_mutate_the_original_audit_transport():
    t = transport(prompt=[]); values = costs.cost_values(t, model='SCRIPTED-designer')
    values['native_prompt_eval_count'].append('changed')
    assert t['response_payload']['prompt_eval_count'] == [] and t['prompt_tokens'] == []


def test_http_and_parsed_body_or_foreign_model_disagreement_is_rejected():
    for field, value in [('prompt_eval_count', 999), ('model', 'FOREIGN')]:
        t = transport(); t['response_payload'][field] = value
        if field == 'model': t['raw_http_response'] = json.dumps(t['response_payload'])
        with pytest.raises(ValueError): costs.cost_values(t, model='SCRIPTED-designer')


@pytest.mark.parametrize('mutate', [
    lambda a: a['writer']['ended'].update(status='running'),
    lambda a: a['writer']['ended'].update(exit_code=False),
    lambda a: a.update(source_commit='d' * 40),
    lambda a: a['certificates']['run-00'].update(certificate_sha256='WRONG'),
    lambda a: a['runs']['run-00']['throughput:parameters']['designer']['proofs'][0]['counts'].update(recorded_POST_attempts=2),
    lambda a: a['designer_loads'].append(deepcopy(a['designer_loads'][0])),
    lambda a: a['runs']['run-00']['throughput:parameters']['designer']['proofs'].clear(),
    lambda a: a['runs']['run-00']['throughput:parameters']['designer']['proofs'][0]['completed_records'][0].update(model_call_seconds=999.),
    lambda a: a['designer_loads'][0]['proof'].update(status='made-up-status'),
])
def test_rehashed_invalid_source_terminal_counts_and_identity_do_not_become_cost_evidence(tmp_path, mutate):
    root, p, a = fixture(tmp_path); mutate(a); hashed(a)
    with pytest.raises(ValueError): analyze(root, p, a)


def test_missing_load_completion_remains_unknown_without_fabricated_response_or_usage(tmp_path):
    root, p, a = fixture(tmp_path); path = Path(a['designer_loads'][0]['load'])
    path.rename(root / 'SCRIPTED-original-completion-kept.json')
    a['designer_loads'][0]['proof']['status'] = 'dispatched-response-unknown'
    a['input_inventory'] = costs._inventory(root); hashed(a)
    r = analyze(root, p, a); e = r['role_loads'][0]
    assert not e['completion_record_available'] and not e['recorded_POST_attempt']
    assert all(v is None for v in e['values'].values())


def test_explicit_reported_load_zero_is_different_from_unreported_usage(tmp_path):
    root, p, a = fixture(tmp_path); path = Path(a['designer_loads'][0]['load'])
    record = json.loads(path.read_text()); record['response_payload'].update(prompt_eval_count=0, eval_count=0)
    record['raw_http_response'] = json.dumps(record['response_payload']); hashed(record); save(path, record)
    a['input_inventory'] = costs._inventory(root); hashed(a)
    r = analyze(root, p, a)['groups']['role-load-designer']['measurements']['native_prompt_eval_count']
    assert r['recorded_sum'] == 0 and r['known_records'] == 1 and r['missing_records'] == 0


def test_identical_record_content_at_distinct_physical_loads_is_not_deduplicated(tmp_path):
    root, p, a = fixture(tmp_path); original = Path(a['designer_loads'][0]['load'])
    copied = root / 'SCRIPTED-second-designer-load.json'
    copied.write_bytes(original.read_bytes())
    copied.with_suffix('.started.json').write_bytes(original.with_suffix('.started.json').read_bytes())
    a['designer_loads'].append({'load': str(copied), 'proof': {'status': 'completed-load'}})
    a['input_inventory'] = costs._inventory(root); hashed(a)
    r = analyze(root, p, a)['groups']['role-load-designer']
    assert r['request_intents'] == 2 and r['measurements']['caller_elapsed_seconds']['recorded_sum'] == 4.


def test_resealed_duplicate_calibration_id_is_not_an_additional_physical_control(tmp_path):
    root, p, a = fixture(tmp_path); path = root / 'search/run-00/preflight/certificate.json'
    c = json.loads(path.read_text()); c['records'][1]['intent']['id'] = c['records'][0]['intent']['id']
    hashed(c); save(path, c)
    a['certificates']['run-00']['certificate_sha256'] = c['content_sha256']
    a['input_inventory'] = costs._inventory(root); hashed(a)
    with pytest.raises(ValueError, match='duplicate physical calibration'): analyze(root, p, a)


def test_raw_mutation_during_projection_is_detected_without_repair_or_cleanup(tmp_path, monkeypatch):
    root, p, a = fixture(tmp_path); original = costs.summarize; writes = []
    def changing(events):
        if not writes:
            save(root / 'SCRIPTED-unexpected.json', {'changed': True}); writes.append(True)
        return original(events)
    monkeypatch.setattr(costs, 'summarize', changing)
    with pytest.raises(ValueError, match='changed during auxiliary'): analyze(root, p, a)
    assert (root / 'SCRIPTED-unexpected.json').exists()


def test_changed_raw_inventory_or_unbound_load_is_rejected(tmp_path):
    root, p, a = fixture(tmp_path); (root / 'extra.json').write_text('{}')
    with pytest.raises(ValueError, match='inventory'): analyze(root, p, a)
    a['input_inventory'] = costs._inventory(root)
    a['designer_loads'][0]['load'] = str(tmp_path / 'outside.json'); hashed(a)
    with pytest.raises(ValueError, match='outside'): analyze(root, p, a)


def test_cli_no_overwrites_raw_mutation_or_hidden_execution_and_adapter_provenance_retained(tmp_path):
    root, p, a = fixture(tmp_path); a['analysis_adapter'] = {'schema': 'SCRIPTED-adapter'}; hashed(a)
    plan = tmp_path / 'plan.json'; proof = tmp_path / 'audit.json'
    save(plan, p); save(proof, a); output = tmp_path / 'result.json'
    args = ['--run', str(root), '--plan', str(plan), '--audit', str(proof), '--expected-source', p['source_commit'], '--output', str(output)]
    assert costs.main(args) == 0
    r = json.loads(output.read_text()); assert r['input_audit_analysis_adapter'] == a['analysis_adapter']
    before = output.read_bytes()
    with pytest.raises(SystemExit): costs.main(args)
    assert output.read_bytes() == before
    with pytest.raises(SystemExit): costs.main(args[:-1] + [str(root / 'not-permitted.json')])
    assert r['new_model_calls'] == r['new_code_executions'] == 0
