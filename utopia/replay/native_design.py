"""Export native design/loss lineage and replay using authoritative state only."""
from pathlib import Path

from .converter import ArtifactBundle, convert_artifacts
from .viewer import build_viewer_payload_v2
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.design_patch import digest


def native_design_replay(checkpoint, *, expected_system_fingerprint, label):
    state = read_portable_checkpoint(Path(checkpoint))
    native = state.get('native_system')
    if not native or native['system_fingerprint'] != expected_system_fingerprint:
        raise ValueError('native design replay and candidate identity differ')
    events = convert_artifacts(ArtifactBundle.discover(checkpoint))
    return build_viewer_payload_v2(events, metadata={
        'title': label, 'source_kind': 'native-design-development-run',
        'system_fingerprint': expected_system_fingerprint,
        'interpretation': 'Canonical evidence, not scientific improvement or live player intervention'})


def native_design_view(campaign):
    campaign._validate()
    rows = [{'suggestion': r['suggestion'], 'difference': r['difference'], 'patch': r['patch'],
             'observation': r['observation']} for r in campaign.state['records']]
    return {'schema': 'scienceutopia.native-design-view.v1', 'binding': campaign.binding,
            'records': rows, 'records_sha256': digest(rows),
            'pending': campaign.state['pending'],
            'interpretation': {'development_only': True, 'world': 'native-research-world',
                               'recursive_self_improvement': False, 'end_to_end_native_autograd': False}}
