"""Literal institutional changes in a retained CLOSED pre-scale report.

No source is evaluated or imported. Differences describe submitted JSON, not
semantic novelty, exercised effects, successful invention or a new selection.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from scripts.reports.pre_scale_search_v1 import METHODS, OBJECTIVES
from utopia.optimization.native_numeric_designer import checked
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


def literal_changes(before, after, path=()):
    """Deterministic JSON changes, retaining absent versus null and empty values."""
    if digest(before) == digest(after):
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        rows = []
        for key in sorted(before.keys() | after.keys()):
            if key in before and key in after:
                rows.extend(literal_changes(before[key], after[key], path+(key,)))
            else:
                rows.append(change(path+(key,), key in before, before.get(key),
                    key in after, after.get(key)))
        return rows
    if isinstance(before, list) and isinstance(after, list):
        rows = []
        for i in range(max(len(before), len(after))):
            if i < min(len(before), len(after)):
                rows.extend(literal_changes(before[i], after[i], path+(i,)))
            else:
                rows.append(change(path+(i,), i < len(before), before[i] if i < len(before) else None,
                    i < len(after), after[i] if i < len(after) else None))
        return rows
    return [change(path, True, before, True, after)]


def change(path, before_present, before, after_present, after):
    # Full values remain in the hash-bound input. Long authored source is not
    # duplicated, and a digest is never described as a semantic interpretation.
    def value(present, item):
        return {'present': present, 'sha256': digest(item) if present else None,
            'value': deepcopy(item) if present and len(json.dumps(item, ensure_ascii=False)) <= 160 else None,
            'value_omitted': present and len(json.dumps(item, ensure_ascii=False)) > 160}
    return {'path': list(path), 'before': value(before_present, before),
        'after': value(after_present, after)}


def parameter_category(path):
    if 'code_artifact' in path:
        return 'literal-source' if path[-1] == 'source' else 'code-descriptor'
    if 'delegate' in path:
        return 'process-delegate'
    return 'parameter-or-program'


def describe(before, after):
    # Typed parsing and exact round-trip only, not a new graph/execution audit.
    for system in (before, after):
        if digest(SystemSpec.from_dict(system).to_dict()) != digest(system):
            raise ValueError('canonical submitted SystemSpec required; no silent normalization')
    old = {m['mechanism_id']: m for m in before['mechanisms']}
    new = {m['mechanism_id']: m for m in after['mechanisms']}
    if len(old) != len(before['mechanisms']) or len(new) != len(after['mechanisms']):
        raise ValueError('unique mechanism identities required; no silent collapse')
    mechanisms = []
    for identity in sorted(old.keys() & new.keys()):
        a, b = old[identity], new[identity]
        changes = literal_changes(a, b)
        if changes:
            for row in changes:
                row['category'] = parameter_category(row['path']) if row['path'][0] == 'parameters' else 'mechanism-interface'
            mechanisms.append({'mechanism_id': identity, 'changes': changes})
    sections = {key: literal_changes(before[key], after[key]) for key in sorted(before)
        if key != 'mechanisms'}
    return {'baseline_sha256': digest(before), 'candidate_sha256': digest(after),
        'nodes_added': sorted(new.keys()-old.keys()), 'nodes_removed': sorted(old.keys()-new.keys()),
        'node_order_changed': list(old) != list(new), 'mechanism_changes': mechanisms,
        'changed_mechanism_categories': dict(Counter(row['category'] for m in mechanisms for row in m['changes'])),
        'connections_literal_changed': bool(sections['connections']),
        'schedules_literal_changed': bool(sections['schedules']),
        'nonmechanism_section_changes': {key: value for key, value in sections.items() if value}}


def project(report):
    checked(report)
    native=report.get('schema')=='scienceutopia.native-institution-loop-report.v1'
    methods=tuple(report.get('methods',())) if native else METHODS
    if native and methods!=('parameters','code-fixed-graph','code-and-graph'):
        raise ValueError('native loop methods differ')
    if not native and report.get('schema') != 'scienceutopia.pre-scale-search-report.v1':
        raise ValueError('closed pre-scale report required')
    initial, = [r for r in report['references'] if r['row_id'] == 'reference:open-seed']
    baseline = initial['system']; systems = report['systems_by_sha256']
    if any(digest(system) != key for key, system in systems.items()) or systems.get(digest(baseline)) != baseline:
        raise ValueError('exact retained policy identities required')
    expected = {f'run-00:{o}:{m}:g{g}' for o in OBJECTIVES for m in methods for g in (0, 1)}
    slots = report['search_slots']
    if len(slots) != 4*len(methods) or {r['row_id'] for r in slots} != expected:
        raise ValueError('all distinct declared slots required')
    rows = []
    for slot in slots:
        if slot['row_id'] != f"run-00:{slot['arm']}:g{slot['generation']}":
            raise ValueError('slot arm/generation differs from retained row identity')
        fingerprint = slot['system_sha256']
        if slot['status'] == 'generation-failure':
            if fingerprint is not None or slot['own_loss'] is not None:
                raise ValueError('unsubmitted slot cannot have a policy or loss')
            difference = None
        else:
            if fingerprint not in systems:
                raise ValueError('submitted slot lacks its literal policy')
            difference = describe(baseline, systems[fingerprint])
        rows.append({'row_id': slot['row_id'], 'arm': slot['arm'], 'status': slot['status'],
            'own_loss': slot['own_loss'], 'difference_from_common_initial': difference})
    result = {'schema': 'scienceutopia.native-institution-loop-mechanism-changes.v1' if native else 'scienceutopia.pre-scale-mechanism-changes.v1',
        'input_report_content_sha256': report['content_sha256'], 'source_commit': report['source_commit'],
        'plan_sha256': report['plan_sha256'], 'baseline_row_id': initial['row_id'], 'rows': rows,
        'comparison_basis': 'Literal common initial, NOT inferred request parent or semantic graph equivalence.',
        'source_text_retained_in_input_report': True, 'semantic_novelty_or_effect_inferred': False,
        'independent_original_source_audit': False, 'new_model_calls': 0, 'new_authored_code_executions': 0}
    result['content_sha256'] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.report.resolve():
        raise ValueError('fresh independent output required')
    before = file_sha256(args.report)
    result = project(json.loads(args.report.read_text()))
    if file_sha256(args.report) != before:
        raise ValueError('retained report changed during projection')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({'output': str(args.output), 'content_sha256': result['content_sha256'], 'new_model_calls': 0}))


if __name__ == '__main__':
    main()
