"""Opt-in real-container/full-workflow SOFTWARE proof, never model invention.

The HTTP backend and trusted child boundary are explicitly SCRIPTED. Existing
production calibration, role factory, bounded public APIs and cold replays are
not replaced. Authored source executes only through DockerCodeExecutor.
"""
import json
import os
from pathlib import Path

import pytest

from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
from utopia.optimization import native_bounded_staged_designer as bounded
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.optimization.native_designer_tools_v25 import function_data
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_post_edit_feedback_v1 import NativePostEditFeedback
from utopia.optimization.native_staged_author_v15 import replay_staged_generation
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256


def read(path):
    return checked(json.loads(Path(path).read_text()))


def transparent_office(request):
    """Prescribed new literal node and two wires, not autonomous discovery."""
    parent = request['parent_system']
    identity = 'scripted-transparent-observation-office'
    assert all(n['mechanism_id'] != identity for n in parent['mechanisms'])
    edge = next(e for e in parent['connections'] if e['target_mechanism'] == 'world.selection'
        and e['target_port'] == 'observations')
    selection = next(n for n in parent['mechanisms'] if n['mechanism_id'] == 'world.selection')
    port = next(p for p in selection['inputs'] if p['port_id'] == 'observations')
    node = {'mechanism_id': identity, 'family': 'custom', 'implementation': 'code.python.v1',
        'version': 1, 'inputs': [{**port, 'port_id': 'world'}],
        'outputs': [{**port, 'port_id': 'observations'}], 'parameters': {
            'runtime_image_id': selection['parameters']['runtime_image_id'],
            'code_artifact': {'schema': 'scienceutopia.code-mechanism.v1',
                'label': 'SCRIPTED transparent wiring software probe, not invented science',
                'source': "def step(context):\n    return {'outputs': {'observations': context['inputs']['world']}, 'state': {}}\n",
                'inputs': {'world': {'type': 'object'}},
                'outputs': {'observations': {'type': 'object'}}, 'state_schema': {'type': 'object'}}}}
    connections = clone(parent['connections'])
    connections[connections.index(edge)] = {**edge, 'source_mechanism': identity, 'source_port': 'observations'}
    connections.append({**edge, 'target_mechanism': identity, 'target_port': 'world'})
    phase = next(s['phase'] for s in parent['schedules'] if s['mechanism_id'] == 'world.selection') - 1
    return {'tool': 'edit', 'operations': [
        {'op': 'add', 'path': '/mechanisms/-', 'value': node},
        {'op': 'add', 'path': '/schedules/-', 'value': {
            'mechanism_id': identity, 'phase': phase, 'trigger': 'annual'}},
        {'op': 'replace', 'path': '/connections', 'value': connections}]}


