"""Conditional reserve-command response on four closed native R7 input frames.

This executes the unchanged archived component in Docker, NOT alternative
scientist worlds, a loss optimization or committed counterfactual transfers.
The live designer and numeric comparator never receive these diagnostic data.
"""
import argparse
from copy import deepcopy
import csv
import json
from pathlib import Path
import time

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import utc
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.code_mechanisms import DockerCodeExecutor, sha
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-reserve-response.v1'
REFERENCE = 'assignment-reserve21-no-review-all'
RESERVES = list(range(1, 61))


def command_summary(result, frame):
    """Report commands only; do not emulate native resource commitment/loss."""
    actors = {a['id']: a for a in frame['context']['inputs']['world'][0]['payload']['ecosystem']['agents']
        if a['can_author'] and a['is_active']}
    funds = result['outputs']['funds']; sent = {}; received = {}; ids = set()
    for value in funds:
        item = value['payload']; amount = item['amount']; source, target = item['from_actor'], item['to_actor']
        if (type(amount) is not int or amount <= 0 or source == target or source not in actors or target not in actors
                or item['transaction_id'] in ids):
            raise ValueError('finite positive whole-unit conserving commands over actual active authors required')
        ids.add(item['transaction_id']); sent[source] = sent.get(source, 0) + amount
        received[target] = received.get(target, 0) + amount
    if any(amount > actors[source]['resources'] for source, amount in sent.items()):
        raise ValueError('commanded outgoing funds exceed observed sender balance')
    return {'command_count': len(funds), 'recipient_count': len(received), 'requested_units': sum(sent.values()),
        'transfer_payload_sha256': sha(funds), 'result_sha256': sha(result)}


def intervals(rows):
    """Adjacent integer values with the same exact requested transfer payload."""
    result = []
    for row in rows:
        if result and row['reserve_units'] != result[-1]['upper'] + 1:
            raise ValueError('adjacent integer reserve observations required; never fill an unobserved gap')
        if result and result[-1]['transfer_payload_sha256'] == row['transfer_payload_sha256']:
            result[-1]['upper'] = row['reserve_units']
        else:
            result.append({'lower': row['reserve_units'], 'upper': row['reserve_units'],
                **{k: row[k] for k in ('transfer_payload_sha256', 'command_count', 'recipient_count', 'requested_units')}})
    return result


