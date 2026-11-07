#!/usr/bin/env python3
"""Read-only, exact-source audit of the finite two-slot warm-start pilot.

Historical rescoring is initialization, never a new native execution or a
physical cache alias. Existing auditors own all author/native evidence truth.
"""
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

from scripts.analyze_native_autonomous_search_v14 import (
    _inventory, audit_native_campaign, read, replay_campaign,
)
from scripts.analyze_native_staged_search_v15 import audit_authoring
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-warmstart-audit.v45'
PLAN_SCHEMA = 'scienceutopia.native-warmstart-pilot.v45'
ARMS = ('efficiency', 'throughput')


def source_proofs(source, *, protocol):
    """Bind all native Python and the actual driver/auditor/helper closure.

    No fixture bypass and no comparison against an older driver's allowlist.
    Walking source imports binds trusted helper code, not model-authored code.
    """
    if not isinstance(source, str) or not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('exact original warm-start source commit required')
    if not isinstance(protocol, str) or not re.fullmatch(
            r'research/protocols/campaigns/native-warmstart-v45-a[0-9]+\.md', protocol):
        raise ValueError('explicit prospective warm-start protocol required')
    names = {p for p in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source,
        '--', 'utopia'], cwd=ROOT, text=True).splitlines() if p.endswith('.py')}
    pending = ['scripts/run_native_warmstart_v45.py', 'scripts/analyze_native_warmstart_v45.py']
    while pending:
        name = pending.pop()
        if name in names:
            continue
        names.add(name)
        body = subprocess.check_output(['git', 'show', source + ':' + name], cwd=ROOT)
        for node in ast.walk(ast.parse(body)):
            dependencies = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            if isinstance(node, ast.ImportFrom) and node.module == 'scripts':
                dependencies = ['scripts.' + alias.name for alias in node.names]
            for module in dependencies:
                if module.startswith('scripts.'):
                    dependency = module.replace('.', '/') + '.py'
                    if dependency not in names:
                        pending.append(dependency)
    names.update({protocol,
        'research/objectives/losses/native-joint-v5-throughput.json',
        'research/objectives/losses/native-reviewed-production-efficiency-v13.json'})
    files = {}
    for name in sorted(names):
        expected = hashlib.sha256(subprocess.check_output(
            ['git', 'show', source + ':' + name], cwd=ROOT)).hexdigest()
        path = ROOT / name
        if path.is_symlink() or file_sha256(path) != expected:
            raise ValueError('warm-start replay-critical source differs: ' + name)
        files[name] = expected
    return {'status': 'verified-exact-warmstart-runtime-driver-helper-source-blobs', 'files': files}


def _plan_and_bank(root, expected_source):
    # Delayed imports permit the audit and bounded-profile/evidence modules to
    # be developed independently, but production dispatch requires all of them.
    from scripts.run_native_warmstart_v45 import build_plan, HISTORICAL_AUDIT, HISTORICAL_SOURCE
    from utopia.optimization.native_initial_evidence import build_initial_evidence, validate_initial_evidence
    from utopia.system.native_open_examples import open_native_system
    plan, bank = read(root / 'plan.json'), read(root / 'bank.json')
    if plan.get('schema') != PLAN_SCHEMA or plan.get('source_commit') != expected_source:
        raise ValueError('warm-start plan source/schema differs')
    source = source_proofs(expected_source, protocol=plan['protocol'])
    validate_initial_evidence(bank)
    if bank['content_sha256'] != plan.get('initial_evidence_sha256'):
        raise ValueError('warm-start initial bank identity differs')
    manifest = plan['historical_audit_manifest']
    donor = Path(manifest['path'])
    if not donor.is_absolute() or donor.is_symlink() or not donor.is_file():
        raise ValueError('warm-start original historical audit path is not an explicit immutable input')
    before = file_sha256(donor)
    if before != manifest['file_sha256']:
        raise ValueError('warm-start original historical audit file identity differs')
    reconstructed_bank = build_initial_evidence(read(donor), expected_audit_content_sha256=HISTORICAL_AUDIT,
        expected_source_commit=HISTORICAL_SOURCE)
    if file_sha256(donor) != before or reconstructed_bank != bank:
        raise ValueError('warm-start bank differs from its pinned original historical audit')
    if (plan['initial_system'] != open_native_system(plan['provider_binding']['image_id']).to_dict()
            or plan['runtime_seed_binding'].get('python_hash_seed_environment') != '42'):
        raise ValueError('warm-start original researcher world or hash seed differs')
    reconstructed = build_plan(source_commit=expected_source,
        provider_binding=plan['provider_binding'],
        designer_provider_binding=plan['designer_provider_binding'],
        runtime_seed_binding=plan['runtime_seed_binding'],
        initial_system=plan['initial_system'], bank=bank, historical_audit_manifest=manifest)
    if reconstructed != plan:
        raise ValueError('warm-start prospective plan differs from exact driver reconstruction')
    return plan, bank, source


