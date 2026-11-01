#!/usr/bin/env python3
"""Read-only compact analysis of a terminal native joint-objective experiment.

No inference, container/code execution or new scientific worlds. Reconstructs
model requests from saved prompts and exact read-only response journals; replays
trusted graph routing against saved execution receipts, never generated Python.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
from types import MethodType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EXHAUSTED = 'bounded region technical drafts exhausted; no native loss fabricated'


def _proposer_class(binding_schema):
    """Versioned reconstruction, never reinterpret old prompts with new syntax."""
    known = {
        'scienceutopia.native-region-proposal.v5':
            ('utopia.optimization.native_region_proposer_v5', 'NativeRegionIRProposer'),
        'scienceutopia.native-region-proposal.v5a2':
            ('utopia.optimization.native_region_proposer_v5a2', 'NativeBoundaryRegionProposer'),
    }
    if binding_schema not in known:
        raise ValueError('unknown native region authoring binding schema')
    module, name = known[binding_schema]
    return getattr(importlib.import_module(module), name)


def _read(path):
    return json.loads(Path(path).read_text())


def _inventory(root):
    from utopia.utils.data_utils import file_sha256
    return {str(p.relative_to(root)): file_sha256(p) for p in sorted(root.rglob('*')) if p.is_file()}


class ReceiptExecutor:
    """Validate trusted graph/context reconstruction; never execute source."""
    def __init__(self, image_id):
        self.image_id = image_id
        self.current = None
        self.offset = 0
        self.failed_error_replayed = False

    def begin(self, receipt):
        self.current, self.offset = receipt, 0

    def execute(self, artifact, context):
        from utopia.system.code_mechanisms import CodeExecution, sha
        if self.current['status'] == 'invalid-technical-manifest':
            # Failed probes do not archive partial executions. Preserve their
            # recorded exception, without pretending to rerun/verify its cause.
            self.failed_error_replayed = True
            raise ValueError(self.current['error'])
        executions = [e for run in self.current['runs'] for e in run['code_executions']]
        if self.offset >= len(executions):
            raise ValueError('receipt replay requested an unrecorded code execution')
        execution = executions[self.offset]
        self.offset += 1
        receipt = execution['receipt']
        if (execution['context'] != context or receipt['image_id'] != self.image_id
                or receipt['artifact_sha256'] != sha(artifact)
                or receipt['context_sha256'] != sha(context)
                or receipt['result_sha256'] != sha(execution['result'])):
            raise ValueError('saved probe source/context/result/image provenance differs')
        return CodeExecution(execution['result'], receipt)

    def require_consumed(self):
        if self.current['status'] == 'isolated-native-region-passed-not-native-evaluated':
            expected = sum(len(r['code_executions']) for r in self.current['runs'])
            if self.offset != expected:
                raise ValueError('saved successful probe has unconsumed code executions')


class JournalReplay:
    """Use native transport/seed/request building, but only read committed SQL."""
    def __init__(self, path, *, binding, world, protocol):
        from utopia.models.models import VLLMServerModel
        self.path, self.binding = Path(path).resolve(), binding
        self.used = set()
        db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
        try:
            if db.execute('SELECT binding FROM metadata').fetchall() != [(
                    json.dumps(binding, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False),)]:
                # Canonical comparison below also supports archived JSON
                # whitespace from an independently serialized fixture.
                rows = db.execute('SELECT binding FROM metadata').fetchall()
                if len(rows) != 1 or json.loads(rows[0][0]) != binding:
                    raise ValueError('designer response journal binding differs')
            self.rows = {identity: (payload_sha, outcome, data, data_sha) for identity, payload_sha, outcome, data, data_sha
                         in db.execute('SELECT identity,payload_sha,outcome,data,data_sha FROM replies')}
        finally:
            db.close()
        for _, outcome, data, digest in self.rows.values():
            if outcome != 'response' or hashlib.sha256(data.encode()).hexdigest() != digest:
                raise ValueError('designer response journal content hash differs')
        model = VLLMServerModel.__new__(VLLMServerModel)
        model.model_name, model.run_seed = world['model'], protocol['seed']
        model.server_backend = 'ollama'
        thinking = protocol.get('designer_thinking', False)
        if type(thinking) is not bool:
            raise ValueError('designer_thinking must be an explicitly bound boolean')
        model.thinking_override = thinking
        model.max_tokens_override = protocol['max_tokens']
        model.response_cache = object()  # Native JSON parse must fail closed.

        def completion(_model, *, seed_ctx=None, **payload):
            from openai.types.chat import ChatCompletion
            from utopia.runtime.checkpointing import canonical_json
            seed = payload.get('seed', (payload.get('extra_body') or {}).get('seed'))
            identity = hashlib.sha256(canonical_json({'binding': self.binding, 'seed_ctx': seed_ctx,
                'item_index': 0, 'attempt': 0, 'seed': seed}).encode()).hexdigest()
            payload_sha = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
            if identity not in self.rows or self.rows[identity][0] != payload_sha:
                raise ValueError('reconstructed designer request identity/payload not in journal')
            self.used.add(identity)
            return ChatCompletion.model_validate(json.loads(self.rows[identity][2]))

        model._create_completion = MethodType(completion, model)
        self.model = model


def audit_proposals(arm, controller, *, run, protocol, world):
    if protocol.get('authoring_format') == 'staged-v5':
        from scripts.analyze_native_joint_staged_v5 import audit_staged_proposals
        return audit_staged_proposals(arm, controller, run=run, protocol=protocol, world=world)
    from utopia.optimization.native_code_trace import parent_context_provider
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    from utopia.system.design_patch import apply_design_patch

    directory = Path(run) / 'arms' / arm / 'design-proposals'
    groups = {}
    for path in sorted(directory.glob('region-*.json')):
        match = re.fullmatch(r'region-(\d+)-(\d+)\.json', path.name)
        if match:
            groups.setdefault(int(match[1]), []).append((int(match[2]), path))
    prompt_pairs = {tuple(map(int, m.groups())) for p in directory.glob('region-prompt-*.json')
                    if (m := re.fullmatch(r'region-prompt-(\d+)-(\d+)\.json', p.name))}
    if prompt_pairs != {(index, attempt) for index, paths in groups.items() for attempt, _ in paths}:
        raise ValueError('orphaned model prompt or draft receipt')
    binding = {'protocol': protocol['schema'], 'cell': controller.initial.fingerprint,
        'model': world['model'], 'model_revision': world['model_digest'],
        'corpus_sha256': world['corpus_sha256'], 'seed': protocol['seed'],
        'science_config': {'source_commit': world['source_commit'],
            'objective_campaign_binding': controller.binding, 'protocol': protocol}}
    journal = JournalReplay(Path(run) / 'arms' / arm / 'designer-replies.sqlite',
        binding=binding, world=world, protocol=protocol)
    summaries = []
    provider = parent_context_provider(Path(run) / 'runs', source_commit=world['source_commit'])
    for index, paths in sorted(groups.items()):
        if not 1 <= index <= len(controller.state['records']):
            raise ValueError('proposal index has no matching adaptive observation or terminal draft')
        paths.sort()
        if [i for i, _ in paths] != list(range(len(paths))) or len(paths) > protocol['max_technical_drafts']:
            raise ValueError('technical draft sequence exceeds/misses declared budget')
        history = controller.state['records'][:index]
        best = min((r for r in history if r['observation']['status'] == 'complete'),
                   key=lambda r: r['observation']['loss'])
        parent = SystemSpec.from_dict(best['suggestion']['candidate'])
        receipts = [_read(path) for _, path in paths]
        authoring_schema = receipts[0]['binding']['schema']
        declared_schema = {'scoped-v5': 'scienceutopia.native-region-proposal.v5',
            'boundary-v5a2': 'scienceutopia.native-region-proposal.v5a2'}.get(protocol.get('authoring_format', 'scoped-v5'))
        if authoring_schema != declared_schema:
            raise ValueError('actual authoring version differs from frozen experiment format')
        if any(r['binding']['schema'] != authoring_schema for r in receipts):
            raise ValueError('authoring version changed inside one repair chain')
        proposer_class = _proposer_class(authoring_schema)
        first_prompt = _read(directory / f'region-prompt-{index}-0.json')
        instructions = json.loads(first_prompt['prompt'])['instructions']
        executor = ReceiptExecutor(world['image_id'])
        draft_model = journal.model
        original_generate = draft_model.generate
        calls = []

        class CheckedModel:
            def generate(self, **kwargs):
                attempt = len(calls)
                if attempt >= len(receipts):
                    raise ValueError('reconstruction requests an unrecorded draft')
                receipt = receipts[attempt]
                prompt = _read(directory / f'region-prompt-{index}-{attempt}.json')
                if (prompt['prompt'] != kwargs['prompt'] or sha(kwargs['prompt']) != prompt['prompt_sha256']
                        or receipt['prompt_sha256'] != prompt['prompt_sha256']):
                    raise ValueError('exact objective/history/context/repair prompt differs')
                generated, messages = original_generate(**kwargs)
                if generated != receipt['generated']:
                    raise ValueError('model journal reply differs from claimed generated IR')
                executor.begin(receipt)
                calls.append(attempt)
                return generated, messages

        with tempfile.TemporaryDirectory(prefix='native-joint-v5-audit-') as temporary:
            proposer = proposer_class(CheckedModel(), executor,
                removed_nodes=['world.selection'], context_provider=provider,
                receipts=temporary, instructions=instructions,
                max_attempts=protocol['max_technical_drafts'], max_tokens=protocol['max_tokens'])
            try:
                patch = proposer(parent, history, index, controller.loss_spec)
            except ValueError as error:
                if str(error) != EXHAUSTED or receipts[-1]['status'] != 'invalid-technical-manifest':
                    raise
                patch = None
            if len(calls) != len(receipts):
                raise ValueError('extra draft remains beyond the reproduced terminal result')
            executor.require_consumed()
            for attempt, original in enumerate(receipts):
                rebuilt = _read(Path(temporary) / f'region-{index}-{attempt}.json')
                rebuilt_prompt = _read(Path(temporary) / f'region-prompt-{index}-{attempt}.json')
                if rebuilt != original or rebuilt_prompt != _read(directory / f'region-prompt-{index}-{attempt}.json'):
                    raise ValueError('saved draft/prompt/binding/receipt chain differs from reconstruction')
        if patch is not None:
            if index >= len(controller.state['records']):
                raise ValueError('eligible authored proposal has no native observation')
            record = controller.state['records'][index]
            child = apply_design_patch(parent, patch)
            if record['patch'] != patch or record['suggestion']['candidate'] != child.to_dict():
                raise ValueError('generated code/graph patch differs from native evaluated candidate')
        elif index != len(controller.state['records']) or len(receipts) != protocol['max_technical_drafts']:
            raise ValueError('technical exhaustion is not the final complete declared draft budget')
        summaries.append({'proposal_index': index, 'draft_count': len(receipts),
            'authoring_binding_schema': authoring_schema,
            'status': receipts[-1]['status'], 'candidate_fingerprint': receipts[-1].get('candidate_fingerprint'),
            'receipts': [{'attempt': i, 'receipt_sha256': r['receipt_sha256'],
                'prompt_sha256': r['prompt_sha256'], 'status': r['status'],
                'error': r.get('error'), 'generated_source_sha256s': r.get('generated_source_sha256s', {})}
                for i, r in enumerate(receipts)],
            'failed_probe_error_preserved_not_reexecuted': executor.failed_error_replayed})
    expected_observed = set(range(1, len(controller.state['records'])))
    if not expected_observed <= groups.keys():
        raise ValueError('an adaptive native observation lacks model authoring provenance')
    if journal.used != set(journal.rows):
        raise ValueError('designer journal contains an unaccounted model response')
    return summaries


def analyze(run):
    from scripts.audit_native_objective_v5 import audit_campaign, checkpoint_measurements
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_shared_initial import verify_shared_initial
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    from utopia.runtime.checkpointing import read_portable_checkpoint

    run = Path(run).resolve()
    if not (run / 'completion.json').exists():
        raise ValueError('analysis requires a terminal experiment completion receipt')
    before = _inventory(run)
    plan, terminal = _read(run / 'plan.json'), _read(run / 'completion.json')
    protocol, world = plan['protocol'], plan['world']
    classification = protocol.get('classification', 'actual-native-development-objective-conditioned-joint-design')
    if classification not in {'actual-native-development-objective-conditioned-joint-design',
                               'scripted-fixture-not-native-results'}:
        raise ValueError('unknown explicitly bound experiment evidence classification')
    if protocol['schema'] != 'scienceutopia.native-joint-objectives.v5' or world['protocol'] != protocol:
        raise ValueError('joint experiment protocol/world binding differs')
    arm_ids, losses = protocol['arm_ids'], protocol['losses']
    if len(arm_ids) != len(losses) or len(set(arm_ids)) != len(arm_ids):
        raise ValueError('joint objective arms are not one-to-one')
    controllers = []
    for arm, loss in zip(arm_ids, losses):
        state = _read(run / 'arms' / arm / 'campaign/native-design-state.json')
        initial = SystemSpec.from_dict(state['records'][0]['parent_system'])
        if initial.fingerprint != plan['initial_fingerprint']:
            raise ValueError('initial system differs from frozen experiment plan')
        controllers.append(NativeDesignCampaign(run / 'arms' / arm / 'campaign',
            initial_system=initial, loss_spec=loss, seeds=[protocol['seed']], world_binding=world))
    for target in controllers[1:]:
        verify_shared_initial(target, controllers[0], checkpoint_measurement=checkpoint_measurements)
    errors = _read(run / 'terminal-authoring-errors.json') if (run / 'terminal-authoring-errors.json').exists() else {}
    if not set(errors) <= set(arm_ids):
        raise ValueError('terminal errors refer to an undeclared arm')
    arms = {}
    physical = {}
    checked_physical = set()
    for arm, loss, controller in zip(arm_ids, losses, controllers):
        audited = audit_campaign(run / 'arms' / arm, loss, {s['id']: s for s in losses})
        completion = _read(run / 'arms' / arm / 'completion.json')
        count = len(controller.state['records'])
        complete = count == protocol['budget_per_arm']
        expected_status = 'declared-budget-complete' if complete else 'terminal-authoring-failure-not-budget-complete'
        error = errors.get(arm)
        if (completion['declared_budget'] != protocol['budget_per_arm'] or completion['budget'] != count
                or completion['logical_observations'] != count or completion['status'] != expected_status
                or completion['terminal_authoring_error'] != error or completion['source_commit'] != world['source_commit']):
            raise ValueError('arm completion does not match actual terminal observations')
        if not complete and (not error or error['loss'] is not None or error['automatic_redraft'] is not False
                or error['proposal_index'] != count or error['error'] != EXHAUSTED):
            raise ValueError('incomplete arm lacks explicit bounded technical null-score exhaustion')
        if complete and error:
            raise ValueError('completed arm also claims a terminal authoring error')
        proposals = audit_proposals(arm, controller, run=run, protocol=protocol, world=world)
        expected_indices = set(range(1, count if complete else count + 1))
        if {p['proposal_index'] for p in proposals} != expected_indices:
            raise ValueError('authoring provenance count differs from declared terminal outcome')
        if not complete and (not proposals or proposals[-1]['proposal_index'] != count
                or proposals[-1]['status'] != 'invalid-technical-manifest'):
            raise ValueError('terminal authoring error lacks full preserved draft evidence')
        best = controller.incumbent()
        selected_index = next(i for i, r in enumerate(controller.state['records']) if r == best)
        for i, row in enumerate(audited['rows']):
            row['proposal_index'] = i
            covered = [e['seed'] for e in row['runs']] + [f['seed'] for f in row['technical_failures']]
            if sorted(covered) != [protocol['seed']]:
                raise ValueError('native observation/failure does not cover exact declared development seed')
            for evidence in row['runs']:
                identity = (evidence['checkpoint'], evidence['checkpoint_sha256'])
                old = physical.setdefault(evidence['run_id'], identity)
                if old != identity:
                    raise ValueError('one physical run ID refers to different checkpoint evidence')
                if identity not in checked_physical:
                    state = read_portable_checkpoint(evidence['checkpoint'])
                    science = state['portable']['contract']['binding']['science_config']
                    if (science['years'] != protocol['years'] or science['corpus_years'] != protocol['corpus_years']
                            or science.get('runtime_seed_binding') != world['runtime_seed_binding']
                            or science.get('experiment') != protocol
                            or science.get('thinking_override') is not False):
                        raise ValueError('native physical horizon/hash-seed/experiment/researcher-thinking binding differs')
                    checked_physical.add(identity)
        arms[arm] = {'loss_spec': loss, 'status': expected_status, 'audit': audited,
            'loss_path': audited['loss_path'], 'selected_index': selected_index,
            'selected_system': best['suggestion']['candidate'],
            'selected_fingerprint': best['observation']['metadata']['system_fingerprint'],
            'authoring_error': error, 'proposals': proposals}
    all_complete = all(a['status'] == 'declared-budget-complete' for a in arms.values())
    status = 'declared-budget-complete' if all_complete else 'terminal-with-preserved-failures'
    logical = sum(len(a['loss_path']) for a in arms.values())
    if terminal['status'] != status or terminal['physical_complete_runs'] != len(physical):
        raise ValueError('root completion classification or physical run count differs')
    if terminal['source_commit'] != world['source_commit'] or terminal['budget_per_arm'] != protocol['budget_per_arm']:
        raise ValueError('root completion source/budget differs')
    if set(terminal['arms']) != set(arms):
        raise ValueError('root completion objective arms differ')
    for arm, value in arms.items():
        expected = {'logical_observations': len(value['loss_path']), 'loss_path': value['loss_path'],
            'candidate_fingerprints': [r['system_fingerprint'] for r in value['audit']['rows']],
            'terminal_authoring_error': value['authoring_error'], 'pending': False}
        if terminal['arms'][arm] != expected:
            raise ValueError('root completion trajectory differs from audited objective arm')
    after = _inventory(run)
    if after != before:
        raise ValueError('read-only analysis changed, added, removed or observed changing input files')
    return {'schema': 'scienceutopia.native-joint-objectives-analysis.v5',
        'classification': classification,
        'status': status, 'source_commit': world['source_commit'], 'raw_output_root': str(run),
        'input_manifest_sha256': sha(before), 'input_file_count': len(before),
        'input_file_hashes': before, 'physical_complete_runs': len(physical),
        'logical_observations': logical, 'shared_initial_physical_runs': len(controllers[0].seeds),
        'new_inference_requests': 0, 'generated_code_executions_during_analysis': 0,
        'arms': arms,
        'limits': ['one development seed and small horizon, not held-out superiority',
            'explicit engineering throughput/peer-score utility, not scientific value',
            'cross-loss shared initial and cross-scoring are not independent replicates',
            'successful frozen probes verify saved receipts/routing; code is not reexecuted',
            'failed sandbox errors are preserved claims, not independently reexecuted failure causes',
            'no full native-world pathwise backpropagation claim']}


def main():
    from utopia.utils.data_utils import write_json_atomic
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run, output = args.run.resolve(), args.output.resolve()
    if output.is_relative_to(run):
        parser.error('analysis output must be outside immutable raw run directory')
    result = analyze(run)
    write_json_atomic(output, result, sort_keys=True, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'status': result['status'], 'output': str(output),
                      'physical_complete_runs': result['physical_complete_runs']}, sort_keys=True))


if __name__ == '__main__':
    main()
