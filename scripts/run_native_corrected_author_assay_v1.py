"""Finite corrected-author readiness/free-generation assay, not world optimization.

Historical native inputs/losses remain literal. Only the technical author
binding changes; the edited-shape case explicitly exposes an already measured
own program as parent, not a newly selected scientific winner.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_author_visibility_v1 import read_visibility
from utopia.optimization import native_workflow_staged_designer_v1 as authoring
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_bounded_author_context_v45 import context_contract
from utopia.optimization.native_designer_decoding_v24 import decoding_contracts
from utopia.optimization.native_designer_preflight import backend_binding, planned_cases, runtime_binding
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_open_workflow_submission_v1 import bound_systems
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-corrected-author-assay.v1'
PROTOCOL = 'research/protocols/campaigns/native-corrected-author-assay-v1.md'
CLOSED = 'research/results/native-priority-method-comparison-closed-v1.json'
QA = 'research/results/native-priority-corrected-public-native-qa-v1.json'
CASES = (
    ('parent-zero', 'history-0/content-utility', '05951423d05746fcdd7238679bcd601f7adc152f721d26d8b3d328456b7b012d'),
    ('parent-terminal', 'history-0/resource-aware-content', '55b69f7c95e2db62cede2978ea13465ccab605f86d9ddb576a47bb9f3eb7d29e'),
    ('after-feature-write', 'history-1/content-utility', 'c23f07a0f73314ece47d39a7d38814bcc410b237f45125ea178d0aba836399f7'),
)
EXTRA_VERIFIED_MODULES = ('scripts/reports/stage_native_component_fixtures_v1.py',
    'scripts/analyze_native_staged_search_v15.py', 'scripts/analyze_native_open_v7.py')


def read(path):
    return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def utc():
    return datetime.now(timezone.utc).isoformat()


def rebind_request(original, document, *, label, source, contract):
    """Explicit technical exposure, never overwrite a historical journal/loss."""
    request = clone(original); changed = []
    if label == 'after-feature-write':
        matches = [pair for pair in request['observations']
            if digest(pair['suggestion']['candidate']) == digest(document)
            and digest(pair['observation']['candidate']) == digest(document) and pair['observation']['status'] == 'complete']
        if len(matches) != 1: raise ValueError('one literal previously measured edited parent required')
        observation = matches[0]['observation']
        score = evaluate_loss(request['loss_spec'], observation['metadata']['measurements'])
        if score['status'] != 'complete' or score['loss'] != observation['loss']:
            raise ValueError('edited parent must retain its actual assigned historical loss')
        request['parent_system'] = clone(document)
        request['based_on_observation_id'] = observation['observation_id']
        changed += ['/parent_system', '/based_on_observation_id']
    elif label not in ('parent-zero', 'parent-terminal') or digest(request['parent_system']) != digest(document):
        raise ValueError('literal original zero/terminal request parent required')
    request['strategy_provenance']['post_edit_component_contract'] = clone(contract)
    request['strategy_provenance']['protocol'] = PROTOCOL
    request['binding_sha256'] = digest({'schema': SCHEMA + '.technical-request-binding',
        'source_commit': source, 'label': label, 'original_request_sha256': digest(original),
        'document_sha256': digest(document), 'component_contract': contract})
    changed += ['/strategy_provenance/post_edit_component_contract', '/strategy_provenance/protocol', '/binding_sha256']
    bound_systems(request)
    return {'label': label, 'request': request, 'original_request_sha256': digest(original),
        'request_sha256': digest(request), 'document_sha256': digest(document),
        'explicit_changed_paths': changed,
        'parent_exposure': 'Previously measured own edited program; technical shape choice, not greedy reselection'
            if label == 'after-feature-write' else 'Literal original parent',
        'planned_calibration_POSTs': len(planned_cases(request, 'staged-v15', BOUNDED_AUTHORING))}


def verified_runtime(source):
    """The tested production modules stay exact; the new orchestrator is separate."""
    proof = read(ROOT / QA)
    if pinned_revision(source) != proof['source_commit'] or proof['actual_exit_code'] != 0:
        raise ValueError('exact clean successfully tested corrected software source required')
    paths = ['utopia/' + p for p in runtime_binding()] + list(EXTRA_VERIFIED_MODULES)
    for path in paths:
        if (ROOT / path).read_bytes() != (source / path).read_bytes():
            raise ValueError('tested corrected production module changed: ' + path)
    return {'source_commit': proof['source_commit'], 'QA_content_sha256': proof['content_sha256'],
        'exact_production_module_files': len(paths), 'orchestrator_is_new': True,
        'real_model_certificate_reused': False}


def build_plan(origin, scientific, verified, *, backend):
    source = pinned_revision(ROOT); closed = read(ROOT / CLOSED); original = read(origin / 'plan.json')
    if (pinned_revision(scientific) != closed['source_commits']['scientific']
            or original['source_commit'] != closed['source_commits']['scientific']
            or original['content_sha256'] != closed['plan_content_sha256']
            or digest(_inventory(origin)) != closed['raw_inventory_sha256']
            or any(file_sha256(path) != sha for path, sha in closed['input_file_sha256'].items())):
        raise ValueError('literal normally closed original scientific inputs required')
    if backend.get('model') != original['designer']['model'] or backend.get('model_digest') != original['designer']['model_digest']:
        raise ValueError('approved existing local designer identity required')
    verified_proof = verified_runtime(verified)
    bank = authoring.require_bank(original['component_bank'], original['component_evidence'], original['initial_system'])
    contract = authoring.component_feedback(bank, original['designer'], source).contract
    cases = []; files = {}
    for label, history, identity in CASES:
        path = origin / 'search/free-code-graph' / history / 'authoring' / ('proposal-' + identity) / 'editor-session/authoring' / ('generation-' + identity) / 'request.json'
        binding = decode_json(path.read_text(), strict=True, finite_floats=True)
        request = binding['request']
        if digest(request) != identity or binding['request_sha256'] != identity:
            raise ValueError('exact original source-bound author request required')
        fixture = ROOT / 'tests/fixtures/native_author_context_boundary_v1' / (label + '.json')
        document = decode_json(fixture.read_text(), strict=True, finite_floats=True)
        cases.append(rebind_request(request, document, label=label, source=source, contract=contract))
        files[str(path)] = file_sha256(path); files[str(fixture)] = file_sha256(fixture)
    return {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT / PROTOCOL),
        'origin': str(origin), 'scientific_source': str(scientific), 'verified_source': str(verified),
        'original_closed_content_sha256': closed['content_sha256'], 'verified_software': verified_proof,
        'provider': original['designer'], 'backend': clone(backend), 'bank': bank,
        'author_settings': authoring.settings(), 'context_contract': context_contract(),
        'decoding': decoding_contracts('staged-v15', conversation_profile=BOUNDED_AUTHORING),
        'cases': cases, 'input_file_sha256': files,
        'budget': {'cases': 3, 'maximum_calibration_POSTs': 120, 'maximum_proposal_POSTs': 48,
            'maximum_designer_role_load_POSTs': 6, 'maximum_component_probes': 192,
            'session_wall_seconds': 1800, 'maximum_sessions': 6, 'maximum_native_worlds': 0,
            'maximum_scientist_POSTs': 0, 'maximum_content_critic_POSTs': 0,
            'replace_failed_case': False, 'network_retries': 0},
        'scientific_search': False, 'held_out_evaluation': False, 'publication_ready': False}


def require_plan(root):
    plan = read(root / 'plan.json')
    expected = build_plan(Path(plan['origin']), Path(plan['scientific_source']), Path(plan['verified_source']), backend=plan['backend'])
    if plan != {**expected, 'content_sha256': digest(expected)}:
        raise ValueError('assay source/input/budget plan changed; no dispatch')
    return plan


def prepare(args):
    root = args.output.resolve()
    if root.exists(): raise ValueError('fresh unused assay output required')
    origin, scientific, verified = [getattr(args, k).resolve() for k in ('origin_run', 'origin_source', 'verified_source')]
    if any(root.is_relative_to(p) for p in (origin, scientific, verified)):
        raise ValueError('assay output must not modify any original/tested evidence source')
    provider = read(origin / 'plan.json')['designer']
    with (origin / 'writer.lock').open('r') as handle:
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        plan = build_plan(origin, scientific, verified, backend=backend_binding(provider))
        root.mkdir(parents=True); save(root / 'plan.json', plan)


def generation_directory(root, request):
    identity = digest(request)
    return root / ('proposal-' + identity) / 'editor-session/authoring' / ('generation-' + identity)


def transport_projection(directory):
    """Original backend counts/envelopes only; missing remains unknown."""
    rows = []
    for path in sorted(directory.glob('step-*.completed.json')):
        value = decode_json(path.read_text(), strict=True, finite_floats=True)
        transport = (value.get('model_reply') or {}).get('transport') or {}
        body = transport.get('response_payload') or {}
        rows.append({'step': value['step'], 'receipt_status': value['status'],
            'prompt_tokens': transport.get('prompt_tokens'), 'completion_tokens': transport.get('completion_tokens'),
            'done': body.get('done'), 'done_reason': body.get('done_reason'),
            'active_context_observation': clone(transport.get('active_context_observation'))})
    return rows


def run(root):
    for key, value in {'PYTHONHASHSEED': '42', 'CUDA_VISIBLE_DEVICES': '', 'HF_HUB_OFFLINE': '1',
            'HF_DATASETS_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}.items():
        if os.environ.get(key) != value: raise ValueError('explicit local/offline assay environment required: ' + key)
    if any('FIXTURE' in key and key.startswith('SCIENCE_UTOPIA_') for key in os.environ):
        raise ValueError('test-only HTTP fixtures cannot enter actual assay dispatch')
    plan = require_plan(root)
    if backend_binding(plan['provider']) != plan['backend']: raise ValueError('local backend changed before dispatch')
    with ExitStack() as stack:
        for path, mode in [(root / 'writer.lock', 'a'), (Path(plan['origin']) / 'writer.lock', 'r')]:
            handle = stack.enter_context(path.open(mode)); fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists(): raise ValueError('assay consumed; no redispatch or failed-case refill')
        save(root / 'started.json', {'source_commit': plan['source_commit'], 'plan_content_sha256': plan['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc(), 'shared_host_process_snapshot': subprocess.check_output(
                ['ps', '-axo', 'pid,ppid,%cpu,%mem,etime,comm'], text=True), 'exclusive_hardware_claimed': False})
        stage = 'starting'; rows = []; status = 'stopped'
        try:
            for case in plan['cases']:
                require_plan(root); directory = root / case['label']; request = case['request']
                designer = authoring.StagedWorkflowDesigner(directory, provider=plan['provider'], backend=plan['backend'],
                    source_commit=plan['source_commit'], bank=plan['bank'], inference_lock=root / 'inference.lock')
                stage = case['label'] + ':calibration'; save(root / (case['label'] + '.started.json'), {'stage': stage, 'utc': utc()})
                print(json.dumps({'stage': stage}), flush=True)
                certificate = designer.calibrate(request)
                stage = case['label'] + ':free-generation'; print(json.dumps({'stage': stage}), flush=True)
                result = designer.execute(request, purpose='proposal', certificate=certificate)
                visibility = read_visibility(generation_directory(directory, request))
                row = {'label': case['label'], 'request_sha256': case['request_sha256'],
                    'certificate': str(certificate), 'certificate_file_sha256': file_sha256(certificate),
                    'public_proposal_result': result, 'visibility': visibility,
                    'free_submission_available': 'generation_failure' not in result['definition'],
                    'implementation_phase_calls': visibility['phase_counts'].get('implementation', 0),
                    'actual_calibration_records': len(read(certificate)['records']),
                    'actual_proposal_started_calls': visibility['started_calls'],
                    'generation_transport': transport_projection(generation_directory(directory, request)),
                    'new_native_worlds': 0, 'new_scientific_loss': None}
                save(root / (case['label'] + '.result.json'), row); rows.append(row)
                if visibility['any_phase_interpretation_mismatch_calls']:
                    raise ValueError('actual corrected free-session phase mismatch; retain and stop')
            require_plan(root); status = 'closed'
        except BaseException as error:
            save(root / 'failure.json', {'stage': stage, 'error_type': type(error).__name__, 'error': str(error),
                'no_retry': True, 'no_fallback': True, 'known_cases_completed': len(rows)})
            raise
        finally:
            save(root / 'terminal.json', {'schema': SCHEMA + '.terminal', 'status': status, 'stage': stage,
                'completed_cases': len(rows), 'ended_utc': utc(), 'new_native_worlds': 0,
                'corrected_free_invention_or_loss_gain_claimed': False, 'publication_ready': False})


def replay(root):
    """Recheck actual public calibration/proposal returns; no model/client/code."""
    plan = require_plan(root); terminal = read(root / 'terminal.json')
    if terminal['status'] != 'closed' or terminal['completed_cases'] != 3:
        raise ValueError('all three original known-terminal assay cases required; never refill')
    rows = []
    for case in plan['cases']:
        directory = root / case['label']; request = case['request']; identity = digest(request)
        row = read(root / (case['label'] + '.result.json'))
        for purpose in ('calibration', 'proposal'):
            actual = authoring.replay(directory / (purpose + '-' + identity), request=request,
                provider=plan['provider'], backend=plan['backend'], source_commit=plan['source_commit'],
                bank=plan['bank'], purpose=purpose)
            if purpose == 'proposal' and actual != row['public_proposal_result']:
                raise ValueError('actual public proposal return differs; no repair')
        authoring.cold_certificate(row['certificate'], request=request, provider=plan['provider'],
            backend=plan['backend'], contract=request['strategy_provenance']['post_edit_component_contract'])
        visibility = read_visibility(generation_directory(directory, request))
        if (visibility != row['visibility'] or file_sha256(row['certificate']) != row['certificate_file_sha256']
                or row['request_sha256'] != case['request_sha256']
                or transport_projection(generation_directory(directory, request)) != row['generation_transport']):
            raise ValueError('original author/certificate/visibility changed')
        rows.append({'label': case['label'], 'free_submission_available': row['free_submission_available'],
            'implementation_phase_calls': row['implementation_phase_calls'],
            'actual_calibration_records': row['actual_calibration_records'],
            'actual_proposal_started_calls': row['actual_proposal_started_calls']})
    return {'schema': SCHEMA + '.cold', 'source_commit': plan['source_commit'],
        'plan_content_sha256': plan['content_sha256'], 'cases': rows,
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0,
        'corrected_free_invention_or_loss_gain_claimed': False, 'publication_ready': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    for key in ('origin-run', 'origin-source', 'verified-source', 'output'): prep.add_argument('--' + key, type=Path, required=True)
    execution = sub.add_parser('run'); execution.add_argument('--run', type=Path, required=True)
    cold = sub.add_parser('replay'); cold.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args)
    elif args.command == 'run': run(args.run.resolve())
    else: print(json.dumps(replay(args.run.resolve()), sort_keys=True))


if __name__ == '__main__': main()
