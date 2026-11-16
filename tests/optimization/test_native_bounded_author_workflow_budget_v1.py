"""Real native document boundary data; no inference or candidate execution."""
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import request
from tests.optimization.test_native_bounded_author_context_v45 import frame
from utopia.optimization.native_staged_author_v15 import initial_draft, call_task, StagedVocabularyGenerator, replay_staged_generation
from utopia.optimization.native_authoring_recovery_v44 import workflow, IMPLEMENT_TASK
from utopia.optimization.native_bounded_author_context_v45 import compact, MAX_ACTIVE_DOCUMENT_BYTES, context_contract
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.system.design_patch import digest

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/native_author_context_boundary_v1'
CASES = [('parent-zero', 61892, 65479), ('parent-terminal', 62755, 66342),
         ('after-feature-write', 62032, 65619)]


@pytest.fixture(autouse=True)
def forbid_candidate_execution(monkeypatch):
    def forbidden(*a, **kw): pytest.fail('boundary regression must never execute generated code')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


def inspected(body):
    state = initial_draft(body)
    steps = [{'step': i, 'status': 'applied', 'errors': [],
        'model_reply': {'output': {'tool': 'read_file', 'filename': 'system.json'}},
        'transition': {'tool': 'read_file', 'ok': True,
            'draft_before_sha256': digest(state), 'draft_after_sha256': digest(state)}} for i in range(3)]
    return state, steps


@pytest.mark.parametrize('name,compact_bytes,legacy_bytes', CASES)
def test_full_document_actually_supplied_must_enable_its_implementation_checkpoint(name, compact_bytes, legacy_bytes):
    doc = json.loads((FIXTURES / (name + '.json')).read_text())
    assert len(json.dumps(doc, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=(',', ':')).encode()) == compact_bytes
    assert len(json.dumps(doc, ensure_ascii=False, allow_nan=False).encode()) == legacy_bytes
    body = request(); body['parent_system'] = doc; state, steps = inspected(body)
    prompt, _ = frame(body, state, steps); data = json.loads(prompt)
    flow = data['000_current_turn']['authoring_workflow']
    assert data['literal_current_system'] == doc and flow['literal_current_system_included']
    assert flow['successful_inspections_since_last_document_change'] == 3
    assert flow['phase'] == 'implementation'
    assert call_task(len(steps), 16, conversation_profile=BOUNDED_AUTHORING, prompt=prompt) == IMPLEMENT_TASK
    # V44's default byte rule is unchanged. Only V45's actual projection is
    # corrected; historical source-bound receipts/certificates are not reused.
    assert workflow(state, steps, max_steps=16)['phase'] == (
        'implementation' if legacy_bytes <= 65536 else 'general')


def test_prospective_contract_names_visibility_revision_and_exact_byte_budget():
    contract = context_contract()
    assert contract['prospective_context_revision'] == 'matched-bounded-author-64k-v2-literal-visibility'
    assert contract['max_literal_document_utf8_bytes'] == MAX_ACTIVE_DOCUMENT_BYTES == 65536
    assert contract['literal_document_visibility_controls_workflow'] is True
    assert contract['automatic_context_truncation'] is False and contract['source_repair'] is False


