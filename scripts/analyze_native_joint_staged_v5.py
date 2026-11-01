"""Separate staged-authoring audit; old v5/v5a2 reconstruction stays unchanged."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile

from scripts.analyze_native_joint_objectives_v5 import (
    EXHAUSTED, JournalReplay, ReceiptExecutor, _read,
)


class StagedReceiptExecutor(ReceiptExecutor):
    def execute(self, artifact, context):
        if self.current['binding']['phase'] == 'plan':
            raise AssertionError('structure-only placeholder must never be executed')
        if self.current['status'] == 'invalid-technical-source':
            prefix = 'full chronological native probe: '
            errors = [e for e in self.current['errors'] if e.startswith(prefix)]
            if len(errors) != 1:
                raise ValueError('failed source execution lacks one preserved probe error')
            self.failed_error_replayed = True
            raise ValueError(errors[0][len(prefix):])
        return super().execute(artifact, context)


def audit_staged_proposals(arm, controller, *, run, protocol, world):
    from utopia.optimization.native_code_trace import parent_context_provider
    from utopia.optimization.native_staged_region_proposer import NativeStagedRegionProposer, SCHEMA
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    from utopia.system.design_patch import apply_design_patch

    directory = Path(run) / 'arms' / arm / 'design-proposals'
    groups, prompt_pairs = {}, set()
    for path in sorted(directory.glob('*.json')):
        match = re.fullmatch(r'(plan|region)-(\d+)-(\d+)\.json', path.name)
        if match:
            phase, index, attempt = match.groups()
            groups.setdefault(int(index), {}).setdefault(phase, []).append((int(attempt), path))
        match = re.fullmatch(r'(plan|region)-prompt-(\d+)-(\d+)\.json', path.name)
        if match:
            phase, index, attempt = match.groups()
            prompt_pairs.add((phase, int(index), int(attempt)))
    if prompt_pairs != {(phase, index, attempt) for index, phases in groups.items()
                        for phase, paths in phases.items() for attempt, _ in paths}:
        raise ValueError('orphaned staged model prompt or draft receipt')
    binding = {'protocol': protocol['schema'], 'cell': controller.initial.fingerprint,
        'model': world['model'], 'model_revision': world['model_digest'],
        'corpus_sha256': world['corpus_sha256'], 'seed': protocol['seed'],
        'science_config': {'source_commit': world['source_commit'],
            'objective_campaign_binding': controller.binding, 'protocol': protocol}}
    journal = JournalReplay(Path(run) / 'arms' / arm / 'designer-replies.sqlite',
        binding=binding, world=world, protocol=protocol)
    provider = parent_context_provider(Path(run) / 'runs', source_commit=world['source_commit'])
    budgets = {'plan': protocol.get('plan_attempts', protocol['max_technical_drafts']),
               'region': protocol.get('source_attempts', protocol['max_technical_drafts'])}
    summaries = []
    for index, phases in sorted(groups.items()):
        if not 1 <= index <= len(controller.state['records']) or 'plan' not in phases:
            raise ValueError('staged proposal index has no parent history or graph plan')
        entries = []
        for phase in ('plan', 'region'):
            paths = sorted(phases.get(phase, []))
            if [i for i, _ in paths] != list(range(len(paths))) or len(paths) > budgets[phase]:
                raise ValueError('staged draft sequence exceeds/misses declared phase budget')
            entries.extend((phase, attempt, path, _read(path)) for attempt, path in paths)
        if any(r['binding']['schema'] != SCHEMA or r['binding']['phase'] != ('plan' if phase == 'plan' else 'source')
               or r['loss'] is not None for phase, _, _, r in entries):
            raise ValueError('staged phase/schema/null-score binding differs')
        history = controller.state['records'][:index]
        best = min((r for r in history if r['observation']['status'] == 'complete'),
                   key=lambda r: r['observation']['loss'])
        parent = SystemSpec.from_dict(best['suggestion']['candidate'])
        instructions = json.loads(_read(directory / f'plan-prompt-{index}-0.json')['prompt'])['instructions']
        executor = StagedReceiptExecutor(world['image_id'])
        calls = []

        class CheckedModel:
            def generate(self, **kwargs):
                offset = len(calls)
                if offset >= len(entries):
                    raise ValueError('staged reconstruction requests an unrecorded model draft')
                phase, attempt, _, receipt = entries[offset]
                prompt = _read(directory / f'{phase}-prompt-{index}-{attempt}.json')
                if (prompt['prompt'] != kwargs['prompt'] or sha(kwargs['prompt']) != prompt['prompt_sha256']
                        or receipt['prompt_sha256'] != prompt['prompt_sha256']):
                    raise ValueError('exact staged objective/history/plan/repair prompt differs')
                generated, messages = journal.model.generate(**kwargs)
                if generated != receipt['generated']:
                    raise ValueError('staged journal reply differs from claimed graph/source')
                executor.begin(receipt)
                calls.append((phase, attempt))
                return generated, messages

        with tempfile.TemporaryDirectory(prefix='native-staged-v5-audit-') as temporary:
            proposer = NativeStagedRegionProposer(CheckedModel(), executor,
                removed_nodes=['world.selection'], context_provider=provider, receipts=temporary,
                instructions=instructions, plan_attempts=budgets['plan'],
                source_attempts=budgets['region'], max_tokens=protocol['max_tokens'])
            try:
                patch = proposer(parent, history, index, controller.loss_spec)
            except ValueError as error:
                if str(error) != EXHAUSTED or entries[-1][3]['status'] not in {'invalid-technical-plan', 'invalid-technical-source'}:
                    raise
                patch = None
            if len(calls) != len(entries):
                raise ValueError('extra staged draft remains beyond reconstructed terminal result')
            executor.require_consumed()
            for phase, attempt, _, receipt in entries:
                if (_read(Path(temporary) / f'{phase}-{index}-{attempt}.json') != receipt
                        or _read(Path(temporary) / f'{phase}-prompt-{index}-{attempt}.json')
                        != _read(directory / f'{phase}-prompt-{index}-{attempt}.json')):
                    raise ValueError('staged plan/source/receipt hash chain differs from reconstruction')
        last = entries[-1][3]
        if patch is not None:
            if index >= len(controller.state['records']):
                raise ValueError('eligible staged source has no native observation')
            record = controller.state['records'][index]
            child = apply_design_patch(parent, patch)
            if record['patch'] != patch or record['suggestion']['candidate'] != child.to_dict():
                raise ValueError('staged model source/graph differs from native evaluated candidate')
        else:
            final_phase = entries[-1][0]
            if index != len(controller.state['records']) or len(phases[final_phase]) != budgets[final_phase]:
                raise ValueError('staged technical failure did not exhaust exact final phase budget')
        summaries.append({'proposal_index': index, 'draft_count': len(entries),
            'plan_draft_count': len(phases['plan']), 'source_draft_count': len(phases.get('region', [])),
            'authoring_binding_schema': SCHEMA, 'terminal_phase': last['binding']['phase'],
            'status': last['status'] if patch is not None else 'invalid-technical-manifest',
            'saved_terminal_status': last['status'], 'candidate_fingerprint': last.get('candidate_fingerprint'),
            'receipts': [{'phase': r['binding']['phase'], 'attempt': attempt, 'status': r['status'],
                'receipt_sha256': r['receipt_sha256'], 'prompt_sha256': r['prompt_sha256'],
                'errors': r.get('errors', []), 'generated_source_sha256s': r.get('generated_source_sha256s', {})}
                for _, attempt, _, r in entries],
            'structure_only_placeholder_executions': 0,
            'failed_probe_error_preserved_not_reexecuted': executor.failed_error_replayed})
    if not set(range(1, len(controller.state['records']))) <= groups.keys():
        raise ValueError('adaptive native observation lacks staged model provenance')
    if journal.used != set(journal.rows):
        raise ValueError('staged designer journal contains an unaccounted model response')
    return summaries
