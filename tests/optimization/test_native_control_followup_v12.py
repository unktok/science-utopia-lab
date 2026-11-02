"""Forward-only followup software QA; scripted replies are never Qwen evidence."""
from copy import deepcopy
import fcntl
import json

import pytest

from scripts import run_native_control_followup_v12 as followup
from tests.optimization.test_native_adaptive_search import tiny_definition, tiny_parent
from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign, expectation_compatibility
from utopia.runtime.checkpointing import PortableStop
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


def fixture_plan():
    parent, definition, loss = tiny_parent(), tiny_definition(), loss_spec()
    compatibility = expectation_compatibility(GeneratedMixedDesign(parent, definition, loss_spec=loss, seed=43))
    receipt = {'audit_content_sha256': 'scripted-QA-not-v11-actual', 'compatibility_sha256': compatibility}
    return followup.make_plan(receipt, parent, definition, loss,
        {'source_commit': 'followup-scripted-QA', 'model_digest': 'fake-revision',
            'corpus_sha256': 'fixed-test-documents-v1', 'classification': 'scripted-fixture-not-native-results'})


def test_new_rng_stream_is_deterministic_preserves_exact_likelihoods_and_all_draws():
    plan = fixture_plan()
    a, version = followup.compile_draws(plan)
    b, other_version = followup.compile_draws(deepcopy(plan))
    assert a == b and version == other_version
    assert len(a) == followup.DRAWS == 2
    assert plan['draw_seed'] == 43 and plan['world_seed'] == 42
    assert all(row['suggestion']['proposal_index'] >= 4 for row in a)
    old = deepcopy(plan)
    old['draw_seed'] = 42
    earlier, _ = followup.compile_draws(old)
    assert [row['latent'] for row in a] != [row['latent'] for row in earlier]
    mixed = GeneratedMixedDesign(tiny_parent(), plan['definition'], loss_spec=plan['loss_spec'], seed=43)
    assert mixed.log_probabilities(a).detach().tolist() == [r['conditional_latent_log_probability'] for r in a]
    assert plan['optimizer_update'] is False and plan['causal_comparison'] is False


@pytest.mark.parametrize('mutation', ['source', 'likelihood', 'draw', 'extra-observation'])
def test_saved_batch_or_native_binding_tampering_refuses_before_factory(tmp_path, mutation):
    plan = fixture_plan()
    def stopped(*args):
        raise PortableStop('before first native execution')
    with pytest.raises(PortableStop):
        followup.advance(tmp_path, plan, simulation_factory=stopped, parent_guard=lambda: None)
    path = tmp_path / 'state.json'
    state = json.loads(path.read_text())
    if mutation == 'source': state['plan_sha256'] = 'changed'
    if mutation == 'likelihood': state['draws'][0]['conditional_latent_log_probability'] += .01
    if mutation == 'draw': state['draws'][0]['latent'][0] += .01
    if mutation == 'extra-observation': state['observations'] = [None, None, None]
    write_json_atomic(path, state)
    with pytest.raises(ValueError, match='immutable batch'):
        followup.advance(tmp_path, plan, simulation_factory=lambda *a: pytest.fail('no forward after tamper'),
            parent_guard=lambda: None)


def test_technical_failure_is_null_not_rerolled_or_followed_by_second_draw(tmp_path):
    plan, calls = fixture_plan(), []
    def fail(*args):
        calls.append(args)
        raise RuntimeError('scripted transport is unavailable')
    for _ in range(2):
        state = followup.advance(tmp_path, plan, simulation_factory=fail, parent_guard=lambda: None)
    assert len(calls) == 1 and len(state['observations']) == 1
    assert state['observations'][0]['status'] == 'failed'
    assert state['observations'][0]['loss'] is None
    result = followup.summarize(tmp_path, plan)
    assert result['status'] == 'technically-stopped' and result['complete_native_worlds'] == 0
    assert result['physical_reply_count'] == 0
    assert not result['claims']['post_final_cv_proposal_native_evaluated']
    assert not result['claims']['live_fixed_Qwen_researchers']
    assert not result['claims']['variance_reduction_established']


def test_parent_raw_guard_is_strictly_read_only_and_rejects_new_or_mutated_files(tmp_path):
    raw = tmp_path / 'parent'
    raw.mkdir()
    audit = tmp_path / 'audit.json'
    write_json_atomic(audit, {'audited': True})
    write_json_atomic(raw / 'evidence.json', {'frozen': True})
    receipt = {'audit_file_sha256': file_sha256(audit), 'raw_input_sha256s': followup._inventory(raw)}
    followup.guard_parent(raw, audit, receipt)
    assert followup._inventory(raw) == receipt['raw_input_sha256s']
    write_json_atomic(raw / 'unexpected.json', {})
    with pytest.raises(ValueError, match='immutable parent'):
        followup.guard_parent(raw, audit, receipt)


