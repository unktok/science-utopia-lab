"""Original-world scripted QA only. No actual model or scientific evidence."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from tests.runtime.test_portable_checkpoint_integration import BINDING, FakeHTTPModel, fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_code_trace import RecordingCodeExecutor
from utopia.optimization.native_hybrid import native_endpoint, project_continuous
from utopia.optimization.native_qwen_response import gradient_proposal, control_proof, require_same_control
from utopia.optimization.native_relaxation import replay_tensor_trace, trace_objective
from utopia.optimization.native_response_fidelity import (
    NativeResponseOperator, boundary_layout, programs, raw_review_projection, project_response)
from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.native_response_examples import DECLARATIONS, TERMS, response_gradient_system
from utopia.system.native_review_identity import enable_review_identity_recording

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('g,expected', [(0., .5), (100., .4), (-100., .6), (1., .48)])
def test_fixed_center_step_uses_only_model_gradient(g, expected):
    result = gradient_proposal({'coordinates': [.5], 'gradient': [g], 'representation_sha256': 'fixture'})
    assert result['candidate'] == pytest.approx(expected)
    assert result['unused_outcomes_seen'] == 0
    assert result['candidate'] not in (.35, .65)


def test_numerically_unchanged_projected_step_is_labelled_noop_without_forging_zero_gradient():
    tiny = 1e-16
    result = gradient_proposal({'coordinates': [.5], 'gradient': [tiny], 'representation_sha256': 'fixture'})
    assert result['gradient'] == tiny
    assert result['candidate'] == .5 and result['unchanged']


class HeterogeneousActualInputScript(FakeHTTPModel):
    def reply(self, **payload):
        response = super().reply(**payload)
        phase, year = self.context[0][:2]
        prompt = '\n'.join(m.get('content', '') for m in payload['messages'])
        assert ('"evidence_weight":' in prompt) == (phase == 'phase3_reviews' and year == 2)
        if phase == 'phase3_reviews':
            body = json.loads(response.choices[0].message.content)
            # Deliberately heterogeneous tasks and non-integer raw scores. The
            # signal is read from actual model inputs, never a hidden teacher.
            value = .5
            if year == 2:
                from utopia.optimization.native_qwen_response import HEADER
                charter = json.loads(prompt.rpartition(HEADER)[2])
                assert set(charter) == {'institution', 'instruction', 'native_year', 'evidence_weight', 'originality_weight'}
                value = charter['evidence_weight']
            body['overall_score'] = 2.25+(self.context[1] % 3)+value
            response.choices[0].message.content = json.dumps(body)
        return response


def test_original_two_year_native_world_heterogeneous_response_fit_and_center_backward(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    try:
        executor = DockerCodeExecutor(timeout=60.)
    except (OSError, CodeExecutionError):
        pytest.skip('pinned networkless Docker required')
    objective = load_loss_spec(ROOT/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    base = response_gradient_system(executor.image_id)
    endpoints, evidence, controls = [], {}, []
    for index, value in enumerate((.2, .5, .8)):
        spec, _ = project_continuous(base, DECLARATIONS, {'evidence-weight': value})
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': 'scripted-v9-QA', 'years': 2})
        seed()
        root = tmp_path/str(index)
        recording = RecordingCodeExecutor(executor, root/'code-contexts.jsonl', binding={
            'source_commit': 'scripted-v9-QA', 'system_fingerprint': spec.fingerprint, 'run_id': str(index)})
        sim, calls = make_sim(root, native=NativeScienceKernel(spec, code_executor=recording), model_class=HeterogeneousActualInputScript)
        sim.num_years = 2
        from utopia.optimization.native_factory import record_native_http
        record_native_http(sim.llm, sim, root/'wire.jsonl')
        enable_review_identity_recording(sim)
        try:
            sim.run()
            endpoint = native_endpoint(root/'checkpoints/portable_checkpoint_year_2.json.gz', spec,
                DECLARATIONS, objective, world={'source_commit': 'scripted-v9-QA',
                    'model_digest': BINDING['model_revision'], 'corpus_sha256': BINDING['corpus_sha256'],
                    'seed': 42, 'years': 2, 'classification': 'scripted-fixture-not-native-results'},
                code_contexts=root/'code-contexts.jsonl')
            hard = float(trace_objective(replay_tensor_trace(endpoint['trace'], programs(endpoint),
                hard=True, verify_recorded=True), TERMS))
            assert hard == pytest.approx(endpoint['native_loss'])
            args = {'journal': str(root/'cache/responses.sqlite'), 'wire': str(root/'wire.jsonl'),
                'mechanism': 'addressed-selection', 'input_name': 'features'}
            layout, numeric, _ = boundary_layout(endpoint)
            raw, projection = raw_review_projection(endpoint, layout, numeric, **args)
            assert len(raw) > len(numeric)
            assert project_response(raw, projection, hard=True, temperature=.2).tolist() == numeric.tolist()
            endpoints.append(endpoint)
            evidence[endpoint['checkpoint_sha256']] = args
            assert sim.llm.reused == 0
        finally:
            sim.llm.response_cache.close()
        # This explicitly SCRIPTED QA copies its completed journal into the
        # production filename profile to exercise the public control checker.
        # No real-Qwen output or old frozen evidence is copied/relabelled.
        (root/'replies').mkdir()
        shutil.copy2(root/'cache/responses.sqlite', root/'replies/responses.sqlite')
        shutil.copy2(root/'wire.jsonl', root/'wire-requests.jsonl')
        controls.append(control_proof(endpoint, root))
    assert require_same_control(controls)['world_count'] == 3
    operator = NativeResponseOperator.fit(endpoints, DECLARATIONS, objective, TERMS,
        temperatures=[1., .2], numeric_response_evidence=evidence)
    backward = operator.backward([.5])
    assert backward['frozen_boundary_gradient'] == [0.]
    assert backward['gradient'][0] != 0.
    proposal = gradient_proposal(backward)
    assert .4 <= proposal['candidate'] <= .6
    operator.save(tmp_path/'scripted-operator.json')
    assert NativeResponseOperator.load(tmp_path/'scripted-operator.json').backward([.5]) == backward
