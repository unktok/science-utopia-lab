"""Literal choices, current/stale advice and all three audited control outcomes.

Read only. Message presence, chosen topic, annual state and loss are different
observations. This is not an optimizer, obedience gate or mediation estimate.
"""
import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_institution_effect_trace_v1 import checkpoint
from scripts.reports.native_instruction_timing_v1 import completed_pairs, direction_input, native_history
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.system.native_legacy_choice_controls import PRODUCER, PROTOCOL as ADVICE
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-legacy-choice-pilot-report.v1'
LABELS = ('core-assignment', 'native-choice', 'native-choice-advice')
HEADER = '\n## Information received from scientific institutions\n'


def advice_in_input(payload, year, selected_topic):
    """Decode the literal model-facing JSON, not a raw marker substring.

Opaque provenance aliases stay in the original input. Scientific payloads are
never scrubbed/repaired. Shared messages do not identify the request's actor.
"""
    messages, statuses = [], []
    for message in payload.get('messages', []):
        text = message.get('content')
        if not isinstance(text, str) or HEADER not in text:
            continue
        if text.count(HEADER) != 1:
            statuses.append('ambiguous-institutional-header'); continue
        body = text.split(HEADER, 1)[1].lstrip()
        try:
            value, _ = json.JSONDecoder().raw_decode(body)
        except ValueError:
            statuses.append('unparseable-institutional-json'); continue
        if (not isinstance(value, dict) or value.get('schema') != 'scienceutopia.model-provenance-view.v30'
                or not isinstance(value.get('messages'), list)
                or any(not isinstance(m, dict) for m in value['messages'])):
            statuses.append('unrecognized-institutional-view'); continue
        statuses.append('literal-institutional-view')
        messages.extend(m for m in value['messages'] if m.get('source') == PRODUCER
            and isinstance(m.get('payload'), dict) and m['payload'].get('schema') == ADVICE)
    current = [m for m in messages if m['payload'].get('effective_year') == year
               and type(m['payload'].get('effective_year')) is int]
    valid = [m for m in current if isinstance(m['payload'].get('recommended_topic'), str)
        and type(m['payload'].get('recommended_original_duration')) is int
        and m['payload']['recommended_original_duration'] > 0
        and isinstance(m['payload'].get('eligible_topics'), list)
        and all(isinstance(t, dict) and isinstance(t.get('topic'), str)
            and type(t.get('years')) is int and t['years'] > 0 for t in m['payload']['eligible_topics'])]
    scientific = {digest(m['payload']): m['payload'] for m in valid}
    one = next(iter(scientific.values())) if len(scientific) == 1 and len(valid) == len(current) else None
    # A malformed or conflicting view does not silently become an assessed
    # compliance sample. Retain every parsed message and ambiguity explicitly.
    parse_ok = bool(statuses) and all(s == 'literal-institutional-view' for s in statuses)
    if not parse_ok:
        one = None
    return {'institutional_frame_statuses': statuses, 'literal_advice_messages_in_input': clone(messages),
        'current_effective_year_advice_messages': len(current),
        'other_effective_year_advice_messages': len(messages) - len(current),
        'distinct_current_valid_advice_payloads': len(scientific),
        'assessable_current_advice': one is not None,
        'current_recommended_topic': None if one is None else one['recommended_topic'],
        'current_recommended_duration': None if one is None else one['recommended_original_duration'],
        'selected_matches_current_recommendation': None if one is None or selected_topic is None
            else selected_topic == one['recommended_topic'],
        'selected_in_current_advice_eligible_topics': None if one is None or selected_topic is None
            else selected_topic in {t['topic'] for t in one['eligible_topics']}}


def summarize_world(cell, world, catalog):
    states = [checkpoint(cell, item, world['system']) for item in world['physical_proof']['annual_checkpoints']]
    if world['status'] != 'complete' or [s['year'] for s in states] != [1, 2, 3, 4]:
        raise ValueError('complete original four-year control required')
    annual, memories, _ = native_history(states, ADVICE, catalog)
    stored = []
    for actor in states[-1]['ecosystem_data']['agents']:
        for message in actor.get('institutional_context', []):
            if message.get('source') == PRODUCER:
                stored.append({'actor_id': actor['id'], 'message': clone(message), 'message_sha256': digest(message)})
    wires, replies = completed_pairs(cell); directions = []
    for index, wire in enumerate(wires):
        row = direction_input(wire, replies.get(index), memories, ADVICE, catalog)
        if row is None:
            continue
        row['literal_known_advice_marker_present'] = row.pop('literal_instruction_present')
        row.update(advice_in_input(wire['payload'], wire['year'], row['selected_topic']))
        row['wire_index'] = index
        directions.append(row)
    current = [r for r in directions if r['assessable_current_advice'] and r['selected_topic'] is not None]
    return {k: clone(world[k]) for k in ('identity', 'condition', 'seed', 'status', 'scores')} | {
        'annual': annual, 'direction_memories': memories, 'stored_advice': stored,
        'direction_requests': directions,
        'catalog_project_effects': clone(world['physical_proof'].get('native_counts', {}).get('project_assignments_verified', [])),
        'physical_wire_requests': len(wires), 'committed_responses': len(replies),
        'wire_without_committed_reply': len(wires) - len(replies),
        'direction_request_attempts': len(directions), 'stored_advice_recipient_records': len(stored),
        'assessable_current_advice_completed_direction_attempts': len(current),
        'selected_current_recommendation_attempts': sum(r['selected_matches_current_recommendation'] for r in current),
        'attempts_are_independent_choices': False}


