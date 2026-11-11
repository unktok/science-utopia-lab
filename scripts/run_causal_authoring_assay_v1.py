"""Finite paired historical-request diagnostic; never a new native loss study.

Only the existing bounded local editor dispatches inference. Unknown completion
stops subsequent calls. All eight slots are frozen before calibration; no refill.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path

from scripts.run_pre_scale_search_v1 import require_environment
from utopia.optimization.native_bounded_staged_designer import execute, replay, CompletionUnknown
from utopia.optimization.native_causal_design import OPTION
from utopia.optimization.native_designer_preflight import runtime_binding, backend_binding, planned_cases
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_fixed_production_domain import allow_review_routing
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import save, checked
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.causal-authoring-assay.v1'
PROTOCOL = 'research/protocols/campaigns/causal-authoring-assay-v1.md'
OBJECTIVES = ('throughput', 'efficiency')
HISTORICAL_SOURCE = '62388a74d071a3a4fdc8cc309c2807422f96223f'


def read(path):
    return json.loads(Path(path).read_text())


def request_pair(original, *, source, archive):
    """Prospective domain/context, literal archived parent/history/objective.

    Historical world_binding stays historical. It is not a new measurement or
    source-equivalence assertion. Both actual model views carry this notice.
    """
    base = clone(original)
    anchor = SystemSpec.from_dict(base['design_space_anchor'])
    base['design_space'] = allow_review_routing(anchor, base['design_space'])
    provenance = {**base['strategy_provenance'], 'protocol': PROTOCOL,
                  'diagnostic_request_replay': True}
    base['strategy_provenance'] = provenance
    base['feedback_policy'] = {**base['feedback_policy'],
        'study': 'historical-request authoring diagnostic, not closed-loop optimization',
        'measurement_source_commit': original['world_binding']['source_commit'],
        'authoring_source_commit': source,
        'historical_source_equivalence_established': False,
        'historical_measurements_are_not_new_candidate_losses': True,
        'archive': clone(archive)}
    # This is a diagnostic binding, not a forged adaptive-campaign binding.
    base['binding_sha256'] = digest({'assay': SCHEMA, 'source': source,
                                    'archive': archive, 'base_request': original})
    result = {}
    for enabled in (False, True):
        request = clone(base)
        request['strategy_provenance'][OPTION] = enabled
        if enabled:
            request[OPTION] = True
        result['on' if enabled else 'off'] = request
    return result


def build_plan(old_root, *, source, backend):
    old_root = Path(old_root)
    operator = checked(read(old_root/'plan.json'))
    if operator['source_commit'] != HISTORICAL_SOURCE:
        raise ValueError('predeclared closed historical source required')
    validate_designer_binding(operator['designer'], scientist_binding=operator['scientist'])
    slots = []; archives = []
    for history in (0, 1):
        for objective_index, objective in enumerate(OBJECTIVES):
            path = old_root/f'search/run-00/{objective}--code-and-graph/campaign/native-adaptive-state.json'
            state = read(path)
            record = state['records'][history]
            original = record['request']
            if (record['request_sha256'] != digest(original)
                    or original['generation'] != history
                    or len(original['history']) != history
                    or original['world_binding']['source_commit'] != HISTORICAL_SOURCE
                    or original['loss_spec'] != operator['losses'][objective]):
                raise ValueError('historical request identity/order/objective differs')
            archive = {'path': str(path.resolve()), 'file_sha256': file_sha256(path),
                       'record_index': history, 'request_sha256': digest(original)}
            archives.append(archive)
            pair = request_pair(original, source=source, archive=archive)
            # Fixed counterbalancing; no ordering based on a generated outcome.
            order = ('off', 'on') if (history + objective_index) % 2 == 0 else ('on', 'off')
            for condition in order:
                request = pair[condition]
                slots.append({'id': f'{objective}-h{history}-{condition}', 'objective': objective,
                              'history_index': history, 'condition': condition,
                              'request': request, 'request_sha256': digest(request)})
    return {'schema': SCHEMA+'.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'designer': operator['designer'], 'scientist': operator['scientist'],
        'backend': backend, 'operator_plan_sha256': file_sha256(old_root/'plan.json'),
        'archives': archives, 'slots': slots,
        'calibration_slot_ids': {c: f'efficiency-h1-{c}' for c in ('off', 'on')},
        'budget': {'authoring_sessions': 8, 'authoring_posts_upper_bound': 128,
            'calibration_sessions': 2, 'calibration_posts_upper_bound': 80,
            'steps_per_authoring_session': 16, 'output_tokens_per_post': 8192,
            'context_tokens': 40960, 'think': False, 'session_wall_seconds': 1200,
            'http_timeout_seconds': [10, 900], 'native_worlds': 0,
            'replace_failed_slots': False, 'unknown_completion_stops_following_calls': True},
        'interpretation': {'historical_request_replay': True,
            'new_closed_loop_optimization': False, 'scientist_inference': False,
            'candidate_losses_measured': False,
            'decoding_seeds': 'existing request-bound seeds; context changes binding and may change seed',
            'paired_conditions': 'same historical request, parent, loss, domain and budgets; only context availability differs',
            'inference': 'eight fixed diagnostic sessions, not a powered causal-effect estimate'}}


def require_plan(root):
    plan = checked(read(root/'plan.json'))
    if (plan['source_commit'] != pinned_revision(ROOT) or plan['runtime'] != runtime_binding()
            or plan['protocol_sha256'] != file_sha256(ROOT/PROTOCOL)):
        raise ValueError('assay clean source/runtime/protocol changed')
    return plan


def prepare(root, old_root):
    require_environment()
    if root.exists():
        raise ValueError('fresh assay output required')
    source = pinned_revision(ROOT)
    operator = checked(read(old_root/'plan.json'))
    backend = backend_binding(operator['designer'])
    plan = build_plan(old_root, source=source, backend=backend)
    root.mkdir(parents=True)
    save(root/'plan.json', plan)
    print(json.dumps({'prepared': source, 'slots': len(plan['slots']), 'inference_calls': 0}), flush=True)


def run(root):
    require_environment()
    plan = require_plan(root)
    with (root/'assay-writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root/'run-started.json').exists():
            raise ValueError('assay already consumed; audit only, no redispatch')
        save(root/'run-started.json', {'schema': SCHEMA+'.start',
            'plan_sha256': file_sha256(root/'plan.json'),
            'started_utc': datetime.now(timezone.utc).isoformat()})
        outcome = {'schema': SCHEMA+'.terminal', 'status': 'complete', 'slots': []}
        try:
            for condition in ('off', 'on'):
                slot = next(s for s in plan['slots'] if s['id'] == plan['calibration_slot_ids'][condition])
                count = len(planned_cases(slot['request'], 'staged-v15', BOUNDED_AUTHORING))
                if count > 40:
                    raise ValueError('calibration exceeds declared40 POST ceiling')
                result = execute(root/'readiness'/condition, kind='calibration',
                    request=slot['request'], provider=plan['designer'], source_commit=plan['source_commit'],
                    maximum_posts=count, inference_lock=root/'inference.lock')
                if not result['passed']:
                    raise ValueError('fresh '+condition+' readiness failed; no candidate dispatch')
                cert = checked(read(root/'readiness'/condition/'calibration/certificate.json'))
                if (cert['plan']['request'] != slot['request'] or cert['plan']['backend'] != plan['backend']
                        or cert['plan']['runtime'] != plan['runtime']):
                    raise ValueError('fresh readiness condition/backend/runtime differs')
            for slot in plan['slots']:
                target = root/'sessions'/slot['id']
                print(json.dumps({'active': slot['id']}), flush=True)
                try:
                    definition = execute(target, kind='proposal', request=slot['request'],
                        provider=plan['designer'], source_commit=plan['source_commit'],
                        certificate=root/'readiness'/slot['condition']/'calibration/certificate.json',
                        inference_lock=root/'inference.lock')
                    row = {'id': slot['id'], 'returned_definition': definition is not None}
                except Exception as error:
                    # Known terminal failure is charged, not replaced. Unknown
                    # completion is a BaseException and exits the entire loop.
                    row = {'id': slot['id'], 'error_type': type(error).__name__, 'error': str(error)}
                outcome['slots'].append(row)
                save(target/'assay-slot.json', {'schema': SCHEMA+'.slot', **row})
        except BaseException as error:
            outcome.update(status='stopped', error_type=type(error).__name__, error=str(error),
                           completion_unknown=isinstance(error, CompletionUnknown))
        save(root/'terminal.json', outcome)
        print(json.dumps(outcome), flush=True)


def differences(left, right, path=''):
    if type(left) is not type(right):
        return [path or '/']
    if isinstance(left, dict):
        return [p for k in sorted(set(left) | set(right)) for p in (
            differences(left[k], right[k], path+'/'+k) if k in left and k in right else [path+'/'+k])]
    if isinstance(left, list):
        if len(left) != len(right):
            return [path]
        return [p for i, (a, b) in enumerate(zip(left, right)) for p in differences(a, b, path+'/'+str(i))]
    return [] if left == right else [path]


def wire_usage(directory):
    rows = []
    for intent in sorted(directory.rglob('dispatch-*.intent.json')):
        http = intent.with_name(intent.name.replace('.intent.json', '.http.json'))
        raw = read(http) if http.exists() else {}
        try:
            body = json.loads(raw.get('raw_http_response', 'null'))
        except ValueError:
            body = None
        body = body if isinstance(body, dict) else {}
        rows.append({'intent_sha256': file_sha256(intent), 'http_sha256': file_sha256(http) if http.exists() else None,
            'http_status': raw.get('http_status'), 'done': body.get('done'),
            'done_reason': body.get('done_reason'), 'prompt_tokens': body.get('prompt_eval_count'),
            'output_tokens': body.get('eval_count'), 'elapsed_seconds': raw.get('elapsed_seconds')})
    return rows


def audit(root):
    plan = require_plan(root)
    rows = []
    for slot in plan['slots']:
        target = root/'sessions'/slot['id']
        row = {k: slot[k] for k in ('id', 'objective', 'history_index', 'condition', 'request_sha256')}
        row.update(status='not-dispatched', native_effect_verified=False, measured_loss=None)
        if (target/'intent.json').exists():
            row['status'] = 'dispatched'
            try:
                definition = replay(target)
                if definition and not definition.get('generation_failure'):
                    from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
                    from utopia.optimization.native_design_space import require_candidate_in_space
                    parent = SystemSpec.from_dict(slot['request']['parent_system'])
                    mixed = GeneratedMixedDesign(parent, definition, loss_spec=slot['request']['loss_spec'],
                        seed=slot['request']['rng_seed'], single_draw_blackbox=True)
                    draws = mixed.draw(1, version_sha256=digest(definition), proposal_start=0, based_on=None)
                    candidate = SystemSpec.from_dict(draws[0]['suggestion']['candidate'])
                    require_candidate_in_space(SystemSpec.from_dict(slot['request']['design_space_anchor']),
                                               candidate, slot['request']['design_space'])
                    row.update(status='static-valid-submission', candidate_sha256=candidate.fingerprint,
                        changed_paths=differences(parent.to_dict(), candidate.to_dict()),
                        connections_changed=parent.connections != candidate.connections,
                        schedules_changed=parent.schedules != candidate.schedules)
                else:
                    row.update(status='generation-failure', generation_failure=definition)
            except BaseException as error:
                row.update(status='replay-or-compilation-failure', error_type=type(error).__name__, error=str(error))
            row['wire'] = wire_usage(target)
        rows.append(row)
    return {'schema': SCHEMA+'.audit', 'plan_sha256': file_sha256(root/'plan.json'),
        'source_commit': plan['source_commit'],
        'terminal': checked(read(root/'terminal.json')) if (root/'terminal.json').exists() else None,
        'slots': rows, 'readiness_wire': wire_usage(root/'readiness'),
        'new_native_worlds': 0, 'new_candidate_losses': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'audit'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--historical-root', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.historical_root is None:
            parser.error('--historical-root required')
        prepare(args.output, args.historical_root)
    elif args.command == 'run':
        run(args.output)
    else:
        if args.report is None or args.report.exists():
            parser.error('fresh --report required')
        save(args.report, audit(args.output))


if __name__ == '__main__':
    main()
