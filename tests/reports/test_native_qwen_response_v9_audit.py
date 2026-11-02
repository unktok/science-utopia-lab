"""Synthetic contract tests only; never actual-Qwen or native-world evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.analyze_native_qwen_response_v9 import (
    ACTUAL,
    AMENDMENT_A3,
    CALIBRATION,
    EXPERIMENT,
    FIXED_NAMES,
    RAW_SCHEMA,
    UNUSED,
    _endpoint_sequence,
    _audit_common_prefix,
    _audit_review_clock_coupling,
    _prefix_control_status,
    _represented_landscape,
    _response_coupling,
    _validate_amendment,
    analyze,
    markdown_summary,
    source_proof,
)
from utopia.agents.base_agent import PaperReview
from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_response_prefix import SCHEMA as PREFIX_SCHEMA
from utopia.runtime.checkpointing import canonical_json, write_portable_checkpoint
from utopia.system.native_response_examples import DECLARATIONS, TERMS, response_gradient_system
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


def _rows(candidate=.48):
    values = CALIBRATION + UNUSED + [candidate]
    return [{'name': name, 'theta': theta} for name, theta in zip(FIXED_NAMES, values)]


def test_complete_sequence_is_exactly_six_preregistered_worlds():
    rows = _rows()
    result = _endpoint_sequence({'status': 'complete', 'endpoints': rows, 'failures': []},
                                require_complete=True)
    assert result == (rows, [], True)
    changed = deepcopy(rows)
    changed[3]['theta'] = .36
    with pytest.raises(ValueError, match='coordinate'):
        _endpoint_sequence({'status': 'complete', 'endpoints': changed, 'failures': []},
                           require_complete=True)


def test_stopped_attempt_retains_null_failure_and_rejects_live_prefix():
    rows = _rows()[:2]
    failure = {'name': 'calibration-2', 'loss': None, 'error_type': 'FixtureError',
               'error': 'synthetic failure'}
    assert _endpoint_sequence({'status': 'stopped-with-preserved-failure',
        'endpoints': rows, 'failures': [failure]}, require_complete=False) == (
            rows, [failure], False)
    with pytest.raises(ValueError, match='not a terminal'):
        _endpoint_sequence({'status': 'in-progress', 'endpoints': rows, 'failures': []},
                           require_complete=False)
    changed = deepcopy(failure)
    changed['loss'] = 1.0
    with pytest.raises(ValueError, match='converted'):
        _endpoint_sequence({'status': 'stopped-with-preserved-failure',
            'endpoints': rows, 'failures': [changed]}, require_complete=False)


def test_partial_audit_reproduces_strict_control_failure_without_relabelling(monkeypatch):
    proofs = [{'control_proof': {'identity': 'a'}}, {'control_proof': {'identity': 'b'}}]
    error = 'uncontrolled actual pre-intervention/prompt drift: identity'
    failures = [{'stage': 'fit-control-or-report', 'error_type': 'BoundaryUnsupported',
        'error': error, 'loss': None}]
    status = _prefix_control_status(proofs, failures)
    assert status['status'] == 'reproduced-preserved-strict-control-failure'
    assert 'not a negative' in status['scope']
    changed = deepcopy(failures)
    changed[0].update(error_type='PortableStop', error='cooperative operator stop',
                      name='calibration-2')
    separate = _prefix_control_status(proofs, changed)
    assert separate['status'] == 'observed-uncontrolled-prefix-separate-from-terminal-failure'
    assert separate['matches_recorded_terminal_failure_cause'] is False
    assert separate['recorded_terminal_failure']['error_type'] == 'PortableStop'
    assert 'not asserted to have caused' in separate['scope']


def test_markdown_reports_unfavorable_candidate_without_promotion_claim():
    report = {'schema': 'scienceutopia.native-qwen-response-audit.v9',
        'classification': ACTUAL, 'status': 'complete', 'source_commit': 'a'*40,
        'technical_validity': {'completed_worlds': 6, 'failures': []},
        'physical_reply_count': 12,
        'endpoints': [{'name': name, 'theta': theta, 'native_loss': float(index),
                       'response_count': 2}
                      for index, (name, theta) in enumerate(zip(FIXED_NAMES,
                                                                CALIBRATION+UNUSED+[.48]))],
        'response_operator_analysis': {
            'frozen_proposal': {'proposal': {'candidate': .48}},
            'candidate_minus_center_native_loss': 3.,
            'candidate_improvement_status': 'worse'}}
    report['content_sha256'] = digest(report)
    text = markdown_summary(report)
    assert 'Observed status: `worse`' in text
    assert 'No promotion policy' in text
    assert 'not an exact Qwen' in text


def test_represented_landscape_is_fixed_posthoc_frozen_grid():
    class Operator:
        _hash = 'a'*64
        def backward(self, coordinates):
            theta = coordinates[0]
            return {'represented_loss': theta**2, 'gradient': [2*theta],
                'frozen_boundary_gradient': [0.]}
    result = _represented_landscape(Operator())
    assert result['scope'] == ('posthoc frozen representation visualization; '
                                'not native samples or candidate selection')
    assert result['new_native_forward_calls'] == result['new_model_calls'] == 0
    assert result['representation_sha256'] == 'a'*64
    assert len(result['coordinates']) == 61
    assert result['coordinates'][0]['theta'] == .2
    assert result['coordinates'][-1]['theta'] == pytest.approx(.8)
    assert set(result['coordinates'][0]) == {
        'theta', 'predicted_loss', 'gradient', 'frozen_boundary_gradient'}


def _plan(source):
    root = Path(__file__).resolve().parents[2]
    world = {'source_commit': source, 'model_digest': 'e'*64,
        'corpus_sha256': 'f'*64, 'seed': 42, 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': {'kind': 'fixture'}, 'experiment': EXPERIMENT,
        'classification': ACTUAL}
    return {'schema': RAW_SCHEMA, 'classification': ACTUAL, 'world': world,
        'population': {'authors': 5, 'institutions': 5}, 'image_id': 'fixture-image',
        'loss_spec': load_loss_spec(root/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json'),
        'system': response_gradient_system('fixture-image').to_dict(),
        'declarations': DECLARATIONS, 'terms': TERMS, 'calibration': CALIBRATION,
        'unused': UNUSED, 'maximum_native_worlds': 6,
        'temperatures': [1., .2, .05, .01],
        'candidate_rule': 'center point .5, lr .02, displacement clamp +/-.10, support [.2,.8]',
        'protocol_sha256': file_sha256(root/'research/protocols/campaigns/native-qwen-response-gradient-v9.md')}


def test_analyze_binds_inventory_and_keeps_loss_separate_from_promotion(tmp_path, monkeypatch):
    source = 'a'*40
    plan = _plan(source)
    rows = _rows()
    raw = {'schema': RAW_SCHEMA, 'classification': ACTUAL, 'source_commit': source,
        'plan': plan, 'status': 'complete', 'endpoints': rows, 'failures': [],
        'physical_reply_count': 12, 'claims': {'actual_fixed_weight_Qwen': True,
            'scripted_researcher_HTTP': False, 'exact_Qwen_Jacobian': False,
            'full_native_world_autograd': False, 'held_out_seeds': False,
            'causal_scientific_benefit': False}}
    raw['content_sha256'] = digest(raw)
    (tmp_path/'plan.json').write_text(json.dumps(plan))
    (tmp_path/'evidence.json').write_text(json.dumps(raw))

    def proof(_root, row, **_kwargs):
        index = FIXED_NAMES.index(row['name'])
        return {'name': row['name'], 'theta': row['theta'], 'native_loss': float(index),
            'hard_represented_loss': float(index), 'checkpoint_sha256': str(index)*64,
            'initial_checkpoint_sha256': '1'*64, 'system_fingerprint': 'system',
            'physical_initial_identity': 'initial', 'noncoordinate_system_sha256': '2'*64,
            'response_count': 2, 'fresh_physical_reply_count': 2,
            'replayed_response_count': 0, 'common_prefix_proof': None,
            'review_reply_count': 1, 'review_cohorts': [],
            'objective_measurements': {'native.accepted_decisions': index,
                'native.accepted_peer_score_sum': float(index),
                'native.review_records': index+1},
            'raw_projection_sha256': '3'*64, 'journal_sha256': '4'*64,
            'wire_sha256': '5'*64, 'code_contexts_sha256': '6'*64,
            'completion_receipt_sha256': '7'*64, 'run_manifest_sha256': '8'*64,
            'control_proof': {'same': True}, 'endpoint': {'fixture': index}}

    monkeypatch.setattr('scripts.analyze_native_qwen_response_v9._audit_endpoint', proof)
    monkeypatch.setattr('scripts.analyze_native_qwen_response_v9._complete_reconstruction',
                        lambda *_args, **_kwargs: {'candidate_improvement_status': 'worse'})
    monkeypatch.setattr('scripts.analyze_native_qwen_response_v9.source_proof',
                        lambda *_args, **_kwargs: {'fixture.py': '9'*64})
    monkeypatch.setattr('scripts.analyze_native_qwen_response_v9._physical_response_ledger',
                        lambda *_args, **_kwargs: {'worlds': [],
                            'completed_endpoint_replies': 12,
                            'partial_null_loss_replies': 0,
                            'completed_endpoint_fresh_physical_replies': 12,
                            'partial_null_loss_fresh_physical_replies': 0,
                            'all_logical_replies': 12, 'all_replayed_replies': 0,
                            'all_fresh_physical_replies': 12})
    report = analyze(tmp_path, expected_source=source)
    assert report['objective']['role'] == 'optimization-loss'
    assert report['promotion_policy']['status'] == 'not-defined-or-applied'
    assert report['held_out_metrics']['status'] == 'not-measured'
    assert report['raw_hashes']['file_count'] == 2
    assert report['source_proof']['current_scientific_and_comparator_modules_match_experiment_commit']
    assert report['content_sha256'] == digest({k: v for k, v in report.items()
                                                if k != 'content_sha256'})


def test_scientific_source_modules_match_current_clean_pin():
    import subprocess
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    proof = source_proof(source)
    assert 'utopia/optimization/native_qwen_response.py' in proof
    assert all(len(value) == 64 for value in proof.values())
    a3 = source_proof(source, amendment_id=AMENDMENT_A3)
    assert 'utopia/optimization/native_response_prefix.py' in a3
    assert 'research/protocols/campaigns/native-qwen-response-gradient-v9-a3.md' in a3


def test_amendment_is_explicit_and_binds_prior_plus_combined_budget(tmp_path, monkeypatch):
    amendment = tmp_path/'a2.md'
    amendment.write_text('prospective synthetic amendment fixture')
    monkeypatch.setitem(__import__('scripts.analyze_native_qwen_response_v9', fromlist=['AMENDMENT_PATHS']).AMENDMENT_PATHS,
                        'native-qwen-response-gradient-v9-a2', amendment)
    expected = {'id': 'native-qwen-response-gradient-v9-a2',
        'sha256': file_sha256(amendment), 'prior_maximum_worlds': 3,
        'maximum_combined_physical_worlds': 9,
        'changes': 'exclude only server envelope metadata from cross-world semantic response equality'}
    assert _validate_amendment({'amendment': expected}, expected['id']) == expected
    with pytest.raises(ValueError, match='explicit expected amendment'):
        _validate_amendment({'amendment': expected}, None)
    changed = deepcopy(expected)
    changed['maximum_combined_physical_worlds'] = 6
    with pytest.raises(ValueError, match='combined budget'):
        _validate_amendment({'amendment': changed}, expected['id'])
    root = Path(__file__).resolve().parents[2]
    a3_path = root/'research/protocols/campaigns/native-qwen-response-gradient-v9-a3.md'
    a3 = {'id': AMENDMENT_A3, 'sha256': file_sha256(a3_path),
        'prior_world_attempts': 4, 'prior_completed_worlds': 2,
        'prior_partial_worlds': 2, 'prior_physical_replies': 228,
        'maximum_combined_world_attempts': 10,
        'changes': ('replay an exact actual Qwen pre-intervention history; '
                    'generate affected and later replies freshly')}
    assert _validate_amendment({'amendment': a3}, AMENDMENT_A3) == a3


def _coupled_transport(tmp_path):
    cell = tmp_path/'world'
    (cell/'replies').mkdir(parents=True)
    binding = {'cell': 'target-cell', 'seed': 42, 'model': 'fixture-model',
        'model_revision': 'e'*64, 'corpus_sha256': 'f'*64,
        'science_config': {'source_commit': 'a'*40}}
    prefix_payload = {'model': 'fixture-model', 'seed': 10,
        'messages': [{'role': 'user', 'content': 'exact actual prefix'}]}
    review_payload = {'model': 'fixture-model', 'seed': 20,
        'messages': [{'role': 'user', 'content': 'first affected review'}],
        'response_format': {'json_schema': {'schema': PaperReview.model_json_schema()}}}
    payloads = [prefix_payload, review_payload]
    payload_shas = [hashlib.sha256(canonical_json(value).encode()).hexdigest()
                    for value in payloads]
    data = [canonical_json({'model': 'fixture-model', 'choices': []}),
            canonical_json({'model': 'fixture-model', 'choices': []})]
    data_shas = [hashlib.sha256(value.encode()).hexdigest() for value in data]
    call = {'index': 0, 'year': 1, 'seed': 10, 'payload_sha256': payload_shas[0],
        'anchor_cache_identity': '1'*64, 'anchor_sql_rowid': 1,
        'anchor_wire_line': 1, 'response_sha256': data_shas[0]}
    review = {'year': 1, 'conference_id': 'conference-1', 'arxiv_id': 'paper-1',
        'reviewer_id': 'reviewer-1', 'review_time': 123.25, 'overall_score': 7}
    checkpoint_state = {'conference_system': {'conferences': [{'conference_id': 'conference-1',
        'reviews': {'paper-1': [review]}}]}}
    anchor_checkpoint = tmp_path/'anchor/year1.json.gz'
    target_checkpoint = cell/'simulation/checkpoints/native-design/portable_checkpoint_year_1.json.gz'
    anchor_checkpoint.parent.mkdir(parents=True)
    target_checkpoint.parent.mkdir(parents=True)
    write_portable_checkpoint(anchor_checkpoint, checkpoint_state)
    write_portable_checkpoint(target_checkpoint, checkpoint_state)
    record = {'year': 1, 'conference_id': 'conference-1', 'paper_id': 'paper-1',
        'reviewer_id': 'reviewer-1', 'review_time': 123.25,
        'anchor_review_sha256': digest(review),
        'nonclock_review_sha256': digest({k: v for k, v in review.items() if k != 'review_time'})}
    source_checkpoint_sha = file_sha256(anchor_checkpoint)
    prepared = {'schema': PREFIX_SCHEMA, 'content_sha256': '2'*64, 'prefix_count': 1,
        'calls': [call], 'anchor_endpoint': {'checkpoint_sha256': '3'*64},
        'anchor_world_dir': str(tmp_path/'anchor'),
        'anchor_files': {'journal': {'sha256': '4'*64},
            'year1_checkpoint': {'path': str(anchor_checkpoint), 'sha256': source_checkpoint_sha}},
        'review_clock_coupling': {'source_checkpoint_sha256': source_checkpoint_sha,
            'field': 'review_time', 'period': 1, 'records': [record]},
        'boundary': {'year': 2, 'seed': 20,
            'task_schema_sha256': digest(PaperReview.model_json_schema())}}
    origin = {'schema': PREFIX_SCHEMA+'.replayed-from',
        'manifest_sha256': prepared['content_sha256'],
        'anchor_checkpoint_sha256': '3'*64, 'anchor_journal_sha256': '4'*64, **call}
    wires = [{'year': 1, 'payload_sha256': payload_shas[0], 'payload': prefix_payload,
              'replayed_from': origin},
             {'year': 2, 'payload_sha256': payload_shas[1], 'payload': review_payload}]
    (cell/'wire-requests.jsonl').write_text(''.join(canonical_json(value)+'\n' for value in wires))
    with sqlite3.connect(cell/'replies/responses.sqlite') as db:
        db.execute('CREATE TABLE metadata(binding TEXT NOT NULL)')
        db.execute('INSERT INTO metadata VALUES (?)', (canonical_json(binding),))
        db.execute('CREATE TABLE replies(identity TEXT,payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        db.executemany('INSERT INTO replies VALUES (?,?,?,?,?)', [
            ('5'*64, payload_shas[0], 'response', data[0], data_shas[0]),
            ('6'*64, payload_shas[1], 'response', data[1], data_shas[1])])
    receipt = {'schema': PREFIX_SCHEMA+'.execution',
        'manifest_sha256': prepared['content_sha256'], 'anchor_checkpoint_sha256': '3'*64,
        'used_prefix_count': 1, 'expected_prefix_count': 1, 'replayed_response_count': 1,
        'initially_committed_prefix_count': 0, 'replayed_in_this_session': 1,
        'fresh_physical_calls': 1, 'fresh_physical_reply_count': 1,
        'fresh_physical_calls_this_session': 1, 'fresh_review_boundary_reached': True,
        'logical_response_count': 2, 'prefix_complete': True,
        'independent_prefix_replication': False,
        'review_clock_coupling': {'source_checkpoint_sha256': source_checkpoint_sha,
            'field': 'review_time', 'period': 1, 'expected_records': 1,
            'current_session_before_after_records': [{
                'year': 1, 'conference_id': 'conference-1', 'paper_id': 'paper-1',
                'reviewer_id': 'reviewer-1', 'field': 'review_time',
                'before_review_time': 999.75, 'after_review_time': 123.25,
                'before_review_sha256': digest({**review, 'review_time': 999.75}),
                'after_review_sha256': digest(review),
                'nonclock_review_sha256': record['nonclock_review_sha256'],
                'source_checkpoint_sha256': source_checkpoint_sha}],
            'completed_checkpoint_verification': 'exact-semantic-year1-checkpoint-clocks-verified',
            'prior_session_before_timestamps_reconstructed': False,
            'global_and_transport_clock_modified': False,
            'year2_review_clock_modified': False},
        'target_binding_sha256': digest(binding)}
    receipt['content_sha256'] = digest(receipt)
    (cell/'common-prefix-receipt.json').write_text(json.dumps(receipt))
    row = {'name': 'calibration-0', 'common_prefix_receipt': receipt,
        'logical_response_count': 2, 'replayed_response_count': 1, 'fresh_physical_replies': 1}
    return cell, row, {'response_cache_count': 2}, prepared


def test_common_prefix_audit_joins_origin_new_cache_and_first_fresh_review(tmp_path, monkeypatch):
    cell, row, endpoint, prepared = _coupled_transport(tmp_path)
    monkeypatch.setattr('scripts.analyze_native_qwen_response_v9.control_proof',
                        lambda *_args, **_kwargs: {'same': True})
    proof = _audit_common_prefix(cell, row, endpoint, {'same': True},
                                 {'mode': 'actual-common-prefix-replay', 'prepared': prepared})
    assert proof['replayed_response_count'] == 1
    assert proof['fresh_physical_reply_count'] == 1
    assert proof['first_fresh_review_boundary_verified']
    assert proof['review_clock_coupling']['all_semantic_records_verified']
    assert not proof['review_clock_coupling']['historical_before_timestamps_independently_authenticated']
    with sqlite3.connect(cell/'replies/responses.sqlite') as db:
        db.execute('UPDATE replies SET identity=? WHERE rowid=1', ('1'*64,))
    with pytest.raises(ValueError, match='anchor origin'):
        _audit_common_prefix(cell, row, endpoint, {'same': True},
                             {'mode': 'actual-common-prefix-replay', 'prepared': prepared})


def test_review_clock_audit_rejects_tampered_before_hash(tmp_path):
    cell, row, _endpoint, prepared = _coupled_transport(tmp_path)
    receipt = deepcopy(row['common_prefix_receipt'])
    receipt['review_clock_coupling']['current_session_before_after_records'][0][
        'before_review_sha256'] = '0'*64
    with pytest.raises(ValueError, match='hashes do not reconstruct'):
        _audit_review_clock_coupling(cell, prepared, receipt)
