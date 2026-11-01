"""Scripted original-world QA only: no live model, Docker, or empirical finding."""
from copy import deepcopy
import json

import pytest

from scripts.analyze_native_society_v6 import (
    FIXTURE, SOURCE_COMMIT, analyze, inventory, protocol_classification,
)
from scripts.run_native_society_pilot_v6 import (
    INTERPRETATION, SCHEMA, ExternalSocietyProposer, run_society_pilot,
    write_society_server_config,
)
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_society_pilot_v6 import author_pending
from tests.optimization.test_native_world import loss_spec
from utopia.models.response_cache import CompletedResponseCache
from utopia.optimization.native_code_trace import RecordingCodeExecutor
from utopia.optimization.native_factory import record_native_http
from utopia.optimization.native_society_design import NativeSocietyDesignSession
from utopia.system.code_mechanisms import CodeExecution, sha
from utopia.system.native_activity_contracts import activity_world_system
from utopia.system.native_kernel import NativeScienceKernel
from utopia.utils.data_utils import write_json_atomic


class ScriptedExecutor:
    """Declared test algorithm, not execution of saved Python or a container."""
    image_id = 'sha256:' + '1' * 64

    def execute(self, artifact, context):
        assignment = deepcopy(context['inputs']['plans'][0]['payload']['assignments'][0])
        assignment['detailed_focus'] = 'Scripted QA activity effect'
        amendment = {'schema': 'native-research-amendment-v1', 'target_year': context['period'],
            'assignment': assignment, 'submit': assignment['project_end_year'] == context['period']}
        result = {'outputs': {'amendments': [{'payload': amendment}]}, 'state': {'cycles': context['period']}}
        return CodeExecution(result, {'image_id': self.image_id, 'artifact_sha256': sha(artifact),
            'context_sha256': sha(context), 'result_sha256': sha(result), 'wall_seconds': 0.0})


@pytest.fixture
def prepared(tmp_path, fixed_corpus, monkeypatch):
    return prepare_fixture(tmp_path, monkeypatch)


def prepare_fixture(tmp_path, monkeypatch):
    from tests.runtime import test_portable_checkpoint_integration as fixture
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    protocol = {'schema': SCHEMA, 'kind': 'scripted-same-society-audit-fixture-v6', 'evidence': FIXTURE,
        'loss': loss_spec(), 'years': 3, 'adoptions': 2, 'technical_drafts_per_boundary': 1,
        'interpretation': INTERPRETATION}
    binding = deepcopy(fixture.BINDING)
    binding['science_config']['source_commit'] = SOURCE_COMMIT
    monkeypatch.setattr(fixture, 'BINDING', binding)
    founding = activity_world_system()
    world = {'source_commit': SOURCE_COMMIT, 'years': 3, 'seed': 42, 'model': binding['model'],
        'model_digest': binding['model_revision'], 'corpus_sha256': binding['corpus_sha256'],
        'image_id': ScriptedExecutor.image_id, 'protocol': protocol}
    write_json_atomic(tmp_path / 'plan.json', {'protocol': protocol, 'world': world, 'founding_system': founding.to_dict()})
    cell = tmp_path / 'runs/persistent-society'
    write_json_atomic(cell / 'system.json', founding.to_dict())

    def advance(confirmations=()):
        seed()
        session = NativeSocietyDesignSession(tmp_path / 'session', founding_system=founding,
            loss_spec=loss_spec(), world_binding=world)
        executor = RecordingCodeExecutor(ScriptedExecutor(), cell / 'code-contexts.jsonl', binding={
            'source_commit': SOURCE_COMMIT, 'system_fingerprint': founding.fingerprint, 'run_id': 'persistent-society'})
        sim, calls = make_sim(cell, native=NativeScienceKernel(founding, code_executor=executor))
        sim.num_years = 3
        sim.llm.response_cache.close()
        sim.llm.response_cache = CompletedResponseCache(cell / 'replies/responses.sqlite', binding=binding)
        record_native_http(sim.llm, sim, cell / 'wire-requests.jsonl')
        write_society_server_config(tmp_path, session, checkpoint_directory=sim.output_dir)
        proposer = ExternalSocietyProposer(tmp_path / 'authoring-inbox', world_binding=world,
            domain_provider=lambda: session._domain(sim), runtime_image_id=executor.image_id)
        try:
            result = run_society_pilot(sim, session, proposer, output=tmp_path, confirm_request_sha256=confirmations)
            return result, session
        finally:
            sim.llm.response_cache.close()
    return tmp_path, advance


