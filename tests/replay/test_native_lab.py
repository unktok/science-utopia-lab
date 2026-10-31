import hashlib
import json

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.optimization.test_native_design import factory
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.replay.native_lab import native_lab_envelope
from utopia.system.native_kernel import legacy_world_system


def test_actual_native_campaign_exports_identity_bound_ui_without_simulating_browser_activity(tmp_path, fixed_corpus):
    campaign = NativeDesignCampaign(tmp_path / 'campaign', initial_system=legacy_world_system(),
        loss_spec=loss_spec(), seeds=[42], world_binding={'mode': 'scripted-transport-native-QA', 'years': 6})
    campaign.advance(simulation_factory=factory(tmp_path / 'runs'))
    envelope = native_lab_envelope(tmp_path, loss_spec=loss_spec())
    assert hashlib.sha256(envelope['payload_json'].encode()).hexdigest() == envelope['payload_sha256']
    data = json.loads(envelope['payload_json'])
    row = data['systems'][0]
    assert hashlib.sha256(row['system_spec_json'].encode()).hexdigest() == row['system_fingerprint']
    assert len(row['runs'][0]['frames']) == 6
    assert all(a['can_author'] for frame in row['runs'][0]['frames'] for a in frame['actors'])
    assert row['native_loss'] == campaign.state['records'][0]['observation']['loss']
    assert data['interpretation']['live_player_intervention'] is False
    assert data['interpretation']['model_weights_trained'] is False
