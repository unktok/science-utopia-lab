"""SCRIPTED regression evidence, not local model invention performance."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, BINDING, request
from tests.optimization.test_native_planning_author_v22 import PLAN, prompt
from tests.optimization.test_native_staged_author_v15 import Model, author, finish
from utopia.optimization.native_authoring_feedback_v26 import own_trial_feedback
from utopia.optimization.native_designer_tools_v25 import (
    CHANNEL, action_from_body, response_message_from_action)
from utopia.optimization.native_staged_author_v15 import (
    PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, build_conversation, replay_staged_generation)
from utopia.system.design_patch import digest


def record(definition, candidate, observation=None):
    return {'request_sha256': 'a' * 64, 'version_sha256': 'b' * 64,
        'definition': definition, 'generation_error': None,
        'draws': [{'suggestion': {'candidate': candidate}}],
        'observations': [observation], 'report': {'losses': [-1]}}


def test_noop_plan_is_not_reported_as_an_implemented_institution_and_all_own_trials_reach_planner(tmp_path):
    req = request()
    model = Model([PLAN, finish()])
    definition = author(model, tmp_path, max_steps=2)(req)
    observation = {'observation_id': 'own-observation', 'status': 'complete', 'loss': -1}
    req['history'] = [record(definition, req['parent_system'], observation)]
    req['based_on_observation_id'] = 'own-observation'
    original = deepcopy(req)
    feedback = own_trial_feedback(req)
    trial = feedback['all_own_trials'][0]
    assert trial['untrusted_model_authored_plan']['design_intent'] == PLAN['design_intent']
    assert trial['literal_submission']['no_literal_intervention'] is True
    assert trial['literal_submission']['observed_session']['literal_document_changed'] is False
    assert trial['observations'][0]['observation'] == observation
    assert trial['observations'][0]['is_current_parent'] is True
    for task in (PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT):
        messages = build_conversation(prompt(req), task, native_tools=True)
        assert json.dumps(feedback, ensure_ascii=False, sort_keys=True) in messages[1]['content']
        assert PLAN['design_intent'] not in messages[0]['content']
    assert req == original


def test_literal_change_and_unknown_or_failed_outcomes_are_not_replaced_by_zero(tmp_path):
    req = request()
    edit = {'tool': 'edit', 'operations': [{'op': 'replace', 'selector': {'mechanism_id': ALPHA},
        'path': '/parameters/gain', 'value': .8}]}
    definition = author(Model([edit, finish()]), tmp_path, max_steps=2)(req)
    req['history'] = [record(definition, req['parent_system']),
        {'definition': {'generation_failure': {'reason': 'SCRIPTED failure'}},
            'generation_error': 'SCRIPTED failed', 'observations': [None], 'draws': []}]
    feedback = own_trial_feedback(req)
    assert len(feedback['all_own_trials']) == 2
    changed, failed = feedback['all_own_trials']
    assert changed['literal_submission']['no_literal_intervention'] is False
    assert changed['literal_submission']['authored_operation_count'] == 1
    assert changed['literal_submission']['observed_session']['literal_document_changed'] is True
    assert changed['observations'][0]['observation'] is None
    assert failed['literal_submission']['no_literal_intervention'] is None
    assert failed['literal_submission']['authored_operation_count'] is None
    assert failed['literal_submission']['observed_session'] is None
    assert failed['observations'][0]['candidate_sha256'] is None
    assert failed['observations'][0]['observation'] is None
    assert failed['generation_failure']['reason'] == 'SCRIPTED failure'


@pytest.mark.parametrize('truncated', [False, True])
def test_known_http200_invalid_reply_is_not_a_transport_failure_and_cold_replays_without_retry(tmp_path, truncated):
    class KnownInvalidModel(Model):
        def generate(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) > 1:
                output = finish()
                return output, [{'role': 'assistant', 'content': json.dumps(output)}]
            message = response_message_from_action({'tool': 'validate'})
            if not truncated:
                message['content'] += '}'
            body = {'message': message, 'done': True, 'done_reason': 'length' if truncated else 'stop'}
            self.last_messages = [message]
            self.last_transport = {'response_channel': CHANNEL, 'http_status': 200,
                'raw_http_response': json.dumps(body), 'response_payload': body}
            return action_from_body(body), self.last_messages

    # Explicit fake transport for each call: the second is a legacy SCRIPTED
    # final, not a native response silently substituted by production.
    class ModelWithFreshTransport(KnownInvalidModel):
        def generate(self, **kwargs):
            self.last_transport, self.last_messages = {}, []
            return super().generate(**kwargs)
    model = ModelWithFreshTransport([])
    definition = author(model, tmp_path, max_steps=2)(request())
    folder = next(tmp_path.glob('generation-*'))
    first = json.loads((folder / 'step-00.completed.json').read_text())
    assert first['status'] == 'invalid-response'
    assert first['model_reply']['output'] is None
    assert first['model_reply']['transport']['http_status'] == 200
    assert first['errors'][0]['message']
    assert definition['provenance']['staged_author']['observed_session']['steps'][0]['status'] == 'invalid-response'
    assert replay_staged_generation(folder, expected_provider_binding=BINDING) == definition
    assert len(model.calls) == 2


def test_terminal_session_facts_are_recomputed_not_trusted_after_rehash(tmp_path):
    from tests.optimization.test_native_staged_author_v15 import rehash
    definition = author(Model([finish()]), tmp_path, max_steps=2)(request())
    folder = next(tmp_path.glob('generation-*'))
    assert definition['provenance']['staged_author']['observed_session']['literal_document_changed'] is False
    def tamper(value):
        value['definition']['provenance']['staged_author']['observed_session']['literal_document_changed'] = True
    rehash(folder / 'response.json', tamper)
    with pytest.raises(ValueError, match='exact replay'):
        replay_staged_generation(folder)


@pytest.mark.parametrize('truncated', [False, True])
def test_local_sender_known_bad_final_is_archived_and_cold_replayed_without_new_post(tmp_path, monkeypatch, truncated):
    from tests.optimization.test_native_designer_contract_v16 import Response, ScriptedSession
    from utopia.optimization.native_staged_author_v15 import LocalStagedQwenDesignerModel
    class Session(ScriptedSession):
        posts = 0
        def post(self, url, **kwargs):
            self.posts += 1
            action = {'tool': 'validate'} if self.posts == 1 else finish()
            message = response_message_from_action(action)
            if self.posts == 1 and not truncated:
                message['content'] += '}'
            return Response({'message': message, 'model': BINDING['model'], 'done': True,
                'done_reason': 'length' if self.posts == 1 and truncated else 'stop'})
    monkeypatch.setattr('requests.Session', Session)
    model = LocalStagedQwenDesignerModel(BINDING)
    definition = author(model, tmp_path, max_steps=2)(request())
    folder = next(tmp_path.glob('generation-*'))
    first = json.loads((folder / 'step-00.completed.json').read_text())
    assert first['status'] == 'invalid-response' and first['model_reply']['output'] is None
    assert first['model_reply']['transport']['raw_http_response']
    assert definition['base_patch'] is None and model.session.posts == 2
    assert replay_staged_generation(folder, expected_provider_binding=BINDING) == definition
    assert model.session.posts == 2


@pytest.mark.parametrize('protocol', [
    'native-tool-calling-exploration-v25-a1', 'native-tool-calling-exploration-v25-a2',
    'native-tool-calling-exploration-v25-a3', 'native-function-feedback-v26-a1',
    'native-literal-workbench-v27-a1', 'native-literal-workbench-v27-a2'])
def test_reporting_protocol_allowlist_includes_each_declared_continuation(monkeypatch, protocol):
    from scripts import analyze_native_staged_search_v15 as audit
    import hashlib
    monkeypatch.setattr(audit.subprocess, 'check_output',
        lambda args, **kwargs: '' if '--name-only' in args else b'')
    monkeypatch.setattr(audit, 'file_sha256', lambda path: hashlib.sha256(b'').hexdigest())
    path = 'research/protocols/campaigns/' + protocol + '.md'
    proof = audit.source_proofs('a' * 40, audit.CLASSIFICATION, protocol_path=path)
    assert path in proof['files']
    with pytest.raises(ValueError, match='explicit versioned'):
        audit.source_proofs('a' * 40, audit.CLASSIFICATION,
            protocol_path='research/protocols/campaigns/model-chosen-protocol.md')


def test_parent_feedback_uses_current_best_candidate_without_host_policy_or_source_read(tmp_path):
    req = request()
    secret = 'SCRIPTED_SOURCE_NOT_FOR_PLANNER'
    req['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source'] += '\n# ' + secret
    req['history'] = [record({}, req['parent_system'], {'loss': 2, 'status': 'complete',
        'candidate': deepcopy(req['parent_system'])})]
    feedback = own_trial_feedback(req)
    assert feedback['current_parent_sha256'] == digest(req['parent_system'])
    assert feedback['all_own_trials'][0]['observations'][0]['is_current_parent'] is True
    messages = build_conversation(prompt(req), PLAN_SYSTEM_PROMPT, native_tools=True)
    assert secret not in json.dumps(messages)


def test_full_observed_candidate_is_explicitly_referenced_without_dropping_any_other_observation_fact():
    req = request()
    observation = {'candidate': deepcopy(req['parent_system']), 'observation_id': 'actual-shape',
        'status': 'complete', 'loss': -2, 'suggestion_id': 'own-suggestion',
        'metadata': {'measurements': {'A': 2}, 'technical_failures': [],
            'runs': [{'checkpoint_sha256': 'c' * 64, 'seed': 42}], 'unknown_future_field': [None, True, 9007199254740993]}}
    req['history'] = [record({}, req['parent_system'], observation)]
    original = deepcopy(req)
    item = own_trial_feedback(req)['all_own_trials'][0]['observations'][0]
    assert item['observation'] == {key: value for key, value in observation.items() if key != 'candidate'}
    assert item['original_observation_sha256'] == digest(observation)
    assert item['explicit_body_omission']['field'] == 'candidate'
    assert item['explicit_body_omission']['body_sha256'] == digest(observation['candidate'])
    assert item['candidate_sha256'] == digest(req['parent_system']) and item['is_current_parent'] is True
    assert req == original


def test_null_candidate_body_is_not_replaced_with_an_empty_system_or_zero():
    req = request()
    observation = {'candidate': None, 'status': 'technical-failure', 'loss': None,
        'metadata': {'technical_failures': [{'message': 'SCRIPTED failed native measurement'}]}}
    req['history'] = [record({}, req['parent_system'], observation)]
    item = own_trial_feedback(req)['all_own_trials'][0]['observations'][0]
    assert item['observation']['loss'] is None
    assert item['observation']['metadata'] == observation['metadata']
    assert item['explicit_body_omission']['body_sha256'] == digest(None)
