"""Opt-in27-world mixed-method SOFTWARE proof, not real model optimization.

Actual public CLI functions, native Docker/installed SDK, role/transport proofs,
bounded editor worker, objective feedback and cold readers run. Corpus, HTTP,
upstream historical provenance and child supervision are explicitly SCRIPTED.
"""
import json
import os
from pathlib import Path
import tempfile
from contextlib import nullcontext
from types import SimpleNamespace

from openai import OpenAI
import pytest

from scripts import run_native_priority_method_comparison_v1 as driver
from scripts import audit_native_priority_method_comparison_v1 as auditor
from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from scripts.reports.native_author_visibility_v1 import prompt_projection
from tests.reports.test_native_legacy_choice_pilot_native_v1 import public_operator_path
from tests.reports.test_native_legacy_choice_native_v1 import ScriptedCritic
from tests.reports.test_native_open_workflow_post_edit_v1 import transparent_office
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization import native_bounded_staged_designer as bounded
from utopia.optimization.native_designer_tools_v25 import function_data
from utopia.system import code_mechanisms
from utopia.system.design_patch import clone, digest
from utopia.optimization.native_objective_view import loss_arithmetic
from utopia.utils.data_utils import write_json_atomic


def prescribed_author_actions(request):
    """Test-only workflow canary: no real inventor or extra native worlds.

    Exercise three reads before an edit and again after it, so the public
    proof cannot bypass the implementation checkpoint with plan/edit/finish.
    """
    reads = [{'tool': 'read_file', 'filename': name} for name in (
        'system.json', 'code/developer-catalog-agenda.py', 'system.json')]
    return [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED loss-aware interface test',
        'design_intent': 'Exercise literal code/wiring and actual-body workflow, not scientific improvement'},
        *clone(reads),
        transparent_office(request, identity='scripted-mixed-office-' + str(request['generation'])),
        *clone(reads),
        {'tool': 'finish', 'rationale': 'SCRIPTED mixed-method software construction'}]


def checked_actual_workflow(payload, *, step, request):
    """Inspect the exact saved/sent SCRIPTED body, not a reconstructed prompt."""
    marker = 'BOUNDED ACTIVE SESSION DATA\n'
    texts = [m['content'].split('\n', 1)[1] for m in payload['messages']
             if m['role'] == 'user' and m.get('content', '').startswith(marker)]
    assert len(texts) == 1, 'one literal active-session backend message required'
    view, _ = json.JSONDecoder().raw_decode(texts[0])
    assert view['active_context_contract']['prospective_context_revision'] == (
        'matched-bounded-author-64k-v2-literal-visibility')
    remaining = view['000_current_turn']['authoring_workflow']['remaining_calls_including_this_one']
    row = prompt_projection(json.dumps(view, ensure_ascii=False, allow_nan=False),
        index=step, maximum=step + remaining, previous_status=None if step == 0 else 'applied',
        expected_loss=loss_arithmetic(request['loss_spec']))
    assert not row['phase_differs_from_actual_body_interpretation'], 'actual body/phase mismatch'
    assert row['displayed_visibility_matches_body_presence'], 'actual visibility flag mismatch'
    assert row['supplied_body_matches_declared_document_hash'] is not False, 'actual body hash mismatch'
    assert row['exact_loss_arithmetic_and_definitions_present'], 'actual objective view differs'
    return row


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_PRIORITY_METHOD_PUBLIC_QA') != '1',
                   reason='explicit clean-source hardware window, no real inference active')
def test_public_prepare_run_all_methods_and_paired_cold_without_new_models(tmp_path, fixed_corpus, monkeypatch):
    public_mixed_operator_path(tmp_path, fixed_corpus, monkeypatch)


