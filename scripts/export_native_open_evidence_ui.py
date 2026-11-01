#!/usr/bin/env python3
"""Validate and export one completed v7 evidence artifact for the local UI.

Run with the project-approved Python, never Apple/Xcode Python:
  ~/.local/bin/python3 scripts/export_native_open_evidence_ui.py PATH/evidence.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = 'scienceutopia.native-open-integrated-pilot.v7'
FALSE_CLAIMS = ('scripted_researcher_HTTP', 'held_out', 'causal_institutional_benefit', 'scientific_value',
                'full_native_world_pathwise_autograd', 'designer_improvement_established',
                'external_authorship_authenticated')
COMPLETE_FIELDS = ('checkpoint_sha256', 'open_domain', 'process_receipts', 'events', 'system', 'year',
                   'boundary_coverage', 'conditional_backward')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate(value):
    if not isinstance(value, dict) or value.get('schema') != SCHEMA or value.get('ui_fixture'):
        raise ValueError('only an actual native-open-integrated-pilot.v7 artifact may be exported')
    claimed = value.get('content_sha256')
    payload = dict(value)
    payload.pop('content_sha256', None)
    if claimed != digest(payload):
        raise ValueError('source content_sha256 differs from exact evidence payload')
    claims = value.get('claims', {})
    if (value.get('status') not in ('in-progress', 'complete', 'budget-complete-with-failures')
            or value.get('configured_researcher_provider') != 'qwen3:8b'
            or type(value.get('physical_reply_count')) is not int
            or type(value.get('complete_native_worlds')) is not int):
        raise ValueError('pilot status, configured provider and physical counts must remain explicit')
    if (claims.get('live_fixed_Qwen_researchers') is not (value['physical_reply_count'] > 0)
            or claims.get('engineering_count_loss') is not True):
        raise ValueError('live researcher claim must follow physical replies; engineering objective must remain explicit')
    response_total = sum(cache.get('outcomes', {}).get('response', 0)
        for cache in value.get('physical_response_caches', []))
    if value['physical_reply_count'] != response_total:
        raise ValueError('physical reply count differs from response caches')
    if value['status'] == 'complete' and value['complete_native_worlds'] != 4:
        raise ValueError('complete pilot must contain all four native worlds')
    if any(claims.get(key) is not False for key in FALSE_CLAIMS):
        raise ValueError('unsupported positive scientific/derivative/authorship claim')
    for index, row in enumerate(value.get('observations', [])):
        observation = row.get('observation')
        complete = isinstance(observation, dict) and observation.get('status') == 'complete'
        if not complete:
            if isinstance(observation, dict) and observation.get('loss') is not None:
                raise ValueError(f'incomplete observation {index} has a numerical loss')
            if any(key in row for key in COMPLETE_FIELDS):
                raise ValueError(f'incomplete observation {index} has complete-only endpoint fields')
        else:
            if type(observation.get('loss')) not in (int, float):
                raise ValueError(f'complete observation {index} lacks a numerical loss')
            if any(key not in row for key in COMPLETE_FIELDS):
                raise ValueError(f'complete observation {index} lacks endpoint evidence')
            backward = row['conditional_backward']
            coverage = row['boundary_coverage']
            if (backward.get('native_loss_gradient_verified') is not False
                    or backward.get('full_native_world_autograd') is not False
                    or coverage.get('full_native_world_autograd') is not False):
                raise ValueError('conditional derivative boundary was overstated')
            for report in (coverage, backward):
                if report.get('status') == 'failed-diagnostic' and (not report.get('error_type') or not report.get('error')):
                    raise ValueError('failed derivative diagnostic must retain its actual error')
    if value['complete_native_worlds'] != sum(r.get('observation', {}).get('status') == 'complete'
            for r in value.get('observations', []) if isinstance(r.get('observation'), dict)):
        raise ValueError('complete native-world count differs from observations')
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path,
        default=Path(__file__).resolve().parents[1] / 'game-ui-v2/public/data/native-open-integrated-v7.json')
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    evidence = validate(json.loads(source_bytes))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Preserve the independently audited compact artifact byte-for-byte after
    # validation; do not inflate or semantically rewrite it in the UI export.
    args.output.write_bytes(source_bytes)
    print(json.dumps({'schema': SCHEMA, 'source': str(args.source.resolve()),
        'source_file_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'content_sha256': evidence['content_sha256'], 'output': str(args.output.resolve())}, indent=2))


if __name__ == '__main__':
    main()