def finish(root, advance):
    result, session = advance()
    for _ in range(2):
        author_pending(root, result, ScriptedExecutor())
        staged, session = advance()
        assert staged['status'] == 'waiting-for-explicit-confirmation'
        result, session = advance([staged['confirm_request_sha256']])
    assert result['status'] == 'complete'
    return session


def test_complete_scripted_same_society_independent_whole_audit(prepared, monkeypatch):
    root, advance = prepared
    session = finish(root, advance)
    # Analyzer must not accidentally construct a factory, container or model.
    def forbidden(*args, **kwargs):
        raise AssertionError('audit attempted execution/inference')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.__init__', forbidden)
    monkeypatch.setattr('utopia.optimization.native_factory.LocalQwenNativeFactory.__init__', forbidden)
    before = inventory(root)
    report = analyze(root)
    assert inventory(root) == before
    assert report['classification'] == FIXTURE and report['status'] == 'complete'
    assert report['loss_path'] == [o['loss'] for o in session.projection()['observations']]
    assert report['physical_societies'] == 1 and report['audit_new_model_calls'] == 0
    assert len(report['adoptions']) == 2 and len(report['rows']) == 3
    assert report['cumulative_responses_per_year'][-1] == report['researcher_responses']
    assert report['uncheckpointed_responses'] == 0
    assert [r['actual_activity_effects'] for r in report['rows']] == [0, 1, 1]
    assert report['code_contexts']['checkpointed_executions'] == 2
    assert all(r['pre_adoption_society_sha256'] for r in report['rows'][:2])


def test_pending_is_incomplete_never_success_and_has_no_loss_for_future_year(prepared):
    root, advance = prepared
    advance()
    with pytest.raises(ValueError, match='incomplete'):
        analyze(root)
    before = inventory(root)
    report = analyze(root, require_complete=False)
    assert inventory(root) == before
    assert report['status'] == 'incomplete' and report['native_status'] == 'waiting-for-external-authoring'
    assert len(report['rows']) == len(report['loss_path']) == 1
    assert not report['adoptions']


def test_actual_classification_cannot_be_inferred_from_a_scripted_world(prepared):
    root, advance = prepared
    plan = json.loads((root / 'plan.json').read_text())
    plan['protocol'].pop('evidence')
    plan['world']['protocol'] = plan['protocol']
    with pytest.raises(ValueError, match='explicit non-live'):
        protocol_classification(plan, SOURCE_COMMIT)
    plan['protocol']['kind'] = 'external-native-same-society-v6'
    with pytest.raises(ValueError, match='actual fixed-Qwen'):
        protocol_classification(plan, SOURCE_COMMIT)
    with pytest.raises(ValueError, match='pinned source'):
        analyze(root, require_complete=False, expected_source='wrong-source')


def test_actual_checkpoint_non_design_tamper_is_detected(prepared):
    from utopia.runtime.checkpointing import read_portable_checkpoint, write_portable_checkpoint
    root, advance = prepared
    finish(root, advance)
    config = json.loads((root / 'society-session-config.json').read_text())
    from pathlib import Path
    path = Path(config['checkpoint_directory']) / 'portable_checkpoint_year_1.json.gz'
    saved = read_portable_checkpoint(path)
    saved['portable']['llm_call_stats']['prompt_tokens'] += 1
    write_portable_checkpoint(path, saved)
    with pytest.raises(ValueError, match='non-design'):
        analyze(root)


def test_actual_code_context_tamper_is_detected(prepared):
    root, advance = prepared
    finish(root, advance)
    path = root / 'runs/persistent-society/code-contexts.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]['receipt']['context_sha256'] = '0' * 64
    rows[0]['bundle_sha256'] = sha({k: v for k, v in rows[0].items() if k != 'bundle_sha256'})
    # This is intentional fixture corruption, never a raw actual-run edit.
    path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    with pytest.raises(ValueError, match='container receipt'):
        analyze(root)


