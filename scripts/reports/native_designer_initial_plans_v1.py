"""Literal first plans of every closed T/U slot, not inferred author cognition."""
import argparse
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-designer-initial-plans.v1'


def first_plan(step):
    checked(step)
    transition = step['transition']
    if step['step'] != 0 or step['status'] != 'applied' or transition['tool'] != 'plan' or not transition['ok']:
        raise ValueError('literal successful first planner action required')
    if transition['result']['source_execution'] or transition['result']['literal_document_changed']:
        raise ValueError('first plan must not be relabeled as implementation')
    return clone(transition['result']['stored_model_authored_plan'])


def export(args):
    source = pinned_revision(ROOT)
    root, out = args.run.resolve(), args.output.resolve()
    files = [args.audit_one.resolve(), args.audit_two.resolve(), args.report.resolve(), root/'plan.json']
    if out.exists() or out.is_relative_to(root) or any(p.is_relative_to(out) for p in files):
        raise ValueError('fresh output outside original inputs required')
    if files[0] == files[1] or files[0].read_bytes() != files[1].read_bytes():
        raise ValueError('two distinct matching original audits required')
    hashes = {str(p): file_sha256(p) for p in files}
    audit, _, report, plan = [checked(json.loads(p.read_text())) for p in files]
    before = _inventory(root)
    if (report['schema'] != 'scienceutopia.native-objective-instrument-report.v1'
            or audit['schema'] != 'scienceutopia.native-objective-instrument-loop-audit.v1'
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or report['source_commit'] != plan['source_commit'] or audit['source_commit'] != plan['source_commit']
            or audit['plan_sha256'] != plan['content_sha256'] or report['plan_sha256'] != plan['content_sha256']
            or report['audit_sha256'] != audit['content_sha256']
            or audit['raw_inventory_sha256'] != digest(before)
            or audit['new_model_calls'] or audit['new_code_executions']
            or len(report['slots']) != 8
            or {(s['objective'], s['generation']) for s in report['slots']}
                != {(o, g) for o in ('throughput', 'content-utility') for g in range(4)}):
        raise ValueError('complete original-source T/U closure and every proposal slot required')
    rows = []
    for slot in report['slots']:
        sha = slot['request_sha256']
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('literal request identity required')
        p = root/'search'/slot['objective']/'authoring'/('generation-'+sha)/'authoring'/('generation-'+sha)/'step-00.completed.json'
        relative = str(p.relative_to(root))
        if not p.is_file() or before.get(relative) != file_sha256(p):
            raise ValueError('exact original audited first planner file required')
        step = checked(json.loads(p.read_text()))
        rows.append({'objective': slot['objective'], 'generation': slot['generation'],
            'request_sha256': sha, 'first_step_relative_path': relative,
            'first_step_file_sha256': file_sha256(p), 'first_step_content_sha256': step['content_sha256'],
            'untrusted_initial_plan': first_plan(step),
            'actual_native_status': slot['status'], 'actual_assigned_loss': slot['loss'],
            'actual_changed_paths_from_parent': clone(slot['changed_paths_from_parent']),
            'actual_connections_changed': slot['connections_changed'],
            'actual_schedules_changed': slot['schedules_changed'],
            'actual_nodes_added': clone(slot['nodes_added']), 'actual_nodes_removed': clone(slot['nodes_removed'])})
    result = {'schema': SCHEMA, 'analysis_source_commit': source,
        'scientific_source_commit': plan['source_commit'], 'plan_sha256': plan['content_sha256'],
        'original_audit_content_sha256': audit['content_sha256'],
        'original_report_content_sha256': report['content_sha256'],
        'raw_inventory_sha256': digest(before), 'slots': rows,
        'scope': 'Literal first stored planner actions from all eight original proposal slots, including '
            'later nulls and identity submission. Plans are untrusted hypotheses, not implemented '
            'effects, measured counterfactuals or an explanation of model cognition. First targets '
            'may be revised later; original final edit/status fields remain separate. No causal '
            'effect of catalog coverage, initial representation, reasoning mode or model capacity '
            'is identified by this descriptive join.',
        'new_model_calls': 0, 'new_code_executions': 0, 'candidate_reselection': False,
        'publication_ready': False}
    if (before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in files}
            or pinned_revision(ROOT) != source):
        raise ValueError('original raw/input or reader source changed')
    out.mkdir(parents=True); save(out/'plans.json', result)
    save(out/'manifest.json', {'schema': SCHEMA+'.export', 'inputs': hashes,
        'analysis_source_commit': source, 'raw_inventory_sha256': digest(before),
        'plans_file_sha256': file_sha256(out/'plans.json'), 'new_model_calls': 0,
        'new_code_executions': 0})
    print(json.dumps({'slots': len(rows), 'plans_file_sha256': file_sha256(out/'plans.json')}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'audit-one', 'audit-two', 'report', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    export(p.parse_args())


if __name__ == '__main__':
    main()
