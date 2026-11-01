"""Scripted receipt/journal reconstruction QA, NOT actual native-world results.

No generated Python executes, and no LLM/container is called. Fixture execution
outputs below are explicitly supplied by the test, not computed discoveries.
"""
from copy import deepcopy
import json
from types import MethodType, SimpleNamespace

import pytest

from scripts.analyze_native_joint_objectives_v5 import EXHAUSTED, JournalReplay, ReceiptExecutor, audit_proposals
from tests.optimization.test_native_world import loss_spec
from utopia.models.models import VLLMServerModel
from utopia.models.response_cache import CompletedResponseCache
from utopia.system.code_mechanisms import CodeExecution, sha
from utopia.system import SystemSpec
from utopia.system.native_kernel import CONTROL_ARTIFACT, legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot


@pytest.fixture
def authored_fixture(tmp_path, monkeypatch):
    from openai.types.chat import ChatCompletion
    from utopia.optimization import native_code_trace
    from utopia.optimization.native_region_proposer_v5 import NativeRegionIRProposer
    from utopia.system.design_patch import apply_design_patch

    arm = 'scripted-fixture-not-native-results'
    image = 'sha256:' + '1' * 64
    parent = selection_source_slot(legacy_world_system(seed=42), image_id=image)
    node = next(n for n in parent.mechanisms if n.mechanism_id == 'world.selection')
    world_state = {'schema': 'scienceutopia.native-world-observation.v1', 'year': 1,
                   'conferences': {'conferences': []}}
    def value(payload):
        return {'payload': payload, 'actor_ids': [], 'artifact_ids': [],
                'source_mechanism': 'world.review', 'emitted_period': 1}
    context = {'period': 1, 'phase': 140, 'random_seed': 42, 'state': {}, 'parameters': {},
               'inputs': {'observations': [value(world_state)], 'after': [value({'year': 1})]}}
    result = {'outputs': {'next': [{'payload': {'year': 1}}], 'world': [{'payload': world_state}],
                          'decisions': [{'payload': {'empty_cycle': True}}]}, 'state': {'cycles': 1}}
    native_record = {'schema': 'scienceutopia.native-code-input.v1',
        'binding': {'source_commit': 'QA', 'system_fingerprint': parent.fingerprint, 'run_id': 'baseline'},
        'artifact': node.parameters['code_artifact'], 'context': context, 'result': result,
        'receipt': {'artifact_sha256': sha(node.parameters['code_artifact']), 'context_sha256': sha(context),
                    'result_sha256': sha(result), 'image_id': image}}
    native_record['bundle_sha256'] = sha(native_record)
    provider = lambda *args: [deepcopy(native_record)]
    monkeypatch.setattr(native_code_trace, 'parent_context_provider', lambda *args, **kwargs: provider)
    protocol = {'schema': 'scienceutopia.native-joint-objectives.v5', 'seed': 42,
                'max_technical_drafts': 3, 'max_tokens': 4096}
    world = {'source_commit': 'QA', 'model': 'scripted-model', 'model_digest': 'scripted-revision',
             'corpus_sha256': 'scripted-corpus', 'image_id': image}
    controller = SimpleNamespace(initial=parent, loss_spec=loss_spec(), binding={'fixture': True},
        state={'records': [{'suggestion': {'candidate': parent.to_dict(), 'proposal_index': 0},
                            'observation': {'status': 'complete', 'loss': -1, 'metadata': {'measurements': []}}}]})
    binding = {'protocol': protocol['schema'], 'cell': parent.fingerprint,
        'model': world['model'], 'model_revision': world['model_digest'],
        'corpus_sha256': world['corpus_sha256'], 'seed': 42,
        'science_config': {'source_commit': 'QA', 'objective_campaign_binding': controller.binding, 'protocol': protocol}}
    model = VLLMServerModel.__new__(VLLMServerModel)
    model.model_name, model.run_seed, model.server_backend = 'scripted-model', 42, 'ollama'
    model.thinking_override, model.max_tokens_override = False, 4096
    journal = tmp_path / 'arms' / arm / 'designer-replies.sqlite'
    model.response_cache = CompletedResponseCache(journal, binding=binding)
    valid = {'rationale': 'Scripted fixture, no algorithm executed', 'nodes': [{
        'id': 'tribunal', 'inputs': {
            'evidence': {'sources': ['boundary:world'], 'required': True, 'schema': {'type': 'object'}},
            'trigger': {'sources': ['boundary:next'], 'required': True, 'schema': {'type': 'object'}}},
        'outputs': {
            'ready': {'channel': 'signal', 'artifact_type': CONTROL_ARTIFACT, 'required': True, 'schema': {'type': 'object'}},
            'verdicts': {'channel': 'decision', 'artifact_type': 'native-paper-decision', 'required': True, 'schema': {'type': 'object'}}},
        'parameters': {}, 'python_code': 'def step(context):\n    return None\n', 'state_schema': {'type': 'object'}}],
        'exports': {'after': ['node:tribunal:ready'], 'decisions': ['node:tribunal:verdicts']}}
    invalid = deepcopy(valid)
    invalid['exports'].pop('after')

    class ScriptedExecutor:
        image_id = image
        def execute(self, artifact, context):
            result = {'outputs': {'ready': [{'payload': {'year': context['period']}}],
                                   'verdicts': [{'payload': {'empty_cycle': True}}]}, 'state': {'cycles': 1}}
            return CodeExecution(result, {'artifact_sha256': sha(artifact), 'context_sha256': sha(context),
                'result_sha256': sha(result), 'image_id': image, 'wall_seconds': 0.0})

    def create(*, success=True):
        queue = [invalid, valid] if success else [invalid, invalid, invalid]
        def callback(**payload):
            content = queue.pop(0)
            return ChatCompletion.model_validate({'id': 'scripted-QA', 'object': 'chat.completion', 'created': 0,
                'model': 'scripted-model', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': json.dumps(content)},
                                                       'finish_reason': 'stop'}]})
        def completion(_model, *, seed_ctx=None, **payload):
            return model.response_cache.create(callback, seed_ctx=seed_ctx, **payload)
        model._create_completion = MethodType(completion, model)
        proposer = NativeRegionIRProposer(model, ScriptedExecutor(), removed_nodes=['world.selection'],
            context_provider=provider, receipts=tmp_path / 'arms' / arm / 'design-proposals', instructions='Scripted QA')
        try:
            if success:
                patch = proposer(parent, controller.state['records'], 1, controller.loss_spec)
                child = apply_design_patch(parent, patch)
                controller.state['records'].append({'patch': patch, 'suggestion': {'candidate': child.to_dict()},
                    'observation': {'status': 'complete', 'loss': -1, 'metadata': {'measurements': []}}})
            else:
                with pytest.raises(ValueError, match='bounded region'):
                    proposer(parent, controller.state['records'], 1, controller.loss_spec)
        finally:
            model.response_cache.close()
        return SimpleNamespace(run=tmp_path, arm=arm, controller=controller, protocol=protocol,
                               world=world, journal=journal, binding=binding)
    return create