def _summary(runs, bank, losses):
    from utopia.optimization.native_initial_evidence import objective_view
    initial = {name: objective_view(bank, losses[name])['selection'] for name in ARMS}
    result = {}
    for name in ARMS:
        rows = runs[name]['observations']
        values = [r['loss'] for r in rows if r['status'] == 'complete']
        baseline = initial[name]['loss']
        best = min(values) if values else None
        result[name] = {'historical_initial_selection': initial[name],
            'new_complete_losses': values, 'new_best_loss': best,
            'historical_best_updated': best is not None and baseline is not None and best < baseline,
            'observed_improvement_over_historical': baseline - best if best is not None and baseline is not None else None,
            'source_equivalence_established': False, 'same_source_counterfactual_comparison': False,
            'new_slot_statuses': [r['status'] for r in rows]}
    return result


def _writer_and_progress(root, plan, runs):
    started, ended = read(root / 'writer.started.json'), read(root / 'writer.ended.json')
    for record in (started, ended):
        if (record.get('schema') != PLAN_SCHEMA + '.writer'
                or record.get('source_commit') != plan['source_commit'] or record.get('action') != 'run'):
            raise ValueError('warm-start writer source/action differs')
    if (started.get('status') != 'started' or ended.get('status') != 'exited'
            or type(ended.get('exit_code')) is not int or ended['exit_code'] != 0
            or any(started.get(k) != ended.get(k) for k in ('pid', 'argv', 'started_utc', 'environment'))
            or datetime.fromisoformat(ended['ended_utc']) < datetime.fromisoformat(started['started_utc'])):
        raise ValueError('warm-start writer is not the matching successful terminal receipt')
    if started.get('environment', {}).get('PYTHONHASHSEED') != '42':
        raise ValueError('warm-start writer lacks the fixed Python hash seed')
    arms, counts = {}, {'complete': 0, 'technical-failure': 0, 'generation-failure': 0}
    for name, run in runs.items():
        status = run['observations'][0]['status']
        arms[name] = {'consumed_slots': 1, 'pending': False, 'status': status,
            'loss': run['observations'][0]['loss'] if status == 'complete' else None}
        counts[status] += 1
    expected = {'schema': PLAN_SCHEMA + '.progress', 'source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'arms': arms, 'counts': counts, 'terminal': True,
        'consumed_native_slots': 2,
        'status': 'complete' if counts['complete'] == 2 else 'budget-complete-with-failures'}
    expected['content_sha256'] = digest(expected)
    if read(root / 'progress.json') != expected:
        raise ValueError('warm-start progress hides or changes terminal attempts/losses/nulls')
    return {'started': started, 'ended': ended, 'progress': expected}


