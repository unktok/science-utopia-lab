#!/usr/bin/env python3
"""Explicit finite real-backend calibration. Never dispatches a scientific world."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from utopia.optimization.native_designer_preflight import require_certificate, run_calibration
    from utopia.optimization.native_jobs import pinned_revision
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('run', 'verify'))
    parser.add_argument('--provider-config', type=Path, required=True, help='operator-owned {provider_binding}')
    parser.add_argument('--request', type=Path, help='actual parent authoring request JSON, run only')
    parser.add_argument('--output', type=Path, help='new immutable evidence directory, run only')
    parser.add_argument('--certificate', type=Path, help='existing certificate, verify only')
    parser.add_argument('--protocol', choices=('staged-v15', 'one-shot-v14'), default='staged-v15')
    parser.add_argument('--scope', choices=('literal-controls-v16', 'execution-readiness-v39'),
        default='literal-controls-v16', help='prospective technical criteria; never reinterpret old evidence')
    args = parser.parse_args()
    provider = json.loads(args.provider_config.read_text())['provider_binding']
    if args.mode == 'verify':
        result = require_certificate(args.certificate, provider, protocol=args.protocol, scope=args.scope)
    else:
        source = pinned_revision(ROOT)  # actual calls only from a clean, source-pinned checkout
        if args.request is None or args.output is None:
            parser.error('run requires --request and a fresh --output')
        request = json.loads(args.request.read_text())
        request = request.get('request', request)
        result = run_calibration(args.output, request=request, provider=provider, protocol=args.protocol,
            source_commit=source, scope=args.scope)
        print(json.dumps({'all_controls_passed': result['all_controls_passed'],
            'calls': len(result['records']), 'certificate_sha256': result['content_sha256']}), flush=True)
        if not result['all_controls_passed']:
            return 1
        result = require_certificate(args.output / 'certificate.json', provider, protocol=args.protocol, scope=args.scope)
    print(json.dumps(result), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
