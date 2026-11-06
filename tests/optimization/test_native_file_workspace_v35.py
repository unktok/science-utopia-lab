"""SCRIPTED virtual-editor semantics only; no actual model or world claims."""
from copy import deepcopy
import json
from urllib.parse import quote

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, parent
from utopia.optimization.native_file_workspace_v35 import file_catalog, read_file, write_file_operations
from utopia.optimization.native_authoring_ir import translate_operations


def edited(document, filename, content):
    return translate_operations(document, write_file_operations(document, filename, content), stage='SCRIPTED-file-QA')[0]


def test_code_write_is_verbatim_and_preserves_runtime_abi_parameters_graph_and_parent():
    doc = parent().to_dict(); before = deepcopy(doc)
    filename = 'code/' + quote(ALPHA, safe='._-') + '.py'
    source = 'raise RuntimeError("NEVER_EXECUTE_SCRIPTED_SOURCE")\n# 研究者\\n\ndef step(context):\n    return {}\n'
    out = edited(doc, filename, source)
    expected = deepcopy(doc); expected['mechanisms'][0]['parameters']['code_artifact']['source'] = source
    assert out == expected and doc == before
    assert read_file(out, filename)['content'] == source
    assert read_file(out, filename)['complete']


def test_full_system_roundtrip_can_change_nodes_wires_schedule_and_unknown_data_without_merging():
    doc = parent().to_dict(); desired = deepcopy(doc)
    desired['mechanisms'].reverse(); desired['connections'] = [{'SCRIPTED': 'arbitrary new wiring'}]
    desired['schedules'] = [{'SCRIPTED': 'arbitrary new schedule'}]
    desired['new arbitrary root'] = {'value': [True, None, '界']}; del desired['metadata']
    assert edited(doc, 'system.json', json.dumps(desired)) == desired
    assert json.loads(read_file(doc, 'system.json')['content']) == doc
    assert write_file_operations(doc, 'system.json', json.dumps(doc)) == []


def test_root_file_replaces_whole_authored_value_not_a_parameter_merge():
    doc = parent().to_dict(); new = {'my independently authored field': 3}
    out = edited(doc, 'system/initial_state.json', json.dumps(new))
    assert out['initial_state'] == new
    assert 'coordinate' not in out['initial_state']


@pytest.mark.parametrize('before,after', [(1, True), (0, False), (1, 1.0), (0.0, -0.0)])
def test_whole_system_edits_do_not_confuse_python_equal_but_distinct_json_values(before, after):
    doc = parent().to_dict(); doc['metadata'] = {'literal': before}
    wanted = deepcopy(doc); wanted['metadata'] = {'literal': after}
    out = edited(doc, 'system.json', json.dumps(wanted))
    assert json.dumps(out['metadata'], sort_keys=True) == json.dumps(wanted['metadata'], sort_keys=True)
    assert write_file_operations(doc, 'system.json', json.dumps(wanted))


@pytest.mark.parametrize('identity', ['new-institution', 'a/b%2F', '../escape', '研究所~x', 'a.py'])
def test_new_nodes_and_arbitrary_literal_id_encoding_never_access_host_files(identity):
    doc = parent().to_dict(); node = {'mechanism_id': identity, 'custom': {'no template': True}}
    filename = 'new/' + quote(identity, safe='._-') + '.json'
    out = edited(doc, filename, json.dumps(node))
    assert out['mechanisms'] == doc['mechanisms'] + [node]
    existing = 'nodes/' + quote(identity, safe='._-') + '.json'
    assert json.loads(read_file(out, existing)['content']) == node
    with pytest.raises(ValueError): write_file_operations(out, filename, json.dumps(node))


@pytest.mark.parametrize('filename', ['/etc/passwd', '../../.ssh/id_rsa', 'code/absent.py', 'nodes/absent.json'])
def test_unknown_files_are_not_guessed_repaired_or_used_as_os_paths(filename):
    doc = parent().to_dict()
    with pytest.raises(ValueError): read_file(doc, filename)
    with pytest.raises(ValueError): write_file_operations(doc, filename, 'never a filesystem write')