def test_partial_year_response_is_physical_not_an_extra_scored_observation(prepared):
    import sqlite3
    from utopia.runtime.checkpointing import canonical_json
    import hashlib
    root, advance = prepared
    advance()
    cell = root / 'runs/persistent-society'
    wire_path = cell / 'wire-requests.jsonl'
    wire = json.loads(wire_path.read_text().splitlines()[0])
    wire['year'] = 2
    wire['payload']['extra_body']['seed'] += 99
    wire['payload_sha256'] = hashlib.sha256(canonical_json(wire['payload']).encode()).hexdigest()
    with wire_path.open('a') as stream:
        stream.write(json.dumps(wire) + '\n')
    with sqlite3.connect(cell / 'replies/responses.sqlite') as database:
        row = list(database.execute('SELECT * FROM replies LIMIT 1').fetchone())
        row[0], row[1] = 'a' * 64, wire['payload_sha256']
        database.execute('INSERT INTO replies VALUES (?,?,?,?,?)', row)
    progress = json.loads((root / 'progress.json').read_text())
    progress.update(status='technical-failure', failed_candidate_loss=None, automatic_redraft=False,
        error_type='FixtureInfrastructureFailure', error='Explicit scripted partial-year QA')
    write_json_atomic(root / 'progress.json', progress)
    before = inventory(root)
    report = analyze(root, require_complete=False)
    assert inventory(root) == before
    assert report['status'] == 'incomplete' and report['native_status'] == 'technical-failure'
    assert report['uncheckpointed_responses'] == 1
    assert len(report['loss_path']) == len(report['rows']) == 1
    assert report['researcher_responses'] == report['cumulative_responses_per_year'][0] + 1
    assert report['technical_failure']['failed_candidate_loss'] is None


def test_response_content_hash_tamper_is_detected(prepared):
    import sqlite3
    root, advance = prepared
    advance()
    with sqlite3.connect(root / 'runs/persistent-society/replies/responses.sqlite') as database:
        database.execute("UPDATE replies SET data_sha=? WHERE rowid=1", ('0' * 64,))
    with pytest.raises(ValueError, match='response identity/content hash'):
        analyze(root, require_complete=False)


def test_pre_adoption_archive_byte_tamper_is_detected(prepared):
    root, advance = prepared
    finish(root, advance)
    path = next((root / 'runs/persistent-society/checkpoints/design-migration-archives').glob('*.json.gz'))
    path.chmod(0o600)  # Intentional corruption of a disposable QA fixture only.
    path.write_bytes(b'not the observed whole society')
    with pytest.raises(ValueError, match='whole-society bytes'):
        analyze(root)


def test_raw_whole_tree_mutation_during_inspection_is_rejected(prepared, monkeypatch):
    from scripts import analyze_native_society_v6 as auditor
    root, advance = prepared
    advance()
    original = auditor.code_proofs
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        write_json_atomic(root / 'deliberate-fixture-mutation.json', {'QA': True})
        return result
    monkeypatch.setattr(auditor, 'code_proofs', changed)
    with pytest.raises(ValueError, match='raw evidence changed'):
        analyze(root, require_complete=False)