@pytest.mark.parametrize('repair', [False, True])
def test_original_workflow_errors_reach_next_outer_prompt_and_do_not_veto_finish(tmp_path, monkeypatch, repair):
    names = ('SCIENCE_UTOPIA_WORKFLOW_BANK', 'SCIENCE_UTOPIA_WORKFLOW_BINDING', 'SCIENCE_UTOPIA_WORKFLOW_RESULT')
    paths = [os.environ.get(name) for name in names]
    if not all(paths):
        pytest.skip('opt-in audited native inputs and real local Docker required')
    bank_path, binding_path, original_result_path = map(Path, paths)
    bank, binding, original = map(read, (bank_path, binding_path, original_result_path))
    assert bank['references'] == ['R7-original'] and len(bank['records']) == 20
    assert set(bank['nodes']) == {'world.selection', 'native-feature-extractor',
        'information-office', 'developer-liquidity-director', 'developer-catalog-agenda'}
    request, provider = clone(binding['request']), clone(binding['provider'])
    parent = SystemSpec.from_dict(request['parent_system'])
    assert {r['binding']['system_fingerprint'] for r in bank['records']} == {parent.fingerprint}
    bad = GeneratedMixedDesign(parent, original['definition'], loss_spec=request['loss_spec'],
        seed=request['rng_seed'], single_draw_blackbox=True).base
    artifact = lambda spec: next(n.parameters['code_artifact'] for n in spec.mechanisms
        if n.mechanism_id == 'world.selection')
    bad_source, original_source = artifact(bad)['source'], artifact(parent)['source']
    assert bad_source != original_source
    # This is the literal recorded T0 failure, not a host-generated approximation.
    assert "'world': [world]" in bad_source and 'range(500)' in bad_source
    source = pinned_revision(Path(__file__).resolve().parents[2])
    feedback = NativePostEditFeedback(bank, executor=DockerCodeExecutor(image=provider['image_id'], timeout=15.),
        source_commit=source, maximum_probes=8)
    request = feedback.declare_request(request)
    write = lambda text: {'tool': 'write_file', 'filename': 'code/world.selection.py', 'content': text}
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED software replay, not optimization',
        'design_intent': 'Exercise original failed source and explicit author-controlled correction'}, write(bad_source)]
    if repair:
        actions.extend([{'tool': 'read_file', 'filename': 'archive/steps/00.json', 'limit': 30000},
            write(original_source), transparent_office(request)])
    actions.append({'tool': 'finish', 'rationale': 'SCRIPTED explicit submission; not an invented improvement'})

    class Session(ScriptedSession):
        calls = []
        production = []
        calibration_count = 0

        def get(self, url, **kwargs):
            if url.endswith('/version'):
                return Response({'version': 'SCRIPTED-not-actual'})
            return Response({'models': [{'name': provider['model'], 'digest': provider['model_digest']}]})

        def post(self, url, **kwargs):
            payload = json.loads(kwargs['data'])
            if 'TRUSTED INTERFACE CALIBRATION TASK' in payload['messages'][0]['content']:
                type(self).calibration_count += 1
                result = super().post(url, **kwargs).json()
                result['model'] = provider['model']
                return Response(result)
            action = actions[len(self.production)]
            self.production.append(payload)
            self.calls.append(payload)
            return Response({'model': provider['model'], 'done': True, 'done_reason': 'stop',
                'prompt_eval_count': 120, 'eval_count': 12,
                'message': {'role': 'assistant', 'content': json.dumps(function_data(action)),
                    **({'thinking': 'SCRIPTED planner, not actual model reasoning'} if payload['think'] else {})}})

    monkeypatch.setattr('requests.Session', Session)
    # Explicitly no model loading, no real inference, and a synchronous child
    # substitute. Wall-clock process supervision is NOT tested by this fixture.
    monkeypatch.setattr('utopia.optimization.native_scientist_load_v38.load_local_role', lambda *a, **kw: None)

    def scripted_child(argv, **kwargs):
        bounded.worker(argv[-2], argv[-1])
        return {'timed_out': False, 'returncode': 0}

    monkeypatch.setattr(bounded, 'run_bounded', scripted_child)
    calibration = bounded.execute(tmp_path/'calibration', kind='calibration', request=request,
        provider=provider, source_commit=source, maximum_posts=40)
    assert calibration['passed']
    definition = bounded.execute(tmp_path/'proposal', kind='proposal', request=request,
        provider=provider, source_commit=source,
        certificate=tmp_path/'calibration/calibration/certificate.json', post_edit_bank=bank)
    assert definition is not None and 'generation_failure' not in definition
    generation = tmp_path/'proposal/authoring'/('generation-'+digest(request))
    steps = [read(p) for p in sorted(generation.glob('step-*.completed.json'))]
    first = steps[0]['transition']['result']['component_feedback']
    assert first['probe_attempts'] == 4
    assert all(r['status'] == 'raised' for r in first['tests'][0]['results'])
    assert all('payload' in r['error_excerpt'] for r in first['tests'][0]['results'])
    assert 'payload' in json.dumps(Session.production[2])
    if repair:
        corrected = steps[2]['transition']['result']['component_feedback']
        assert corrected['probe_attempts'] == 4
        assert all(r['status'] == 'returned' for r in corrected['tests'][0]['results'])
        assert steps[3]['transition']['result']['component_feedback']['tests'][0]['status'] == 'not-configured'
        candidate = GeneratedMixedDesign(parent, definition, loss_spec=request['loss_spec'],
            seed=request['rng_seed'], single_draw_blackbox=True).base
        assert len(candidate.mechanisms) == len(parent.mechanisms)+1
        assert len(candidate.connections) == len(parent.connections)+1
        assert artifact(candidate)['source'] == original_source
    else:
        assert GeneratedMixedDesign(parent, definition, loss_spec=request['loss_spec'],
            seed=request['rng_seed'], single_draw_blackbox=True).base == bad
    count = len(Session.production)
    assert count == len(actions)
    assert replay_staged_generation(generation) == definition
    assert bounded.replay(tmp_path/'proposal') == definition
    assert len(Session.production) == count
    save(tmp_path/'verification.json', {
        'schema': 'scienceutopia.scripted-open-workflow-post-edit-verification.v1',
        'source_commit': source, 'bank_content_sha256': bank['content_sha256'],
        'bank_file_sha256': file_sha256(bank_path), 'original_binding_file_sha256': file_sha256(binding_path),
        'original_result_file_sha256': file_sha256(original_result_path),
        'scripted_repair': repair, 'scripted_calibration_posts': Session.calibration_count,
        'scripted_proposal_posts': count, 'real_component_probes': 8 if repair else 4,
        'full_workflow_domain': request['design_space']['world_law_scope'],
        'definition_sha256': digest(definition), 'public_outer_and_inner_cold_replays_agree': True,
        'failure_veto_on_finish': False, 'new_node_and_wires_compile': repair,
        'new_node_component_executed': False, 'actual_model_calls': 0, 'new_native_worlds': 0,
        'deadline_supervision_tested': False, 'automatic_model_repair_or_improvement_claimed': False})
