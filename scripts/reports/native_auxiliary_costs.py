"""Closed-audit cost projection for proposal, calibration and empty-prompt loads.

Provider-reported counts/durations are not fresh GPU operations, FLOPs or money.
Native/transport token aliases and nested elapsed times must never be added.
"""
import argparse
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path
import re

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_design_benchmark import SCHEMA as STUDY, checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json, file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-auxiliary-model-costs.v1'
FIELDS = {'native_prompt_eval_count': 'integer count', 'native_eval_count': 'integer count',
    'transport_prompt_tokens': 'integer count', 'transport_completion_tokens': 'integer count',
    'provider_total_duration_ns': 'integer nanoseconds', 'provider_load_duration_ns': 'integer nanoseconds',
    'provider_prompt_eval_duration_ns': 'integer nanoseconds', 'provider_eval_duration_ns': 'integer nanoseconds',
    'host_model_call_seconds': 'seconds', 'caller_elapsed_seconds': 'seconds', 'transport_seconds': 'seconds'}


def summarize(events):
    result = {}
    for key, unit in FIELDS.items():
        values = [e['values'][key] for e in events]
        valid = lambda v: (type(v) is int and v >= 0 if unit.startswith('integer') else
                          type(v) in (int, float) and math.isfinite(v) and v >= 0)
        known = [v for v in values if valid(v)]; missing = sum(v is None for v in values)
        result[key] = {'unit': unit,
            'recorded_sum': (sum(known) if unit.startswith('integer') else math.fsum(known))
                if known or not events else None,
            'known_records': len(known), 'missing_records': missing,
            'invalid_records': len(events) - len(known) - missing,
            'all_records_known': len(known) == len(events)}
    return {'request_intents': len(events),
        **{name: sum(e[name] for e in events) for name in ('completion_record_available',
            'recorded_POST_attempt', 'known_HTTP_response', 'final_response_reported')},
        'status_counts': dict(Counter(e['status'] for e in events)), 'measurements': result,
        'unknown_usage_imputed': False}


def cost_values(transport, *, model, host_seconds=None, caller_seconds=None):
    parsed = transport.get('response_payload')
    if parsed is not None:
        raw = transport.get('raw_http_response')
        if not isinstance(raw, str) or digest(decode_json(raw, strict=True, finite_floats=True)) != digest(parsed):
            raise ValueError('auxiliary parsed response differs from exact original HTTP body')
    body = parsed if isinstance(parsed, dict) else {}
    if body.get('model') is not None and body['model'] != model:
        raise ValueError('auxiliary response model differs from declared role')
    # Keep both reported aliases, but never add or repair them. A missing native
    # count remains missing even for a confirmed empty-prompt role load.
    return deepcopy({'native_prompt_eval_count': body.get('prompt_eval_count'), 'native_eval_count': body.get('eval_count'),
        'transport_prompt_tokens': transport.get('prompt_tokens'),
        'transport_completion_tokens': transport.get('completion_tokens'),
        **{'provider_' + key + '_ns': body.get(key) for key in
            ('total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration')},
        'host_model_call_seconds': host_seconds, 'caller_elapsed_seconds': caller_seconds,
        'transport_seconds': transport.get('elapsed_seconds')})


def event(kind, identity, transport, *, model, status, completion=True, host_seconds=None, caller_seconds=None):
    body = transport.get('response_payload'); body = body if isinstance(body, dict) else {}
    return {'kind': kind, 'identity': identity, 'status': status,
        'completion_record_available': completion, 'recorded_POST_attempt': 'request_payload' in transport,
        'known_HTTP_response': 'http_status' in transport and 'raw_http_response' in transport,
        'final_response_reported': body.get('done') is True and body.get('done_reason') != 'length',
        'values': cost_values(transport, model=model, host_seconds=host_seconds, caller_seconds=caller_seconds)}


