"""Small JSON-only reporting fixtures, not native execution or LLM evidence."""
import json
from types import SimpleNamespace

import pytest

from scripts import run_native_workflow_objective_loop_v1 as driver
from scripts.reports import native_workflow_construction_trace_v1 as module
from tests.reports.test_native_workflow_objective_report_v1 import fixture
from utopia.optimization.native_numeric_designer import save
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import clone, digest


def seal(value):
    value.pop('content_sha256', None); value['content_sha256'] = digest(value)
    return value


def evidence():
    p, a, records = fixture()
    p.update(designer_mode=module.MODE, authoring_scope=driver.OPEN_SCOPE,
        protocol=driver.staged_author.PROTOCOL, optimizer_reference_labels=['R7-original'])
    seal(p); a['plan_sha256'] = p['content_sha256']; a['held_out_evaluation'] = False
    sessions = {}
    for key, r in records.items():
        r['definition'] = {'SCRIPTED': list(key)}
        if r['generation_error'] is not None:
            r['definition'] = {'generation_failure': {'SCRIPTED': list(key)}}
        summary = {'probe_attempts': 0, 'returned': 0, 'raised': 0,
            'veto_on_finish': False, 'new_native_worlds': 0, 'new_model_calls_from_tests': 0}
        response = seal({'request_sha256': r['request_sha256'],
            'status': 'generation-failed' if r['generation_error'] else 'generated',
            'definition': clone(r['definition']), 'component_testing': summary})
        sessions[key] = {'request_sha256': r['request_sha256'],
            'definition': clone(r['definition']), 'response': response, 'steps': []}
    seal(a)
    return p, a, records, sessions


def make_probe_step(index, artifact, status):
    rows = [{'fixture_id': 'SCRIPTED-f'+str(i), 'status': status,
        'error_type': 'ValueError' if status == 'raised' else None,
        'full_error_sha256': digest('SCRIPTED error') if status == 'raised' else None,
        'reply_content_sha256': digest([index, i]),
        'result_sha256': digest({}) if status == 'returned' else None,
        'error_excerpt': 'SCRIPTED error' if status == 'raised' else None}
        for i in range(2)]
    return seal({'step': index, 'status': 'applied', 'transition': {'tool': 'edit',
        'result': {'component_feedback': {'probe_offset': index*2, 'probe_attempts': 2,
            'veto_on_test_failure': False, 'source_repair': False,
            'new_native_worlds': 0, 'new_model_calls': 0,
            'tests': [{'node_id': 'a', 'status': 'tested', 'artifact_sha256': sha(artifact), 'results': rows}]}}}})


def test_all_six_paths_keep_generation_nulls_losses_and_own_selection():
    p, a, records, sessions = evidence()
    report = module.summarize(p, a, records, sessions)
    assert len(report['slots']) == 6 and report['slots'][1]['status'] == 'generation-null'
    assert report['slots'][1]['loss'] is None
    assert report['selection'] == a['selection']
    assert report['construction_counts']['known_probe_attempts'] == 0
    assert not report['interpretation']['staged_method_superiority_claimed']


def test_observed_later_return_does_not_become_repair_native_success_or_final_artifact_pass():
    p, a, records, sessions = evidence(); key = 'throughput', 0
    old, new, untested = [{'source': 'SCRIPTED-'+s} for s in ('raises', 'returns', 'final-untested')]
    candidate = records[key]['observations'][0]['candidate']
    candidate['mechanisms'][0]['parameters']['code_artifact'] = untested
    records[key]['draws'][0]['suggestion']['candidate'] = clone(candidate)
    records[key]['observations'][0].update(status='failed', loss=None)
    w = next(w for w in a['worlds'] if w['identity'] == 'throughput:0')
    w.update(system=clone(candidate), status='failed', scores={o: None for o in p['objectives']})
    seal(a)
    session = sessions[key]
    session['steps'] = [make_probe_step(0, old, 'raised'), make_probe_step(1, new, 'returned')]
    session['response']['component_testing'].update(probe_attempts=4, returned=2, raised=2)
    seal(session['response'])
    report = module.summarize(p, a, records, sessions)
    row = report['slots'][0]; trace = row['construction_trace']
    assert row['status'] == 'failed' and row['loss'] is None
    assert [c['transition'] for c in trace['same_fixture_later_code_comparisons']] == ['raised-to-returned']*2
    assert trace['drawn_candidate_artifact_observations']['components'][0]['test_applicability'] == 'current-artifact-untested'
    assert report['construction_counts'] == {'known_probe_attempts': 4, 'returned': 2,
        'raised': 2, 'sessions_missing_component_summary': 0, 'recorded_model_steps': 2}
    assert not trace['automatic_repair_claimed']


