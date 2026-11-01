"""Real six-year scientific phases; scripted corpus/HTTP, not live invention."""
from copy import deepcopy
import json

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.system.test_native_migration import notice_spec, register_notice, domain
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_society_design import NativeSocietyDesignSession
from utopia.optimization.native_world import measure_native_world
from utopia.runtime.checkpointing import PortableStop, capture_rng
from utopia.system.design_patch import make_patch
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system


def session(directory, **kwargs):
    return NativeSocietyDesignSession(directory, founding_system=legacy_world_system(),
        loss_spec=kwargs.get('loss', loss_spec()),
        world_binding={'origin': 'actual-native-phases-scripted-corpus-http-QA'})


def patch_to(parent, target):
    return make_patch(parent, [{'op': 'replace', 'path': '/' + key, 'value': value}
        for key, value in target.to_dict().items() if value != parent.to_dict()[key]])


def test_online_loss_proposal_adoption_feedback_and_original_config_resume(tmp_path, fixed_corpus):
    root = tmp_path / 'society'
    controller = session(tmp_path / 'session')
    sim, calls = make_sim(root, native=NativeScienceKernel(legacy_world_system(), registry_extension=register_notice))
    original = sim.checkpoint_callback
    observed, installed = [], []

    def boundary(path):
        original(path)
        if sim.native_system.last_year < 1:
            return
        observation = controller.observe(sim)
        observed.append(observation)
        assert controller.observe(sim) == observation  # no duplicate measurements
        if sim.native_system.last_year not in (1, 3):
            return
        # A designer sees actual prior losses, exact current graph and adoption
        # effects. These are developer-authored policies, not LLM invention.
        view = controller.projection()
        assert view['observations'][-1]['loss'] == observation['loss']
        parent = sim.native_system.spec
        target = notice_spec(parent) if sim.native_system.last_year == 1 else notice_spec(legacy_world_system(), 'second-notice')
        request = controller.stage(parent_observation_id=observation['observation_id'],
            patch=patch_to(parent, target), authoring={'identity': 'scripted-QA-designer',
                'feedback_observation_ids': [o['observation_id'] for o in observed]})
        assert controller.adoption_status(request['request_id'], checkpoint=path)['status'] == 'pending'
        pending = controller.confirm(request_id=request['request_id'], confirmed_request_sha256=request['request_sha256'])
        assert pending['status'] == 'pending'
        assert len(controller.projection()['adoptions']) == len(installed)
        assert controller.confirm(request_id=request['request_id'], confirmed_request_sha256=request['request_sha256']) == pending
        before, rng = domain(sim), capture_rng()
        with pytest.raises(ValueError, match='confirmation'):
            controller.adopt(sim, request_id=request['request_id'], confirmed_request_sha256='0' * 64)
        pre_adoption_kernel = sim.native_system
        receipt = controller.adopt(sim, request_id=request['request_id'],
            confirmed_request_sha256=request['request_sha256'])
        assert domain(sim) == before and capture_rng() == rng
        assert receipt == controller.adopt(sim, request_id=request['request_id'],
            confirmed_request_sha256=request['request_sha256'])
        verified = controller.adoption_status(request['request_id'], checkpoint=path)
        assert verified['status'] == 'adopted' and verified['verified_receipt']
        assert verified['migration_receipt_sha256'] == receipt['migration_receipt_sha256']
        assert controller.adoption_status(request['request_id'])['status'] == 'pending'
        from types import SimpleNamespace
        with controller._lock():
            with pytest.raises(ValueError, match='acknowledged adoption'):
                controller._reconcile(controller._read(), SimpleNamespace(native_system=pre_adoption_kernel))
        installed.append(request['request_sha256'])

    sim.checkpoint_callback = boundary
    try:
        sim.run()
        assert len(observed) == 6 and len(installed) == 2
        assert observed[1]['preceding_adoption'] == installed[0]
        assert observed[3]['preceding_adoption'] == installed[1]
        assert observed[1]['after_year'] == 1 and observed[1]['through_year'] == 2
        assert any('Migration notice' in json.dumps(payload) for (ctx, _, _), payload in calls
                   if ctx[:2] == ('phase1_directions', 3))
        assert sum(o['measurement']['metrics']['native.accepted_decisions']['value'] for o in observed) == (
            measure_native_world(sim, run_id='all')['metrics']['native.accepted_decisions']['value'])
        saved = sim.native_system.to_dict()
        assert controller.projection()['pending'] is None
        assert not controller.projection()['causal_improvement_established']
    finally:
        sim.llm.response_cache.close()
    seed()
    resumed, resumed_calls = make_sim(root, native=NativeScienceKernel(legacy_world_system(), registry_extension=register_notice))
    try:
        resumed.run()
        assert not resumed_calls and resumed.native_system.to_dict() == saved
        assert session(tmp_path / 'session').projection() == controller.projection()
    finally:
        resumed.llm.response_cache.close()


