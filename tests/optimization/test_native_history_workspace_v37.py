"""SCRIPTED own-failure source retrieval; not scientific invention evidence."""
from copy import deepcopy
import json
from urllib.parse import quote

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, IMAGE, request
from tests.optimization.test_native_planning_author_v22 import PLAN
from tests.optimization.test_native_staged_author_v15 import apply
from utopia.optimization.native_authoring_feedback_v26 import own_trial_feedback
from utopia.optimization.native_file_workspace_v35 import file_catalog, read_file, write_file_operations
from utopia.optimization.native_staged_author_v15 import initial_draft, read_memory, build_prompt, build_conversation, SYSTEM_PROMPT
from utopia.system.design_patch import digest

PREFIX = 'history/trial-000/observation-000/'
PAST_SOURCE = 'def step(context):\n    # SCRIPTED_PREVIOUS_FAILED_SOURCE\n    return {"outputs": {}, "state": context["state"]}\n'


def failed_request():
    body = request(); candidate = deepcopy(body['parent_system'])
    node = next(n for n in candidate['mechanisms'] if n['mechanism_id'] == ALPHA)
    node['parameters']['code_artifact']['source'] = PAST_SOURCE
    observation = {'status': 'failed', 'loss': None, 'candidate': candidate,
        'metadata': {'technical_failures': [{'error': 'SCRIPTED actual-shaped code failure'}]}}
    body['history'] = [{'definition': {'generation_failure': {'raw_operand': 'SCRIPTED literal'}},
        'observations': [observation], 'draws': []}]
    return body


def test_failed_candidate_is_inspectable_even_when_incumbent_is_the_original_parent():
    body = failed_request(); before = deepcopy(body); doc = body['parent_system']
    # The scalar/failure view still avoids repeating full candidate bodies.
    feedback = own_trial_feedback(body)
    assert 'SCRIPTED_PREVIOUS_FAILED_SOURCE' not in json.dumps(feedback)
    item = feedback['all_own_trials'][0]['observations'][0]
    assert item['archived_candidate_file'] == PREFIX + 'system.json'
    catalog = file_catalog(doc, request=body)
    assert catalog['all_current_draft_names_included'] and not catalog['all_file_names_included']
    assert catalog['deferred_archive_names']['complete_index_filename'] == 'history/index.json'
    index = read_file(doc, 'history/index.json', request=body)
    names = json.loads(index['content'])['trials'][0]['observations'][0]['files']
    target = PREFIX + 'code/' + quote(ALPHA, safe='._-') + '.py'
    assert target in names
    result = read_file(doc, target, request=body)
    assert result['content'] == PAST_SOURCE and result['read_only']
    assert result['archive']['candidate_sha256'] == digest(body['history'][0]['observations'][0]['candidate'])
    assert result['source_kind'] == 'own-history' and result['complete']
    assert json.loads(read_file(doc, PREFIX + 'observation.json', request=body)['content']) == body['history'][0]['observations'][0]
    assert body == before


@pytest.mark.parametrize('target', ['history/index.json', PREFIX + 'system.json',
    PREFIX + 'nodes/' + quote(ALPHA, safe='._-') + '.json',
    PREFIX + 'code/' + quote(ALPHA, safe='._-') + '.py', 'history/trial-000/definition.json'])
def test_every_archive_alias_is_readonly_before_parsing_or_mutation(target):
    body = failed_request(); before = deepcopy(body)
    with pytest.raises(ValueError, match='read-only'):
        write_file_operations(body['parent_system'], target, 'INVALID JSON OR PYTHON', request=body)
    assert body == before


def test_no_history_means_no_donor_alias_or_implicit_parent_adoption():
    body = request(); old = deepcopy(body)
    catalog = file_catalog(body['parent_system'], request=body)
    assert catalog['all_file_names_included']
    assert not any(x['filename'].startswith('history/') for x in catalog['files'])
    with pytest.raises(ValueError, match='unknown exact'):
        read_file(body['parent_system'], PREFIX + 'system.json', request=body)
    assert body == old


def test_history_read_uses_existing_charged_tool_and_never_edits_the_incumbent():
    body = failed_request(); state = initial_draft(body); target = PREFIX + 'code/' + quote(ALPHA, safe='._-') + '.py'
    after, receipt = apply(state, {'tool': 'read_file', 'filename': target}, body)
    assert after == state and receipt['ok'] and receipt['result']['resource'] == 'history'
    assert receipt['result']['value'] == PAST_SOURCE
    changed, edit = apply(after, {'tool': 'edit_fields', 'mechanism_id': ALPHA,
        'field_updates': [{'field_name': 'gain', 'value': .8}]}, body)
    steps = [{'step': 0, 'status': 'applied', 'transition': receipt}]
    memory = read_memory(changed, steps)
    assert memory['entries'][0]['immutable_own_history']
    assert memory['entries'][0]['current_document'] is None
    assert changed['document'] != body['history'][0]['observations'][0]['candidate']


