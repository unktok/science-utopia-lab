"""Join recorded staged construction paths to audited native outcomes.

Read-only post-closure analysis, not another audit, inference, probe, repair,
selection or matched causal comparison of the staged and one-shot designers.
"""
import argparse
import csv
import inspect
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_code_tested_loop_v1 import component_trace
from scripts.reports.native_workflow_objective_loop_v1 import summarize as native_summary
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

MODE = 'open-institutions-staged-tests-v1'
SCHEMA = 'scienceutopia.native-workflow-construction-trace.v1'


def summarize(plan, audit, records, sessions):
    checked(plan); checked(audit)
    if plan.get('designer_mode') != MODE:
        raise ValueError('explicit staged workflow required; do not relabel earlier one-shot studies')
    result = native_summary(plan, audit, records)
    matched = plan['schema'] == 'scienceutopia.native-longitudinal-comparison.v1.plan'
    def slot_key(row):
        history = (row['arm'], row['objective']) if matched else row['objective']
        return history, row['generation']
    keys = {slot_key(s) for s in result['slots']}
    if set(sessions) != keys:
        raise ValueError('every consumed slot requires its original staged session, including nulls')
    counts = {'known_probe_attempts': 0, 'returned': 0, 'raised': 0,
        'sessions_missing_component_summary': 0, 'recorded_model_steps': 0}
    for row in result['slots']:
        key = slot_key(row); record = records[key]; session = sessions[key]
        if session['request_sha256'] != record['request_sha256'] or session['definition'] != record['definition']:
            raise ValueError('literal staged wrapper request/definition differs from audited slot')
        response, steps = session['response'], session['steps']
        if response is None:
            if steps or record['generation_error'] is None:
                raise ValueError('absent staged terminal requires retained technical null; never fabricate one')
            trace = {'component_testing': None, 'terminal_response_missing': True,
                'completed_steps': None, 'events': [], 'same_fixture_later_code_comparisons': [],
                'drawn_candidate_artifact_observations': None, 'automatic_repair_claimed': False}
            counts['sessions_missing_component_summary'] += 1
        else:
            checked(response)
            if (response['request_sha256'] != record['request_sha256']
                    or response['status'] not in ('generated', 'generation-failed')
                    or (response['status'] == 'generated' and response['definition'] != record['definition'])
                    or (response['status'] == 'generation-failed' and record['generation_error'] is None)):
                raise ValueError('recorded staged terminal differs from literal audited proposal')
            for step in steps: checked(step)
            candidate = (record['draws'][0]['suggestion']['candidate']
                if record['draws'] and record['draws'][0]['suggestion'] is not None else None)
            trace = component_trace(steps, response, candidate)
            trace['terminal_response_missing'] = False
            trace['author_steps'] = [{'step': s['step'], 'status': s['status'],
                'tool': (s.get('transition') or {}).get('tool'),
                'step_content_sha256': s['content_sha256']} for s in steps]
            summary = trace['component_testing']
            for target, source in (('known_probe_attempts', 'probe_attempts'), ('returned', 'returned'), ('raised', 'raised')):
                counts[target] += summary[source]
            counts['recorded_model_steps'] += len(steps)
        row['construction_trace'] = trace
    result.update(schema='scienceutopia.native-longitudinal-construction-trace.v1' if matched else SCHEMA,
        construction_counts=counts)
    result['interpretation'].update(
        component_return_is_native_success=False, observed_revision_is_causal_repair=False,
        staged_method_superiority_claimed=False, new_native_worlds=0,
        independent_optimizer_units_are_not_steps_or_probes=True)
    count = 'twelve' if matched else 'six'
    result['scope'] = (f'Original directed calibration is separate from these {count} proposal paths. '
        'Same-fixture later-code transitions describe observations, not caused repair or scientific gains. '
        'Untested/new interfaces and technical nulls remain visible. Old suites apply only to their '
        'literal artifact version. Native outcomes, both losses and frozen selections are unchanged.')
    return result