def test_committed_migration_recovers_missing_journal_ack_on_cold_restart(tmp_path, fixed_corpus, monkeypatch):
    controller = session(tmp_path / 'session')
    root = tmp_path / 'society'
    sim, _ = make_sim(root, native=NativeScienceKernel(legacy_world_system(), registry_extension=register_notice))
    original = sim.checkpoint_callback
    requests = []
    def boundary(path):
        original(path)
        if sim.native_system.last_year != 1:
            return
        observation = controller.observe(sim)
        request = controller.stage(parent_observation_id=observation['observation_id'],
            patch=patch_to(sim.native_system.spec, notice_spec(sim.native_system.spec)),
            authoring={'identity': 'scripted-crash-QA'})
        requests.append(request)
        append = controller._append
        def crash(state, kind, payload):
            if kind == 'adopted':
                raise PortableStop('crash after society commit before journal ack')
            return append(state, kind, payload)
        monkeypatch.setattr(controller, '_append', crash)
        controller.adopt(sim, request_id=request['request_id'], confirmed_request_sha256=request['request_sha256'])
    sim.checkpoint_callback = boundary
    try:
        with pytest.raises(PortableStop, match='journal ack'):
            sim.run()
        assert len(sim.native_system.design_history) == 1
    finally:
        sim.llm.response_cache.close()
    seed()
    resumed, _ = make_sim(root, native=NativeScienceKernel(legacy_world_system(), registry_extension=register_notice))
    recovered = session(tmp_path / 'session')
    original = resumed.checkpoint_callback
    def next_boundary(path):
        original(path)
        observation = recovered.observe(resumed)
        if resumed.native_system.last_year > 1:
            assert observation['preceding_adoption'] == requests[0]['request_sha256']
        assert recovered.projection()['adoptions'][0]['request_sha256'] == requests[0]['request_sha256']
    resumed.checkpoint_callback = next_boundary
    try:
        resumed.run()
        view = recovered.projection()
        assert len(view['adoptions']) == 1 and view['pending'] is None
        assert len(resumed.native_system.design_history) == 1
    finally:
        resumed.llm.response_cache.close()


@pytest.mark.parametrize('mutation', ['resources', 'rag', 'agent_extra', 'initial_count', 'outputs'])
def test_unsaved_domain_mutation_and_stale_boundary_cannot_be_installed(tmp_path, fixed_corpus, mutation):
    controller = session(tmp_path / 'session')
    sim, _ = make_sim(tmp_path / 'society', native=NativeScienceKernel(legacy_world_system(), registry_extension=register_notice))
    original = sim.checkpoint_callback
    def boundary(path):
        original(path)
        if sim.native_system.last_year != 1:
            return
        observation = controller.observe(sim)
        request = controller.stage(parent_observation_id=observation['observation_id'],
            patch=patch_to(sim.native_system.spec, notice_spec(sim.native_system.spec)),
            authoring={'identity': 'scripted-invalid-QA'})
        agent = next(iter(sim.ecosystem.agent_population.values()))
        if mutation == 'resources':
            agent.resources += 1
        elif mutation == 'rag':
            sim.rag.document_status.loc[0, 'status'] = 'unsaved-mutation'
        elif mutation == 'agent_extra':
            agent.new_unsaved_capability_state = {'not_in_legacy_to_dict': True}
        elif mutation == 'initial_count':
            sim.initial_university_count = (sim.initial_university_count or 0) + 1
        else:
            from utopia.utils.data_utils import write_bytes_atomic
            write_bytes_atomic(next(iter(sim._portable_replay_paths.values())), b'unsaved output')
        before = sim.native_system.to_dict()
        with pytest.raises(ValueError, match='stale'):
            controller.adopt(sim, request_id=request['request_id'], confirmed_request_sha256=request['request_sha256'])
        assert sim.native_system.to_dict() == before
        raise PortableStop('invalid adoption checked')
    sim.checkpoint_callback = boundary
    try:
        with pytest.raises(PortableStop, match='invalid adoption checked'):
            sim.run()
    finally:
        sim.llm.response_cache.close()


def test_loss_binding_and_journal_tampering_are_rejected(tmp_path):
    controller = session(tmp_path)
    with pytest.raises(ValueError, match='binding'):
        session(tmp_path, loss=loss_spec(coefficient=1.))
    state = json.loads(controller.path.read_text())
    with controller._lock():
        controller._append(state, 'observed', {'example': True})
    state = json.loads(controller.path.read_text())
    state['events'][0]['payload']['example'] = False
    with controller._lock():
        controller._save(state)
    with pytest.raises(ValueError, match='hash chain'):
        session(tmp_path)


def test_external_proposer_receives_loss_and_feedback_then_explicit_cancel(tmp_path, fixed_corpus):
    controller = session(tmp_path / 'session')
    sim, _ = make_sim(tmp_path / 'society', native=NativeScienceKernel(legacy_world_system(), registry_extension=register_notice))
    original = sim.checkpoint_callback
    def boundary(path):
        original(path)
        if sim.native_system.last_year != 1:
            return
        observation = controller.observe(sim)
        seen = []
        def propose(parent, feedback, index, declared_loss):
            assert declared_loss == loss_spec() and index == 0
            assert feedback['observations'][-1] == observation
            assert parent.to_dict() == observation['system']
            seen.append(feedback)
            return patch_to(parent, notice_spec(parent))
        request = controller.author(propose, authoring={'identity': 'scripted-proposer'})
        assert seen and request['authoring']['proposer_input_sha256']
        assert controller.author(lambda *a: pytest.fail('reuse pending'), authoring={'identity': 'same'}) == request
        controller.cancel(sim, request_id=request['request_id'],
            confirmed_request_sha256=request['request_sha256'], reason='explicitly stop unexecuted QA design')
        assert controller.projection()['pending'] is None
        with pytest.raises(ValueError, match='cancelled'):
            controller.adopt(sim, request_id=request['request_id'], confirmed_request_sha256=request['request_sha256'])
        assert not sim.native_system.design_history
        raise PortableStop('authoring and explicit cancellation verified')
    sim.checkpoint_callback = boundary
    try:
        with pytest.raises(PortableStop, match='cancellation'):
            sim.run()
    finally:
        sim.llm.response_cache.close()