def render(rows, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
        for ax, field, ylabel in zip(axes, ('requested_units', 'recipient_count'), ('Requested transfer units', 'Recipients in requested commands')):
            for year, color in zip(range(1, 5), ('#087f8c', '#9c5d8a', '#b47835', '#536c45')):
                selected = [r for r in rows if r['year'] == year]
                ax.step([r['reserve_units'] for r in selected], [r[field] for r in selected], where='mid',
                    color=color, label='Historical year ' + str(year), lw=1.5)
            for value in (10, 21): ax.axvline(value, color='#777777', lw=.7, ls=':')
            ax.set(xlabel='Reserve parameter (integer 1–60)', ylabel=ylabel, xlim=(1, 60))
            ax.yaxis.set_major_locator(MaxNLocator(integer=True)); ax.grid(axis='y', color='#ededed'); ax.legend(fontsize=6.5)
        fig.suptitle('Same archived component, fixed historical native inputs: reserve-to-command response', fontsize=10)
        fig.text(.045, .035, 'Conditional component diagnostic, not alternative world outcomes or loss improvement. '
            'Dotted lines: existing reserve10/21 controls.', fontsize=6.8)
        fig.tight_layout(rect=(0, .07, 1, .94))
        for ext in ('png', 'svg'):
            fig.savefig(output / ('reserve-command-response.' + ext), dpi=200, metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def run(args):
    root, original, output = (Path(getattr(args, k)).resolve() for k in ('run', 'scientific_source', 'output'))
    inputs = [Path(args.audit_one).resolve(), Path(args.audit_two).resolve(), root / 'plan.json']
    if (output.exists() or output.is_relative_to(root) or output.is_relative_to(original)
            or inputs[0] == inputs[1] or inputs[0].read_bytes() != inputs[1].read_bytes()):
        raise ValueError('fresh independent output and distinct matching closed original audit pair required')
    analysis = pinned_revision(ROOT); scientific = pinned_revision(original)
    audit, plan = checked(json.loads(inputs[0].read_text())), checked(json.loads(inputs[2].read_text()))
    inventory = _inventory(root)
    if (audit['schema'] != 'scienceutopia.native-planning-objective-loop-audit.v1'
            or audit['source_commit'] != scientific or plan['source_commit'] != scientific
            or audit['plan_sha256'] != plan['content_sha256'] or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or digest(inventory) != audit['raw_inventory_sha256'] or len(inventory) != audit['raw_files']):
        raise ValueError('exact normally closed original planning source, plan and raw inventory required')
    executor_file = 'utopia/system/code_mechanisms.py'
    if file_sha256(ROOT / executor_file) != file_sha256(original / executor_file):
        raise ValueError('archived code-executor bytes differ; no compatible replacement')
    context_file = root / ('references/' + REFERENCE + '/worlds/reference-' + REFERENCE + '-s61001/code-contexts.jsonl')
    inputs.append(context_file); hashes = {str(p): file_sha256(p) for p in inputs}
    frames = [json.loads(line) for line in context_file.read_text().splitlines()]
    frames = [f for f in frames if f['context']['parameters'].get('allocation_rule') == 'reserve-proximity'
        and f['context']['parameters'].get('reserve_units') == 21]
    artifact = next(n['parameters']['code_artifact'] for n in plan['reference_systems'][REFERENCE]['mechanisms']
        if n['mechanism_id'] == 'developer-liquidity-director')
    if len(frames) != 4 or [f['context']['period'] for f in frames] != [1, 2, 3, 4]:
        raise ValueError('exact four original annual allocation frames required')
    for f in frames:
        if f['artifact'] != artifact or any(f['receipt'][key + '_sha256'] != sha(f[key]) for key in ('artifact', 'context', 'result')):
            raise ValueError('original artifact/context/result receipt differs')
    if len({f['receipt']['image_id'] for f in frames}) != 1:
        raise ValueError('one original pinned local image required')
    executor = DockerCodeExecutor(image=frames[0]['receipt']['image_id'], timeout=15)
    if executor.image_id != frames[0]['receipt']['image_id']:
        raise ValueError('local execution image differs from the archived image')
    output.mkdir(parents=True); rows = []; attempts = 0; deadline = time.monotonic() + 300; stage = 'profile'
    save(output / 'started.json', {'schema': SCHEMA + '.start', 'started_utc': utc(), 'analysis_source_commit': analysis,
        'scientific_source_commit': scientific, 'inputs': hashes, 'maximum_component_executions': 240,
        'safe_point_seconds': 300, 'per_execution_seconds': 15, 'reserve_values': RESERVES, 'new_model_calls': 0, 'new_native_worlds': 0})
    try:
        for frame in frames:
            for reserve in RESERVES:
                if time.monotonic() > deadline: raise TimeoutError('finite component profile safe-point allowance exceeded; no retry')
                context = deepcopy(frame['context']); context['parameters']['reserve_units'] = reserve
                call = output / 'calls' / ('year-' + str(context['period']) + '-reserve-' + str(reserve).zfill(2))
                save(call.with_suffix('.started.json'), {'year': context['period'], 'reserve_units': reserve,
                    'original_context_sha256': frame['receipt']['context_sha256'], 'variant_context_sha256': sha(context),
                    'artifact_sha256': sha(frame['artifact']), 'started_utc': utc()})
                attempts += 1
                execution = executor.execute(frame['artifact'], context)
                row = {'year': context['period'], 'reserve_units': reserve, **command_summary(execution.result, frame)}
                if reserve == 21 and execution.result != frame['result']:
                    raise ValueError('original reserve21 isolated replay differs from its recorded result')
                save(call.with_suffix('.json'),
                    {'row': row, 'receipt': execution.receipt, 'result': execution.result})
                rows.append(row)
        stage = 'summarize'
        if hashes != {str(p): file_sha256(p) for p in inputs} or inventory != _inventory(root) or pinned_revision(ROOT) != analysis or pinned_revision(original) != scientific:
            raise ValueError('original inputs/raw or pinned source changed')
        frame_summaries = [{'year': f['context']['period'], 'context_sha256': f['receipt']['context_sha256'],
            'active_author_inputs': [{k: a[k] for k in ('id', 'resources', 'project_end_year')} for a in
                f['context']['inputs']['world'][0]['payload']['ecosystem']['agents'] if a['can_author'] and a['is_active']],
            'distinct_transfer_outputs': len({r['transfer_payload_sha256'] for r in rows if r['year'] == f['context']['period']}),
            'adjacent_equal_output_intervals': intervals([r for r in rows if r['year'] == f['context']['period']])} for f in frames]
        save(output / 'report.json', {'schema': SCHEMA + '.report', 'analysis_source_commit': analysis,
            'scientific_source_commit': scientific, 'audit_content_sha256': audit['content_sha256'], 'plan_content_sha256': plan['content_sha256'],
            'raw_inventory_sha256': audit['raw_inventory_sha256'], 'inputs': hashes, 'reference': REFERENCE,
            'image_id': executor.image_id, 'source': artifact['source'], 'artifact_sha256': sha(artifact), 'frames': frame_summaries,
            'rows': rows, 'new_code_executions': len(rows), 'original_reserve21_replays_match': True,
            'interpretation': {'fixed_recorded_states_not_alternative_worlds': True, 'native_transfer_commit_reexecuted': False,
                'loss_improvement_inferred_from_commands': False, 'new_model_calls': 0, 'new_native_worlds': 0,
                'optimizer_feedback_changed': False, 'new_parameter_domains_dispatched': False, 'publication_ready': False}})
        with (output / 'response.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
        render(rows, output)
        save(output / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': hashes,
            'files': {p.name: file_sha256(p) for p in output.iterdir() if p.name in ('report.json', 'response.csv', 'reserve-command-response.png', 'reserve-command-response.svg')}})
    except BaseException as error:
        save(output / 'ended.json', {'status': 'stopped', 'stage': stage, 'attempted_component_executions': attempts, 'completed_component_executions': len(rows),
            'error_type': type(error).__name__, 'error': str(error), 'ended_utc': utc(), 'automatic_retries': False}); raise
    save(output / 'ended.json', {'status': 'closed', 'attempted_component_executions': attempts, 'completed_component_executions': len(rows), 'ended_utc': utc(),
        'new_model_calls': 0, 'new_native_worlds': 0, 'optimizer_feedback_changed': False})
    print(json.dumps({'status': 'closed', 'component_executions': len(rows), 'new_native_worlds': 0, 'output': str(output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'scientific-source', 'audit-one', 'audit-two', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__': main()
