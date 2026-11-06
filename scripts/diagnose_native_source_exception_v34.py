#!/usr/bin/env python3
"""Limited read-only original-source component proof, NOT a full queue/UI audit.

Run this diagnostic from a separate checkout. Imports and all native/interpreter
checks use the immutable original source, while this script's own hash is stated
separately. A missing terminal journal is never created or treated as complete.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def inventory(root):
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('raw evidence cannot contain symlinks')
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def analyze(root, source, expected_source):
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() != expected_source:
        raise ValueError('original source HEAD differs')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=source, text=True).strip():
        raise ValueError('original source worktree is dirty')
    sys.path.insert(0, str(source))
    from scripts.analyze_native_staged_search_v15 import (
        source_proofs, read, _hashed_record, _transport, audit_native_campaign)
    from utopia.optimization import native_staged_author_v15 as author
    from utopia.system.design_patch import digest

    before = inventory(root)
    ended = read(root / 'writer.ended.json')
    if ended['source_commit'] != expected_source or ended['status'] not in {'exited', 'aborted'}:
        raise ValueError('original writer is not terminal at expected source')
    plan = read(root / 'plan.json')
    if plan['source_commit'] != expected_source:
        raise ValueError('plan source differs')
    sources = source_proofs(expected_source, plan['classification'], protocol_path=plan['protocol'])
    searches, runs = read(root / 'searches.json'), {}
    provider = plan['provider_binding']
    for entry in plan['runs']:
        request, runtime = entry['request'], entry['runtime_plan']
        directory = root / 'queue' / searches[entry['id']]
        native = audit_native_campaign(directory, method=request['method'],
            world={'source_commit': expected_source, **provider,
                'runtime_seed_binding': plan['runtime_seed_binding'], 'years': request['years']},
            classification=plan['classification'], loss=request['loss_spec'],
            initial_system=plan['initial_system'], expected_budget=request['native_budget'],
            experiment={'request_sha256': digest(request), 'loss_spec': request['loss_spec']},
            campaign_world={'source_commit': expected_source, **provider,
                'request_sha256': digest(request), 'search_plan_sha256': digest(runtime),
                'years': request['years'], 'population': 'five-independent-balanced-researchers',
                'origin': runtime['origin']})
        if not native['terminal'] or native['pending']:
            raise ValueError('component campaign is not terminal')
        proofs = []
        expected_dirs = set()
        for record in native['records']:
            cell = directory / 'authoring' / ('generation-' + record['request_sha256'])
            expected_dirs.add(cell)
            binding = read(cell / 'request.json'); _hashed_record(binding, field='binding_sha256')
            if any(binding['settings'][k] != request['designer'][k] for k in ('max_steps', 'max_tokens')):
                raise ValueError('designer settings differ from the frozen plan')
            class NoDispatch:
                def generate(self, **kwargs):
                    raise AssertionError('diagnostic must never dispatch')
            generator = author.StagedVocabularyGenerator(NoDispatch(), cell.parent,
                image_id=binding['image_id'], provider_binding=provider,
                max_steps=binding['settings']['max_steps'], max_tokens=binding['settings']['max_tokens'])
            if generator._binding(record['request']) != binding:
                raise ValueError('original generation binding differs')
            state, steps, physical = author.initial_draft(record['request']), [], []
            starts = sorted(cell.glob('step-*.started.json'))
            completes = sorted(cell.glob('step-*.completed.json'))
            if len(starts) != len(completes) or len(starts) > binding['settings']['max_steps']:
                raise ValueError('component diagnostic does not infer unknown dispatch results')
            for index, start_path in enumerate(starts):
                if start_path.name != f'step-{index:02d}.started.json':
                    raise ValueError('non-contiguous original prefix')
                start = read(start_path)
                prompt = author.build_prompt(record['request'], state, steps,
                    image_id=binding['image_id'], binding_sha256=binding['binding_sha256'], settings=binding['settings'])
                if generator._started(binding, index, prompt, state, steps, start['started_utc']) != start:
                    raise ValueError('original prompt/intent prefix differs')
                step = read(cell / f'step-{index:02d}.completed.json'); _hashed_record(step)
                generator._verify_step(step, start_path, state, record['request'], binding)
                if step['transition'] is not None:
                    state, transition = author.transition(state, step['model_reply']['output'], record['request'],
                        binding_sha256=binding['binding_sha256'], provider_binding=provider)
                    if transition != step['transition']:
                        raise ValueError('original prefix transition differs')
                transport = step['model_reply'].get('transport', {})
                physical.append({'step': index, 'status': step['status'],
                    'evidence': _transport(step, start, binding, plan['classification']),
                    'model_call_seconds': step.get('model_call_seconds'),
                    **{k: transport.get(k) for k in ('elapsed_seconds', 'prompt_tokens', 'completion_tokens')}})
                steps.append(step)
            if (cell / 'response.json').exists():
                definition = author.replay_staged_generation(cell, expected_request=record['request'],
                    expected_provider_binding=provider)
                if definition != record['definition']:
                    raise ValueError('original terminal definition differs')
                terminal = {'status': 'original-terminal-replayed',
                    'result_status': read(cell / 'response.json')['status']}
            else:
                expected = record['definition'].get('generation_failure')
                if not expected or record['draws'] or record['observations']:
                    raise ValueError('missing terminal is not the recorded pre-world source exception')
                try:
                    author.build_prompt(record['request'], state, steps,
                        image_id=binding['image_id'], binding_sha256=binding['binding_sha256'], settings=binding['settings'])
                except Exception as error:
                    if type(error).__name__ != expected['type'] or str(error) != expected['message']:
                        raise ValueError('source exception is not exactly reproduced') from error
                    terminal = {'status': 'original-source-exception-reproduced',
                        'type': type(error).__name__, 'message': str(error),
                        'original_terminal_journal_present': False, 'terminal_journal_created': False}
                else:
                    raise ValueError('original expected source exception did not recur')
            proofs.append({'request_sha256': record['request_sha256'], 'terminal': terminal,
                'physical_designer_calls': physical})
        if set((directory / 'authoring').glob('generation-*')) != expected_dirs:
            raise ValueError('extra or omitted generation directories')
        runs[entry['id']] = {'native_component': native, 'designer_prefix_components': proofs}
    if inventory(root) != before:
        raise ValueError('raw evidence changed during diagnostic')
    result = {'scope': 'limited original-source native/prefix/exception component diagnostic; NOT full queue/UI audit',
        'original_full_audit_pass_claimed': False, 'new_model_calls': 0, 'new_worlds': 0,
        'source_commit': expected_source, 'source_proofs': sources, 'writer_ended': ended,
        'diagnostic_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'raw_inventory': before, 'raw_inventory_sha256': digest(before), 'runs': runs}
    result['content_sha256'] = digest(result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--source-worktree', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.run.resolve(), args.output.resolve()
    if output == root or root in output.parents or output.exists():
        raise ValueError('diagnostic output must be new and outside immutable raw evidence')
    result = analyze(root, args.source_worktree.resolve(), args.expected_source)
    from utopia.utils.data_utils import write_json_atomic
    write_json_atomic(output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({'content_sha256': result['content_sha256'], 'scope': result['scope']}))
