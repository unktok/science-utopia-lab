"""Runner persistence and production filenames with SCRIPTED HTTP only.

No Ollama/network model, corpus download or actual-Qwen scientific result is
created by these regressions. The integration test retains original Simulation
phases and uses the existing pinned, networkless institution executor.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import BINDING, SmallRealSimulation, fixed_corpus, seed
from tests.optimization.test_native_qwen_response_v9 import HeterogeneousActualInputScript
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.design_patch import digest

ROOT = Path(__file__).resolve().parents[2]


def runner_module():
    spec = importlib.util.spec_from_file_location('native_response_runner_v9_unit', ROOT/'scripts/run_native_qwen_response_v9.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_save_read_content_hash_roundtrip_does_not_carry_a_stale_previous_hash(tmp_path):
    module = runner_module()
    path = tmp_path/'receipt.json'
    old = {'status': 'in-progress', 'endpoints': [], 'content_sha256': 'stale'}
    saved = module.save(path, old)
    assert saved['content_sha256'] == digest({k: v for k, v in saved.items() if k != 'content_sha256'})
    assert module.read(path) == saved
    assert old['content_sha256'] == 'stale'  # Saving does not mutate the caller.
    saved['endpoints'].append({'name': 'calibration-0'})
    newer = module.save(path, saved)
    assert module.read(path) == newer
    assert newer['content_sha256'] != saved['content_sha256']
    corrupted = deepcopy(newer)
    corrupted['endpoints'][0]['name'] = 'foreign'
    path.write_text(json.dumps(corrupted))
    with pytest.raises(ValueError, match='content hash'):
        module.read(path)


def test_completed_evidence_refuses_startup_before_constructing_any_factory(tmp_path, monkeypatch):
    module = runner_module()
    module.save(tmp_path/'evidence.json', {'status': 'complete'})
    def must_not_construct(*args, **kwargs):
        pytest.fail('completed evidence must not construct an executor or model factory')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor', must_not_construct)
    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory', must_not_construct)
    with pytest.raises(ValueError, match='immutable'):
        module.run(SimpleNamespace(output=tmp_path))


@pytest.mark.parametrize('condition', ['operator-without-evidence', 'proposal-without-evidence',
    'operator-before-calibration', 'proposal-without-operator', 'unused-without-freeze',
    'duplicate-prefix', 'skipped-prefix', 'tampered-operator', 'unhashed-operator', 'retained-failure'])
def test_startup_rejects_stale_or_orphaned_artifacts_before_any_factory(tmp_path, monkeypatch, condition):
    module = runner_module()
    evidence = {'schema': module.SCHEMA, 'classification': module.ACTUAL, 'status': 'in-progress',
        'endpoints': [{'name': name} for name in module.WORLD_NAMES[:3]], 'failures': []}
    operator = {'schema': 'synthetic-operator-unit-only'}
    if condition in ('operator-without-evidence', 'proposal-without-evidence'):
        module.save(tmp_path/('response-operator.json' if condition.startswith('operator') else 'frozen-proposal.json'), operator)
    else:
        if condition == 'operator-before-calibration':
            evidence['endpoints'].pop()
            module.save(tmp_path/'response-operator.json', operator)
        elif condition == 'proposal-without-operator': module.save(tmp_path/'frozen-proposal.json', {'proposal': 'unit-only'})
        elif condition == 'unused-without-freeze': evidence['endpoints'].append({'name': 'unused-0'})
        elif condition == 'duplicate-prefix': evidence['endpoints'][1]['name'] = 'calibration-0'
        elif condition == 'skipped-prefix': evidence['endpoints'][1]['name'] = 'unused-0'
        elif condition == 'retained-failure': evidence['failures'].append({'loss': None, 'error': 'preserved original failure'})
        elif condition == 'unhashed-operator': (tmp_path/'response-operator.json').write_text(json.dumps(operator))
        elif condition == 'tampered-operator':
            value = module.save(tmp_path/'response-operator.json', operator)
            value['schema'] = 'tampered'
            (tmp_path/'response-operator.json').write_text(json.dumps(value))
        module.save(tmp_path/'evidence.json', evidence)
    def must_not_construct(*args, **kwargs):
        pytest.fail('invalid startup must not construct an executor or factory')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor', must_not_construct)
    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory', must_not_construct)
    with pytest.raises(ValueError):
        module.run(SimpleNamespace(output=tmp_path))


def test_preflight_allows_a_plan_bound_partial_world_and_complete_calibration_before_fit(tmp_path):
    module = runner_module()
    # Directory presence alone is not a reason to erase/reject a legitimate
    # interrupted original-world cache; the factory verifies its full binding.
    (tmp_path/'worlds/calibration-0').mkdir(parents=True)
    module.preflight_saved_artifacts(tmp_path)
    module.save(tmp_path/'evidence.json', {'schema': module.SCHEMA, 'classification': module.ACTUAL,
        'status': 'in-progress', 'endpoints': [{'name': n} for n in module.WORLD_NAMES[:3]], 'failures': []})
    module.preflight_saved_artifacts(tmp_path)


def test_native_observation_projection_already_omits_clocks_and_archive_destinations():
    from utopia.system.native_kernel import _json
    source = {'papers': {'output_dir': '/world-a/checkpoints', 'papers': [{'id': 'actual-id', 'review_history': [{
        'reviews': [{'overall_score': 4, 'review_time': 123.}], 'decision_time': 125.}]}]},
        'conferences': [{'submitted_papers': [{'id': 'actual-id', 'submission_time': 122.}]}]}
    normalized = _json(source)
    encoded = json.dumps(normalized)
    assert not any(key in encoded for key in ('output_dir', 'review_time', 'decision_time', 'submission_time'))
    assert normalized['papers']['papers'][0]['review_history'][0]['reviews'] == [{'overall_score': 4}]
    assert normalized['conferences'][0]['submitted_papers'] == [{'id': 'actual-id'}]


def _add_actual_ollama_envelope_shape(root, *, variant, change_content=False):
    """Synthetic metadata values from the real envelope schema, not real replies."""
    import hashlib
    from utopia.runtime.checkpointing import canonical_json
    journal = root/'replies/responses.sqlite'
    with sqlite3.connect(journal) as db:
        rows = db.execute('SELECT rowid,data FROM replies ORDER BY rowid').fetchall()
        for rowid, data in rows:
            body = json.loads(data)
            body.update(id='chatcmpl-unit-'+str(variant)+'-'+str(rowid), created=1700000000+variant,
                object='chat.completion', system_fingerprint='fp_ollama', moderation=None, service_tier=None,
                usage={'completion_tokens': 20, 'prompt_tokens': 50,
                    'prompt_tokens_details': {'cached_tokens': variant, 'audio_tokens': None}, 'total_tokens': 70})
            body['choices'][0]['finish_reason'] = 'stop'
            if change_content and rowid == 1:
                body['choices'][0]['message']['content'] = '{"overall_score": 1, "justification": "changed scientific response"}'
            encoded = canonical_json(body)
            db.execute('UPDATE replies SET data=?,data_sha=? WHERE rowid=?',
                (encoded, hashlib.sha256(encoded.encode()).hexdigest(), rowid))


def test_control_comparison_ignores_only_nonconsumed_ollama_envelope_metadata(tmp_path):
    """Regression: d5b08d6 fails this; the prospective fix must make it pass."""
    from tests.optimization.test_native_qwen_response_controls_v9 import _fixture
    from utopia.optimization.native_qwen_response import control_proof, require_same_control
    from utopia.utils.data_utils import file_sha256
    left, left_root, _ = _fixture(tmp_path/'left', theta=.2)
    right, right_root, _ = _fixture(tmp_path/'right', theta=.8)
    _add_actual_ollama_envelope_shape(left_root, variant=1)
    _add_actual_ollama_envelope_shape(right_root, variant=2)
    assert file_sha256(left_root/'replies/responses.sqlite') != file_sha256(right_root/'replies/responses.sqlite')
    assert require_same_control([control_proof(left, left_root), control_proof(right, right_root)])['world_count'] == 2


def test_control_comparison_still_rejects_changed_scientific_reply_despite_envelope_normalization(tmp_path):
    from tests.optimization.test_native_qwen_response_controls_v9 import _fixture
    from utopia.optimization.native_qwen_response import control_proof, require_same_control
    from utopia.optimization.native_response_fidelity import BoundaryUnsupported
    left, left_root, _ = _fixture(tmp_path/'left', theta=.2)
    right, right_root, _ = _fixture(tmp_path/'right', theta=.8)
    _add_actual_ollama_envelope_shape(left_root, variant=1)
    _add_actual_ollama_envelope_shape(right_root, variant=2, change_content=True)
    with pytest.raises(BoundaryUnsupported):
        require_same_control([control_proof(left, left_root), control_proof(right, right_root)])


def test_complete_six_world_runner_uses_production_checkpoint_manifest_and_response_profiles(
        tmp_path, monkeypatch, fixed_corpus):
    """Six SCRIPTED two-year/five-author worlds, no Qwen or model downloads."""
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.optimization.native_code_trace import RecordingCodeExecutor
    from utopia.optimization.native_factory import record_native_http
    from utopia.funding.feedback import FundingFeedbackMixin
    from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.agents.researcher_agents import UniversityResearcher
    from tests.runtime.test_portable_checkpoint_integration import DIRECTION
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    try:
        executor = DockerCodeExecutor(timeout=60.)
    except (OSError, CodeExecutionError):
        pytest.skip('existing pinned networkless Docker required')
    records = []

    class ProductionProfileScriptedSimulation(SmallRealSimulation):
        def __init__(self, root, model):
            self.root, self.after_effects, self.uploaded_years = root, False, []
            output, docs = root/'simulation/checkpoints/native-design', root/'simulation/docs/native-design'
            output.mkdir(parents=True)
            docs.mkdir(parents=True)
            args = SimpleNamespace(seed=42, num_conferences=1, docs_dir=str(docs), rag_device='cpu',
                checkpoint_callback=self.record_upload, portable_checkpoint=True, checkpoint_binding=BINDING,
                funding_feedback=True, expected_founders=5, log_resource_ledger=False,
                log_funding_applications=True, funding_application_cost=1.)
            FundingFeedbackMixin.__init__(self, model, num_years=2, output_dir=str(output), args=args,
                funding_allocation_mode='fixed', debug=True)
            model.sim = self

        def initialize_agents(self):
            super().initialize_agents()
            self.ecosystem.add_agent(UniversityResearcher('researcher-4', 'university-4', funding_level=1000,
                expertise=[DIRECTION], llm=self.llm))
            self._record_initial_university_count()

    class ScriptedFactory:
        def __init__(self, directory, data_cache, **kwargs):
            assert kwargs['years'] == 2 and kwargs['corpus_years'] == 4
            assert kwargs['record_wire'] and kwargs['record_code']
            self.directory = directory
            self.source_commit = 'SCRIPTED-RUNNER-QA-NOT-QWEN'
            self.model_digest, self.corpus_sha256 = BINDING['model_revision'], BINDING['corpus_sha256']
            self.runtime_seed_binding = {'scripted_fixture': True}

        def __call__(self, system, run_seed, name):
            assert run_seed == 42
            seed()
            monkeypatch.setitem(BINDING, 'cell', system.fingerprint)
            monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'],
                'source_commit': self.source_commit, 'years': 2})
            root = self.directory/name
            calls = []
            model = HeterogeneousActualInputScript(root, calls)
            model.response_cache.close()
            model.response_cache = CompletedResponseCache(root/'replies/responses.sqlite', binding=BINDING)
            sim = ProductionProfileScriptedSimulation(root, model)
            recorder = RecordingCodeExecutor(executor, root/'code-contexts.jsonl', binding={
                'source_commit': self.source_commit, 'system_fingerprint': system.fingerprint, 'run_id': name})
            sim.native_system = NativeScienceKernel(system, code_executor=recorder)
            record_native_http(model, sim, root/'wire-requests.jsonl')
            records.append((name, sim, calls))
            return sim

    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory', ScriptedFactory)
    output = tmp_path/'six-scripted-worlds'
    output.mkdir()
    args = SimpleNamespace(output=output, data_cache=tmp_path/'fake-cache', inference_lock=tmp_path/'fake-lock', amendment=None)
    module = runner_module()
    result = module.run(args)
    assert result['status'] == 'complete' and result['physical_native_worlds'] == 6
    assert len(records) == 6
    assert [name for name, _, _ in records] == ['calibration-0', 'calibration-1', 'calibration-2',
        'unused-0', 'unused-1', 'gradient-candidate']
    assert result['physical_reply_count'] == sum(len(calls) for _, _, calls in records)
    assert result['frozen_proposal']['unused_outcomes_seen'] == 0
    assert result['claims']['exact_Qwen_Jacobian'] is False
    assert {k: v for k, v in module.read(output/'evidence.json').items() if k != 'content_sha256'} == {
        k: v for k, v in result.items() if k != 'content_sha256'}
    for row, (name, sim, calls) in zip(result['endpoints'], records):
        root = output/'worlds'/name
        assert row['endpoint']['checkpoint'] == str(root/'simulation/checkpoints/native-design/portable_checkpoint_year_2.json.gz')
        assert row['numeric_response_evidence']['journal'] == str(root/'replies/responses.sqlite')
        assert row['numeric_response_evidence']['wire'] == str(root/'wire-requests.jsonl')
        assert row['completion_receipt'] == module.read(root/'completion-receipt.json')
        assert row['completion_receipt']['run_manifest_sha256']
        state = read_portable_checkpoint(row['endpoint']['checkpoint'])
        assert sum(a['can_author'] for a in state['ecosystem_data']['agents']) == 5
        assert len(calls) == row['fresh_physical_replies']
        assert sim.llm.reused == 0
    with pytest.raises(ValueError, match='immutable'):
        module.run(args)
