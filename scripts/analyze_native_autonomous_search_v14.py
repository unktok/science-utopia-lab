#!/usr/bin/env python3
"""Read-only autonomous designer/native evidence audit; never runs a model/world."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_open_v7 import FIXTURE, _inventory, read, partial_physical_proof
from scripts.analyze_native_open_estimators_v11 import incumbent_path
from scripts.analyze_native_nested_search_v13 import design_change, executable_contracts, objective_specs
from scripts.analyze_native_objective_structure_v8 import cross_score_measurement
from scripts.native_activity_effect_audit_v12 import activity_effect_proof
from scripts.native_capability_effect_audit_v13 import capability_effect_proof
from scripts.native_nested_estimator_audit_v13 import conditional_update_proof
from scripts.native_physical_evidence_v13 import audit_native_run_v13
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, GeneratedMixedDesign
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic, decode_json

SCHEMA = 'scienceutopia.native-autonomous-search-audit.v14'
RAW_SCHEMA = 'scienceutopia.native-autonomous-search-pilot.v14'
ACTUAL = 'actual-native-qwen-autonomous-search-development-v14'
EXPERIMENT = {'protocol': 'native-autonomous-search-v14', 'role': 'development-engineering'}
FORBIDDEN_CLAIMS = ('held_out', 'causal_institutional_benefit', 'scientific_value',
    'designer_improvement_established', 'full_native_world_pathwise_autograd',
    'variance_reduction_established', 'method_superiority_established')


def source_proofs(expected_source, classification):
    """Compare actual v14 runtime and reused helpers, never a different driver."""
    if classification == FIXTURE:
        return {'status': 'scripted-fixture-no-actual-source-claim', 'files': {}}
    if len(expected_source) != 40 or any(c not in '0123456789abcdef' for c in expected_source):
        raise ValueError('exact actual source commit required')
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', expected_source,
        '--', 'utopia'], cwd=ROOT, text=True).splitlines()
    names = [name for name in names if name.endswith('.py')]
    names += ['scripts/run_native_autonomous_search_v14.py',
        'research/protocols/campaigns/native-autonomous-search-v14.md',
        'scripts/analyze_native_open_v7.py', 'scripts/analyze_native_society_v6.py',
        'scripts/audit_native_objective_v5.py', 'scripts/analyze_native_open_estimators_v11.py',
        'scripts/analyze_native_objective_structure_v8.py', 'scripts/analyze_native_nested_search_v13.py',
        'scripts/native_activity_effect_audit_v12.py', 'scripts/native_capability_effect_audit_v13.py',
        'scripts/native_nested_estimator_audit_v13.py', 'scripts/native_physical_evidence_v13.py',
        *['research/objectives/losses/'+identity+'.json' for identity in objective_specs()]]
    files = {}
    for name in names:
        original = subprocess.check_output(['git', 'show', f'{expected_source}:{name}'], cwd=ROOT)
        actual, local = hashlib.sha256(original).hexdigest(), file_sha256(ROOT/name)
        if actual != local:
            raise ValueError('replay-critical actual v14 source differs: '+name)
        files[name] = {'actual_source_sha256': actual, 'analysis_source_sha256': local}
    return {'status': 'verified-exact-replay-source-blobs', 'files': files,
        'scope': 'Actual v14 driver/runtime and reused physical helpers; no v13-driver equivalence claim.'}


class ReadOnlyAdaptive(NativeAdaptiveDesignCampaign):
    def _save(self):
        raise AssertionError('read-only audit attempted persistence')


class ReadOnlyNested(NativeNestedDesignCampaign):
    def _save(self):
        raise AssertionError('read-only audit attempted persistence')


def replay_campaign(directory, method):
    directory = Path(directory)
    filename = 'native-adaptive-state.json' if method == 'blackbox' else 'native-nested-state.json'
    if method not in ('blackbox', 'nested-lr') or not (directory/filename).is_file():
        raise ValueError('declared method needs its saved campaign state')
    state = read(directory/filename)
    b = state['binding']
    kwargs = dict(initial_system=SystemSpec.from_dict(b['initial_system']), loss_spec=b['loss_spec'],
        seeds=b['seeds'], world_binding=b['world'], seed=b['seed'], learning_rate=b['learning_rate'])
    if method == 'blackbox':
        if b['mode'] != 'blackbox' or 'expectation_estimator' in b:
            raise ValueError('v14 blackbox must use unchanged singleton blackbox controller')
        kwargs.update(strategies=b['strategies'], mode=b['mode'],
            strategy_learning_rate=b['strategy_learning_rate'], strategy_baseline=b['strategy_baseline'],
            exploration=b['exploration'])
    controller = (ReadOnlyAdaptive if method == 'blackbox' else ReadOnlyNested)(directory, **kwargs)
    if method == 'blackbox' and any(r['request']['count'] != 1 for r in
            state['records'] + ([state['pending']] if state['pending'] else [])):
        raise ValueError('blackbox generations must each consume one native slot')
    return controller


def audit_native_campaign(directory, *, method, world, classification, loss, initial_system,
        expected_budget, experiment=EXPERIMENT):
    """Reconstruct physical evidence below one autonomous runtime directory."""
    directory = Path(directory)
    controller = replay_campaign(directory/'campaign', method)
    binding, state = controller.binding, controller.state
    if (binding['world'] != world or binding['loss_spec'] != loss
            or binding['initial_system'] != initial_system or binding['seed'] != 42 or binding['seeds'] != [42]
            or binding['learning_rate'] != .1):
        raise ValueError('autonomous campaign world/loss/initial/seed binding differs')
    records, pending = state['records'], state['pending']
    declared, physical, observation_ids = {}, set(), set()
    rows, native, slots, failures, authored = [], [], 0, 0, []
    for record in records + ([pending] if pending else []):
        for draw in record['draws']:
            if draw.get('suggestion'):
                run_id = draw['suggestion']['suggestion_id']+'-s42'
                if run_id in declared:
                    raise ValueError('physical world shared by distinct native slots')
                declared[run_id] = SystemSpec.from_dict(draw['suggestion']['candidate'])
    for index, record in enumerate(records):
        request = record['request']
        count, parent = request['count'], request['parent_system']
        start = slots
        slots += count
        external = method == 'blackbox' or request['external_authoring']
        if external:
            base = None if record['generation_error'] else GeneratedMixedDesign(
                SystemSpec.from_dict(parent), record['definition'], loss_spec=loss,
                seed=request['rng_seed'], single_draw_blackbox=count == 1).base.to_dict()
            authored.append({'record_index': index, 'request_sha256': record['request_sha256'],
                'definition': deepcopy(record['definition']), 'definition_sha256': digest(record['definition']),
                'generation_error': record['generation_error'],
                'base_system': base, 'literal_change': design_change(parent, base) if base else None})
        attempted = [(None, None, None)] if record['generation_error'] else [
            (i,d,o) for i,(d,o) in enumerate(zip(record['draws'], record['observations']))]
        if not record['generation_error'] and (len(record['draws']) != count or len(record['observations']) != count):
            raise ValueError('committed stage does not retain every scheduled attempt')
        for draw_index, draw, observation in attempted:
            system = draw['suggestion']['candidate'] if draw and draw.get('suggestion') else None
            row = {'generation': request['generation'], 'stage': record.get('stage', 'blackbox-generation'),
                'record_index': index, 'draw_index': draw_index, 'slot': start+(draw_index or 0),
                'scheduled_native_slots': count if draw is None else 1,
                'request_sha256': record['request_sha256'], 'version_sha256': record['version_sha256'],
                'draw': deepcopy(draw), 'observation': deepcopy(observation), 'system': system,
                'observation_id': observation['observation_id'] if observation else None,
                'system_fingerprint': SystemSpec.from_dict(system).fingerprint if system else None,
                'contracts': executable_contracts(system) if system else None,
                'lineage': {'vs_parent': design_change(parent, system),
                    'vs_initial': design_change(initial_system, system)} if system else None,
                'generation_error': record['generation_error'], 'status': 'generation-failure' if draw is None else 'technical-failure',
                'loss': None, 'own_loss': None, 'cross_scores': {key:None for key in objective_specs()},
                'metrics': None, 'checkpoint_sha256': None, 'physical_proof': None}
            if observation:
                if observation['observation_id'] in observation_ids:
                    raise ValueError('native observation reused')
                observation_ids.add(observation['observation_id'])
            valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
            if valid:
                runs = observation['metadata'].get('runs', [])
                if len(runs) != 1 or runs[0]['run_id'] in physical or runs[0]['run_id'] not in declared:
                    raise ValueError('native complete draw needs a unique declared world')
                evidence = runs[0]
                proof = audit_native_run_v13(directory, draw, observation, evidence, world, classification,
                    expected_experiment=experiment, expected_loss=loss)
                cell = directory/'worlds'/evidence['run_id']
                proof['activity_effect_proof'] = activity_effect_proof(cell, declared[evidence['run_id']], evidence['checkpoint_path'])
                proof['capability_effect_proof'] = capability_effect_proof(cell, declared[evidence['run_id']], evidence['checkpoint_path'])
                measurement = proof['measurement']
                evaluations, cross = cross_score_measurement(measurement, objective_specs(), loss['id'], observation['loss'])
                if ([measurement] != observation['metadata']['measurements']
                        or evaluations[loss['id']] != observation['metadata']['loss_evaluation']
                        or proof['native_loss'] != observation['loss']):
                    raise ValueError('saved autonomous loss differs from native checkpoint')
                row.update(status='complete', loss=observation['loss'], own_loss=observation['loss'],
                    cross_scores=cross, metrics=measurement['metrics'], physical_proof=proof,
                    checkpoint_sha256=proof['checkpoint_sha256'], run_id=evidence['run_id'])
                physical.add(evidence['run_id'])
                native.append(proof)
            else:
                failures += row['scheduled_native_slots']
                if observation and observation.get('loss') is not None:
                    raise ValueError('failed native attempt converted to numerical loss')
            rows.append(row)
    terminal = pending is None and (len(records) == expected_budget if method == 'blackbox' else len(records) == 3)
    if slots > expected_budget:
        raise ValueError('native budget exceeded')
    dirs = {p.name for p in (directory/'worlds').iterdir() if p.is_dir()} if (directory/'worlds').exists() else set()
    if not dirs <= declared.keys() or not physical <= dirs:
        raise ValueError('undeclared or missing physical world')
    caches, partial = [], []
    for path in sorted((directory/'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
            outcomes = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': outcomes})
        if path.parent.parent.name not in physical:
            partial.append(partial_physical_proof(path.parent.parent, declared[path.parent.parent.name], world, classification))
    cache_ids = {Path(c['path']).parent.parent.name for c in caches}
    for run_id in sorted(dirs-physical-cache_ids):
        cell = directory/'worlds'/run_id
        if read(cell/'system.json') != declared[run_id].to_dict():
            raise ValueError('partial native world source differs')
        partial.append({'run_id': run_id, 'status': 'partial-before-response-journal', 'loss': None,
            'files': {str(p.relative_to(cell)):file_sha256(p) for p in sorted(cell.rglob('*')) if p.is_file()}})
    replies = sum(c['outcomes'].get('response',0) for c in caches)
    completed_replies = sum(p['response_proof']['researcher_responses'] for p in native)
    if terminal and not failures and (len(caches) != expected_budget or replies != completed_replies):
        raise ValueError('physical/logical scientist replies differ or were reused')
    return {'method': method, 'loss_spec': loss, 'binding': binding, 'records': records, 'pending': pending,
        'observations': rows, 'authored_definitions': authored, 'incumbents': incumbent_path(rows),
        'conditional_update_proof': conditional_update_proof(records) if method == 'nested-lr' else None,
        'terminal': terminal, 'consumed_native_slots': slots, 'technical_failures': failures,
        'physical_native_worlds': len(physical), 'physical_world_directory_count': len(dirs),
        'physical_response_caches': caches, 'physical_researcher_responses': replies,
        'completed_researcher_responses': completed_replies,
        'completed_wire_requests': sum(p['response_proof']['wire_requests'] for p in native),
        'completed_code_executions': sum(p['code_proof']['recorded_executions'] for p in native),
        'completed_researcher_model_call_seconds': sum(p['annual_checkpoints'][-1]['llm_call_stats'].get(
            'elapsed_seconds',0.) for p in native),
        'partial_physical_run_proofs': partial}


def _hashed_record(value, *, field='content_sha256'):
    if value.get(field) != digest({k:v for k,v in value.items() if k != field}):
        raise ValueError('durable record content hash differs')


def _inside(root, relative):
    path = (root/relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('declared evidence path escapes raw root')
    return path


def audit_designer(directory, records, settings, *, provider_binding=None, classification=FIXTURE):
    """Join exact requests and durable HTTP intent/completion/raw authoring files.

    Intent is an upper bound on dispatches, not an exactly-once network claim.
    A started attempt without completion remains an unknown response.
    """
    directory = Path(directory)
    expected = {r['request_sha256']:r for r in records
        if r.get('request',{}).get('external_authoring', True)}
    proofs, observed = [], set()
    started_total = known_total = valid_total = interrupted = 0
    posts = raw_assistant = 0
    measurements = {k:[] for k in ('model_call_seconds','transport_seconds','prompt_tokens','completion_tokens')}
    for cell in sorted(directory.glob('generation-*')):
        binding = read(cell/'request.json')
        _hashed_record(binding, field='binding_sha256')
        request_sha = binding['request_sha256']
        if (binding.get('schema') != 'scienceutopia.llm-vocabulary-request.v14'
                or request_sha != digest(binding['request'])
                or request_sha not in expected or request_sha in observed
                or binding['request'] != expected[request_sha]['request']
                or cell.name != 'generation-'+request_sha
                or binding['settings'] != settings
                or provider_binding is not None and binding['provider_binding'] != provider_binding):
            raise ValueError('designer exact request/provider/settings binding differs')
        observed.add(request_sha)
        result = read(cell/'response.json')
        _hashed_record(result)
        if (result.get('schema') != 'scienceutopia.llm-vocabulary-result.v14'
                or result['binding_sha256'] != binding['binding_sha256']
                or result['request_sha256'] != request_sha
                or result.get('source_execution_on_host') is not False
                or result['definition'] != expected[request_sha]['definition']):
            raise ValueError('designer result is not exact consumed unmodified definition')
        attempts, selected_definition = [], None
        errors = []
        starts = sorted(cell.glob('attempt-*.started.json'))
        completions = {p.name for p in cell.glob('attempt-*.completed.json')}
        if len(starts) > settings['max_attempts'] or not completions <= {
                p.name.replace('.started.json','.completed.json') for p in starts}:
            raise ValueError('designer HTTP attempt budget exceeded')
        for index, start_path in enumerate(starts):
            started_total += 1
            start = read(start_path)
            if (start_path.name != f'attempt-{index:02d}.started.json'
                    or start['attempt'] != index or start['binding_sha256'] != binding['binding_sha256']
                    or start.get('dispatch_intent') is not True
                    or not isinstance(start.get('prompt'),str) or start.get('prompt_sha256') != digest(start['prompt'])
                    or not isinstance(start.get('response_schema'),dict)):
                raise ValueError('designer started-attempt index or request binding differs')
            if classification == ACTUAL:
                from utopia.optimization.native_search_generator_v14 import build_prompt, OUTPUT_SCHEMA
                if (start['prompt'] != build_prompt(binding['request'],image_id=binding['image_id'],errors=errors)
                        or start['response_schema'] != OUTPUT_SCHEMA):
                    raise ValueError('designer exact objective/history/error prompt differs')
            completed_path = cell/f'attempt-{index:02d}.completed.json'
            if not completed_path.exists():
                interrupted += 1
                attempts.append({'attempt':index, 'started_sha256':file_sha256(start_path),
                    'completed_sha256':None, 'status':'interrupted-response-unknown'})
                errors.append({'type':'InterruptedDispatch','message':'started attempt has no completed receipt; consumes budget, not redispatched'})
                continue
            done = read(completed_path)
            _hashed_record(done)
            if (done.get('schema') != 'scienceutopia.llm-vocabulary-attempt.v14'
                    or done['binding_sha256'] != binding['binding_sha256'] or done['attempt'] != index
                    or done['started_file_sha256'] != file_sha256(start_path)):
                raise ValueError('designer completion detached from dispatch intent')
            if any(a['status'] == 'valid' for a in attempts):
                raise ValueError('designer made an extra attempt after a valid draft')
            reply = done['model_reply']
            output = reply.get('output') if reply else None
            if reply is not None:
                if not isinstance(reply.get('messages'), list):
                    raise ValueError('designer completion lacks raw messages list')
                transport = reply.get('transport',{})
                posts += int('request_payload' in transport)
                assistants = [m for m in reply['messages'] if m.get('role') == 'assistant']
                known_total += int(bool(assistants) or 'raw_http_response' in transport)
                raw_assistant += int(bool(assistants))
                if assistants:
                    content = assistants[-1].get('content')
                    raw = content if isinstance(content,str) else ''.join(
                        b['text'] for b in content if b.get('type') == 'text') if isinstance(content,list) else None
                    try:
                        parsed = decode_json(raw,strict=True,finite_floats=True)
                    except (ValueError,TypeError):
                        parsed = None
                    if output is not None and parsed != output:
                        raise ValueError('parsed designer output differs from strict original raw response')
                elif output is not None:
                    raise ValueError('parsed designer output lacks original assistant response')
                for key,value in (('model_call_seconds',done.get('model_call_seconds')),
                        ('transport_seconds',transport.get('elapsed_seconds')),
                        ('prompt_tokens',transport.get('prompt_tokens')),
                        ('completion_tokens',transport.get('completion_tokens'))):
                    if value is not None:
                        if type(value) not in (int,float) or not math.isfinite(value) or value < 0:
                            raise ValueError('designer recorded time/token cost is invalid')
                        measurements[key].append(value)
            if done['status'] == 'valid':
                from utopia.optimization.native_search_generator_v14 import compile_authored_output
                if output is None or done['errors']:
                    raise ValueError('valid designer response lacks original model output')
                reconstructed = compile_authored_output(binding['request'], output,
                    binding_sha256=binding['binding_sha256'], provider_binding=binding['provider_binding'])
                if done['definition'] != reconstructed:
                    raise ValueError('designer operations/source repaired after model reply')
                # The only semantic payload conversion is the explicit patch
                # envelope. Never normalize, fix or replace model operations.
                patch = reconstructed['base_patch']
                if ((patch['operations'] if patch else []) != output['operations']
                        or reconstructed['factors'] != output['factors']
                        or reconstructed['continuous'] != output['continuous']
                        or reconstructed.get('logits') != output.get('logits')):
                    raise ValueError('designer operations/factors/coordinates/logits changed')
                valid_total += 1
                if result['selected_attempt'] == index:
                    selected_definition = reconstructed
            elif (done['status'] not in ('invalid', 'transport-error') or done['definition'] is not None
                    or not done['errors']):
                raise ValueError('failed designer attempt contains repaired definition')
            attempts.append({'attempt':index,'started_sha256':file_sha256(start_path),
                'completed_sha256':file_sha256(completed_path),'status':done['status']})
            errors.extend(done['errors'])
        if result['attempts'] != attempts:
            raise ValueError('designer response hides or changes an attempted draft')
        if result['status'] == 'generated':
            if selected_definition != result['definition'] or attempts[-1]['status'] != 'valid':
                raise ValueError('designer successful selection differs from preserved attempt')
        elif (result['status'] != 'generation-failed' or result['selected_attempt'] is not None
                or not isinstance(result['definition'], dict) or 'generation_failure' not in result['definition']
                or any(a['status'] == 'valid' for a in attempts)):
            raise ValueError('failed designer result must remain malformed/null-slot sentinel')
        if classification == ACTUAL and result['status'] == 'generation-failed':
            from utopia.optimization.native_search_generator_v14 import build_prompt, MAX_PROMPT_BYTES
            if len(starts) < settings['max_attempts']:
                if len(build_prompt(binding['request'],image_id=binding['image_id'],errors=errors).encode()) <= MAX_PROMPT_BYTES:
                    raise ValueError('designer failed before exhausting allowed drafts without prompt limit')
                errors.append({'type':'PromptBudgetExceeded','message':'explicit author prompt exceeds byte budget; no truncation or model call'})
            expected_failure = {'generation_failure':{'schema':'scienceutopia.llm-vocabulary-result.v14',
                'request_sha256':request_sha,'reason':'bounded automatic authoring failed','technical_errors':errors}}
            if result['definition'] != expected_failure:
                raise ValueError('designer failure sentinel hides or changes technical errors')
        proofs.append({'request_sha256': request_sha, 'binding':binding, 'result':result,
            'attempts':attempts, 'attempt_records':[read(cell/f'attempt-{a["attempt"]:02d}.completed.json')
                if a['completed_sha256'] else None for a in attempts]})
    if set(expected) != observed:
        raise ValueError('consumed designer request missing durable authoring evidence')
    return {'generations':len(proofs), 'dispatch_intents':started_total, 'known_responses':known_total,
        'valid_drafts':valid_total, 'interrupted_response_unknown':interrupted, 'proofs':proofs,
        'recorded_post_payloads':posts,'raw_assistant_responses':raw_assistant,
        'cost_measurements':{key:{'recorded_sum':math.fsum(values),'record_count':len(values),
            'scope':'sum of present recorded values; missing values are not inferred zero'}
            for key,values in measurements.items()},
        'counting_scope':'Durable dispatch intents and known replies; a missing completion cannot prove whether HTTP ran.'}


def analyze(run, *, expected_source, require_complete=True):
    root = Path(run).resolve()
    before = _inventory(root)
    try:
        return _analyze(root, expected_source=expected_source, require_complete=require_complete, inventory=before)
    finally:
        if _inventory(root) != before:
            raise ValueError('raw evidence changed during read-only audit')


def _analyze(root, *, expected_source, require_complete, inventory):
    plan = read(root/'plan.json')
    classification = plan.get('classification')
    if (plan.get('schema') != RAW_SCHEMA or classification not in (ACTUAL,FIXTURE)
            or plan.get('source_commit') != expected_source or plan.get('experiment') != EXPERIMENT
            or plan.get('seed') != 42 or plan.get('population') != {'authors':5,'conference_setting':1}
            or plan.get('designer_budget') != {'generations':6,'max_attempts_per_generation':2,'max_http_attempts':12}
            or len(plan.get('runs',[])) != 3):
        raise ValueError('exact preregistered autonomous v14 source/budget/population plan required')
    world = plan['world']
    if (world.get('classification') != classification or world.get('source_commit') != expected_source
            or world.get('years') != 2 or world.get('corpus_years') != 4
            or world.get('experiment') != EXPERIMENT):
        raise ValueError('autonomous original-world binding differs')
    if classification == ACTUAL and (any(not isinstance(world.get(k),str) or len(world[k]) != 64
            or any(c not in '0123456789abcdef' for c in world[k]) for k in ('model_digest','corpus_sha256'))
            or world.get('runtime_seed_binding',{}).get('python_hash_seed_environment') != '42'):
        raise ValueError('actual autonomous model/corpus/runtime seed binding missing')
    sources = source_proofs(expected_source, classification)
    runs, contracts, request_hashes = {}, [], set()
    for entry in plan['runs']:
        identity, request = entry['id'], entry['request']
        if identity in runs or digest(request) in request_hashes:
            raise ValueError('duplicate autonomous run/request')
        request_hashes.add(digest(request))
        if (request.get('schema') != 'scienceutopia.native-search-request.v14'
                or request['initial_system'] != plan['initial_system']
                or request['seed'] != 42 or request['years'] != 2
                or request['designer'] != {'model':'qwen3:8b','max_attempts':2,'max_tokens':4096}
                or request['loss_spec'] != objective_specs().get(request['loss_spec']['id'])):
            raise ValueError('exact autonomous request/initial/loss/designer contract differs')
        contracts.append((request['loss_spec']['id'], request['method'], request['native_budget']))
        directory = _inside(root, entry['directory'])
        native = audit_native_campaign(directory, method=request['method'], world=world,
            classification=classification, loss=request['loss_spec'], initial_system=plan['initial_system'],
            expected_budget=request['native_budget'])
        saved = read(directory/'plan.json')
        if (saved.get('schema') != 'scienceutopia.native-search-plan.v14'
                or saved['request'] != request or saved['request_sha256'] != digest(request)
                or saved['source_commit'] != expected_source):
            raise ValueError('runtime frozen request/plan differs from aggregate preregistration')
        provider = saved.get('provider_binding')
        if classification == ACTUAL and (not isinstance(provider,dict) or provider.get('model') != 'qwen3:8b'
                or any(provider.get(k) != world.get(k) for k in ('model_digest','corpus_sha256','image_id'))):
            raise ValueError('designer provider differs from source-pinned researcher/corpus/image binding')
        native['designer'] = audit_designer(directory/'authoring', native['records'],
            {'max_attempts':2,'max_tokens':4096},provider_binding=provider,classification=classification)
        native.update(request=request, runtime_plan=saved)
        runs[identity] = native
    expected = [(list(objective_specs())[0],'blackbox',2),
        (list(objective_specs())[1],'blackbox',2),(list(objective_specs())[1],'nested-lr',4)]
    if contracts != expected:
        raise ValueError('v14 requires throughput BB2, efficiency BB2, efficiency nested4 in frozen order')
    terminal = all(r['terminal'] for r in runs.values())
    if require_complete and not terminal:
        raise ValueError('incomplete autonomous audit requires explicit flag')
    counts = {key:sum(r[key] for r in runs.values()) for key in ('consumed_native_slots',
        'physical_native_worlds','physical_world_directory_count','physical_researcher_responses',
        'completed_researcher_responses','completed_wire_requests','completed_code_executions','technical_failures',
        'completed_researcher_model_call_seconds')}
    designer = {key:sum(r['designer'][key] for r in runs.values()) for key in
        ('generations','dispatch_intents','known_responses','valid_drafts','interrupted_response_unknown')}
    designer_measurements = {key:{'recorded_sum':math.fsum(r['designer']['cost_measurements'][key]['recorded_sum']
            for r in runs.values()),'record_count':sum(r['designer']['cost_measurements'][key]['record_count']
            for r in runs.values())} for key in ('model_call_seconds','transport_seconds','prompt_tokens','completion_tokens')}
    if designer['generations'] > 6 or designer['dispatch_intents'] > 12:
        raise ValueError('aggregate designer generation/provider budget exceeded')
    result = {'schema':SCHEMA,'classification':classification,'source_commit':expected_source,
        'status':'complete' if terminal and not counts['technical_failures'] else
            'budget-complete-with-failures' if terminal else 'in-progress',
        'plan':plan,'run_order':list(runs),'runs':runs,'planned_native_world_budget':8,
        **counts,'designer_costs':designer,
        'designer_cost_measurements':designer_measurements,
        'designer_recorded_post_payloads':sum(r['designer']['recorded_post_payloads'] for r in runs.values()),
        'claims':{**{key:False for key in FORBIDDEN_CLAIMS},
            'live_fixed_Qwen_researchers':classification == ACTUAL and counts['physical_researcher_responses'] > 0,
            'scripted_researcher_HTTP':classification == FIXTURE,
            'provider_provenance':'local configured provider records; no cryptographic external identity attestation'},
        'held_out_metrics':{'status':'not-defined-or-measured'},
        'promotion_policy':{'status':'not-defined-or-applied'},
        'audit':{'raw_root':str(root),'raw_inventory_sha256':digest(inventory),
            'raw_input_sha256s':inventory,'raw_files_verified_unchanged':len(inventory),
            'new_model_calls':0,'new_container_executions':0,'campaign_and_lineage_replayed':True,
            'checkpoint_loss_reextracted':True,'all_failures_and_exact_ties_retained':True,
            'designer_requests_raw_replies_and_operations_joined':True,
            'scientist_and_designer_costs_separate':True,'replay_source_proofs':sources,
            'analysis_source_sha256':file_sha256(Path(__file__)),
            'limits':['Three development requests are not a controlled comparison of methods.',
                'Literal source/topology edits and physical execution do not establish useful invention.',
                'Cross-scores reuse original development checkpoints, not held-out outcomes.',
                'Unknown interrupted designer responses remain unknown; no exactly-once HTTP claim.']}}
    result['content_sha256'] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected-source',required=True)
    parser.add_argument('--allow-incomplete',action='store_true')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError('audit output must be outside immutable raw evidence')
    report = analyze(args.run,expected_source=args.expected_source,require_complete=not args.allow_incomplete)
    write_json_atomic(args.output,report,sort_keys=True,allow_nan=False)
    print(json.dumps({key:report[key] for key in ('status','physical_native_worlds',
        'physical_researcher_responses','designer_costs','content_sha256')},sort_keys=True))


if __name__ == '__main__':
    main()
