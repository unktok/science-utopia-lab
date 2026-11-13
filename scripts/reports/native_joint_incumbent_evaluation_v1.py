"""Freeze development-only K/O aliases, then copy their unused-world outcomes.

No policy, evaluation job, selection file, raw audit or loss is changed. An
incumbent can lose on unused worlds; no outcome permits switching its alias.
"""
import argparse
import csv
import json
from pathlib import Path

from scripts.reports.native_optimization_incumbents_v1 import OBJECTIVES, finite, summarize as development_view
from scripts.run_native_joint_fixed_evaluation_v1 import contrasts_for
from scripts.run_native_parent_presentation_loop_v1 import ARM_ORDER
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.system.native_planning_controls import ORDER
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-joint-incumbent-evaluation.v1'
KINDS = ('planning', 'presentation', 'numeric')
HISTORIES = ['planning:' + k for k in OBJECTIVES] + ['presentation:' + k for k in ARM_ORDER] + ['numeric:' + k for k in OBJECTIVES]


def freeze_aliases(binding, developments):
    """Only pre-evaluation selection metadata and development losses are read."""
    checked(binding)
    if binding['schema'] not in ('scienceutopia.native-joint-fixed-evaluation.v1.plan', 'scienceutopia.native-joint-fixed-report.v1'):
        raise ValueError('explicit joint plan or closed joint report required')
    if (set(developments) != set(KINDS) or binding['selection_order'] != HISTORIES
            or set(binding['selection_definitions']) != set(HISTORIES)):
        raise ValueError('all three development origins and eight literal histories required')
    frozen = checked(binding['fixed_selection'])
    if (frozen['baseline_fallback'] or frozen['candidate_reselection'] or frozen['held_out_evaluation']
            or set(frozen['selected']) != set(HISTORIES) or set(frozen['original_selections']) != set(KINDS)):
        raise ValueError('unchanged original own-only selection bank required')
    views = {kind: development_view(developments[kind]) for kind in KINDS}
    if any(views[k]['scope'] != k for k in KINDS):
        raise ValueError('development report belongs to a different origin')
    for kind, dev in developments.items():
        audit_key = 'numeric_audit_sha256' if kind == 'numeric' else 'audit_sha256'
        original = checked(frozen['original_selections'][kind])
        if (dev[audit_key] != binding['origin_audit_content_sha256'][kind]
                or dev['plan_sha256'] != original['plan_sha256']):
            raise ValueError('development audit/plan differs from joint frozen origin')
    if (developments['numeric']['original_audit_sha256'] != binding['origin_audit_content_sha256']['planning']
            or views['numeric']['references'] != views['planning']['references']):
        raise ValueError('numeric reused reference bank is not the same planning bank')
    aliases = []
    for label in HISTORIES:
        kind, key = label.split(':', 1)
        history = next(h for h in views[kind]['histories'] if h['history'] == key)
        definition = binding['selection_definitions'][label]
        original = frozen['original_selections'][kind]
        own = frozen['selected'][label]
        if (definition != {'origin_study': kind, 'origin_key': key, 'objective': history['objective'],
                'origin_selection_sha256': original['content_sha256']}
                or own != original['selected'][key]
                or any(own[k] != v for k, v in history['original_own_selection'].items())
                or (own['system'] is None) != (own['selected_id'] is None)):
            raise ValueError('literal original selection, objective or tie identities differ')
        for readout, field in [('known-incumbent', 'best_known'), ('own-submission', 'best_own')]:
            value = history['final'][field]
            if value['origin'] == 'reference':
                reference = value['identity'].removeprefix('reference-')
                if reference not in ORDER:
                    raise ValueError('unknown development reference alias')
                target = 'reference:' + reference
            elif value['origin'] == 'own':
                if value['identity'] != own['selected_id']:
                    raise ValueError('only the original earliest-tied own policy is covered')
                target = 'selected:' + label
            elif value['origin'] is None and readout == 'own-submission' and own['system'] is None:
                target = 'selected:' + label
            else:
                raise ValueError('incumbent identity is not an already covered fixed policy')
            aliases.append({'history': label, 'objective': history['objective'], 'readout': readout,
                'development_identity': value['identity'], 'development_origin': value['origin'],
                'development_loss': value['loss'], 'all_development_tied_ids': clone(value['all_tied_ids']),
                'evaluation_label': target, 'all_tied_programs_claimed_evaluated': False})
    result = {'schema': SCHEMA + '.aliases', 'joint_plan_sha256': binding['content_sha256'] if binding['schema'].endswith('.plan') else binding['plan_sha256'],
        'joint_source_commit': binding['source_commit'], 'history_order': HISTORIES,
        'origin_audit_content_sha256': clone(binding['origin_audit_content_sha256']),
        'development_report_content_sha256': {k: d['content_sha256'] for k, d in developments.items()},
        'aliases': aliases, 'selection_uses_evaluation_outcomes': False, 'new_physical_jobs': 0,
        'original_own_selection_changed': False, 'reference_first_then_own_chronology': True}
    result['content_sha256'] = digest(result)
    return result


