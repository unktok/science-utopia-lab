#!/usr/bin/env python3
"""Freeze four audited original native worlds; train probabilities offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build_bank(receipt):
    from utopia.optimization.loss import loss_spec_sha256
    from utopia.optimization.native_cost_bank import BANK_SCHEMA, validate_bank
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.utils.data_utils import file_sha256
    receipt = Path(receipt).resolve()
    audited = json.loads(receipt.read_text())
    if not audited['raw_outputs_unchanged'] or audited['new_native_executions'] != 0:
        raise ValueError('read-only independently audited native receipt required')
    calibration = audited['calibration']
    if len(calibration['cells']) != 6 or calibration['pending_cells'] or 'analysis_error' in calibration:
        raise ValueError('complete independent calibration receipt required')
    upstream = Path(calibration['raw_output_root'])
    plan = json.loads((upstream / 'plan.json').read_text())
    entries, seeds = [], None
    for cell in calibration['cells'][:4]:
        state_path = upstream / 'cells' / cell['name'] / 'campaign/native-design-state.json'
        saved = json.loads(state_path.read_text())
        if len(saved['records']) != 1 or saved['pending'] is not None:
            raise ValueError('one terminal native world per bank entry required')
        record = saved['records'][0]
        if file_sha256(state_path) != cell['audit']['campaign_sha256']:
            raise ValueError('campaign changed after independent audit')
        candidate = record['suggestion']['candidate']
        system = SystemSpec.from_dict(candidate)
        observation = record['observation']
        if observation['loss'] != cell['actual_loss'] or observation['metadata']['technical_failures']:
            raise ValueError('native cost or technical validity differs')
        if seeds is None:
            seeds = saved['binding']['seeds']
        if seeds != saved['binding']['seeds']:
            raise ValueError('all bank entries must share native seeds')
        runs = []
        for evidence, proof in zip(observation['metadata']['runs'], cell['audit']['rows'][0]['runs']):
            checkpoint = Path(proof['checkpoint'])
            if file_sha256(checkpoint) != proof['checkpoint_sha256']:
                raise ValueError('native bank checkpoint changed after independent audit')
            portable = read_portable_checkpoint(checkpoint)
            binding = portable['portable']['contract']['binding']
            world = calibration['world']
            if (binding['cell'] != system.fingerprint or binding['seed'] != evidence['seed']
                    or binding['model_revision'] != world['model_digest']
                    or binding['corpus_sha256'] != world['corpus_sha256']
                    or binding['science_config']['source_commit'] != world['source_commit']):
                raise ValueError('frozen bank native design/model/source/corpus/RNG binding differs')
            runs.append({'run_id': proof['run_id'], 'seed': evidence['seed'],
                'checkpoint': str(checkpoint), 'checkpoint_sha256': proof['checkpoint_sha256'],
                'response_cache_sha256': proof['response_cache_sha256'],
                'wire_sha256': proof['wire']['wire_sha256'], 'native_requests': proof['wire']['actual_requests'],
                'native_event_stream_hash': proof['native_event_stream_hash']})
        entries.append({'id': cell['name'], 'candidate': candidate, 'system_fingerprint': system.fingerprint,
            'controls': cell['controls'], 'loss': observation['loss'],
            'measurements': observation['metadata']['measurements'], 'runs': runs,
            'campaign_sha256': cell['audit']['campaign_sha256']})
    return validate_bank({'schema': BANK_SCHEMA, 'world': calibration['world'], 'seeds': seeds,
        'common_initial_world_sha256': calibration['representation']['provenance']['binding']['initial_world_sha256'],
        'loss_spec': plan['loss_spec'], 'loss_spec_sha256': loss_spec_sha256(plan['loss_spec']),
        'bank_origin': 'first four independently audited native calibration worlds; validation worlds excluded',
        'independent_audit_receipt': str(receipt), 'independent_audit_sha256': file_sha256(receipt),
        'entries': entries})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from utopia.optimization.native_cost_bank import optimize_bank
    from utopia.utils.data_utils import write_json_atomic
    bank = build_bank(args.audit_receipt)
    result = optimize_bank(bank)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json_atomic(args.output / 'bank.json', bank, sort_keys=True, allow_nan=False)
    write_json_atomic(args.output / 'result.json', result, sort_keys=True, allow_nan=False)
    print(json.dumps({k: result[k] for k in ('initial_expected_loss', 'final_expected_loss',
        'best_already_observed_native_loss', 'new_native_executions', 'new_native_best_discovered')}))


if __name__ == '__main__':
    main()
