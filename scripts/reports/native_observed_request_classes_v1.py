"""Exact observed model-input classes, not semantic equivalence of worlds."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-observed-request-classes.v1'
AUDITS = {
    'scienceutopia.native-objective-instrument-loop-audit.v1',
    'scienceutopia.native-objective-fixed-evaluation-audit.v1',
}


def sequence(wires, replies):
    """Keep every literal input; match committed replies in original order."""
    if any(digest(w['payload']) != w['payload_sha256'] for w in wires):
        raise ValueError('literal model request hash differs')
    offset = 0
    matched = []
    choices = []
    body_hashes = []
    for payload_sha, outcome, body, expected_sha in replies:
        if outcome != 'response' or hashlib.sha256(body.encode()).hexdigest() != expected_sha:
            raise ValueError('committed provider response differs')
        while offset < len(wires) and wires[offset]['payload_sha256'] != payload_sha:
            offset += 1
        if offset == len(wires):
            raise ValueError('committed reply lacks its ordered original request')
        matched.append(offset)
        offset += 1
        response = json.loads(body)
        if not isinstance(response.get('choices'), list) or not response['choices']:
            raise ValueError('original response choices required')
        choices.append(response['choices'])
        body_hashes.append(expected_sha)
    return {
        'wire_requests': len(wires), 'completed_responses': len(replies),
        'wire_inputs_without_committed_reply': len(wires) - len(replies),
        'ordered_full_request_payload_sha256': digest([w['payload'] for w in wires]),
        'ordered_completed_request_payload_sha256': digest([wires[i]['payload'] for i in matched]),
        'ordered_literal_response_choices_sha256': digest(choices),
        'ordered_full_provider_body_hashes_sha256': digest(body_hashes),
    }


def groups(rows):
    """Never join different seeds or compare incomplete traces as whole runs."""
    if len({r['identity'] for r in rows}) != len(rows):
        raise ValueError('unique physical world identities required')
    members = {}
    for row in rows:
        if type(row['seed']) is not int:
            raise ValueError('literal world seed required')
        if row['status'] != 'complete':
            continue
        key = (row['seed'], row['requests']['ordered_full_request_payload_sha256'])
        members.setdefault(key, []).append(row)
    return [
        {'seed': key[0], 'full_request_sequence_sha256': key[1],
         'physical_ids': sorted(r['identity'] for r in values),
         'all_literal_response_choices_equal': len({r['requests']['ordered_literal_response_choices_sha256'] for r in values}) == 1,
         'all_full_provider_bodies_equal': len({r['requests']['ordered_full_provider_body_hashes_sha256'] for r in values}) == 1}
        for key, values in sorted(members.items())
    ]


def export(args):
    root, out = args.run.resolve(), args.output.resolve()
    source = pinned_revision(ROOT)
    paths = [root/'plan.json', args.audit_one.resolve(), args.audit_two.resolve()]
    if out.exists() or out.is_relative_to(root):
        raise ValueError('fresh output outside original scientific raw required')
    if paths[1].read_bytes() != paths[2].read_bytes():
        raise ValueError('two matching independent original audits required')
    hashes = {str(p): file_sha256(p) for p in paths}
    plan, audit = [checked(json.loads(p.read_text())) for p in paths[:2]]
    if (audit['schema'] not in AUDITS or audit['source_commit'] != plan['source_commit']
            or audit['plan_sha256'] != plan['content_sha256']
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions']):
        raise ValueError('matching normally closed original source audit required')
    before = _inventory(root)
    if digest(before) != audit['raw_inventory_sha256']:
        raise ValueError('scientific raw differs from original audit')
    rows = []
    for w in audit['worlds']:
        cell = Path(w['loaded']['context']).resolve().parent
        if not cell.is_relative_to(root):
            raise ValueError('world outside audited raw')
        wire, cache = cell/'wire-requests.jsonl', cell/'replies/responses.sqlite'
        wires = [json.loads(line) for line in wire.read_text().splitlines()] if wire.exists() else []
        replies = []
        if cache.exists():
            with sqlite3.connect(cache.resolve().as_uri()+'?mode=ro', uri=True) as db:
                replies = db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
        rows.append({'identity': w['identity'], 'seed': w['seed'], 'status': w['status'],
                     'requests': sequence(wires, replies)})
    result = {
        'schema': SCHEMA, 'analysis_source_commit': source,
        'scientific_source_commit': plan['source_commit'], 'plan_sha256': plan['content_sha256'],
        'audit_content_sha256': audit['content_sha256'], 'raw_inventory_sha256': digest(before),
        'worlds': rows, 'complete_observed_input_classes': groups(rows),
        'scope': 'Exact ordered full model payloads including model, messages and generation settings. '
                 'No text, timestamp, score or identity is scrubbed. Classes are within recorded world seeds '
                 'and completed worlds only; failed prefixes remain listed separately. Response choices '
                 'include literal finish metadata; full provider envelopes are compared separately. '
                 'Equality on observed histories is not program equivalence, identical scientific state, '
                 'a causal effect estimate, independent optimizer replication or a license to deduplicate new worlds.',
        'new_model_calls': 0, 'new_code_executions': 0, 'loss_or_selection_changed': False,
        'publication_ready': False,
    }
    if (before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in paths}
            or pinned_revision(ROOT) != source):
        raise ValueError('readout inputs or reader source changed')
    out.mkdir(parents=True)
    save(out/'report.json', result)
    save(out/'manifest.json', {'schema': SCHEMA+'.export', 'inputs': hashes,
                             'report_sha256': file_sha256(out/'report.json'),
                             'analysis_source_commit': source, 'new_model_calls': 0})
    print(json.dumps({'worlds': len(rows), 'complete_observed_input_classes': len(result['complete_observed_input_classes']),
                      'report_sha256': file_sha256(out/'report.json')}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'audit-one', 'audit-two', 'output'):
        p.add_argument('--'+key, type=Path, required=True)
    export(p.parse_args())


if __name__ == '__main__':
    main()
