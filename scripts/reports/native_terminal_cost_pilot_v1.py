"""Literal terminal-cost readout from paired closed audits/costs; no inference."""
import argparse
import csv
import fcntl
import json
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_content_overlap_v1 import overlap
from scripts.reports.native_institution_effect_trace_v1 import checkpoint
from scripts.reports.native_legacy_topic_pilot_v1 import summarize_world
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_resource_cost import INSTRUMENT
from utopia.system.design_patch import clone, digest
from utopia.system.native_resource_transfers import EVENT
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-terminal-cost-pilot-readout.v1'
LABELS = ['strong-related-reference', 'terminal-consolidation']


def request_position(wires, index):
    if index == len(wires):
        return None
    wire = wires[index]
    payload = wire['payload']
    return {'year': wire['year'], 'payload_sha256': digest(payload),
        'response_schema': payload.get('response_format', {}).get('json_schema', {}).get('name'),
        'native_phase': None, 'phase_scope': 'Wire records contain year, not an independently observed phase.'}


def export(args):
    root, frozen, out = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    source, reader = pinned_revision(frozen), pinned_revision(ROOT)
    if out.exists() or any(out.is_relative_to(p) for p in (root, frozen, ROOT)):
        raise ValueError('fresh readout outside scientific raw and both sources required')
    pairs = [[getattr(args, f'{kind}_{i}').resolve() for i in ('one', 'two')]
             for kind in ('audit', 'cost')]
    if any(paths[0] == paths[1] or paths[0].read_bytes() != paths[1].read_bytes() for paths in pairs):
        raise ValueError('distinct matching original audit and cost pairs required')
    paths = [root / 'plan.json', *pairs[0], *pairs[1]]
    inputs = {str(path): file_sha256(path) for path in paths}
    with (root / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root)
        plan, audit, cost = [checked(json.loads(path.read_text())) for path in (paths[0], paths[1], paths[3])]
        if (plan['schema'] != 'scienceutopia.native-terminal-cost-pilot.v1.plan'
                or audit['schema'] != 'scienceutopia.native-terminal-cost-pilot-audit.v1'
                or plan['source_commit'] != source or audit['source_commit'] != source
                or audit['plan_sha256'] != plan['content_sha256']
                or audit['closure']['terminal'] != checked(json.loads((root / 'terminal.json').read_text()))
                or audit['closure']['terminal']['status'] != 'closed'
                or audit['source_proof']['status'] != 'verified-exact-source-closure'
                or digest(before) != audit['raw_inventory_sha256'] or len(audit['worlds']) != 2
                or [job['condition'] for job in plan['jobs']] != LABELS
                or audit['automatic_invention'] or audit['policy_selection'] or audit['held_out_world_seeds']
                or cost['source_commit'] != source or cost['plan_sha256'] != plan['content_sha256']
                or cost['input_audit_content_sha256'] != audit['content_sha256']
                or cost['raw_inventory_sha256'] != audit['raw_inventory_sha256']
                or cost['new_model_calls'] != 0 or cost['new_code_executions'] != 0):
            raise ValueError('exact closed two-control source/audit/cost/raw required')
        worlds, sequences = [], []
        for job, world in zip(plan['jobs'], audit['worlds']):
            if any(world[key] != value for key, value in job.items()):
                raise ValueError('literal ordered developer control differs')
            row, wires = summarize_world(root, world)
            cell = Path(world['loaded']['context']).resolve().parent
            state = checkpoint(cell, world['physical_proof']['annual_checkpoints'][-1], world['system'])
            instrument = world['measurements'][0][INSTRUMENT]
            annual = []
            for value in instrument['annual']:
                annual.append({**clone(value), 'requested_activity_cost':
                    value['collected_activity_cost'] + value['uncollected_activity_cost'],
                    'closing_resources': math.fsum(a['closing_balance'] for a in value['reconciled_authors']),
                    'closing_active_authors': sum(a['closing_active'] for a in value['reconciled_authors'])})
            transfers = [clone(event) for event in state['native_system']['events'] if event['event_type'] == EVENT]
            for event in transfers:
                receipt = event['payload']
                if (not math.isclose(math.fsum(receipt['balances_before'].values()),
                                     math.fsum(receipt['balances_after'].values()), rel_tol=0, abs_tol=1e-9)
                        or receipt['actual_debit'] != receipt['actual_credit']):
                    raise ValueError('audited literal transfer does not conserve native balances')
            worlds.append({**row, 'annual_resource_categories': annual,
                'requested_activity_cost': math.fsum(a['requested_activity_cost'] for a in annual),
                'native_transfers': transfers, 'final_active_authors': annual[-1]['closing_active_authors'],
                'final_resources': annual[-1]['closing_resources'],
                'institution_system_fingerprint': world['measurements'][0]['system_fingerprint']})
            sequences.append(wires)
        left, right = [[wire['payload'] for wire in sequence] for sequence in sequences]
        index = next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), min(len(left), len(right)))
        first = None if left == right else {'zero_based_wire_index': index,
            'left': request_position(sequences[0], index), 'right': request_position(sequences[1], index)}
        delta_u = worlds[1]['scores']['content-utility'] - worlds[0]['scores']['content-utility']
        delta_k = worlds[1]['resource_cost'] - worlds[0]['resource_cost']
        delta_c = worlds[1]['scores']['resource-aware-content'] - worlds[0]['scores']['resource-aware-content']
        if not math.isclose(delta_c, delta_u + 0.1 * delta_k, rel_tol=0, abs_tol=1e-9):
            raise ValueError('original declared C contrast does not reconcile with U and collected K')
        result = {'schema': SCHEMA, 'analysis_source_commit': reader, 'scientific_source_commit': source,
            'plan_sha256': plan['content_sha256'], 'audit_content_sha256': audit['content_sha256'],
            'cost_content_sha256': cost['content_sha256'], 'raw_inventory_sha256': digest(before),
            'worlds': worlds, 'accepted_content_overlap': overlap(worlds[0]['accepted_content'], worlds[1]['accepted_content']),
            'full_scientist_request_sequences_equal': left == right, 'first_literal_request_difference': first,
            'loss_contrast_control_minus_reference': {'content_loss': delta_u, 'collected_cost': delta_k,
                'resource_coefficient': 0.1, 'resource_aware_content_loss': delta_c},
            'scope': 'Two development-informed hand controls on one reused condition; no automatic invention, '
                'independent optimizer replication or global optimum. Collected versus requested/unpaid cost '
                'and terminal participation are reported without a veto. Input equality is not program equivalence. '
                'A C gain need not mean real resource efficiency, better science, welfare or improvement beyond the horizon.',
            'new_model_calls': 0, 'new_code_executions': 0, 'loss_or_selection_changed': False,
            'held_out_evaluation': False, 'automatic_invention': False, 'publication_ready': False}
        if (before != _inventory(root) or inputs != {str(path): file_sha256(path) for path in paths}
                or pinned_revision(frozen) != source or pinned_revision(ROOT) != reader):
            raise ValueError('scientific raw or pinned source changed during readout')
    out.mkdir(parents=True)
    save(out / 'report.json', result)
    fields = ['condition', 'seed', 'throughput', 'content-utility', 'resource-aware-content',
              'resource_cost', 'uncollected_activity_cost', 'requested_activity_cost',
              'final_active_authors', 'final_resources']
    with (out / 'controls.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({key: row['scores'][key] if key in row['scores'] else row[key]
                         for key in fields} for row in worlds)
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': inputs,
        'analysis_source_commit': reader, 'adapter_file_sha256': file_sha256(Path(__file__)),
        'files': {path.name: file_sha256(path) for path in sorted(out.iterdir())},
        'new_model_calls': 0, 'new_code_executions': 0})
    print(json.dumps({'worlds': len(worlds), 'content_loss_delta': delta_u, 'K_delta': delta_k, 'C_delta': delta_c}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'audit-one', 'audit-two', 'cost-one', 'cost-two', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__':
    main()
