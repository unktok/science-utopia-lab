#!/usr/bin/env python3
"""One original native society: observe, externally author, confirm, adopt, repeat.

No external provider API is called. Missing authored patches and confirmations
stop at saved boundaries without inventing a loss or resetting the society.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox
from utopia.runtime.checkpointing import PortableStop
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json, file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-society-pilot.v6'
INTERPRETATION = 'online-same-society-sequential-losses-not-causal-benefit'
MANIFEST_KEYS = {'patch', 'state_actions', 'discard_deliveries'}


class SocietyPilotWaiting(PortableStop):
    """An expected boundary wait, distinct from technical/native failures."""


class SocietyPatchInbox(ManifestInbox):
    """The existing hash/raw-byte-bound inbox, with strict JSON decoding."""
    @staticmethod
    def _read(path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_097_152:
            raise ValueError('society authoring file must be bounded regular JSON')
        value = decode_json(path.read_text(), strict=True, finite_floats=True)
        digest(value)
        return value


class ExternalSocietyProposer:
    """Interchangeable callable(parent, feedback, index, loss) -> exact design.

    Complete patch/source/protocol/wires and migration state choices are authored
    externally; no institution algorithm or missing edge is supplied by the host.
    """
    def __init__(self, directory, *, world_binding, domain_provider, runtime_image_id):
        self.inbox = SocietyPatchInbox(directory)
        self.world_binding = clone(world_binding)
        self.domain_provider = domain_provider
        self.image_id = runtime_image_id

    def __call__(self, parent, feedback, index, loss):
        request = {'parent_system': parent.to_dict(), 'feedback': clone(feedback),
            'proposal_index': index, 'loss_spec': clone(loss), 'world_binding': self.world_binding,
            'actual_domain': clone(self.domain_provider()), 'runtime_image_id': self.image_id,
            'interpretation': INTERPRETATION,
            'activity_contract': (ROOT / 'research/components/native-activity-contracts-v6.md').read_text()}
        manifest, _ = self.inbox.generate(
            system='External authorship of an original native society, not Qwen researcher training.',
            prompt='Author a COMPLETE SystemSpec design patch from the exact observed society and loss. '
                'Return manifest {patch,state_actions,discard_deliveries}; all three fields are required. '
                'The host supplies no missing wires or policy/source repairs. Python is unrestricted '
                'inside the pinned networkless container and must define def step(context). '
                "Runtime input ABI is context['inputs'][your_port][0]['payload'] (a list of envelopes). "
                'The research activity contract is native-research-plan-v1; amendments must have '
                'schema native-research-amendment-v1, target_year, full assignment and submit bool. '
                'See the complete native-activity-contracts-v6 contract for timeline/identity fields. '
                'Use actual author IDs and actual next delivery year; never invent researcher IDs. '
                'Outputs are lists of {payload: object}; step returns {outputs: {...}, state: {...}}. '
                'Explicitly preserve/reset/replace changed mechanism state and explicitly account '
                'for pending-message changes. Freely author nodes/protocols/wires/algorithms; do not '
                'change founding seed or system_id. Optimize only the supplied loss. '
                'No improvement claim follows from nonstationary sequential losses. '
                'External authoring metadata must include kind and a nonempty identity.',
            seed_ctx=['native_society_design_v6', index, digest(self.world_binding)],
            output_schema={'type': 'object', 'required': sorted(MANIFEST_KEYS), 'additionalProperties': False,
                'properties': {key: {'type': 'object'} for key in MANIFEST_KEYS}},
            settings={'technical_drafts_per_boundary': 1, 'provider_API_calls': 0},
            authoring_input=request)
        if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS or any(
                not isinstance(manifest[key], dict) for key in MANIFEST_KEYS):
            raise ValueError('external society manifest requires exact patch/state_actions/discard_deliveries objects')
        from utopia.system.design_patch import apply_design_patch
        candidate = apply_design_patch(parent, manifest['patch'])
        if any(n.parameters.get('runtime_image_id') != self.image_id for n in candidate.mechanisms
                if n.implementation == 'code.python.v1'):
            raise ValueError('external society source must use the preregistered pinned runtime image')
        # Recover the exact request receipt, not a guessed latest response.
        expected = [p for p in (self.inbox.directory / 'consumed').glob('*.json')
            if self.inbox._verify_request(p.stem)['request'].get('authoring_input') == request]
        if len(expected) != 1:
            raise ValueError('exact society authoring input has no unique consumed response')
        receipt = self.inbox._read(expected[0])
        authoring = receipt['authoring']
        if not isinstance(authoring.get('identity'), str) or not authoring['identity'].strip():
            raise ValueError('external society authoring requires explicit self-reported identity')
        return {**clone(manifest), 'authoring': {**authoring,
            'external_request_sha256': receipt['request_sha256'],
            'external_response_sha256': receipt['response_sha256'],
            'external_manifest_sha256': receipt['manifest_sha256'],
            'proposer_input_sha256': digest(request)}}


def progress(session, *, status, **extra):
    view = session.projection()
    return {'schema': SCHEMA, 'status': status,
        'loss_path': [o['loss'] for o in view['observations']],
        'through_year': view['observations'][-1]['through_year'] if view['observations'] else 0,
        'adoptions': len(view['adoptions']), 'pending': view['pending'],
        'interpretation': INTERPRETATION, 'causal_benefit_established': False,
        'population_reset': False, **extra}


def write_society_server_config(output, session, *, checkpoint_directory):
    """Freeze operator-owned paths/bindings for serve_native_lab --society-config.

    Neither author responses nor HTTP requests get to select server filesystem
    roots. Use the actual Simulation output path, not a guessed layout.
    """
    value = {'directory': str(session.directory.resolve()),
        'founding_system': session.founding.to_dict(), 'loss_spec': clone(session.loss_spec),
        'world_binding': clone(session.binding['world']),
        'checkpoint_directory': str(Path(checkpoint_directory).resolve())}
    path = Path(output) / 'society-session-config.json'
    if path.exists():
        if SocietyPatchInbox._read(path) != value:
            raise ValueError('operator-owned society server config changed')
    else:
        write_json_atomic(path, value, sort_keys=True, allow_nan=False)
    return path


def run_society_pilot(simulation, session, proposer, *, output, confirm_request_sha256=(), horizon=3):
    """Generic callable proposer/loss route; the CLI pins the small live protocol.

    One caller owns the output/session/society. A confirmation names the staged
    request hash, NOT the external inbox request hash. No extra source draft is
    silently made on technical failure.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    confirmed = set(confirm_request_sha256)
    if type(horizon) is not int or horizon < 3 or simulation.num_years != horizon:
        raise ValueError('a society pilot needs its explicitly configured horizon, at least three years')
    if (output / 'completion.json').exists():
        result = SocietyPatchInbox._read(output / 'completion.json')
        if (result != progress(session, status='complete') or result['through_year'] != horizon
                or result['adoptions'] != horizon - 1 or result['pending'] is not None):
            raise ValueError('terminal society receipt differs from its complete session')
        audit_society_pilot(session)
        return result
    previous_callback = simulation.checkpoint_callback

    def save(status, **extra):
        result = progress(session, status=status, **extra)
        write_json_atomic(output / 'progress.json', result, sort_keys=True, allow_nan=False)
        return result

    def boundary(path):
        if previous_callback is not None:
            previous_callback(path)
        year = simulation.native_system.last_year
        if year < 1:
            return
        session.observe(simulation)
        view = session.projection()
        if year == horizon:
            if len(view['adoptions']) != horizon - 1 or view['pending'] is not None:
                raise ValueError('final society boundary lacks the declared prior yearly adoptions')
            save('complete')
            return
        # A resumed already-adopted boundary must advance its SAME society,
        # rather than author a duplicate proposal against the pre-adoption view.
        if any(a['after_year'] == year for a in view['adoptions']):
            save('continuing-adopted-society')
            return
        request = view['pending']
        if request is None:
            parent = simulation.native_system.spec
            feedback = {k: view[k] for k in ('observations', 'requests', 'adoptions', 'journal_sha256')}
            try:
                proposal = proposer(parent, clone(feedback), len(view['requests']), clone(session.loss_spec))
            except ExternalAuthoringPending as waiting:
                save('waiting-for-external-authoring', external=waiting.to_dict())
                raise SocietyPilotWaiting('saved society waits for exact external authoring') from waiting
            if (not isinstance(proposal, dict) or set(proposal) != MANIFEST_KEYS | {'authoring'}):
                raise ValueError('proposer must return complete patch, migration choices and authoring provenance')
            request = session.stage(parent_observation_id=view['observations'][-1]['observation_id'],
                patch=proposal['patch'], authoring=proposal['authoring'],
                state_actions=proposal['state_actions'], discard_deliveries=proposal['discard_deliveries'])
        digest_ = request['request_sha256']
        if digest_ in confirmed:
            session.confirm(request_id=request['request_id'], confirmed_request_sha256=digest_)
        approvals = session.projection().get('confirmations', ())
        if not any(c['request_sha256'] == digest_ for c in approvals):
            save('waiting-for-explicit-confirmation', confirm_request_sha256=digest_)
            raise SocietyPilotWaiting('saved society waits for exact staged-request confirmation')
        session.adopt(simulation, request_id=request['request_id'], confirmed_request_sha256=digest_)
        save('continuing-adopted-society')

    simulation.checkpoint_callback = boundary
    try:
        simulation.run()
    except SocietyPilotWaiting:
        return json.loads((output / 'progress.json').read_text())
    except BaseException as error:
        cause = error.__cause__ if isinstance(error, PortableStop) else error
        if isinstance(cause, Exception):
            save('technical-failure', error_type=type(cause).__name__, error=str(cause),
                failed_candidate_loss=None, automatic_redraft=False)
        raise
    finally:
        simulation.checkpoint_callback = previous_callback
    result = save('complete')
    write_json_atomic(output / 'completion.json', result, sort_keys=True, allow_nan=False)
    return result


