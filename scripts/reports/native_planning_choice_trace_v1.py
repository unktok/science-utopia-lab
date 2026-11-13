"""Literal planning choices and projects from every audited planning world.

The cold CLI uses the original scientific decoder/parser. Generated institutions
need not preserve the developer agenda, obey it or select a shortest project.
"""
import argparse
import csv
import json
from pathlib import Path
import sqlite3

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_institution_effect_trace_v1 import checkpoint
from scripts.reports.native_instruction_timing_v1 import completed_pairs, direction_input, native_history
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-planning-choice-trace.v1'
MARKER = 'native-developer-catalog-agenda-v1'


def original_pairs(cell):
    if (cell / 'wire-requests.jsonl').is_file(): return completed_pairs(cell)
    cache = cell / 'replies/responses.sqlite'
    if cache.is_file():
        with sqlite3.connect(cache.resolve().as_uri() + '?mode=ro', uri=True) as db:
            if db.execute('SELECT count(*) FROM replies').fetchone()[0]:
                raise ValueError('committed replies without an original wire journal')
    return [], {}


def summarize_world(cell, world, catalog):
    states = [checkpoint(cell, item, world['system']) for item in world['physical_proof'].get('annual_checkpoints', [])]
    years = [s['year'] for s in states]
    if years != list(range(1, len(years) + 1)) or (world['status'] == 'complete' and years != [1, 2, 3, 4]):
        raise ValueError('exact original complete or partial annual prefix required')
    annual, memories = [], []
    if states: annual, memories, _ = native_history(states, MARKER, catalog)
    wires, replies = original_pairs(cell); directions = []
    for i, wire in enumerate(wires):
        row = direction_input(wire, replies.get(i), memories, MARKER, catalog)
        if row is not None:
            # This is only literal presence of the original developer marker.
            # A new authored message can omit it and still affect researchers.
            row['literal_known_developer_agenda_marker_present'] = row.pop('literal_instruction_present')
            directions.append({'wire_index': i, **row})
    return {k: world[k] for k in ('identity', 'role', 'seed', 'status', 'scores')} | {
        'annual': annual, 'direction_memories': memories, 'direction_requests': directions,
        'catalog_project_effects': world['physical_proof'].get('native_counts', {}).get('project_assignments_verified', []),
        'physical_wire_requests': len(wires), 'committed_responses': len(replies),
        'wire_without_committed_reply': len(wires) - len(replies),
        'partial_boundaries_are_not_completed_outcomes': world['status'] != 'complete'}


def export(args):
    root, frozen, out = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    reader_source = pinned_revision(ROOT)
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen):
        raise ValueError('fresh planning trace outside scientific raw/source required')
    paths = [root / 'plan.json', args.audit_one, args.audit_two]
    if paths[1].read_bytes() != paths[2].read_bytes(): raise ValueError('matching original double audits required')
    hashes = {str(p): file_sha256(p) for p in paths}; before = _inventory(root)
    plan, audit = [checked(json.loads(p.read_text())) for p in paths[:2]]
    if (plan['schema'] != 'scienceutopia.native-planning-objective-loop.v1.plan'
            or audit['schema'] != 'scienceutopia.native-planning-objective-loop-audit.v1'
            or audit['source_commit'] != plan['source_commit'] or pinned_revision(frozen) != plan['source_commit']
            or audit['plan_sha256'] != plan['content_sha256'] or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or digest(before) != audit['raw_inventory_sha256'] or audit['new_model_calls'] or audit['new_code_executions']
            or plan['objectives'] != ['throughput', 'content-utility'] or plan['generations'] != 3
            or len(plan['reference_order']) != 8 or len(audit['authoring']) != 6
            or len({w['identity'] for w in audit['worlds']}) != len(audit['worlds'])
            or not {'reference-' + n for n in plan['reference_order']} <= {w['identity'] for w in audit['worlds']}):
        raise ValueError('complete original planning source/audit/raw and all declared references/slots required')
    rows = plan['catalog']['directions']
    if (len({r['topic'] for r in rows}) != len(rows) or digest(rows) != plan['catalog']['directions_sha256']):
        raise ValueError('literal original native catalog required')
    catalog = {r['topic']: r['years'] for r in rows}; worlds = []
    for world in audit['worlds']:
        cells = [p for p in root.glob('**/worlds/' + world['identity'] + '-s' + str(world['seed'])) if p.is_dir()]
        if len(cells) != 1: raise ValueError('unique original audited world directory required')
        worlds.append(summarize_world(cells[0], world, catalog))
    result = {'schema': SCHEMA, 'analysis_source_commit': reader_source,
        'scientific_source_commit': plan['source_commit'], 'plan_sha256': plan['content_sha256'],
        'audit_content_sha256': audit['content_sha256'], 'raw_inventory_sha256': digest(before),
        'catalog': plan['catalog'], 'worlds': worlds,
        'scope': 'Literal original direction frames, committed replies, saved memories/project dates and validated catalog assignments. '
            'All audited worlds, including failed prefixes, remain present. Marker presence only checks the known developer agenda, '
            'not every possible authored message. No author is guessed from shared content; malformed frames, unparseable replies '
            'and ambiguous memory matches remain explicit. Assignment replaces a choice, not proof of obedience or completed work. '
            'Observed input, selected topic, native state, outcome and causal mediation are distinct quantities.',
        'known_marker_is_not_all_information': True, 'new_model_calls': 0, 'new_code_executions': 0,
        'loss_or_selection_changed': False, 'publication_ready': False}
    if (before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in paths}
            or pinned_revision(ROOT) != reader_source or pinned_revision(frozen) != plan['source_commit']):
        raise ValueError('planning trace inputs or bound source changed')
    out.mkdir(parents=True); save(out / 'report.json', result)
    fields = ['world', 'role', 'status', 'seed', 'year', 'actor_id', 'is_active', 'resources',
              'project_start_year', 'project_end_year', 'newest_direction_json']
    with (out / 'annual-project-states.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for w in worlds:
            for year in w['annual']:
                for actor in year['authors']:
                    writer.writerow({'world': w['identity'], **{k: w[k] for k in ('role', 'status', 'seed')},
                        'year': year['year'], 'actor_id': actor['id'],
                        **{k: actor[k] for k in ('is_active', 'resources', 'project_start_year', 'project_end_year')},
                        'newest_direction_json': json.dumps(actor['newest_direction'], sort_keys=True, ensure_ascii=False)})
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': hashes,
        'analysis_source_commit': reader_source, 'adapter_file_sha256': file_sha256(Path(__file__)),
        'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())}, 'new_model_calls': 0, 'new_code_executions': 0})
    print(json.dumps({'worlds': len(worlds), 'direction_requests': sum(len(w['direction_requests']) for w in worlds)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'audit-one', 'audit-two', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    import os, subprocess, sys
    if os.environ.get('SCIENCE_UTOPIA_COLD_PLANNING_CHOICES_WORKER') == '1': export(args); return
    result = subprocess.run([sys.executable, '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=args.frozen_source,
        env={**os.environ, 'PYTHONHASHSEED': '42', 'SCIENCE_UTOPIA_COLD_PLANNING_CHOICES_WORKER': '1'}, timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
