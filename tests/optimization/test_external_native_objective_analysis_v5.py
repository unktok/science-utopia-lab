"""External whole-audit QA: scripted authors/researchers, no model API calls."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.analyze_external_native_objectives_v5 import EXHAUSTED, ExternalManifestReplay, analyze
from scripts.audit_native_objective_v5 import checkpoint_measurements
from tests.optimization.test_native_region_ir import fixture_ir
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.models.response_cache import CompletedResponseCache
from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_code_trace import RecordingCodeExecutor, parent_context_provider
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox
from utopia.optimization.native_region_proposer_v5a2 import NativeBoundaryRegionProposer
from utopia.optimization.native_shared_initial import adopt_shared_initial
from utopia.system.code_mechanisms import DockerCodeExecutor, sha
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False))


def test_independent_inbox_verifies_raw_bytes_not_only_canonical_json(tmp_path):
    inbox = ManifestInbox(tmp_path)
    kwargs = {'prompt': 'explicit fixture data', 'seed_ctx': ('fixture', 1)}
    with pytest.raises(ExternalAuthoringPending) as waiting:
        inbox.generate(**kwargs)
    pending = waiting.value
    response = {'request_sha256': pending.request_sha256, 'manifest': {'fixture': True},
                'authoring': {'kind': 'external', 'name': 'Scripted QA, not a provider'}}
    write(pending.response_path, response)
    inbox.generate(**kwargs)
    replay = ExternalManifestReplay(tmp_path)
    assert replay.generate(**kwargs)[0] == response['manifest']
    assert len(replay.used) == 1
    # Identical parsed JSON is not identical consumed raw bytes.
    pending.response_path.write_text(json.dumps(response, indent=2))
    with pytest.raises(ValueError, match='raw/canonical'):
        ExternalManifestReplay(tmp_path)


def test_external_pending_or_orphaned_files_are_not_terminal_evidence(tmp_path):
    with pytest.raises(ExternalAuthoringPending):
        ManifestInbox(tmp_path).generate(prompt='pending, not a technical failure')
    with pytest.raises(ValueError, match='orphaned or unconsumed'):
        ExternalManifestReplay(tmp_path)


@pytest.mark.parametrize('technical_failure', [False, True])
def test_external_full_native_pipeline_readonly_audit(tmp_path, fixed_corpus, monkeypatch, technical_failure):
    """Real scientific phases/Docker; explicit developer-scripted transport/data.

    Three physical six-year worlds, four logical observations. No designer SQL
    cache exists; researcher caches are real and mandatory for native auditing.
    """
    from tests.runtime import test_portable_checkpoint_integration as fixture

    run = tmp_path / 'external-scripted-QA-not-research-results'
    run.mkdir()
    losses = [load_loss_spec(ROOT / f'research/objectives/losses/native-joint-v5-{name}.json')
              for name in ('throughput', 'net-reviewed-utility')]
    arms = [loss['id'] for loss in losses]
    protocol = {'schema': 'scienceutopia.external-native-objectives.v5', 'kind': 'externalnative-v5',
        'authoring_format': 'boundary-v5a2-external-manifest', 'designer_transport': 'hash-bound-file-inbox-no-provider-API',
        'researcher_model': 'fake-model', 'losses': losses, 'arm_ids': arms, 'seed': 42,
        'years': 6, 'corpus_years': 6, 'budget_per_arm': 2, 'max_technical_drafts': 3,
        'requested_designer_max_tokens': 4096, 'classification': 'scripted-fixture-not-native-results'}
    executor = DockerCodeExecutor()
    initial = selection_source_slot(legacy_world_system(seed=42), image_id=executor.image_id)
    world = {'source_commit': 'QA-external-full-audit', 'model': 'fake-model', 'model_digest': 'fake-revision',
        'corpus_sha256': 'fixed-test-documents-v1', 'image_id': executor.image_id, 'years': 6,
        'corpus_years': 6, 'runtime_seed_binding': {'scripted_QA_hash_seed': 42}, 'protocol': protocol}
    write(run / 'plan.json', {'protocol': protocol, 'world': world, 'initial_fingerprint': initial.fingerprint})
    physical = []

    def factory(system, run_seed, run_id):
        seed()
        physical.append(run_id)
        cell = run / 'runs' / run_id
        binding = deepcopy(fixture.BINDING)
        binding['cell'] = system.fingerprint
        binding['science_config'].update(source_commit=world['source_commit'], years=6, corpus_years=6,
            runtime_seed_binding=world['runtime_seed_binding'], thinking_override=False, experiment=protocol)
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
        loss_spec=loss, seeds=[42], world_binding=world) for arm, loss in zip(arms, losses)]
    first = controllers[0].advance(simulation_factory=factory)
    assert first['observation']['status'] == 'complete'
    adopt_shared_initial(controllers[1], controllers[0], checkpoint_measurement=checkpoint_measurements)

    class ScriptedExternalAuthor:
        def __init__(self, arm):
            self.arm = arm
            self.inbox = ManifestInbox(run / 'arms' / arm / 'authoring-inbox')

        def generate(self, **kwargs):
            try:
                return self.inbox.generate(**kwargs)
            except ExternalAuthoringPending as pending:
                manifest = fixture_ir()
                if technical_failure and self.arm == arms[0]:
                    manifest['exports'].pop('after')
                write(pending.response_path, {'request_sha256': pending.request_sha256, 'manifest': manifest,
                    'authoring': {'kind': 'external', 'name': 'Developer-scripted QA, not authenticated model output'}})
                return self.inbox.generate(**kwargs)

    errors = {}
    for arm, controller in zip(arms, controllers):
        proposer = NativeBoundaryRegionProposer(ScriptedExternalAuthor(arm), executor,
            removed_nodes=['world.selection'], context_provider=parent_context_provider(run / 'runs', source_commit=world['source_commit']),
            receipts=run / 'arms' / arm / 'design-proposals', instructions='Developer-scripted external integration QA only')
        if technical_failure and arm == arms[0]:
            with pytest.raises(ValueError, match='bounded region'):
                controller.advance(simulation_factory=factory, proposer=proposer)
            errors[arm] = {'proposal_index': 1, 'error_type': 'ValueError', 'error': EXHAUSTED,
                           'loss': None, 'automatic_redraft': False}
        else:
            record = controller.advance(simulation_factory=factory, proposer=proposer)
            assert record['observation']['status'] == 'complete', record['observation']['metadata']['technical_failures']
    write(run / 'terminal-authoring-errors.json', errors)
    terminal = {'schema': protocol['schema'], 'terminal': True,
        'status': 'terminal-with-preserved-failures' if technical_failure else 'declared-budget-complete',
        'pending_external_authoring': {}, 'source_commit': world['source_commit'],
        'arms': {arm: {'logical_observations': len(c.state['records']), 'loss_path': [r['observation']['loss'] for r in c.state['records']],
            'pending_native_execution': False, 'terminal_authoring_error': errors.get(arm)} for arm, c in zip(arms, controllers)}}
    write(run / 'completion.json', terminal)
    result = analyze(run)
    assert result['classification'] == 'scripted-fixture-not-native-results'
    assert result['schema'] == 'scienceutopia.native-joint-objectives-analysis.v5'
    assert len(physical) == result['physical_complete_runs'] == (2 if technical_failure else 3)
    assert result['logical_observations'] == (3 if technical_failure else 4)
    assert result['status'] == terminal['status']
    assert result['authoring_provenance']['provider_authenticated'] is False
    assert result['authoring_provenance']['qwen_designer_authorship_claimed'] is False
    assert result['authoring_provenance']['self_reported_authors'][0]['kind'] == 'external'
    assert not list(run.rglob('designer-replies.sqlite'))
    assert result['new_inference_requests'] == result['generated_code_executions_during_analysis'] == 0
    for arm in arms:
        failed = technical_failure and arm == arms[0]
        assert result['arms'][arm]['proposals'][0]['status'] == ('invalid-technical-manifest' if failed else 'isolated-native-region-passed-not-native-evaluated')
        assert len(result['arms'][arm]['external_authoring']) == (3 if failed else 1)
        if not failed:
            assert len(result['arms'][arm]['audit']['rows'][1]['runs'][0]['executed_code']) == 2
        else:
            assert result['arms'][arm]['authoring_error']['loss'] is None
            assert len(result['arms'][arm]['loss_path']) == 1
        assert not (run / 'arms' / arm / 'completion.json').exists()  # root-only external driver contract
    # Canonical manifest + consumed receipts can be consistently rewritten, but
    # exact IR -> proposer -> native execution reconstruction still detects it.
    inbox = run / 'arms' / arms[0] / 'authoring-inbox'
    path = next((inbox / 'responses').glob('*.json'))
    response = json.loads(path.read_text())
    response['manifest']['rationale'] = 'unrecorded external rewrite'
    write(path, response)
    with pytest.raises(ValueError, match='raw/canonical'):
        analyze(run)
    # Updating the consumed hashes does not make an unrecorded generated IR the
    # one actually compiled/executed. The independent proposer chain still fails.
    from utopia.utils.data_utils import file_sha256
    consumed_path = inbox / 'consumed' / path.name
    consumed = json.loads(consumed_path.read_text())
    consumed.update(response_sha256=sha(response), response_file_sha256=file_sha256(path),
                    manifest_sha256=sha(response['manifest']))
    write(consumed_path, consumed)
    with pytest.raises(ValueError, match='manifest differs from generated IR'):
        analyze(run)
