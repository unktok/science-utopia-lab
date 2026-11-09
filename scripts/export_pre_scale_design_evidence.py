"""Closed O/E development cells for the existing read-only Native Foundry.

No model, simulator, authored source or container execution. The full original
audit and exact raw inventory must already be closed; this is a projection,
not another independent scientific audit or a new candidate selection.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.pre_scale_search_v1 import summarize, OBJECTIVES, METHODS
from utopia.optimization.loss import loss_spec_sha256
from utopia.optimization.native_numeric_designer import checked
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import design_difference, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SOURCE = '62388a74d071a3a4fdc8cc309c2807422f96223f'
PLAN = 'db2df5c5e54a68c8201b6b8c460cffa66770ee37da4f7b0d1089c7f5fc7702cb'
SCOPE = 'closed-pre-scale-development-cells-not-unused-seed-generalization'


def envelope(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {'schema': 'scienceutopia.native-design-lab-envelope.v1', 'payload_json': raw,
        'payload_sha256': hashlib.sha256(raw.encode()).hexdigest()}


def cell_run(cell, world, *, years):
    """Read only committed annual frames; a partial attempt is not a full world."""
    proof = world['physical_proof']; spec = SystemSpec.from_dict(world['system'])
    annual = proof.get('annual_checkpoints', [])
    if not annual:
        return []  # No fabricated actors/events for a year-zero failure.
    directory = Path(cell) / 'simulation/checkpoints/native-design'
    frames = []; last_events = []
    for ordinal, item in enumerate(annual, 1):
        if item['year'] != ordinal or ordinal > years:
            raise ValueError('nonconsecutive audited native frame')
        path = directory / f'portable_checkpoint_year_{ordinal}.json.gz'
        if file_sha256(path) != item['checkpoint_sha256']:
            raise ValueError('native frame differs from original audit')
        state = read_portable_checkpoint(path); native = state['native_system']
        if (state['year'] != ordinal or native['system_fingerprint'] != spec.fingerprint
                or native['spec'] != spec.to_dict() or native['events'][:len(last_events)] != last_events):
            raise ValueError('native year, policy or event prefix differs')
        frames.append({'year': ordinal, 'actors': [{key: agent[key] for key in
            ('id', 'type', 'resources', 'is_active', 'can_author')}
            for agent in state['ecosystem_data']['agents'] if agent.get('can_author', False)],
            'paper_count': len(state['paper_tracker']['papers'])})
        last_events = native['events']
    if proof['status'] == 'complete' and len(frames) != years:
        raise ValueError('complete physical trajectory lacks its final annual frame')
    return [{'seed': world['seed'], 'run_id': Path(cell).name, 'frames': frames,
        'events': deepcopy(last_events), 'checkpoint_sha256': annual[-1]['checkpoint_sha256'],
        'physical_forward_status': proof['status']}]


def build(root, plan, audit):
    root = Path(root).resolve(); checked(plan); checked(audit)
    if (plan.get('schema') != 'scienceutopia.pre-scale-search.v1.plan'
            or plan['source_commit'] != SOURCE or audit['source_commit'] != SOURCE
            or plan['content_sha256'] != PLAN or audit['plan_sha256'] != PLAN
            or audit.get('source_proof', {}).get('status') != 'verified-exact-source-closure'
            or audit.get('new_model_calls') != 0 or audit.get('new_code_executions') != 0):
        raise ValueError('exact closed original pre-scale source/plan/audit required')
    closure = checked(json.loads((root / 'complete.json').read_text()))
    if closure['plan_sha256'] != PLAN or closure['selection_sha256'] != audit['selection']['content_sha256']:
        raise ValueError('normal study closure and frozen selection required')
    before = _inventory(root)
    if digest(before) != audit['raw_inventory_sha256'] or len(before) != audit['raw_files']:
        raise ValueError('closed raw inventory differs from original audit')
    report = summarize(audit)  # All slots, physical joins and selection remain those of the audit.
    worlds = {row['identity']: row for row in audit['worlds']}
    initial = next(row for row in audit['selection']['all_rows'] if row['row_id'] == 'reference:open-seed')
    initial_world = worlds[report['development_world_bindings'][initial['row_id']]]
    artifacts = {}
    for objective in OBJECTIVES:
        for method in METHODS:
            arm = objective + ':' + method; directory = root / 'search/run-00' / arm.replace(':', '--')
            records = json.loads((directory / 'campaign/native-adaptive-state.json').read_text())['records']
            if len(records) != 2:
                raise ValueError('two terminal original proposal records required')
            systems = []; unsubmitted = []

            def add(row, world, cell, parent, label, technical_failures):
                spec = SystemSpec.from_dict(world['system']); score = row['cross_scores'][objective]
                runs = cell_run(cell, world, years=4)
                systems.append({'suggestion_id': world['identity'], 'evidence_label': label,
                    'parent_observation_id': None, 'system_fingerprint': spec.fingerprint,
                    'system_spec_json': spec.canonical_json(), 'status': 'complete' if score is not None else 'failed',
                    'native_loss': score, 'technical_failures': deepcopy(technical_failures),
                    'measurements': [] if world['physical_proof'].get('measurement') is None else
                        [deepcopy(world['physical_proof']['measurement'])],
                    'difference': design_difference(SystemSpec.from_dict(parent), spec), 'runs': runs})

            add(initial, initial_world, root / 'references/open-seed/worlds' /
                (initial_world['identity'] + '-s41001'), initial['system'],
                'INITIAL REFERENCE / DEVELOPMENT SEED 41001',
                json.loads((root / 'references/open-seed/observation.json').read_text())['metadata']['technical_failures'])
            for generation, record in enumerate(records):
                row_id = f'run-00:{arm}:g{generation}'
                row = next(r for r in audit['selection']['all_rows'] if r['row_id'] == row_id)
                identity = report['development_world_bindings'][row_id]
                if identity is None:
                    if record['generation_error'] is None or record['observations']:
                        raise ValueError('unsubmitted row has incompatible original campaign evidence')
                    unsubmitted.append({'row_id': row_id, 'generation': generation,
                        'generation_error': deepcopy(record['generation_error'])})
                    continue
                observation, = record['observations']; world = worlds[identity]
                if (observation['suggestion_id'] != identity or observation['candidate'] != row['system']
                        or observation['status'] != row['status'] or record['generation_error'] is not None):
                    raise ValueError('original proposal and audited physical world differ')
                add(row, world, directory / 'worlds' / (identity + '-s41001'),
                    record['request']['parent_system'], f'G{generation} / {arm} / DEVELOPMENT SEED 41001',
                    observation['metadata']['technical_failures'])
            payload = {'schema': 'scienceutopia.native-design-lab.v1',
                'source': {'world': deepcopy(plan['world']), 'loss_spec_sha256': loss_spec_sha256(plan['losses'][objective])},
                'systems': systems, 'relaxation': None, 'pending': None,
                'interpretation': {'world': 'original-native-researcher-world', 'model_weights_trained': False,
                    'full_native_world_autograd': False, 'live_player_intervention': False,
                    'spatial_layout': 'schematic-only', 'development_only': True,
                    'pre_scale_arm': arm, 'scope': SCOPE, 'plan_sha256': PLAN,
                    'original_audit_content_sha256': audit['content_sha256'],
                    'unsubmitted_slots': unsubmitted,
                    'selection_is_not_recomputed_by_viewer': True}}
            artifacts[arm.replace(':', '--') + '.json'] = envelope(payload)
    if _inventory(root) != before:
        raise ValueError('raw evidence changed during read-only export')
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'audit', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(); root = args.run.resolve(); output = args.output.resolve()
    if output.exists() or output.is_relative_to(root):
        raise ValueError('fresh independent evidence destination required')
    audit_hash = file_sha256(args.audit)
    plan = json.loads((root / 'plan.json').read_text()); audit = json.loads(args.audit.read_text())
    artifacts = build(root, plan, audit)
    if file_sha256(args.audit) != audit_hash:
        raise ValueError('audit changed during export')
    output.mkdir(parents=True)
    for filename, value in artifacts.items():
        write_json_atomic(output / filename, value, sort_keys=True, allow_nan=False)
    manifest = {'schema': 'scienceutopia.pre-scale-foundry-export.v1', 'source_commit': SOURCE,
        'plan_sha256': PLAN, 'original_audit_file_sha256': audit_hash,
        'files': {filename: file_sha256(output / filename) for filename in artifacts},
        'scope': SCOPE, 'new_model_calls': 0, 'new_authored_code_executions': 0,
        'independent_original_audit': False}
    write_json_atomic(output / 'manifest.json', {**manifest, 'content_sha256': digest(manifest)},
        sort_keys=True, allow_nan=False)
    print(json.dumps({'output': str(output), 'files': len(artifacts), 'new_model_calls': 0}))


if __name__ == '__main__':
    main()