@pytest.mark.parametrize('different_discarded_result', [False, True])
def test_stop_after_physical_code_then_cold_resume_preserves_ambiguous_attempts(
        prepared, monkeypatch, different_discarded_result):
    """Actual scripted native restart; every physical receipt survives, none deduped."""
    from utopia.runtime.checkpointing import PortableStop
    root, advance = prepared
    first, _ = advance()
    author_pending(root, first, ScriptedExecutor())
    staged, _ = advance()
    stopped = {'value': False}
    execute = RecordingCodeExecutor.execute
    scripted = ScriptedExecutor.execute

    def scripted_attempt(self, artifact, context):
        result = scripted(self, artifact, context)
        if different_discarded_result and context['period'] == 2 and not stopped['value']:
            value = deepcopy(result.result)
            value['state']['discarded_scripted_attempt'] = True
            receipt = deepcopy(result.receipt)
            receipt['result_sha256'] = sha(value)
            return CodeExecution(value, receipt)
        return result

    def stop_after_record(self, artifact, context):
        result = execute(self, artifact, context)
        if context['period'] == 2 and not stopped['value']:
            stopped['value'] = True
            raise PortableStop('QA stop after physical code receipt but before year-two commit')
        return result

    monkeypatch.setattr(ScriptedExecutor, 'execute', scripted_attempt)
    monkeypatch.setattr(RecordingCodeExecutor, 'execute', stop_after_record)
    boundary = NativeSocietyDesignSession._boundary
    strict_rejected = []
    def checked_boundary(self, simulation, *, allow_observed_replay=False):
        from pathlib import Path
        from utopia.runtime.checkpointing import read_portable_checkpoint
        saved = read_portable_checkpoint(Path(simulation.output_dir) /
            f'portable_checkpoint_year_{simulation.native_system.last_year}.json.gz')
        if allow_observed_replay and simulation.llm.response_cache.committed_count() > saved['portable']['response_cache_count']:
            with pytest.raises(ValueError):
                boundary(self, simulation)  # Adoption/new-boundary path stays strict.
            strict_rejected.append(True)
        return boundary(self, simulation, allow_observed_replay=allow_observed_replay)
    monkeypatch.setattr(NativeSocietyDesignSession, '_boundary', checked_boundary)
    with pytest.raises(PortableStop, match='QA stop after physical code'):
        advance([staged['confirm_request_sha256']])
    # Original founding configuration, checkpoint, society and response cache;
    # the uncheckpointed year is rerun, not treated as another scientific year.
    second, session = advance()
    assert second['through_year'] == 2 and second['adoptions'] == 1
    author_pending(root, second, ScriptedExecutor())
    staged2, _ = advance()
    complete, session = advance([staged2['confirm_request_sha256']])
    assert complete['status'] == 'complete'
    before = inventory(root)
    report = analyze(root)
    assert inventory(root) == before
    evidence = report['code_contexts']
    assert report['classification'] == FIXTURE and report['status'] == 'complete'
    assert len(report['rows']) == 3 and len(report['adoptions']) == 2
    assert len(set(r['same_actor_ids_sha256'] for r in report['rows'])) == 1
    assert evidence['recorded_executions'] == len(evidence['physical_records']) == 3
    assert evidence['checkpointed_native_event_count'] == evidence['checkpointed_executions'] == 2
    assert evidence['one_to_one_physical_execution_proven'] is False
    assert evidence['status'] == 'physical-attempt-attribution-incomplete'
    assert evidence['uncheckpointed_execution_contexts'] == 0
    assert evidence['unattributed_completed_year_contexts'] == int(different_discarded_result)
    assert evidence['ambiguous_native_event_count'] == int(not different_discarded_result)
    assert [r['actual_activity_effects'] for r in report['rows']] == [0, 1, 1]
    assert report['uncheckpointed_responses'] == 0
    assert strict_rejected
    assert all(p['pinned_by_observation'] for p in report['response_prefix_proofs'])
    if not different_discarded_result:
        group = next(g for g in evidence['native_event_context_candidates'] if g['year'] == 2)
        assert group['physical_record_indices'] == [0, 1] and group['unique_attribution'] is False
    # Compare completed scientific serializers to an uninterrupted reference.
    # Session receipt IDs intentionally bind different host checkpoint bytes.
    reference_root, reference_advance = prepare_fixture(root.parent / (root.name + '-continuous'), monkeypatch)
    finish(reference_root, reference_advance)
    from pathlib import Path
    from utopia.runtime.checkpointing import read_portable_checkpoint
    def science(directory):
        config = json.loads((directory / 'society-session-config.json').read_text())
        state = read_portable_checkpoint(Path(config['checkpoint_directory']) / 'portable_checkpoint_year_3.json.gz')
        state['portable'].pop('outputs')  # Host output locations, not scientific state.
        state['paper_tracker'].pop('output_dir')
        state['native_system'].pop('design_history')  # Receipt identity, independently audited above.
        def normalize(value):
            if isinstance(value, dict):
                return {k: normalize(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [normalize(v) for v in value]
            if isinstance(value, set):
                return sorted(normalize(v) for v in value)
            if hasattr(value, 'to_dict'):
                return normalize(value.to_dict())
            if type(value).__name__ == 'FundingProgram':
                return normalize(vars(value))
            return value
        return normalize(state)
    assert science(root) == science(reference_root)


def test_changed_original_response_prefix_blocks_replay(prepared, monkeypatch):
    import sqlite3
    from utopia.runtime.checkpointing import PortableStop
    root, advance = prepared
    first, _ = advance()
    author_pending(root, first, ScriptedExecutor())
    staged, _ = advance()
    original = RecordingCodeExecutor.execute
    def stop(self, artifact, context):
        original(self, artifact, context)
        raise PortableStop('scripted interrupted year with committed reply tail')
    monkeypatch.setattr(RecordingCodeExecutor, 'execute', stop)
    with pytest.raises(PortableStop):
        advance([staged['confirm_request_sha256']])
    with sqlite3.connect(root / 'runs/persistent-society/replies/responses.sqlite') as database:
        # Internally hash-shaped, but no longer the exact previously pinned input.
        database.execute('UPDATE replies SET payload_sha=? WHERE rowid=1', ('e' * 64,))
    with pytest.raises(PortableStop) as error:
        advance()
    assert isinstance(error.value.__cause__, ValueError)
    assert 'observed response prefix changed' in str(error.value.__cause__)


def test_response_prefix_is_read_only_and_checks_original_and_extra_rows(tmp_path):
    from types import SimpleNamespace
    from tests.runtime.test_portable_checkpoint_integration import BINDING
    from utopia.runtime.checkpointing import PortableCheckpointError
    cache = CompletedResponseCache(tmp_path / 'cache.sqlite', binding=BINDING)
    def reply(value):
        return SimpleNamespace(model_dump=lambda **kwargs: {'fixture': value})
    try:
        cache.store('a' * 64, 'b' * 64, reply(1))
        prefix = cache.committed_prefix_identity(1)
        cache.store('c' * 64, 'd' * 64, reply(2))
        assert cache.committed_prefix_identity(1) == prefix
        assert cache.committed_count() == 2
        cache._db.execute('UPDATE replies SET data_sha=? WHERE identity=?', ('e' * 64, 'c' * 64))
        cache._db.commit()
        with pytest.raises(PortableCheckpointError, match='content/identity hash'):
            cache.committed_prefix_identity(1)  # Even the extra tail must be intact.
    finally:
        cache.close()


def test_primary_full_plan_lineage_has_effect_even_without_amendments():
    from scripts.analyze_native_society_v6 import primary_plan_proof
    plan = {'schema': 'native-research-plan-v1', 'year': 3, 'submit_actor_ids': ['actor'], 'assignments': [{
        'actor_id': 'actor', 'direction': {'topic': 'free topic'}, 'detailed_focus': 'full primary plan',
        'reason': 'scripted lineage QA', 'project_start_year': 3, 'project_end_year': 3}]}
    receipt = {key: key for key in ('image_id', 'artifact_sha256', 'context_sha256', 'result_sha256')}
    source = {'event_id': 'code-event', 'event_type': 'generated.code_executed',
        'provenance': {'mechanism_id': 'free-institution'}, 'payload': receipt}
    effect = {'event_id': 'effect', 'year': 3, 'provenance': {'mechanism_id': 'consumer',
        'input_event_ids': ['code-event']}, 'payload': {'amendments': [], 'plan_sha256': sha(plan)}}
    saved = {'native_system': {'events': [source], 'spec': {'connections': [{'source_mechanism': 'free-institution',
        'source_port': 'prepared', 'target_mechanism': 'consumer', 'target_port': 'plans', 'channel': 'artifact'}]}},
        'portable': {'agent_states': {'actor': {'state': {'project_start_year': 3, 'project_end_year': 3,
            'newest_direction': {key: plan['assignments'][0][key] for key in ('direction', 'detailed_focus', 'reason')}}}}},
        'paper_tracker': {'papers': [{'year': 3, 'id': 'actual-paper', 'author_id': 'actor'}]}}
    rows = [{'context': {'period': 3}, 'receipt': receipt,
        'result': {'outputs': {'prepared': [{'payload': plan}]}}}]
    proof = primary_plan_proof(saved, effect, rows)
    assert not effect['payload']['amendments']
    assert proof['verified_actor_assignment_ids'] == ['actor']
    assert proof['actual_unique_submission_ids'] == ['actual-paper']
    assert proof['source_native_event_ids'] == ['code-event']
    saved['portable']['agent_states']['actor']['state']['project_end_year'] = 4
    with pytest.raises(ValueError, match='actual saved actor state'):
        primary_plan_proof(saved, effect, rows)
