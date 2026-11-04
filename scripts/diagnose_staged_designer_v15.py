"""Read-only historical forensics and bounded local-author input interventions.

This is a diagnostic harness, NOT a production author fix or native campaign.
Generated code is data only. No researcher, Docker, world or adoption is run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ACTUAL = '51d9cbbd49054cdb89c24ea5bc192ff9b63e9155'
VARIANTS = ('baseline', 'trusted_role', 'explicit_objective', 'observation_memory',
    'nonconsecutive_notice', 'json_grammar', 'thinking', 'temperature',
    'interface_control', 'combined')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()


def read(path):
    return json.loads(Path(path).read_text())


def fresh(path, value):
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def inventory(root):
    files = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('historical input may not be a symlink')
        if path.is_file():
            files[str(path.relative_to(root))] = sha(path.read_bytes())
    return files


def context(payload):
    text = payload['messages'][1]['content']
    marker = 'EXACT SESSION CONTEXT\n'
    offset = text.index(marker) + len(marker)
    value, end = json.JSONDecoder().raw_decode(text[offset:])
    return value, text[:offset], text[offset + end:]


def replace_context(payload, document):
    _, prefix, suffix = context(payload)
    payload['messages'][1]['content'] = prefix + canonical(document).decode() + suffix


def generations(raw):
    result = []
    for path in sorted((Path(raw) / 'queue').glob('*/authoring/*/request.json')):
        binding = read(path)
        steps = [read(p) for p in sorted(path.parent.glob('step-*.completed.json'))]
        result.append((path.parent, binding, steps))
    return result


def offline(raw):
    raw = Path(raw).resolve()
    compact = read(ROOT / 'research/results/native-staged-search-v15-a2.json')
    expected = compact['audit']['raw_input_sha256s']
    before = inventory(raw)
    if before != expected:
        raise ValueError('historical bytes differ from the independent published audit')
    rows, all_counts, repeats, prompt_tokens, completion_tokens = [], Counter(), [], [], []
    for directory, binding, steps in generations(raw):
        operations = []
        empty, warnings, duplicate_reads, recent_identical = 0, 0, 0, 0
        seen = set()
        roles, seeds, limits = set(), set(), set()
        for step in steps:
            reply = step['model_reply']; transport = reply['transport']; payload = transport['request_payload']
            data, _, _ = context(payload)
            action = reply['output']; tool = action['tool']; all_counts[tool] += 1
            controls = data['000_current_turn']
            warnings += controls['inspection_notice'] is not None
            recent_identical = max(recent_identical, controls['consecutive_same_successful_inspections_of_unchanged_draft'])
            prompt_tokens.append(transport['prompt_tokens']); completion_tokens.append(transport['completion_tokens'])
            seeds.add(payload['options']['seed']); limits.add(payload['options']['num_ctx'])
            roles.add(tuple(m['role'] for m in payload['messages']))
            if tool == 'inspect':
                receipt = step['transition']['result']; value = receipt.get('value')
                empty += value == {}
                identity = (receipt['path'], step['transition']['draft_before_sha256'], sha(canonical(value)))
                duplicate_reads += identity in seen
                seen.add(identity)
                operations.append({'tool': tool, 'mechanism': action.get('selector', {}).get('mechanism_id'),
                    'path': action['path'], 'resolved_path': receipt['path'], 'empty_object': value == {},
                    'warnings': controls['inspection_notice'], 'actual_repeat_count': controls[
                        'consecutive_same_successful_inspections_of_unchanged_draft']})
            else:
                operations.append({'tool': tool, 'rationale': action.get('rationale')})
        first = steps[0]['model_reply']['transport']['request_payload']
        data, _, _ = context(first)
        rows.append({'directory': str(directory), 'generation': binding['request']['generation'],
            'objective': binding['request']['loss_spec']['id'], 'action_sequence': operations,
            'empty_inspections': empty, 'nonconsecutive_duplicate_reads': duplicate_reads,
            'inspection_notices': warnings, 'maximum_consecutive_counter': recent_identical,
            'prior_history_rows': len(binding['request']['history']),
            'transport_options': first['options'], 'think': first['think'],
            'first_system_message': first['messages'][0]['content'],
            'optimization_instruction_in_system': 'minimize' in first['messages'][0]['content'].lower(),
            'optimization_instruction_in_user_json': 'minimize' in data['instructions'].lower(),
            'input_role_patterns': sorted([list(r) for r in roles]), 'distinct_seeds': len(seeds),
            'context_limits': sorted(limits), 'draft_index': data['draft_index']})
        repeats.append(duplicate_reads)
    if inventory(raw) != before:
        raise ValueError('historical bytes changed while reading')
    return {'schema': 'scienceutopia.staged-author-forensics.v15', 'historical_source': ACTUAL,
        'raw_root': str(raw), 'raw_files': len(before), 'raw_inventory_sha256': sha(canonical(before)),
        'independently_published_raw_inventory_matched': True, 'historical_bytes_unchanged': True,
        'action_counts': dict(all_counts), 'nonconsecutive_duplicate_reads': sum(repeats),
        'prompt_tokens_min_max': [min(prompt_tokens), max(prompt_tokens)],
        'completion_tokens_min_max': [min(completion_tokens), max(completion_tokens)],
        'generations': rows, 'new_model_calls': 0, 'native_trials': 0,
        'claims': {'loop_detector_blind_spot_proven_offline': True,
            'loop_origin_identified_by_offline_counts_alone': False,
            'eight_billion_parameter_limit_proven': False}}


def observed_reads(steps):
    result = []
    for step in steps:
        receipt = step.get('transition') or {}
        if receipt.get('tool') == 'inspect' and receipt.get('ok'):
            result.append({'step': step['step'], 'action': step['model_reply']['output'],
                'observed_result': receipt['result'], 'draft_sha256': receipt['draft_after_sha256']})
    return result


def intervene(payload, variant, steps):
    """A priori named interventions; an edit is never supplied except the labelled control."""
    if variant not in VARIANTS:
        raise ValueError('unknown diagnostic variant')
    result = deepcopy(payload)
    data, _, _ = context(result)
    if variant in ('trusted_role', 'combined'):
        result['messages'][0]['content'] += '\nTRUSTED AUTHORING PROTOCOL\n' + data.pop('instructions')
        result['messages'][0]['content'] += '\nTRUSTED EXECUTION CONTRACT\n' + data.pop('technical_ABI_and_distribution_contract')
        replace_context(result, data)
    if variant in ('explicit_objective', 'combined'):
        result['messages'][0]['content'] += (
            '\nYour task is to minimize the numeric exact_loss_spec supplied in session data, '
            'by designing the scientific SYSTEM. A successful inspection is not evidence that '
            'the current institution minimizes that loss. Choose actions for that optimization '
            'task. Retention remains legal; no edit or improvement is required.')
    if variant in ('observation_memory', 'combined'):
        result['messages'].append({'role': 'user', 'content':
            'Previously observed read results, as data only:\n' + canonical(observed_reads(steps)).decode()})
    if variant in ('nonconsecutive_notice', 'combined'):
        result['messages'].append({'role': 'user', 'content':
            'Progress notice: the prior reads listed below already returned at this unchanged '
            'draft. Revisiting them, including alternating addresses, provides no new value. '
            'This is a notice, not an action prohibition or mandatory-edit rule.\n'
            + canonical([{'action': r['action'], 'observed_result_sha256': sha(canonical(r['observed_result']))}
                for r in observed_reads(steps)]).decode()})
    if variant == 'json_grammar':
        result['format'] = 'json'
    if variant == 'thinking':
        result['think'] = True
    if variant == 'temperature':
        result['options']['temperature'] = 0.8
    if variant == 'interface_control':
        result['messages'][0]['content'] += (
            '\nINTERFACE CONTROL ONLY, NOT AN OPTIMIZATION TRIAL: for this one response, '
            'test the edit interface by adding /metadata/diagnostic_probe with literal value '
            '"control" using an edit action. This task is not institutional invention or '
            'scientific optimization. The edit will not be adopted or executed in a world.')
    return result


def prepare(raw, output):
    output.mkdir(parents=True, exist_ok=False)
    if git('status', '--porcelain=v1'):
        raise ValueError('diagnostic source must be clean and committed before planning')
    before = inventory(raw)
    report = offline(raw)
    fresh(output / 'historical-forensics.json', report)
    cases = []
    for directory, binding, steps in generations(raw):
        if binding['request']['generation'] != 1:
            continue
        original = steps[2]['model_reply']['transport']['request_payload']
        target = 'throughput' if binding['request']['loss_spec']['id'] == 'native-joint-v5-throughput' else 'efficiency'
        for variant in VARIANTS:
            case = {'id': target + '-' + variant, 'target': target, 'variant': variant,
                'historical_step_file': str(directory / 'step-02.completed.json'),
                'historical_step_sha256': sha((directory / 'step-02.completed.json').read_bytes()),
                'historical_generation_directory': str(directory), 'historical_context_steps': 2,
                'payload': intervene(original, variant, steps[:2])}
            case['payload_sha256'] = sha(canonical(case['payload']))
            cases.append(case)
    if len(cases) != 20:
        raise ValueError('expected two G1 contexts and ten prespecified variants')
    plan = {'schema': 'scienceutopia.staged-author-diagnosis-plan.v15', 'source_commit': git('rev-parse', 'HEAD'),
        'created_utc': now(), 'historical_source': ACTUAL, 'raw_root': str(raw),
        'raw_inventory_sha256': sha(canonical(before)), 'model_digest': read(Path(raw) / 'plan.json')['provider_binding']['model_digest'],
        'endpoint': 'http://127.0.0.1:11434/api/chat', 'max_single_step_POSTs': 20,
        'max_followup_POSTs': 10, 'max_total_POSTs': 30, 'max_output_tokens_per_POST': 2048,
        'request_timeout_seconds': 180, 'network_retries': 0,
        'followup': 'combined only, both G1 contexts, at most6 steps each including first recorded combined response',
        'historical_runtime_version_known': False, 'current_runtime_version_recorded_separately': True,
        'controls_are_not_institutional_discoveries': True, 'native_trials': 0,
        'generated_source_execution': False, 'production_code_changed': False,
        'cases': cases}
    plan['content_sha256'] = sha(canonical(plan))
    fresh(output / 'plan.json', plan)
    return {'output': str(output), 'cases': len(cases), 'maximum_generation_POSTs': 30,
        'source_commit': plan['source_commit'], 'plan_content_sha256': plan['content_sha256']}


def local_get(name):
    with urllib.request.urlopen('http://127.0.0.1:11434/api/' + name, timeout=10) as stream:
        return json.load(stream)


def dispatch(directory, case, model_digest):
    """Intent before POST. Never redispatch an uncertain/known attempt."""
    started, completed = directory / (case['id'] + '.started.json'), directory / (case['id'] + '.completed.json')
    if started.exists() or completed.exists():
        raise ValueError('diagnostic call already has an intent or reply; never overwrite/redispatch')
    fresh(started, {'started_utc': now(), 'case_id': case['id'], 'payload_sha256': case['payload_sha256'],
        'payload': case['payload'], 'model_digest': model_digest})
    begin = time.monotonic()
    record = {'case_id': case['id'], 'variant': case['variant'], 'target': case['target'],
        'payload_sha256': case['payload_sha256'], 'started_file_sha256': sha(started.read_bytes()),
        'new_model_calls': 1, 'native_trials': 0}
    try:
        request = urllib.request.Request('http://127.0.0.1:11434/api/chat',
            data=canonical(case['payload']), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=180) as stream:
            raw = stream.read(); record['http_status'] = stream.status
        record['raw_response'] = raw.decode()
        body = json.loads(raw); record['response'] = body
        record['status'] = 'reply-known'
        record['truncated'] = body.get('done') is not True or body.get('done_reason') == 'length'
        try:
            record['action'] = json.loads(body['message']['content'])
        except (ValueError, KeyError) as error:
            record['parse_error'] = str(error)
    except Exception as error:
        record.update(status='transport-failed-or-response-unknown', error=type(error).__name__ + ': ' + str(error))
    record.update(elapsed_seconds=time.monotonic() - begin, ended_utc=now())
    fresh(completed, record)
    return record


def run(output):
    plan = read(output / 'plan.json')
    if git('rev-parse', 'HEAD') != plan['source_commit'] or git('status', '--porcelain=v1'):
        raise ValueError('clean exact diagnostic source required')
    tagged = local_get('tags')
    actual = next(m['digest'] for m in tagged['models'] if m['name'] == 'qwen3:8b')
    if actual != plan['model_digest']:
        raise ValueError('historical/current Qwen digest differs')
    fresh(output / 'current-backend.json', {'created_utc': now(), 'version': local_get('version'),
        'model_digest': actual, 'historical_backend_version_not_archived': True})
    directory = output / 'calls'; directory.mkdir()
    for case in plan['cases']:
        if case['payload_sha256'] != sha(canonical(case['payload'])):
            raise ValueError('planned payload changed')
        result = dispatch(directory, case, actual)
        print(json.dumps({'id': case['id'], 'status': result['status'], 'action': result.get('action'),
            'seconds': result['elapsed_seconds'], 'truncated': result.get('truncated')}), flush=True)
    # Followups are deliberately a separate explicit command after single-step
    # analysis. They must use the same plan and consume the remaining budget.
    return {'known_or_charged_POSTs': len(plan['cases']), 'followups_not_automatically_dispatched': True}


def summarize(output):
    plan = read(output / 'plan.json')
    cases = {c['id']: c for c in plan['cases']}
    rows = []
    for path in sorted((output / 'calls').glob('*.completed.json')):
        value = read(path); case = cases.get(value['case_id'])
        if case is None:
            continue
        body = value.get('response', {}); action = value.get('action')
        rows.append({'id': value['case_id'], 'variant': value['variant'], 'target': value['target'],
            'status': value['status'], 'truncated': value.get('truncated'), 'action': action,
            'elapsed_seconds': value['elapsed_seconds'], 'prompt_tokens': body.get('prompt_eval_count'),
            'output_tokens': body.get('eval_count'), 'thinking_characters': len(body.get('message', {}).get('thinking', '')),
            'completion_file_sha256': sha(path.read_bytes()), 'payload_sha256': value['payload_sha256']})
    return {'schema': 'scienceutopia.staged-author-diagnosis-summary.v15',
        'plan_sha256': sha((output / 'plan.json').read_bytes()), 'source_commit': plan['source_commit'],
        'single_step_rows': rows, 'single_step_POSTs': len(list((output / 'calls').glob('*.started.json'))),
        'native_trials': 0, 'generated_source_executed': False,
        'historical_raw_inventory_unchanged': sha(canonical(inventory(Path(plan['raw_root'])))) == plan['raw_inventory_sha256'],
        'limits': ['Single-step action differences do not prove successful sustained institutional invention.',
            'Backend version was not archived historically; contemporary paired interventions share current backend.',
            'The combined intervention is a bundle, not attribution to one individual factor.',
            'Interface-control edits are instructed syntax checks, not inventions or optimization outcomes.']}


def followup(output, historical_root):
    """At most5 additional tool calls per arm; literal/static transitions only."""
    plan = read(output / 'plan.json')
    if git('rev-parse', 'HEAD') != plan['source_commit'] or git('status', '--porcelain=v1'):
        raise ValueError('exact clean diagnostic source required')
    if git('rev-parse', 'HEAD', root=historical_root) != ACTUAL or git('status', '--porcelain=v1', root=historical_root):
        raise ValueError('clean exact historical interpreter source required')
    sys.path.insert(0, str(historical_root))
    from utopia.optimization import native_staged_author_v15 as historical
    if not Path(historical.__file__).resolve().is_relative_to(historical_root):
        raise ValueError('historical interpreter import resolved to another source')
    actual = next(m['digest'] for m in local_get('tags')['models'] if m['name'] == 'qwen3:8b')
    if actual != plan['model_digest']:
        raise ValueError('pinned model differs')
    directory = output / 'followups'; directory.mkdir()
    records = []
    for original in [c for c in plan['cases'] if c['variant'] == 'combined']:
        generation = Path(original['historical_generation_directory'])
        binding = read(generation / 'request.json'); request = binding['request']
        state = historical.initial_draft(request)
        steps = [read(generation / f'step-{i:02d}.completed.json') for i in range(2)]
        first = read(output / 'calls' / (original['id'] + '.completed.json'))
        response = first
        for number in range(6):
            if number:
                prompt = historical.build_prompt(request, state, steps, image_id=binding['image_id'],
                    binding_sha256=binding['binding_sha256'], settings=binding['settings'])
                base = deepcopy(original['payload'])
                # Start again from the original unmodified SYSTEM protocol,
                # then apply exactly the same combined treatment to new data.
                historical_payload = read(Path(original['historical_step_file']))['model_reply']['transport']['request_payload']
                base['messages'] = historical.build_conversation(prompt, historical_payload['messages'][0]['content'].split('\nThis is a continuing tool session.')[0])
                case = {'id': original['target'] + f'-combined-followup-{number}',
                    'target': original['target'], 'variant': 'combined',
                    'payload': intervene(base, 'combined', steps)}
                case['payload_sha256'] = sha(canonical(case['payload']))
                response = dispatch(directory, case, actual)
                print(json.dumps({'id': case['id'], 'status': response['status'],
                    'action': response.get('action'), 'seconds': response['elapsed_seconds']}), flush=True)
            action = response.get('action')
            if response['status'] != 'reply-known' or response.get('truncated') or not isinstance(action, dict):
                records.append({'target': original['target'], 'step': number, 'stopped': 'unknown, truncated or invalid reply'})
                break
            # Even trusted compiler diagnostics may not spawn a process or
            # access a socket in this harness. Literal generated source is
            # parsed/validated as data, never imported, exec'ed or sandbox-run.
            with patch('subprocess.Popen', side_effect=AssertionError('diagnosis forbids process execution')), \
                 patch('socket.socket', side_effect=AssertionError('diagnosis forbids tool network calls')):
                state, receipt = historical.transition(state, action, request,
                    binding_sha256=binding['binding_sha256'], provider_binding=binding['provider_binding'])
            step = {'step': len(steps), 'status': 'applied' if receipt['ok'] else 'rejected',
                'transition': receipt, 'model_reply': {'output': action}, 'errors': []}
            steps.append(step)
            entry = {'target': original['target'], 'step': number, 'action': action, 'receipt': receipt,
                'applied_operations': len(state['operations']), 'state': state,
                'native_trials': 0, 'generated_source_executed': False}
            fresh(directory / (original['target'] + f'-step-{number}.state.json'), entry)
            records.append({k: entry[k] for k in ('target', 'step', 'action', 'applied_operations', 'native_trials')})
            if receipt.get('definition') is not None:
                break
    started = len(list((output / 'calls').glob('*.started.json'))) + len(list(directory.glob('*.started.json')))
    if started > plan['max_total_POSTs']:
        raise ValueError('diagnostic budget exceeded')
    result = {'schema': 'scienceutopia.staged-author-diagnosis-followups.v15',
        'historical_interpreter_commit': ACTUAL, 'steps': records, 'total_generation_POSTs': started,
        'native_trials': 0, 'source_execution': False,
        'limits': 'Two bundled-treatment tool continuations only; no world loss, no demonstrated scientific improvement.'}
    fresh(directory / 'summary.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['offline', 'prepare', 'run', 'summarize', 'followup'])
    parser.add_argument('--raw', type=Path)
    parser.add_argument('--historical-root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'offline':
        result = offline(args.raw); fresh(args.output, result)
        print(json.dumps({'output': str(args.output), 'raw_files': result['raw_files'], 'actions': result['action_counts']}))
    elif args.mode == 'prepare':
        print(json.dumps(prepare(args.raw.resolve(), args.output.resolve())))
    elif args.mode == 'run':
        print(json.dumps(run(args.output.resolve())))
    elif args.mode == 'followup':
        print(json.dumps(followup(args.output.resolve(), args.historical_root.resolve())))
    else:
        result = summarize(args.output.resolve()); fresh(args.output / 'single-step-summary.json', result)
        print(json.dumps({'rows': len(result['single_step_rows']), 'historical_unchanged': result['historical_raw_inventory_unchanged']}))


if __name__ == '__main__':
    main()
