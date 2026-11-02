"""Synthetic contract tests only; never actual-Qwen or native-world evidence."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.analyze_native_qwen_response_v9 import (
    ACTUAL,
    CALIBRATION,
    EXPERIMENT,
    FIXED_NAMES,
    RAW_SCHEMA,
    UNUSED,
    _endpoint_sequence,
    _prefix_control_status,
    _validate_amendment,
    analyze,
    markdown_summary,
    source_proof,
)
from utopia.optimization.loss import load_loss_spec
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
    changed[0]['error'] = 'different error'
    with pytest.raises(ValueError, match='does not reproduce'):
        _prefix_control_status(proofs, changed)


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
            'response_count': 2, 'review_reply_count': 1, 'review_cohorts': [],
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
    report = analyze(tmp_path, expected_source=source)
    assert report['objective']['role'] == 'optimization-loss'
    assert report['promotion_policy']['status'] == 'not-defined-or-applied'
    assert report['held_out_metrics']['status'] == 'not-measured'
    assert report['raw_hashes']['file_count'] == 2
    assert report['source_proof']['current_scientific_and_comparator_modules_match_experiment_commit']
    assert report['content_sha256'] == digest({k: v for k, v in report.items()
                                                if k != 'content_sha256'})


def test_scientific_source_modules_match_original_a1_pin():
    proof = source_proof('d5b08d64193c32bf05dec95e54ba53d2f1b8cab9')
    assert 'utopia/optimization/native_qwen_response.py' in proof
    assert all(len(value) == 64 for value in proof.values())


def test_amendment_is_explicit_and_binds_prior_plus_combined_budget(tmp_path, monkeypatch):
    amendment = tmp_path/'a2.md'
    amendment.write_text('prospective synthetic amendment fixture')
    monkeypatch.setattr('scripts.analyze_native_qwen_response_v9.AMENDMENT_PATH', amendment)
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
