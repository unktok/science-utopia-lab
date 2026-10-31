#!/usr/bin/env python3
"""Generate free Python institution source with grammar-enforced metadata.

The native attachment is trusted plumbing, NOT model-invented wiring. Source
algorithms and JSON memory are generated freely and isolated-probed on actual
saved native snapshots. No host execution or fabricated native observation.
"""
import argparse
import json
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-draft', type=Path, help='reuse exact preserved model source; only metadata compilation changes')
    args = parser.parse_args()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT): raise ValueError('clean pinned source required')
    from utopia.models.models import VLLMServerModel
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec, MechanismSpec, MechanismFamily, PortSpec, ChannelKind
    from utopia.system.code_mechanisms import DockerCodeExecutor, CODE_SCHEMA, CODE_IMPLEMENTATION
    from utopia.system.native_examples import connect_native_institution
    from utopia.system.native_kernel import WORLD_ARTIFACT
    from utopia.system.design_patch import digest, make_patch, apply_design_patch
    from utopia.utils.data_utils import write_json_atomic
    import requests
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    saved = json.loads(args.history.read_text())
    baseline = saved['records'][0]
    parent = SystemSpec.from_dict(baseline['suggestion']['candidate'])
    evidence = baseline['observation']['metadata']['runs'][0]
    run_root = args.history.parent.parent / 'runs' / evidence['run_id'] / 'simulation/checkpoints/native-design'
    worlds = []
    for year in (1, 2, 4):
        state = read_portable_checkpoint(run_root / f'portable_checkpoint_year_{year}.json.gz')
        worlds.append({'year': year, 'ecosystem': state['ecosystem_data'], 'papers': state['paper_tracker'],
                       'conferences': state['conference_system'], 'year_results': state['yearly_results'][-1]})
    tags = requests.get('http://127.0.0.1:11434/api/tags', timeout=10).json()
    revision = next(m['digest'] for m in tags['models'] if m['name'] == 'qwen3:8b')
    model = VLLMServerModel('qwen3:8b', base_url='http://127.0.0.1:11434/v1', server_backend='ollama',
        run_seed=1301, model_revision=revision, thinking_override=False, max_tokens_override=3072,
        request_timeout=180, sdk_max_retries=0)
    model.response_cache = CompletedResponseCache(args.output / 'responses.sqlite', binding={
        'protocol': 'native-structured-source-proposal-v1', 'cell': parent.fingerprint, 'model': 'qwen3:8b',
        'model_revision': revision, 'seed': 1301, 'corpus_sha256': saved['binding']['world']['corpus_sha256'],
        'science_config': {'source_commit': source, 'history_sha256': digest(baseline),
                           'thinking_override': False, 'max_tokens': 3072,
                           'reused_draft_sha256': digest(json.loads(args.reuse_draft.read_text())) if args.reuse_draft else None}})
    executor = DockerCodeExecutor()
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['institution_id', 'label', 'protocol', 'source'],
        'properties': {'institution_id': {'type': 'string'}, 'label': {'type': 'string'},
                       'protocol': {'type': 'string'}, 'source': {'type': 'string'}}}
    prompt = ("Write an original executable scientific institution as free Python source, not a selection from a rule menu. "
        "Only its attachment is supplied: it sees the actual world after publication and sends observation-derived messages "
        "to real researchers, affecting their later prompts. Keep their fixed LLM/personas unchanged. "
        "Return JSON {institution_id,label,protocol,source}; IDs are simple lowercase-hyphenated strings. "
        "source defines def step(context). Standard library only; no import utopia/scienceutopia/third-party packages. "
        "EXACT input: world=context['inputs']['observations'][0]['payload']; do NOT access payload['world']. "
        "world has year,ecosystem:{agents:[{id,type,resources,is_active,can_author,...}]},papers:{papers:[{id,title,author_id,review_history,...}]}. "
        "Some years have no papers/reviews. Choose your own institutional algorithm and JSON memory; prior memory=context['state']. "
        "EXACT return: {'outputs':{'messages':[{'payload':{YOUR_FIELDS},'actor_ids':[EXISTING_AUTHOR_ID],'artifact_ids':[]},...]},'state':{YOUR_MEMORY}}. "
        "Actor IDs must come from world['ecosystem']['agents'] entries whose can_author is true. An author_id can be a string or list. "
        "Messages must be concise objects derived from actual observations, not made-up IDs or measurements. "
        "Empty messages list is allowed when appropriate. Do not assume other services or context keys exist. "
        "The outer engineering target is negative accepted-decision count (previous native loss -4), not scientific quality. "
        "Do not claim observed improvement. Institution's mechanism source is yours to invent; plumbing is not your task here.")
    original = prompt
    try:
        for attempt in range(3):
            if attempt == 0 and args.reuse_draft:
                draft = json.loads(args.reuse_draft.read_text())['draft']
            else:
                draft, _ = model.generate(prompt=prompt, seed_ctx=('structured_native_source', attempt),
                    response_format={'type': 'json_schema', 'json_object': {'name': 'native_institution', 'schema': schema}})
            receipt = {'attempt': attempt, 'draft': draft, 'prompt_sha256': digest(prompt), 'source_commit': source, 'loss': None}
            try:
                artifact = {'schema': CODE_SCHEMA, 'label': draft['label'], 'source': draft['source'],
                    'inputs': {'observations': {'type': 'object'}}, 'outputs': {'messages': {'type': 'object'}}, 'state_schema': {'type': 'object'}}
                def identifier(value, prefix):
                    return value if re.fullmatch(r'[a-z][a-z0-9_.-]{0,63}', value) else prefix + digest(value)[:16]
                node_id = identifier(draft['institution_id'], 'generated-')
                protocol_id = identifier(draft['protocol'], 'generated-message-')
                receipt['compiled_identifiers'] = {'institution_id': node_id, 'protocol_id': protocol_id}
                node = MechanismSpec(node_id, MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
                    inputs=(PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
                    outputs=(PortSpec('messages', ChannelKind.ARTIFACT, protocol_id, required=False),),
                    parameters={'code_artifact': artifact, 'runtime_image_id': executor.image_id})
                child = connect_native_institution(parent, node, phase=191, researcher_output='messages')
                document = child.to_dict()
                patch = make_patch(parent, [{'op': 'replace', 'path': '/' + k, 'value': v} for k, v in document.items() if parent.to_dict()[k] != v], rationale='LLM-generated source; host-provided native attachment')
                apply_design_patch(parent, patch)
                memory, probes = {}, []
                for world in worlds:
                    result = executor.execute(artifact, {'period': world['year'], 'phase': 191, 'random_seed': 1301,
                        'state': memory, 'parameters': {}, 'inputs': {'observations': [{'payload': world, 'actor_ids': [], 'artifact_ids': []}]}})
                    authors = {a['id'] for a in world['ecosystem']['agents'] if a.get('can_author')}
                    for record in result.result['outputs']['messages']:
                        if not record.get('actor_ids') or not set(record['actor_ids']) <= authors:
                            raise ValueError('message lacks actual author recipient IDs')
                    memory = result.result['state']
                    probes.append({'year': world['year'], 'messages': len(result.result['outputs']['messages']), **result.receipt})
                receipt.update(status='isolated-source-probes-passed-not-native-rollout', candidate_fingerprint=child.fingerprint, probes=probes)
            except Exception as error:
                receipt.update(status='invalid', error=str(error)[:3000])
                write_json_atomic(args.output / f'attempt-{attempt}.json', receipt, allow_nan=False)
                prompt = original + '\nYOUR ACTUAL LAST SOURCE:\n' + json.dumps(draft) + '\nACTUAL VALIDATION/ISOLATED EXECUTION ERROR:\n' + str(error)[:3000]
                continue
            write_json_atomic(args.output / f'attempt-{attempt}.json', receipt, allow_nan=False)
            write_json_atomic(args.output / 'candidate.json', child.to_dict(), allow_nan=False)
            write_json_atomic(args.output / 'proposal.json', {'source_commit': source, 'model_digest': revision,
                'history_source_commit': saved['binding']['world']['source_commit'], 'history_sha256': digest(baseline),
                'candidate_fingerprint': child.fingerprint, 'patch': patch, 'status': receipt['status'], 'loss': None,
                'code_origin': 'LLM-generated', 'wiring_origin': 'trusted generic native attachment, not LLM-invented wiring'}, allow_nan=False)
            print(child.fingerprint)
            return
        raise ValueError('three actual source/probe repairs failed; no loss assigned')
    finally:
        model.response_cache.close()


if __name__ == '__main__': main()
