#!/usr/bin/env python3
"""Independent external-manifest -> compiled design -> actual native audit.

Read-only file-response replay, not a Qwen-designer journal or provider identity
attestation. Saved Python is NEVER executed during analysis; researcher response
journals and native checkpoint measurements are still independently verified.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_joint_objectives_v5 import EXHAUSTED, ReceiptExecutor, _inventory, _read


class ExternalManifestReplay:
    """Verify every consumed canonical object AND exact request/response bytes."""
    def __init__(self, directory):
        from utopia.system.code_mechanisms import sha
        from utopia.utils.data_utils import file_sha256
        self.directory, self.used = Path(directory).resolve(), set()
        self.records = {}
        sets = {section: {p.stem for p in (self.directory / section).glob('*.json')}
                for section in ('requests', 'responses', 'consumed')}
        if not sets['requests'] == sets['responses'] == sets['consumed']:
            raise ValueError('terminal external inbox has orphaned or unconsumed files')
        for digest in sorted(sets['requests']):
            paths = {section: self.directory / section / (digest + '.json') for section in sets}
            if any(p.is_symlink() or not p.is_file() or p.stat().st_size > 2_097_152 for p in paths.values()):
                raise ValueError('external audit requires bounded regular non-symlink files')
            request, response, consumed = (_read(paths[key]) for key in ('requests', 'responses', 'consumed'))
            if (set(request) != {'schema', 'request'} or request['schema'] != 'scienceutopia.external-manifest-request.v5'
                    or not isinstance(request['request'], dict) or sha(request) != digest):
                raise ValueError('external request canonical identity differs')
            if (set(response) != {'request_sha256', 'manifest', 'authoring'} or response['request_sha256'] != digest
                    or not isinstance(response['manifest'], dict) or not isinstance(response['authoring'], dict)
                    or response['authoring'].get('kind') not in {'codex-agent', 'external'}):
                raise ValueError('external response/request/author declaration differs')
            expected = {'schema': 'scienceutopia.external-manifest-consumed.v5', 'request_sha256': digest,
                'response_sha256': sha(response), 'request_file_sha256': file_sha256(paths['requests']),
                'response_file_sha256': file_sha256(paths['responses']),
                'manifest_sha256': sha(response['manifest']), 'authoring': response['authoring']}
            if consumed != expected:
                raise ValueError('external consumed raw/canonical request/response/manifest hashes differ')
            self.records[digest] = {'request': request, 'response': response, 'consumed': consumed}

    def generate(self, **kwargs):
        from utopia.system.code_mechanisms import sha
        request = json.loads(json.dumps({'schema': 'scienceutopia.external-manifest-request.v5', 'request': kwargs},
                                       ensure_ascii=False, allow_nan=False))
        digest = sha(request)
        if digest not in self.records or self.records[digest]['request'] != request:
            raise ValueError('exact objective/history/context/seed/schema request absent from external inbox')
        if digest in self.used:
            raise ValueError('one external request was consumed twice during reconstruction')
        self.used.add(digest)
        return deepcopy(self.records[digest]['response']['manifest']), []

    def summary(self):
        return [{'request_sha256': digest, **record['consumed']} for digest, record in self.records.items()]


def audit_external_proposals(arm, controller, *, run, protocol, world):
    from utopia.optimization.native_code_trace import parent_context_provider
    from utopia.optimization.native_region_proposer_v5a2 import NativeBoundaryRegionProposer
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    from utopia.system.design_patch import apply_design_patch

    directory = Path(run) / 'arms' / arm / 'design-proposals'
    inbox = ExternalManifestReplay(Path(run) / 'arms' / arm / 'authoring-inbox')
    groups, prompt_pairs = {}, set()
    for path in directory.glob('*.json'):
        match = re.fullmatch(r'region-(\d+)-(\d+)\.json', path.name)
        if match:
            index, attempt = map(int, match.groups())
            groups.setdefault(index, []).append((attempt, path))
        match = re.fullmatch(r'region-prompt-(\d+)-(\d+)\.json', path.name)
        if match:
            prompt_pairs.add(tuple(map(int, match.groups())))
    if prompt_pairs != {(index, attempt) for index, paths in groups.items() for attempt, _ in paths}:
        raise ValueError('orphaned external proposer prompt or draft')
    provider = parent_context_provider(Path(run) / 'runs', source_commit=world['source_commit'])
    summaries = []
    for index, paths in sorted(groups.items()):
        paths.sort()
        if not 1 <= index <= len(controller.state['records']):
            raise ValueError('external proposal has no corresponding parent/native observation')
        if [i for i, _ in paths] != list(range(len(paths))) or len(paths) > protocol['max_technical_drafts']:
            raise ValueError('external technical draft sequence differs from explicit budget')
        history = controller.state['records'][:index]
        best = min((r for r in history if r['observation']['status'] == 'complete'), key=lambda r: r['observation']['loss'])
        parent = SystemSpec.from_dict(best['suggestion']['candidate'])
        receipts = [_read(path) for _, path in paths]
        if any(r['binding']['schema'] != 'scienceutopia.native-region-proposal.v5a2' or r['loss'] is not None for r in receipts):
            raise ValueError('external authoring receipt version or null technical loss differs')
        instructions = json.loads(_read(directory / f'region-prompt-{index}-0.json')['prompt'])['instructions']
        executor = ReceiptExecutor(world['image_id'])
        calls = []

        class CheckedModel:
            def generate(self, **kwargs):
                attempt = len(calls)
                if attempt >= len(receipts):
                    raise ValueError('external reconstruction requested an unrecorded draft')
                receipt = receipts[attempt]
                prompt = _read(directory / f'region-prompt-{index}-{attempt}.json')
                if prompt['prompt'] != kwargs['prompt'] or sha(kwargs['prompt']) != prompt['prompt_sha256']:
                    raise ValueError('exact external proposer prompt differs')
                generated, messages = inbox.generate(**kwargs)
                if generated != receipt['generated']:
                    raise ValueError('consumed external manifest differs from generated IR receipt')
                executor.begin(receipt)
                calls.append(attempt)
                return generated, messages

        with tempfile.TemporaryDirectory(prefix='external-native-v5-audit-') as temporary:
            proposer = NativeBoundaryRegionProposer(CheckedModel(), executor,
                removed_nodes=['world.selection'], context_provider=provider, receipts=temporary,
                instructions=instructions, max_attempts=protocol['max_technical_drafts'],
                max_tokens=protocol['requested_designer_max_tokens'])
            try:
                patch = proposer(parent, history, index, controller.loss_spec)
            except ValueError as error:
                if str(error) != EXHAUSTED or receipts[-1]['status'] != 'invalid-technical-manifest':
                    raise
                patch = None
            if len(calls) != len(receipts):
                raise ValueError('extra external draft beyond reconstructed terminal result')
            executor.require_consumed()
            for attempt, receipt in enumerate(receipts):
                if (_read(Path(temporary) / f'region-{index}-{attempt}.json') != receipt
                        or _read(Path(temporary) / f'region-prompt-{index}-{attempt}.json')
                        != _read(directory / f'region-prompt-{index}-{attempt}.json')):
                    raise ValueError('external prompt/IR/patch/probe receipt chain differs')
        if patch is not None:
            if index >= len(controller.state['records']):
                raise ValueError('eligible external design has no native evaluation')
            child = apply_design_patch(parent, patch)
            record = controller.state['records'][index]
            if record['patch'] != patch or record['suggestion']['candidate'] != child.to_dict():
                raise ValueError('external generated IR/compiled patch differs from actual native design')
        elif index != len(controller.state['records']) or len(receipts) != protocol['max_technical_drafts']:
            raise ValueError('external failure is not final exact technical-budget exhaustion')
        summaries.append({'proposal_index': index, 'draft_count': len(receipts),
            'status': receipts[-1]['status'], 'candidate_fingerprint': receipts[-1].get('candidate_fingerprint'),
            'authoring_binding_schema': 'scienceutopia.native-region-proposal.v5a2',
            'receipts': [{'attempt': i, 'receipt_sha256': r['receipt_sha256'], 'prompt_sha256': r['prompt_sha256'],
                'status': r['status'], 'error': r.get('error'), 'generated_source_sha256s': r.get('generated_source_sha256s', {})}
                for i, r in enumerate(receipts)],
            'failed_probe_error_preserved_not_reexecuted': executor.failed_error_replayed})
    if not set(range(1, len(controller.state['records']))) <= groups.keys() or inbox.used != set(inbox.records):
        raise ValueError('external observations or consumed inbox responses lack one-to-one provenance')
    return summaries, inbox.summary()


def analyze(run):
    from scripts.audit_native_objective_v5 import audit_campaign, checkpoint_measurements
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_shared_initial import verify_shared_initial
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha

    run = Path(run).resolve()
    if not (run / 'completion.json').exists():
        raise ValueError('external analysis requires terminal root completion, not waiting manifests')
    before = _inventory(run)
    plan, terminal = _read(run / 'plan.json'), _read(run / 'completion.json')
    protocol, world = plan['protocol'], plan['world']
    if (protocol['schema'] != 'scienceutopia.external-native-objectives.v5'
            or protocol['kind'] != 'externalnative-v5'
            or protocol['authoring_format'] != 'boundary-v5a2-external-manifest'
            or protocol['designer_transport'] != 'hash-bound-file-inbox-no-provider-API'
            or protocol['researcher_model'] != world['model'] or world['protocol'] != protocol):
        raise ValueError('external protocol/authoring/world binding differs')
    classification = protocol.get('classification', 'actual-native-development-objective-conditioned-joint-design')
    if classification not in {'actual-native-development-objective-conditioned-joint-design', 'scripted-fixture-not-native-results'}:
        raise ValueError('unknown explicit external evidence classification')
    arm_ids, losses = protocol['arm_ids'], protocol['losses']
    if len(arm_ids) != 2 or len(losses) != 2 or len(set(arm_ids)) != 2:
        raise ValueError('external experiment requires two distinct explicit objective arms')
    if arm_ids != [re.sub(r'[^a-zA-Z0-9_-]', '-', loss['id']) for loss in losses]:
        raise ValueError('external arm paths do not match safe objective identifiers')
    controllers = []
    for arm, loss in zip(arm_ids, losses):
        state = _read(run / 'arms' / arm / 'campaign/native-design-state.json')
        initial = SystemSpec.from_dict(state['records'][0]['parent_system'])
        if initial.fingerprint != plan['initial_fingerprint']:
            raise ValueError('external initial graph differs from frozen plan')
        controllers.append(NativeDesignCampaign(run / 'arms' / arm / 'campaign', initial_system=initial,
            loss_spec=loss, seeds=[protocol['seed']], world_binding=world))
    verify_shared_initial(controllers[1], controllers[0], checkpoint_measurement=checkpoint_measurements)
    errors = _read(run / 'terminal-authoring-errors.json') if (run / 'terminal-authoring-errors.json').exists() else {}
    if not set(errors) <= set(arm_ids):
        raise ValueError('external terminal error refers to undeclared arm')
    arms, physical, author_claims = {}, {}, {}
    for arm, loss, controller in zip(arm_ids, losses, controllers):
        audited = audit_campaign(run / 'arms' / arm, loss, {l['id']: l for l in losses}, require_completion=False)
        count, error = len(controller.state['records']), errors.get(arm)
        if not 1 <= count <= protocol['budget_per_arm'] or controller.state['pending'] is not None:
            raise ValueError('external terminal arm exceeds budget or retains pending native execution')
        complete = count == protocol['budget_per_arm']
        if (complete and error) or (not complete and (not error or error['proposal_index'] != count
                or error['error'] != EXHAUSTED or error['loss'] is not None or error['automatic_redraft'] is not False)):
            raise ValueError('external arm budget outcome and null technical exhaustion disagree')
        proposals, inbox = audit_external_proposals(arm, controller, run=run, protocol=protocol, world=world)
        if {p['proposal_index'] for p in proposals} != set(range(1, count if complete else count + 1)):
            raise ValueError('external proposal count differs from actual terminal native history')
        if not complete and proposals[-1]['status'] != 'invalid-technical-manifest':
            raise ValueError('external terminal failure lacks exhausted invalid draft receipts')
        for entry in inbox:
            author_claims[sha(entry['authoring'])] = entry['authoring']
        for i, row in enumerate(audited['rows']):
            row['proposal_index'] = i
            if sorted([e['seed'] for e in row['runs']] + [f['seed'] for f in row['technical_failures']]) != [protocol['seed']]:
                raise ValueError('external native observation does not cover exact development seed')
            for evidence in row['runs']:
                identity = (evidence['checkpoint'], evidence['checkpoint_sha256'])
                if physical.setdefault(evidence['run_id'], identity) != identity:
                    raise ValueError('one external physical run ID aliases different checkpoints')
                state = read_portable_checkpoint(evidence['checkpoint'])
                science = state['portable']['contract']['binding']['science_config']
                if (science['years'] != protocol['years'] or science['corpus_years'] != protocol['corpus_years']
                        or science.get('runtime_seed_binding') != world['runtime_seed_binding']
                        or science.get('experiment') != protocol or science.get('thinking_override') is not False):
                    raise ValueError('external native physical horizon/hash-seed/researcher binding differs')
        best = controller.incumbent()
        selected = next(i for i, r in enumerate(controller.state['records']) if r == best)
        arms[arm] = {'loss_spec': loss, 'audit': audited, 'loss_path': audited['loss_path'],
            'status': 'declared-budget-complete' if complete else 'terminal-authoring-failure-not-budget-complete',
            'observed_systems': [deepcopy(record['suggestion']['candidate']) for record in controller.state['records']],
            'selected_index': selected, 'selected_system': best['suggestion']['candidate'],
            'selected_fingerprint': best['observation']['metadata']['system_fingerprint'],
            'authoring_error': error, 'proposals': proposals, 'external_authoring': inbox}
    expected_status = 'declared-budget-complete' if all(a['status'] == 'declared-budget-complete' for a in arms.values()) else 'terminal-with-preserved-failures'
    if (terminal['schema'] != protocol['schema'] or terminal['status'] != expected_status or terminal.get('terminal') is not True
            or terminal['source_commit'] != world['source_commit'] or terminal['pending_external_authoring']
            or set(terminal['arms']) != set(arms)):
        raise ValueError('external root terminal classification/source/pending state differs')
    for arm, value in arms.items():
        if terminal['arms'][arm] != {'logical_observations': len(value['loss_path']), 'loss_path': value['loss_path'],
                'pending_native_execution': False, 'terminal_authoring_error': value['authoring_error']}:
            raise ValueError('external root completion path differs from audited native observations')
    if _inventory(run) != before:
        raise ValueError('external read-only audit changed or observed changing raw inputs')
    return {'schema': 'scienceutopia.native-joint-objectives-analysis.v5', 'classification': classification,
        'status': expected_status, 'source_commit': world['source_commit'], 'raw_output_root': str(run),
        'designer_transport': protocol['designer_transport'],
        'authoring_provenance': {'kind': 'hash-bound-external-manifest', 'provider_authenticated': False,
            'self_reported_authors': list(author_claims.values()), 'qwen_designer_authorship_claimed': False},
        'input_manifest_sha256': sha(before), 'input_file_count': len(before), 'input_file_hashes': before,
        'physical_complete_runs': len(physical), 'logical_observations': sum(len(a['loss_path']) for a in arms.values()),
        'shared_initial_physical_runs': 1, 'new_inference_requests': 0, 'generated_code_executions_during_analysis': 0,
        'arms': arms, 'limits': ['external author metadata is self-reported, not authenticated provider identity',
            'no Qwen-designer response-journal or authorship claim; researcher journals are audited',
            'one development seed; explicit engineering proxies, not held-out scientific quality',
            'shared baseline and cross-scoring are not independent replicates',
            'saved successful probe routing/receipts replayed without Python/container execution',
            'failed sandbox causes preserved, not independently reexecuted']}


def main():
    from utopia.utils.data_utils import write_json_atomic
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error('analysis output must be outside immutable raw run directory')
    result = analyze(args.run)
    write_json_atomic(args.output, result, sort_keys=True, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'status': result['status'], 'physical_complete_runs': result['physical_complete_runs'],
                      'output': str(args.output.resolve())}, sort_keys=True))


if __name__ == '__main__':
    main()
