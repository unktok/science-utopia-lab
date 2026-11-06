"""SCRIPTED role separation, not evidence of actual 35B provider compatibility."""
import copy

import pytest

from tests.optimization.test_native_search_v14 import BINDING, REVISION, FailedFactory
from tests.optimization.test_native_search_v15 import request as old_request
from tests.optimization.test_native_search_generator_v14 import Model
from utopia.optimization.native_designer_roles_v38 import (
    LOCAL_DESIGNER_IDENTITIES, LocalRoleBoundDesignerModel,
    NativeRoleBoundSearchController, NativeRoleBoundSearchQueue,
    make_search_plan, validate_search_request, validate_designer_binding,
)
from utopia.optimization.native_search_v15 import validate_search_request as old_validate
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator
from utopia.optimization.native_search_generator_v14 import LocalQwenDesignerModel
from utopia.runtime.checkpointing import PortableStop
from utopia.system.design_patch import digest


def designer_binding():
    name = next(iter(LOCAL_DESIGNER_IDENTITIES))
    return {**copy.deepcopy(BINDING), 'model': name, 'model_digest': LOCAL_DESIGNER_IDENTITIES[name]}


def request(budget=2):
    value = old_request(budget=budget)
    binding = designer_binding()
    value.update(schema='scienceutopia.native-search-request.v38',
        designer={**value['designer'], 'model': binding['model'], 'provider_binding': binding})
    return value


def test_new_plan_keeps_actual_request_and_two_distinct_roles():
    body = request()
    original = copy.deepcopy(body)
    plan = make_search_plan(body, source_commit=REVISION, provider_binding=BINDING)
    assert body == original
    assert plan['request'] == body and plan['request_sha256'] == digest(body)
    assert plan['schema'] == 'scienceutopia.native-search-plan.v38'
    assert plan['provider_binding'] == BINDING
    assert plan['designer_provider_binding'] == designer_binding()
    assert plan['request']['designer']['model'] != plan['provider_binding']['model']
    assert plan['stage_counts'] == [1, 1]
    assert plan['maximum_designer_provider_attempts'] == 32
    with pytest.raises(ValueError):
        old_validate(body)
    hidden = old_request()
    hidden['designer']['model'] = designer_binding()['model']
    with pytest.raises(ValueError):
        old_validate(hidden)


@pytest.mark.parametrize('change', [
    lambda r: r['designer'].update(model='qwen3:8b'),
    lambda r: r['designer']['provider_binding'].update(model='remote:cloud'),
    lambda r: r['designer']['provider_binding'].update(model_digest='0' * 64),
    lambda r: r['designer']['provider_binding'].update(endpoint='https://example.invalid'),
    lambda r: r['designer'].update(max_steps=True),
    lambda r: r['designer'].update(max_tokens=9000),
    lambda r: r.update(seed=701),
    lambda r: r.update(native_budget=9),
    lambda r: r.update(command='host source'),
    lambda r: r.update(schema='scienceutopia.native-search-request.v15'),
])
def test_role_request_rejects_hidden_remote_or_changed_safety_settings(change):
    body = request(); change(body)
    with pytest.raises((ValueError, KeyError, TypeError)):
        validate_search_request(body)


@pytest.mark.parametrize('key,value', [
    ('corpus_sha256', 'different-corpus'),
    ('dataset_identity', {'different': 'dataset'}),
    ('image_id', 'sha256:' + '2' * 64),
])
def test_separate_designer_cannot_change_the_scientific_world(key, value):
    body = request(); body['designer']['provider_binding'][key] = value
    with pytest.raises(ValueError, match='share the exact'):
        make_search_plan(body, source_commit=REVISION, provider_binding=BINDING)


