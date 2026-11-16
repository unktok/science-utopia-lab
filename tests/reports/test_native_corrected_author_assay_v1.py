"""Assay orchestration/real document shapes; SCRIPTED losses are not science."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import run_native_corrected_author_assay_v1 as driver
from tests.optimization.test_native_authoring_ir import request as carrier
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_institution_workflow_domain_v6 import institution_workflow_design_space
from utopia.optimization.native_numeric_designer import save
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/native_author_context_boundary_v1'


def example(label):
    document = json.loads((FIXTURES / (label + '.json')).read_text())
    zero = json.loads((FIXTURES / 'parent-zero.json').read_text())
    request = carrier(); request.update(parent_system=clone(zero if label == 'after-feature-write' else document),
        design_space_anchor=clone(zero), design_space=institution_workflow_design_space(SystemSpec.from_dict(zero)),
        based_on_observation_id='SCRIPTED-original-parent', binding_sha256='SCRIPTED-old-binding',
        strategy_provenance={'protocol': 'SCRIPTED-old', 'post_edit_component_contract': {'SCRIPTED': 'old'}},
        loss_spec=loss_spec(), world_binding={'source_commit': 'SCRIPTED-original-world'},
        history_sha256='SCRIPTED-history-hash', history=[{'SCRIPTED': 'unchanged original history'}])
    if label == 'after-feature-write':
        request['observations'] = [{'suggestion': {'candidate': clone(document)}, 'observation': {
            'observation_id': 'SCRIPTED-measured-edit', 'status': 'complete', 'candidate': clone(document), 'loss': -2.,
            'metadata': {'measurements': [{'run_id': 'SCRIPTED', 'metrics': {
                'native.accepted_decisions': {'status': 'measured', 'value': 2}}}]}}}]
    return request, document


@pytest.fixture(autouse=True)
def no_inference_or_generated_code(monkeypatch):
    def forbidden(*a, **kw): pytest.fail('metadata assay tests cannot call models or generated code')
    monkeypatch.setattr('requests.Session.post', forbidden)
    monkeypatch.setattr('openai.OpenAI.__init__', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


@pytest.mark.parametrize('label', ['parent-zero', 'parent-terminal', 'after-feature-write'])
def test_declared_rebinding_preserves_all_original_scientific_data(label):
    original, document = example(label); before = deepcopy(original)
    result = driver.rebind_request(original, document, label=label, source='SCRIPTED-new-source', contract={'SCRIPTED': 'new-contract'})
    request = result['request']
    assert original == before and result['original_request_sha256'] == digest(original)
    assert result['request_sha256'] == digest(request) and request['parent_system'] == document
    for key in ['observations', 'history', 'history_sha256', 'loss_spec', 'world_binding', 'rng_seed']:
        assert request[key] == original[key]
    assert request['strategy_provenance']['protocol'] == driver.PROTOCOL
    assert request['binding_sha256'] != original['binding_sha256']
    if label == 'after-feature-write':
        assert request['based_on_observation_id'] == 'SCRIPTED-measured-edit'
        assert '/parent_system' in result['explicit_changed_paths']
    else:
        assert request['based_on_observation_id'] == original['based_on_observation_id']
        assert '/parent_system' not in result['explicit_changed_paths']
    assert result['planned_calibration_POSTs'] <= 40


@pytest.mark.parametrize('problem', ['absent', 'duplicate', 'unmeasured', 'wrong-loss', 'wrong-candidate'])
def test_edited_parent_requires_one_exact_measured_original_pair(problem):
    original, document = example('after-feature-write')
    if problem == 'absent': original['observations'] = []
    elif problem == 'duplicate': original['observations'] *= 2
    elif problem == 'unmeasured': original['observations'][0]['observation']['status'] = 'failed'
    elif problem == 'wrong-loss': original['observations'][0]['observation']['loss'] = -999.
    else: original['observations'][0]['observation']['candidate']['metadata']['SCRIPTED'] = True
    with pytest.raises(ValueError):
        driver.rebind_request(original, document, label='after-feature-write', source='SCRIPTED', contract={})


def test_other_native_shape_is_not_silently_substituted():
    original, _ = example('parent-terminal'); _, document = example('parent-zero')
    with pytest.raises(ValueError, match='literal original'):
        driver.rebind_request(original, document, label='parent-zero', source='SCRIPTED', contract={})


@pytest.mark.parametrize('mode', ['no-submissions', 'calibration-failure', 'generation-unknown'])
def test_finite_actual_api_return_shapes_and_no_refill(tmp_path, monkeypatch, mode):
    from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
    origin = tmp_path / 'SCRIPTED-origin'; origin.mkdir(); (origin / 'writer.lock').touch()
    root = tmp_path / 'assay'; root.mkdir(); cases = []
    for label, _, _ in driver.CASES:
        original, document = example(label)
        cases.append(driver.rebind_request(original, document, label=label, source='SCRIPTED', contract={}))
    plan = {'origin': str(origin), 'cases': cases, 'provider': {'SCRIPTED': True}, 'backend': {'SCRIPTED': True},
        'bank': {'SCRIPTED': True}, 'source_commit': 'SCRIPTED', 'content_sha256': 'SCRIPTED'}
    monkeypatch.setattr(driver, 'require_plan', lambda root: deepcopy(plan))
    monkeypatch.setattr(driver, 'backend_binding', lambda provider: deepcopy(plan['backend']))
    for k,v in {'PYTHONHASHSEED': '42', 'CUDA_VISIBLE_DEVICES': '', 'HF_HUB_OFFLINE': '1',
            'HF_DATASETS_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}.items(): monkeypatch.setenv(k,v)
    seen = []
    class Designer:
        def __init__(self, directory, **kwargs): self.directory = directory
        def calibrate(self, request):
            seen.append(('calibration', self.directory.name))
            if mode == 'calibration-failure': raise ValueError('SCRIPTED known failed calibration')
            path = self.directory / 'certificate.json'
            save(path, {'records': [{'ok': True, 'SCRIPTED': True}]})
            return path  # Actual public API returns Path, not a certificate dictionary.
        def execute(self, request, *, purpose, certificate):
            assert isinstance(certificate, Path) and purpose == 'proposal'
            seen.append(('proposal', self.directory.name))
            if mode == 'generation-unknown': raise CompletionUnknown('SCRIPTED unknown generation completion')
            return save(self.directory / 'public-result.json', {'definition': {'generation_failure': {
                'SCRIPTED': 'no explicit submission; do not adopt parent'}}, 'completion_unknown': False})
    monkeypatch.setattr(driver.authoring, 'StagedWorkflowDesigner', Designer)
    monkeypatch.setattr(driver, 'read_visibility', lambda path: {'phase_counts': {},
        'started_calls': 16, 'any_phase_interpretation_mismatch_calls': 0})
    monkeypatch.setattr(driver, 'transport_projection', lambda path: [])
    if mode == 'no-submissions':
        driver.run(root)
        assert driver.read(root / 'terminal.json')['status'] == 'closed'
        assert len(seen) == 6
        assert all(not driver.read(root / (case['label'] + '.result.json'))['free_submission_available'] for case in cases)
    else:
        with pytest.raises(ValueError if mode == 'calibration-failure' else CompletionUnknown): driver.run(root)
        assert driver.read(root / 'terminal.json')['status'] == 'stopped'
        assert len(seen) == (1 if mode == 'calibration-failure' else 2)
        assert driver.read(root / 'failure.json')['known_cases_completed'] == 0
    before = deepcopy(seen)
    with pytest.raises(ValueError, match='no redispatch'): driver.run(root)
    assert seen == before


def test_closed_assay_cold_replay_uses_actual_public_api_without_calibrate_or_dispatch(tmp_path, monkeypatch):
    cases = []
    for label, _, _ in driver.CASES:
        original, document = example(label)
        cases.append(driver.rebind_request(original, document, label=label, source='SCRIPTED', contract={}))
    plan = {'cases': cases, 'provider': {'SCRIPTED': True}, 'backend': {'SCRIPTED': True},
        'bank': {'SCRIPTED': True}, 'source_commit': 'SCRIPTED', 'content_sha256': 'SCRIPTED'}
    monkeypatch.setattr(driver, 'require_plan', lambda root: deepcopy(plan))
    save(tmp_path / 'terminal.json', {'status': 'closed', 'completed_cases': 3})
    calls = []
    def public_replay(path, **kwargs):
        calls.append((path.name, kwargs['purpose']))
        # Preserve the real role-level public return shape; never substitute
        # a richer calibration certificate for its actual returned Path/API.
        return {'SCRIPTED-public-result': True}
    monkeypatch.setattr(driver.authoring, 'replay', public_replay)
    monkeypatch.setattr(driver.authoring, 'cold_certificate', lambda *a, **kw: None)
    monkeypatch.setattr(driver, 'read_visibility', lambda path: {'SCRIPTED-visibility': True})
    monkeypatch.setattr(driver, 'transport_projection', lambda path: [])
    for case in cases:
        certificate = tmp_path / (case['label'] + '.certificate.json')
        save(certificate, {'SCRIPTED': 'certificate'})
        save(tmp_path / (case['label'] + '.result.json'), {'request_sha256': case['request_sha256'],
            'public_proposal_result': {'SCRIPTED-public-result': True}, 'certificate': str(certificate),
            'certificate_file_sha256': driver.file_sha256(certificate), 'visibility': {'SCRIPTED-visibility': True},
            'free_submission_available': False, 'implementation_phase_calls': 0,
            'actual_calibration_records': 28, 'actual_proposal_started_calls': 16, 'generation_transport': []})
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    result = driver.replay(tmp_path)
    assert len(calls) == 6 and len(result['cases']) == 3
    assert result['new_model_calls'] == result['new_code_executions'] == result['new_native_worlds'] == 0
    assert not result['publication_ready'] and not result['corrected_free_invention_or_loss_gain_claimed']
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