def interval_from_checkpoint(path, *, after_year, fingerprint):
    """Independent read-only extraction; does not import native measurement code."""
    import math
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.native_kernel import NativeScienceKernel
    saved = read_portable_checkpoint(path)
    spec = SystemSpec.from_dict(saved['native_system']['spec'])
    kernel = NativeScienceKernel(spec, checkpoint=saved['native_system'])
    if spec.fingerprint != fingerprint or saved['phase'] != 5 or not after_year < kernel.last_year == saved['year']:
        raise ValueError('saved society interval fingerprint/year/phase differs')
    decisions = [d for paper in saved['paper_tracker']['papers'] for d in paper['review_history']
        if after_year == 0 or d['year'] > after_year]
    accepted = [d for d in decisions if d.get('decision') == 'accept']
    authors = [a for a in saved['ecosystem_data']['agents'] if a['can_author']]
    values = {'native.accepted_decisions': len(accepted),
        'native.rejected_decisions': sum(d.get('decision') == 'reject' for d in decisions),
        'native.review_records': sum(len(d.get('reviews', [])) for d in decisions),
        'native.final_active_authors': sum(a['is_active'] for a in authors),
        'native.final_author_resources': sum(a['resources'] for a in authors),
        'native.institutional_context_deliveries': sum(e.event_type == 'native.system.context_delivered'
            and e.year > after_year for e in kernel.events),
        'native.accepted_unreviewed_decisions': sum(not d.get('reviews', []) for d in accepted)}
    metrics = {key: {'status': 'measured', 'value': value} for key, value in values.items()}
    means, invalid = [], False
    for decision in accepted:
        scores = [r.get('overall_score') for r in decision.get('reviews', [])]
        if any(type(s) not in (int, float) or not math.isfinite(s) for s in scores):
            invalid = True
            break
        means.append(math.fsum(scores) / len(scores) if scores else 0.)
    metrics['native.accepted_peer_score_sum'] = ({'status': 'unavailable', 'value': None,
        'reason': 'accepted decision has a missing or nonfinite raw reviewer score'} if invalid else
        {'status': 'measured', 'value': sum(means)})
    return saved, kernel, {'run_id': f'same-society-{kernel.last_year}', 'system_fingerprint': fingerprint,
        'measurement_schema': 'scienceutopia.native-interval-measurements.v1', 'metrics': metrics,
        'interval': {'after_year': after_year, 'through_year': kernel.last_year},
        'comparison': 'online-same-society-not-counterfactual'}