def public_mixed_operator_path(tmp_path, fixed_corpus, monkeypatch, *, closure_output=None):
    # Optional persistent external closure is for the follow-on public
    # evaluation proof. Keep both actual cold outputs, never duplicate one
    # retained audit and call those two new independent executions.
    if closure_output is not None:
        closure_output = Path(closure_output).resolve()
        if (closure_output.exists() or closure_output.is_relative_to(driver.ROOT.resolve())
                or closure_output.is_relative_to((tmp_path / 'mixed-study').resolve())):
            raise ValueError('fresh persistent closure outside source/raw required before native QA')
    sdk_init = OpenAI.__init__
    docker_execute = code_mechanisms.DockerCodeExecutor.execute
    upstream = public_operator_path(tmp_path / 'SCRIPTED-upstream', monkeypatch, topic=True)
    monkeypatch.setattr(OpenAI, '__init__', sdk_init)
    monkeypatch.setattr(driver, 'SEED', 42); monkeypatch.setattr(driver.free, 'SEED', 42)
    monkeypatch.setattr(driver, 'LocalObserverBackend', lambda **kw: ScriptedCritic())
    monkeypatch.setattr(driver, 'native_sources', lambda old, source: {'original_source': old,
        'SCRIPTED': 'upstream provenance only; actual current runtime source cold checked'})
    old = driver.read(upstream['run'] / 'plan.json'); provider, scientist = old['designer'], old['scientist']
    current = {'request': None, 'kind': None}; production, calibration, sessions = [], [], {}
    workflows = []

    class Session(ScriptedSession):
        calls = []

        def get(self, url, **kw):
            if url.endswith('/version'): return Response({'version': 'SCRIPTED'})
            if url.endswith('/ps'):
                return Response({'models': [{'name': p['model'], 'digest': p['model_digest'],
                    'context_length': 65536 if p is provider else 40960} for p in (provider, scientist)]})
            assert url.endswith('/tags')
            return Response({'models': [{'name': p['model'], 'digest': p['model_digest']} for p in (provider, scientist)]})

        def post(self, url, **kw):
            payload = json.loads(kw['data'])
            if url.endswith('/generate'):
                assert payload['prompt'] == ''
                return Response({'model': payload['model'], 'done': True, 'done_reason': 'load',
                    'response': '', 'eval_count': 0, 'prompt_eval_count': 0})
            assert url.endswith('/chat')
            if current['kind'] == 'calibration':
                calibration.append(payload); marker = 'nothing is executed or adopted.\n'
                text = next(m['content'] for m in reversed(payload['messages']) if marker in m['content'])
                target = text.rsplit(marker, 1)[1]
                from utopia.optimization.native_designer_preflight import CONTROL_JSON_BEGIN, CONTROL_JSON_END
                if target.startswith(CONTROL_JSON_BEGIN):
                    target = target.removeprefix(CONTROL_JSON_BEGIN).split(CONTROL_JSON_END, 1)[0]
                action, _ = json.JSONDecoder().raw_decode(target.lstrip())
                if set(action) == {'name', 'arguments'}:
                    action = {'tool': action['name'], **action['arguments']}
            else:
                assert current['kind'] == 'proposal'; req = current['request']; key = digest(req)
                i = sessions.get(key, 0); sessions[key] = i + 1
                # Prescribed workflow/source/wiring probe, not autonomous invention.
                actions = prescribed_author_actions(req)
                workflows.append(checked_actual_workflow(payload, step=i, request=req))
                if i >= len(actions):
                    pytest.fail('SCRIPTED author did not finish after its prescribed valid actions')
                action = actions[i]; production.append(payload)
                if req['generation'] == 1:
                    assert len(req['history']) == 1 and req['observations']
                    assert all(row['observation']['loss'] is not None for row in req['observations'])
                    assert req['based_on_observation_id'] in {
                        row['observation']['observation_id'] for row in req['observations']}
            return Response({'model': provider['model'], 'done': True, 'done_reason': 'stop',
                'prompt_eval_count': 120, 'eval_count': 12,
                'message': {'role': 'assistant', 'content': json.dumps(function_data(action)),
                    **({'thinking': 'SCRIPTED separate reasoning'} if payload['think'] else {})}})

    monkeypatch.setattr('requests.Session', Session)

    def child(argv, **kw):
        intent = driver.read(Path(argv[-2])); current.update(request=intent['request'], kind=intent['kind'])
        bounded.worker(argv[-2], argv[-1])
        return {'timed_out': False, 'returncode': 0}

    monkeypatch.setattr(bounded, 'run_bounded', child)
    root = tmp_path / 'mixed-study'
    driver.prepare(SimpleNamespace(output=root, origin_run=upstream['run'], origin_source=driver.ROOT,
        audit_one=upstream['audit_one'], audit_two=upstream['audit_two']))
    driver.run(root); p = driver.require_plan(root); end = driver.read(root / 'terminal.json')
    assert end['status'] == 'closed' and end['consumed_slots'] == 24 and end['observations'] == 27
    assert len(sessions) == 8 and set(sessions.values()) == {9}
    assert len(production) == len(workflows) == 72 and calibration
    boundary = [r for r in workflows if r['step'] == 4 and r['whole_document_actually_supplied']
        and r['compact_document_utf8_bytes'] <= r['declared_literal_byte_cap'] < r['legacy_spaced_document_utf8_bytes']]
    assert len(boundary) >= 2, 'both actual terminal-parent histories must exercise the serializer boundary'
    assert all(r['recorded_phase'] == 'implementation' for r in boundary)
    post_edit = [r for r in workflows if r['step'] == 8 and r['whole_document_actually_supplied']]
    assert post_edit and all(r['recorded_phase'] == 'implementation' for r in post_edit)
    assert len(list((root / 'slots').glob('*.json'))) == 24
    for key in driver.all_history_keys(p):
        if key[0] == driver.METHODS[2]:
            c = driver.campaign(root, p, key, driver.read(root / 'developer-reference-context.json'))
            assert len(c.state['records']) == 2 and not c.state['pending']
            assert all(len(r['draws'][0]['suggestion']['candidate']['mechanisms']) >
                       len(r['request']['parent_system']['mechanisms']) for r in c.state['records'])
        else:
            path = driver.history_directory(root, key)
            state = driver.read(path / 'generation-1/optimizer-after-tell.json')
            assert len(state['optimizer']['observations']) == 3
            assert driver.read(path / 'generation-1/started.json')['suggestion']['phase'] == (
                'initial' if key[0] == driver.METHODS[0] else 'adaptive')
    for client in upstream['clients']: client.close()
    before = _inventory(root); posts = (len(production), len(calibration), len(upstream['scientist_requests']))
    def forbidden(*a, **kw): pytest.fail('cold reader cannot construct a model/client or execute source')
    monkeypatch.setattr(OpenAI, '__init__', forbidden)
    monkeypatch.setattr(code_mechanisms.DockerCodeExecutor, 'execute', forbidden)
    if closure_output is not None: closure_output.mkdir(parents=True)
    closure_context = (tempfile.TemporaryDirectory(prefix='mixed-method-cold-') if closure_output is None
        else nullcontext(str(closure_output)))
    with closure_context as external:
        paths = [Path(external) / f'audit-{i}.json' for i in (1, 2)]
        for path in paths: auditor.worker(root, path)
        assert paths[0].read_bytes() == paths[1].read_bytes()
        proof = driver.read(paths[0]); assert len(proof['worlds']) == 27
        pair = [costs(root, p, driver.read(path)) for path in paths]
        assert pair[0] == pair[1] and len(pair[0]['scientist']['physical_response_caches']) == 27
        assert all(w['loaded']['confirmed'] and w['status'] == 'complete' for w in proof['worlds'])
        assert len({digest(w['physical_proof']['initial_identity']) for w in proof['worlds']}) == 1
        assert len([w for w in proof['worlds'] if w['role'] == 'numeric-own-proposal']) == 16
        assert len([w for w in proof['worlds'] if w['role'] == 'workflow-own-proposal']) == 8
        driver.save(tmp_path / 'audit-retained.json', driver.literal(proof))
        driver.save(tmp_path / 'cost-retained.json', driver.literal(pair[0]))
        if closure_output is not None:
            for i, value in enumerate(pair, 1):
                saved = driver.save(closure_output / ('costs-' + str(i) + '.json'), driver.literal(value))
                assert saved == value
    assert before == _inventory(root) and posts == (len(production), len(calibration), len(upstream['scientist_requests']))
    with pytest.raises(ValueError, match='no redispatch'): driver.run(root)
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': 'scienceutopia.native-priority-method-public-software.v1', 'source_commit': p['source_commit'],
        'classification': 'SCRIPTED-HTTP-corpus-critics-upstream-and-child-supervision-not-scientific-performance',
        'public_prepare_run_and_double_cold': True, 'native_worlds': 27, 'upstream_native_software_worlds': 2,
        'own_slots': 24, 'numeric_own_worlds': 16, 'free_own_worlds': 8,
        'scientist_SDK_POSTs_including_upstream': len(upstream['scientist_requests']),
        'scripted_proposal_POSTs': len(production), 'scripted_calibration_POSTs': len(calibration),
        'scripted_workflow_calls': len(workflows), 'literal_serializer_boundary_checkpoint_calls': len(boundary),
        'post_edit_full_document_checkpoint_calls': len(post_edit),
        'actual_body_phase_mismatches': sum(r['phase_differs_from_actual_body_interpretation'] for r in workflows),
        'audit_content_sha256': proof['content_sha256'], 'cost_content_sha256': pair[0]['content_sha256'],
        'new_real_model_calls': 0, 'deadline_supervision_tested': False,
        'scientific_improvement_demonstrated': False, 'publication_ready': False}, sort_keys=True)
    # The cold guards applied to the complete cold phase above. A caller may
    # now start a distinct SCRIPTED native evaluation, not reuse forbidden
    # constructors or silently keep a mocked source executor for that phase.
    monkeypatch.setattr(OpenAI, '__init__', sdk_init)
    monkeypatch.setattr(code_mechanisms.DockerCodeExecutor, 'execute', docker_execute)
    return {'run': root, 'plan': p, 'closure': closure_output, 'upstream': upstream,
        'sdk_init': sdk_init, 'docker_execute': docker_execute}