def test_editor_exposes_archive_index_as_data_not_system_authority():
    body = failed_request(); state, receipt = apply(initial_draft(body), PLAN, body)
    steps = [{'step': 0, 'status': 'applied', 'model_reply': {'output': PLAN}, 'transition': receipt}]
    prompt = build_prompt(body, state, steps, image_id=IMAGE, binding_sha256='d' * 64, settings={'max_steps': 8})
    messages = build_conversation(prompt, SYSTEM_PROMPT, native_tools=True)
    assert PAST_SOURCE not in messages[0]['content']
    assert 'history/index.json' in messages[0]['content']
    data = json.loads(messages[1]['content'].split('EXACT SESSION DATA\n', 1)[1])
    assert 'history/index.json' in {x['filename'] for x in data['virtual_editor_workspace']['files']}


def test_explicit_slices_of_historical_code_preserve_codepoints_and_hashes():
    body = failed_request(); doc = body['parent_system']; target = PREFIX + 'code/' + quote(ALPHA, safe='._-') + '.py'
    result = read_file(doc, target, request=body, offset=4, limit=13)
    assert result['content'] == PAST_SOURCE[4:17] and not result['complete']
    assert result['total_characters'] == len(PAST_SOURCE)


def test_history_calibration_adds_one_exact_read_without_changing_original_targets():
    from utopia.optimization.native_designer_preflight import planned_cases
    original = planned_cases(request(), 'staged-v15')
    with_history = planned_cases(failed_request(), 'staged-v15')
    extra = [c for c in with_history if c['id'] == 'sequence-read-own-history']
    assert len(original) == 27 and len(with_history) == 28 and len(extra) == 1
    assert [c for c in with_history if c['id'] != extra[0]['id']] == original
    assert extra[0]['expected'] == {'tool': 'read_file',
        'filename': PREFIX + 'code/' + quote(ALPHA, safe='._-') + '.py'}


def test_history_probe_and_explicit_reuse_cold_replay_without_any_container_execution(tmp_path):
    from tests.optimization.test_native_staged_author_v15 import Model, author
    from utopia.optimization.native_staged_author_v15 import replay_staged_generation
    body = failed_request(); target = PREFIX + 'code/' + quote(ALPHA, safe='._-') + '.py'
    model = Model([PLAN, {'tool': 'read_file', 'filename': target},
        {'tool': 'write_file', 'filename': 'code/' + quote(ALPHA, safe='._-') + '.py', 'content': PAST_SOURCE},
        {'tool': 'finish', 'rationale': 'SCRIPTED explicit reuse, not automatic adoption or a research result'}])
    definition = author(model, tmp_path, max_steps=5)(body)
    path = next(tmp_path.glob('generation-*'))
    assert len(model.calls) == 4 and definition['base_patch'] is not None
    replayed = replay_staged_generation(path, expected_request=body)
    assert replayed == definition
    assert len(model.calls) == 4
    tampered = deepcopy(body)
    tampered['history'][0]['observations'][0]['candidate']['metadata']['SCRIPTED_tamper'] = True
    with pytest.raises(ValueError, match='request differs'):
        replay_staged_generation(path, expected_request=tampered)
    assert len(model.calls) == 4


def test_mocked_real_transport_contract_includes_and_cold_replays_the_history_read(tmp_path, monkeypatch):
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession
    from tests.optimization.test_native_authoring_ir import BINDING
    from utopia.optimization.native_designer_preflight import run_calibration, require_certificate
    monkeypatch.setattr('requests.Session', ScriptedSession)
    directory = tmp_path / 'SCRIPTED_history_controls'
    result = run_calibration(directory, request=failed_request(), provider=BINDING)
    assert result['all_controls_passed'] and len(result['records']) == 28
    assert any(r['intent']['id'] == 'sequence-read-own-history' and r['ok'] for r in result['records'])
    assert require_certificate(directory / 'certificate.json', BINDING, protocol='staged-v15')['controls'] == 28


def test_missing_candidates_and_malformed_record_shapes_are_not_filled_from_parent():
    body = request(); body['history'] = [None, {'definition': None, 'observations': [None, {'status': 'failed'}]}]
    doc = body['parent_system']; index = json.loads(read_file(doc, 'history/index.json', request=body)['content'])
    assert len(index['trials']) == 2
    assert all(not o['candidate_present'] for t in index['trials'] for o in t['observations'])
    with pytest.raises(ValueError, match='unknown exact'):
        read_file(doc, 'history/trial-001/observation-001/system.json', request=body)


def test_archive_json_types_and_literal_strings_are_not_normalized():
    body = failed_request(); value = [True, 1, 1.0, -0.0, 9007199254740993, '研究者\n"quoted"\\n']
    body['history'][0]['observations'][0]['candidate']['metadata']['literal'] = value
    read = read_file(body['parent_system'], PREFIX + 'system/metadata.json', request=body)
    assert digest(json.loads(read['content'])['literal']) == digest(value)
