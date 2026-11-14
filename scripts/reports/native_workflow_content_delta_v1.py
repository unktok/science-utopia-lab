"""All completed workflow accepted sets, with nulls retained; no new evaluation."""
import argparse
import itertools
import inspect
import json
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_content_overlap_v1 import overlap
from scripts.reports.native_planning_content_contributions_v1 import contributions
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-workflow-content-delta.v1'


def analyze(report, audit, observations):
    checked(report); checked(audit)
    if (report['schema'] != 'scienceutopia.native-workflow-objective-report.v1'
            or audit['schema'] != 'scienceutopia.native-workflow-objective-loop-audit.v1'
            or report['audit_content_sha256'] != audit['content_sha256']
            or report['source_commit'] != audit['source_commit']
            or report['plan_sha256'] != audit['plan_sha256']
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['held_out_evaluation'] or audit['new_model_calls'] or audit['new_code_executions']):
        raise ValueError('normally closed original workflow report/audit required')
    if (report['score_order'] != ['throughput', 'content-utility'] or len(report['slots']) != 6
            or {(s['objective'], s['generation']) for s in report['slots']}
                != {(o, g) for o in report['score_order'] for g in range(3)}):
        raise ValueError('all six original objective slots required, including generation nulls')
    labels = {r['physical_job']: r['label'] for r in report['references']}
    labels.update({s['physical_job']: ('T' if s['objective'] == 'throughput' else 'U') + str(s['generation'])
        for s in report['slots'] if s['physical_job'] is not None})
    identities = {w['identity'] for w in audit['worlds']}
    if (len(identities) != len(audit['worlds']) or set(labels) != identities
            or set(observations) != identities or report['physical_worlds'] != len(identities)):
        raise ValueError('every physical world and original observation required')
    cache = {}; worlds = []; accepted = {}
    for w in audit['worlds']:
        identity = w['identity']; o = observations[identity]
        if (o['status'] != w['status'] or o['suggestion_id'] != identity
                or o['candidate'] != w['system'] or o['loss'] != w['scores'][w['objective']]):
            raise ValueError('original observation identity/system/status differs')
        row = {k: clone(w[k]) for k in ('identity', 'role', 'seed', 'status', 'scores')}
        row.update(label=labels[identity], accepted_records=None, sign_counts=None)
        if w['status'] == 'complete':
            m, = o['metadata']['measurements']; observer = checked(m['common_content_observer'])
            detail = contributions(observer['accepted_decisions'], cache)
            u = math.fsum(r['recorded_centered_utility'] for r in detail)
            q = math.fsum(r['mean_score'] for r in detail)
            if (w['scores'] != {'throughput': -float(len(detail)), 'content-utility': -u}
                    or m['metrics']['native.accepted_decisions'] != {'status': 'measured', 'value': len(detail)}
                    or m['metrics']['native.common_content_score_sum'] != {'status': 'measured', 'value': q}
                    or m['metrics']['native.common_content_utility_sum'] != {'status': 'measured', 'value': u}
                    or observer['unique_contents'] != len({r['content_sha256'] for r in detail})):
                raise ValueError('accepted records do not reconstruct original operational scores')
            row.update(accepted_records=detail, sign_counts={s: sum(r['sign'] == s for r in detail)
                for s in ('positive', 'zero', 'negative')})
            accepted[identity] = observer['accepted_decisions']
        elif any(v is not None for v in w['scores'].values()) or o['loss'] is not None:
            raise ValueError('failed world has no scientific score or zero contribution')
        worlds.append(row)
    if len({w['seed'] for w in worlds}) != 1:
        raise ValueError('one common development condition required; no cross-seed overlap pooling')
    result = {'schema': SCHEMA, 'scientific_source_commit': report['source_commit'],
        'original_report_content_sha256': report['content_sha256'],
        'original_audit_content_sha256': audit['content_sha256'], 'worlds': worlds,
        'all_slots': [{k: clone(s[k]) for k in ('objective', 'generation', 'status', 'physical_job')}
            for s in report['slots']],
        'all_complete_pairs': [{'left': a, 'right': b, 'left_label': labels[a], 'right_label': labels[b],
            'overlap': overlap(accepted[a], accepted[b])} for a, b in itertools.combinations(accepted, 2)],
        'scope': 'Post-hoc accepted-record multisets and exact arithmetic of existing fixed opinions. '
            'Every decision occurrence counts; same-year/paper/content occurrences define overlap. '
            'These are not causal extra/missing papers, new counterfactuals, attainable subset optima, '
            'independent critic errors, verified science, a changed objective or independent optimizer histories.',
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_code_executions': 0,
        'loss_changed': False, 'selection_changed': False, 'publication_ready': False}
    result['content_sha256'] = digest(result)
    return result


def export(args):
    root = args.run.resolve(); out = args.output.resolve()
    if out.exists() or out.is_relative_to(root):
        raise ValueError('fresh output outside original run required')
    if args.audit_one.read_bytes() != args.audit_two.read_bytes():
        raise ValueError('two matching original-source audits required')
    before = _inventory(root); audit = checked(json.loads(args.audit_one.read_text()))
    plan = checked(json.loads((root / 'plan.json').read_text()))
    if (digest(before) != audit['raw_inventory_sha256'] or len(before) != audit['raw_files']
            or plan['content_sha256'] != audit['plan_sha256']):
        raise ValueError('original audited raw inventory/plan differs')
    paths = [args.report, args.audit_one, args.audit_two, Path(__file__),
        Path(inspect.getfile(overlap)), Path(inspect.getfile(contributions))]
    inputs = {str(p.resolve()): file_sha256(p) for p in paths}
    observations = {}
    for label in plan['reference_order']:
        o = checked(json.loads((root / 'references' / label / 'observation.json').read_text()))
        observations[o['suggestion_id']] = o
    for objective in plan['objectives']:
        state = json.loads((root / 'search' / objective / 'campaign/native-adaptive-state.json').read_text())
        if state['pending'] is not None:
            raise ValueError('closed campaign cannot have a pending proposal')
        for record in state['records']:
            for o in record['observations']:
                if o is not None:
                    if o['suggestion_id'] in observations:
                        raise ValueError('duplicate physical observation')
                    observations[o['suggestion_id']] = o
    result = analyze(json.loads(args.report.read_text()), audit, observations)
    if before != _inventory(root) or inputs != {p: file_sha256(Path(p)) for p in inputs}:
        raise ValueError('original raw evidence or reader inputs changed')
    return save(out, {'schema': SCHEMA + '.export', 'analysis': result,
        'input_and_component_file_sha256': inputs, 'raw_inventory_sha256': digest(before),
        'raw_files': len(before), 'original_bytes_unchanged': True,
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_code_executions': 0})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'report', 'audit-one', 'audit-two', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    print(export(parser.parse_args())['content_sha256'])


if __name__ == '__main__': main()