def test_old_model_class_stays_fixed_new_class_requires_pinned_local_identity():
    with pytest.raises(ValueError, match='qwen3:8b model only'):
        LocalQwenDesignerModel(designer_binding())
    model = LocalRoleBoundDesignerModel(designer_binding())
    assert model.binding == designer_binding()
    assert model.session.trust_env is False
    changed = designer_binding(); changed['model_digest'] = 'wrong'
    with pytest.raises(ValueError, match='approved installed local'):
        LocalRoleBoundDesignerModel(changed)


def test_queue_uses_designer_for_author_and_scientist_for_world_and_cold_resume(tmp_path):
    queue = NativeRoleBoundSearchQueue(tmp_path, provider_binding=BINDING)
    body = request()
    submitted = queue.submit(body, confirmed_request_sha256=digest(body), source_commit=REVISION)
    assert submitted['role_bindings'] == {'scientist': BINDING, 'designer': designer_binding()}
    assert submitted['authoring_trace']['warnings'] == []
    calls, authors = [], []

    def builder(root, current, binding):
        assert binding == designer_binding()
        assert current == body
        authors.append(copy.deepcopy(binding))
        model = Model([{'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'}])
        return StagedVocabularyGenerator(model, root / 'authoring', image_id=binding['image_id'],
            provider_binding=binding, max_steps=current['designer']['max_steps'],
            max_tokens=current['designer']['max_tokens'])

    def stop(_):
        raise PortableStop('SCRIPTED one committed stage, no actual models')

    with pytest.raises(PortableStop):
        queue.run_one(lambda *a: FailedFactory(calls), generator_builder=builder,
            source_commit=REVISION, after_stage=stop)
    partial = queue.get(submitted['search_id'])
    assert partial['budget']['consumed'] == 1
    assert partial['authoring_trace']['warnings'] == []
    reopened = NativeRoleBoundSearchQueue(tmp_path, provider_binding=BINDING)
    result = reopened.run_one(lambda *a: FailedFactory(calls), generator_builder=builder, source_commit=REVISION)
    assert result['status'] == 'complete' and result['budget']['consumed'] == 2
    assert authors == [designer_binding(), designer_binding()]
    assert len(calls) == len(set(calls)) == 2
    assert result['role_bindings']['scientist']['model'] == 'qwen3:8b'
    assert result['authoring_trace']['warnings'] == []
    assert result['live_progress']['designer']['attempts_completed'] == 2
    assert result['best']['loss'] is None
    assert reopened.run_one(lambda *a: pytest.fail('no repeat factory'),
        generator_builder=lambda *a: pytest.fail('no repeat author'), source_commit=REVISION) is None


def test_designer_binding_changes_invalidate_immutable_plan(tmp_path):
    body = request()
    plan = make_search_plan(body, source_commit=REVISION, provider_binding=BINDING)
    NativeRoleBoundSearchController(tmp_path, plan=plan, plan_sha256=digest(plan))
    plan['designer_provider_binding']['model_digest'] = '0' * 64
    with pytest.raises(ValueError, match='immutable search plan binding changed'):
        NativeRoleBoundSearchController(tmp_path, plan=plan, plan_sha256=digest(plan))


def test_worker_rejects_accidentally_stronger_scientists_before_author_dispatch(tmp_path):
    queue = NativeRoleBoundSearchQueue(tmp_path, provider_binding=BINDING)
    body = request(budget=1)
    queue.submit(body, confirmed_request_sha256=digest(body), source_commit=REVISION)
    factory = FailedFactory(); factory.model = designer_binding()['model']
    result = queue.run_one(lambda *a: factory,
        generator_builder=lambda *a: pytest.fail('scientist mismatch must stop first'), source_commit=REVISION)
    assert result['status'] == 'failed'
    assert result['budget']['consumed'] == 0
    assert 'actual native factory model/corpus differs' in str(result['errors'])


