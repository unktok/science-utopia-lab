from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.data.rag import RAG
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.system.native_kernel import legacy_world_system


def install_transport(monkeypatch, *, drift=False):
    calls = []
    fixture_load = RAG.load_documents
    def load(rag, *args, **kwargs):
        calls.append(1)
        documents = fixture_load(rag, *args, **kwargs)
        rag.document_identity = 'different-corpus' if drift and len(calls) > 1 else 'fixed-corpus'
        rag.dataset_identity = {'dataset': 'explicit-QA-fixture'}
        return documents
    monkeypatch.setattr(RAG, 'load_documents', load)
    monkeypatch.setattr('requests.get', lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {'models': [{'name': 'qwen3:8b', 'digest': 'fixed-model'}]}))
    monkeypatch.setattr('utopia.models.models.OpenAI', lambda **kwargs: SimpleNamespace(
        models=SimpleNamespace(list=lambda: SimpleNamespace(data=[SimpleNamespace(id='qwen3:8b')])),
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: pytest.fail('no inference in factory QA')))))


def test_native_factory_binds_actual_corpus_and_builds_portable_original_world(tmp_path, fixed_corpus, monkeypatch):
    install_transport(monkeypatch)
    factory = LocalQwenNativeFactory(tmp_path / 'runs', tmp_path / 'cache', allow_dirty=True)
    sim = factory(legacy_world_system(), 42, 'factory-probe')
    try:
        assert factory.corpus_sha256 == 'fixed-corpus'
        assert sim.llm.response_cache.binding['corpus_sha256'] == factory.corpus_sha256
        assert sim.native_system.spec == legacy_world_system()
        assert sim.args.num_institutions == 5 and sim.args.researchers_per_institution == 1
        assert sim.llm.server_backend == 'ollama'
        assert sim.llm.thinking_override is False
    finally:
        sim.llm.response_cache.close()


def test_native_factory_refuses_corpus_drift_between_candidates(tmp_path, fixed_corpus, monkeypatch):
    install_transport(monkeypatch, drift=True)
    factory = LocalQwenNativeFactory(tmp_path / 'runs', tmp_path / 'cache', allow_dirty=True)
    with pytest.raises(ValueError, match='corpus changed'):
        factory(legacy_world_system(), 42, 'factory-probe')


def test_short_world_uses_explicit_larger_fixed_corpus_without_reloading_shorter_subset(tmp_path, fixed_corpus, monkeypatch):
    install_transport(monkeypatch)
    calls = []
    load = RAG.load_documents
    def record(rag, *args, **kwargs):
        calls.append(kwargs['num_years'])
        return load(rag, *args, **kwargs)
    monkeypatch.setattr(RAG, 'load_documents', record)
    factory = LocalQwenNativeFactory(tmp_path / 'runs', tmp_path / 'cache', years=2, corpus_years=4, allow_dirty=True)
    sim = factory(legacy_world_system(), 42, 'short-world')
    try:
        sim._prepare_paper_index(1)
        assert calls == [4, 4, 4]
        assert sim.num_years == 2
        assert sim.llm.response_cache.binding['science_config']['corpus_years'] == 4
    finally:
        sim.llm.response_cache.close()


@pytest.mark.parametrize('profile',['equal','balanced_two_band'])
def test_explicit_resource_conditions_reach_original_population_and_ledger(tmp_path,fixed_corpus,monkeypatch,profile):
    install_transport(monkeypatch)
    conditions={'schema':'scienceutopia.native-world-conditions.v1','initial_funding':60.,
        'population_resource_profile':profile,'log_resource_ledger':True}
    factory=LocalQwenNativeFactory(tmp_path/'runs',tmp_path/'cache',allow_dirty=True,world_conditions=conditions)
    conditions['initial_funding']=999. # caller mutation cannot silently reconfigure a prepared factory
    sim=factory(legacy_world_system(),42,'resource-condition-probe')
    try:
        sim.initialize_agents()
        sim.resource_ledger.start_year(1,sim.ecosystem.agent_population)
        authors=[a for a in sim.ecosystem.agent_population.values() if a.can_author]
        assert len(authors)==5 and sum(a.resources for a in authors)==300.
        assert sorted(a.resources for a in authors)==([60.]*5 if profile=='equal' else [30.,30.,80.,80.,80.])
        assert all(a.initial_funding==a.resources and a.is_active for a in authors)
        assert sim.resource_ledger is not None and all(a.resource_ledger is sim.resource_ledger for a in authors)
        bound=sim.llm.response_cache.binding['science_config']['world_conditions']
        assert bound==factory.world_conditions and bound['initial_funding']==60.
        assert sim.args.initial_funding==60. and sim.args.population_resource_profile==profile
        assert sim.args.log_resource_ledger
        from scripts.native_benchmark_physical import initial_world_conditions_proof
        state={'ecosystem_data':sim.ecosystem.to_dict(),'project_cost_policy':sim.cost_policy,
            'resource_ledger':sim.resource_ledger.to_dict()}
        proof=initial_world_conditions_proof(state,factory.world_conditions,42)
        assert proof['actual_initial_total']==300. and proof['ledger_present']
    finally:sim.llm.response_cache.close()


def test_absent_conditions_preserve_original_binding_and_population_defaults(tmp_path,fixed_corpus,monkeypatch):
    install_transport(monkeypatch)
    factory=LocalQwenNativeFactory(tmp_path/'runs',tmp_path/'cache',allow_dirty=True)
    sim=factory(legacy_world_system(),42,'original-condition-probe')
    try:
        sim.initialize_agents()
        assert 'world_conditions' not in sim.llm.response_cache.binding['science_config']
        assert sim.args.population_resource_profile=='equal' and not sim.args.log_resource_ledger
        assert [a.resources for a in sim.ecosystem.agent_population.values() if a.can_author]==[100.]*5
    finally:sim.llm.response_cache.close()


@pytest.mark.parametrize('bad',[{}, {'schema':'wrong'},
    {'schema':'scienceutopia.native-world-conditions.v1','initial_funding':0,'population_resource_profile':'equal','log_resource_ledger':True},
    {'schema':'scienceutopia.native-world-conditions.v1','initial_funding':float('nan'),'population_resource_profile':'equal','log_resource_ledger':True},
    {'schema':'scienceutopia.native-world-conditions.v1','initial_funding':True,'population_resource_profile':'equal','log_resource_ledger':True},
    {'schema':'scienceutopia.native-world-conditions.v1','initial_funding':60.,'population_resource_profile':'invented','log_resource_ledger':True}])
def test_invalid_operator_conditions_reject_before_any_model_or_corpus_access(tmp_path,monkeypatch,bad):
    monkeypatch.setattr('requests.get',lambda *a,**k:pytest.fail('no backend access'))
    with pytest.raises(ValueError,match='initial-resource conditions'):
        LocalQwenNativeFactory(tmp_path/'runs',tmp_path/'cache',world_conditions=bad)