def _role_proofs(root, plan):
    from utopia.optimization.native_loaded_roles_v38 import replay_loaded_context
    from utopia.optimization.native_scientist_load_v38 import replay_load
    scientist, designer = plan['provider_binding'], plan['designer_provider_binding']
    loads, gates = [], []
    expected = [(root / 'role-load-designer-calibration.started.json', designer,
        'before-v45-calibration', 'designer'),
        (root / 'role-load-scientist-before-run.started.json', scientist,
        'before-v45-native-pilot', 'scientist')]
    gate_expected = [(root / 'loaded-designer-calibration.json', {'designer': designer}, 'before-v45-calibration'),
        (root / 'loaded-scientist-before-run.json', {'scientist': scientist}, 'before-v45-native-pilot')]
    for arm in ARMS:
        for cell in sorted((root / 'arms' / arm / 'worlds').glob('*')):
            if not cell.is_dir():
                raise ValueError('unexpected non-directory in native worlds')
            starts = sorted(cell.glob('role-load-*.started.json'))
            observations = sorted(cell.glob('loaded-role-context-*.json'))
            if (cell / 'system.json').exists() and (len(starts) != 1 or len(observations) != 1):
                raise ValueError('native world lacks its unique confirmed role/context load')
            expected += [(p, scientist, 'before-native-world:' + cell.name, 'scientist') for p in starts]
            gate_expected += [(p, {'scientist': scientist}, 'before-native-world:' + cell.name) for p in observations]
    for path, provider, purpose, role in expected:
        completed = path.with_name(path.name.replace('.started.json', '.json'))
        proof = replay_load(read(path), read(completed) if completed.is_file() else None,
            provider=provider, purpose=purpose, role=role)
        if not proof['empty_prompt_load_confirmed']:
            raise ValueError('warm-start explicit role load failed or is unknown')
        loads.append({'path': str(path.relative_to(root)), 'proof': proof})
    for path, expected_roles, purpose in gate_expected:
        if not replay_loaded_context(read(path), expected=expected_roles, purpose=purpose):
            raise ValueError('warm-start role/context metadata gate failed')
        gates.append({'path': str(path.relative_to(root)), 'sha256': file_sha256(path)})
    declared = {p.resolve() for p, *_ in expected}
    if {p.resolve() for p in root.rglob('role-load-*.started.json')} != declared:
        raise ValueError('unaccounted explicit role-load POST')
    return {'loads': loads, 'loaded_context_observations': gates,
        'explicit_empty_prompt_load_POSTs': len(loads), 'scientific_generation': False}


def _certificate_proof(root, plan, terminal):
    """Cold replay using captured backend binding, never recontact the endpoint.

    The session below supplies only the certificate's archived metadata identity
    to the existing replay function. It does not claim a current live backend
    observation. Actual control HTTP inputs/bodies remain independently checked.
    """
    from utopia.optimization.native_designer_preflight import require_certificate
    path = root / 'preflight' / 'certificate.json'
    certificate = read(path)
    binding = certificate['plan']['backend']
    if certificate['plan']['source_commit'] != plan['source_commit']:
        raise ValueError('warm-start calibration source differs')
    class ArchivedMetadata:
        def get(self, url, timeout):
            if url == 'http://127.0.0.1:11434/api/version':
                value = {'version': binding['ollama_version']}
            elif url == 'http://127.0.0.1:11434/api/tags':
                value = {'models': [{'name': binding['model'], 'digest': binding['model_digest']}]}
            else:
                raise AssertionError('read-only certificate replay attempted an undeclared resource')
            class Response:
                def raise_for_status(self):
                    return None
                def json(self):
                    return deepcopy(value)
            return Response()
    proof = require_certificate(path, plan['designer_provider_binding'], protocol='staged-v15',
        session=ArchivedMetadata(), scope=plan['readiness_scope'],
        conversation_profile=plan['conversation_profile'],
        now=datetime.fromisoformat(terminal['started']['started_utc']).timestamp())
    if proof['controls'] > plan['budget']['maximum_calibration_POSTs']:
        raise ValueError('warm-start calibration exceeded its declared finite budget')
    return {**proof, 'backend_metadata_reobserved': False,
        'backend_binding_scope': 'archived certificate only; no live metadata GET during audit',
        'new_model_calls_during_replay': 0}


def analyze(run, *, expected_source):
    root = Path(run).resolve()
    before = _inventory(root)
    try:
        return _analyze(root, expected_source=expected_source, inventory=before)
    finally:
        if _inventory(root) != before:
            raise ValueError('raw warm-start evidence changed during read-only audit')