def test_new_pilot_keeps_original_losses_world_and_finite_budgets():
    from scripts.run_native_designer_roles_v38 import build_plan as pilot_plan, CLASSIFICATION, PROTOCOL
    plan = pilot_plan(source_commit=REVISION, initial_system=request()['initial_system'],
        provider_binding=BINDING, runtime_seed_binding={'python_hash_seed_environment': '42'},
        designer_provider_binding=designer_binding())
    assert plan['classification'] == CLASSIFICATION and plan['protocol'] == PROTOCOL
    assert plan['budget']['scheduled_native_slots'] == 8
    assert plan['budget']['maximum_generation_POSTs'] == 64
    assert plan['provider_binding'] == BINDING
    assert plan['designer_provider_binding'] == designer_binding()
    assert [r['id'] for r in plan['runs']] == ['throughput', 'efficiency']
    for entry in plan['runs']:
        assert entry['request']['native_budget'] == 4
        assert entry['request']['designer']['max_steps'] == 8
        assert entry['request']['designer']['max_tokens'] == 8192
        assert entry['runtime_plan']['request'] == entry['request']
        assert entry['runtime_plan']['provider_binding'] == BINDING
        assert entry['plan_sha256'] == digest(entry['runtime_plan'])


def test_mocked_stronger_designer_controls_use_exact_role_and_cold_certificate(tmp_path, monkeypatch):
    import json
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
    from tests.optimization.test_native_history_workspace_v37 import failed_request
    from utopia.optimization.native_designer_preflight import run_calibration, require_certificate
    from utopia.optimization.native_designer_roles_v38 import make_local_role_bound_generator
    binding = designer_binding()
    body = failed_request()
    binding['image_id'] = body['parent_system']['mechanisms'][0]['parameters']['runtime_image_id']

    class Session(ScriptedSession):
        def get(self, url, **kwargs):
            if url.endswith('/version'):
                return Response({'version': 'SCRIPTED-role-backend-only'})
            return Response({'models': [
                {'name': binding['model'], 'digest': binding['model_digest']},
                {'name': 'qwen3:8b', 'digest': 'b' * 64},
            ]})

        def post(self, url, **kwargs):
            payload = json.loads(kwargs['data'])
            assert payload['model'] == binding['model']
            response = super().post(url, **kwargs).json()
            response['model'] = binding['model']
            return Response(response)

    monkeypatch.setattr('requests.Session', Session)
    directory = tmp_path / 'SCRIPTED-stronger-designer-controls'
    result = run_calibration(directory, request=body, provider=binding)
    assert result['all_controls_passed'] and len(result['records']) == 28
    assert all(r['transport']['request_payload']['model'] == binding['model'] for r in result['records'])
    assert result['reasoning_evidence']['all_role_modes_compatible']
    certificate = directory / 'certificate.json'
    assert require_certificate(certificate, binding, protocol='staged-v15')['controls'] == 28
    wrong = {**binding, 'model': 'qwen3:8b', 'model_digest': 'b' * 64}
    with pytest.raises(ValueError):
        require_certificate(certificate, wrong, protocol='staged-v15')
    author = make_local_role_bound_generator(tmp_path / 'unused-author',
        image_id=binding['image_id'], provider_binding=binding, max_steps=8, max_tokens=8192,
        preflight_certificate=certificate)
    assert author.provider_binding == binding and isinstance(author.model, LocalRoleBoundDesignerModel)
    assert not (tmp_path / 'unused-author').exists()


