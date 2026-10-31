"""Native design-campaign UI evidence, not a browser simulator or city fiction."""
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_design import NativeDesignCampaign
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.native_kernel import NativeScienceKernel
from utopia.utils.data_utils import file_sha256


def native_lab_envelope(run, *, loss_spec):
    run = Path(run)
    path = run / 'campaign' / 'native-design-state.json'
    saved = json.loads(path.read_text())
    if not saved['records']: raise ValueError('no completed native observations to export')
    campaign = NativeDesignCampaign(run / 'campaign', initial_system=SystemSpec.from_dict(saved['records'][0]['parent_system']),
        loss_spec=loss_spec, seeds=saved['binding']['seeds'], world_binding=saved['binding']['world'])
    systems = []
    for record in campaign.state['records']:
        observation = record['observation']
        spec = SystemSpec.from_dict(record['suggestion']['candidate'])
        rows = []
        for evidence in observation['metadata']['runs']:
            cell = run / 'runs' / evidence['run_id']
            root = cell / 'simulation' / 'checkpoints' / 'native-design'
            years = saved['binding']['world']['years']
            final_path = Path(evidence['checkpoint_path']) if evidence.get('checkpoint_path') else root / f'portable_checkpoint_year_{years}.json.gz'
            root = final_path.parent
            final = read_portable_checkpoint(final_path)
            kernel = NativeScienceKernel(spec, checkpoint=final['native_system'])
            if kernel.to_dict()['event_stream_hash'] != evidence['event_stream_hash'] or kernel.last_year != years:
                raise ValueError('native UI kernel/run identity changed')
            frames = []
            for year in range(1, years + 1):
                state = read_portable_checkpoint(root / f'portable_checkpoint_year_{year}.json.gz')
                if state['native_system']['system_fingerprint'] != spec.fingerprint:
                    raise ValueError('native UI year frame belongs to another candidate')
                frames.append({'year': year, 'actors': [{k: agent[k] for k in ('id', 'type', 'resources', 'is_active', 'can_author')}
                    for agent in state['ecosystem_data']['agents'] if agent.get('can_author', False)],
                    'paper_count': len(state['paper_tracker']['papers'])})
            rows.append({'seed': evidence['seed'], 'run_id': evidence['run_id'],
                'checkpoint_sha256': file_sha256(final_path), 'frames': frames,
                'native_event_stream_hash': evidence['event_stream_hash'],
                'events': [e.to_dict() for e in kernel.events]})
        systems.append({'suggestion_id': record['suggestion']['suggestion_id'],
            'parent_observation_id': record['suggestion']['based_on_observation_id'],
            'system_fingerprint': spec.fingerprint, 'system_spec_json': spec.canonical_json(),
            'status': observation['status'], 'native_loss': observation['loss'],
            'technical_failures': observation['metadata']['technical_failures'],
            'measurements': observation['metadata']['measurements'],
            'difference': {k: record['difference'][k] for k in ('nodes_added', 'nodes_changed', 'nodes_removed')}, 'runs': rows})
    fit_path = run / 'relaxation.json'
    fit = json.loads(fit_path.read_text()) if fit_path.exists() else None
    payload = {'schema': 'scienceutopia.native-design-lab.v1', 'source': saved['binding'], 'systems': systems,
        'relaxation': None if fit is None else {k: fit[k] for k in ('trace_sha256', 'history', 'terms', 'conditional_hard_loss_after', 'temperature', 'scope', 'full_native_world_autograd')},
        'interpretation': {'world': 'original-native-researcher-world', 'model_weights_trained': False,
            'full_native_world_autograd': False, 'live_player_intervention': False,
            'spatial_layout': 'schematic-only', 'development_only': True},
        'pending': None if campaign.state['pending'] is None else campaign.state['pending']['suggestion']['suggestion_id']}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {'schema': 'scienceutopia.native-design-lab-envelope.v1', 'payload_json': raw,
            'payload_sha256': hashlib.sha256(raw.encode()).hexdigest()}
