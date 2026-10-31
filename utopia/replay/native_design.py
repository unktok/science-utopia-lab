"""Export native design/loss lineage and replay using authoritative state only."""
from pathlib import Path

from .converter import ArtifactBundle, convert_artifacts
from .viewer import build_viewer_payload_v2
from .campaign_adapter import web_event_stream_hash, validate_portable_bundle
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.design_patch import digest


def native_design_replay(checkpoint, *, expected_system_fingerprint, label):
    state = read_portable_checkpoint(Path(checkpoint))
    native = state.get('native_system')
    if not native or native['system_fingerprint'] != expected_system_fingerprint:
        raise ValueError('native design replay and candidate identity differ')
    events = convert_artifacts(ArtifactBundle.discover(checkpoint))
    payload = build_viewer_payload_v2(events, metadata={
        'title': label, 'source_kind': 'native-design-development-run',
        'system_fingerprint': expected_system_fingerprint,
        'empirical': False,
        'native_presentation_pending': True,
        'disclosure': 'Native development evidence; not a released verified-campaign source, scientific improvement or live player intervention. ' + label,
        'interpretation': 'Canonical evidence, not scientific improvement or live player intervention'})
    payload['web_stream_hash'] = web_event_stream_hash(payload['canonical']['events'])
    payload['web_stream_hash_algorithm'] = 'scienceutopia.web-f64-json-sha256.v1'
    validate_portable_bundle(payload)
    return payload


def native_design_view(campaign):
    campaign._validate()
    rows = [{'suggestion': r['suggestion'], 'difference': r['difference'], 'patch': r['patch'],
             'observation': r['observation']} for r in campaign.state['records']]
    return {'schema': 'scienceutopia.native-design-view.v1', 'binding': campaign.binding,
            'records': rows, 'records_sha256': digest(rows),
            'pending': campaign.state['pending'],
            'interpretation': {'development_only': True, 'world': 'native-research-world',
                               'recursive_self_improvement': False, 'end_to_end_native_autograd': False}}