def test_role_aware_audit_cold_replays_all_failure_journals_without_inference(tmp_path, monkeypatch):
    from scripts import analyze_native_staged_search_v15 as audit
    from scripts.run_native_designer_roles_v38 import build_plan as pilot_plan
    from utopia.system.native_open_examples import open_native_system
    from utopia.utils.data_utils import write_json_atomic
    from utopia.optimization.native_loaded_roles_v38 import SCIENTIST_DIGEST, record_loaded_context
    scientist = {**copy.deepcopy(BINDING), 'model_digest': SCIENTIST_DIGEST, 'corpus_sha256': '3' * 64}
    designer = {**scientist, **{k: designer_binding()[k] for k in ('model', 'model_digest')}}
    plan = pilot_plan(source_commit=REVISION, initial_system=open_native_system(scientist['image_id']).to_dict(),
        provider_binding=scientist, runtime_seed_binding={'python_hash_seed_environment': '42'},
        designer_provider_binding=designer)

    def save(path, value):
        write_json_atomic(path, value, sort_keys=True, allow_nan=False)

    save(tmp_path / 'plan.json', plan)
    save(tmp_path / 'operator-config.json', {'provider_binding': scientist, 'designer_provider_binding': designer})
    class MetadataSession:
        def get(self, url, **kwargs):
            from tests.optimization.test_native_designer_contract_v16 import Response
            return Response({'models': [{'name': b['model'], 'digest': b['model_digest'],
                'context_length': 40960} for b in (scientist, designer)]})
    record_loaded_context(tmp_path / 'loaded-role-context-before-pilot-000.json',
        expected={'scientist': scientist, 'designer': designer}, purpose='before-role-bound-pilot',
        session=MetadataSession())
    queue = NativeRoleBoundSearchQueue(tmp_path / 'queue', provider_binding=scientist)
    searches = {}
    for entry in plan['runs']:
        queued = queue.submit(entry['request'], confirmed_request_sha256=digest(entry['request']), source_commit=REVISION)
        searches[entry['id']] = queued['search_id']
    save(tmp_path / 'searches.json', searches)

    class FailingModel:
        calls = 0
        def generate(self, **kwargs):
            self.calls += 1
            raise RuntimeError('SCRIPTED pre-HTTP model failure, not an actual 35B call')
    model = FailingModel()

    def author(root, current, provider):
        assert provider == designer
        return StagedVocabularyGenerator(model, root / 'authoring', image_id=provider['image_id'],
            provider_binding=provider, max_steps=current['designer']['max_steps'], max_tokens=current['designer']['max_tokens'])

    def forbidden_world(*args):
        # Queue construction checks native model/corpus attributes even if no
        # candidate can execute. It must still be the scientist, not designer.
        factory = FailedFactory()
        factory.__dict__.update({k: v for k, v in scientist.items() if k != 'image_id'})
        return factory

    for _ in plan['runs']:
        queue.run_one(forbidden_world, generator_builder=author, source_commit=REVISION)
    runs = {name: queue.get(identity) for name, identity in searches.items()}
    progress = {'schema': plan['schema'] + '.progress', 'classification': plan['classification'],
        'source_commit': REVISION, 'plan_sha256': digest(plan), 'runs': runs, 'terminal': True,
        'scheduled_native_slots': 8, 'consumed_native_slots': 8}
    progress['content_sha256'] = digest(progress)
    save(tmp_path / 'progress.json', progress)
    # This test has no real source/provider claim; bypass source proofs ONLY
    # here, leaving every request/role/journal/loss/trace check intact.
    monkeypatch.setattr(audit, 'source_proofs', lambda *a, **k: {'status': 'SCRIPTED-no-actual-source-claim', 'files': {}})
    before = audit._inventory(tmp_path)
    first = audit.analyze(tmp_path, expected_source=REVISION)
    assert first == audit.analyze(tmp_path, expected_source=REVISION)
    assert before == audit._inventory(tmp_path)
    assert first['role_bindings'] == {'scientist': scientist, 'designer': designer}
    assert first['loaded_role_context_observations']['records'] == 1
    assert first['consumed_native_slots'] == first['technical_failures'] == 8
    assert first['physical_native_worlds'] == first['physical_researcher_responses'] == 0
    assert first['designer_costs']['dispatch_intents'] == model.calls == 64
    assert not first['claims']['operational_two_generation_native_feedback_arm']
    assert not first['claims']['live_fixed_Qwen_researchers']
    assert not first['claims']['scientific_benefit_established']
    assert audit.compact_summary(first)['role_bindings'] == first['role_bindings']
