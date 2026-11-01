from copy import deepcopy

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.optimization.test_native_design import factory
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.optimization.native_shared_initial import adopt_shared_initial
from utopia.system.native_kernel import legacy_world_system


@pytest.fixture(autouse=True)
def actual_binding(monkeypatch):
    from tests.runtime import test_portable_checkpoint_integration as fixture
    binding = deepcopy(fixture.BINDING)
    binding['cell'] = legacy_world_system().fingerprint
    binding['science_config']['source_commit'] = 'native-shared-initial-QA'
    monkeypatch.setattr(fixture, 'BINDING', binding)


def controllers(tmp_path, **world):
    kwargs = dict(initial_system=legacy_world_system(), seeds=[42],
                  world_binding={'runtime': 'scripted-native-QA',
                    'model_digest': 'fake-revision', 'corpus_sha256': 'fixed-test-documents-v1',
                    'source_commit': 'native-shared-initial-QA', **world})
    return (NativeDesignCampaign(tmp_path / 'a', loss_spec=loss_spec(), **kwargs),
            NativeDesignCampaign(tmp_path / 'b', loss_spec=loss_spec(coefficient=2), **kwargs))


def test_shared_initial_rescores_without_new_world_and_resumes(tmp_path, fixed_corpus):
    source, target = controllers(tmp_path)
    original = source.advance(simulation_factory=factory(tmp_path / 'runs'))
    calls = []
    def extract(path, **identity):
        calls.append((path, identity))
        return deepcopy(original['observation']['metadata']['measurements'][0])
    adopted = adopt_shared_initial(target, source, checkpoint_measurement=extract)
    assert adopted['observation']['loss'] == -2 * original['observation']['loss']
    assert adopted['observation']['metadata']['runs'] == original['observation']['metadata']['runs']
    assert adopted['suggestion']['suggestion_id'] != original['suggestion']['suggestion_id']
    assert adopted['observation']['metadata']['initial_adoption']['independent_replication'] is False
    _, resumed = controllers(tmp_path)
    assert adopt_shared_initial(resumed, source, checkpoint_measurement=extract) == adopted
    assert len(calls) == 2


def test_shared_initial_rejects_other_world_before_save(tmp_path, fixed_corpus):
    source, _ = controllers(tmp_path)
    source.advance(simulation_factory=factory(tmp_path / 'runs'))
    target = NativeDesignCampaign(tmp_path / 'other', initial_system=source.initial,
        seeds=[42], loss_spec=loss_spec(coefficient=2), world_binding={'runtime': 'different'})
    with pytest.raises(ValueError, match='identical'):
        adopt_shared_initial(target, source, checkpoint_measurement=lambda *a, **k: None)
    assert target.state['records'] == []


def test_measurement_disagreement_cannot_commit_adoption(tmp_path, fixed_corpus):
    source, target = controllers(tmp_path)
    source.advance(simulation_factory=factory(tmp_path / 'runs'))
    before = target.path.read_bytes()
    with pytest.raises(ValueError, match='measurements differ'):
        adopt_shared_initial(target, source, checkpoint_measurement=lambda *a, **k: {})
    assert not target.state['records'] and target.path.read_bytes() == before


def test_tampered_logical_adoption_fails_on_resume(tmp_path, fixed_corpus):
    source, target = controllers(tmp_path)
    original = source.advance(simulation_factory=factory(tmp_path / 'runs'))
    extract = lambda *a, **k: deepcopy(original['observation']['metadata']['measurements'][0])
    adopt_shared_initial(target, source, checkpoint_measurement=extract)
    target.state['records'][0]['observation']['metadata']['initial_adoption']['physical_run_ids'] = ['wrong']
    with pytest.raises(ValueError, match='differs from original'):
        adopt_shared_initial(target, source, checkpoint_measurement=extract)


def test_actual_checkpoint_binding_cannot_be_relabelled(tmp_path, fixed_corpus):
    source, target = controllers(tmp_path, model_digest='different-model')
    original = source.advance(simulation_factory=factory(tmp_path / 'runs'))
    with pytest.raises(ValueError, match='checkpoint world/seed'):
        adopt_shared_initial(target, source, checkpoint_measurement=lambda *a, **k:
            deepcopy(original['observation']['metadata']['measurements'][0]))
    assert target.state['records'] == []
