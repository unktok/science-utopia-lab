#!/usr/bin/env python3
"""At most two seven-step unforced sessions, no native worlds/source execution."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.native_designer_preflight import require_certificate
    from utopia.optimization.native_staged_author_v15 import make_local_staged_generator
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import write_json_atomic
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request', type=Path, action='append', required=True)
    p.add_argument('--provider-config', type=Path, required=True)
    p.add_argument('--certificate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = pinned_revision(ROOT)
    if len(args.request) != 2:
        p.error('exactly two predeclared objective-arm requests required')
    provider = json.loads(args.provider_config.read_text())['provider_binding']
    checked = require_certificate(args.certificate, provider, protocol='staged-v15')
    requests = []
    for path in args.request:
        body = json.loads(path.read_text())
        body = body.get('request', body)
        if body.get('generation') != 0 or body.get('history') or body.get('observations'):
            raise ValueError('use first-generation requests; no inherited/cross-arm observation')
        requests.append(body)
    args.output.mkdir(parents=True, exist_ok=False)
    plan = {'source_commit': source, 'requests': requests, 'certificate_sha256': checked['certificate_sha256'],
        'max_POSTs': 14, 'max_steps_per_arm': 7, 'max_tokens_per_call': 2048, 'native_worlds': 0,
        'source_execution': False, 'forced_edits': False, 'temperature': .2, 'network_retries': 0}
    write_json_atomic(args.output / 'plan.json', plan, sort_keys=True, allow_nan=False)
    results = []
    for index, request in enumerate(requests):
        generator = make_local_staged_generator(args.output / f'arm-{index}', image_id=provider['image_id'],
            provider_binding=provider, max_steps=7, max_tokens=2048,
            inference_lock=args.output.parent / 'interface-calibration.lock', preflight_certificate=args.certificate)
        result = {'arm': index, 'request_sha256': digest(request), 'finished': False}
        try:
            design = generator(request)
            if not isinstance(design, dict):
                raise ValueError('finite session ended without an explicit valid finish')
            result.update(finished=True, definition=design)
        except Exception as error:
            result['error'] = type(error).__name__ + ': ' + str(error)
        results.append(result)
        write_json_atomic(args.output / 'results.json', results, sort_keys=True, allow_nan=False)
        print(json.dumps({key: value for key, value in result.items() if key != 'definition'}), flush=True)
    return 0 if all(result['finished'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
