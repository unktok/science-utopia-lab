"""Scripted native original-world QA; never live Qwen/designer evidence."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.system.test_native_activity_contracts import authored_system
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_society_design import NativeSocietyDesignSession
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.design_patch import make_patch, digest
from utopia.system.native_activity_contracts import activity_world_system
from utopia.system.native_kernel import NativeScienceKernel
from utopia.utils.data_utils import file_sha256, write_json_atomic
from scripts.run_native_society_pilot_v6 import (
    ExternalSocietyProposer, SocietyPatchInbox, audit_society_pilot, run_society_pilot,
)


def prepare(root, executor):
    seed()
    founding = activity_world_system()
    session = NativeSocietyDesignSession(root / 'session', founding_system=founding,
        loss_spec=loss_spec(), world_binding={'evidence': 'scripted-real-native-QA-not-live'})
    sim, calls = make_sim(root / 'society', native=NativeScienceKernel(founding, code_executor=executor))
    sim.num_years = 3
    proposer = ExternalSocietyProposer(root / 'authoring-inbox', world_binding=session.binding['world'],
        domain_provider=lambda: session._domain(sim), runtime_image_id=executor.image_id)
    return session, sim, calls, proposer


def advance(root, executor, *, confirmations=()):
    session, sim, calls, proposer = prepare(root, executor)
    try:
        result = run_society_pilot(sim, session, proposer, output=root, confirm_request_sha256=confirmations)
        return result, session, list(calls)
    finally:
        sim.llm.response_cache.close()


def author_pending(root, result, executor):
    request_path = result['external']['request_path']
    saved = SocietyPatchInbox._read(__import__('pathlib').Path(request_path))
    request = saved['request']['authoring_input']
    parent = SystemSpec.from_dict(request['parent_system'])
    index = request['proposal_index']
    assert request['loss_spec'] == loss_spec()
    assert request['actual_domain']['ecosystem_data']['agents']
    assert request['feedback']['observations'][-1]['through_year'] == index + 1
    if index == 0:
        target = authored_system(executor.image_id)
        actions = {}
    else:
        assert request['feedback']['adoptions'] and request['feedback']['observations'][-1]['preceding_adoption']
        nodes = []
        for node in parent.mechanisms:
            if node.mechanism_id == 'invented-project-director':
                params = deepcopy(node.parameters)
                params['code_artifact']['source'] = params['code_artifact']['source'].replace(
                    'independent replication commons', 'feedback-conditioned revised replication commons')
                nodes.append(replace(node, parameters=params))
            else:
                nodes.append(node)
        target, actions = replace(parent, mechanisms=tuple(nodes)), {'invented-project-director': 'preserve'}
    operations = [{'op': 'replace', 'path': '/' + key, 'value': value}
        for key, value in target.to_dict().items() if parent.to_dict()[key] != value]
    manifest = {'patch': make_patch(parent, operations, rationale='Scripted native QA, not autonomous invention'),
        'state_actions': actions, 'discard_deliveries': {}}
    response = {'request_sha256': result['external']['request_sha256'], 'manifest': manifest,
        'authoring': {'kind': 'external', 'identity': 'scripted-test-designer', 'evidence': 'QA-only'}}
    write_json_atomic(result['external']['response_path'], response, sort_keys=True, allow_nan=False)
    return response


def hashes(root):
    return {str(p.relative_to(root)): file_sha256(p) for p in root.rglob('*') if p.is_file()}


def test_same_original_society_external_author_confirm_adopt_observe_revise_and_cold_resume(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    first, session, calls = advance(tmp_path, executor)
    assert first['status'] == 'waiting-for-external-authoring' and first['through_year'] == 1 and calls
    assert first['adoptions'] == 0 and first['loss_path']
    # Waiting is idempotent: reopen the exact founding config and saved society.
    waiting, _, replay_calls = advance(tmp_path, executor)
    assert waiting == first and not replay_calls
    author_pending(tmp_path, first, executor)
    staged, session, no_calls = advance(tmp_path, executor)
    assert staged['status'] == 'waiting-for-explicit-confirmation' and not no_calls
    assert staged['adoptions'] == 0 and session.projection()['pending']
    staged_again, _, no_calls = advance(tmp_path, executor)
    assert staged_again == staged and not no_calls
    # Wrong confirmation does not install anything or advance native science.
    wrong, _, no_calls = advance(tmp_path, executor, confirmations=['0' * 64])
    assert wrong == staged and not no_calls
    second, session, year2_calls = advance(tmp_path, executor, confirmations=[staged['confirm_request_sha256']])
    assert second['status'] == 'waiting-for-external-authoring' and second['through_year'] == 2 and year2_calls
    assert second['adoptions'] == 1 and len(second['loss_path']) == 2
    assert len(session.projection()['confirmations']) == 1
    author_pending(tmp_path, second, executor)
    staged2, session, no_calls = advance(tmp_path, executor)
    assert staged2['status'] == 'waiting-for-explicit-confirmation' and not no_calls
    # UI-equivalent consent is data-only and does not migrate the native kernel.
    request = session.projection()['pending']
    session.confirm(request_id=request['request_id'], confirmed_request_sha256=request['request_sha256'])
    assert len(session.projection()['adoptions']) == 1
    complete, session, year3_calls = advance(tmp_path, executor)
    assert complete['status'] == 'complete' and complete['through_year'] == 3 and year3_calls
    assert complete['adoptions'] == 2 and len(complete['loss_path']) == 3
    assert complete['population_reset'] is False and complete['causal_benefit_established'] is False
    before = hashes(tmp_path)
    audit = audit_society_pilot(session, inbox_directory=tmp_path / 'authoring-inbox')
    assert hashes(tmp_path) == before  # all byte contents preserved by read-only audit
    assert audit['loss_path'] == complete['loss_path'] and audit['adoptions'] == 2
    assert [r['actual_activity_effects'] for r in audit['rows']] == [0, 1, 1]
    assert [len(r['code']) for r in audit['rows']] == [0, 1, 1]
    assert audit['rows'][1]['code'][0]['source_sha256'] != audit['rows'][2]['code'][0]['source_sha256']
    done, _, no_calls = advance(tmp_path, executor)
    assert done == complete and not no_calls
    write_json_atomic(tmp_path / 'plan.json', {'protocol': {'loss': session.loss_spec},
        'world': session.binding['world'], 'founding_system': session.founding.to_dict()})
    # Standalone audit never constructs a factory or executes a container/model.
    from scripts.run_native_society_pilot_v6 import main
    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory.__init__',
        lambda *a, **k: pytest.fail('audit must not construct native factory'))
    monkeypatch.setattr(DockerCodeExecutor, 'execute', lambda *a, **k: pytest.fail('audit must not execute source'))
    monkeypatch.setattr('sys.argv', ['run_native_society_pilot_v6.py', '--output', str(tmp_path), '--audit-only'])
    before = hashes(tmp_path)
    main()
    assert hashes(tmp_path) == before


def test_consumed_external_response_raw_bytes_are_immutable(tmp_path):
    inbox = SocietyPatchInbox(tmp_path)
    with pytest.raises(ExternalAuthoringPending) as pending:
        inbox.generate(prompt='exact', seed_ctx=['one'])
    wait = pending.value
    write_json_atomic(wait.response_path, {'request_sha256': wait.request_sha256, 'manifest': {},
        'authoring': {'kind': 'external', 'identity': 'QA'}})
    assert inbox.generate(prompt='exact', seed_ctx=['one']) == ({}, [])
    # Semantically identical whitespace edits still change the consumed raw file.
    with wait.response_path.open('a') as stream:
        stream.write(' ')
    with pytest.raises(ValueError, match='changed'):
        SocietyPatchInbox(tmp_path)


def test_ambiguous_duplicate_response_keys_are_rejected(tmp_path):
    path = tmp_path / 'ambiguous.json'
    path.write_text('{"request_sha256":"one","request_sha256":"two"}')
    with pytest.raises(ValueError, match='Duplicate'):
        SocietyPatchInbox._read(path)


@pytest.mark.parametrize('field', ['model_digest', 'corpus_sha256', 'seed', 'source_commit'])
def test_changed_original_model_corpus_binding_cannot_reopen_session(tmp_path, field):
    founding = activity_world_system()
    original = {'model_digest': 'original', 'corpus_sha256': 'original', 'seed': 1301, 'source_commit': 'original'}
    NativeSocietyDesignSession(tmp_path, founding_system=founding, loss_spec=loss_spec(),
        world_binding=original)
    with pytest.raises(ValueError, match='binding'):
        NativeSocietyDesignSession(tmp_path, founding_system=founding, loss_spec=loss_spec(),
            world_binding={**original, field: 'changed'})


def test_invalid_external_source_is_a_preserved_null_loss_technical_failure(tmp_path, fixed_corpus):
    from utopia.runtime.checkpointing import PortableStop
    executor = DockerCodeExecutor()
    first, _, _ = advance(tmp_path, executor)
    response = author_pending(tmp_path, first, executor)
    # A malformed complete patch is retained, never repaired by the host.
    response['manifest']['patch']['parent_fingerprint'] = '0' * 64
    write_json_atomic(first['external']['response_path'], response, sort_keys=True, allow_nan=False)
    with pytest.raises(PortableStop):
        advance(tmp_path, executor)
    progress = json.loads((tmp_path / 'progress.json').read_text())
    assert progress['status'] == 'technical-failure'
    assert progress['failed_candidate_loss'] is None and progress['automatic_redraft'] is False
    assert progress['adoptions'] == 0 and len(progress['loss_path']) == 1
    assert len(list((tmp_path / 'authoring-inbox/requests').glob('*.json'))) == 1
