"""Export compact, all-slot evidence from two closed identical cold audits."""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import shutil

from utopia.optimization.native_numeric_designer import checked, save
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest, make_patch, apply_design_patch
from utopia.utils.data_utils import file_sha256


def read(path):
    return json.loads(Path(path).read_text())


def usage(rows):
    return {'chat_posts': len(rows),
        **{name: {'known_sum': sum(r[key] for r in rows if type(r.get(key)) is int),
                  'unknown_responses': sum(type(r.get(key)) is not int for r in rows)}
           for name, key in [('prompt_tokens', 'prompt_tokens'), ('output_tokens', 'output_tokens')]},
        'known_http_seconds': sum(r['elapsed_seconds'] for r in rows if r.get('elapsed_seconds') is not None),
        'unknown_http_durations': sum(r.get('elapsed_seconds') is None for r in rows),
        'length_terminated_responses': sum(r.get('done_reason') == 'length' for r in rows),
        'nonfinal_responses': sum(r.get('done') is not True for r in rows)}


def literal_patch(base, candidate):
    """Retain ALL literal edits, including upstream parameters, not only code."""
    def walk(left, right, path=''):
        if isinstance(left, dict) and isinstance(right, dict):
            result = []
            for key in sorted(set(left) | set(right)):
                child = path+'/'+key.replace('~','~0').replace('/','~1')
                if key not in right:
                    result.append({'op':'remove','path':child})
                elif key not in left:
                    result.append({'op':'add','path':child,'value':clone(right[key])})
                else:
                    result.extend(walk(left[key], right[key], child))
            return result
        if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
            return [p for i, (a, b) in enumerate(zip(left, right)) for p in walk(a, b, path+'/'+str(i))]
        return [] if digest(left) == digest(right) else [{'op':'replace','path':path,'value':clone(right)}]
    operations = walk(base.to_dict(), candidate.to_dict())
    if not operations:
        return None
    patch = make_patch(base, operations, rationale='Literal complete candidate export, not an executed policy evaluation')
    if apply_design_patch(base, patch).fingerprint != candidate.fingerprint:
        raise ValueError('literal candidate reconstruction differs')
    return patch


def export(root, audit_one, audit_two, probe, base_system, output):
    if output.exists():
        raise ValueError('fresh compact data directory required')
    if audit_one.read_bytes() != audit_two.read_bytes():
        raise ValueError('original-source cold audits differ')
    audit = checked(read(audit_one)); plan = checked(read(root/'plan.json'))
    probe_report = checked(read(probe/'report.json')); probe_plan = checked(read(probe/'plan.json'))
    if (audit['terminal']['status'] != 'complete'
            or any(len(x) != 8 for x in (audit['slots'], plan['slots'], probe_plan['candidates'], probe_report['slots']))
            or audit['plan_sha256'] != file_sha256(root/'plan.json')
            or probe_report['audit_file_sha256'] != file_sha256(audit_one)
            or probe_report['plan_file_sha256'] != file_sha256(probe/'plan.json')):
        raise ValueError('closed assay/probe inputs differ')
    base = SystemSpec.from_dict(read(base_system)); rows = []
    for slot, audited, candidate in zip(plan['slots'], audit['slots'], probe_plan['candidates']):
        if not slot['id'] == audited['id'] == candidate['id']:
            raise ValueError('all-slot chronology differs')
        path = root/'sessions'/slot['id']; request = slot['request']
        steps = [read(p) for p in sorted(path.glob('authoring/generation-*/step-*.completed.json'))]
        actions = [(s.get('model_reply') or {}).get('output') or {} for s in steps]
        row = {'id': slot['id'], 'objective': slot['objective'], 'history_index': slot['history_index'],
            'condition': slot['condition'], 'request_sha256': slot['request_sha256'],
            'model_plan': actions[0], 'finish_action': actions[-1],
            'read_file_counts': dict(Counter(a['filename'] for a in actions
                if a.get('tool') == 'read_file' and isinstance(a.get('filename'), str))),
            'step_status_counts': dict(Counter(s['status'] for s in steps)),
            'elapsed_worker_seconds': checked(read(path/'worker-result.json'))['elapsed_seconds'],
            'usage': usage(audited['wire'])}
        if candidate['system'] is not None:
            system = SystemSpec.from_dict(candidate['system'])
            node = next(n for n in system.mechanisms if n.mechanism_id == 'world.selection')
            source = node.parameters['code_artifact']['source']
            row.update(candidate_sha256=system.fingerprint, selection_source=source,
                selection_source_utf8_sha256=hashlib.sha256(source.encode()).hexdigest(),
                complete_literal_patch=literal_patch(base, system))
        rows.append(row)
    loads = [checked(read(p)) for p in sorted(root.glob('readiness/*/designer-load.json'))
             + sorted(root.glob('sessions/*/designer-load.json'))]
    endpoints = []
    for p in root.rglob('dispatch-*.intent.json'):
        intent = checked(read(p)); response = checked(read(p.with_name(p.name.replace('.intent.', '.http.'))))
        endpoints.append(datetime.fromisoformat(intent['started_utc']) + timedelta(seconds=response['elapsed_seconds']))
    started = datetime.fromisoformat(checked(read(root/'run-started.json'))['started_utc'])
    output.mkdir(parents=True)
    shutil.copyfile(audit_one, output/'audit.json')
    shutil.copyfile(probe/'report.json', output/'fixed-record-probe.json')
    save(output/'policies.json', {'schema':'scienceutopia.causal-authoring-policy-export.v1',
        'source_commit': plan['source_commit'], 'base_system_file_sha256':file_sha256(base_system),
        'base_system_sha256':base.fingerprint, 'slots':rows})
    save(output/'costs.json', {'schema':'scienceutopia.causal-authoring-costs.v1',
        'authoring':usage([w for s in audit['slots'] for w in s['wire']]),
        'readiness':usage(audit['readiness_wire']),
        'explicit_empty_prompt_loads':{'requests':len(loads),
            'confirmed_empty':sum(r['valid_empty_prompt_load'] for r in loads),
            'unreported_prompt_token_counts':sum('prompt_eval_count' not in r['response_payload'] for r in loads),
            'unreported_output_token_counts':sum('eval_count' not in r['response_payload'] for r in loads)},
        'started_utc':started.isoformat(), 'last_chat_response_utc':max(endpoints).isoformat(),
        'observed_start_to_last_chat_response_seconds':(max(endpoints)-started).total_seconds(),
        'new_scientist_inference':0, 'new_native_worlds':0,
        'interpretation':'Chat generation, readiness and empty-prompt loading are separate; absent load token counts are unknown.'})
    save(output/'manifest.json', {'schema':'scienceutopia.causal-authoring-export.v1',
        'assay_source_commit':plan['source_commit'], 'probe_source_commit':probe_plan['source_commit'],
        'assay_plan_file_sha256':file_sha256(root/'plan.json'),
        'two_identical_cold_audit_sha256':file_sha256(audit_one),
        'probe_plan_file_sha256':file_sha256(probe/'plan.json'),
        'files':{p.name:file_sha256(p) for p in sorted(output.glob('*.json'))}})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ('root', 'audit-one', 'audit-two', 'probe', 'base-system', 'output'):
        p.add_argument('--'+field, type=Path, required=True)
    a = p.parse_args()
    export(a.root, a.audit_one, a.audit_two, a.probe, a.base_system, a.output)


if __name__ == '__main__':
    main()