def _analyze(root, *, expected_source, inventory):
    plan, bank, source = _plan_and_bank(root, expected_source)
    if not (root / 'writer.ended.json').is_file():
        raise ValueError('warm-start terminal audit requires ended writer receipt')
    if set(plan['campaign_bindings']) != set(ARMS) or set(plan['losses']) != set(ARMS):
        raise ValueError('exact two declared warm-start arms required')
    runs, physical_paths, journals = {}, set(), set()
    for name in ARMS:
        directory = root / 'arms' / name
        controller = replay_campaign(directory / 'campaign', 'blackbox')
        if (controller.binding != plan['campaign_bindings'][name]
                or controller.binding.get('initial_evidence') != bank):
            raise ValueError('warm-start campaign/source/loss/initial evidence binding differs')
        native = audit_native_campaign(directory, method='blackbox', world=plan['world_binding'],
            classification=plan['classification'], loss=plan['losses'][name],
            initial_system=plan['initial_system'], expected_budget=1,
            experiment=plan['experiment'], campaign_world=plan['campaign_bindings'][name]['world'])
        if not native['terminal'] or native['consumed_native_slots'] != 1:
            raise ValueError('warm-start must retain exactly one terminal attempt per arm')
        native['designer'] = audit_authoring(directory / 'authoring', native['records'],
            pending=native['pending'], provider=plan['designer_provider_binding'],
            designer=plan['designer'], classification=plan['classification'])
        if native['designer']['generations'] != 1 or native['designer']['dispatch_intents'] > 16:
            raise ValueError('warm-start authoring exceeds one finite 16-call generation')
        journals.update((directory / 'authoring' / ('generation-' + p['request_sha256'])).resolve()
            for p in native['designer']['proofs'])
        for item in native['physical_response_caches']:
            path = Path(item['path']).resolve()
            if path in physical_paths:
                raise ValueError('warm-start arms share a physical scientist response cache')
            physical_paths.add(path)
        runs[name] = native
    if {p.resolve() for p in root.rglob('responses.sqlite')} != physical_paths:
        raise ValueError('unaccounted physical scientist response cache')
    if {p.resolve() for p in root.rglob('generation-*') if p.is_dir()} != journals:
        raise ValueError('unaccounted authoring generation directory')
    counts = {key: sum(r[key] for r in runs.values()) for key in (
        'consumed_native_slots', 'technical_failures', 'physical_native_worlds',
        'physical_world_directory_count', 'physical_researcher_responses',
        'completed_researcher_responses', 'physical_wire_requests',
        'recorded_code_executions_including_partial', 'completed_researcher_model_call_seconds')}
    designer_counts = {key: sum(r['designer'][key] for r in runs.values()) for key in (
        'generations', 'dispatch_intents', 'completed_step_receipts', 'recorded_POST_attempts',
        'known_HTTP_responses', 'known_designer_responses', 'interrupted_response_unknown',
        'valid_finished_generations')}
    if counts['consumed_native_slots'] != 2 or designer_counts['dispatch_intents'] > 32:
        raise ValueError('warm-start finite total budget differs')
    terminal = _writer_and_progress(root, plan, runs)
    role_proofs = _role_proofs(root, plan)
    certificate = _certificate_proof(root, plan, terminal)
    report = {'schema': SCHEMA, 'source_commit': expected_source,
        'classification': plan['classification'],
        'status': 'budget-complete-with-failures' if counts['technical_failures'] else 'budget-complete',
        'budget_terminal': True, 'plan_sha256': plan['content_sha256'],
        'initial_evidence_sha256': bank['content_sha256'], 'historical_source_audit': bank['source_audit'],
        'runs': runs, **counts, 'designer_costs': designer_counts,
        'terminal_writer_and_progress': terminal, 'role_loading': role_proofs,
        'calibration_cold_replay': certificate,
        'comparisons': _summary(runs, bank, plan['losses']),
        'new_model_calls_during_audit': 0, 'new_code_executions_during_audit': 0,
        'claims': {'historical_initialization_is_not_new_improvement': True,
            'source_equivalence_established': False, 'held_out': False,
            'causal_institutional_benefit': False, 'designer_improvement_established': False,
            'method_superiority_established': False, 'physical_historical_cache_reuse': False},
        'audit': {'source_proofs': source, 'input_inventory': deepcopy(inventory),
            'input_file_count': len(inventory), 'input_inventory_sha256': digest(inventory),
            'exact_authoring_and_native_truth_reused': True,
            'raw_files_verified_unchanged': True}}
    report['content_sha256'] = digest(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()) or args.output.exists():
        parser.error('audit output must be a fresh path outside the raw run')
    report = analyze(args.run, expected_source=args.expected_source)
    write_json_atomic(args.output, report, sort_keys=True, allow_nan=False)
    print({key: report[key] for key in ('status', 'consumed_native_slots',
        'physical_native_worlds', 'physical_researcher_responses', 'content_sha256')})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