def test_changed_parent_audit_cannot_be_a_new_followup_parent(tmp_path):
    audit = tmp_path / 'audit.json'
    write_json_atomic(audit, {'status': 'complete', 'content_sha256': followup.PARENT_CONTENT_SHA256})
    with pytest.raises(ValueError, match='pinned independently audited'):
        followup.load_parent(tmp_path / 'parent', audit, tmp_path / 'old-audit-source')


@pytest.mark.parametrize('changed', [False, True])
def test_old_source_reaudit_is_separate_read_only_json_normalized_and_source_guarded(tmp_path, monkeypatch, changed):
    status_calls, child_calls = [], []
    def command(args, **kwargs):
        if args[0] == followup.sys.executable:
            child_calls.append(args)
            return json.dumps({'responses_by_physical_year': {1: 2, 2: 3}})
        if args[1] == 'status':
            status_calls.append(True)
            return b'M source' if changed and len(status_calls) > 1 else b''
        if args[1] == 'rev-parse': return 'clean-old-commit\n'
        pytest.fail('unexpected source audit command')
    monkeypatch.setattr(followup.subprocess, 'check_output', command)
    monkeypatch.setattr(followup, 'compatible_source_proof', lambda *a, **k: {'files': 'old-byte-proof'})
    if changed:
        with pytest.raises(ValueError, match='old audit source changed'):
            followup.reaudit_parent(tmp_path / 'parent', tmp_path / 'old-source')
    else:
        result, proof = followup.reaudit_parent(tmp_path / 'parent', tmp_path / 'old-source')
        assert result['responses_by_physical_year'] == {'1': 2, '2': 3}
        assert proof['source_commit'] == 'clean-old-commit'
        assert proof['new_model_calls'] == proof['new_container_executions'] == 0
    assert len(child_calls) == 1 and child_calls[0][1] == '-B'


def test_parent_guard_failure_occurs_before_any_forward_or_saved_outcome(tmp_path):
    def changed():
        raise ValueError('immutable parent changed')
    with pytest.raises(ValueError, match='immutable parent changed'):
        followup.advance(tmp_path, fixture_plan(), simulation_factory=lambda *a: pytest.fail('no forward'),
            parent_guard=changed)
    assert not (tmp_path / 'state.json').exists()


@pytest.mark.parametrize('relation', ['equal', 'inside-parent', 'ancestor-parent', 'contains-audit'])
def test_cli_rejects_old_parent_output_overlap_before_any_write_or_factory(tmp_path, monkeypatch, relation):
    parent = tmp_path / 'parent'
    audit = tmp_path / 'report' / 'audit.json'
    output = {'equal': parent, 'inside-parent': parent / 'child',
        'ancestor-parent': tmp_path, 'contains-audit': audit.parent}[relation]
    monkeypatch.setattr(followup.subprocess, 'check_output', lambda *a, **k: b'')
    monkeypatch.setattr('sys.argv', ['followup', '--parent-run', str(parent), '--parent-audit', str(audit),
        '--parent-audit-source', str(tmp_path / 'old-audit-source'),
        '--output', str(output), '--data-cache', str(tmp_path / 'data'),
        '--inference-lock', str(tmp_path / 'http.lock')])
    monkeypatch.setattr(followup, 'run', lambda *a: pytest.fail('no factory/parent mutation'))
    with pytest.raises(SystemExit) as error:
        followup.main()
    assert error.value.code == 2 and not parent.exists() and not audit.parent.exists()


