"""Stage a fixed content instrument on CLOSED native records; zero inference.

The original-source child reads checksum-bound historical checkpoints. The
current parent validates complete content/prompt bounds without loading models.
Raw abstracts remain in the caller's ignored output, not the compact summary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def scientific_inputs(run, audit_path, output):
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.native_numeric_designer import checked, save
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256
    source = Path.cwd(); run = Path(run).resolve(); output = Path(output).resolve()
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(source):
        raise ValueError('fresh historical readout outside scientific source/raw required')
    audit_sha = file_sha256(audit_path)
    audit = checked(json.loads(Path(audit_path).read_text()))
    plan = checked(json.loads((run / 'plan.json').read_text()))
    if (audit['schema'] != 'scienceutopia.pre-scale-search-audit.v1'
            or audit['source_commit'] != pinned_revision(source) or plan['source_commit'] != audit['source_commit']
            or audit['plan_sha256'] != plan['content_sha256'] or not (run / 'complete.json').exists()):
        raise ValueError('closed exact original-source historical audit/plan required')
    cells = {}
    for path in run.glob('**/worlds/*'):
        if path.is_dir():
            if path.name in cells:
                raise ValueError('ambiguous physical native cell')
            cells[path.name] = path
    accepted = []; worlds = []; skipped = []
    for world in audit['worlds']:
        proof = world['physical_proof']
        if proof['status'] != 'complete':
            skipped.append({'identity': world['identity'], 'status': world['status']})
            continue
        cell = cells[world['identity'] + '-s' + str(world['seed'])]
        paths = list(cell.rglob('portable_checkpoint_year_4.json.gz'))
        if len(paths) != 1 or file_sha256(paths[0]) != proof['checkpoint_sha256']:
            raise ValueError('historical checkpoint differs from full audit')
        checkpoint = read_portable_checkpoint(paths[0])
        if checkpoint['year'] != 4 or checkpoint['native_system']['spec'] != world['system']:
            raise ValueError('historical world horizon/system differs')
        rows = []
        for paper in checkpoint['paper_tracker']['papers']:
            for index, decision in enumerate(paper['review_history']):
                if decision.get('decision') == 'accept':
                    rows.append({'physical_world': world['identity'], 'paper_id': paper['id'],
                        'year': decision['year'], 'decision_index': index,
                        'content': {k: paper.get(k) for k in ('title', 'abstract', 'topics')}})
        measured = proof['measurement']['metrics']['native.accepted_decisions']
        if measured['status'] != 'measured' or len(rows) != measured['value']:
            raise ValueError('content decision count differs from original measurement')
        accepted.extend(rows)
        worlds.append({'identity': world['identity'], 'seed': world['seed'],
            'checkpoint_sha256': file_sha256(paths[0]), 'accepted_decisions': len(rows)})
    if pinned_revision(source) != plan['source_commit'] or file_sha256(audit_path) != audit_sha:
        raise ValueError('historical source changed during readout')
    save(output, {'schema': 'scienceutopia.common-content-staging.v1.inputs',
        'scientific_source_commit': plan['source_commit'], 'plan_sha256': plan['content_sha256'],
        'historical_full_audit_content_sha256': audit['content_sha256'],
        'historical_full_audit_file_sha256': audit_sha,
        'worlds': worlds, 'skipped_partial_worlds': skipped, 'accepted_decisions': accepted,
        'new_model_calls': 0, 'new_native_worlds': 0, 'full_raw_audit_repeated': False})


def project(inputs, contract):
    from utopia.optimization.common_content_observer import content, request_for
    from utopia.optimization.native_numeric_designer import checked
    from utopia.system.design_patch import digest
    checked(inputs); checked(contract)
    by_content = {}; errors = []
    for row in inputs['accepted_decisions']:
        projected = {k: row['content'].get(k) for k in ('title', 'abstract', 'topics')}
        key = digest(projected)
        if key in by_content:
            continue
        try:
            value = content(projected)
            prompts = []
            for critic in range(contract['critics']):
                identity, _, wire = request_for(contract, value, critic)
                prompts.append({'critic': critic, 'request_key': identity,
                    'request_wire_sha256': wire['request_wire_sha256'],
                    'request_utf8_bytes': len(wire['request_wire_utf8'].encode())})
            by_content[key] = {'status': 'eligible', 'prompts': prompts}
        except (ValueError, KeyError, TypeError) as error:
            by_content[key] = {'status': 'unavailable', 'error_type': type(error).__name__, 'error': str(error)}
            errors.append(key)
    sizes = [p['request_utf8_bytes'] for row in by_content.values() if row['status'] == 'eligible' for p in row['prompts']]
    result = {'schema': 'scienceutopia.common-content-staging.v1',
        'input_content_sha256': inputs['content_sha256'], 'contract_sha256': contract['content_sha256'],
        'scientific_source_commit': inputs['scientific_source_commit'],
        'historical_full_audit_content_sha256': inputs['historical_full_audit_content_sha256'],
        'complete_physical_worlds': len(inputs['worlds']), 'partial_worlds_skipped': len(inputs['skipped_partial_worlds']),
        'accepted_decision_records': len(inputs['accepted_decisions']), 'unique_contents': len(by_content),
        'eligible_unique_contents': sum(r['status'] == 'eligible' for r in by_content.values()),
        'unavailable_unique_contents': len(errors), 'contents': by_content,
        'minimum_prompt_utf8_bytes': min(sizes) if sizes else None,
        'maximum_prompt_utf8_bytes': max(sizes) if sizes else None,
        'all_eligible_panel_posts_upper_bound': len(sizes),
        'new_model_calls': 0, 'new_native_worlds': 0, 'scores_observed': False,
        'scope': 'Historical accepted contents only. Eligibility and byte bounds, not token capacity, real-backend readiness, scientific quality or new objective optimization.'}
    result['content_sha256'] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'audit', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--frozen-source', type=Path)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        scientific_inputs(args.run, args.audit, args.output); return
    from utopia.optimization.common_content_observer import make_contract
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.native_numeric_designer import checked, save
    from utopia.optimization.native_scientist_load_v38 import SCIENTIST_DIGEST
    source = Path(__file__).resolve().parents[2]; revision = pinned_revision(source)
    if (args.frozen_source is None or args.output.exists()
            or args.output.resolve().is_relative_to(args.run.resolve())
            or args.output.resolve().is_relative_to(args.frozen_source.resolve())):
        raise ValueError('explicit frozen source and fresh output required')
    args.output.mkdir(parents=True)
    command = [sys.executable, '-c', 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(Path(__file__).resolve()), '--worker',
        '--run', str(args.run.resolve()), '--audit', str(args.audit.resolve()),
        '--output', str((args.output / 'contents.json').resolve())]
    result = subprocess.run(command, cwd=args.frozen_source.resolve(),
        env={**os.environ, 'PYTHONHASHSEED': '42'}, timeout=900, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
    inputs = checked(json.loads((args.output / 'contents.json').read_text()))
    provider = {'model': 'qwen3:8b', 'model_digest': SCIENTIST_DIGEST}
    # Expected existing backend, NOT a fresh server or token-capacity check.
    contract = make_contract(source_commit=revision, provider=provider,
        backend={**provider, 'ollama_version': '0.33.3'},
        maximum_posts=max(1, len(inputs['accepted_decisions']) * 3), critics=3)
    summary = project(inputs, contract)
    if pinned_revision(source) != revision:
        raise ValueError('instrument source changed while staging historical inputs')
    save(args.output / 'contract.json', {k: v for k, v in contract.items() if k != 'content_sha256'})
    save(args.output / 'staging.json', {k: v for k, v in summary.items() if k != 'content_sha256'})
    print(json.dumps({k: summary[k] for k in ('content_sha256', 'accepted_decision_records',
        'unique_contents', 'eligible_unique_contents', 'unavailable_unique_contents', 'maximum_prompt_utf8_bytes',
        'all_eligible_panel_posts_upper_bound', 'new_model_calls')}), flush=True)


if __name__ == '__main__':
    main()