@pytest.mark.parametrize('target,phase', [(65536, 'implementation'), (65537, 'general')])
def test_exact_utf8_projection_boundary_controls_body_and_phase_together(target, phase):
    doc = json.loads((FIXTURES / 'parent-zero.json').read_text()); doc['metadata']['utf8_boundary'] = ''
    remaining = target - len(compact(doc).encode())
    doc['metadata']['utf8_boundary'] = 'é' * (remaining // 2) + 'x' * (remaining % 2)
    assert len(compact(doc).encode()) == target
    body = request(); body['parent_system'] = doc; state, steps = inspected(body)
    prompt, _ = frame(body, state, steps); data = json.loads(prompt); included = target <= MAX_ACTIVE_DOCUMENT_BYTES
    assert data['000_current_turn']['authoring_workflow']['phase'] == phase
    assert data['000_current_turn']['authoring_workflow']['literal_current_system_included'] is included
    assert (data['literal_current_system'] == doc) is included
    assert (data['literal_current_system'] is None) is (not included)


@pytest.mark.parametrize('invalid', [0, 1, {}, 'true'])
def test_visibility_override_is_not_an_untrusted_truthy_value(invalid):
    body = request(); state, steps = inspected(body)
    with pytest.raises(ValueError, match='source-owned boolean'):
        workflow(state, steps, max_steps=16, literal_document_included=invalid)


def test_real_edit_crossing_legacy_limit_resets_reads_but_does_not_disable_next_checkpoint():
    before = request(); before['parent_system'] = json.loads((FIXTURES / 'parent-zero.json').read_text())
    after = request(); after['parent_system'] = json.loads((FIXTURES / 'after-feature-write.json').read_text())
    old_state, old_reads = inspected(before); state, new_reads = inspected(after)
    write = {'step': 3, 'status': 'applied', 'errors': [],
        'model_reply': {'output': {'tool': 'write_file'}}, 'transition': {'tool': 'write_file', 'ok': True,
            'draft_before_sha256': digest(old_state), 'draft_after_sha256': digest(state)}}
    prompt, _ = frame(after, state, old_reads + [write])
    assert json.loads(prompt)['000_current_turn']['authoring_workflow']['phase'] == 'general'
    for i, item in enumerate(new_reads, 4): item['step'] = i
    prompt, _ = frame(after, state, old_reads + [write] + new_reads)
    assert json.loads(prompt)['000_current_turn']['authoring_workflow']['phase'] == 'implementation'


@pytest.mark.parametrize('remaining,phase', [(3, 'submit'), (2, 'recovery'), (1, 'submit')])
def test_submission_reserve_precedes_implementation_without_changing_budget(remaining, phase):
    body = request(); body['parent_system'] = json.loads((FIXTURES / 'parent-terminal.json').read_text())
    state, reads = inspected(body)
    steps = [dict(reads[0], step=i) for i in range(16 - remaining)]
    prompt, _ = frame(body, state, steps); flow = json.loads(prompt)['000_current_turn']['authoring_workflow']
    assert flow['phase'] == phase and flow['remaining_calls_including_this_one'] == remaining
    assert flow['submission_reserve'] == 3 and flow['all_calls_charged'] and not flow['host_auto_submit']


@pytest.mark.parametrize('name,_,__', CASES)
def test_real_native_boundary_document_reaches_scripted_generator_wire_and_cold_replay(tmp_path, monkeypatch, name, _, __):
    from tests.optimization import test_native_json_history_v40 as dialogue
    from tests.optimization.test_native_bounded_author_context_v45 import Model
    from scripts.analyze_native_staged_search_v15 import _transport, CLASSIFICATION
    doc = json.loads((FIXTURES / (name + '.json')).read_text()); body = request(); body['parent_system'] = doc
    image = next(n['parameters']['runtime_image_id'] for n in doc['mechanisms']
        if n['implementation'] == 'code.python.v1')
    # The real document/image is preserved; only the already SCRIPTED dialogue
    # fixture's provider binding is adapted. No model, image or code is loaded.
    binding = {**dialogue.BINDING, 'image_id': image}
    monkeypatch.setattr(dialogue, 'BINDING', binding)
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED interface regression',
        'design_intent': 'Explicitly retain the existing draft, not a scientific result.'}]
    actions += [{'tool': 'read_file', 'filename': 'system.json'} for _ in range(3)]
    actions += [{'tool': 'finish'}]
    model = Model(actions)
    generator = StagedVocabularyGenerator(model, tmp_path / 'author', image_id=image,
        provider_binding=binding, max_steps=16, max_tokens=8192, conversation_profile=BOUNDED_AUTHORING)
    result = generator(body)
    assert 'generation_failure' not in result and len(model.calls) == 5
    directory = next((tmp_path / 'author').glob('generation-*'))
    last = json.loads((directory / 'step-04.completed.json').read_text())
    messages = last['model_reply']['transport']['request_payload']['messages']
    data_text = next(m['content'] for m in messages if m['role'] == 'user'
        and m.get('content', '').startswith('BOUNDED ACTIVE SESSION DATA\n'))
    view = json.JSONDecoder().raw_decode(data_text.split('\n', 1)[1])[0]
    assert view['literal_current_system'] == doc
    assert view['000_current_turn']['authoring_workflow']['phase'] == 'implementation'
    before = {f.name: f.read_bytes() for f in directory.glob('*.json')}
    assert replay_staged_generation(directory) == result and len(model.calls) == 5
    assert before == {f.name: f.read_bytes() for f in directory.glob('*.json')}
    saved_binding = json.loads((directory / 'request.json').read_text())
    for i in range(5):
        completed = json.loads((directory / f'step-{i:02d}.completed.json').read_text())
        started = json.loads((directory / f'step-{i:02d}.started.json').read_text())
        assert _transport(completed, started, saved_binding, CLASSIFICATION)['known_designer_response']
