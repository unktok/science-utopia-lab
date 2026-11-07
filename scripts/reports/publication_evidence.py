"""Project pinned development evidence into comparable paths, not new claims.

No simulator, provider, generated code, raw cache or model is imported/executed.
Source strata stay separate. This is not a raw re-audit, significance test,
benchmark execution, candidate-admission policy or acceptance prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = 'research/publication/evidence-catalog-v1.json'
SCHEMA = 'scienceutopia.publication-evidence-inventory.v1'
SUPPORTED = {'scienceutopia.native-method-paths-audit.v10',
    'scienceutopia.native-objective-redesign-independent-audit.v12',
    'scienceutopia.native-nested-search-independent-audit.v13',
    'scienceutopia.native-warmstart-audit-summary.v45'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON member: ' + key)
        result[key] = value
    return result


def decode(text):
    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid)


def read(path):
    return decode(path.read_text(encoding='utf-8'))


def _path(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('evidence path must be repository-relative')
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError('missing or escaped evidence: ' + relative)
    return target


def _row(row, *, index, arm, source, case, modern=False, numerical=False):
    loss = row.get('loss')
    status = row.get('status', 'complete') if numerical else row['status']
    if status not in ('complete', 'technical-failure', 'generation-failure'):
        raise ValueError('unsupported terminal status')
    if status == 'complete':
        if type(loss) not in (int, float) or not math.isfinite(loss):
            raise ValueError('complete observation requires a finite nonboolean loss')
    elif loss is not None:
        raise ValueError('technical failure cannot carry a numerical loss')
    historical = row.get('origin') == 'shared-historical'
    return {'row_id': f'{case}:{arm}:{index}', 'arm': arm,
        'source_commit': None if historical else source, 'report_source_commit': source,
        'original_historical_source_not_in_row': historical,
        'status': status, 'loss': loss,
        'origin': row.get('origin', 'new-development-observation'),
        'stage': row.get('stage', 'numerical-path' if numerical else 'development'),
        'generation': row.get('generation'),
        'observation_id': row.get('observation_id', row.get('name')),
        'system_fingerprint': row.get('system_fingerprint'),
        'checkpoint_sha256': row.get('checkpoint_sha256'),
        'retrospective_cross_scores': row.get('retrospective_cross_scores' if modern else 'cross_scores'),
        'historical_start': row.get('historical_start'),
        'technical_errors': row.get('technical_errors', []),
        'numeric_loss_is_not_scientific_value': True}


def _best(rows):
    valid = [r for r in rows if r['status'] == 'complete']
    value = min((r['loss'] for r in valid), default=None)
    return {'loss': value, 'tied_row_ids': [r['row_id'] for r in valid if r['loss'] == value]}


def project(data, entry):
    source, schema = data['source_commit'], data['schema']
    arms = {}
    for name, body in data['arms'].items():
        modern = schema == 'scienceutopia.native-warmstart-audit-summary.v45'
        numerical = schema == 'scienceutopia.native-method-paths-audit.v10'
        raw = [body['new_slot']] if modern else body['observations']
        rows = [_row(row, index=i, arm=name, source=source, case=entry['id'],
            modern=modern, numerical=numerical) for i, row in enumerate(raw)]
        fresh = [r for r in rows if r['origin'] != 'shared-historical']
        arms[name] = {'loss_id': (data['objective']['loss_spec']['id'] if numerical
            else body['loss_spec']['id']), 'rows': rows,
            'fresh_loss_path': [r['loss'] for r in fresh],
            'fresh_status_path': [r['status'] for r in fresh],
            'fresh_observed_best': _best(fresh), 'all_recorded_observed_best': _best(rows),
            'historical_references': len(rows) - len(fresh),
            'saved_selection': body.get('selection'),
            'historical_comparison': body.get('comparison') if modern else None}
    physical = (data.get('physical_costs') if schema.endswith('summary.v45') else
        {'physical_researcher_responses': data.get('physical_researcher_responses', data.get('physical_reply_count')),
         'physical_native_worlds': data.get('physical_native_worlds'),
         'replayed_responses': data.get('replayed_response_count')})
    return {'id': entry['id'], 'path': entry['path'], 'schema': schema,
        'source_commit': source, 'content_sha256': data['content_sha256'],
        'classification': data.get('classification'), 'provenance_note': entry['provenance_note'],
        'arms': arms, 'physical_costs': physical, 'original_claims': data.get('claims'),
        'stratum': entry['id'],
        'stratum_note': 'One archived case; same source alone does not establish matched worlds, budgets or independent samples.'}


def build(root=ROOT, *, catalog=CATALOG):
    root = Path(root).resolve()
    catalog_path = _path(root, catalog)
    catalog_bytes = catalog_path.read_bytes()
    config = decode(catalog_bytes.decode('utf-8'))
    if config.get('schema') != 'scienceutopia.publication-evidence-catalog.v1' or not config.get('cases'):
        raise ValueError('explicit nonempty curated evidence catalog required')
    cases, identities, before = [], set(), {}
    for entry in config['cases']:
        if entry['id'] in identities:
            raise ValueError('duplicate evidence case ID')
        identities.add(entry['id'])
        path = _path(root, entry['path'])
        if path in before:
            raise ValueError('duplicate evidence artifact path')
        saved = path.read_bytes()
        before[path] = hashlib.sha256(saved).hexdigest()
        data = decode(saved.decode('utf-8'))
        if (data.get('schema') not in SUPPORTED or data.get('schema') != entry['schema']
                or data.get('source_commit') != entry['source_commit']
                or data.get('content_sha256') != entry['content_sha256']
                or digest({k: v for k, v in data.items() if k != 'content_sha256'}) != entry['content_sha256']):
            raise ValueError('pinned source/schema/content evidence identity differs: ' + entry['id'])
        case = project(data, entry)
        case['file_sha256'] = before[path]
        cases.append(case)
    if catalog_path.read_bytes() != catalog_bytes or any(
            hashlib.sha256(p.read_bytes()).hexdigest() != sha for p, sha in before.items()):
        raise ValueError('evidence changed during read-only projection')
    result = {'schema': SCHEMA, 'catalog_sha256': hashlib.sha256(catalog_bytes).hexdigest(),
        'scope': config['scope'], 'cases': cases,
        'open_comparisons': [
            'Matched free-code/graph search versus parameter-only search under the same objective and oracle budget',
            'Feedback versus no-feedback proposals with designer and scientist costs separately reported',
            'Fresh common-source baselines and selected-system evaluation on unused conditions',
            'Mechanistic analysis of proxy exploitation and whether objective-selected structures differ',
            'A replicated conditional-estimator comparison if an optimizer claim is made'],
        'interpretation': {'fresh_raw_audit': False, 'new_model_calls': 0, 'new_world_executions': 0,
            'generated_code_executions': 0, 'cross_source_method_ranking_established': False,
            'complete_project_inventory': False, 'conference_acceptance_predicted': False,
            'candidate_admission_veto_added': False,
            'numerical_fixtures_are_scientific_results': False},
        'note': 'Open comparisons are research questions for this curated scope, not a merit gate or proof of absence elsewhere.'}
    result['content_sha256'] = digest(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--catalog', default=CATALOG)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = build(args.root, catalog=args.catalog)
    if args.output is not None:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError('publication output already exists; never overwrite evidence')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n')
    print(json.dumps({'cases': [c['id'] for c in result['cases']],
        'content_sha256': result['content_sha256'], 'new_model_calls': 0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
