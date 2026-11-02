"""Full moving-clock original-world QA with SCRIPTED HTTP, never Qwen results.

Only the factory, historical-loader boundary and model/classification constants
are fixture substitutions. Native phases, code execution, raw correspondence,
source-byte guards, fitting, gradients, policies and saved-operator reload run
their real implementations.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import BINDING, SmallRealSimulation, fixed_corpus, seed
from tests.optimization.test_native_qwen_response_v9 import HeterogeneousActualInputScript
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def driver():
    spec = importlib.util.spec_from_file_location('native_method_paths_v10_integration', ROOT/'scripts/run_native_method_paths_v10.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_clock_three_shared_and_six_adaptive_native_method_worlds(tmp_path, fixed_corpus, monkeypatch):
    from tests.runtime.test_portable_checkpoint_integration import DIRECTION
    from utopia.agents.researcher_agents import UniversityResearcher
    from utopia.funding.feedback import FundingFeedbackMixin
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.optimization.native_code_trace import RecordingCodeExecutor
    from utopia.optimization.native_factory import record_native_http
    import utopia.optimization.native_method_paths as methods
    from utopia.optimization.native_response_prefix import prepare_common_prefix
    from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
    from utopia.system.native_kernel import NativeScienceKernel
    try:
        executor = DockerCodeExecutor(timeout=60.)
    except (OSError, CodeExecutionError):
        pytest.skip('existing pinned networkless Docker required')
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    module = driver()
    monkeypatch.setattr(module, 'MODEL', BINDING['model'])
    monkeypatch.setattr(module, 'ACTUAL', 'scripted-online-v10-software-QA')
    monkeypatch.setattr(methods, 'ACTUAL', module.ACTUAL)
    monkeypatch.setattr(methods, 'HISTORICAL_SOURCE', source)
    monkeypatch.setattr(methods, 'HISTORICAL_CLASSIFICATION', 'scripted-historical-v10-software-QA')
    calls_by_name, simulations = {}, {}

    class ProductionScriptedSimulation(SmallRealSimulation):
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
            self.directory, self.source_commit = directory, source
            self.model_digest, self.corpus_sha256 = BINDING['model_revision'], BINDING['corpus_sha256']
            self.runtime_seed_binding = {'scripted_fixture': True}

        def __call__(self, system, run_seed, name):
            seed()
            monkeypatch.setitem(BINDING, 'cell', system.fingerprint)
            monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': source, 'years': 2})
            root = self.directory/name
            calls = []
            model = HeterogeneousActualInputScript(root, calls)
            assert model.max_concurrent_requests == 1
            model.response_cache.close()
            model.response_cache = CompletedResponseCache(root/'replies/responses.sqlite', binding=BINDING)
            sim = ProductionScriptedSimulation(root, model)
            sim.native_system = NativeScienceKernel(system, code_executor=RecordingCodeExecutor(executor,
                root/'code-contexts.jsonl', binding={'source_commit': source,
                    'system_fingerprint': system.fingerprint, 'run_id': name}))
            record_native_http(model, sim, root/'wire-requests.jsonl')
            calls_by_name[name], simulations[name] = calls, sim
            return sim

    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory', ScriptedFactory)
    historical_output = tmp_path/'scripted-history'
    historical_factory = ScriptedFactory(historical_output/'worlds', tmp_path/'fake-cache', years=2, corpus_years=4)
    system = module.response_gradient_system(executor.image_id)
    historical_world = {'source_commit': source, 'model_digest': historical_factory.model_digest,
        'corpus_sha256': historical_factory.corpus_sha256, 'seed': 42, 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': historical_factory.runtime_seed_binding,
        'experiment': {**module.EXPERIMENT, 'protocol': 'native-qwen-response-gradient-v9'},
        'classification': methods.HISTORICAL_CLASSIFICATION}
    first = module.execute_world(historical_factory, system, historical_world, None, None,
        'calibration-0', .2, historical_output)
    anchor_root = historical_output/'worlds/calibration-0'
    prepared = prepare_common_prefix(anchor_root, first['endpoint'])
    rows = [first]+[module.execute_world(historical_factory, system, historical_world, prepared, anchor_root,
        'calibration-'+str(i), theta, historical_output) for i, theta in ((1, .5), (2, .8))]
    shared = {'audit_path': 'explicit-scripted-QA-loader-boundary', 'audit_file_sha256': 'a'*64,
        'audit_content_sha256': digest({'fixture': True}), 'source_commit': source,
        'raw_root': str(historical_output), 'raw_inventory_sha256': digest({'fixture': 'bound-by-endpoint-files'}),
        'raw_file_count': len([p for p in historical_output.rglob('*') if p.is_file()]),
        'rows': rows, 'anchor_world_dir': str(anchor_root), 'anchor_endpoint': first['endpoint'],
        'historical_observations_charged_per_arm': 3,
        'historical_calibration_fresh_calls': sum(r['fresh_physical_replies'] for r in rows),
        'unique_anchor_origin_calls': prepared['prefix_count']}
    # This is the sole historical-loader fixture. Every actual row beneath it
    # is restored, hash checked, source-guarded and parsed by the real fitter.
    monkeypatch.setattr(module, 'load_shared_historical', lambda _: deepcopy(shared))
    output = tmp_path/'six-method-worlds'
    output.mkdir()
    result = module.run(SimpleNamespace(output=output, historical_audit=tmp_path/'scripted-audit.json',
        data_cache=tmp_path/'fake-cache', inference_lock=tmp_path/'fake-lock'))
    assert result['status'] == 'complete' and result['physical_native_worlds'] == 6
    assert result['classification'] == 'scripted-online-v10-software-QA'
    assert result['physical_reply_count'] == sum(len(calls_by_name[r['name']]) for r in result['endpoints'])
    assert result['logical_response_count'] == result['physical_reply_count']+6*prepared['prefix_count']
    assert result['all_control_check']['world_count'] == 6
    assert len(result['steps']) == 6 and not result['failures']
    assert methods.read(output/'evidence.json') == result
    objective = module.load_loss_spec(ROOT/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    for row in result['endpoints']:
        assert row['elapsed_seconds'] > 0  # Global/HTTP clocks remain live.
        assert len(calls_by_name[row['name']]) == row['fresh_physical_replies']
        prefix = row['common_prefix_receipt']
        assert prefix['review_clock_coupling']['completed_checkpoint_verification'] == 'exact-semantic-year1-checkpoint-clocks-verified'
        assert not prefix['review_clock_coupling']['global_and_transport_clock_modified']
        assert prefix['replayed_response_count'] == prepared['prefix_count']
    for step in result['steps']:
        if step['arm'] != 'gradient': continue
        eligible = rows+[row for row in result['endpoints'] if row['arm'] == 'gradient' and row['step'] < step['step']]
        assert len(eligible) == 3+step['step']
        operator_file = Path(step['operator']['path'])
        restored = methods.load_path_operator(operator_file, eligible, objective,
            module.GRADIENT_RULE['temperature_schedule'][step['step']], ROOT)
        assert restored._hash == step['operator']['representation_sha256']
        assert restored.state['temperature'] == module.GRADIENT_RULE['temperature_schedule'][step['step']]
        assert [p['checkpoint_sha256'] for p in restored.state['calibration']] == [r['endpoint']['checkpoint_sha256'] for r in eligible]
    # Terminal evidence cannot be silently rerolled or overwritten.
    with pytest.raises(ValueError, match='immutable'):
        module.run(SimpleNamespace(output=output))


@pytest.mark.parametrize('tamper', ['changed-runtime-byte', 'missing-runtime', 'fake-source'])
def test_source_bridge_rejects_changed_missing_or_unresolvable_original_runtime(tmp_path, tamper):
    from utopia.optimization.native_method_paths import runtime_source_equivalence
    source = '1d29f1fc0c61bf9e0d1952ce33c4b0cac137cf6a'
    if tamper == 'fake-source':
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            runtime_source_equivalence(ROOT, ['not-a-real-source'])
        return
    # A lightweight Git-object fixture exposes one original file. No actual
    # worktree/runtime/source file is edited by the test.
    import unittest.mock
    file = tmp_path/'utopia/original.py'
    file.parent.mkdir()
    file.write_bytes(b'changed' if tamper == 'changed-runtime-byte' else b'original')
    expected = __import__('hashlib').sha1(b'blob 8\0original').hexdigest()
    if tamper == 'missing-runtime': file.unlink()
    with unittest.mock.patch('utopia.optimization.native_method_paths.subprocess.check_output',
            return_value='100644 blob '+expected+'\tutopia/original.py\n'):
        with pytest.raises(ValueError, match='runtime'):
            runtime_source_equivalence(tmp_path, [source])