def export(args):
    root, frozen, out = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    source = pinned_revision(ROOT)
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen):
        raise ValueError('fresh export outside scientific raw/source required')
    paths = [root / 'plan.json', args.audit_one.resolve(), args.audit_two.resolve()]
    if paths[1] == paths[2] or paths[1].read_bytes() != paths[2].read_bytes():
        raise ValueError('two distinct matching original audits required')
    inputs = {str(p): file_sha256(p) for p in paths}; before = _inventory(root)
    plan, audit = [checked(json.loads(p.read_text())) for p in paths[:2]]
    if (plan['schema'] != 'scienceutopia.native-legacy-choice-pilot.v1.plan'
            or audit['schema'] != 'scienceutopia.native-legacy-choice-pilot-audit.v1'
            or plan['source_commit'] != audit['source_commit'] or pinned_revision(frozen) != plan['source_commit']
            or plan['content_sha256'] != audit['plan_sha256']
            or audit['closure']['terminal'] != checked(json.loads((root / 'terminal.json').read_text()))
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions']
            or audit['held_out_world_seeds'] or audit['automatic_invention'] or audit['policy_selection']
            or digest(before) != audit['raw_inventory_sha256'] or len(audit['worlds']) != 3
            or tuple(j['condition'] for j in plan['jobs']) != LABELS
            or plan['objectives'] != ['throughput', 'content-utility']):
        raise ValueError('normally closed exact three-control original source/audit/raw required')
    catalog = plan['catalog']['directions']
    if digest(catalog) != plan['catalog']['directions_sha256'] or len({r['topic'] for r in catalog}) != len(catalog):
        raise ValueError('literal original catalog required')
    catalog = {r['topic']: r['years'] for r in catalog}; worlds = []
    for job, world in zip(plan['jobs'], audit['worlds']):
        if any(world[k] != v for k, v in job.items()):
            raise ValueError('literal ordered control identity/system/seed differs')
        cell = Path(world['loaded']['context']).resolve().parent
        if not cell.is_relative_to(root):
            raise ValueError('audited world outside original raw')
        worlds.append(summarize_world(cell, world, catalog))
    reference = worlds[0]['scores']
    for w in worlds:
        w['loss_difference_from_core_assignment'] = {k: w['scores'][k] - reference[k] for k in plan['objectives']}
    result = {'schema': SCHEMA, 'analysis_source_commit': source, 'scientific_source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'audit_content_sha256': audit['content_sha256'],
        'raw_inventory_sha256': digest(before), 'worlds': worlds, 'catalog': plan['catalog'],
        'scope': 'All three fixed developer controls on one reused condition. Every direction request '
            'attempt remains, with literal frames/replies, current versus other effective-year advice, '
            'ambiguous actor-memory matches, native annual project states and actual catalog applications. '
            'Advice topic matches are descriptive, not obedience, unique actor attribution, independent '
            'samples, feasibility beyond the observed worlds, mediation, optimization or scientific truth.',
        'new_model_calls': 0, 'new_code_executions': 0, 'loss_or_selection_changed': False,
        'held_out_evaluation': False, 'policy_selection': False, 'automatic_invention': False, 'publication_ready': False}
    if (before != _inventory(root) or inputs != {str(p): file_sha256(p) for p in paths}
            or pinned_revision(ROOT) != source or pinned_revision(frozen) != plan['source_commit']):
        raise ValueError('original raw or bound source changed during export')
    out.mkdir(parents=True); save(out / 'report.json', result)
    columns = ['condition', 'seed', 'throughput', 'content-utility', 'direction_request_attempts',
        'stored_advice_recipient_records', 'assessable_current_advice_completed_direction_attempts',
        'selected_current_recommendation_attempts', 'physical_wire_requests', 'committed_responses',
        'wire_without_committed_reply']
    with (out / 'controls.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        writer.writerows({k: w['scores'][k] if k in plan['objectives'] else w[k] for k in columns} for w in worlds)
    columns = ['condition', 'wire_index', 'year', 'payload_sha256', 'reply_status', 'selected_topic',
        'selected_catalog_duration_years', 'unique_actor_attribution', 'literal_known_advice_marker_present',
        'current_effective_year_advice_messages', 'other_effective_year_advice_messages',
        'assessable_current_advice', 'current_recommended_topic', 'current_recommended_duration',
        'selected_matches_current_recommendation', 'selected_in_current_advice_eligible_topics']
    with (out / 'direction-attempts.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        writer.writerows({k: w['condition'] if k == 'condition' else r[k] for k in columns}
                         for w in worlds for r in w['direction_requests'])
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': inputs,
        'analysis_source_commit': source, 'adapter_file_sha256': file_sha256(Path(__file__)),
        'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())}, 'new_model_calls': 0, 'new_code_executions': 0})
    print(json.dumps({'worlds': len(worlds), 'direction_requests': sum(w['direction_request_attempts'] for w in worlds)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    keys = ('run', 'frozen-source', 'audit-one', 'audit-two', 'output')
    for key in keys:
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    for key in keys:
        name = key.replace('-', '_'); setattr(args, name, getattr(args, name).resolve())
    import os, subprocess, sys
    if os.environ.get('SCIENCE_UTOPIA_COLD_LEGACY_CHOICES_WORKER') == '1':
        export(args); return
    result = subprocess.run([sys.executable, '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source), str(Path(__file__).resolve()),
        *[v for k in keys for v in ('--' + k, str(getattr(args, k.replace('-', '_'))))]],
        cwd=args.frozen_source, env={**os.environ, 'PYTHONHASHSEED': '42',
            'SCIENCE_UTOPIA_COLD_LEGACY_CHOICES_WORKER': '1'}, timeout=1800, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