def summarize(joint, developments, frozen_aliases):
    checked(joint); checked(frozen_aliases)
    if joint['schema'] != 'scienceutopia.native-joint-fixed-report.v1' or freeze_aliases(joint, developments) != frozen_aliases:
        raise ValueError('pre-frozen development aliases do not match this exact joint evaluation')
    seeds = joint['seeds']; labels = ['reference:' + r for r in ORDER] + ['selected:' + h for h in HISTORIES]
    if (not 1 <= len(seeds) <= 3 or any(type(s) is not int or not 0 <= s < 2**31 or s == 61001 for s in seeds)
            or len(set(seeds)) != len(seeds) or joint['score_order'] != OBJECTIVES or joint['labels'] != labels
            or joint['contrast_definitions'] != contrasts_for()):
        raise ValueError('literal unused seeds, all policy labels and original contrasts required')
    physical = {p['identity']: p for p in joint['physical_worlds']}
    by = {(r['label'], r['seed']): r for r in joint['logical_rows']}
    if (len(physical) != len(joint['physical_worlds']) or len(by) != len(joint['logical_rows'])
            or set(by) != {(label, seed) for label in labels for seed in seeds}):
        raise ValueError('complete unique physical/logical evaluation coverage required')
    for row in by.values():
        scores = row['scores']
        if (set(scores) != set(OBJECTIVES) or any(v is not None and not finite(v) for v in scores.values())
                or ((row['status'] == 'complete') != all(finite(v) for v in scores.values()))
                or row['status'] != 'complete' and any(v is not None for v in scores.values())):
            raise ValueError('literal finite completed losses or unavailable losses required')
        job = physical.get(row['physical_job'])
        if row['physical_job'] is None:
            key = row['label'].removeprefix('selected:')
            if (key not in joint['fixed_selection']['selected'] or joint['fixed_selection']['selected'][key]['system'] is not None
                    or row['status'] != 'no-completed-submission' or any(v is not None for v in scores.values())):
                raise ValueError('missing own pool cannot be substituted or numerically imputed')
        elif (job is None or row['label'] not in job['labels']
                or any(job[k] != row[k] for k in ('seed', 'scores', 'status'))):
            raise ValueError('logical outcome differs from its original physical job')
    for job in physical.values():
        if set(job['labels']) != {label for (label, seed), row in by.items() if seed == job['seed'] and row['physical_job'] == job['identity']}:
            raise ValueError('physical sharing coverage differs')
    rows = [{**clone(alias), 'seed': seed, **{k: clone(by[alias['evaluation_label'], seed][k])
        for k in ('physical_job', 'status', 'scores')}} for alias in frozen_aliases['aliases'] for seed in seeds]
    selected = {(r['history'], r['readout'], r['seed']): r for r in rows}
    def difference(a, b):
        return {'left_physical_job': a['physical_job'], 'right_physical_job': b['physical_job'],
            'same_physical_job': a['physical_job'] is not None and a['physical_job'] == b['physical_job'],
            'differences': {o: None if a['scores'][o] is None or b['scores'][o] is None else a['scores'][o] - b['scores'][o] for o in OBJECTIVES}}
    contrasts = [{**clone(d), 'readout': readout, 'seed': seed, **difference(selected[d['left'], readout, seed], selected[d['right'], readout, seed])}
        for readout in ('known-incumbent', 'own-submission') for d in joint['contrast_definitions'] for seed in seeds]
    own_vs_known = [{'history': h, 'seed': s, **difference(selected[h, 'own-submission', s], selected[h, 'known-incumbent', s])} for h in HISTORIES for s in seeds]
    return {'schema': SCHEMA + '.report', 'joint_report_content_sha256': joint['content_sha256'],
        'joint_plan_sha256': joint['plan_sha256'], 'joint_audit_sha256': joint['audit_sha256'],
        'frozen_aliases': clone(frozen_aliases), 'score_order': OBJECTIVES, 'seeds': clone(seeds),
        'logical_rows': rows, 'fixed_policy_contrasts': contrasts, 'own_minus_incumbent': own_vs_known,
        'original_physical_worlds': len(physical), 'data_identity': clone(joint['data_identity']),
        'interpretation': {'selection_uses_evaluation_outcomes': False, 'original_own_selection_changed': False,
            'missing_losses_imputed': False, 'all_tied_programs_claimed_evaluated': False,
            'shared_aliases_are_independent_replications': False, 'new_model_calls': 0, 'new_native_worlds': 0,
            'raw_audit_reexecuted': False, 'scientific_gain_demonstrated': False, 'publication_ready': False}}


