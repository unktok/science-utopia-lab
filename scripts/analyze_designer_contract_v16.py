"""Read-only transport/accounting summary for the finite V16 repair verification."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.system.design_patch import digest
from utopia.optimization.native_search_generator_v14 import _strict_json
from utopia.utils.data_utils import write_json_atomic


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(root):
    rows, assets, certificates, planning_results = [], {}, [], []
    for name in ('staged-a1', 'staged-a2', 'staged-a3', 'staged-a4', 'staged-a5'):
        directory = root / name
        if not directory.exists():
            continue
        certificate = _strict_json((directory / 'certificate.json').read_text())
        if certificate['content_sha256'] != digest({k: v for k, v in certificate.items() if k != 'content_sha256'}):
            raise ValueError('certificate content differs')
        if _strict_json((directory / 'plan.json').read_text()) != certificate['plan']:
            raise ValueError('plan/certificate differs')
        completed = sorted(directory.glob('*.completed.json'))
        started = sorted(directory.glob('*.started.json'))
        if len(completed) != len(started) or len(completed) != len(certificate['records']):
            raise ValueError('unknown/orphan calibration dispatch')
        certificates.append({'id': name, 'source_commit': certificate['plan']['source_commit'],
            'passed': certificate['all_controls_passed'], 'record_count': len(completed),
            'sha256': certificate['content_sha256'], 'protocol': certificate['plan']['protocol'],
            'runtime_sha256': digest(certificate['plan']['runtime']), 'backend': certificate['plan']['backend']})
        for record in certificate['records']:
            identity = record['intent']['id']
            if (_strict_json((directory / (identity + '.started.json')).read_text()) != record['intent']
                    or _strict_json((directory / (identity + '.completed.json')).read_text()) != record):
                raise ValueError('calibration intent/completion/certificate differs')
            rows.append(_row(name + '/' + identity, record['transport'], record['ok']))
        for path in sorted(directory.glob('*.json')):
            assets[str(path.relative_to(root))] = sha(path)
    planning = root / 'planning-a4'
    if planning.exists():
        plan = _strict_json((planning / 'plan.json').read_text())
        wrapper = _strict_json((planning / 'results.json').read_text())
        for terminal in sorted(planning.glob('arm-*/generation-*/response.json')):
            value = _strict_json(terminal.read_text())
            if value['content_sha256'] != digest({key: item for key, item in value.items() if key != 'content_sha256'}):
                raise ValueError('planning terminal hash differs')
            index = int(terminal.parent.parent.name.removeprefix('arm-'))
            reported = next(item for item in wrapper if item['arm'] == index)
            valid_finish = value['status'] == 'generated' and 'generation_failure' not in value['definition']
            planning_results.append({'arm': index, 'source_commit': plan['source_commit'],
                'request_sha256': value['request_sha256'], 'terminal_status': value['status'],
                'valid_explicit_finish': valid_finish, 'terminal_sha256': value['content_sha256'],
                'original_probe_wrapper_finished_flag': reported['finished'],
                'wrapper_flag_matches_terminal': reported['finished'] == valid_finish,
                'authoritative_status_source': 'original hashed generation terminal, not probe wrapper'})
        for path in sorted(planning.glob('arm-*/generation-*/step-*.completed.json')):
            step = _strict_json(path.read_text())
            rows.append(_row(str(path.relative_to(root)), step['model_reply']['transport'],
                bool((step.get('transition') or {}).get('ok'))))
        intents = list(planning.glob('arm-*/generation-*/step-*.started.json'))
        replies = list(planning.glob('arm-*/generation-*/step-*.completed.json'))
        if len(intents) != len(replies) or len(intents) > plan['max_POSTs']:
            raise ValueError('unknown/out-of-budget planning dispatch')
        for path in sorted(planning.rglob('*.json')):
            assets[str(path.relative_to(root))] = sha(path)
    if len(rows) > 49:
        raise ValueError('declared repair verification budget exceeded')
    sums = {}
    for field in ('prompt_tokens', 'completion_tokens', 'elapsed_seconds'):
        values = [row[field] for row in rows if type(row[field]) in (int, float)]
        sums[field] = {'known_sum': sum(values), 'known_count': len(values),
            'missing_count': len(rows) - len(values), 'missing_not_imputed': True}
    historical = {}
    for name in ('a1', 'a2'):
        published = _strict_json((ROOT / f'research/results/native-staged-search-v15-{name}.json').read_text())
        expected = published['audit']['raw_input_sha256s']
        directory = root.parent / ('native-staged-search-v15-' + name)
        actual = {str(path.relative_to(directory)): sha(path) for path in sorted(directory.rglob('*')) if path.is_file()}
        if actual != expected:
            raise ValueError('historical native evidence changed')
        historical[name] = {'files': len(actual), 'inventory_sha256': digest(actual), 'unchanged': True}
    result = {'schema': 'scienceutopia.designer-contract-verification-summary.v16',
        'certificates': certificates, 'planning_results': planning_results,
        'actual_POSTs': len(rows), 'maximum_POSTs': 49,
        'native_worlds': 0, 'generated_source_executions': 0, 'rows': rows, 'costs': sums,
        'evidence_inventory': assets, 'historical_native_inventories': historical,
        'scope': 'literal transport evidence/accounting; planning and invention claims require separate interpretation'}
    result['content_sha256'] = digest(result)
    return result


def _row(identity, transport, ok):
    payload = transport['request_payload']
    wire = transport['request_wire_utf8']
    if hashlib.sha256(wire.encode()).hexdigest() != transport['request_wire_sha256'] or _strict_json(wire) != payload:
        raise ValueError('original request wire differs')
    if payload['format'] != 'json' or payload['think'] is not False or payload['stream'] is not False:
        raise ValueError('unexpected actual generation mode')
    body = _strict_json(transport['raw_http_response'])
    if body != transport['response_payload']:
        raise ValueError('raw/parsed response differs')
    text = body['message']['content']
    return {'id': identity, 'accepted_control_or_tool': ok, 'output': _strict_json(text),
        'done': body.get('done'), 'done_reason': body.get('done_reason'),
        'prompt_tokens': body.get('prompt_eval_count'), 'completion_tokens': body.get('eval_count'),
        'elapsed_seconds': transport.get('elapsed_seconds'), 'request_wire_sha256': transport['request_wire_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root)
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({key: result[key] for key in ('actual_POSTs', 'costs', 'content_sha256')}))