def test_missing_known_null_terminal_stays_unknown_not_zero_probes_or_fabricated_finish():
    p, a, records, sessions = evidence(); key = 'content-utility', 0
    sessions[key]['response'] = None
    report = module.summarize(p, a, records, sessions)
    trace = report['slots'][1]['construction_trace']
    assert trace['terminal_response_missing'] and trace['component_testing'] is None
    assert trace['completed_steps'] is None
    assert report['construction_counts']['sessions_missing_component_summary'] == 1


@pytest.mark.parametrize('case', ['old-mode', 'missing-slot', 'request', 'definition',
    'response-request', 'response-definition', 'response-checksum', 'missing-complete-terminal', 'probe-total', 'veto'])
def test_changed_or_unsupported_records_fail_without_changing_input(case):
    p, a, records, sessions = evidence(); s = sessions['throughput', 0]
    if case == 'old-mode': p['designer_mode'] = driver.OPEN_IR_MODE; seal(p)
    elif case == 'missing-slot': sessions.pop(('throughput', 0))
    elif case == 'request': s['request_sha256'] = '0'*64
    elif case == 'definition': s['definition'] = {}
    elif case == 'response-request': s['response']['request_sha256'] = '0'*64; seal(s['response'])
    elif case == 'response-definition': s['response']['definition'] = {}; seal(s['response'])
    elif case == 'response-checksum': s['response']['status'] = 'changed'
    elif case == 'missing-complete-terminal': s['response'] = None
    elif case == 'probe-total': s['response']['component_testing']['returned'] = 1; seal(s['response'])
    elif case == 'veto': s['response']['component_testing']['veto_on_finish'] = True; seal(s['response'])
    before = digest([p, a, list(records.values()), list(sessions.values())])
    with pytest.raises(ValueError): module.summarize(p, a, records, sessions)
    assert before == digest([p, a, list(records.values()), list(sessions.values())])


def test_real_export_api_reads_six_scripted_paths_twice_and_rejects_raw_mutation(tmp_path):
    p, a, records, sessions = evidence(); raw = tmp_path/'raw'; raw.mkdir()
    save(raw/'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    terminal = save(raw/'terminal.json', {'status': 'closed', 'SCRIPTED': True})
    a['closure']['terminal'] = terminal
    for o in p['objectives']:
        save(raw/'search'/o/'campaign/native-adaptive-state.json',
            {'pending': None, 'records': [records[o, g] for g in range(3)]})
    for key, r in records.items():
        d = raw/'search'/key[0]/'authoring'/('proposal-'+r['request_sha256'])
        binding = save(d/'binding.json', {'request': r['request']})
        save(d/'result.json', {'binding_sha256': binding['content_sha256'], 'definition': r['definition']})
        inner = d/'editor-session/authoring'/('generation-'+r['request_sha256'])
        save(inner/'response.json', {k: v for k, v in sessions[key]['response'].items() if k != 'content_sha256'})
    a.update(raw_inventory_sha256=digest(module._inventory(raw)), raw_files=len(module._inventory(raw)))
    seal(a)
    for name in ('audit-one', 'audit-two'):
        save(tmp_path/(name+'.json'), {k: v for k, v in a.items() if k != 'content_sha256'})
    args = SimpleNamespace(run=raw, audit_one=tmp_path/'audit-one.json',
        audit_two=tmp_path/'audit-two.json', output=tmp_path/'one')
    one = module.export(args); args.output = tmp_path/'two'; two = module.export(args)
    assert one == two
    for name in ('report.json', 'manifest.json', 'slots.csv'):
        assert (tmp_path/'one'/name).read_bytes() == (tmp_path/'two'/name).read_bytes()
    assert len((tmp_path/'one/slots.csv').read_text().splitlines()) == 7
    (raw/'SCRIPTED-mutation.json').write_text('{}')
    args.output = tmp_path/'three'
    with pytest.raises(ValueError, match='raw'): module.export(args)
    assert not args.output.exists()