def test_exact_prompt_cache_repair_probe_and_native_candidate_reconstruct_without_execution(authored_fixture):
    f = authored_fixture()
    report = audit_proposals(f.arm, f.controller, run=f.run, protocol=f.protocol, world=f.world)
    assert report[0]['draft_count'] == 2
    assert report[0]['status'] == 'isolated-native-region-passed-not-native-evaluated'
    assert report[0]['candidate_fingerprint'] == SystemSpec.from_dict(f.controller.state['records'][1]['suggestion']['candidate']).fingerprint


def test_preserved_exhaustion_is_not_an_observed_native_loss(authored_fixture):
    f = authored_fixture(success=False)
    report = audit_proposals(f.arm, f.controller, run=f.run, protocol=f.protocol, world=f.world)
    assert report[0]['draft_count'] == 3
    assert report[0]['status'] == 'invalid-technical-manifest'
    assert report[0]['candidate_fingerprint'] is None
    assert len(f.controller.state['records']) == 1


def test_model_reply_or_candidate_tamper_is_detected(authored_fixture):
    f = authored_fixture()
    f.controller.state['records'][1]['patch']['rationale'] = 'unrecorded host rewrite'
    with pytest.raises(ValueError, match='patch differs'):
        audit_proposals(f.arm, f.controller, run=f.run, protocol=f.protocol, world=f.world)


def test_designer_binding_tamper_fails_before_request_replay(authored_fixture):
    f = authored_fixture()
    bad = deepcopy(f.binding)
    bad['seed'] = 43
    with pytest.raises(ValueError, match='journal binding'):
        JournalReplay(f.journal, binding=bad, world=f.world, protocol=f.protocol)


