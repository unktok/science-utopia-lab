"""Positive whole-analyzer QA, NOT an actual LLM/native research finding.

Real native scientific phases and no-network Docker execute developer-scripted
institution source. Corpus, researcher HTTP and designer HTTP are scripted. The
designer's real request cache is checked by the complete read-only analyzer.
Nothing here calls Ollama or exports a scientific-results artifact.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import MethodType

from openai.types.chat import ChatCompletion

from scripts.analyze_native_joint_objectives_v5 import analyze
from scripts.audit_native_objective_v5 import checkpoint_measurements
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.models.models import VLLMServerModel
from utopia.models.response_cache import CompletedResponseCache
from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_code_trace import RecordingCodeExecutor, parent_context_provider
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.optimization.native_shared_initial import adopt_shared_initial
from utopia.optimization.native_staged_region_proposer import NativeStagedRegionProposer
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_kernel import CONTROL_ARTIFACT, WORLD_ARTIFACT, NativeScienceKernel, legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot


ROOT = Path(__file__).resolve().parents[2]


def test_positive_staged_shared_native_loop_passes_whole_readonly_analyzer(tmp_path, fixed_corpus, monkeypatch):
    from tests.runtime import test_portable_checkpoint_integration as fixture

    run = tmp_path / 'scripted-QA-not-native-research-results'
    run.mkdir()
    losses = [load_loss_spec(ROOT / f'research/objectives/losses/native-joint-v5-{name}.json')
              for name in ('throughput', 'net-reviewed-utility')]
    arm_ids = [loss['id'] for loss in losses]
    protocol = {'schema': 'scienceutopia.native-joint-objectives.v5', 'arm_ids': arm_ids,
        'losses': losses, 'seed': 42, 'years': 6, 'corpus_years': 6, 'budget_per_arm': 2,
        'max_technical_drafts': 3, 'max_tokens': 4096,
        'authoring_format': 'staged-v5', 'designer_thinking': True,
        'classification': 'scripted-fixture-not-native-results'}
    executor = DockerCodeExecutor()
    initial = selection_source_slot(legacy_world_system(seed=42), image_id=executor.image_id)
    world = {'protocol': protocol, 'source_commit': 'QA-scripted-whole-staged-analyzer',
        'model': 'fake-model', 'model_digest': 'fake-revision',
        'corpus_sha256': 'fixed-test-documents-v1', 'image_id': executor.image_id,
        'years': 6, 'corpus_years': 6, 'runtime_seed_binding': {'scripted_QA_hash_seed': 42}}

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, allow_nan=False))

    save(run / 'plan.json', {'protocol': protocol, 'world': world, 'initial_fingerprint': initial.fingerprint})
    physical_worlds = []

    def factory(system, run_seed, run_id):
        seed()
        physical_worlds.append(run_id)
        cell = run / 'runs' / run_id
        binding = deepcopy(fixture.BINDING)
        binding['cell'] = system.fingerprint
        binding['science_config'].update(source_commit=world['source_commit'], years=6,
            corpus_years=6, runtime_seed_binding=world['runtime_seed_binding'],
            thinking_override=False, experiment=protocol)
        monkeypatch.setattr(fixture, 'BINDING', binding)
        recorder = RecordingCodeExecutor(executor, cell / 'code-contexts.jsonl', binding={
            'source_commit': world['source_commit'], 'system_fingerprint': system.fingerprint, 'run_id': run_id})
        sim, _ = make_sim(cell / 'simulation', native=NativeScienceKernel(system, code_executor=recorder))
        sim.llm.response_cache.close()
        sim.llm.response_cache = CompletedResponseCache(cell / 'replies/responses.sqlite', binding=binding)
        sim.output_dir = str(cell / 'simulation/checkpoints/native-design')
        Path(sim.output_dir).mkdir(parents=True)
        return sim

    controllers = [NativeDesignCampaign(run / 'arms' / arm / 'campaign', initial_system=initial,
        loss_spec=loss, seeds=[42], world_binding=world) for arm, loss in zip(arm_ids, losses)]
    baseline = controllers[0].advance(simulation_factory=factory)
    assert baseline['observation']['status'] == 'complete'
    adopt_shared_initial(controllers[1], controllers[0], checkpoint_measurement=checkpoint_measurements)
    assert len(physical_worlds) == 1
    plan = {'rationale': 'Developer-scripted QA structure, not discovered by an LLM', 'nodes': [{
        'id': 'qa_decider', 'inputs': {
            'observations': {'sources': ['boundary:world'], 'required': True, 'schema': {'type': 'object'}},
            'pulse': {'sources': ['boundary:next'], 'required': True, 'schema': {'type': 'object'}}},
        'outputs': {'ready': {'channel': 'signal', 'artifact_type': CONTROL_ARTIFACT, 'required': True, 'schema': {'type': 'object'}},
                    'verdicts': {'channel': 'decision', 'artifact_type': 'native-paper-decision', 'required': True, 'schema': {'type': 'object'}}},
        'parameters': {}, 'state_schema': {'type': 'object'}}],
        'exports': {'after': ['node:qa_decider:ready'], 'decisions': ['node:qa_decider:verdicts']}}
    source_template = """def step(context):
    world = context['inputs']['observations'][0]['payload']
    decisions = []
    for conference in world['conferences']['conferences']:
        for paper in conference['submitted_papers']:
            reviews = conference['reviews'].get(paper['id'], [])
            score = sum(review['overall_score'] for review in reviews) / len(reviews) if reviews else 0.0
            decisions.append({'payload': {'paper_id': paper['id'], 'conference_id': conference['conference_id'],
                'decision': DECISION_LITERAL, 'final_score': score}})
    if not decisions:
        decisions = [{'payload': {'empty_cycle': True}}]
    return {'outputs': {'ready': [{'payload': {'year': context['period']}}], 'verdicts': decisions},
            'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    for arm, controller, decision in zip(arm_ids, controllers, ('accept', 'reject')):
        model = VLLMServerModel.__new__(VLLMServerModel)
        model.model_name, model.run_seed, model.server_backend = 'fake-model', 42, 'ollama'
        model.thinking_override, model.max_tokens_override = True, 4096
        binding = {'protocol': protocol['schema'], 'cell': initial.fingerprint,
            'model': world['model'], 'model_revision': world['model_digest'],
            'corpus_sha256': world['corpus_sha256'], 'seed': 42,
            'science_config': {'source_commit': world['source_commit'],
                'objective_campaign_binding': controller.binding, 'protocol': protocol}}
        model.response_cache = CompletedResponseCache(run / 'arms' / arm / 'designer-replies.sqlite', binding=binding)
        queue = [plan, {'sources': {'qa_decider': source_template.replace('DECISION_LITERAL', repr(decision))}}]

        def reply(**payload):
            return ChatCompletion.model_validate({'id': 'scripted-native-QA', 'object': 'chat.completion', 'created': 0,
                'model': 'fake-model', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': json.dumps(queue.pop(0))},
                    'finish_reason': 'stop'}]})

        def completion(_model, *, seed_ctx=None, **payload):
            return _model.response_cache.create(reply, seed_ctx=seed_ctx, **payload)

        model._create_completion = MethodType(completion, model)
        proposer = NativeStagedRegionProposer(model, executor, removed_nodes=['world.selection'],
            context_provider=parent_context_provider(run / 'runs', source_commit=world['source_commit']),
            receipts=run / 'arms' / arm / 'design-proposals', instructions='Developer scripted end-to-end QA only')
        try:
            record = controller.advance(simulation_factory=factory, proposer=proposer)
            assert record['observation']['status'] == 'complete', record['observation']['metadata']['technical_failures']
            assert not queue
        finally:
            model.response_cache.close()
        save(run / 'arms' / arm / 'completion.json', {'status': 'declared-budget-complete', 'budget': 2,
            'declared_budget': 2, 'logical_observations': 2, 'terminal_authoring_error': None,
            'source_commit': world['source_commit']})
    terminal = {'status': 'declared-budget-complete', 'physical_complete_runs': 3,
        'source_commit': world['source_commit'], 'budget_per_arm': 2,
        'arms': {arm: {'logical_observations': 2, 'loss_path': [r['observation']['loss'] for r in c.state['records']],
            'candidate_fingerprints': [r['observation']['metadata']['system_fingerprint'] for r in c.state['records']],
            'terminal_authoring_error': None, 'pending': False} for arm, c in zip(arm_ids, controllers)}}
    save(run / 'completion.json', terminal)
    result = analyze(run)
    assert result['classification'] == 'scripted-fixture-not-native-results'
    assert len(physical_worlds) == result['physical_complete_runs'] == 3
    assert result['logical_observations'] == 4
    assert result['status'] == 'declared-budget-complete'
    assert result['new_inference_requests'] == result['generated_code_executions_during_analysis'] == 0
    for arm in arm_ids:
        summary = result['arms'][arm]['proposals'][0]
        assert summary['plan_draft_count'] == summary['source_draft_count'] == 1
        assert summary['structure_only_placeholder_executions'] == 0
        assert summary['status'] == 'isolated-native-region-passed-not-native-evaluated'
        assert summary['candidate_fingerprint'] == result['arms'][arm]['audit']['rows'][1]['system_fingerprint']
    assert controllers[1].state['records'][0]['observation']['metadata']['initial_adoption']['independent_replication'] is False
