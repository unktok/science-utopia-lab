"""Digest-verified local tokenizer/template counts, NOT backend observations."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


def measure(plan_file, models_root):
    from tokenizers import Tokenizer
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    plan_file, models_root = Path(plan_file), Path(models_root)
    p = checked(json.loads(plan_file.read_text())); provider = p['provider']
    model, tag = provider['model'].split(':', 1)
    manifest = models_root/'manifests/registry.ollama.ai/library'/model/tag
    if file_sha256(manifest) != provider['model_digest']:
        raise ValueError('literal used local model manifest differs')
    layers = {r.get('name'): r for r in json.loads(manifest.read_text())['layers'] if 'name' in r}
    bodies, inputs = {}, {str(plan_file): file_sha256(plan_file), str(manifest): file_sha256(manifest)}
    for name in ('tokenizer.json', 'tokenizer_config.json', 'config.json'):
        item = layers[name]; path = models_root/'blobs'/item['digest'].replace(':','-')
        raw = path.read_bytes()
        if len(raw) != item['size'] or hashlib.sha256(raw).hexdigest() != item['digest'].split(':')[1]:
            raise ValueError('used local tokenizer/config blob differs: '+name)
        bodies[name] = raw; inputs[str(path)] = file_sha256(path)
    tokenizer = Tokenizer.from_str(bodies['tokenizer.json'].decode())
    config = json.loads(bodies['tokenizer_config.json'])
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    def fail(message): raise ValueError(message)
    env.globals['raise_exception'] = fail
    template = env.from_string(config['chat_template']); rows = []
    for frame in p['frames']:
        payload = json.loads(frame['wire_utf8'])
        text = template.render(messages=payload['messages'], tools=payload.get('tools'),
            add_generation_prompt=True, enable_thinking=payload['think'],
            bos_token=config.get('bos_token'), eos_token=config.get('eos_token'))
        tokens = tokenizer.encode(text, add_special_tokens=False).ids
        reserved = payload['options']['num_predict']; context = payload['options']['num_ctx']
        rows.append({'arm': frame['arm'], 'wire_sha256': digest(frame['wire_utf8']),
            'wire_utf8_bytes': len(frame['wire_utf8'].encode()), 'local_template_utf8_sha256': digest(text),
            'local_token_ids_sha256': digest(tokens), 'local_template_tokens': len(tokens),
            'requested_context_tokens': context, 'reserved_output_tokens': reserved,
            'prompt_plus_reserved': len(tokens)+reserved,
            'reservation_fits_requested_context': len(tokens)+reserved <= context,
            'prospective_65536_context_would_fit': len(tokens)+reserved <= 65536})
    result = {'schema': 'scienceutopia.longitudinal-offline-token-counts.v1',
        'classification': 'local-tokenizer-template-analysis-not-backend-rendering-or-counts',
        'input_plan_source_commit': p['source_commit'], 'reader_file_sha256': file_sha256(__file__),
        'input_files': inputs, 'provider': provider,
        'package_versions': {n: version(n) for n in ('tokenizers','jinja2')},
        'rendering_arguments': {'add_generation_prompt': True, 'enable_thinking': False,
            'tokenizer_add_special_tokens': False},
        'local_config_nominal_max_positions': json.loads(bodies['config.json'])['text_config']['max_position_embeddings'],
        'rows': rows, 'new_model_calls': 0, 'original_input_modified': False,
        'backend_token_counts_measured': False, 'backend_tokenizer_rendering_independently_verified': False,
        'real_readiness_proved': False, 'scientific_gain_claimed': False, 'publication_ready': False}
    if any(file_sha256(Path(path)) != sha for path, sha in inputs.items()):
        raise ValueError('local artifact/plan changed during measurement')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True); parser.add_argument('--models-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result = save(args.output, measure(args.plan,args.models_root))
    print(json.dumps({'content_sha256': result['content_sha256'], 'rows': result['rows'], 'new_model_calls': 0}))


if __name__ == '__main__': main()
