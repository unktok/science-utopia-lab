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