def audit_society_pilot(session, *, inbox_directory=None):
    """Audit immutable observed societies, explicit adoptions and actual code effects."""
    from utopia.optimization.loss import evaluate_loss
    from utopia.optimization.native_manifest_inbox import audit_manifest_inbox
    from utopia.system.code_mechanisms import sha
    view = session.projection()
    original = file_sha256(session.path)
    rows = []
    for obs in view['observations']:
        path = session.directory / 'observed-societies' / (obs['checkpoint_sha256'] + '.json.gz')
        if file_sha256(path) != obs['checkpoint_sha256']:
            raise ValueError('observed complete society archive changed')
        saved, kernel, measured = interval_from_checkpoint(path, after_year=obs['after_year'], fingerprint=obs['system_fingerprint'])
        if measured != obs['measurement'] or evaluate_loss(session.loss_spec, [measured]) != obs['loss_evaluation']:
            raise ValueError('independently extracted society interval measurements/loss differ')
        contract = clone(saved['portable']['contract'])
        contract.pop('native_system', None)
        if contract != view['actual_society_binding']['portable_contract']:
            raise ValueError('native model/corpus/seed/source/original configuration changed')
        binding = contract['binding']
        scientific = binding.get('science_config', {})
        actual_world = {'model': binding.get('model'), 'model_digest': binding.get('model_revision'),
            'corpus_sha256': binding.get('corpus_sha256'), 'seed': binding.get('seed'),
            'source_commit': scientific.get('source_commit'), 'years': contract['simulation']['num_years'],
            'corpus_years': scientific.get('corpus_years'), 'runtime_seed_binding': scientific.get('runtime_seed_binding')}
        if any(session.binding['world'][k] != value for k, value in actual_world.items()
               if k in session.binding['world']):
            raise ValueError('declared pilot world differs from actual native checkpoint model/corpus/source/seed')
        adoptions = [a for a in view['adoptions'] if a['after_year'] < obs['through_year']]
        if [a['migration'] for a in adoptions] != kernel.design_history:
            raise ValueError('observed society migration lineage differs from adopted history')
        code = []
        for node in kernel.spec.mechanisms:
            if node.implementation != 'code.python.v1':
                continue
            executions = [e for e in kernel.events if e.event_type == 'generated.code_executed'
                and e.year > obs['after_year'] and e.provenance.get('mechanism_id') == node.mechanism_id]
            if not executions or any(e.payload['artifact_sha256'] != sha(node.parameters['code_artifact'])
                    or e.payload['image_id'] != node.parameters['runtime_image_id'] for e in executions):
                raise ValueError('adopted source has no exact actual execution in its following interval')
            code.append({'mechanism_id': node.mechanism_id, 'source_sha256': sha(node.parameters['code_artifact']['source']),
                'artifact_sha256': sha(node.parameters['code_artifact']), 'executions': len(executions)})
        effects = [e for e in kernel.events if e.event_type == 'native.system.research_plan_applied'
            and obs['after_year'] < e.year <= obs['through_year'] and e.payload['amendments']]
        event_map = {e.event_id: e for e in kernel.events}
        for effect in effects:
            for amendment in effect.payload['amendments']:
                if amendment['command_sha256'] != sha(amendment['command']) or not amendment['input_event_ids']:
                    raise ValueError('actual native activity effect lacks command/source binding')
                if any(i not in event_map or event_map[i].event_type != 'generated.code_executed'
                       for i in amendment['input_event_ids']):
                    raise ValueError('native activity effect is not caused by recorded generated code')
        rows.append({'through_year': obs['through_year'], 'after_year': obs['after_year'],
            'checkpoint_sha256': obs['checkpoint_sha256'], 'system_fingerprint': kernel.spec.fingerprint,
            'loss': obs['loss'], 'measurement': measured, 'code': code, 'actual_activity_effects': len(effects)})
    authoring = None
    if inbox_directory is not None:
        inbox = SocietyPatchInbox(inbox_directory)
        authoring = audit_manifest_inbox(inbox_directory)
        journal = session._read()['events']
        for index, request in enumerate(view['requests']):
            receipt = inbox._read(inbox._path('consumed', request['authoring']['external_request_sha256']))
            response = inbox._response(receipt['request_sha256'])
            if (response['manifest'] != {key: request[key] for key in MANIFEST_KEYS}
                    or receipt['manifest_sha256'] != request['authoring']['external_manifest_sha256']
                    or receipt['response_sha256'] != request['authoring']['external_response_sha256']):
                raise ValueError('external exact response-to-staged patch binding differs')
            authored = inbox._verify_request(receipt['request_sha256'])['request']['authoring_input']
            staged = next(e for e in journal if e['kind'] == 'staged'
                and e['payload']['request_sha256'] == request['request_sha256'])
            before = journal[:staged['index']]
            feedback = {'observations': [e['payload'] for e in before if e['kind'] == 'observed'],
                'requests': [e['payload'] for e in before if e['kind'] == 'staged'],
                'adoptions': [e['payload'] for e in before if e['kind'] == 'adopted'],
                'journal_sha256': staged['previous_sha256']}
            obs = feedback['observations'][-1]
            if (authored['feedback'] != feedback or authored['proposal_index'] != index
                    or authored['parent_system'] != obs['system'] or authored['loss_spec'] != session.loss_spec
                    or authored['world_binding'] != session.binding['world']
                    or digest(authored['actual_domain']) != obs['domain_sha256']
                    or digest(authored) != request['authoring']['proposer_input_sha256']
                    or any(request['authoring'].get(k) != v for k, v in receipt['authoring'].items())):
                raise ValueError('external author did not receive the exact parent society/objective/feedback binding')
    if file_sha256(session.path) != original:
        raise ValueError('read-only society audit changed the design journal')
    return {'schema': SCHEMA + '.audit', 'rows': rows, 'loss_path': [r['loss'] for r in rows],
        'adoptions': len(view['adoptions']), 'authoring': authoring, 'interpretation': INTERPRETATION,
        'live_model_calls': 0, 'causal_benefit_established': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path)
    parser.add_argument('--inference-lock', type=Path)
    parser.add_argument('--loss', type=Path, default=ROOT / 'research/objectives/losses/native-joint-v5-throughput.json')
    parser.add_argument('--confirm-request-sha256', action='append', default=[])
    parser.add_argument('--audit-only', action='store_true', help='read archived societies without factory, endpoint, Docker or inference')
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.audit_only or (args.output / 'completion.json').exists():
        from utopia.optimization.native_society_design import NativeSocietyDesignSession
        from utopia.system import SystemSpec
        plan = SocietyPatchInbox._read(args.output / 'plan.json')
        if not (args.output / 'session/society-design.json').is_file():
            raise ValueError('read-only audit requires an existing society journal')
        session = NativeSocietyDesignSession(args.output / 'session',
            founding_system=SystemSpec.from_dict(plan['founding_system']),
            loss_spec=plan['protocol']['loss'], world_binding=plan['world'])
        audit = audit_society_pilot(session, inbox_directory=args.output / 'authoring-inbox')
        if not args.audit_only:
            receipt = SocietyPatchInbox._read(args.output / 'completion.json')
            if receipt != progress(session, status='complete'):
                raise ValueError('terminal receipt differs from verified society session')
        print(json.dumps(audit, sort_keys=True), flush=True)
        return
    if args.data_cache is None or args.inference_lock is None:
        parser.error('live/resume mode requires explicit --data-cache and shared --inference-lock')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        parser.error('native society experiments require a clean commit-pinned source worktree')
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / '.pilot.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        from utopia.optimization.loss import load_loss_spec
        from utopia.optimization.native_factory import LocalQwenNativeFactory
        from utopia.optimization.native_society_design import NativeSocietyDesignSession
        from utopia.optimization.native_code_trace import RecordingCodeExecutor
        from utopia.system.code_mechanisms import DockerCodeExecutor
        from utopia.system.native_activity_contracts import activity_world_system
        loss = load_loss_spec(args.loss)
        protocol = {'schema': SCHEMA, 'kind': 'external-native-same-society-v6',
            'loss': loss, 'seed': 1301, 'years': 3, 'corpus_years': 4,
            'researcher_model': 'qwen3:8b', 'thinking': False, 'max_tokens': 768,
            'population': 'five-independent-balanced-researchers', 'adoptions': 2,
            'technical_drafts_per_boundary': 1, 'interpretation': INTERPRETATION,
            'no_hidden_merit_or_promotion_veto': True}
        factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache,
            years=3, corpus_years=4, max_tokens=768, experiment_binding=protocol,
            record_wire=True, record_code=True, inference_lock=args.inference_lock)
        executor = DockerCodeExecutor()
        initial = activity_world_system(seed=1301)
        world = {'source_commit': factory.source_commit, 'model': factory.model,
            'model_digest': factory.model_digest, 'corpus_sha256': factory.corpus_sha256,
            'dataset_identity': factory.dataset_identity, 'runtime_seed_binding': factory.runtime_seed_binding,
            'years': 3, 'corpus_years': 4, 'seed': 1301, 'image_id': executor.image_id,
            'data_cache': str(args.data_cache.resolve()), 'inference_lock': str(args.inference_lock.resolve()),
            'protocol': protocol}
        plan = {'protocol': protocol, 'world': world, 'founding_system': initial.to_dict()}
        plan_path = args.output / 'plan.json'
        if plan_path.exists() and SocietyPatchInbox._read(plan_path) != plan:
            raise ValueError('frozen same-society experiment plan changed')
        if not plan_path.exists():
            write_json_atomic(plan_path, plan, sort_keys=True, allow_nan=False)
        session = NativeSocietyDesignSession(args.output / 'session', founding_system=initial,
            loss_spec=loss, world_binding=world)
        # Always reopen the original founding configuration. Portable restore,
        # not a reset or rewritten system.json, recovers its migrated descendants.
        simulation = factory(initial, 1301, 'persistent-society')
        try:
            write_society_server_config(args.output, session, checkpoint_directory=simulation.output_dir)
            simulation.native_system.code_executor = RecordingCodeExecutor(executor,
                args.output / 'runs/persistent-society/code-contexts.jsonl', binding={
                    'source_commit': factory.source_commit, 'system_fingerprint': initial.fingerprint,
                    'run_id': 'persistent-society'})
            proposer = ExternalSocietyProposer(args.output / 'authoring-inbox', world_binding=world,
                domain_provider=lambda: session._domain(simulation), runtime_image_id=executor.image_id)
            result = run_society_pilot(simulation, session, proposer, output=args.output,
                confirm_request_sha256=args.confirm_request_sha256)
        finally:
            simulation.llm.response_cache.close()
        if result['status'] == 'complete':
            audit = audit_society_pilot(session, inbox_directory=args.output / 'authoring-inbox')
            write_json_atomic(args.output / 'audit.json', audit, sort_keys=True, allow_nan=False)
        print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
