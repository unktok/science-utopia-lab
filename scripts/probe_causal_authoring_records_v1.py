"""Execute every available authored selector on four frozen native inputs.

Partial mechanism probes, not native worlds, policy rollouts or new loss values.
Only the pinned networkless Docker executor runs authored Python.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.run_causal_authoring_assay_v1 import HISTORICAL_SOURCE
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.optimization.native_code_trace import validate_record
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import DockerCodeExecutor, sha
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.causal-authoring-record-probe.v1'
PROTOCOL = 'research/protocols/campaigns/causal-authoring-record-probe-v1.md'


def read(path):
    return json.loads(Path(path).read_text())


def emitted_summary(result, context):
    world = context['inputs']['observations'][0]['payload']
    expected = [(c['conference_id'], p['id']) for c in world['conferences']['conferences']
                for p in c['submitted_papers']]
    payloads = [m['payload'] for m in result['outputs'].get('decisions', [])]
    empty = payloads == [{'empty_cycle': True}]
    ordinary = [] if empty else payloads
    actual = [(p.get('conference_id'), p.get('paper_id')) for p in ordinary]
    # Output identities are untrusted JSON, not necessarily hashable strings.
    # Hash exact JSON instead of Python equality (which also conflates 1/True).
    expected_keys = [digest(list(pair)) for pair in expected]
    actual_keys = [digest(list(pair)) for pair in actual]
    return {'expected_papers': len(expected), 'emitted_decisions': len(ordinary),
        'decision_labels': dict(sorted(Counter(str(p.get('decision')) for p in ordinary).items())),
        'exact_identity_coverage': Counter(expected_keys) == Counter(actual_keys),
        'duplicate_identity_count': len(actual_keys)-len(set(actual_keys)),
        'empty_cycle_marker': empty,
        'native_receiver_executed': False, 'new_loss': None}


def prepare(output, assay_root, audit_path, contexts_path, system_path):
    if output.exists():
        raise ValueError('fresh post-hoc probe output required')
    source = pinned_revision(ROOT)
    audit = checked(read(audit_path)); assay_plan = checked(read(assay_root/'plan.json'))
    if (audit['plan_sha256'] != file_sha256(assay_root/'plan.json')
            or audit['terminal']['status'] != 'complete' or len(audit['slots']) != 8
            or audit['source_commit'] != assay_plan['source_commit']):
        raise ValueError('complete original-source eight-slot audit required')
    native = SystemSpec.from_dict(read(system_path))
    node = next(n for n in native.mechanisms if n.mechanism_id == 'world.selection')
    frames = []
    for line in contexts_path.read_text().splitlines():
        record = validate_record(json.loads(line))
        if (record['binding']['source_commit'] != HISTORICAL_SOURCE
                or record['binding']['system_fingerprint'] != native.fingerprint):
            raise ValueError('historical source/system differs')
        if record['artifact'] == node.parameters['code_artifact']:
            frames.append(record)
    if [f['context']['period'] for f in frames] != [1, 2, 3, 4]:
        raise ValueError('exact four chronological native selection frames required')
    candidates = []
    for slot, row in zip(assay_plan['slots'], audit['slots']):
        if slot['id'] != row['id'] or slot['request_sha256'] != row['request_sha256']:
            raise ValueError('audit/plan slot order differs')
        candidate = {'id': slot['id'], 'audit_status': row['status'], 'system': None}
        if row['status'] == 'static-valid-submission':
            worker = checked(read(assay_root/'sessions'/slot['id']/'worker-result.json'))
            definition = worker['definition']; request = slot['request']
            mixed = GeneratedMixedDesign(SystemSpec.from_dict(request['parent_system']), definition,
                loss_spec=request['loss_spec'], seed=request['rng_seed'], single_draw_blackbox=True)
            draw = mixed.draw(1, version_sha256=digest(definition), proposal_start=0, based_on=None)[0]
            system = SystemSpec.from_dict(draw['suggestion']['candidate'])
            if system.fingerprint != row['candidate_sha256']:
                raise ValueError('compiled candidate differs from original-source cold replay')
            nodes = request['parent_system']['mechanisms']
            selection_index = next(i for i, n in enumerate(nodes) if n['mechanism_id'] == 'world.selection')
            selection_path = f'/mechanisms/{selection_index}/parameters/code_artifact/source'
            candidate.update(system=system.to_dict(), candidate_sha256=system.fingerprint,
                whole_graph_unchanged_except_selection_source=all(
                    p == selection_path for p in row['changed_paths']))
        candidates.append(candidate)
    plan = {'schema': SCHEMA+'.plan', 'source_commit': source,
        'assay_source_commit': assay_plan['source_commit'], 'audit_file_sha256': file_sha256(audit_path),
        'protocol_sha256': file_sha256(ROOT/PROTOCOL), 'image_id': node.parameters['runtime_image_id'],
        'historical_contexts_file_sha256': file_sha256(contexts_path),
        'historical_system_file_sha256': file_sha256(system_path),
        'frames': frames, 'candidates': candidates,
        'budget': {'original_replays': 4, 'candidate_slots': 8,
            'candidate_executions_upper_bound': 32, 'total_executions_upper_bound': 36,
            'container_seconds_each': 15, 'model_calls': 0, 'native_worlds': 0, 'replace_failures': False},
        'interpretation': 'Post-hoc fixed-record partial-selector execution. Historical state/inputs/clock/seed '
            'are fixed independently per frame, not rolled forward. Candidate parameters replace old parameters. '
            'No new native decisions, review work, scientist actions or losses are measured.'}
    output.mkdir(parents=True)
    save(output/'plan.json', plan)


def run(output):
    plan = checked(read(output/'plan.json'))
    if plan['source_commit'] != pinned_revision(ROOT) or plan['protocol_sha256'] != file_sha256(ROOT/PROTOCOL):
        raise ValueError('probe clean source/protocol changed')
    # Exclusive creation consumes the run before the first container call.
    with (output/'consumed.json').open('x') as handle:
        json.dump({'plan_sha256': file_sha256(output/'plan.json')}, handle)
    executor = DockerCodeExecutor(plan['image_id'], timeout=15)
    if executor.image_id != plan['image_id']:
        raise ValueError('probe image differs')
    rows = []
    # Verify all original result bytes first. Never probe a candidate against
    # a baseline whose exact container replay has failed.
    for index, frame in enumerate(plan['frames']):
        execution = executor.execute(frame['artifact'], frame['context'])
        save(output/f'original-{index}.json', {'schema': SCHEMA+'.original',
            'bundle_sha256': frame['bundle_sha256'], 'result': execution.result, 'receipt': execution.receipt})
        if execution.result != frame['result']:
            raise ValueError('original historical container result did not replay exactly')
    for candidate in plan['candidates']:
        row = {k: v for k, v in candidate.items() if k != 'system'}
        row['frames'] = []
        if candidate['system'] is None:
            row['status'] = 'no-static-valid-candidate'
        else:
            system = SystemSpec.from_dict(candidate['system'])
            node = next((n for n in system.mechanisms if n.mechanism_id == 'world.selection'), None)
            if node is None or node.implementation != 'code.python.v1':
                row['status'] = 'selector-not-applicable'
            else:
                if node.parameters['runtime_image_id'] != plan['image_id']:
                    raise ValueError('candidate requested different image')
                for index, frame in enumerate(plan['frames']):
                    context = clone(frame['context'])
                    context['parameters'] = {k: clone(v) for k, v in node.parameters.items()
                                             if k not in ('runtime_image_id', 'code_artifact')}
                    result = {'schema': SCHEMA+'.frame', 'period': context['period'],
                        'historical_bundle_sha256': frame['bundle_sha256'],
                        'context_sha256': sha(context), 'status': 'failed'}
                    try:
                        executed = executor.execute(node.parameters['code_artifact'], context)
                        result.update(status='executed', result=executed.result, receipt=executed.receipt)
                        result['emitted_summary'] = emitted_summary(executed.result, context)
                    except Exception as error:
                        result.update(error_type=type(error).__name__, error=str(error))
                    path = output/'candidates'/candidate['id']/f'frame-{index}.json'
                    save(path, result)
                    row['frames'].append({k: v for k, v in result.items()
                                          if k not in ('result', 'receipt', 'schema')})
                row['status'] = 'all-frames-executed' if all(x['status'] == 'executed'
                    for x in row['frames']) else 'one-or-more-frames-failed'
        rows.append(row)
    save(output/'report.json', {'schema': SCHEMA+'.report', 'source_commit': plan['source_commit'],
        'plan_file_sha256': file_sha256(output/'plan.json'), 'audit_file_sha256': plan['audit_file_sha256'],
        'slots': rows, 'original_exact_replays': 4, 'model_calls': 0, 'native_worlds': 0,
        'measured_candidate_losses': 0, 'interpretation': plan['interpretation']})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('prepare', 'run')); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--assay-root', type=Path); p.add_argument('--audit', type=Path)
    p.add_argument('--contexts', type=Path); p.add_argument('--system', type=Path)
    args = p.parse_args()
    if args.command == 'prepare':
        if not all((args.assay_root, args.audit, args.contexts, args.system)):
            p.error('prepare requires --assay-root, --audit, --contexts, --system')
        prepare(args.output, args.assay_root, args.audit, args.contexts, args.system)
    else:
        run(args.output)


if __name__ == '__main__':
    main()