def test_cli_exclusive_writer_before_parent_or_factory_access(tmp_path, monkeypatch):
    output = tmp_path / 'output'
    output.mkdir()
    monkeypatch.setattr(followup.subprocess, 'check_output', lambda *a, **k: b'')
    monkeypatch.setattr('sys.argv', ['followup', '--parent-run', str(tmp_path / 'parent'),
        '--parent-audit', str(tmp_path / 'audit.json'), '--parent-audit-source', str(tmp_path / 'old-audit-source'),
        '--output', str(output),
        '--data-cache', str(tmp_path / 'data'), '--inference-lock', str(tmp_path / 'http.lock')])
    monkeypatch.setattr(followup, 'run', lambda *a: pytest.fail('no factory before writer ownership'))
    with (output / 'followup-writer.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match='another v12 followup writer'):
            followup.main()


@pytest.mark.parametrize('mutation', ['reviewed-optimizer', 'unknown-optimizer', 'native-forward'])
def test_only_exact_reviewed_optimizer_extension_is_allowed(monkeypatch, tmp_path, mutation):
    names = [followup.OPTIMIZER_FILE, 'utopia/native_forward.py']
    old_bytes = b'frozen original bytes'
    old_sha = followup.hashlib.sha256(old_bytes).hexdigest()
    def git(args, **kwargs):
        if args[1] == 'show': return old_bytes
        return '\n'.join(names) + '\n'
    monkeypatch.setattr(followup.subprocess, 'check_output', git)
    hashes = {name: old_sha for name in names}
    if mutation == 'native-forward': hashes[names[1]] = '0' * 64
    else: hashes[names[0]] = followup.OPTIMIZER_EXTENSION_SHA256 if mutation == 'reviewed-optimizer' else '0' * 64
    monkeypatch.setattr(followup, 'file_sha256', lambda path: hashes[str(path.relative_to(tmp_path))])
    if mutation == 'reviewed-optimizer':
        proof = followup.compatible_source_proof(tmp_path)
        assert list(proof['reviewed_exceptions']) == [followup.OPTIMIZER_FILE]
        with pytest.raises(ValueError, match='source differs'):
            followup.compatible_source_proof(tmp_path, allow_optimizer_extension=False)
    else:
        with pytest.raises(ValueError, match='source differs'):
            followup.compatible_source_proof(tmp_path)


def test_original_six_year_native_scripted_world_cold_resume_no_update_no_rerun(
        tmp_path, fixed_corpus, monkeypatch):
    """Original Simulation + portable checkpoints + isolated source; fake HTTP/data."""
    from tests.optimization.test_native_adaptive_search import evolving_native_generator
    from tests.runtime.test_portable_checkpoint_integration import BINDING, seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('isolated runtime required for original-world scripted QA')
    parent = legacy_world_system()
    definition = evolving_native_generator(executor.image_id, [])({'generation': 0,
        'parent_system': parent.to_dict(), 'history': [], 'history_sha256': digest([])})
    loss = loss_spec()
    mixed = GeneratedMixedDesign(parent, definition, loss_spec=loss, seed=43)
    receipt = {'audit_content_sha256': 'scripted-not-actual-v11',
        'compatibility_sha256': expectation_compatibility(mixed)}
    world = {'source_commit': 'followup-scripted-native-QA', 'model_digest': BINDING['model_revision'],
        'corpus_sha256': BINDING['corpus_sha256'], 'classification': 'scripted-fixture-not-native-results'}
    plan = followup.make_plan(receipt, parent, definition, loss, world)
    monkeypatch.setattr(GeneratedMixedDesign, 'update', lambda *a, **k: pytest.fail('forward-only: no update'))
    runs, replies, guards = [], [], []
    def guard():
        guards.append('checked')
    def factory(spec, requested_seed, run_id):
        runs.append(run_id)
        assert requested_seed == 42
        if len(runs) == 2:
            raise PortableStop('cold stop after first committed native draw')
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        sim, calls = make_sim(tmp_path / 'worlds' / run_id, native=NativeScienceKernel(spec))
        replies.append(calls)
        return sim
    with pytest.raises(PortableStop):
        followup.advance(tmp_path, plan, simulation_factory=factory, parent_guard=guard)
    partial = json.loads((tmp_path / 'state.json').read_text())
    assert len(partial['observations']) == 1
    frozen_bytes = (tmp_path / 'plan.json').read_bytes()
    complete = followup.advance(tmp_path, plan, simulation_factory=factory, parent_guard=guard)
    assert len(complete['observations']) == 2 and complete['observations'][0] == partial['observations'][0]
    assert len(runs) == 3 and runs[1] == runs[2] and runs[0] != runs[1]
    assert len(replies) == 2 and all(replies) and len(guards) >= 6
    again = followup.advance(tmp_path, plan, simulation_factory=lambda *a: pytest.fail('no third native world'),
        parent_guard=guard)
    assert again == complete and (tmp_path / 'plan.json').read_bytes() == frozen_bytes
    assert complete['draws'] == partial['draws'] and 'gradient' not in complete
    for observation in complete['observations']:
        checkpoint = read_portable_checkpoint(observation['metadata']['runs'][0]['checkpoint_path'])
        stages = [e['payload']['stage'] for e in checkpoint['native_system']['events']
            if e['event_type'] == 'native.system.phase_executed']
        assert stages.count('research') == stages.count('publication') == 6
        assert observation['metadata']['measurements'][0]['metrics']['native.review_records']['value'] > 0
    result = followup.summarize(tmp_path, plan)
    assert result['status'] == 'complete' and result['complete_native_worlds'] == 2
    assert result['claims']['post_final_cv_proposal_native_evaluated']
    assert not result['claims']['live_fixed_Qwen_researchers']
    assert not result['claims']['gradient_update_after_followup']
