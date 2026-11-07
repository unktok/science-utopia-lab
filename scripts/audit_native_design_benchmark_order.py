#!/usr/bin/env python3
"""Explicit order-only analysis backport over a clean frozen V2 checkout.

Run this file directly in a fresh approved Python interpreter. No simulator,
designer or generated mechanism is dispatched. The original auditor body and
guards execute unchanged, with only two equal-valued JSON reads restored to
their source-defined mapping order in a private function globals dictionary.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = ('scripts/audit_native_design_benchmark_order.py',
         'scripts/native_design_audit_order.py')
SCHEMA = 'scienceutopia.native-design-audit-order-adapter.v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def clean_pin(root, expected):
    if git(root, 'rev-parse', 'HEAD') != expected or git(root, 'status', '--porcelain'):
        raise ValueError('audit requires a clean exact source checkout')


def fresh_output(output, raw, source):
    if output.exists() or output.is_symlink():
        raise ValueError('audit output must be fresh; never overwrite evidence')
    target = output.resolve()
    if target.is_relative_to(raw.resolve()) or target.is_relative_to(source.resolve()):
        raise ValueError('audit output must be outside raw and frozen source roots')
    return target


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def isolated_runtime(source):
    for name, module in tuple(sys.modules.items()):
        if name == 'scripts' or name.startswith('scripts.') or name == 'utopia' or name.startswith('utopia.'):
            file = getattr(module, '__file__', None)
            if file is None or not Path(file).resolve().is_relative_to(source):
                raise ValueError('cross-checkout runtime import is not permitted: ' + name)


def require_closed(raw, source):
    try:
        start = json.loads((raw / 'writer.started.json').read_text())
        end = json.loads((raw / 'writer.ended.json').read_text())
    except FileNotFoundError as error:
        raise ValueError('full audit requires normal writer closure; do not audit a live study') from error
    if (start.get('source_commit') != source or start.get('action') != 'all'
            or start.get('status') != 'started' or type(end.get('exit_code')) is not int
            or end != {**start, 'status': 'exited', 'exit_code': 0, 'ended_utc': end.get('ended_utc')}
            or datetime.fromisoformat(end['ended_utc']) < datetime.fromisoformat(start['started_utc'])):
        raise ValueError('full audit requires the exact normal terminal writer record')


def fixed_inventory(raw, plan):
    paths = {raw / name for name in ('plan.json', 'selection.json', 'evaluation-plan.json',
                                    'evaluation-seed-usage.json')}
    paths.update(raw / 'references' / name / 'observation.json' for name in plan['reference_systems'])
    for run, bindings in plan['campaign_bindings'].items():
        for arm in bindings:
            directory = raw / 'search' / run / 'arms' / arm.replace(':', '--') / 'campaign'
            paths.update(p for p in directory.rglob('*') if p.is_file() or p.is_symlink())
    if any(p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(raw) for p in paths):
        raise ValueError('fixed replay input is missing, linked or outside raw root')
    return {str(p.relative_to(raw)): sha(p) for p in sorted(paths)}


def run(args):
    raw, source = args.run.resolve(), args.source_tree.resolve()
    if not re.fullmatch('[a-f0-9]{40}', args.expected_source):
        raise ValueError('exact experiment source SHA required')
    output = fresh_output(args.output, raw, source)
    # Never permit imports from the integration tree to contaminate the replay.
    if any(n == 'scripts' or n.startswith('scripts.') or n == 'utopia' or n.startswith('utopia.')
           for n in sys.modules):
        raise ValueError('run this script directly in a fresh Python interpreter, not with -m/import')
    clean_pin(source, args.expected_source)
    analysis_commit = git(ROOT, 'rev-parse', 'HEAD')
    clean_pin(ROOT, analysis_commit)
    analysis_files = {name: sha(ROOT / name) for name in FILES}
    for name, expected in analysis_files.items():
        blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', analysis_commit + ':' + name])
        if hashlib.sha256(blob).hexdigest() != expected:
            raise ValueError('analysis code differs from its committed source')
    if not args.check_order_only:
        require_closed(raw, args.expected_source)
    sys.dont_write_bytecode = True
    order = load_file('_native_design_order_backport', ROOT / FILES[1])
    original_path = source / 'scripts/analyze_native_design_benchmark.py'
    expected_blob = subprocess.check_output(['git', '-C', str(source), 'show',
        args.expected_source + ':scripts/analyze_native_design_benchmark.py'])
    if sha(original_path) != hashlib.sha256(expected_blob).hexdigest():
        raise ValueError('frozen audit entrypoint differs from the original source')
    sys.path.insert(0, str(source))
    original = load_file('_native_design_original_auditor', original_path)
    isolated_runtime(source)
    closure_args = dict(scripts=['scripts/run_native_design_benchmark.py',
        'scripts/analyze_native_design_benchmark.py'], resources=[original.spec.PROTOCOL,
        'research/objectives/losses/native-joint-v5-throughput.json',
        'research/objectives/losses/native-reviewed-production-efficiency-v13.json'])
    closure = original.source_proofs(source, args.expected_source, **closure_args)
    before = None if args.check_order_only else original._inventory(raw)
    saved_plan = original.read(raw / 'plan.json')
    fixed_before = fixed_inventory(raw, saved_plan)
    usage = original.read(raw / 'evaluation-seed-usage.json')
    if (usage.get('content_sha256') != order.digest({
            k: v for k, v in usage.items() if k != 'content_sha256'})
            or usage.get('valid') is not True or usage.get('seeds') != list(original.spec.EVALUATION_SEEDS)
            or usage.get('errors') or usage.get('prior_matching_runs')):
        raise ValueError('evaluation seed history check is absent, failed or unknown')
    plan = order.restore_plan(saved_plan, spec=original.spec, source=args.expected_source,
                              seed_usage_sha256=usage['content_sha256'])
    saved_selection = original.read(raw / 'selection.json')

    def readonly(base, unused_plan, run_name, arm):
        return original.replay_campaign(Path(base) / 'search' / run_name / 'arms' /
                                        arm.replace(':', '--') / 'campaign', 'blackbox')

    selection = order.restore_selection(raw, saved_selection, plan=plan,
                                        driver=original.driver, campaign_loader=readonly)
    jobs = original.driver.evaluation_jobs(plan, selection)
    expected_jobs = {'schema': original.spec.SCHEMA + '.evaluation-plan',
                     'selection_sha256': selection['content_sha256'], 'jobs': jobs}
    if not order.same_values(original.read(raw / 'evaluation-plan.json'), expected_jobs):
        raise ValueError('evaluation jobs differ from immutable selection/seed projection')
    provenance = {'schema': SCHEMA, 'analysis_source_commit': analysis_commit,
        'analysis_source_files': analysis_files, 'experiment_source_commit': args.expected_source,
        'frozen_auditor_sha256': sha(original_path),
        'replacement_dependency': 'read of exact plan.json and selection.json only, private globals copy',
        'plan_values_and_hash_preserved': True, 'selection_values_and_hash_preserved': True,
        'ordered_evaluation_jobs_exactly_reproduced': True,
        'fixed_input_sha256': fixed_before, 'source_guards_removed': False,
        'unmodified_frozen_CLI_claimed_to_pass': False,
        'new_model_calls': 0, 'new_generated_code_executions': 0}
    if args.check_order_only:
        result = {'schema': SCHEMA + '.component-check',
            'status': 'closed-search-order-check-not-full-study-audit',
            'physical_evaluation_jobs': len(jobs), 'source_proofs': closure,
            'analysis_adapter': provenance, 'full_original_source_audit_completed': False}
    else:
        reader = order.OrderedSourceReader(original.read, raw, saved_plan=saved_plan,
            ordered_plan=plan, saved_selection=saved_selection, ordered_selection=selection)
        corrected = order.with_ordered_reader(original.analyze, reader)
        result = corrected(raw, args.expected_source)
        if result.get('content_sha256') != order.digest({
                k: v for k, v in result.items() if k != 'content_sha256'}):
            raise ValueError('original audit returned an invalid content hash')
        result['analysis_adapter'] = provenance
    isolated_runtime(source)
    if fixed_inventory(raw, saved_plan) != fixed_before:
        raise ValueError('fixed raw evidence changed during analysis')
    if before is not None and original._inventory(raw) != before:
        raise ValueError('raw evidence changed during complete audit')
    if original.source_proofs(source, args.expected_source, **closure_args) != closure:
        raise ValueError('frozen replay source changed during analysis')
    clean_pin(source, args.expected_source)
    clean_pin(ROOT, analysis_commit)
    if analysis_files != {name: sha(ROOT / name) for name in FILES}:
        raise ValueError('analysis adapter code changed during audit')
    result['content_sha256'] = order.digest({k: v for k, v in result.items() if k != 'content_sha256'})
    # Exclusive creation makes a late collision fail, never overwrite evidence.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2)
        handle.write('\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--source-tree', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check-order-only', action='store_true',
                        help='explicit live-evaluation component check; never a full audit')
    result = run(parser.parse_args(argv))
    print(json.dumps({'schema': result['schema'], 'content_sha256': result['content_sha256']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