@pytest.mark.parametrize('technical_failure', [False, True])
def test_terminal_classification_and_physical_vs_logical_counts(tmp_path, monkeypatch, technical_failure):
    """Summary-control fixture only; native evidence validators are mocked."""
    from scripts import analyze_native_joint_objectives_v5 as analysis
    from scripts import audit_native_objective_v5 as audit_module
    from utopia.optimization import native_design, native_shared_initial
    from utopia.runtime import checkpointing

    system = legacy_world_system(seed=42)
    losses = [loss_spec(), {**loss_spec(), 'id': 'second', 'version': '2'}]
    arms = ['first', 'second']
    protocol = {'schema': 'scienceutopia.native-joint-objectives.v5', 'arm_ids': arms, 'losses': losses,
                'seed': 42, 'years': 2, 'corpus_years': 4, 'budget_per_arm': 2}
    world = {'protocol': protocol, 'source_commit': 'scripted-summary-fixture', 'runtime_seed_binding': {'fixture': True}}
    plan = {'protocol': protocol, 'world': world, 'initial_fingerprint': system.fingerprint}
    error = {'proposal_index': 1, 'error_type': 'ValueError', 'error': EXHAUSTED,
             'loss': None, 'automatic_redraft': False}
    controllers, audits, expected_arms = {}, {}, {}

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    for i, arm in enumerate(arms):
        count = 1 if technical_failure and i == 0 else 2
        rows, records = [], []
        for index in range(count):
            physical = 'common-baseline' if index == 0 else arm + '-candidate'
            checkpoint = tmp_path / 'runs' / physical / 'checkpoint.gz'
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text('scripted summary fixture, not a checkpoint')
            row = {'system_fingerprint': system.fingerprint, 'loss': -index - 1, 'status': 'complete',
                   'runs': [{'run_id': physical, 'seed': 42, 'checkpoint': str(checkpoint),
                             'checkpoint_sha256': 'scripted-summary-hash'}], 'technical_failures': []}
            rows.append(row)
            records.append({'parent_system': system.to_dict(), 'suggestion': {'candidate': system.to_dict()},
                            'observation': {'loss': -index - 1, 'metadata': {'system_fingerprint': system.fingerprint}}})
        c = SimpleNamespace(initial=system, seeds=[42], state={'records': records})
        c.incumbent = lambda records=records: records[-1]
        controllers[arm] = c
        audits[arm] = {'rows': rows, 'loss_path': [r['loss'] for r in rows]}
        arm_error = error if count == 1 else None
        status = 'terminal-authoring-failure-not-budget-complete' if arm_error else 'declared-budget-complete'
        save(tmp_path / 'arms' / arm / 'campaign/native-design-state.json', {'records': records})
        save(tmp_path / 'arms' / arm / 'completion.json', {'status': status, 'budget': count,
            'declared_budget': 2, 'logical_observations': count, 'terminal_authoring_error': arm_error,
            'source_commit': world['source_commit']})
        expected_arms[arm] = {'logical_observations': count, 'loss_path': audits[arm]['loss_path'],
            'candidate_fingerprints': [system.fingerprint] * count,
            'terminal_authoring_error': arm_error, 'pending': False}
    save(tmp_path / 'plan.json', plan)
    save(tmp_path / 'completion.json', {'status': 'terminal-with-preserved-failures' if technical_failure else 'declared-budget-complete',
        'arms': expected_arms, 'physical_complete_runs': 2 if technical_failure else 3,
        'source_commit': world['source_commit'], 'budget_per_arm': 2})
    if technical_failure:
        save(tmp_path / 'terminal-authoring-errors.json', {'first': error})
    monkeypatch.setattr(native_design, 'NativeDesignCampaign', lambda directory, **kwargs: controllers[directory.parent.name])
    verified = []
    monkeypatch.setattr(native_shared_initial, 'verify_shared_initial', lambda target, source, **kwargs: verified.append((target, source)))
    monkeypatch.setattr(audit_module, 'audit_campaign', lambda directory, *args: deepcopy(audits[directory.name]))
    monkeypatch.setattr(checkpointing, 'read_portable_checkpoint', lambda path: {'portable': {'contract': {'binding': {
        'science_config': {'years': 2, 'corpus_years': 4, 'runtime_seed_binding': {'fixture': True}, 'experiment': protocol}}}}})
    monkeypatch.setattr(analysis, 'audit_proposals', lambda arm, *args, **kwargs: [{
        'proposal_index': 1, 'status': 'invalid-technical-manifest' if technical_failure and arm == 'first'
        else 'isolated-native-region-passed-not-native-evaluated'}])
    report = analysis.analyze(tmp_path)
    assert len(verified) == 1
    assert report['logical_observations'] == (3 if technical_failure else 4)
    assert report['physical_complete_runs'] == (2 if technical_failure else 3)
    assert report['arms']['first']['selected_index'] == (0 if technical_failure else 1)
    assert report['new_inference_requests'] == report['generated_code_executions_during_analysis'] == 0
    # A technical failure is legal, but relabelling it as a finished budget is not.
    terminal = json.loads((tmp_path / 'completion.json').read_text())
    terminal['arms']['first']['loss_path'] = [999]
    save(tmp_path / 'completion.json', terminal)
    with pytest.raises(ValueError, match='trajectory differs'):
        analysis.analyze(tmp_path)
