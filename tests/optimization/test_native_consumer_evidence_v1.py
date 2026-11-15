"""Native source attribution and SCRIPTED authoring; no scientific inference."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE, request
from tests.optimization.test_native_bounded_author_context_v45 import Model, frame
from utopia.optimization import native_consumer_evidence_v1 as evidence
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING as PROFILE
from utopia.optimization.native_parent_evidence_v46 import OPTION as PARENT_OPTION, MODE as PARENT_MODE
from utopia.optimization.native_staged_author_v15 import (
    StagedVocabularyGenerator, initial_draft, replay_staged_generation)
from utopia.system.design_patch import digest


def body():
    value = request()
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=evidence.ROOT, text=True).strip()
    value.setdefault('world_binding', {})['source_commit'] = source
    value['strategy_provenance'] = {evidence.OPTION: evidence.build(source_commit=source)}
    return value


def test_literal_native_evidence_is_exact_committed_source_without_neighboring_control():
    value = body(); pack = value['strategy_provenance'][evidence.OPTION]
    assert len(pack['cards']) == 6 and len(json.dumps(pack).encode()) < evidence.MAX_BYTES
    assert not pack['new_model_calls'] and not pack['new_code_executions']
    assert not pack['source_repair'] and not pack['veto_on_finish']
    for card in pack['cards']:
        raw = (evidence.ROOT / card['path']).read_bytes()
        assert evidence.sha(raw) == card['whole_file_sha256']
        exact = ''.join(raw.decode().splitlines(keepends=True)[card['first_line']-1:card['last_line']])
        assert card['literal_source'] == exact
        assert card['excerpt_utf8_sha256'] == evidence.sha(exact.encode())
    catalog = next(c for c in pack['cards'] if c['qualified_name'] == 'validate_catalog_assignment')
    assert 'def validate_catalog_assignment' in catalog['literal_source']
    assert 'def catalog_agenda_control' not in catalog['literal_source']
    assert 'def step(context)' not in catalog['literal_source']
    assert 'terminal-consolidation' not in json.dumps(pack)


def test_all_active_source_is_user_data_never_promoted_to_trusted_instructions():
    value = body(); before = deepcopy(value)
    prompt, messages = frame(value, initial_draft(value), [])
    data = json.loads(prompt)
    assert data['literal_native_consumer_source_evidence'] == value['strategy_provenance'][evidence.OPTION]
    sent, _ = json.JSONDecoder().raw_decode(messages[1]['content'].split('BOUNDED ACTIVE SESSION DATA\n', 1)[1])
    assert sent['literal_native_consumer_source_evidence'] == data['literal_native_consumer_source_evidence']
    for card in data['literal_native_consumer_source_evidence']['cards']:
        assert card['literal_source'] not in messages[0]['content']
    assert value == before


def test_absent_evidence_does_not_change_existing_control_frame():
    value = request(); before = deepcopy(value)
    prompt, _ = frame(value, initial_draft(value), [])
    assert 'literal_native_consumer_source_evidence' not in json.loads(prompt)
    assert evidence.in_request(value, conversation_profile=PROFILE) is None
    assert value == before


@pytest.mark.parametrize('mutation', ['raw-body', 'resealed-body', 'missing', 'extra', 'source', 'wrong-profile', 'nonobject'])
def test_wrong_native_source_or_scope_never_silently_degrades_to_control(mutation):
    value = body(); pack = value['strategy_provenance'][evidence.OPTION]
    profile = PROFILE
    if mutation in ('raw-body', 'resealed-body'): pack['cards'][0]['literal_source'] += '# not actual source\n'
    if mutation == 'missing': pack['cards'].pop()
    if mutation == 'extra': pack['recommended_edit'] = 'not part of literal selection'
    if mutation == 'source': value['world_binding']['source_commit'] = 'f' * 40
    if mutation == 'wrong-profile': profile = 'plain-function-recovery-v44'
    if mutation == 'nonobject': value['strategy_provenance'][evidence.OPTION] = True
    if mutation in ('resealed-body', 'missing', 'extra'):
        del pack['content_sha256']; pack['content_sha256'] = digest(pack)
    with pytest.raises(ValueError): evidence.in_request(value, conversation_profile=profile)


def test_binding_rejects_unsupported_profile_before_any_model_calls(tmp_path):
    value = body(); model = Model([])
    model.conversation_profile = 'plain-function-recovery-v44'
    author = StagedVocabularyGenerator(model, tmp_path/'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=16, max_tokens=8192,
        conversation_profile='plain-function-recovery-v44')
    with pytest.raises(ValueError, match='bounded author profile'): author(value)
    assert not model.calls


def test_complete_retained_native_parent_plus_evidence_fits_declared_wire_bytes_not_token_claim():
    from utopia.optimization.native_bounded_author_context_v45 import capacity_observation, MAX_WIRE_BYTES
    from utopia.optimization.native_designer_decoding_v24 import designer_payload
    value = body()
    literal = json.loads((evidence.ROOT / 'research/data/native-terminal-cost-pilot-v1/systems/strong-related-reference.json').read_text())
    value['parent_system'] = value['initial_system'] = literal
    value['strategy_provenance'][PARENT_OPTION] = PARENT_MODE
    prompt, messages = frame(value, initial_draft(value), [])
    data = json.loads(prompt)
    assert data['literal_current_system'] == literal
    payload = designer_payload('staged-v15', BINDING, messages, [], max_tokens=8192,
                              temperature=.6, conversation_profile=PROFILE)
    observation = capacity_observation(payload)
    assert observation['actual_wire_utf8_bytes'] <= MAX_WIRE_BYTES
    assert observation['full_output_reservation_fits_observed_prompt'] is None
    assert 'literal_native_consumer_source_evidence' in data


def test_actual_editor_and_cold_replay_retain_literal_evidence_and_legal_unchanged_parent(tmp_path):
    value = body(); original = deepcopy(value)
    model = Model([{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED retain'},
                   {'tool': 'finish'}])
    author = StagedVocabularyGenerator(model, tmp_path/'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=16, max_tokens=8192, conversation_profile=PROFILE)
    result = author(value)
    directory = next((tmp_path/'author').glob('generation-*'))
    assert replay_staged_generation(directory) == result and len(model.calls) == 2
    assert 'generation_failure' not in result and value == original
    assert all(json.loads(call['prompt'])['literal_native_consumer_source_evidence'] ==
               value['strategy_provenance'][evidence.OPTION] for call in model.calls)


def test_stale_build_commit_or_modified_native_file_fails_without_source_repair(tmp_path):
    with pytest.raises(ValueError, match='full source commit'):
        evidence.build(source_commit='not-a-commit')
    raw = 'class Agent:\n    def f(self):\n        return 0\n'
    (tmp_path/'sample.py').write_text(raw)
    card = evidence.source_card(tmp_path, 'sample.py', 'Agent.f')
    assert card['literal_source'] == '    def f(self):\n        return 0\n'
    with pytest.raises(ValueError, match='exact unique source declaration'):
        evidence.source_card(tmp_path, 'sample.py', 'Agent.missing')


def test_build_rejects_an_actually_modified_selected_file_against_real_git_commit(tmp_path):
    paths = [p for p, _ in evidence.SELECTION] + ['utopia/optimization/native_consumer_evidence_v1.py']
    for name in paths:
        target = tmp_path / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((evidence.ROOT / name).read_bytes())
    subprocess.run(['git', 'init', '-q', '--initial-branch=qa'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', *paths], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=SCRIPTED', '-c', 'user.email=qa@example.invalid',
                    'commit', '-qm', 'SCRIPTED immutable selected-source check'], cwd=tmp_path, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, text=True).strip()
    assert evidence.build(source_root=tmp_path, source_commit=commit)['source_commit'] == commit
    changed = tmp_path / paths[0]
    changed.write_bytes(changed.read_bytes() + b'\n# SCRIPTED source drift\n')
    before = changed.read_bytes()
    with pytest.raises(ValueError, match='differs from bound committed source'):
        evidence.build(source_root=tmp_path, source_commit=commit)
    assert changed.read_bytes() == before


def test_oversized_evidence_is_rejected_not_truncated_or_omitted(monkeypatch):
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=evidence.ROOT, text=True).strip()
    monkeypatch.setattr(evidence, 'MAX_BYTES', 128)
    with pytest.raises(ValueError, match='no truncation/fallback'):
        evidence.build(source_commit=source)
