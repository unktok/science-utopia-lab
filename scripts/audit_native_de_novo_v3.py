#!/usr/bin/env python3
"""Audit feedback transfer, unchanged generated source and fresh native cost."""
import argparse
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def audit_transfer(directory, loss):
    from scripts.prepare_native_de_novo_design import runtime_tree
    from scripts.audit_native_design_loop import audit
    from scripts.audit_native_feedback_v2 import wire_summary
    from utopia.optimization.native_code_trace import parent_context_provider
    from utopia.optimization.native_transition_data import physical_initial_identity
    from utopia.optimization.loss import loss_spec_sha256
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    from utopia.system.design_patch import apply_design_patch
    from utopia.optimization.native_region_design import compile_region
    from utopia.utils.data_utils import file_sha256
    plan = json.loads((directory / 'plan.json').read_text())
    history = json.loads((directory / 'upstream-snapshot.json').read_text())
    if sha(history) != plan['upstream_snapshot_sha256'] or sha(history['records']) != plan['history_sha256'] or loss_spec_sha256(loss) != plan['loss_spec_sha256']:
        raise ValueError('frozen upstream history or loss changed')
    best = min((r for r in history['records'] if r['observation']['status'] == 'complete'), key=lambda r: r['observation']['loss'])
    parent = SystemSpec.from_dict(best['suggestion']['candidate'])
    if parent.fingerprint != plan['parent_fingerprint'] or best['observation']['loss'] != plan['baseline_loss']:
        raise ValueError('upstream parent/loss identity changed')
    if runtime_tree(plan['source_commit']) != plan['candidate_native_runtime_sha256'] or runtime_tree(plan['upstream_source_commit']) != plan['baseline_native_runtime_sha256'] or plan['candidate_native_runtime_sha256'] != plan['baseline_native_runtime_sha256']:
        raise ValueError('matched comparison has different native execution source')
    contexts = parent_context_provider(Path(plan['upstream_run']) / 'runs', source_commit=plan['upstream_source_commit'])('world.selection', parent, history['records'])
    if [r['bundle_sha256'] for r in contexts] != plan['exact_native_context_bundles']:
        raise ValueError('actual upstream code input identity changed')
    sources = [n.parameters['code_artifact']['source'] for n in parent.mechanisms if n.implementation == 'code.python.v1']
    prompts = []
    for path in sorted(directory.rglob('*prompt-*.json')):
        value = json.loads(path.read_text())
        if sha(value['prompt']) != value['prompt_sha256'] or any(source in value['prompt'] for source in sources):
            raise ValueError('prompt hash/source withholding failure')
        prompts.append({'file': str(path.relative_to(directory)), 'sha256': value['prompt_sha256'], 'utf8_bytes': len(value['prompt'].encode())})
    drafts = []
    paths = (list((directory / 'drafts').glob('free-source-[0-9]*.json'))
        + list(directory.glob('region-draft-[0-9]*.json')) + list((directory / 'drafts').glob('region-[0-9]*.json')))
    for path in sorted(paths):
        value = json.loads(path.read_text())
        if value['receipt_sha256'] != sha({k: v for k, v in value.items() if k != 'receipt_sha256'}):
            raise ValueError('model draft receipt changed')
        drafts.append({'file': str(path.relative_to(directory)), 'receipt_sha256': value['receipt_sha256'],
            'status': value['status'], 'error': value.get('error'), 'ast_same_as_parent': value.get('ast_same_as_parent')})
    result = {'schema': 'scienceutopia.native-de-novo-independent-audit.v3', 'binding': plan,
        'prompts': prompts, 'drafts': drafts, 'status': 'proposal-not-complete',
        'baseline_origin': 'reused-upstream-not-rerun', 'baseline_loss': plan['baseline_loss'],
        'raw_output_root': str(directory), 'scientific_quality_or_algorithm_novelty_claim': False}
    if plan['source_commit'].startswith('616b6ce'):
        # Preserve the old manifest; the model wrapper overrode the per-call
        # requested cap. This is a configuration limitation, not an extra try.
        result['generation_configuration_disclosure'] = {
            'plan_requested_token_cap': plan['max_tokens'], 'effective_wrapper_token_cap': 8192,
            'reason': 'pinned VLLMServerModel.max_tokens_override=8192 superseded requested4096',
            'old_manifest_rewritten': False}
    if not (directory / 'proposal.json').exists():
        if len(drafts) == plan['max_technical_drafts'] and all(r['status'].startswith('invalid-technical') for r in drafts):
            result['status'] = 'technical-drafts-exhausted-no-native-candidate'
        return result
    proposal = json.loads((directory / 'proposal.json').read_text())
    if proposal['binding'] != plan or proposal['receipt_sha256'] != sha({k: v for k, v in proposal.items() if k != 'receipt_sha256'}):
        raise ValueError('proposal provenance changed')
    candidate = apply_design_patch(parent, proposal['patch'])
    if candidate.fingerprint != proposal['candidate_fingerprint'] or SystemSpec.from_dict(json.loads((directory / 'candidate.json').read_text())) != candidate:
        raise ValueError('actual initial native candidate differs from generated proposal')
    if plan['mode'] == 'region-v4':
        from utopia.optimization.native_region_proposer import expand_authoring_manifest, authoring_schema
        successful = [json.loads(p.read_text()) for p in paths if p.name in proposal['evidence']['draft_receipts']]
        successful = [r for r in successful if r['status'] == 'isolated-native-region-passed-not-native-evaluated']
        if len(successful) != 1 or successful[0]['patch'] != proposal['patch'] or proposal['evidence']['authoring_schema_sha256'] != sha(authoring_schema()):
            raise ValueError('joint region generation and transferred patch differ')
        draft = successful[0]
        _, rebuilt = compile_region(parent, expand_authoring_manifest(draft['generated']),
            removed_nodes=['world.selection'], image_id=plan['image_id'])
        if rebuilt != candidate:
            raise ValueError('exact model generated joint region was not mechanically preserved')
        result['new_region_node_ids'] = candidate.metadata['native_design_region']['node_ids']
        result['generated_source_sha256s'] = {n['mechanism_id']: sha(n['python_code']) for n in draft['generated']['nodes']}
        result['generated_protocols'] = sorted({p['artifact_type'] for n in draft['generated']['nodes']
            for direction in ('inputs', 'outputs') for p in n[direction] if p['artifact_type']})
        result['isolated_probe_years'] = [r['year'] for r in draft['runs']]
        previous_hash = None
        for path in sorted(paths):
            receipt = json.loads(path.read_text())
            prompt = json.loads(path.with_name(path.name.replace('region-', 'region-prompt-', 1)).read_text())
            if (receipt['previous_receipt_sha256'] != previous_hash
                    or prompt['previous_receipt_sha256'] != previous_hash
                    or prompt['binding'] != receipt['binding']
                    or prompt['prompt_sha256'] != receipt['prompt_sha256']
                    or receipt['binding']['parent_fingerprint'] != parent.fingerprint
                    or receipt['binding']['history_sha256'] != plan['history_sha256']
                    or receipt['binding']['loss_spec_sha256'] != sha(loss)
                    or receipt['loss'] is not None):
                raise ValueError('joint region technical repair chain changed')
            previous_hash = receipt['receipt_sha256']
    elif plan['mode'] == 'region':
        evidence = proposal['evidence']
        _, rebuilt = compile_region(parent, evidence['manifest'], removed_nodes=['world.selection'], image_id=plan['image_id'])
        if rebuilt != candidate:
            raise ValueError('generated region was not mechanically preserved')
        result['new_region_node_ids'] = candidate.metadata['native_design_region']['node_ids']
        result['generated_source_sha256s'] = {n.mechanism_id: sha(n.parameters['code_artifact']['source']) for n in candidate.mechanisms if n.mechanism_id in result['new_region_node_ids']}
    else:
        successful = [json.loads(p.read_text()) for p in paths if p.name in proposal['evidence']['draft_receipts']]
        successful = [r for r in successful if r['status'] == 'isolated-probes-passed-not-native-evaluated']
        if len(successful) != 1 or successful[0]['patch'] != proposal['patch']:
            raise ValueError('generated source and actual transferred patch differ')
        source = next(n for n in candidate.mechanisms if n.mechanism_id == 'world.selection').parameters['code_artifact']['source']
        if source != successful[0]['generated']['python_code']:
            raise ValueError('model source was edited after generation')
        result['generated_source_sha256s'] = {'world.selection': sha(source)}
        old_source = next(n for n in parent.mechanisms if n.mechanism_id == 'world.selection').parameters['code_artifact']['source']
        result['ast_equal_to_parent'] = ast.dump(ast.parse(source), include_attributes=False) == ast.dump(ast.parse(old_source), include_attributes=False)
    result['proposal_sha256'] = file_sha256(directory / 'proposal.json')
    result['status'] = 'proposal-audited-native-pending'
    evaluation = directory / 'evaluation'
    if not (evaluation / 'completion.json').exists():
        return result
    checked = audit(evaluation, loss, plan['world']['years'])
    if len(checked['rows']) != 1:
        raise ValueError('one transferred candidate budget required')
    state = json.loads((evaluation / 'campaign/native-design-state.json').read_text())
    if SystemSpec.from_dict(state['records'][0]['suggestion']['candidate']) != candidate:
        raise ValueError('fresh native world did not run the actual generated candidate')
    actual_world = state['binding']['world']
    if (state['binding']['seeds'] != plan['seeds'] or any(actual_world[k] != plan['world'][k] for k in ('model_digest', 'corpus_sha256', 'years', 'corpus_years', 'population', 'runtime_seed_binding'))):
        raise ValueError('native evaluation model/corpus/horizon/RNG differs from declared transfer')
    if actual_world['source_commit'] != plan['source_commit']:
        raise ValueError('native evaluation source differs from the proposal source')
    for row in checked['rows']:
        for run in row['runs']:
            run['wire'] = wire_summary(evaluation / 'runs' / run['run_id'], needle='not-a-context-probe', required=True)
            baseline_checkpoint = Path(best['observation']['metadata']['runs'][0]['checkpoint_path']).parent / 'portable_checkpoint_year_0.json.gz'
            current_checkpoint = Path(run['checkpoint']).parent / 'portable_checkpoint_year_0.json.gz'
            a = physical_initial_identity(read_portable_checkpoint(baseline_checkpoint))
            b = physical_initial_identity(read_portable_checkpoint(current_checkpoint))
            if a != b:
                raise ValueError('fresh native evaluation has a different initial physical/RNG state')
            run['initial_physical_state_sha256'] = a
    result.update(status='generated-proposal-and-fresh-native-evaluation-audited', evaluation=checked,
        candidate_loss=checked['rows'][0]['loss'], engineering_objective_improved=checked['rows'][0]['loss'] < plan['baseline_loss'])
    return result


if __name__ == '__main__':
    from utopia.optimization.loss import load_loss_spec
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_transfer(args.directory.resolve(), load_loss_spec(args.loss)), ensure_ascii=False, indent=2, allow_nan=False))
