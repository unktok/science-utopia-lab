#!/usr/bin/env python3
"""Read-only exact-source replay and cross-objective analysis of the V1 pilot."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime
import hashlib
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_native_feedback_comparison as driver
from scripts.analyze_native_autonomous_search_v14 import (
    _inventory, audit_native_campaign, audit_native_run_v14, partial_physical_proof_v14,
    read, replay_campaign,
)
from scripts.analyze_native_staged_search_v15 import audit_authoring
from scripts.analyze_native_warmstart_v45 import _certificate_proof
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_loaded_roles_v38 import replay_loaded_context
from utopia.optimization.native_scientist_load_v38 import replay_load
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-feedback-comparison-audit.v1'


def source_proofs(source):
    if not isinstance(source, str) or not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('exact comparison source commit required')
    names = {p for p in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source,
        '--', 'utopia'], cwd=ROOT, text=True).splitlines() if p.endswith('.py')}
    pending = ['scripts/run_native_feedback_comparison.py', 'scripts/analyze_native_feedback_comparison.py']
    while pending:
        name = pending.pop()
        if name in names:
            continue
        names.add(name)
        body = subprocess.check_output(['git', 'show', source+':'+name], cwd=ROOT)
        for node in ast.walk(ast.parse(body)):
            dependencies = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            if isinstance(node, ast.ImportFrom) and node.module == 'scripts':
                dependencies = ['scripts.'+a.name for a in node.names]
            for module in dependencies:
                if module.startswith('scripts.'):
                    path = module.replace('.', '/')+'.py'
                    if path not in names:
                        pending.append(path)
    names.update({driver.PROTOCOL, *['research/objectives/losses/'+identity+'.json'
        for identity in driver.LOSSES.values()]})
    result = {}
    for name in sorted(names):
        expected = hashlib.sha256(subprocess.check_output(['git', 'show', source+':'+name], cwd=ROOT)).hexdigest()
        path = ROOT/name
        if path.is_symlink() or file_sha256(path) != expected:
            raise ValueError('comparison replay-critical source differs: '+name)
        result[name] = expected
    return {'status': 'verified-exact-runtime-driver-auditor-helper-blobs', 'files': result}


def best(rows, key):
    valid = [r for r in rows if r['status']=='complete' and r['cross_scores'][key] is not None]
    loss = min((r['cross_scores'][key] for r in valid), default=None)
    return {'loss': loss, 'all_tied_row_ids': [r['row_id'] for r in valid if r['cross_scores'][key]==loss]}


def summarize(plan, runs, baseline):
    rows, arms = [], {}
    for arm in plan['arm_order']:
        own = []
        for r in runs[arm]['observations']:
            row = {key: deepcopy(r[key]) for key in ('generation', 'status', 'loss',
                'system_fingerprint', 'checkpoint_sha256', 'metrics', 'lineage')}
            row.update(row_id=f'{arm}:g{r["generation"]}', arm=arm,
                cross_scores={name: r['cross_scores'].get(loss['id']) for name, loss in plan['losses'].items()})
            rows.append(row); own.append(row)
        objective = plan['assignments'][arm]['objective']
        arms[arm] = {**plan['assignments'][arm], 'rows': own,
            'best': best(own, objective), 'baseline_loss': baseline['cross_scores'][objective],
            'best_so_far': [best(own[:i+1], objective)['loss'] for i in range(len(own))],
            'designer_costs': {k: deepcopy(v) for k, v in runs[arm]['designer'].items() if k != 'proofs'},
            'native_costs': {key: runs[arm][key] for key in (
                'physical_native_worlds', 'physical_world_directory_count', 'physical_researcher_responses',
                'physical_wire_requests', 'recorded_code_executions_including_partial',
                'completed_researcher_model_call_seconds')}}
    pooled = [baseline['row'], *rows]
    result = {'schema': SCHEMA+'.summary', 'source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'arms': arms, 'candidate_rows': rows,
        'baseline': {k: deepcopy(v) for k, v in baseline.items() if k not in ('physical_proof',)},
        'pooled_loss_only_best': {name: best(pooled, name) for name in plan['losses']},
        'scope': 'One development seed, two generations/arm; descriptive observations, not method superiority or independent confirmation.',
        'new_model_calls_during_analysis': 0, 'new_code_executions_during_analysis': 0,
        'arm_label_is_selection_veto': False}
    result['content_sha256'] = digest(result)
    return result


def _baseline(root, plan):
    o = read(root/'baseline/observation.json')
    if o['candidate'] != plan['initial_system'] or o['suggestion_id'] != 'feedback-comparison-baseline':
        raise ValueError('shared baseline candidate/identity differs')
    c = replay_campaign(root/'arms'/driver.ARM_ORDER[0]/'campaign', 'blackbox')
    c._check_observation(o, {'suggestion': {'suggestion_id': o['suggestion_id'], 'candidate': o['candidate']}})
    complete = o['status']=='complete' and not o['metadata'].get('technical_failures')
    proof, caches = None, []
    if complete:
        evidence = o['metadata']['runs'][0]
        proof = audit_native_run_v14(root/'baseline', {'suggestion': {'candidate': o['candidate']}}, o,
            evidence, plan['world_binding'], plan['classification'],
            expected_experiment=plan['experiment'], expected_loss=plan['losses']['throughput'])
        measurements = [proof['measurement']]
        if measurements != o['metadata']['measurements']:
            raise ValueError('baseline measurement differs from native checkpoint')
    else:
        if o['loss'] is not None:
            raise ValueError('baseline failure has numeric loss')
        measurements = o['metadata']['measurements']
    for path in (root/'baseline/worlds').glob('*/replies/responses.sqlite'):
        caches.append(str(path.resolve()))
        if not complete:
            proof = partial_physical_proof_v14(path.parent.parent, SystemSpec.from_dict(o['candidate']),
                plan['world_binding'], plan['classification'])
    scores = {name: evaluate_loss(loss, measurements) for name, loss in plan['losses'].items()}
    if scores != read(root/'baseline/cross-scores.json'):
        raise ValueError('saved baseline cross-scores differ')
    cross = {name: score['loss'] if complete else None for name, score in scores.items()}
    return {'status': 'complete' if complete else 'technical-failure', 'cross_scores': cross,
        'physical_response_caches': caches, 'physical_proof': proof,
        'row': {'row_id': 'shared-baseline', 'status': 'complete' if complete else 'technical-failure',
            'cross_scores': cross, 'system_fingerprint': SystemSpec.from_dict(o['candidate']).fingerprint}}


def _terminal(root, plan, runs):
    started, ended = read(root/'writer.started.json'), read(root/'writer.ended.json')
    if (started.get('schema') != driver.SCHEMA+'.writer' or started.get('source_commit') != plan['source_commit']
            or started.get('action') != 'run' or started.get('status') != 'started'
            or ended.get('status') != 'exited' or type(ended.get('exit_code')) is not int or ended['exit_code'] != 0
            or any(started.get(k) != ended.get(k) for k in ('schema','source_commit','action','pid','argv','started_utc','environment'))
            or started['environment'].get('PYTHONHASHSEED') != '42'
            or datetime.fromisoformat(ended['ended_utc']) < datetime.fromisoformat(started['started_utc'])):
        raise ValueError('comparison terminal writer binding/status differs')
    arms = {arm: {'slots': [{key: r[key] for key in ('generation','status','loss')}
        for r in run['observations']], 'pending': False} for arm, run in runs.items()}
    complete = all(r['status']=='complete' for a in arms.values() for r in a['slots'])
    progress = {'schema': driver.SCHEMA+'.progress', 'source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'arms': arms, 'consumed_candidate_slots': 8,
        'terminal': True, 'status': 'complete' if complete else 'budget-complete-with-failures'}
    progress['content_sha256'] = digest(progress)
    if read(root/'progress.json') != progress:
        raise ValueError('comparison progress differs from every actual attempt')
    return {'started': started, 'ended': ended, 'progress': progress}


def _roles(root, plan):
    designer, scientist = plan['designer_provider_binding'], plan['provider_binding']
    expected = [(root/'load-designer-calibration.started.json', root/'loaded-designer-calibration.json',
        designer, 'designer', 'before-feedback-comparison-calibration')]
    for arm in driver.ARM_ORDER:
        for g in range(driver.GENERATIONS):
            expected.append((root/'arms'/arm/f'designer-load-{g}.started.json',
                root/'arms'/arm/f'designer-context-{g}.json', designer, 'designer',
                f'before-feedback-comparison:{arm}:g{g}'))
    for worldroot in [root/'baseline/worlds', *[root/'arms'/a/'worlds' for a in driver.ARM_ORDER]]:
        for cell in sorted(worldroot.glob('*')):
            starts = sorted(cell.glob('role-load-*.started.json'))
            contexts = sorted(cell.glob('loaded-role-context-*.json'))
            if len(starts) != 1 or len(contexts) != 1:
                raise ValueError('physical world does not have one declared load/context receipt')
            expected.append((starts[0], contexts[0], scientist, 'scientist', 'before-native-world:'+cell.name))
    loads = []
    for path, context, provider, role, purpose in expected:
        proof = replay_load(read(path), read(path.with_name(path.name.replace('.started.json','.json'))),
            provider=provider, purpose=purpose, role=role)
        if not proof['empty_prompt_load_confirmed'] or not replay_loaded_context(read(context),
                expected={role: provider}, purpose=purpose):
            raise ValueError('explicit comparison role load/context failed or unknown')
        loads.append({'path': str(path.relative_to(root)), 'proof': proof,
            'context_sha256': file_sha256(context)})
    actual = {p.resolve() for p in root.rglob('*load*.started.json')}
    if actual != {row[0].resolve() for row in expected}:
        raise ValueError('unaccounted explicit comparison model load')
    return loads


def analyze(root, *, expected_source):
    root = Path(root).resolve(); before = _inventory(root)
    try:
        plan = read(root/'plan.json')
        source = source_proofs(expected_source)
        if plan.get('source_commit') != expected_source or plan.get('schema') != driver.SCHEMA:
            raise ValueError('comparison plan source/schema differs')
        if (plan['initial_system'] != open_native_system(plan['provider_binding']['image_id']).to_dict()
                or plan != driver.build_plan(source_commit=expected_source, provider_binding=plan['provider_binding'],
                    designer_provider_binding=plan['designer_provider_binding'],
                    runtime_seed_binding=plan['runtime_seed_binding'], initial_system=plan['initial_system'])):
            raise ValueError('comparison plan differs from frozen driver reconstruction')
        runs, caches, journals = {}, set(), set()
        for arm in plan['arm_order']:
            c = replay_campaign(root/'arms'/arm/'campaign', 'blackbox')
            if c.binding != plan['campaign_bindings'][arm]:
                raise ValueError('comparison campaign binding differs')
            objective = plan['assignments'][arm]['objective']
            run = audit_native_campaign(root/'arms'/arm, method='blackbox', world=plan['world_binding'],
                classification=plan['classification'], loss=plan['losses'][objective],
                initial_system=plan['initial_system'], expected_budget=2, experiment=plan['experiment'])
            if not run['terminal'] or run['consumed_native_slots'] != 2:
                raise ValueError('comparison needs exactly two terminal slots per arm')
            run['designer'] = audit_authoring(root/'arms'/arm/'authoring', run['records'],
                provider=plan['designer_provider_binding'], designer=plan['designer'], classification=plan['classification'])
            if run['designer']['generations'] != 2 or run['designer']['dispatch_intents'] > 32:
                raise ValueError('comparison designer budget differs')
            journals.update((root/'arms'/arm/'authoring'/('generation-'+p['request_sha256'])).resolve()
                for p in run['designer']['proofs'])
            for cache in run['physical_response_caches']:
                path = Path(cache['path']).resolve()
                if path in caches:
                    raise ValueError('comparison reused a physical scientist cache')
                caches.add(path)
            runs[arm] = run
        baseline = _baseline(root, plan)
        for path in baseline['physical_response_caches']:
            if Path(path) in caches:
                raise ValueError('baseline reused a candidate response cache')
            caches.add(Path(path))
        if caches != {p.resolve() for p in root.rglob('responses.sqlite')}:
            raise ValueError('unaccounted comparison response cache')
        if journals != {p.resolve() for p in root.rglob('generation-*') if p.is_dir()}:
            raise ValueError('unaccounted comparison author generation')
        terminal = _terminal(root, plan, runs)
        roles = _roles(root, plan)
        certificate = _certificate_proof(root, plan, terminal)
        report = {'schema': SCHEMA, 'source_commit': expected_source,
            'classification': plan['classification'], 'plan_sha256': plan['content_sha256'],
            'runs': runs, 'baseline': baseline, 'summary': summarize(plan, runs, baseline),
            'terminal': terminal, 'explicit_loads': roles, 'calibration_cold_replay': certificate,
            'audit': {'source_proofs': source, 'input_inventory': before,
                'input_inventory_sha256': digest(before), 'raw_files_verified_unchanged': True},
            'new_model_calls_during_analysis': 0, 'new_code_executions_during_analysis': 0}
        report['content_sha256'] = digest(report)
        return report
    finally:
        if _inventory(root) != before:
            raise ValueError('raw comparison evidence changed during read-only audit')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary-output', type=Path)
    args = parser.parse_args(argv)
    outputs = [p.resolve() for p in (args.output, args.summary_output) if p is not None]
    if len(outputs) != len(set(outputs)) or any(p.exists() or p.is_relative_to(args.run.resolve()) for p in outputs):
        parser.error('outputs must be distinct fresh paths outside raw evidence')
    result = analyze(args.run, expected_source=args.expected_source)
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    if args.summary_output:
        write_json_atomic(args.summary_output, result['summary'], sort_keys=True, allow_nan=False)
    print({'schema': SCHEMA, 'content_sha256': result['content_sha256'],
        'pooled_loss_only_best': result['summary']['pooled_loss_only_best']})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