def export(args):
    output = Path(args.output).resolve()
    paths = {}
    def one(path):
        path = Path(path).resolve(); paths[str(path)] = file_sha256(path)
        return checked(json.loads(path.read_text()))
    def pair(values):
        a, b = map(lambda p: Path(p).resolve(), values)
        if a == b or a.read_bytes() != b.read_bytes():
            raise ValueError('two distinct matching complete report files required')
        result = one(a); one(b); return result
    if output.exists(): raise ValueError('fresh independent output required')
    source = pinned_revision(ROOT)
    developments = {k: pair(getattr(args, k + '_reports')) for k in KINDS}
    if args.stage == 'freeze':
        joint = one(args.joint_plan); report = None; aliases = freeze_aliases(joint, developments)
    else:
        joint = pair(args.joint_reports); aliases = one(args.frozen_aliases)
        report = summarize(joint, developments, aliases)
    if any(output.is_relative_to(Path(p).parent) for p in paths):
        raise ValueError('projection cannot be placed inside original input directories')
    before = clone(paths); output.mkdir(parents=True)
    save(output / 'aliases.json', {k: v for k, v in aliases.items() if k != 'content_sha256'})
    if report is not None:
        report.update(analysis_source_commit=source, analysis_adapter_sha256=file_sha256(Path(__file__)))
        save(output / 'report.json', report)
        for name, rows, fields, nested in (
                ('fixed-scores', report['logical_rows'], ['history', 'readout', 'evaluation_label', 'seed', 'physical_job', 'status'], 'scores'),
                ('fixed-contrasts', report['fixed_policy_contrasts'], ['id', 'readout', 'left', 'right', 'seed', 'left_physical_job', 'right_physical_job', 'same_physical_job'], 'differences'),
                ('own-minus-incumbent', report['own_minus_incumbent'], ['history', 'seed', 'left_physical_job', 'right_physical_job', 'same_physical_job'], 'differences')):
            with (output / (name + '.csv')).open('x', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields + OBJECTIVES); writer.writeheader()
                for row in rows: writer.writerow({**{k: row[k] for k in fields}, **row[nested]})
    if (before != {p: file_sha256(Path(p)) for p in paths} or pinned_revision(ROOT) != source):
        raise ValueError('original inputs or read-only analysis source changed')
    save(output / 'manifest.json', {'schema': SCHEMA + '.export', 'stage': args.stage, 'inputs': paths,
        'analysis_source_commit': source, 'analysis_adapter_sha256': file_sha256(Path(__file__)),
        'aliases_content_sha256': aliases['content_sha256'], 'new_model_calls': 0, 'new_native_worlds': 0,
        'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())}})
    print(json.dumps({'stage': args.stage, 'aliases': len(aliases['aliases']), 'new_model_calls': 0,
        'original_selection_changed': False, 'output': str(output)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('freeze', 'report'))
    parser.add_argument('--output', type=Path, required=True)
    for kind in KINDS: parser.add_argument('--' + kind + '-reports', type=Path, nargs=2, required=True)
    parser.add_argument('--joint-plan', type=Path); parser.add_argument('--joint-reports', type=Path, nargs=2)
    parser.add_argument('--frozen-aliases', type=Path); args = parser.parse_args()
    if args.stage == 'freeze' and args.joint_plan is None: parser.error('freeze requires the pre-evaluation joint plan')
    if args.stage == 'report' and (args.joint_reports is None or args.frozen_aliases is None): parser.error('report requires the original closed report pair and frozen aliases')
    export(args)


if __name__ == '__main__': main()