@pytest.mark.parametrize('content', ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', 'not JSON'])
def test_json_files_are_strict_and_never_salvaged(content):
    with pytest.raises(ValueError): write_file_operations(parent().to_dict(), 'system/metadata.json', content)


def test_slices_have_explicit_omissions_and_unambiguous_aliases_only():
    doc = parent().to_dict()
    whole = read_file(doc, 'system.json'); piece = read_file(doc, 'system.json', offset=3, limit=8)
    assert piece['content'] == whole['content'][3:11]
    assert not piece['complete'] and not piece['slice_reaches_end']
    assert piece['content_sha256'] == whole['content_sha256']
    doc['mechanisms'].append(deepcopy(doc['mechanisms'][0]))
    catalog = file_catalog(doc)
    assert catalog['ambiguous_node_ids_without_aliases'] == [ALPHA]
    assert 'code/' + ALPHA + '.py' not in {f['filename'] for f in catalog['files']}
    assert json.loads(read_file(doc, 'system/mechanisms.json')['content']) == doc['mechanisms']


def test_file_tools_share_literal_editor_validation_and_do_not_hide_invalid_drafts():
    from tests.optimization.test_native_authoring_ir import request
    from tests.optimization.test_native_staged_author_v15 import apply
    from utopia.optimization.native_staged_author_v15 import initial_draft
    body = request(); state = initial_draft(body)
    content = 'def step(context):\n    return {"outputs": {}, "state": {}}\n'
    changed, receipt = apply(state, {'tool': 'write_file', 'filename': 'code/' + ALPHA + '.py', 'content': content}, body)
    assert receipt['ok'] and receipt['tool'] == 'write_file' and receipt['result']['validation']['valid']
    assert changed['document']['mechanisms'][0]['parameters']['code_artifact']['source'] == content
    assert receipt['result']['literal_document_changed']
    # Deliberate malformed node replacement stays an explicit invalid draft;
    # the interface never supplies a missing runtime/ABI on the author's behalf.
    broken = deepcopy(changed['document']['mechanisms'][0]); broken['parameters'] = {}
    invalid, edited_receipt = apply(changed, {'tool': 'write_file', 'filename': 'nodes/' + ALPHA + '.json',
        'content': json.dumps(broken)}, body)
    assert edited_receipt['ok'] and not edited_receipt['result']['validation']['valid']
    _, finish = apply(invalid, {'tool': 'finish', 'rationale': 'SCRIPTED invalid draft'}, body)
    assert not finish['ok'] and finish['definition'] is None


def test_file_read_write_finish_cold_replay_and_observed_ui_keep_exact_actions(tmp_path):
    from tests.optimization.test_native_authoring_ir import request
    from tests.optimization.test_native_planning_author_v22 import PLAN
    from tests.optimization.test_native_staged_author_v15 import author, Model
    from utopia.optimization.native_staged_author_v15 import project_authoring_trace
    body = request(); filename = 'code/' + ALPHA + '.py'
    source = body['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source'] + '# SCRIPTED file edit\n'
    actions = [PLAN, {'tool': 'read_file', 'filename': filename},
               {'tool': 'write_file', 'filename': filename, 'content': source},
               {'tool': 'finish', 'rationale': 'SCRIPTED interface, no scientific invention'}]
    generator = author(Model(actions), tmp_path, max_steps=4)
    definition = generator(body)
    assert 'generation_failure' not in definition
    assert generator(body) == definition  # No provider actions remain; redispatch would fail.
    trace = project_authoring_trace(tmp_path, allowed_requests=[body], provider_binding=generator.provider_binding,
        settings=generator.settings, authoring_protocol=generator.protocol)
    assert trace['warnings'] == []
    steps = trace['generations'][0]['steps']
    assert [s['status'] for s in steps] == ['applied', 'applied', 'applied', 'finished']
    assert steps[2]['authored_output']['content'] == source
    assert steps[1]['result']['value'] == body['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source']


def test_native_wire_uses_an_explicit_file_index_and_reads_restore_exact_source():
    from tests.optimization.test_native_authoring_ir import IMAGE, request
    from tests.optimization.test_native_planning_author_v22 import PLAN
    from tests.optimization.test_native_staged_author_v15 import apply
    from utopia.optimization.native_staged_author_v15 import initial_draft, build_prompt, build_conversation, SYSTEM_PROMPT
    body = request(); state, plan = apply(initial_draft(body), PLAN, body)
    steps = [{'step': 0, 'status': 'applied', 'model_reply': {'output': PLAN}, 'transition': plan, 'errors': []}]
    raw = build_prompt(body, state, steps, image_id=IMAGE, binding_sha256='d' * 64, settings={'max_steps': 8})
    messages = build_conversation(raw, SYSTEM_PROMPT, native_tools=True)
    context = json.loads(messages[1]['content'].split('EXACT SESSION DATA\n', 1)[1])
    assert 'literal_editor_workbench' not in context
    assert context['virtual_editor_workspace']['all_file_names_included']
    assert context['prompt_view']['virtual_file_index_only']
    assert context['prompt_view']['full_current_draft_included'] is False
    assert 'DO_NOT_EXECUTE_GENERATED_SOURCE' not in json.dumps(messages)
    action = {'tool': 'read_file', 'filename': 'code/' + ALPHA + '.py'}
    state, receipt = apply(state, action, body)
    steps.append({'step': 1, 'status': 'applied', 'model_reply': {'output': action}, 'transition': receipt, 'errors': []})
    wire = build_conversation(build_prompt(body, state, steps, image_id=IMAGE,
        binding_sha256='d' * 64, settings={'max_steps': 8}), SYSTEM_PROMPT, native_tools=True)
    assert 'DO_NOT_EXECUTE_GENERATED_SOURCE' in json.dumps(wire)
    assert wire[1]['role'] == 'user' and body['loss_spec']['id'] in raw


def test_large_unicode_reads_are_explicitly_omitted_not_silently_truncated():
    from tests.optimization.test_native_authoring_ir import request
    from tests.optimization.test_native_staged_author_v15 import apply
    from utopia.optimization.native_staged_author_v15 import initial_draft
    body = request(); body['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source'] = '界' * 100000
    state = initial_draft(body)
    same, receipt = apply(state, {'tool': 'read_file', 'filename': 'code/' + ALPHA + '.py'}, body)
    assert receipt['ok'] and same == state and not receipt['result']['value_included']
    assert 'value' not in receipt['result'] and receipt['result']['reason']
    _, small = apply(state, {'tool': 'read_file', 'filename': 'code/' + ALPHA + '.py', 'limit': 1000}, body)
    assert small['result']['value'] == '界' * 1000 and not small['result']['complete']
