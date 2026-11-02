"""Controlled actual-response receipts and a fixed, loss-only gradient step.

No model calls here. This verifies input/control invariants independently of
numeric fitting; unsupported comparisons are not zero-imputed derivatives.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sqlite3

from .native_response_fidelity import BoundaryUnsupported
from utopia.agents.base_agent import PaperReview
from utopia.runtime.checkpointing import canonical_json
from utopia.system.design_patch import digest
from utopia.system.native_response_examples import RUBRIC_SOURCE
from utopia.utils.data_utils import file_sha256

HEADER = '\n## Information received from scientific institutions\n'


def gradient_proposal(backward):
    """Predeclared center point step, never consult unused native outcomes."""
    if backward['coordinates'] != [.5] or len(backward['gradient']) != 1:
        raise ValueError('v9 step requires the declared center and one gradient')
    g = backward['gradient'][0]
    if type(g) not in (float, int) or not math.isfinite(g):
        raise ValueError('finite represented gradient required')
    displacement = min(.10, max(-.10, -.02*g))
    return {'rule': 'theta=clip(.5+clip(-.02*center_gradient,-.10,.10),.2,.8)',
        'center': .5, 'learning_rate': .02, 'trust_radius': .10,
        'gradient': g, 'requested': .5-.02*g,
        'candidate': min(.8, max(.2, .5+displacement)),
        'unchanged': displacement == 0., 'unused_outcomes_seen': 0,
        'representation_sha256': backward['representation_sha256']}


def control_proof(endpoint, world_root):
    """Exact pre-intervention HTTP and public-review-payload normalization.

    The entire actual batch payload, not merely a prompt substring, is compared.
    Only the declared complementary numeric fields are masked. The prefix uses
    payload+response SHA pairs, so seed equality is never assumed deterministic.
    """
    root = Path(world_root).resolve()
    journal, wire = root/'replies/responses.sqlite', root/'wire-requests.jsonl'
    context_path = Path(endpoint['code_contexts'])
    before = [file_sha256(p) for p in (journal, wire, context_path)]
    if before[2] != endpoint['code_contexts_sha256']:
        raise ValueError('actual code context hash changed')
    with sqlite3.connect(journal.as_uri()+'?mode=ro', uri=True) as db:
        metadata = db.execute('SELECT binding FROM metadata').fetchall()
        rows = db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    if len(metadata) != 1:
        raise ValueError('control proof requires one actual endpoint binding')
    binding = json.loads(metadata[0][0])
    world = endpoint['world']
    if (binding.get('cell') != endpoint['system_fingerprint'] or binding.get('seed') != world['seed']
            or binding.get('model_revision') != world['model_digest']
            or binding.get('corpus_sha256') != world['corpus_sha256']
            or binding.get('science_config', {}).get('source_commit') != world['source_commit']):
        raise ValueError('actual control transport binding differs from endpoint identity')
    contexts = [json.loads(line) for line in context_path.read_text().splitlines()]
    signals = [r for r in contexts if r['artifact']['source'] == RUBRIC_SOURCE]
    if len(signals) != 2 or [r['context']['period'] for r in signals] != [1, 2]:
        raise ValueError('missing exact two-year actual charter execution receipts')
    if signals[0]['result']['outputs']['messages'] != []:
        raise BoundaryUnsupported('first-year charter must not deliver coordinate-dependent information')
    emitted = signals[1]['result']['outputs']['messages']
    if len(emitted) != 1 or not isinstance(emitted[0].get('payload'), dict):
        raise ValueError('actual source receipt must emit one charter payload')
    expected_body = emitted[0]['payload']
    by_sha = {r[0]: r for r in rows}
    wires = [json.loads(line) for line in wire.read_text().splitlines()]
    if len(by_sha) != len(rows) or len(wires) != len(rows) or {w['payload_sha256'] for w in wires} != set(by_sha):
        raise ValueError('control proof requires unique fresh wire/reply bijection')
    prefix, reviews, began = [], [], False
    theta = endpoint['coordinate_values']['evidence-weight']
    for w in wires:
        payload = w['payload']
        _, outcome, data, sha = by_sha[w['payload_sha256']]
        if (outcome != 'response' or payload.get('model') != binding['model']
                or json.loads(data).get('model') != binding['model']
                or sha != hashlib.sha256(data.encode()).hexdigest()
                or w['payload_sha256'] != hashlib.sha256(canonical_json(payload).encode()).hexdigest()):
            raise ValueError('control proof actual request/reply bytes changed')
        schema = (payload.get('extra_body', {}).get('structured_outputs', {}).get('json')
            or payload.get('response_format', {}).get('json_schema', {}).get('schema'))
        review = schema == PaperReview.model_json_schema() and w['year'] == 2
        if review:
            began = True
            clean = deepcopy(payload)
            found, base = 0, []
            for message in clean['messages']:
                text = message.get('content')
                if not isinstance(text, str) or HEADER not in text:
                    continue
                first, marker, suffix = text.rpartition(HEADER)
                body = json.loads(suffix.strip())
                if (body != expected_body
                        or set(body) != {'institution', 'instruction', 'native_year', 'evidence_weight', 'originality_weight'}
                        or body['institution'] != 'Evidence and originality review charter'
                        or body['native_year'] != 2 or body['evidence_weight'] != theta
                        or body['originality_weight'] != 1.-theta):
                    raise BoundaryUnsupported('actual public review input differs from the declared charter')
                body['evidence_weight'] = '<declared-coordinate>'
                body['originality_weight'] = '<one-minus-declared-coordinate>'
                message['content'] = first+marker+json.dumps(body, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n'
                base.append(digest(first))
                found += 1
            if found != 1:
                raise BoundaryUnsupported('actual review input lacks exactly one public charter; no metadata masking')
            reviews.append({'base_prompt_sha256s': base, 'normalized_payload_sha256': digest(clean)})
        elif not began:
            if any('"evidence_weight":' in str(m.get('content', '')) for m in payload['messages']):
                raise BoundaryUnsupported('variable review charter was visible before its declared intervention')
            prefix.append({'year': w['year'], 'payload_sha256': w['payload_sha256'], 'response_sha256': sha})
    pre_world = signals[1]['context']['inputs']['world'][0]['payload']
    if not reviews or not prefix:
        raise BoundaryUnsupported('no actual final-year reviews or pre-intervention replies')
    if before != [file_sha256(p) for p in (journal, wire, context_path)]:
        raise ValueError('control evidence changed during read-only proof')
    value = {'physical_initial_identity': endpoint['physical_initial_identity'],
        'noncoordinate_system_sha256': endpoint['noncoordinate_system_sha256'],
        'preintervention_request_response_sequence_sha256': digest(prefix),
        'preintervention_physical_reply_count': len(prefix),
        'preintervention_world_observation_sha256': digest(pre_world),
        'normalized_final_review_payloads_sha256': digest(reviews),
        'final_review_prompt_count': len(reviews),
        'scope': 'Actual initial state, pre-intervention HTTP+reply bytes and original world observation; canonical public review payload differs only in the two declared complementary weights.'}
    return value


def require_same_control(proofs):
    if not proofs:
        raise ValueError('actual control proofs required')
    if any(p != proofs[0] for p in proofs[1:]):
        differing = sorted({k for p in proofs[1:] for k in proofs[0] if p.get(k) != proofs[0][k]})
        raise BoundaryUnsupported('uncontrolled actual pre-intervention/prompt drift: '+', '.join(differing))
    return {'status': 'exact-control-invariants-verified', 'world_count': len(proofs), 'proof_sha256': digest(proofs[0])}