def analyze(root, plan, audit, *, expected_source):
    root = Path(root).resolve(); checked(plan, STUDY); checked(audit, STUDY + '.audit')
    end = audit.get('writer', {}).get('ended', {})
    if (plan['source_commit'] != expected_source or audit['source_commit'] != expected_source
            or audit['plan_sha256'] != plan['content_sha256']
            or audit['source_proofs']['status'] != 'verified-exact-source-closure'
            or end.get('status') != 'exited' or type(end.get('exit_code')) is not int or end['exit_code'] != 0
            or audit['new_model_calls'] != 0 or audit['new_code_executions'] != 0
            or audit.get('raw_inventory_unchanged') is not True):
        raise ValueError('closed exact-source study audit required; never summarize a live writer')
    before = _inventory(root)
    if before != audit['input_inventory']: raise ValueError('raw inventory differs from exact closed audit')

    def read(relative):
        path = root / relative
        if (relative not in before or any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root))
                or not path.resolve().is_relative_to(root)
                or file_sha256(path) != before[relative]):
            raise ValueError('auxiliary input is absent, linked, outside or changed from audited inventory')
        return decode_json(path.read_text(), strict=True, finite_floats=True)

    try:
        events = []; proposals = {}; calibrations = {}; loads = []; seen_loads = set()
        if set(audit['runs']) != set(plan['campaign_bindings']) or set(audit['certificates']) != set(plan['campaign_bindings']):
            raise ValueError('all declared search runs and calibrations required')
        for run, bindings in plan['campaign_bindings'].items():
            if set(audit['runs'][run]) != set(bindings): raise ValueError('declared proposal arms differ')
            proposals[run] = {}
            for arm in bindings:
                data = audit['runs'][run][arm]; random = plan['assignments'][arm]['method'] == 'random'
                proofs = data.get('designer', {}).get('proofs', [])
                if (random and proofs) or (not random and len(proofs) != plan['generations']):
                    raise ValueError('declared authoring/author-absent counts differ')
                arm_events = []; generations = []
                for proof in proofs:
                    if not isinstance(proof['request_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', proof['request_sha256']):
                        raise ValueError('exact original author request identity required')
                    cell = 'search/' + run + '/arms/' + arm.replace(':', '--') + '/authoring/generation-' + proof['request_sha256']
                    starts, completed = proof['started_records'], proof['completed_records']; current = []
                    if len(starts) != len(completed) or proof['counts']['dispatch_intents'] != len(starts):
                        raise ValueError('author step intents/completions differ')
                    for start, step in zip(starts, completed):
                        started_path = cell + f"/step-{start['step']:02d}.started.json"
                        completed_path = cell + f"/step-{start['step']:02d}.completed.json"
                        if digest(read(started_path)) != digest(start):
                            raise ValueError('author cost intent differs from exact raw record')
                        if step is None:
                            if completed_path in before: raise ValueError('unknown author response has an unaccounted raw completion')
                        elif digest(read(completed_path)) != digest(step):
                            raise ValueError('author costs differ from exact raw completed record')
                        transport = {} if step is None else step['model_reply'].get('transport', {})
                        if not isinstance(transport, dict): raise ValueError('audited author transport must be an object')
                        current.append(event('designer-proposal', run + ':' + arm + ':' + proof['request_sha256'] + ':' + str(start['step']),
                            transport, model=plan['designer']['model'],
                            status='interrupted-response-unknown' if step is None else step['status'], completion=step is not None,
                            host_seconds=None if step is None else step.get('model_call_seconds')))
                    summary = summarize(current)
                    for key in ('recorded_POST_attempt', 'known_HTTP_response'):
                        if summary[key] != proof['counts'][key + 's']:
                            raise ValueError('auxiliary POST/HTTP counts differ from original author audit')
                    generations.append({'request_sha256': proof['request_sha256'], **summary})
                    arm_events.extend(current)
                proposals[run][arm] = {'author_absent_by_design': random, 'generations': generations, **summarize(arm_events)}
                events.extend(arm_events)
            path = 'search/' + run + '/preflight/certificate.json'; certificate = read(path)
            checked(certificate, 'scienceutopia.designer-interface-certificate.v16')
            if (certificate['content_sha256'] != audit['certificates'][run]['certificate_sha256']
                    or certificate['plan']['source_commit'] != expected_source
                    or certificate['plan']['provider'] != plan['designer']
                    or len(certificate['records']) != audit['certificates'][run]['controls']):
                raise ValueError('calibration costs differ from original audited certificate')
            current = []; ids = set()
            for record in certificate['records']:
                identity = record['intent']['id']
                if identity in ids: raise ValueError('duplicate physical calibration control')
                ids.add(identity)
                current.append(event('designer-calibration', run + ':' + identity, record['transport'],
                    model=plan['designer']['model'], status='passed' if record['ok'] else 'failed',
                    caller_seconds=record.get('elapsed_seconds')))
            calibrations[run] = {'certificate_file_sha256': before[path], **summarize(current)}
            events.extend(current)
        for entry in audit['designer_loads']:
            path = Path(entry['load'])
            if not path.is_absolute() or not path.is_relative_to(root): raise ValueError('role load locator outside audited root')
            name = str(path.relative_to(root))
            if name in seen_loads: raise ValueError('duplicate physical role load, never deduplicate by content')
            seen_loads.add(name)
            intent = read(str(path.with_suffix('.started.json').relative_to(root)))
            checked(intent, 'scienceutopia.explicit-local-role-load.v38.intent')
            role = intent['role']
            if role not in ('scientist', 'designer') or intent['provider'] != plan[role]:
                raise ValueError('role load provider differs')
            record = read(name) if name in before else None
            if record is not None:
                checked(record, 'scienceutopia.explicit-local-role-load.v38')
                if (record['intent_sha256'] != intent['content_sha256'] or record['role'] != role
                        or record['provider'] != plan[role]): raise ValueError('load completion differs from exact intent')
            status = ('dispatched-response-unknown' if record is None else
                      'completed-load' if record.get('valid_empty_prompt_load') is True else 'failed-or-unknown-load')
            if entry['proof']['status'] != status: raise ValueError('role load status differs from raw evidence')
            transport = {} if record is None else {
                **{k: record[k] for k in ('http_status', 'raw_http_response', 'response_payload') if k in record},
                'request_payload': intent['request_payload']}
            item = event('role-load-' + role, name, transport, model=plan[role]['model'],
                status=status, completion=record is not None,
                caller_seconds=None if record is None else record.get('elapsed_seconds'))
            loads.append(item); events.append(item)
        groups = {kind: summarize([e for e in events if e['kind'] == kind]) for kind in
                  ('designer-proposal', 'designer-calibration', 'role-load-designer', 'role-load-scientist')}
        result = {'schema': SCHEMA, 'classification': plan['classification'], 'source_commit': expected_source,
            'plan_sha256': plan['content_sha256'], 'input_audit_content_sha256': audit['content_sha256'],
            'input_inventory_sha256': digest(before), 'projection_source_sha256': file_sha256(Path(__file__)),
            'proposal_runs': proposals, 'calibration_runs': calibrations, 'role_loads': loads, 'groups': groups,
            'events': events, 'raw_inventory_unchanged': True, 'new_model_calls': 0, 'new_code_executions': 0,
            'unknown_usage_imputed': False, 'token_aliases_or_nested_durations_added': False,
            'full_project_compute_FLOPs_energy_money_or_fresh_GPU_cost_claimed': False,
            'scope': 'Declared proposal steps, calibration controls and empty-prompt load intents only. Includes failures/unknowns, not just successful designs. Native token fields and transport aliases are separate; durations overlap and are not wall-time summands. Scientist response usage uses the separate native_token_costs projection. Retrieval, containers, host/code-agent work and earlier exploration remain outside these measurements; unreported load usage is unknown, not zero. No actual HTTP server receipt is inferred from a dispatch intent.'}
        if 'analysis_adapter' in audit: result['input_audit_analysis_adapter'] = deepcopy(audit['analysis_adapter'])
        result['content_sha256'] = digest(result)
        return result
    finally:
        if _inventory(root) != before: raise ValueError('raw evidence changed during auxiliary cost projection')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'plan', 'audit', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expected-source', required=True); args = parser.parse_args(argv)
    if args.output.exists() or args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error('fresh auxiliary cost output outside raw root required')
    bodies = {p: p.read_bytes() for p in (args.plan, args.audit)}
    data = {p: decode_json(b.decode(), strict=True, finite_floats=True) for p, b in bodies.items()}
    result = analyze(args.run, data[args.plan], data[args.audit], expected_source=args.expected_source)
    if any(p.read_bytes() != b for p, b in bodies.items()): raise ValueError('input plan/audit changed')
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False, indent=2)
    print({'content_sha256': result['content_sha256'], 'auxiliary_intents': len(result['events'])})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
