"""Identity-bound native design replay export."""
import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_design import campaign, factory
from utopia.replay.native_design import native_design_replay, native_design_view


def test_native_candidate_evidence_and_design_path_export_without_new_world(tmp_path, fixed_corpus):
    controller = campaign(tmp_path / 'campaign')
    record = controller.advance(simulation_factory=factory(tmp_path / 'runs'))
    suggestion = record['suggestion']
    checkpoint = tmp_path / 'runs' / (suggestion['suggestion_id'] + '-s42') / 'checkpoints' / 'portable_checkpoint_year_6.json.gz'
    fingerprint = record['difference']['candidate_fingerprint']
    payload = native_design_replay(checkpoint, expected_system_fingerprint=fingerprint, label='Native QA, scripted model/corpus')
    assert payload['schema_version'] == 'scienceutopia.replay-view.v2'
    assert payload['metadata']['system_fingerprint'] == fingerprint
    view = native_design_view(controller)
    assert view['records'][0]['observation']['loss'] == record['observation']['loss']
    assert not view['interpretation']['recursive_self_improvement']
    with pytest.raises(ValueError, match='identity'):
        native_design_replay(checkpoint, expected_system_fingerprint='wrong', label='invalid')