def export(args):
    root, out = args.run.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(root):
        raise ValueError('fresh construction export outside original scientific raw required')
    if args.audit_one.read_bytes() != args.audit_two.read_bytes():
        raise ValueError('two matching original-source cold audits required')
    before = _inventory(root)
    plan = checked(json.loads((root/'plan.json').read_text()))
    audit = checked(json.loads(args.audit_one.read_text()))
    if (digest(before) != audit['raw_inventory_sha256'] or len(before) != audit['raw_files']
            or audit['closure']['terminal'] != checked(json.loads((root/'terminal.json').read_text()))):
        raise ValueError('unchanged normally closed original raw required')
    paths = [root/'plan.json', args.audit_one, args.audit_two, Path(__file__),
        Path(inspect.getfile(component_trace)), Path(inspect.getfile(native_summary))]
    from utopia.optimization.native_post_edit_feedback_v1 import persistent_diagnostics
    paths.append(Path(inspect.getfile(persistent_diagnostics)))
    inputs = {str(p.resolve()): file_sha256(p) for p in paths}
    records, sessions = {}, {}
    matched = plan['schema'] == 'scienceutopia.native-longitudinal-comparison.v1.plan'
    if matched:
        from scripts import run_native_longitudinal_comparison_v1 as driver
    else:
        from scripts import run_native_workflow_objective_loop_v1 as driver
    for history in driver.history_keys(plan):
        history_root = driver.history_directory(root, history)
        state = json.loads((history_root/'campaign/native-adaptive-state.json').read_text())
        if state['pending'] is not None:
            raise ValueError('pending workflow is not a closed construction trajectory')
        for g, record in enumerate(state['records']):
            key = history, g; records[key] = record
            directory = history_root/'authoring'/('proposal-'+record['request_sha256'])
            wrapper = checked(json.loads((directory/'result.json').read_text()))
            binding = checked(json.loads((directory/'binding.json').read_text()))
            if binding['request'] != record['request'] or wrapper['binding_sha256'] != binding['content_sha256']:
                raise ValueError('exact original proposal wrapper binding required')
            inner = directory/'editor-session/authoring'/('generation-'+record['request_sha256'])
            terminal = inner/'response.json'
            sessions[key] = {'request_sha256': digest(binding['request']), 'definition': wrapper['definition'],
                'response': checked(json.loads(terminal.read_text())) if terminal.is_file() else None,
                'steps': [checked(json.loads(f.read_text())) for f in sorted(inner.glob('step-*.completed.json'))]}
    report = summarize(plan, audit, records, sessions)
    if before != _inventory(root) or inputs != {p: file_sha256(Path(p)) for p in inputs}:
        raise ValueError('original construction/report inputs changed while reading')
    out.mkdir(parents=True)
    saved = save(out/'report.json', report)
    fields = ['slot_index', 'objective', 'generation', 'status', 'physical_job', 'loss',
        'completed_steps', 'probe_attempts', 'returned', 'raised', 'terminal_response_missing']
    if matched: fields.insert(1, 'arm')
    with (out/'slots.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n'); writer.writeheader()
        for row in saved['slots']:
            trace = row['construction_trace']; summary = trace['component_testing']
            writer.writerow({**{k: row[k] for k in fields if k in row},
                **{k: trace[k] for k in ('completed_steps', 'terminal_response_missing')},
                **{k: None if summary is None else summary[k] for k in ('probe_attempts', 'returned', 'raised')}})
    save(out/'manifest.json', {'schema': SCHEMA+'.export', 'inputs': inputs,
        'raw_inventory_sha256': digest(before), 'raw_files': len(before),
        'report_content_sha256': saved['content_sha256'], 'original_bytes_unchanged': True,
        'files': {f.name: file_sha256(f) for f in sorted(out.iterdir()) if f.is_file()},
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0})
    if before != _inventory(root):
        raise ValueError('original raw changed during construction export')
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'audit-one', 'audit-two', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    r = export(parser.parse_args())
    print(json.dumps({'slots': len(r['slots']), 'construction_counts': r['construction_counts'], 'new_model_calls': 0}))


if __name__ == '__main__': main()
